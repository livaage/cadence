# Cadence Roadmap

Living document. Updated whenever we audit "what's missing." Decisions deliberately recorded so we don't second-guess them later.

## ✅ Already shipped

- Live aggregate teacher dashboard (per-checkpoint stats, common-wrong clustering, attempts histograms, timing histograms)
- Two-line student install (`%load_ext cadence`, `check()`)
- Course ↔ notebook hierarchy with per-cohort scope toggle
- Sections via dot-prefixed checkpoint IDs
- Relative difficulty chip (Easier / Average / Harder, peer-relative)
- Solution reveal after N attempts, with `--solution-value` and `--solution-code`
- Manual / self-attest checkpoints (`--comparator manual` + `cadence.mark_done(…)`)
- Code submissions with syntax-highlighted dashboard viewer (`--allow-submissions` + `%%cadence_submit`)
- Student roster panel with "currently on" indicator
- Privacy toggles (Show student roster + Show outlier names)
- Per-checkpoint name attribution via hover (timing tooltips, wrong-answer rows)
- Adaptive polling (heartbeat-gated, pause-when-hidden, auto-slow/idle/pause)
- "N new attempts since you last looked" banner with localStorage timestamp
- Rate limiting on /check (100 attempts/min per session+checkpoint)
- Welcome page + token-paste entry
- Theme overhaul (warm off-white, indigo, Inter + JetBrains Mono)

## 🟡 Pre-demo (Saturday 2026-05-23)

| # | Item | Why | Effort |
|---|---|---|---|
| 1 | Deploy backend + frontend with HTTPS | The demo needs a public URL | half-day, deferred — done separately |
| 2 | Env-driven CORS origin allowlist | Hardcoded `localhost:3000` will break on deploy | 5 min |
| 3 | README screenshots | Visual proof on the repo's landing page | 15 min |
| 4 | `demo-with-cadence.ipynb` (student-side counterpart to `demo-before-cadence.ipynb`) | Makes the "two-line install" pitch visible side-by-side | 20 min |

## 🟠 Post-demo (week 1 after)

| # | Item | Why | Effort |
|---|---|---|---|
| 5 | Teacher accounts (auth + library + folders) | Designed in `docs/teacher-accounts-design.md`. Until then every reload requires a token from memory. | 2–4 days |
| 6 | Token rotation button in dashboard | Already exists in CLI + magic. UI surface for the screen-share leak scenario. | 30 min |
| 7 | Per-student per-attempt chronology drill-in | Currently the roster row shows per-checkpoint status but not the sequence ("Alice: 124 → 126 → 125 over 4 min"). High pedagogical value. | 60–90 min |
| 8 | Lesson rename / archive from UI | Currently only via `cadence-cli`. Friendly UI grows once accounts exist (so the archived list has somewhere to live). | 30 min after accounts |
| 9 | OAuth providers (Google + GitHub) | Already designed; magic-link-only is the v1 auth. Adds 2 more sign-in options. | 1 day |

## 🟢 Nice-to-have

| # | Item | Notes |
|---|---|---|
| 10 | ~~Desktop notifications~~ | ✅ Shipped: stuck-student alerts (3+ wrong attempts in 5 min, no correct). Toggle gates browser-permission request. Dedup per (session, checkpoint). |
| 11 | Gradebook CSV export | `(student, checkpoint, solved, attempts, fastest_ms)`. Low-effort high-perceived-value, but **conflicts with the "we're not nbgrader" positioning** — consider partnering instead. |
| 12 | ~~Bulk checkpoint import via YAML~~ | ✅ Shipped: `%%cadence_register_yaml` cell magic. |
| 13 | Custom uploaded avatars | Animal picker + provider photo cover v1. |
| 14 | Nested folders / tags | Single level of folders is enough until somebody complains. |
| 15 | Multi-owner / TA-shared lessons | Each lesson has at most one owner in v1. |
| 16 | ~~Image / plot submission comparators~~ | ✅ Shipped: `cadence.submit_image()` attaches a matplotlib figure (or PIL image / PNG bytes) to a submission. Renders inline in the dashboard panel. 1 MB cap. |
| 17 | Capture Python exceptions, not just wrong answers | Conflicts with the explicit-checkpoint model. Would be telemetry-flavoured (see deferred section). |
| 18 | `cadence-cli doctor` self-diagnosis | Pings backend, validates env vars, checks YAML. Saves a class when something breaks mid-deploy. Probably medium impact, small effort. |
| 19 | File submissions (CSV / .ipynb / arbitrary attachment) | Same plumbing as image submissions, different MIME. Reasonable next step. |

## 🔴 Explicitly out of scope (decisions, not gaps)

These were considered and *not* chosen — recording the reasoning so we don't re-litigate.

- **Behavioural telemetry** (cell execution counts, time-on-task, idle detection) — there's already an excellent FOSS project for this (EPFL's [Jupyter Analytics](https://github.com/chili-epfl/jupyter-analytics)). Different signal, different niche. Integrate, don't duplicate.
- **Post-hoc grading / autograder infrastructure** — nbgrader / Otter / CodeGrade / Gradescope dominate this category with multi-year incumbents and tighter LMS integration. Cadence's wedge is *live, during-class awareness*. Hand the gradebook export to whichever grader the school uses.
- **Account types ("Teacher" / "Student" / "TA" roles)** — the no-login student flow is a feature, not a stop-gap. Adding student accounts would dilute the two-line-install pitch.
- **Public/SaaS hosting of Cadence itself** — premature. Self-hosted Docker compose is the right entry point until adoption proves otherwise.
- **Email digests of activity** — adds operational complexity (SMTP, unsubscribe, GDPR) for thin value. Banner-on-return-visit serves the same purpose with no infra.
- **Hard-delete background job** — soft archive is enough for years. Build the cleaner when there's actual data to retire.

## Process notes

- Audits like this should happen **before major scope-additions**, not after a feature is half-built.
- "We could add X" should always be cross-referenced against the wedge: *does this help us be the best live-during-class tool, or does it push us into a category we don't want to win?*
- Items only move from 🟢 to 🟠 when a real user (not us) asks for them.
