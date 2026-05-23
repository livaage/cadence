# Cadence

Live student progress dashboards for Jupyter-based teaching. Teachers drop a
few `check(...)` calls into ordinary `.ipynb` files; students get inline ✅/❌
feedback as they work; teachers watch a real-time dashboard of per-checkpoint
solve rates, timing histograms, common wrong answers, and (for multi-notebook
lessons) which notebook each student is currently on.

[**cadence-dash.com**](https://cadence-dash.com) · [Setup guide](https://cadence-dash.com/guide) · [Privacy](https://cadence-dash.com/privacy) · [Terms](https://cadence-dash.com/terms)

![Notebook dashboard with the section-grouped checkpoints, solution & submission chips, roster, and the new-activity banner](docs/images/dashboard-notebook.png)

> Notebook view of a Higgs-discovery lab — section-grouped checkpoints,
> indigo-themed histograms, hover-revealed names on wrong answers, and the
> "N new attempts since you last looked" banner that wakes a returning teacher
> up to what's happened.

## ✨ Core ideas

- **Drop-in, not bolt-on.** Teachers paste two lines into any existing
  notebook to register checkpoints. No magic structure, no separate "problem
  template" file required.
- **Answer-checker, not code-grader.** Cadence compares student answers
  against teacher-registered expected values (`exact`, `numeric` with
  tolerance, `set`, `regex`, `manual`). Student code stays on the student's
  machine — only the answer crosses the network, unless the teacher
  explicitly opts a checkpoint into code/plot submissions.
- **Two organisational shapes.** A single notebook can be its own lesson, or
  group multiple notebooks under a `Course` to get a top-level "which
  notebook is everyone on" view.
- **Light on student identity.** Students join with a short `join_code`
  (e.g. `soup-river-42`) and a display name they pick — pseudonyms welcome.
  No login, email, or account required to participate.
- **Teacher accounts for ownership and rights.** Teachers can sign in
  (password or GitHub) so courses are tied to a named controller, lessons
  appear automatically in a library, and student data-rights requests can
  be authorized against a real account.
- **Privacy-first.** Per-session data retention is bounded (default 7 days
  for quick lessons, 90 days for courses), scheduled deletion enforces it,
  every export and deletion is logged, and students can self-service their
  GDPR Article 15 / 17 / 20 rights from inside their own notebook.

## ⏱ Try Cadence in 15 minutes

The fastest way to feel the product. You'll act as both the teacher and a
student in two separate Jupyter notebooks, watching the dashboard react in
real time.

**1. Boot the stack** (one-time, ~3 min on first run):

```bash
docker compose up -d --build         # backend + frontend + Postgres + Redis
pip install -e jupyter-integration   # the %cadence_* magics + cadence.check
export CADENCE_API_URL=http://localhost:8000   # point at local backend
```

**2. (Optional) Sign in.** Visit `http://localhost:3000/signup` and create a
teacher account. Lessons and courses you create while signed in show up
automatically in your library. Quick one-off lessons work without an
account too.

**3. Open `demo-teacher-setup.ipynb`** — runs `%cadence_create_lesson` then
bulk-registers six checkpoints (numpy warmups + a Higgs-discovery flow) via
`%%cadence_register_yaml`. The output prints a **join code** (e.g.
`soup-river-42`) and a clickable **dashboard URL**.

**4. Open the dashboard URL.** You'll see an empty lesson — the four big-
number stats all read zero. Leave the tab open.

**5. Open `demo-with-cadence.ipynb`** in a second Jupyter tab (pretend you're
a student). Replace `<JOIN_CODE>` with your code from step 3. Run cells
top-to-bottom and watch the dashboard tab update every 3 seconds.

**6. Browse [http://localhost:3000/teacher/library](http://localhost:3000/teacher/library).**
If you signed in, your lesson appears as a card automatically.

### Features to verify

If everything works, all of these should be reachable from the two notebooks
plus the dashboard. Tick them off as you go:

- [ ] **Inline answer feedback** — `check(...)` returns ✅ when correct, ❌ with a hint when wrong.
- [ ] **Numeric / set / exact / regex / manual comparators** — exercised one per cell.
- [ ] **Sectioned dashboard** — dotted IDs like `setup.mean-value` collapse independently.
- [ ] **Difficulty chips** — Easier / Average / Harder relative to siblings.
- [ ] **Solution reveal** — submit 3 wrong answers; the 💡 reveal hint appears; call `cadence.show_solution("...")`.
- [ ] **Code submission** — `%%cadence_submit checkpoint_id` ships code; the dashboard renders it syntax-highlighted.
- [ ] **Plot submission** — `cadence.submit_image("id", fig)` ships a matplotlib figure.
- [ ] **Manual mark-done** — `cadence.mark_done("id")` for reflection-style checkpoints.
- [ ] **Roster + chronology** — expand any student row to see per-checkpoint progress + attempt log.
- [ ] **Wrong-answer attribution** — hover any common-wrong row to see the students who submitted it.
- [ ] **Privacy toggles** — Show student roster / Show outlier names / Stuck-student alerts.
- [ ] **Just-in-time privacy notice** — appears in the student notebook when joining.
- [ ] **Student data rights** — `%cadence_my_data` / `_export_` / `_delete_` from the student notebook.
- [ ] **Retention chip** — visible on the dashboard header; shortenable via `%cadence_set_retention`.
- [ ] **Display join code** button — fullscreen overlay for projecting in class.
- [ ] **Library auto-populates** — courses + lessons you create while signed in appear without copy/pasting tokens.
- [ ] **Account closure** — `/teacher/account` → "Close my account" works; account deletes after 30 days.

If anything in that list doesn't behave as described, that's a real bug —
please flag it via `contact@cadence-dash.com`.

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │
│   (React + MUI) │◄──►│   (FastAPI)     │
│                 │    │   + PostgreSQL  │
│  /teacher/live  │    │                 │
│  /teacher/course│    │   JWT auth      │
│  /teacher/lib   │    │   GitHub OAuth  │
│  /privacy /terms│    │   GDPR endpoints│
└─────────────────┘    └────────▲────────┘
                                │ HTTPS / JSON
                       ┌────────┴────────┐
                       │ Jupyter kernel  │
                       │  + cadence pkg  │
                       │  %cadence_*     │
                       │  check("id", v) │
                       └─────────────────┘
```

## 🎓 Teacher flow

### Install + sign in

```bash
pip install cadence-edu
```

Then either drop a pre-wired starter notebook with the CLI:

```bash
cadence-cli new teacher --name "Week 3: Fibonacci"   # writes ./teacher-setup.ipynb
cadence-cli new student --name "Week 3: Fibonacci"   # writes ./student.ipynb
```

…or write your own. Either way the first cells look like:

```python
%load_ext cadence
%cadence_login --username <you>     # prompts for password
# or sign in with GitHub at https://cadence-dash.com/login
```

Sign-in is required for **courses** and surfaces your lessons in the
library. Quick one-off lessons work without it.

> While you're writing magics, `%cadence_<Tab>` autocompletes the magic name,
> `%cadence_register?` shows full argparse help on any one command, and
> `%cadence_help` prints a one-page cheatsheet of every Cadence magic.
> Cached lesson/course names tab-complete after `%cadence_lesson` /
> `%cadence_course`.

### Create a lesson

```python
%cadence_create_lesson "Week 3: Fibonacci"
```

Prints a join code, a dashboard URL, a Copy-snippet button, and the
per-session retention (default 7 days). Credentials are cached to
`~/.cadence/lessons.yaml` (mode 0600).

### Register checkpoints

Two paths — pick the one that fits.

**Per-line, for ad-hoc additions:**

```python
%cadence_register hello --comparator exact --expected '"Hello, World!"' --hint "Watch the punctuation."
%cadence_register mean  --comparator numeric --expected '{"value": 49.5, "tolerance": 0.001}'
%cadence_register vowels --comparator set --expected '{"value": ["a","e","i","o","u"]}'
%cadence_register reflect --comparator manual --hint "Briefly describe what the peak shape tells you."
```

**Bulk YAML (recommended for anything beyond a couple of checkpoints):**

```python
%%cadence_register_yaml
- id: setup.mean-value
  comparator: numeric
  expected: {value: 49.5, tolerance: 0.001}
  hint: average of 0..99

- id: discovery.higgs-peak
  comparator: exact
  expected: 125
  reveal_after: 3
  solution_code: |
    bin_edges = np.arange(100, 151)
    counts, _ = np.histogram(m_gg, bins=bin_edges)
    int(bin_edges[np.argmax(counts)])
  allow_submissions: true
```

Or load from a file in version control:

```python
%cadence_register_yaml_file checkpoints/week3.yaml
```

### Verify before class

```python
%cadence_self_test
```

Submits the teacher's expected answer for every auto-checked checkpoint —
catches typos in `--expected` or tolerance errors before students do.

### Hand the notebook to students

The lesson card's **Copy snippet** button gives you a pre-filled student
join snippet:

```python
%load_ext cadence
%cadence_session soup-river-42 "your-name"
```

Paste at the top of the student notebook; students just edit their name.

### Project the join code in class

```python
%cadence_show_join
```

Or click **Display join code** on the dashboard for a fullscreen overlay.

### Courses (semester mode)

```python
%cadence_create_course "Spring 2026 — Intro to Python"   # requires sign-in
%cadence_add_notebook  "Week 1 — Variables"  --order 1
%cadence_add_notebook  "Week 2 — Loops"      --order 2

# Or attach an existing lesson:
%cadence_attach_lesson "Last term's lab" --to "Spring 2026 — Intro to Python"
```

Detach with `%cadence_detach_lesson`, delete with `%cadence_delete_course`
or `%cadence_delete_lesson`, duplicate for next term with
`%cadence_clone_lesson "X" --as "X (Spring 2027)"`.

### Retention

Each student session is wiped a teacher-configured number of days after the
student last touches it. Defaults: 7 days for quick lessons, 90 days for
courses. Shorten with `%cadence_set_retention --days N` (or `--course`).
Per the Terms, retention can be shortened but never extended.

## 🎒 Student flow

```python
%load_ext cadence
%cadence_session soup-river-42 "smol_otter"   # shows a privacy notice
```

Then anywhere you want a pulse-check:

```python
from cadence import check

def fib(n):
    return n if n <= 1 else fib(n-1) + fib(n-2)

check("fib-10", fib(10))    # ✅/❌ inline, attempt recorded server-side
```

**Hints unlock** after a configurable number of attempts; the failure cell
shows a 💡 prompt with the exact command:

```python
import cadence
cadence.show_hint("fib-10")
```

**Solutions unlock** after more attempts (when the teacher configured one):

```python
cadence.show_solution("discovery.higgs-peak")
```

**Timed cells** record elapsed milliseconds alongside the attempt:

```python
%%cadence_time fib-10
def fib(n):
    return n if n <= 1 else fib(n-1) + fib(n-2)
fib(10)
```

**Code submissions** for opt-in checkpoints:

```python
%%cadence_submit discovery.higgs-peak
bin_edges = np.arange(100, 151)
peak = int(bin_edges[np.argmax(np.histogram(m_gg, bins=bin_edges)[0])])
check("discovery.higgs-peak", peak)
```

**Plot submissions** for figure-driven checkpoints:

```python
from cadence import submit_image
fig, ax = plt.subplots(); ax.hist(m_gg, bins=50)
submit_image("discovery.peak-plot", fig)
```

**Manual checkpoints** — for reflections or open-ended work where there's
no single right answer:

```python
cadence.mark_done("discovery.reflect")
```

## 🔒 Student data rights

Three Jupyter magics map directly to GDPR Article 15 / 17 / 20:

```python
%cadence_my_data           # see everything Cadence has stored about you
%cadence_export_my_data    # download as machine-readable JSON
%cadence_delete_my_data --yes   # permanently wipe this session's data
```

The just-in-time notice on `%cadence_session` tells students at the moment
of collection what's collected, who sees it, how long it's kept, and how to
exercise these rights — without burying it in a separate notice they have
to find.

For requests outside an active session, the teacher (the controller)
authorizes via the dashboard, or students can escalate to
`privacy@cadence-dash.com`.

## 📚 Documentation

| Doc | What it covers |
|---|---|
| [docs/smoke-test.md](docs/smoke-test.md) | End-to-end manual test covering every feature; run before deploying |
| [docs/deploy-plan.md](docs/deploy-plan.md) | GCP deploy runbook: Cloud Run + Cloud SQL + Firebase Hosting |
| [docs/privacy-notice.md](docs/privacy-notice.md) | The full privacy notice (mirror of what's at /privacy on the live site) |
| [docs/ropa.md](docs/ropa.md) | Records of Processing Activities (Article 30) |
| [docs/breach-response.md](docs/breach-response.md) | Internal breach response playbook |
| [docs/dpa-template.md](docs/dpa-template.md) | Data Processing Agreement template for institutions |
| [docs/teacher-accounts-design.md](docs/teacher-accounts-design.md) | Design doc for the teacher-account flow |
| [docs/security-posture.md](docs/security-posture.md) | Security overview |

## 🚀 Production deployment

See [docs/deploy-plan.md](docs/deploy-plan.md) for the full GCP runbook:
Cloud Run for the backend, Cloud SQL Postgres, Firebase Hosting for the
frontend, Cloud Scheduler for daily retention cleanup. ~75 minutes
end-to-end the first time.

Key env vars on the backend:

```
DATABASE_URL=postgresql+psycopg2://...
JWT_SECRET_KEY=<openssl rand -base64 64>
CLEANUP_SECRET=<openssl rand -base64 32>
CADENCE_WEB_URL=https://cadence-dash.com
CADENCE_CORS_ORIGINS=https://cadence-dash.com,https://<project>.web.app
GITHUB_OAUTH_CLIENT_ID=<from GitHub OAuth app>
GITHUB_OAUTH_CLIENT_SECRET=<same>
GITHUB_OAUTH_REDIRECT_URI=<BACKEND_URL>/auth/github/callback
```

Migrations live in `backend/migrations/*.sql`, applied in order via
cloud_sql_proxy as part of step 6a in the deploy plan.

## 🛠️ Development

```bash
# Backend + frontend + Postgres + Redis
docker compose up -d --build

# Jupyter integration in editable mode
pip install -e jupyter-integration

# Point Jupyter at the local backend
export CADENCE_API_URL=http://localhost:8000

# Run the smoke test (see docs/smoke-test.md)
```

Project layout:

```
cadence/
├── backend/                # FastAPI + SQLAlchemy
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── auth.py
│   └── migrations/         # SQL migrations (alembic-free for now)
├── frontend/               # React + MUI
│   ├── src/components/
│   ├── src/services/api.ts
│   └── src/contexts/AuthContext.tsx
├── jupyter-integration/    # The pip-installable package
│   ├── cadence/
│   ├── setup.py
│   └── LICENSE
├── docs/                   # Compliance + deployment docs
├── docker-compose.yml
├── README.md
└── student-example.ipynb / teacher-notebook-example.ipynb
```

## 🤝 Contributing

Issues and PRs welcome. For substantial changes, open a discussion first so
we can talk through the design.

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

## ✉️ Contact

- **General**: contact@cadence-dash.com
- **Data rights / privacy**: privacy@cadence-dash.com
- **Web**: [cadence-dash.com](https://cadence-dash.com)
