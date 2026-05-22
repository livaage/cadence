# Cadence — security posture

Snapshot as of **22 May 2026**, immediately pre-launch on `cadence-dash.com`.
This document is the source of truth for what protections are in place, what's
deliberately deferred, and what residual risks you should know about.

---

## What's in place

### Transport encryption
- All client connections (student → API, teacher → dashboard, browser → backend)
  are HTTPS via Cloud Run's auto-provisioned TLS certificates.
- Backend → Cloud SQL connection uses TLS 1.3 via the Cloud SQL Auth Proxy
  (Unix socket inside the container; no plaintext leg).
- `cloud sql instances patch cadence-db --require-ssl` is **enforced** —
  non-TLS connections are rejected at the database level.

### Encryption at rest
- Cloud SQL storage: AES-256, Google-managed keys (default).
- Cloud Run container images + logs: AES-256, Google-managed keys (default).
- Daily Cloud SQL backups encrypted with the same scheme; 7-day retention.

### Network exposure
- Cloud SQL has a **public IP but zero authorized networks** — the IP is
  literally unroutable from outside Google's network. The Auth Proxy bypasses
  the IP entirely (it tunnels via Cloud SQL Admin API).
- Cloud Run services (`cadence-backend`, `cadence-frontend`) are public-facing,
  as they must be — the access control sits at the application layer.

### Application-level access controls
- **Teacher auth = unguessable random token (128 bits) in URL.** No password,
  no email, no account. Token is the credential.
- **Token rotation** — one-click button on dashboard. Old token dies
  immediately; new dashboard URL is issued.
- **CORS allowlist** restricts which origins can talk to the API:
  `cadence-frontend-118735504228.us-central1.run.app`, `cadence-dash.com`,
  `www.cadence-dash.com`. Env-driven via `CADENCE_CORS_ORIGINS`.
- **Cloud Run service account** has `roles/cloudsql.client` only. It cannot
  modify the database schema, billing, or other GCP resources.
- DB credentials live in the Cloud Run env var (encrypted by GCP) and in local
  `.env` (gitignored). Never in source control.

### Privacy controls
- **Pseudonyms by default.** `%cadence_session` warns when the display_name
  matches the canonical "Firstname Lastname" shape; nudges students toward
  pseudonyms. The /about and /privacy pages document the expectation.
- **"Show student roster" defaults OFF.** Teacher must opt in to seeing names
  on the dashboard.
- **No PII beyond display name and submitted answer**. We don't collect
  emails, IPs, device fingerprints, behavioural telemetry, or cell-execution
  data. Student code runs locally and never crosses the network unless the
  teacher opts a checkpoint into `--allow-submissions` AND the student runs
  `%%cadence_submit` explicitly.
- **Right to deletion implemented:**
  - `DELETE /sessions/{sid}` — student-side, wipes one student's data
  - `DELETE /lessons/by-token/{t}` — teacher-side, wipes entire lesson
  - "Delete all data" button on dashboard with two-step confirm
  - Both endpoints cascade through `AttemptEvent`, `CodeSubmission`,
    `SolutionReveal`, `CourseNotebook` references.
- **Privacy policy** at `/privacy` documents collection, retention, security,
  and rights.

### Observability
- Cloud SQL admin activity logs flow to Cloud Logging automatically.
- Cloud Run request/error logs flow to Cloud Logging automatically.
- No data-access logs on Cloud SQL (off by default; expensive).

### Backups
- Cloud SQL daily automated backups, 7-day retention.
- Restore requires manual gcloud / console action; not zero-touch.

---

## Residual risks

Honest list of things that could go wrong, with their mitigations.

| # | Risk | Likelihood | Impact | Mitigation in place |
|---|---|---|---|---|
| 1 | **Teacher token leak** (screenshot, screen-share, accidental commit) — gives anyone full lesson access until rotated | Medium | High (full data access + ability to DELETE the lesson) | Rotate-token button on dashboard; teacher must notice the leak themselves |
| 2 | **Students paste real names anyway** — the warning is a nudge, not a block | Medium | Medium (PII in DB) | Warning in magic; default-off roster; quick deletion |
| 3 | **No rate limit on DELETE endpoints** — if a token leaks, attacker could DELETE the lesson | Low | High (data loss, no audit log of who did it) | Daily backup restorable within 7 days via support |
| 4 | **No audit log for teacher actions** — we don't record which token deleted what when | Low | Medium (forensics impossible after the fact) | None today; structured logging would close this |
| 5 | **Cloud SQL public IP exists** (no authorized networks though) | Very low | Low (IP is effectively unreachable) | Defer `--no-assign-ip` until private IP / VPC is set up |
| 6 | **Single-region deployment** (us-central1) | Low | High (full outage during region incident) | Acceptable for scale; multi-region is post-launch |
| 7 | **No DDoS protection beyond Cloud Run's built-in** | Very low | Medium | Acceptable for current threat model; add Cloudflare if traffic grows |
| 8 | **CORS misconfiguration could expose API** if env var is set wrong | Low | High (cross-site abuse) | One-line env var change reverts; smoke test included in deploy plan |
| 9 | **localStorage library is browser-local** — lost laptop loses bookmarks (but not the underlying data on the server) | Low | Low (re-add tokens from a fresh browser) | Cross-device sync lands with teacher accounts |
| 10 | **Backup restoration is manual** via GCP support — not zero-touch | Low | Medium (slow recovery from accidental data loss) | 7-day retention buys you time; document the runbook before you need it |
| 11 | **Image upload size is enforced client-side only** (1 MB limit in `submit_image`) | Low | Low (DoS via fat uploads) | Add server-side check post-launch |
| 12 | **No 2FA / device pinning for teachers** | Medium | Medium (token = credential) | Token rotation; planned to be replaced by accounts |
| 13 | **Retention is documented but not enforced by code** — sessions don't auto-delete after 12 months | Medium | Low (data piles up; minor compliance gap) | Scheduled cleanup job is a post-launch addition |

---

## Deliberately deferred

Things that came up in the security review but were chosen against, with the
reasoning so future-you doesn't have to re-derive it.

| Deferred item | Reason |
|---|---|
| **Cloud SQL no-public-IP** | Requires enabling private IP via VPC peering (~20 min of network setup). Public IP has zero authorized networks so it's effectively unreachable; the marginal benefit doesn't justify the demo-eve disruption. Post-launch. |
| **Customer-managed encryption keys (CMEK)** | Useful for institutions with explicit key-rotation requirements. Google-managed keys are sufficient until that's a procurement demand. |
| **EU-region deployment** | GDPR is satisfied via Google's Standard Contractual Clauses for US-region storage. EU residency only matters for institutions that contractually require it. |
| **Field-level encryption of display names** | Heavy (key management, query complexity) for minimal gain on top of disk encryption + access controls. Disproportionate to the threat model. |
| **PostgreSQL row-level security** | Single-tenant app today. Useful when (if) Cadence becomes a multi-tenant SaaS. |
| **Cell-execution behavioural analytics** | Out of scope — Cadence intentionally doesn't track this (see /about "What Cadence is NOT"). |
| **Teacher 2FA / OAuth** | Pre-empted by the no-accounts design choice. Will land with the teacher-accounts implementation per `docs/teacher-accounts-design.md`. |
| **Web Application Firewall (Cloudflare in front)** | Premature for the current threat model. Worth adding if/when traffic grows beyond a handful of classes. |

---

## Pre-Saturday checklist (what to verify before demo)

- [ ] `gcloud sql instances describe cadence-db --format="value(settings.ipConfiguration.requireSsl)"` → `True`
- [ ] `gcloud run services describe cadence-backend --region=us-central1 --format="value(spec.template.spec.containers[0].env)"` shows the right CORS allowlist
- [ ] `cadence-dash.com` resolves and serves the dashboard with a green padlock
- [ ] Open `/privacy` from the deployed site, links work
- [ ] Click "Delete all data" on a throwaway lesson; confirm the cascade
- [ ] Run `%cadence_session` with `"Daniel Pearson"` and confirm the warning fires

---

## Where to look in the code

| Concern | File |
|---|---|
| Teacher-token rotation endpoint | [backend/main.py](../backend/main.py) `/lessons/by-token/{teacher_token}/rotate` |
| Delete endpoints (cascading wipes) | [backend/main.py](../backend/main.py) `delete_session`, `delete_lesson` |
| CORS env-var handling | [backend/main.py](../backend/main.py:60-69) |
| Real-name nudge in join flow | [jupyter-integration/cadence/magic.py](../jupyter-integration/cadence/magic.py) `_looks_like_real_name` |
| Show-roster default + UI controls | [frontend/src/components/LiveProgress.tsx](../frontend/src/components/LiveProgress.tsx) `useShowRoster` |
| Delete UI flow | [frontend/src/components/LiveProgress.tsx](../frontend/src/components/LiveProgress.tsx) `handleDeleteLesson` |
| Privacy policy page | [frontend/src/components/Privacy.tsx](../frontend/src/components/Privacy.tsx) |
