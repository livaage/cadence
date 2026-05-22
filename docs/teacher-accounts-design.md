# Design — Teacher accounts, folders, and guest mode coexistence

Status: design-only, decisions locked in §11. No code written yet — implementation begins post-Saturday demo.

## 1 — Goals

Add persistent teacher identity on the server, without giving up the "no login, two-line install" pitch.

1. A teacher can sign in (Google, GitHub, or email magic link) and see **every course and lesson they own** across devices.
2. Lessons can be **organised into flat folders** (rename, delete, move).
3. The current `%cadence_create_lesson` flow keeps working untouched for anyone who doesn't sign in — anonymous lessons remain a supported product mode, not a fallback.
4. Anonymous lessons created before a teacher signs in can be **claimed** into their account in one step.

## 2 — Non-goals (for v1)

- Nested folders. A single level of folders is enough; defer hierarchy until a real user complains.
- Multi-owner / co-teacher / TA sharing. Each lesson has at most one owner.
- Password-based signup. Only OAuth + magic link. Avoids password reset, lockouts, breach handling.
- Student accounts. Students still join by code under any display name they pick.
- Migrating away from `~/.cadence/lessons.yaml`. The local YAML stays — see §8.

## 3 — Coexistence model

Two product modes share the same backend. The model the teacher experiences depends on whether they sign in.

| | **Guest mode (today)** | **Signed-in mode (new)** |
|---|---|---|
| How a lesson is created | `%cadence_create_lesson` from a notebook | Same magic, or via web UI |
| Credential | `teacher_token` in URL | Session cookie + `teacher_token` in URL (either works) |
| Where credentials live | `~/.cadence/lessons.yaml` (mode 0600) | Server is source of truth; YAML becomes an offline cache |
| Multi-device | Copy YAML across machines manually | Sign in on the new device |
| Recover from local wipe | Re-create lesson; old token is gone | Sign in, lessons are still there |
| `Lesson.owner_id` | `NULL` | `teacher.id` |
| Dashboard URL still shareable | Yes | Yes (token-in-URL still grants dashboard access) |

The two modes are not separate code paths — they're the same flow with `owner_id` either `NULL` or set.

## 4 — Data model

Reuse the existing `Teacher` table; rework its columns. Add three new tables. Add nullable `owner_id` to `Lesson` and `Course`. Add nullable `folder_id` to both.

### 4.1 Teacher (rebuilt)

The legacy `username` + `password_hash` columns are dropped. The legacy `/auth/login` endpoint and the `admin/teacher123` row are removed in the same migration. The legacy code-competition UI no longer needs a login.

```
teachers
  id              UUID PK
  display_name    TEXT NOT NULL                 -- "Daniel Pearson"
  primary_email   CITEXT UNIQUE NOT NULL        -- canonical identity
  avatar_kind     TEXT NOT NULL                 -- 'animal:fox' | 'provider' | 'initials'
  avatar_url      TEXT NULL                     -- only set when avatar_kind = 'provider'
  is_active       BOOLEAN NOT NULL DEFAULT TRUE -- soft-disable
  created_at      TIMESTAMP NOT NULL
```

`avatar_kind` is a single string column rather than several flags — it directly encodes the picked option. `'animal:fox'` references one of the SVG assets in §5.5. `'provider'` means render `avatar_url`. `'initials'` falls back to a coloured circle with the first letter of `display_name`.

### 4.2 OAuthIdentity (new)

```
oauth_identities
  id              UUID PK
  teacher_id      UUID FK -> teachers.id  ON DELETE CASCADE
  provider        TEXT NOT NULL CHECK (provider IN ('google','github','email_magic'))
  provider_subject TEXT NOT NULL            -- stable provider user id ('sub' claim)
  email_at_signup TEXT
  created_at      TIMESTAMP
  UNIQUE (provider, provider_subject)
```

Multiple identities can map to one teacher (sign in with Google one day, GitHub another — same account). The linking rule: if an OAuth callback returns an email that matches an existing `teachers.primary_email`, link as a new identity; otherwise create a new teacher.

### 4.3 MagicLinkToken (new)

```
magic_link_tokens
  id              UUID PK
  email           CITEXT NOT NULL
  token_hash      TEXT NOT NULL    -- sha256 of the link nonce; raw nonce never stored
  expires_at      TIMESTAMP NOT NULL
  consumed_at     TIMESTAMP        -- null until used; single-use
  created_at      TIMESTAMP
  INDEX (email, expires_at)
```

15 min expiry, single use, rate-limited 3 sends / 15 min / email.

### 4.4 WebSession (new)

```
web_sessions
  id              UUID PK
  teacher_id      UUID FK -> teachers.id  ON DELETE CASCADE
  session_token_hash TEXT NOT NULL   -- sha256 of the cookie value
  user_agent      TEXT
  created_at      TIMESTAMP
  last_seen_at    TIMESTAMP
  expires_at      TIMESTAMP          -- 30 day sliding window
  INDEX (teacher_id, expires_at)
```

Cookie name `cadence_session`, HTTPOnly, Secure (in prod), SameSite=Lax. JWTs not used for sessions — opaque tokens are simpler to revoke. (The legacy `/auth/login` JWT stays for backward compat on the legacy admin pages, but the new auth is cookie-based.)

### 4.5 Folder (new)

```
folders
  id              UUID PK
  owner_id        UUID FK -> teachers.id  ON DELETE CASCADE
  name            TEXT NOT NULL
  color           TEXT             -- hex, optional; for UI affordance
  order_index     INTEGER DEFAULT 0
  created_at      TIMESTAMP
  UNIQUE (owner_id, name)
```

Flat — no `parent_folder_id`. Folders are per-teacher; no cross-teacher visibility in v1.

### 4.6 Lesson + Course (modified)

```
ALTER TABLE lessons ADD COLUMN owner_id UUID NULL REFERENCES teachers(id) ON DELETE SET NULL;
ALTER TABLE lessons ADD COLUMN folder_id UUID NULL REFERENCES folders(id) ON DELETE SET NULL;
ALTER TABLE lessons ADD COLUMN archived_at TIMESTAMP NULL;

ALTER TABLE courses ADD COLUMN owner_id UUID NULL REFERENCES teachers(id) ON DELETE SET NULL;
ALTER TABLE courses ADD COLUMN folder_id UUID NULL REFERENCES folders(id) ON DELETE SET NULL;
ALTER TABLE courses ADD COLUMN archived_at TIMESTAMP NULL;
```

`ON DELETE SET NULL` on `owner_id` is deliberate — if a teacher account is deleted, their lessons revert to guest/anonymous rather than cascading delete and destroying student attempt data.

Soft-delete via `archived_at` rather than hard delete, so a teacher can recover from a misclick. A nightly job (later, not v1) can purge rows with `archived_at < now() - 30d`.

## 5 — Auth flows

### 5.1 Sign-in page UI

`/teacher/signin` renders three buttons + an email field:

```
┌───────────────────────────────────────┐
│  Sign in to Cadence                   │
│                                       │
│  [ Continue with Google     ]         │
│  [ Continue with GitHub     ]         │
│                                       │
│  ─── or with an email link ───        │
│                                       │
│  [ teacher@school.edu        ] [Send] │
│                                       │
│  No account? Just continue —          │
│  we create one on first sign-in.      │
│                                       │
│  Or skip → use Cadence without an     │
│  account (guest mode).                │
└───────────────────────────────────────┘
```

The "skip → guest mode" link is important: it makes guest mode visible as a deliberate choice, not just the default for people who didn't sign up.

### 5.2 OAuth (Google / GitHub)

Standard auth-code flow with PKCE:

```
browser            backend                    provider
   │   GET /auth/google/start                    │
   │ ────────────────────────►                   │
   │                  (mint state + PKCE,        │
   │                   stash in short-lived      │
   │                   cookie)                   │
   │   302 to provider with redirect_uri         │
   │ ◄────────────────────────                   │
   │   (browser auths)                           │
   │ ──────────────────────────────────────────► │
   │   302 back to /auth/google/callback?code=…  │
   │ ◄────────────────────────────────────────── │
   │   GET /auth/google/callback                 │
   │ ────────────────────────►                   │
   │              (exchange code for tokens,     │
   │               verify state, look up email   │
   │               in teachers; create or link)  │
   │   Set-Cookie cadence_session=...            │
   │   302 to /teacher/home                      │
   │ ◄────────────────────────                   │
```

Provider config lives in env: `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GITHUB_OAUTH_CLIENT_ID`, `GITHUB_OAUTH_CLIENT_SECRET`. If either pair is missing, the corresponding button doesn't render.

### 5.3 Email magic link

```
browser                backend                 email
   │  POST /auth/email/start                       │
   │  {email}                                      │
   │ ──────────────────►                           │
   │                (mint nonce, store hash,       │
   │                 send link)                    │
   │                              ──────────────► │
   │                                               │  [email arrives]
   │  GET /auth/email/verify?token=NONCE           │
   │ ──────────────────────────────────►           │
   │                (consume token, find-or-create │
   │                 teacher by email, link)       │
   │  Set-Cookie cadence_session=...               │
   │  302 to /teacher/home                         │
   │ ◄──────────────────                           │
```

Email provider: **Resend** (free 100/day tier). `RESEND_API_KEY` env var, single HTTPS POST per send. From-address must be on a verified domain — until that's set up, send from Resend's `onboarding@resend.dev` for local dev only.

Rate limit: 3 sends / 15 min / email; 20 sends / hour / IP.

### 5.4 First sign-in claim of guest lessons

When a teacher signs in for the first time on a device that already has `~/.cadence/lessons.yaml`, the local CLI (or the magic) should offer to upload the tokens and claim the matching lessons.

The mechanism is a single endpoint: `POST /me/claim` with body `{"teacher_tokens": [...]}`. Server-side, for each token:

- look up the `Lesson`/`Course`
- if `owner_id IS NULL` → set to this teacher; return `claimed`
- if `owner_id == this teacher` → return `already_yours`
- if `owner_id == someone else` → return `denied` (someone already claimed it; rare unless tokens leaked)

Claim is initiated from either:
- `cadence-cli login` finishing successfully — automatically uploads YAML and offers a yes/no prompt
- The web home page banner: "We see you have N anonymous lessons cached locally — claim them?"

**Auto-rotation on claim.** When a lesson is claimed, the server mints a fresh `teacher_token` and `join_code` (the latter only if `--rotate-join-code` is set; default keeps the join code stable so students don't lose access mid-lesson). The old `teacher_token` is immediately invalidated. The claim response returns the new credentials, and `cadence-cli` / the magic update `~/.cadence/lessons.yaml` automatically.

This serves two purposes:
1. **Security:** any old URL that leaked into chat logs, screenshots, or `.yaml` files on backed-up folders stops working the moment you sign in. Claiming = clean slate.
2. **Incentive:** rotation is a tangible benefit of signing in — guest mode users who want this protection get it for free by upgrading.

UX: the post-claim page shows "Lessons claimed: 5. We've rotated your tokens — your bookmarks need updating. Here are the new dashboard URLs:" with copy-to-clipboard buttons. The rotation event is recorded so we can show "rotated 2 minutes ago" on each lesson card.

### 5.5 Avatars (animal picker + provider photo)

`avatar_kind` (§4.1) decides what the UI shows.

**At first sign-in** the default depends on provider:
- Magic link: no provider image available → assign a **random animal** from the set below. Delightful, no extra step required.
- OAuth (future): use the provider's avatar URL. User can change it later.

**In account settings** the teacher can switch between:
1. **Animal** — picker grid of 16 SVGs:
   `fox, owl, cat, dog, panda, otter, capybara, hedgehog, rabbit, raccoon, bear, deer, koala, sloth, penguin, axolotl`
2. **Provider photo** — only available if at least one linked OAuth identity has a usable URL.
3. **Initials** — first letter of `display_name`, deterministic colour hash.

The SVGs ship in `frontend/public/avatars/animals/{name}.svg`. ~3 KB each. Backend doesn't host the images — it just stores the kind string. The frontend resolves `animal:fox` → `/avatars/animals/fox.svg`.

`PATCH /me` with `{"avatar_kind": "animal:owl"}` updates the choice; no upload endpoint, no image processing pipeline. Adding more animals later is a frontend-only change — drop the SVG in the folder, add it to the picker list. The backend never validates the name (forward-compat).

## 6 — API surface

### 6.1 New endpoints

```
GET    /auth/providers            → ["google", "github", "email_magic"]
GET    /auth/google/start         → 302
GET    /auth/google/callback      → 302
GET    /auth/github/start         → 302
GET    /auth/github/callback      → 302
POST   /auth/email/start          {email}
GET    /auth/email/verify         ?token=...
POST   /auth/logout

GET    /me                        → {id, display_name, primary_email, avatar_kind, avatar_url?}
PATCH  /me                        {display_name?, avatar_kind?}
POST   /me/claim                  {teacher_tokens: [...]} → per-token: {old_token, new_token, join_code, new_dashboard_url}
DELETE /me                        {delete_lessons?: bool=false}
                                  → default: lessons revert to owner_id=NULL (anonymous, still reachable by URL)
                                  → delete_lessons=true: also archives every owned lesson

GET    /me/folders                → [{id, name, color, item_count}]
POST   /me/folders                {name, color?}
PATCH  /me/folders/{id}           {name?, color?, order_index?}
DELETE /me/folders/{id}           → items move to "no folder"

GET    /me/library                → {folders: [...], items: [{kind, id, name, ...}]}
                                  → kind ∈ {"lesson","course"}, sorted by recent activity
PATCH  /lessons/{id}              {name?, folder_id?, archived?}
PATCH  /courses/{id}              {name?, folder_id?, archived?}
DELETE /lessons/{id}              → sets archived_at (soft)
DELETE /courses/{id}              → sets archived_at (soft)
```

### 6.2 Existing endpoints stay

All `/lessons/by-token/...` and `/lessons/by-code/...` endpoints stay exactly as they are. They authorise via the URL-embedded `teacher_token`, regardless of whether the lesson has an owner. This is what preserves the share-a-link UX.

`POST /lessons` and `POST /courses` get an optional behaviour: if the request carries a valid `cadence_session` cookie, the new row is created with `owner_id = teacher.id`. If no cookie, `owner_id = NULL` (guest). Backward-compatible.

### 6.3 AuthZ rules summarised

| Request | Authorised when |
|---|---|
| `GET /lessons/by-token/T/live` | `T` is a real token. Same as today. |
| `POST /lessons/by-token/T/checkpoints` | Same. |
| `PATCH /lessons/{id}` (rename/move) | session cookie present AND `Lesson.owner_id == session.teacher_id` |
| `DELETE /lessons/{id}` | same |
| `GET /me/library` | session cookie present |

`PATCH` / `DELETE` deliberately require a session — the `teacher_token` lets you read the dashboard and register checkpoints, but it does NOT let you delete the lesson. That's an intentional asymmetry to protect against leaked-token destruction.

## 7 — Web UI

### 7.1 New routes

| Route | Component | Notes |
|---|---|---|
| `/teacher/signin` | `SignIn` | Provider buttons + email input |
| `/teacher/home` | `TeacherHome` | Library — folders + items |
| `/teacher/folder/:id` | `FolderView` | Filtered library |
| `/teacher/account` | `AccountSettings` | Display name, linked identities, sign out, delete account |

### 7.2 Library layout

```
┌──────────────────────────────────────────────────────────────┐
│ Cadence                          [+ New course] [+ New lesson]│ Daniel ▾
├──────────────────────────────────────────────────────────────┤
│ Folders                                          [+ Folder]   │
│  • Fall 2026 (5)    • Spring 2026 (3)    • Drafts (2)         │
│                                                                │
│ All items                              ⌕ search    [▾ recent] │
│ ┌──────────────────────────────────────────────────────────┐  │
│ │ 📚 Intro to Python — Fall 2026    course  · 8 notebooks  │  │
│ │     join code: soup-river-42     ⋯ rename │ move │ del   │  │
│ ├──────────────────────────────────────────────────────────┤  │
│ │ 📓 Week 3: Fibonacci              lesson  · 23 attempts  │  │
│ │     last student: 2 min ago      ⋯                       │  │
│ ├──────────────────────────────────────────────────────────┤  │
│ │ 📓 Week 1 — Variables              lesson  · archived    │  │
│ └──────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

Drag-and-drop into folders (HTML5 DnD; nothing exotic). Each row links to its existing dashboard URL — i.e. the library is a router for the existing `LiveProgress` and `CourseOverview` pages, not a replacement.

### 7.3 Existing dashboard pages

`/teacher/live?token=...` and `/teacher/course?token=...` stay exactly as they are. New affordances when a session cookie is present:

- A "claim this lesson" button if `Lesson.owner_id` is NULL and the user is signed in.
- A "your library →" breadcrumb back to `/teacher/home`.
- "Rename" / "Move to folder" / "Delete" controls in the lesson card (only if owner).

## 8 — CLI and magic command changes

### 8.1 cadence-cli

```
cadence-cli login                       # opens browser, captures session via loopback callback
cadence-cli logout                      # clears local session, drops claim
cadence-cli whoami                      # prints current signed-in identity, or "guest"

cadence-cli lessons sync                # uploads ~/.cadence/lessons.yaml tokens to /me/claim
cadence-cli lessons list                # unchanged, but with "claimed/unclaimed" marker
```

Login uses the OAuth device-code flow when a browser isn't available (over SSH, headless server), and the loopback flow otherwise.

The CLI session lives in `~/.cadence/auth.yaml` (mode 0600). Separate file from `lessons.yaml` to keep concerns clean.

### 8.2 Jupyter magics

- `%cadence_create_lesson "name"` — unchanged behaviour. If `~/.cadence/auth.yaml` shows a signed-in session, the created lesson gets `owner_id` automatically. Otherwise guest as before.
- `%cadence_login` (new) — runs the same OAuth dance from a notebook, useful for cloud Jupyter environments.
- `%cadence_logout` (new) — symmetric.
- `%cadence_whoami` (new) — prints "signed in as X" or "guest mode".

Crucially, `%cadence_create_lesson` and `check()` do not require sign-in. Guest mode keeps the README's two-line install honest.

## 9 — Migration plan

1. **Schema migration (Alembic or hand-written SQL)** — additive only. New tables, new columns. No data backfill needed because `owner_id` is nullable and existing rows stay NULL.
2. **Server deploy** — old endpoints keep working, new endpoints come online.
3. **CLI release** — `cadence-edu` v0.2.0 with the new `login`/`sync`/`whoami` subcommands and the new magics.
4. **Existing users** — nothing breaks. They keep using guest mode. Whenever they choose to sign in, they get the claim banner.

Rollback: drop the new tables, drop the new columns. Old code still works because the new columns were never required.

## 10 — Security & privacy

- **OAuth state**: short-lived (10 min) signed cookie containing nonce + PKCE verifier. Verified on callback.
- **Session cookies**: `HttpOnly`, `Secure` (in prod), `SameSite=Lax`. 30-day sliding expiry; rotate on every request (cheap with opaque tokens).
- **CSRF**: state-changing endpoints (`POST/PATCH/DELETE /me/*`) require a `X-Cadence-CSRF` header that matches a per-session value stored in a non-HttpOnly cookie. Double-submit pattern, no library needed.
- **Magic link**: nonce is 32 random bytes, stored only as sha256. Single use, 15 min expiry, 3 sends per email per 15 min, 20 sends per hour per IP.
- **PII**: only email + display name + avatar URL stored. No tracking, no third-party JS. Avatar URL is the provider's CDN URL — not proxied.
- **`teacher_token` shape**: still 32 URL-safe characters from `secrets.token_urlsafe(24)`. Tokens are auto-rotated on claim (§5.4), so old bookmarks stop working the moment a guest signs in — the claim response gives the user new URLs and the YAML cache + magic update automatically.
- **Account deletion**: `DELETE /me` is a soft delete + lessons revert to `owner_id = NULL`. Hard delete (90 days later, after a confirmation email) by a background job — out of scope for v1, mention in roadmap.

## 11 — Resolved decisions

| # | Question | Decision |
|---|---|---|
| 1 | Legacy admin login | **Removed.** `/auth/login`, `username`, `password_hash`, and the `admin/teacher123` seed row all deleted in the same migration. No `legacy_admins` table. |
| 2 | Magic-link email provider | **Resend.** Free 100/day tier is enough for v1; `RESEND_API_KEY` env var, simple HTTPS POST. |
| 3 | Token rotation on claim | **Auto-rotate.** When a guest lesson is claimed, the server mints a fresh `teacher_token`, invalidates the old one, and returns the new dashboard URL. Justifies signing in as a tangible security upgrade. (§5.4 expanded.) |
| 4 | Account deletion semantics | **Revert to anonymous by default.** Lessons stay reachable via their `teacher_token` URLs so students can still re-open their notebooks. The deletion UI states this clearly and offers an explicit "Also delete all my lessons (irreversible)" checkbox. (§6.1 endpoint signature reflects this.) |
| 5 | Avatar storage | **Hotlink** provider URL when avatar_kind = `provider`. **Animal SVG picker** as the default for magic-link signups (no provider photo available). Initials as the final fallback. (§5.5 added.) |
| 6 | OAuth registration | **Deferred for v1.** Ship magic link only. OAuth wiring (Google + GitHub) is the first followup once a deploy domain is picked — design already accommodates it (the `oauth_identities` table + `/auth/<provider>/...` route shape are unchanged). Adding a provider later is purely additive. |

## 12 — Followups

**Near-term (next PR after v1 ships):**
- **Google OAuth + GitHub OAuth.** Highest priority — adds the "Continue with Google/GitHub" buttons to the existing sign-in page. Requires you to register the apps once a deploy domain is chosen. The `oauth_identities` table is already in v1; this PR is mostly the callback handlers + env config.

**Out of scope for v1, no specific timeline:**
- Nested folders / tags
- Multi-owner lessons (shared with TA)
- Importing / exporting a lesson as a portable file
- Audit log of who-changed-what
- A "library" view for guest users (cache `~/.cadence/lessons.yaml` to a sidebar in the dashboard — modest UX win but mixes guest and signed-in surfaces)
- Hard-delete background job (30-day grace period after `archived_at`)
- Magic-link templating beyond a single plaintext + HTML pair
- Per-folder colour theming
- Custom uploaded avatars (provider photo + animal picker covers v1 needs)
