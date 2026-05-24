# Security hardening — 2026-05-24

Three changes following the quick security audit. All backend + frontend
(no PyPI / Jupyter-package impact).

## What landed

### 1. Rate limiting on `/auth/login` and `/check`

Added `slowapi==0.1.9` to `backend/requirements.txt`. Configured a per-IP
limiter on the FastAPI app and applied:

- `/auth/login` → **10 / minute** per remote IP. Defeats credential
  stuffing without blocking a human who typo'd their password a few times.
- `/check` → **120 / minute** per remote IP (~2 attempts/sec). Catches
  runaway student loops; doesn't throttle legitimate rapid iteration.

In-memory storage (per Cloud Run instance). That's fine for brute-force
protection — any attack aggressive enough to matter trips a single
instance's limit anyway, and instances are sticky-enough for the
window we care about.

429 responses use slowapi's default handler.

### 2. `Referrer-Policy: strict-origin-when-cross-origin` on the frontend

Added a single `<meta name="referrer" …>` to `frontend/public/index.html`.

The motivation: dashboard URLs carry `teacher_token` in the query string
(`/teacher/live?token=…`, `/teacher/course?token=…`). Before this change,
if a teacher clicked an external link from one of those pages, the
destination saw the full URL — including the token — in the `Referer`
header. Now cross-origin navigation sends only the origin, no path or
query string.

Same-origin navigation is unaffected (we want the full URL within the
app).

### 3. OIDC verification for `/admin/cleanup` (with shared-secret fallback)

The cleanup endpoint previously accepted only `Authorization: Bearer
<CLEANUP_SECRET>` — a long-lived shared secret. If that secret leaked
(env dump, log spill, Slack scrollback) anyone with the URL could
trigger the retention sweep.

Now: if `CLEANUP_OIDC_SA_EMAIL` is set in the Cloud Run env, the endpoint
prefers a Google-signed OIDC token whose claims match that service
account. Tokens are verified against Google's public keys (via
`google-auth==2.34.0`), audience-checked against `CLEANUP_OIDC_AUDIENCE`,
and the signer email is matched explicitly.

If neither env var is set, behavior is unchanged — shared-secret path
still works. This is a transitional setup so you can roll the OIDC
config out without breaking the existing Cloud Scheduler job.

## Deploy steps

1. **Build + deploy the new backend image.** The new `requirements.txt`
   adds `slowapi` and `google-auth`; both pure-Python with no system
   deps. Standard `gcloud builds submit` + `gcloud run deploy`.
2. **Deploy the new frontend bundle.** Single `<meta>` change in
   `index.html` — picked up by your usual build pipeline.
3. **(Optional but recommended) Migrate the cleanup scheduler to OIDC**:
   - Create a service account, e.g.
     `cleanup-scheduler@<project>.iam.gserviceaccount.com`.
   - Grant it `roles/run.invoker` on the `cadence-backend` Cloud Run
     service.
   - Update the Cloud Scheduler job:
     ```bash
     gcloud scheduler jobs update http cadence-cleanup \
       --location us-central1 \
       --oidc-service-account-email cleanup-scheduler@<project>.iam.gserviceaccount.com \
       --oidc-token-audience https://api.cadence-dash.com
     ```
   - Set the matching env vars on the Cloud Run service:
     ```bash
     gcloud run services update cadence-backend --region us-central1 \
       --update-env-vars CLEANUP_OIDC_SA_EMAIL=cleanup-scheduler@<project>.iam.gserviceaccount.com \
       --update-env-vars CLEANUP_OIDC_AUDIENCE=https://api.cadence-dash.com
     ```
   - Confirm the next scheduled run succeeds (Cloud Scheduler dashboard
     → recent invocations).
   - Once stable for a few days, **remove** `CLEANUP_SECRET` from the
     Cloud Run env to fully eliminate the shared-secret path.

## Verifying

- `/auth/login` rate limit: hit the endpoint 11 times in 60 seconds from
  the same IP; the 11th should return HTTP 429 with a `Retry-After`
  header.
- `/check` rate limit: same idea, 121 calls/min from one IP.
- Referrer-Policy: open DevTools → Network on a `/teacher/live?token=…`
  page → click an external link → inspect the outgoing request's
  `Referer` header → should show only the origin, not the path/query.
- OIDC: temporarily set `CLEANUP_OIDC_SA_EMAIL` without the matching
  scheduler config; the next run should fail with 401, confirming the
  check is wired. Then complete the scheduler migration.

## Not done (deferred from the audit)

- DB connection pool tuning (`pool_size`, `pool_pre_ping`, `pool_recycle`).
  Still on the list; orthogonal to security.
- `/healthz` endpoint so Cloud Run can do a real HTTP health check
  (currently TCP-port-open).
- `--min-instances 1` to remove cold-start latency. Cost-discussed.
- JWT TTL reduction (currently 7d). Defensible default; revisit if we
  see token theft in the wild.
- Image MIME whitelist on `CodeSubmission`. Low risk under current
  rendering path; worth tightening before we ever render uploads in a
  `<iframe>` or `<object>`.
