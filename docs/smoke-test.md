# Cadence smoke test

A complete walkthrough that exercises every user-facing feature. Run this
before deploying to production to catch regressions, especially around the
new auth, retention, access logging, and rights-request flows.

**Estimated time:** 30 minutes for a thorough pass.

The smoke test has three parts:
- **Backend health** (curl / browser, ~5 min)
- **Teacher flow** (web + notebook, ~10 min) — see `teacher-notebook-example.ipynb`
- **Student flow** (notebook, ~10 min) — see `student-example.ipynb`
- **Cleanup verification** (~5 min)

Keep an eye on the backend logs in another terminal — any unhandled
exception is a smoke-test failure.

---

## Pre-flight

```bash
cd /path/to/cadence
docker-compose down                       # start fresh
docker-compose up --build                 # in foreground so you see logs
```

Wait until you see `Uvicorn running on http://0.0.0.0:8000` and
`Compiled successfully!` from the frontend.

In a separate terminal:

```bash
pip install -e ./jupyter-integration       # if you haven't already
```

---

## 1. Backend health

```bash
curl -s http://localhost:8000/ | jq .
curl -s http://localhost:8000/auth/providers | jq .
```

Expect:
- Root returns `{"status": "ok", ...}` or similar.
- `/auth/providers` returns `{"github": false, "google": false}` (no OAuth
  configured locally — that's correct).

---

## 2. Web — public pages

Open in browser:

- [http://localhost:3000/](http://localhost:3000/) — Welcome renders.
- [http://localhost:3000/privacy](http://localhost:3000/privacy) — Privacy page renders, mentions
  controller/processor, retention details, GDPR rights, subprocessors.
- [http://localhost:3000/terms](http://localhost:3000/terms) — Terms page renders, links to Privacy.
- [http://localhost:3000/login](http://localhost:3000/login) — Login page renders.
  - GitHub button should be **hidden** (no OAuth configured locally).
  - "or" divider should be hidden too.
  - Only the username/password form should show.
- [http://localhost:3000/signup](http://localhost:3000/signup) — Signup page renders.
  - Same: no GitHub button.
  - Attestation text visible, links to Terms and Privacy.

---

## 3. Web — signup flow

1. Go to [/signup](http://localhost:3000/signup).
2. Username: `smoke_teacher`. Email: `smoke@example.com`. Password: `smoketest12345`.
3. Click **Create account**.
4. Verify: lands on `/teacher/library`. Nav shows `smoke_teacher` and "Sign out".

Expected backend log: `POST /auth/signup 201`.

---

## 4. Web — account page

1. Click `smoke_teacher` in the nav.
2. Verify: account page shows username, email, member-since date.
3. Verify: "Close my account" card is visible (do not click yet).
4. Sign out (top right).
5. Verify: nav goes back to "Sign in".
6. Sign back in at [/login](http://localhost:3000/login) with the credentials from step 3.

---

## 5. Teacher notebook flow

Open `teacher-notebook-example.ipynb` in Jupyter. Follow the steps inline.
This exercises:

- [ ] `%load_ext cadence`
- [ ] `%cadence_login` with the `smoke_teacher` account
- [ ] `%cadence_whoami`
- [ ] `%cadence_create_lesson` (token-only; attestation skipped because logged in)
- [ ] `%cadence_register` — exact / numeric / set / manual comparators
- [ ] `%cadence_register_yaml` bulk registration
- [ ] `%cadence_self_test` (verify expected answers)
- [ ] `%cadence_create_course` (requires login — should succeed)
- [ ] `%cadence_create_course --retention-days 300` (soft warning fires)
- [ ] `%cadence_create_course --retention-days 300 --yes-long-retention` (succeeds)
- [ ] `%cadence_add_notebook` to a course
- [ ] `%cadence_rotate_token` (rotate teacher token)

**Save the join code printed by `%cadence_create_lesson`** — you'll need
it for the student flow.

---

## 6. Student notebook flow

Open `student-example.ipynb` in Jupyter. Paste the join code from step 5
into the first cell. Follow the steps inline:

- [ ] `%cadence_session <code> "smoke_student"` — **the GDPR notice block
      renders**. Verify it mentions data classes, retention, rights, and
      `privacy@cadence-dash.com`.
- [ ] Several `check()` calls (correct + wrong attempts).
- [ ] `cadence.show_hint("...")` after a wrong attempt.
- [ ] `cadence.show_solution("...")` after enough attempts.
- [ ] `%%cadence_time` for a timed check.
- [ ] `%%cadence_submit` for a code submission (on `--allow-submissions` checkpoint).
- [ ] `%cadence_my_data` — table of attempts, submissions, reveals.
- [ ] `%cadence_export_my_data` — JSON file written to disk.
- [ ] `%cadence_delete_my_data` (no `--yes`) — should show the confirmation prompt.
- [ ] `%cadence_delete_my_data --yes` — wipes the session, kernel state cleared.

---

## 7. Web — verify dashboard during the student flow

While the student notebook is running, open the dashboard URL from the
teacher's `%cadence_create_lesson` output. You should see:

- [ ] The student's name in the roster.
- [ ] Real-time attempts arriving as the student runs cells.
- [ ] Submissions visible for `--allow-submissions` checkpoints.
- [ ] After `%cadence_delete_my_data --yes`: the student disappears from the roster.

---

## 8. Backend — admin cleanup

Trigger the cleanup endpoint manually:

```bash
curl -X POST http://localhost:8000/admin/cleanup \
  -H "Authorization: Bearer dev-cleanup-secret" | jq .
```

Expect: `{"sessions": 0, "access_log_entries": 0, "closed_teachers": 0}`
(none expired yet on a fresh DB — that's correct).

Verify the access log:

```bash
docker-compose exec postgres psql -U competition_user -d competition_db \
  -c "SELECT occurred_at, action, actor_kind, target_kind FROM access_log ORDER BY occurred_at DESC LIMIT 10;"
```

Expect: entries for `delete_session`, `export_my_data`, and any other
significant actions you performed.

---

## 9. Web — close account

1. Sign in as `smoke_teacher` at [/login](http://localhost:3000/login).
2. Click username → `/teacher/account`.
3. Click **Close account**, confirm the dialog.
4. Verify: redirected to home, nav back to "Sign in".
5. Try to log back in with the same credentials. Should fail with
   "Incorrect username or password" (account is `is_active=False`).

Verify the backend state:

```bash
docker-compose exec postgres psql -U competition_user -d competition_db \
  -c "SELECT username, is_active, closed_at FROM teachers WHERE username='smoke_teacher';"
```

Expect: `is_active=f`, `closed_at` set to a recent timestamp.

---

## 10. Reset (optional)

If you want a clean DB for the next smoke test:

```bash
docker-compose down -v       # -v wipes the volume
docker-compose up --build
```

---

## What to do if something fails

- **Frontend won't compile**: check the type errors with `cd frontend && npx tsc --noEmit`.
- **Backend won't start**: check the docker-compose logs. Most likely a missing env var or a DB schema mismatch. The inline migrations in `main.py` should keep things in sync — if they're not, manually apply the SQL in `backend/migrations/` to the local DB.
- **Magic command fails with "not configured"**: usually means the backend isn't reachable. Check `CADENCE_API_URL` if you've overridden it (default `http://localhost:8000` works for docker-compose).
- **JWT expired during the test**: re-run `%cadence_login`. JWTs are 7 days in dev.

If anything genuinely breaks, file an internal bug before deploying.

---

## Done

If steps 1–9 all check out: you're safe to deploy. Follow
[`docs/deploy-plan.md`](deploy-plan.md) from step 1.
