# Cadence — deploy plan (GCP)

Target: Cloud Run (backend) + Cloud SQL Postgres + Firebase Hosting (frontend).
Estimated wall-clock time: **60–90 minutes** first time, mostly waiting for the SQL
instance to provision. Subsequent deploys are `git push`-grade fast.

Conventions used below:
- `<PROJECT_ID>` — pick a globally-unique GCP project ID (e.g. `cadence-prod-2026`).
- `<REGION>` — pick one close to your students. `us-central1` is cheapest and the
  default in the plan.
- `<DB_PASSWORD>` — generate one (`openssl rand -base64 24` is fine).
- `<DOMAIN>` — optional custom domain. Skip the domain section if you're okay
  with the auto-generated `.run.app` and `.web.app` URLs.

---

## 0. Pre-flight: fix the Dockerfile

Your current `backend/Dockerfile` runs uvicorn with `--reload` and hardcodes port
8000. Cloud Run expects the app to listen on `$PORT` (default 8080) and you don't
want `--reload` in prod. Edit the last line to:

```dockerfile
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
```

(Keep everything else the same — your local Docker Compose still works because
it sets `PORT` to 8000 implicitly via the port mapping. If you want to be extra
safe, add `ENV PORT=8000` before the CMD for local parity.)

Commit this before you build.

---

## 1. GCP account + project (one-time, ~10 min, browser)

1. Open https://console.cloud.google.com and sign in with the Google account
   you want to bill against.
2. **Create a new project**: top bar → "Select a project" → "NEW PROJECT".
   Name it `Cadence` (or whatever); the project ID will auto-generate or you
   can override it. Note the project ID — that's `<PROJECT_ID>` below.
3. **Enable billing**: Billing → Link a billing account → add a credit card.
   You'll get the $300 / 90-day free trial automatically.
4. **Enable the APIs** you'll need. Either click each link below, or run the
   `gcloud services enable` command in step 2 once the CLI is installed.
   - Cloud Run API
   - Cloud SQL Admin API
   - Artifact Registry API
   - Cloud Build API

---

## 2. Install the CLI (one-time, ~5 min, terminal)

```bash
brew install --cask google-cloud-sdk
gcloud init                           # log in, pick the project
gcloud auth configure-docker us-central1-docker.pkg.dev
gcloud config set project <PROJECT_ID>
gcloud config set run/region us-central1

# Enable the APIs in one shot
gcloud services enable run.googleapis.com sqladmin.googleapis.com \
  artifactregistry.googleapis.com cloudbuild.googleapis.com
```

---

## 3. Create the Postgres database (~5–10 min wait)

Cloud SQL takes a while to provision — start this **first**, then move on
to step 4 in parallel.

```bash
# Smallest instance — ~$10-15/month compute. Bump up later if you need.
gcloud sql instances create cadence-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --storage-size=10GB \
  --storage-type=HDD \
  --root-password=<DB_PASSWORD>

# Create the database and a user
gcloud sql databases create cadence --instance=cadence-db
gcloud sql users create cadence_user \
  --instance=cadence-db \
  --password=<DB_PASSWORD>
```

When this finishes, grab the **connection name** — you'll need it for Cloud Run:

```bash
gcloud sql instances describe cadence-db --format="value(connectionName)"
# Example output: cadence-prod-2026:us-central1:cadence-db
```

Save that as `<SQL_CONNECTION_NAME>`.

> **Note:** `db-f1-micro` is deprecated for new instances in some regions. If the
> command fails with "tier not found", use `--tier=db-perf-optimized-N-2` or the
> smallest currently-offered Enterprise tier (check `gcloud sql tiers list`).

---

## 4. Set up the container registry (~1 min)

```bash
gcloud artifacts repositories create cadence \
  --repository-format=docker \
  --location=us-central1 \
  --description="Cadence container images"
```

Your image URL will be `us-central1-docker.pkg.dev/<PROJECT_ID>/cadence/backend`.

---

## 5. Build and push the backend container (~3–5 min first time)

From the project root:

```bash
# Cloud Build does the docker build remotely so you don't need a fast machine
gcloud builds submit ./backend \
  --tag us-central1-docker.pkg.dev/<PROJECT_ID>/cadence/backend:v1
```

This uploads `./backend/` to Cloud Build, builds the image using your
`Dockerfile`, and pushes it to Artifact Registry. ~5 min for the first build,
~2 min thereafter.

---

## 6. Deploy backend to Cloud Run (~2 min)

First, generate two secrets you'll re-use across deploys:

```bash
JWT_SECRET=$(openssl rand -base64 64 | tr -d '\n')
CLEANUP_SECRET=$(openssl rand -base64 32 | tr -d '\n')

echo "JWT_SECRET=$JWT_SECRET"             # save this — re-deploying with a different
                                           # secret invalidates every issued JWT and
                                           # signs users out
echo "CLEANUP_SECRET=$CLEANUP_SECRET"     # save this too — Cloud Scheduler needs it
                                           # in step 6c
```

Then deploy:

```bash
gcloud run deploy cadence-backend \
  --image us-central1-docker.pkg.dev/<PROJECT_ID>/cadence/backend:v1 \
  --region us-central1 \
  --allow-unauthenticated \
  --add-cloudsql-instances <SQL_CONNECTION_NAME> \
  --set-env-vars "DATABASE_URL=postgresql+psycopg2://cadence_user:<DB_PASSWORD>@/cadence?host=/cloudsql/<SQL_CONNECTION_NAME>" \
  --set-env-vars "CADENCE_CORS_ORIGINS=https://cadence-dash.com,https://<PROJECT_ID>.web.app,https://<PROJECT_ID>.firebaseapp.com" \
  --set-env-vars "CADENCE_WEB_URL=https://cadence-dash.com" \
  --set-env-vars "JWT_SECRET_KEY=$JWT_SECRET" \
  --set-env-vars "CLEANUP_SECRET=$CLEANUP_SECRET" \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 5 \
  --port 8080
```

GitHub OAuth env vars come in step 6b once you've created the OAuth app.

What this does:
- `--allow-unauthenticated`: public API (your security model is teacher-token-based, not GCP IAM).
- `--add-cloudsql-instances`: mounts the Cloud SQL socket so the backend can reach the DB without exposing it publicly.
- `--min-instances 0`: scales to zero when idle. First request after idle has a ~1s cold start. Set to `1` ($5-10/month extra) if you can't tolerate that for the demo.
- `--memory 512Mi`: ample for FastAPI; bump to 1Gi if you start uploading larger plot images.

Output ends with **Service URL: https://cadence-backend-xxxxx-uc.a.run.app** — that's `<BACKEND_URL>`.

Smoke-test:
```bash
curl <BACKEND_URL>/         # expect 200
curl <BACKEND_URL>/lessons  # expect [] or list
```

---

## 6a. Apply all migrations to Cloud SQL (~3 min)

Three migrations under `backend/migrations/`, all idempotent and additive:

| File | Purpose |
|---|---|
| `001_add_teacher_auth.sql` | Teacher OAuth columns + `teacher_id` on courses |
| `002_add_retention.sql` | Per-lesson/course `session_retention_days` |
| `003_add_access_log.sql` | Audit log table for deletions and exports |

Apply via the Cloud SQL Auth Proxy:

```bash
# Terminal 1: start the proxy
cloud_sql_proxy -instances=<SQL_CONNECTION_NAME>=tcp:5433 &

# Terminal 2: apply each migration in order
for m in backend/migrations/*.sql; do
  echo "-> $m"
  PGPASSWORD=<DB_PASSWORD> psql \
    -h localhost -p 5433 -U cadence_user -d cadence \
    -f "$m" || break
done

# Stop the proxy
kill %1
```

If you skip this step, signup / login / GitHub OAuth / course creation /
retention cleanup will all fail with "column does not exist" errors on
first use.

---

## 6b. GitHub OAuth app + env vars (~10 min)

Only needed if you want "Continue with GitHub" to work. The username/password
flow works without this — you can defer step 6b until you want OAuth.

1. Go to **github.com/settings/developers → OAuth Apps → New OAuth App**.
2. Application name: `Cadence`.
3. Homepage URL: `https://cadence-dash.com` (or your `<DOMAIN>`).
4. Authorization callback URL: `<BACKEND_URL>/auth/github/callback`. Use the
   Cloud Run URL during testing; switch to `https://api.<DOMAIN>/auth/github/callback`
   once you have a custom backend subdomain.
5. Click **Register application**. Copy the Client ID.
6. Click **Generate a new client secret**. Copy the secret immediately —
   it's only shown once.
7. Push the values to Cloud Run:

```bash
gcloud run services update cadence-backend \
  --region us-central1 \
  --update-env-vars "GITHUB_OAUTH_CLIENT_ID=<id>" \
  --update-env-vars "GITHUB_OAUTH_CLIENT_SECRET=<secret>" \
  --update-env-vars "GITHUB_OAUTH_REDIRECT_URI=<BACKEND_URL>/auth/github/callback"
```

Test by opening `<BACKEND_URL>/auth/github/authorize` — it should redirect
to GitHub. After authorizing, you should land on the frontend at
`/teacher/auth-callback#token=...` and the nav should flip to "Sign out".

---

## 6c. Schedule the daily cleanup job (~3 min)

The backend's retention enforcement runs in two places: once on startup,
and via `POST /admin/cleanup`. Cloud Run scales to zero when idle, so the
startup sweep alone is unreliable. Cloud Scheduler hitting `/admin/cleanup`
daily fixes that.

```bash
gcloud services enable cloudscheduler.googleapis.com

gcloud scheduler jobs create http cadence-cleanup \
  --schedule="0 3 * * *" \
  --time-zone="UTC" \
  --uri="<BACKEND_URL>/admin/cleanup" \
  --http-method=POST \
  --headers="Authorization=Bearer $CLEANUP_SECRET" \
  --location=us-central1 \
  --description="Daily retention sweep: wipe expired sessions and old access logs"
```

What this does:
- Runs at 03:00 UTC every day (off-peak for most launch markets).
- Calls `POST /admin/cleanup` with the shared secret.
- The handler wipes sessions past their per-lesson/course retention AND
  access log entries older than 12 months.
- Returns `{"sessions": N, "access_log_entries": M}` — visible in Cloud
  Scheduler's execution history if you ever want to confirm it's running.

To verify it works without waiting:

```bash
gcloud scheduler jobs run cadence-cleanup --location=us-central1
gcloud scheduler jobs describe cadence-cleanup --location=us-central1 \
  --format="value(lastAttemptTime,status.message)"
```

If you ever rotate `CLEANUP_SECRET`, also update the scheduler job:

```bash
gcloud scheduler jobs update http cadence-cleanup \
  --location=us-central1 \
  --update-headers="Authorization=Bearer $NEW_CLEANUP_SECRET"
```

---

## 7. Build the frontend with the prod API URL (~2 min)

```bash
cd frontend
REACT_APP_API_URL=<BACKEND_URL> npm run build
```

This produces `frontend/build/` — static HTML/JS/CSS bundles that talk to your
deployed backend.

---

## 8. Deploy frontend to Firebase Hosting (~5 min one-time + ~30s per deploy)

```bash
npm install -g firebase-tools
firebase login
firebase init hosting
#   - Use an existing project → pick <PROJECT_ID>
#   - Public directory: build
#   - Single-page app: Yes (rewrites all routes to /index.html for React Router)
#   - GitHub auto-deploys: No (we'll do it manually for now)
#   - Overwrite build/index.html: No

firebase deploy --only hosting
```

Output ends with **Hosting URL: https://<PROJECT_ID>.web.app**.

Open it. You should see the Welcome page, and clicking "About" / "Guide" / "Library" should all work (because React Router handles routing client-side, and the Firebase SPA rewrite ensures direct hits to `/guide` etc. serve `index.html`).

---

## 9. Verify CORS is happy (~1 min)

The backend deploy in step 6 already set `CADENCE_CORS_ORIGINS` to your Firebase
URL. If you change the frontend's deployed URL (e.g. add a custom domain),
update the env var:

```bash
gcloud run services update cadence-backend \
  --region us-central1 \
  --update-env-vars "CADENCE_CORS_ORIGINS=https://<PROJECT_ID>.web.app,https://<DOMAIN>"
```

---

## 10. Full smoke test

From the deployed frontend:
1. Open `https://<PROJECT_ID>.web.app/guide` — guide should render.
2. Open `https://<PROJECT_ID>.web.app/teacher/library` — library page should render with the demo-seed button.
3. Click the seed button — you should land on a populated dashboard.
4. From your local machine, install the jupyter integration pointed at prod:
   ```bash
   pip install -e ./jupyter-integration
   export CADENCE_API_URL=<BACKEND_URL>
   jupyter notebook demo-with-cadence.ipynb
   ```
   Run the cells; the dashboard should update in real time.

---

## 11. (Optional) Custom domain — ~30 min, mostly waiting for DNS

In the Firebase console: Hosting → Add custom domain → enter `<DOMAIN>` → follow
the DNS instructions (typically two A records). Firebase handles TLS for you.

After DNS propagates (often <1h), update CORS as in step 9.

---

## Subsequent deploys

Backend changes:
```bash
gcloud builds submit ./backend \
  --tag us-central1-docker.pkg.dev/<PROJECT_ID>/cadence/backend:v2
gcloud run deploy cadence-backend \
  --image us-central1-docker.pkg.dev/<PROJECT_ID>/cadence/backend:v2 \
  --region us-central1
# If you added a new migration, apply it via cloud_sql_proxy as in step 6a
# *before* the deploy that needs the new schema.
```

Frontend changes:
```bash
cd frontend && REACT_APP_API_URL=<BACKEND_URL> npm run build
firebase deploy --only hosting
```

Rollback (backend):
```bash
gcloud run services update-traffic cadence-backend \
  --to-revisions cadence-backend-00001-abc=100  # use a previous revision ID
```

(Firebase keeps deploy history too: console → Hosting → release history → "Rollback".)

---

## What this plan deliberately doesn't do

- **No CI/CD.** You're deploying from your laptop. Wire Cloud Build triggers
  off `git push` to main later if you want it.
- **No backups.** Cloud SQL takes automated daily backups by default; that's
  fine for now. Set up point-in-time recovery before you have real teachers
  relying on it.
- **No monitoring beyond Cloud Run's built-in dashboards.** Sentry / Logflare
  can come later.
- **No staging environment.** For the demo, deploy straight to prod and
  iterate. Add a `cadence-backend-staging` Cloud Run service later if you want
  one.

---

## Cost reality check

Once the $300 / 90-day credit runs out (~mid-August 2026):

- Cloud Run (backend): **~$0** under expected load (well within free tier).
- Cloud SQL (smallest tier): **~$15-25/month** — the dominant cost.
- Firebase Hosting: **$0** (free tier covers a class easily).
- Egress: **~$0** for this workload.

Budget **~$25/month** to keep it live indefinitely. Set a billing alert at
$50/month in the GCP console so a runaway loop can't surprise you.
