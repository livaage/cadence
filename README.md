# Cadence

Live student progress dashboards for Jupyter-based teaching. Teachers drop a few `check(...)` calls into ordinary `.ipynb` files; students get inline ✅/❌ feedback as they work; teachers watch a real-time dashboard of per-checkpoint solve rates, timing histograms, common wrong answers, and (for multi-notebook lessons) which notebook each student is currently on.

![Notebook dashboard with the section-grouped checkpoints, solution & submission chips, roster, and the new-activity banner](docs/images/dashboard-notebook.png)

> Notebook view of a Higgs-discovery lab — section-grouped checkpoints, indigo-themed histograms, hover-revealed names on wrong answers, and the "N new attempts since you last looked" banner that wakes a returning teacher up to what's happened.

## ⏱ Try Cadence in 15 minutes

The fastest way to feel the product. You'll act as both the teacher and a student in two separate Jupyter notebooks, watching the dashboard react in real time.

**1. Boot the stack** (one-time, ~3 min on first run):
```bash
docker compose up -d --build           # backend + frontend + Postgres + Redis
pip install -e jupyter-integration     # the %cadence_* magics + cadence.check / mark_done / submit_image
```

**2. Open `demo-teacher-setup.ipynb`** — runs `%cadence_create_lesson` then bulk-registers six checkpoints (numpy warmups + a Higgs-discovery flow) via `%%cadence_register_yaml`. The output prints:
- a **join code** (something like `soup-river-42`) that students need
- a **dashboard URL** with your `teacher_token` baked in — bookmark it

**3. Open the dashboard URL in a browser tab.** You'll see an empty lesson — the four big-number stats all read zero. Leave the tab open.

**4. Open `demo-with-cadence.ipynb`** (a second Jupyter tab — pretend you're a student). Replace `<JOIN_CODE>` on line ~7 with your join code from step 2. Replace `"Your name here"` with anything. Run cells top-to-bottom and watch the dashboard tab update every 3 seconds.

**5. Browse `http://localhost:3000/teacher/library`.** Empty state. Click **+ Add course / lesson**, paste your teacher token from step 2 — your lesson appears as a card.

### Features to verify while you're at it

If everything works, all of these should be reachable from the two notebooks + the dashboard above. Tick them off as you go:

- [ ] **Inline answer feedback** — `check(...)` returns ✅ when correct, ❌ with a hint when wrong.
- [ ] **Numeric / set / exact / manual comparators** — exercised one per cell in `demo-with-cadence.ipynb`.
- [ ] **Sectioned dashboard** — `setup` and `discovery` collapse independently; each shows aggregate solve rate.
- [ ] **Difficulty chips** — Easier / Average / Harder relative to siblings, hover for the raw avg-attempts number.
- [ ] **Solution reveal** — submit 3 wrong answers to `discovery.higgs-peak`; you get the 💡 reveal hint; call `cadence.show_solution("discovery.higgs-peak")` to see it.
- [ ] **Code submission** — the `%%cadence_submit discovery.higgs-peak` cell ships your code; the dashboard's per-checkpoint Submissions panel renders it with syntax highlighting.
- [ ] **Plot submission** — call `cadence.submit_image("discovery.higgs-peak", fig)` from anywhere; the dashboard renders the figure inline above the code.
- [ ] **Manual mark-done** — `mark_done("discovery.reflect")` returns ✅ Marked done; dashboard reads `1/1 marked done`.
- [ ] **Roster + chronology** — expand the Roster card; click a student row to see their per-checkpoint progress + the chronological log of every attempt with timestamps.
- [ ] **Currently-on chip** — each student row shows which checkpoint they last touched.
- [ ] **Wrong-answer attribution** — hover any common-wrong row (`125 ×11`) to see the students who submitted that value.
- [ ] **Timing tooltips** — hover any green timing bar to see who solved in that bucket.
- [ ] **Privacy toggles** — flip **Show student roster** OFF: roster panel disappears, hover-tooltips stop showing names. Flip back on; flip **Show outlier names** on to see inline "Fewest / Most attempts" rows.
- [ ] **Stuck-student alerts** — toggle on, grant browser permission. Submit 3 wrong answers in a row to one checkpoint; a desktop notification fires.
- [ ] **"N new attempts since you last looked" banner** — close the dashboard tab, run a few more `check()` calls in the student notebook, re-open the dashboard — the banner shows you what happened while you were away.
- [ ] **Scope toggle** — change between Standalone / This course / All-time on the notebook view (only when accessed via the course drill-in).
- [ ] **Polling pause** — leave the dashboard idle 5 min; the polling chip flips to amber "class quiet — polling every 15s". Switch tabs away; polling stops entirely.
- [ ] **Rotate token** — click **Rotate token** in the dashboard header. The old URL is dead immediately; the success banner shows the new one.
- [ ] **Library** — `/teacher/library` shows cards for every saved course/lesson with their live student count + solve rate.

If anything in that list doesn't behave as described, that's a real bug — please flag it.

## ✨ Core ideas

- **Drop-in, not bolt-on.** Teachers paste two lines into any existing notebook to register checkpoints. No magic structure, no separate "problem template" file required.
- **No login for students.** A short `join_code` (e.g. `soup-river-42`) is the only thing students need. Teachers hold a `teacher_token` that doubles as the dashboard URL — no password page.
- **Answer-checker, not code-grader.** Cadence compares student answers against teacher-registered expected values (`exact`, `numeric` with tolerance, `set`, `regex`). Student code runs locally on their machine; only the answer crosses the network.
- **Two organisational shapes.** A single notebook can be its own lesson, or you can group multiple notebooks under a `Course` to get a top-level "which notebook is everyone on" view.
- **Persistent and portable.** Lesson + course credentials live in `~/.cadence/lessons.yaml` (mode 0600). The same student notebook works across semesters; an all-time dashboard view aggregates every class that ever used it.

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │
│   (React)       │◄──►│   (FastAPI)     │
│                 │    │   + PostgreSQL  │
│  /teacher/live  │    │                 │
│  /teacher/course│    │   pulse-checks  │
└─────────────────┘    └────────▲────────┘
                                │ HTTPS / JSON
                       ┌────────┴────────┐
                       │ Jupyter kernel  │
                       │  + cadence pkg  │
                       │  %cadence_*     │
                       │  check("id", v) │
                       └─────────────────┘
```

The repo also contains a **legacy** code-competition submission flow (problems, test cases, Docker-sandboxed evaluation, GitHub sync). That flow is unrelated to Cadence's live-progress feature and is being phased out — feel free to ignore the "Problems" / "Submission" sections of the UI.

## 🎯 Jupyter Integration

Cadence ships as a Python package: `import cadence`, then `%load_ext cadence` at the top of any notebook to enable the magics.

### Quick Start with Jupyter

1. **Install the Extension**:
   ```bash
   pip install cadence-edu
   
   ```

2. **Load a Problem Notebook**:
   - Teachers provide `.ipynb` files with embedded problem metadata
   - Students open notebooks in Jupyter Lab or Jupyter Notebook

3. **Write and Submit Solutions**:
   ```python
   # Use magic commands for easy submission
   %%submit_solution hello-world-001
   print("Hello, World!")
   ```

4. **Get Immediate Feedback**:
   - Real-time evaluation results
   - Performance metrics
   - Detailed error messages

### For Teachers: Creating Problem Notebooks

```python
from cadence import create_problem_notebook

notebook = create_problem_notebook(
    problem_id="fibonacci-001",
    title="Fibonacci Sequence",
    description="Write a function that returns the nth Fibonacci number.",
    difficulty="Medium",
    test_cases=[
        {"input": "10", "output": "55", "points": 2},
        {"input": "20", "output": "6765", "points": 3},
    ]
)

notebook.save("fibonacci_problem.ipynb")
```

### For Students: Working with Notebooks

```python
# Setup your student information
%cadence_setup "John Doe" "john@example.com"

# List available problems
%cadence_problems

# Submit a solution
%%submit_solution fibonacci-001
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
```

## 📊 Live Lesson Progress

A teacher-facing dashboard that shows, in real time, how each student in a class is progressing through a notebook. Students call `check("checkpoint-id", answer)` from inside any cell; the teacher sees per-checkpoint solve counts, an attempts-to-first-correct histogram, and the most common wrong answers.

Designed to drop into **existing** notebooks — teachers add two lines to register a session and sprinkle `check(...)` calls wherever they want a pulse-check.

### 1. Start the backend (with Docker)

For this first release the backend has to run somewhere — your laptop is fine for a single class, and a small cloud server works for anything bigger. Either way Cadence ships as **four Docker containers** (FastAPI backend, React frontend, Postgres, Redis) that start with a single command. You don't need any prior Docker knowledge; this section walks the whole thing.

#### 1a. Install Docker Desktop (one-time)

Docker Desktop bundles everything you need — the daemon that runs containers and a small GUI to start/stop it. Grab the installer for your machine, run it, and launch the app at least once so the daemon starts:

- **macOS** — <https://www.docker.com/products/docker-desktop/> (works on both Intel and Apple Silicon).
- **Windows** — same link; the installer enables WSL2 automatically if needed.
- **Linux** — install **Docker Engine** + **Docker Compose plugin** following <https://docs.docker.com/engine/install/>. (No Desktop GUI required.)

Verify it's running:

```bash
docker version          # prints client + server versions
docker compose version  # should print v2.x
```

If `docker version` says it can't reach the daemon, open Docker Desktop and wait for its status to go green — every subsequent command needs the daemon up.

#### 1b. Get the code

```bash
git clone <this-repo-url> cadence
cd cadence
```

(The repo directory is currently named `competition_page/` on disk — that name is a leftover from the project's old identity. You can rename your local checkout to `cadence/` if you like; nothing inside depends on the directory name.)

#### 1c. Start the four containers

From the repo root:

```bash
docker compose up -d --build
```

What this does, in order:
1. **Builds** the backend and frontend images from the local `Dockerfile`s (only the first time, or after code changes). This downloads the Python and Node base images — expect ~2–3 minutes on a fresh machine.
2. **Pulls** the official Postgres and Redis images.
3. **Starts** all four containers in the background (`-d` = detached). They share a private Docker network and expose three ports on your machine:
   - `localhost:8000` → backend API
   - `localhost:3000` → frontend dashboard
   - `localhost:5432` → Postgres (only needed if you want to poke at the DB directly)

Verify everything is up:

```bash
docker compose ps             # all four services should say "Up"
curl http://localhost:8000/   # {"message":"Cadence API"}
open http://localhost:3000    # opens the dashboard in your browser
```

If any service is missing or restarting, jump to **§10 Troubleshooting** below.

#### 1d. Day-to-day commands

Once Cadence is running, these are the only Docker commands you'll need:

```bash
# Stop everything (containers paused, data preserved):
docker compose stop

# Start it back up later:
docker compose start

# Tail logs from the backend (useful for the checkpoint-comparison log):
docker compose logs -f backend

# Apply code changes you've made locally:
docker compose up -d --build

# Wipe everything including the database (start fully fresh):
docker compose down -v
```

`docker compose down -v` is the only command that destroys data — it removes the Postgres volume. Use it if you want a clean slate (e.g. to drop all the lessons you created during testing).

No password is required for the live-progress flow. Each lesson creates its own `teacher_token` (secret) and `join_code` (shareable), generated on the server.

### 2. Install the Jupyter extension

On the teacher's machine and every student machine:

```bash
cd jupyter-integration
pip install -e .

# Tell the package where the backend is (default: http://localhost:8000)
export CADENCE_API_URL=http://localhost:8000
# Optional: where the dashboard lives (default: http://localhost:3000)
export CADENCE_DASHBOARD_URL=http://localhost:3000
```

### 3. Picking a shape: single notebook or full course?

The platform supports two organisational styles — pick whichever fits your lesson:

| Style | When to use | Top-level object |
|---|---|---|
| **Standalone notebook** | One self-contained `.ipynb` per lesson (the default below). | `Lesson` |
| **Course** | You hand out **multiple notebooks** to the same class and want one dashboard that shows "who's on which notebook" plus drill-downs per notebook. | `Course` containing many `Lesson`s |

The course flow is documented in **§11** below. The standalone flow is the sections immediately following. You can mix and match — a standalone lesson can later be added to a course without recreating anything.

### How auth works (no passwords)

Cadence doesn't ask anyone to log in. Every lesson and every course has two server-generated strings:

- **`join_code`** — short and human-readable, e.g. `soup-river-42`. Shared with students. Knowing the code only lets you **join** the lesson as a student; you can't see expected answers or anyone else's data.
- **`teacher_token`** — long random string (32 URL-safe chars, produced by Python's `secrets.token_urlsafe(24)` on the server when the lesson is created). It's the **only** credential that grants register-checkpoints and view-dashboard access. Treat it like a password.

Both are returned in the response to `POST /lessons` or `POST /courses`. The teacher never types or chooses them — the backend mints them, the magic prints them, and they're saved to `~/.cadence/lessons.yaml` (file mode `0600`, owner-only readable). You can override the auto-generated codes with `--code` if you want a memorable join code, but the `teacher_token` is always server-generated and unguessable.

**What this means in practice:**
- The dashboard URL is `http://<host>:3000/teacher/live?token=<teacher_token>` (or `…/teacher/course?…` for courses). Anyone with the URL gets full teacher access — bookmark it, don't paste it in chat.
- If a `teacher_token` leaks, **rotate it** with `%cadence_rotate_token` (in a notebook) or `cadence-cli lessons rotate "<name>"` (in a shell). Either mints a new token and updates `~/.cadence/lessons.yaml` for you; the old token is dead. Pass `--also-join-code` for a full revocation that also disconnects current students.
- If you wipe the Postgres volume (`docker compose down -v`), every `teacher_token` is invalidated. Your local `~/.cadence/lessons.yaml` will still list them but the server won't recognise them — clear the stale rows with `cadence-cli lessons forget "<name>"` and recreate the affected lessons.
- Anyone with a `join_code` can enrol as a student under any display name. That's fine for classrooms; if you ever need stronger identity, you'd add an auth layer in front of the join flow.

#### Managing cached credentials

```bash
cadence-cli lessons list                              # show every cached entry, with masked tokens
cadence-cli lessons forget "Week 3: Fibonacci"        # drop a stale row from ~/.cadence/lessons.yaml
cadence-cli lessons rotate "Week 3: Fibonacci"        # mint a new teacher_token, keep the join_code
cadence-cli lessons rotate "Spring 2026" --also-join-code   # full revocation incl. join code
```

In a notebook the equivalent of the rotate command is:
```python
%cadence_lesson "Week 3: Fibonacci"
%cadence_rotate_token                # token-only rotation
%cadence_rotate_token --also-join-code   # also re-issue the join code
```
Add `--course` to either if the active context is a course rather than a single notebook.

Or **from the dashboard itself**: click the small **Rotate token** link in the live-dashboard header. A confirm dialog explains the consequence (old URL dies immediately); a success banner shows the new dashboard URL ready to copy. Hold Alt/Option while clicking to also rotate the join code.

#### The library page — managing multiple courses

The browser-side counterpart to `~/.cadence/lessons.yaml`. Navigate to:

```
http://localhost:3000/teacher/library
```

You'll see a card for every course and lesson you've added to this browser, with live student count, total attempts, and current solve rate. Click a card → opens that lesson/course's dashboard. Click **+ Add course / lesson** at the top right and paste a `teacher_token` (or a full dashboard URL) to add another. The "Try with demo data" button on the empty state loads the three seeded demo courses.

Storage is browser-local (`localStorage`) for now — the cross-device version arrives with teacher accounts (see [docs/teacher-accounts-design.md](docs/teacher-accounts-design.md)). Clearing site data wipes the library; the lessons themselves stay on the server.

### 3a. Teacher: create a lesson (one-time, at home)

```python
%load_ext cadence

%cadence_create_lesson "Week 3: Fibonacci"
```

This prints:

- A **join code** like `soup-river-42` — this goes into the student notebook.
- A **clickable dashboard link** with the `teacher_token` baked into the URL — bookmark it.

Credentials are persisted to `~/.cadence/lessons.yaml` (mode 0600), so the teacher never has to copy/paste tokens between notebooks.

Pick a memorable code instead of the auto-generated one:
```python
%cadence_create_lesson "Week 3: Fibonacci" --code fib-wk3
```

### 4. Teacher: register the expected answers

Still in the teacher notebook (the same one, or a new one — just re-activate the lesson):

```python
%load_ext cadence
%cadence_lesson "Week 3: Fibonacci"    # loads the token from the local cache

# Exact match
%cadence_register hello --comparator exact --expected '"Hello, World!"' \
    --hint "Watch the punctuation."

# Numeric with tolerance
%cadence_register circle-area --comparator numeric \
    --expected '{"value": 78.5398, "tolerance": 0.001}'

# Order-independent list
%cadence_register unique-vowels --comparator set \
    --expected '{"value": ["a","e","i","o","u"]}'

# Regex
%cadence_register email-format --comparator regex \
    --expected '{"pattern": "^[^@]+@[^@]+\\.[^@]+$"}'

# Manual — no auto-check; student calls cadence.mark_done() to self-attest
%cadence_register reflect --comparator manual \
    --hint "Briefly describe what the peak shape tells you."

# Ordering in the dashboard
%cadence_register fib-10 --order 1 --comparator numeric --expected '{"value": 55}'
```

Re-running with the same `checkpoint_id` updates the record — safe to iterate.

#### Registering many checkpoints at once

For longer labs, retyping `%cadence_register` per row gets tedious. There's a cell magic that takes a YAML block:

```python
%%cadence_register_yaml
- id: setup.mean-value
  comparator: numeric
  expected: {value: 49.5, tolerance: 0.001}
  hint: average of 0..99
  order: 1
- id: discovery.higgs-peak
  comparator: exact
  expected: 125
  reveal_after: 3
  solution_value: '125'
  solution_code: |
    bin_edges = np.arange(100, 151)
    counts, _ = np.histogram(m_gg, bins=bin_edges)
    int(bin_edges[np.argmax(counts)])
  allow_submissions: true
- id: discovery.reflect
  comparator: manual
  hint: Describe the peak shape.
```

Field names mirror the `%cadence_register` flags in snake_case (`reveal_after`, `solution_value`, `solution_code`, `allow_submissions`, `order`). The magic prints a per-row pass/fail summary so a single typo doesn't sink the whole batch. Re-running the same YAML is safe — checkpoints upsert by `id`.

#### Manual ("mark as done") checkpoints

For open-ended tasks with no single right answer — reflections, plots, "experiment with three values", etc. — register with `--comparator manual` and **omit** `--expected`. The student finishes by calling:

```python
cadence.mark_done("reflect")
```

The cell prints `✅ Marked done (attempt 1)` and the dashboard counts it like any solve, with two differences:
- The card header shows a small `✋ manual` chip and reads `N/M marked done` instead of `N/M solved`
- No difficulty chip (everyone "solves" first try), no common-wrong list (wrong is impossible)

Setting `--expected` on a manual checkpoint is an error — there's nothing to compare against. Calling `mark_done()` on an auto-checked checkpoint records a wrong attempt instead. The two flows are intentionally distinct.

> **Coming later:** plotting / image-uploading / teacher-review comparators will reuse the same checkpoint plumbing — `manual` is just the first in that family.

#### Code submissions (optional)

For any checkpoint, the teacher can opt in to **code submissions** — students send their full solution to the dashboard for the teacher to review or demo on screen. The auto-check still runs as configured (or doesn't, if the comparator is `manual`); submissions are a *separate* channel for the code itself.

Enable with `--allow-submissions` on `%cadence_register`:

```python
%cadence_register discovery.higgs-peak \
    --comparator exact --expected '125' \
    --hint "Watch the bin edges" \
    --allow-submissions
```

The student then runs a **cell magic** that executes the cell normally AND ships the source to the teacher:

```python
%%cadence_submit discovery.higgs-peak
bin_edges = np.arange(100, 151)
counts, _ = np.histogram(m_gamma_gamma, bins=bin_edges)
peak_bin_center = int(bin_edges[np.argmax(counts)])
print(peak_bin_center)
```

After the cell runs, the output shows `📤 Code submitted to discovery.higgs-peak`. Multiple submissions per student are allowed — students iterate, the dashboard shows the chronological feed (newest first).

**Teacher view:**

![Submissions panel — three approaches to the same Higgs-peak checkpoint with syntax highlighting](docs/images/dashboard-submissions.png)

- Checkpoint card grows a **`💾 N submissions`** chip in its header
- Below the wrong-answers section, a collapsible **"Submissions (N)"** panel
- Each submission renders with VSCode-dark Python syntax highlighting, the submitter's name (or `anonymous` when "Show student roster" is off), a relative timestamp, and a copy-to-clipboard button
- Useful in live class: open the panel, pick a clever solution, screen-share it as a contrast to the bin-edge confusion you've been discussing

Submitting to a checkpoint without `--allow-submissions` returns a clear error so a student notebook can't silently fail. Submissions are size-capped at 50 KB.

#### Plot / image submissions

Same opt-in (`--allow-submissions` on the checkpoint), different helper. Students can attach a **matplotlib figure** (or PIL image, or raw PNG bytes) to a submission:

```python
import matplotlib.pyplot as plt
fig, ax = plt.subplots()
ax.hist(m_gamma_gamma, bins=range(100, 151))
ax.set_title("Diphoton invariant mass — found the Higgs")

cadence.submit_image("discovery.higgs-peak", fig,
                     code="bins = range(100, 151); counts, _ = np.histogram(m_gg, bins=bins)")
```

The figure is encoded as PNG and shipped to the dashboard. The optional `code=` argument attaches a code snippet to the same submission. Images are size-capped at 1 MB (lower the `dpi=` on `savefig`, or crop the figure, if you hit the limit).

In the dashboard, the same "Submissions (N)" panel renders the figure inline above the code block — useful for plot-driven checkpoints where the headline insight is visual ("show me a histogram with a peak at 125 GeV"). Both `submit_image` and `%%cadence_submit` can target the same checkpoint; the panel mixes text and image submissions in chronological order.

> **Coming later:** automatic marking, exam-style checkpoints, and teacher-side "show this on screen" controls will all build on top of the same `code_submissions` plumbing.

#### Grouping checkpoints into sections (optional)

If a checkpoint id contains a `.` or `/`, Cadence treats the part before the **last** separator as a section name and the rest as the leaf label. The dashboard then groups consecutive same-section cards under a collapsible header. Backward compatible — flat ids still render as before.

```python
%cadence_register setup.mean-value     --comparator numeric --expected '{"value": 49.5}'
%cadence_register setup.row-sums       --comparator set     --expected '{"value": [6,22,38]}'
%cadence_register discovery.higgs-peak --comparator exact   --expected '125' --order 3
```

In the dashboard:
- `setup` and `discovery` show as section headers with aggregate solve rate + total attempts.
- Each header is click-to-collapse so a notebook with 20+ checkpoints stays scannable.
- Cards inside the section show just the leaf label (`mean-value`, `higgs-peak`).

The top-wrong-answers list still shows fully-qualified ids so a glance tells you which section a mistake lives in.

#### Solution reveals (optional)

A checkpoint can have a teacher-authored **solution** that students unlock once they've made enough attempts. Configure on the same `%cadence_register` line with three new flags:

| Flag | Required? | Meaning |
|---|---|---|
| `--reveal-after N` | Yes (to enable reveals) | Student needs `N` attempts before the solution becomes available |
| `--solution-value "<answer>"` | At least one of `value`/`code` | Short canonical answer — rendered as `<code>` |
| `--solution-code "<snippet>"` | At least one of `value`/`code` | Fully worked code block — rendered in a syntax-highlighted box |

If you set `--reveal-after` without either of `--solution-value`/`--solution-code`, registration fails — there's nothing to reveal.

```python
# Both: a short answer plus a worked solution
%cadence_register discovery.higgs-peak \
    --comparator exact --expected '125' \
    --hint "Integer center of the 1-GeV bin with the most events" \
    --reveal-after 3 \
    --solution-value 125 \
    --solution-code "bin_edges = np.arange(100, 151)
counts, _ = np.histogram(m_gamma_gamma, bins=bin_edges)
int(bin_edges[np.argmax(counts)])"

# Numerical-answer-only — for fact-recall checkpoints
%cadence_register half-life --comparator numeric \
    --expected '{"value": 5.27, "tolerance": 0.01}' \
    --reveal-after 4 --solution-value "5.27 years (Cobalt-60)"

# Code-only — when the answer is a procedure, not a number
%cadence_register clean-csv \
    --comparator set --expected '{"value": ["Alice","Bob"]}' \
    --reveal-after 5 --solution-code "df = pd.read_csv('data.csv').dropna()
df['name'].str.strip().tolist()"
```

**What the student sees** (in their notebook):

After every `check(...)`, once the attempt count reaches `--reveal-after`, the cell output gains a purple hint line:

> 💡 Show solution? Run `cadence.show_solution("discovery.higgs-peak")`

The student runs that helper to fetch and render the worked solution. Calling it earlier than the threshold returns a clear lockout message (`"Solution unlocks after 3 attempts; you have 1."`). Solutions for checkpoints with no reveal configured return 404 — students never know one exists.

**What the teacher sees** (on the dashboard):

Each checkpoint card with a solution wired up gets a pink **`🔓 solution`** chip in its header. Once any student uses the reveal, the chip switches to **`🔓 solution · N viewed`** — at a glance you can tell which checkpoints students are leaning on. The count is scope-aware (standalone / this course / all-time), so you can compare reveal-usage across cohorts.

### 5. Teacher: self-test before class

```python
%cadence_self_test
```

Starts a throwaway "self-test" session, submits each registered answer, and prints a table. Use this to catch `--expected` typos or tolerance errors **before** students do. (Regex checkpoints are skipped because a matching string can't be auto-synthesized.)

### 6. Teacher: prepare the student notebook

At the top of the notebook students will open:

```python
%load_ext cadence
%cadence_session soup-river-42 "Your name here"   # swap in your join code
```

Then, wherever a checkpoint belongs:

```python
from cadence import check

def fib(n):
    return n if n <= 1 else fib(n-1) + fib(n-2)

check("fib-10", fib(10))        # ✅/❌ inline, attempt is recorded server-side
```

`check` returns a truthy `CheckResult`, so students can branch on it:

```python
if not check("fib-10", fib(10)):
    print("Hint: remember fib(0) == 0.")
```

**Timed variant** — use `%%cadence_time` when you want a performance histogram alongside correctness:

```python
%%cadence_time fib-10
def fib(n):
    return n if n <= 1 else fib(n-1) + fib(n-2)

fib(10)       # the last expression's value is what gets checked
```

The whole cell is timed (wall clock), and the elapsed time is submitted with the answer. The timing that goes into the dashboard histogram is the time of the student's *first correct* attempt — so re-running a known-good cell 100 times doesn't pollute the stats. Buckets: `<10ms`, `10–100ms`, `100ms–1s`, `1–5s`, `5–30s`, `>30s`.

The **same notebook file** is reusable across classes — the join code is stable until the teacher deletes the lesson.

### 7. Teacher: watch the dashboard live

![Course overview — students enrolled, distribution across notebooks, course-wide completion histogram](docs/images/dashboard-course.png)

The dashboard lives at:

```
http://localhost:3000/teacher/live?token=<teacher_token>
```

You don't need to construct that URL by hand: `%cadence_create_lesson` and `%cadence_lesson` both print a clickable link with the token already embedded (under "🔗 Open live dashboard"). Bookmark it — there is no login page, the `teacher_token` in the URL *is* the credential.

If you ever need to rebuild it manually, the token is in `~/.cadence/lessons.yaml` under the lesson name.

The page polls every 3 s and shows two kinds of information:

**Lesson overview** (top card):
- **Sessions / checkpoints / total attempts / solve rate** — the four big-number stats at a glance.
- **Checkpoints-solved-per-student** histogram — how many students have finished 0, 1, 2, … of the registered checkpoints. A quick read on how far along the class is as a whole.
- **Top wrong answers across the lesson** — the five most-repeated wrong answers across every checkpoint, each tagged with its checkpoint id. Use it to spot shared misconceptions.

**Per checkpoint** (one card each):
- **Difficulty chip** — `Easier` / `Average` / `Harder`, relative to the other checkpoints in this notebook. Hover for the raw `avg attempts to solve`.
- **🔓 solution chip** — appears when the teacher configured `--reveal-after`. Reads `🔓 solution · after N` until any student uses the reveal, then `🔓 solution · N viewed`. Hover for full detail.
- **💾 N submissions chip** — appears when the teacher configured `--allow-submissions`. Click the *Submissions (N)* panel below the wrong-answers list to see each student's code in a syntax-highlighted block, with timestamps and copy-to-clipboard.
- **✋ manual chip** — appears when the comparator is `manual`. The "solved" label switches to "marked done".
- **Solved / attempted** counts and a solve-rate bar.
- **Attempts-to-first-correct** histogram: `1st try`, `2nd try`, `3+`, `unsolved`. Hover a bucket to reveal which students are in it (when "Show student roster" is on).
- **Timing histogram** for first-correct answers — populated when students use `%%cadence_time`; otherwise empty with a one-line hint telling the teacher how to enable it.
- **Most common wrong answers** (top 5) for that specific checkpoint — hover any row to reveal who submitted that wrong answer.

Above the per-checkpoint cards is a **Roster** panel (collapsed by default) listing every joined student with their solve count, attempt total, and a chip showing which checkpoint they're currently on. Filter by name to find one student fast.

Three header toggles control name visibility + alerts:
- **Show student roster** — master switch for any student name appearing in this dashboard. Off = aggregate-only, safe for screen-share.
- **Show outlier names** — adds an inline `Fewest / Most attempts` line at the bottom of each checkpoint card, naming the top 3 students on each side. Off by default so a screen-share doesn't out a struggling student.
- **Stuck-student alerts** — opts into **desktop notifications** when a student is actively struggling. Heuristic: 3+ wrong attempts on a single checkpoint in the last 5 minutes with no correct answer. The browser asks for permission once. Notifications fire even when the tab is in the background, so a teacher walking around the room can react. Each (student, checkpoint) pair only notifies once — re-attempts on the same checkpoint don't double-fire. Off by default.

If you ever need to rebuild the URL by hand:
```
http://<backend-host>:3000/teacher/live?token=<teacher_token>
```

### 8. Student workflow (what the class sees)

```bash
# One-time install (or the teacher pre-bakes it)
pip install -e /path/to/jupyter-integration
export CADENCE_API_URL=http://<teacher-host>:8000
```

Inside the notebook the teacher sent:

```python
%load_ext cadence
%cadence_session soup-river-42 "My Name"
```

…and work through the cells. Every `check(...)` call shows immediate ✅/❌ feedback; the teacher sees aggregate stats live.

### 9. Running against a remote server (for future deployments)

The single join code + teacher token design works identically in every deployment, so the student notebook doesn't need to change — only `CADENCE_API_URL` does.

| Option | Cost | Effort | When it fits |
|---|---|---|---|
| **Teacher laptop + ngrok / Tailscale** | free | low | Small class, you're in the room |
| **Fly.io / Railway / Render** | free tier → ~$5/mo | low | Always-on, one-click deploy |
| **VPS (Hetzner, DO, EC2)** | ~$5/mo | medium | Full control, your domain |

The live-progress flow does **not** execute student code on the server — only the answer crosses the network — so the Docker-in-Docker requirement of the submission flow does not apply. A single `shared-cpu-1x` instance + small Postgres comfortably handles **~15–20 simultaneous classrooms** (~500 students).

When you move between deployments, the teacher creates a fresh lesson on the new server (new `teacher_token`, same lesson name) and updates the join code in the student notebook. The local `~/.cadence/lessons.yaml` can hold entries for multiple deployments.

### 11. Course flow: multiple notebooks under one class

Use a course when students will move between several notebooks in the same teaching session.

#### 11a. Create the course + add notebooks

In a teacher-only notebook:

```python
%load_ext cadence
%cadence_create_course "Spring 2026 — Intro to Python"
# prints:
#   📚 Course created: Spring 2026 — Intro to Python
#   join code: soup-river-42
#   🔗 Open course dashboard  (bookmark this)

# Add notebooks — each one is a full lesson with its own checkpoints.
%cadence_add_notebook "Week 1 — Variables"     --order 1
%cadence_add_notebook "Week 2 — Loops"          --order 2
%cadence_add_notebook "Week 3 — Fibonacci"      --order 3

# Register checkpoints against the notebook most recently added
# (the magic activates it for you, same as %cadence_lesson):
%cadence_register greet --comparator exact --expected '"hello"'

# Switch focus to a different notebook inside the course:
%cadence_lesson "Week 1 — Variables"
%cadence_register colour --comparator set --expected '{"value": ["r","g","b"]}'

# Verify every expected answer before class:
%cadence_self_test
```

Credentials for both the course and each notebook are persisted to `~/.cadence/lessons.yaml` under their respective names. Re-open any teacher notebook later with:
```python
%cadence_course "Spring 2026 — Intro to Python"
%cadence_lesson "Week 1 — Variables"     # to add more checkpoints to that notebook
```

#### 11b. Student distribution

Each `.ipynb` you distribute to students starts with three lines:

```python
%load_ext cadence
%cadence_session soup-river-42 "Alice"     # course join code
%cadence_notebook "Week 1 — Variables"     # which notebook this .ipynb is
```

The first two lines never change between notebooks in the same course — only `%cadence_notebook` differs per file. Students use `check(...)` and `%%cadence_time` inside each notebook as usual.

#### 11c. Dashboards

- **Course overview** — `http://localhost:3000/teacher/course?token=<course_token>` (also the link printed by `%cadence_create_course`):
  - Total enrollments and how many haven't picked a notebook yet.
  - Table of notebooks showing **students currently on each** (from their most recent `%cadence_notebook` call), per-notebook solve rate, and a bar distribution.
  - Click **Open** on any notebook row to drill into its per-notebook dashboard with the scope pre-selected to "this course".
  - Course-wide completion histogram: how many checkpoints across all notebooks each student has solved.

- **Notebook view** — the per-checkpoint dashboard (§7) gains a **scope toggle**:
  - **Standalone joiners** — students who joined this specific notebook directly via its lesson join code.
  - **This course** — students enrolled in the course you drilled in from.
  - **All-time (every course)** — aggregate across every course this notebook has ever been part of. Perfect for seeing how a problem performs historically before re-teaching it.

### 10. Troubleshooting

#### Why did the server reject my answer?

Every `/check` call logs the exact values it compared. Tail the backend:

```bash
docker compose logs -f backend | grep '\[checkpoint\]'
```

You'll see one line per attempt, e.g.

```
[checkpoint] lesson=... cp=fib-10 comparator=numeric expected={'value': 55} submitted='fifty-five' result=False (non-numeric value: could not convert string to float: 'fifty-five')
```

Look for the parenthesised **reason** at the end — it tells you whether the value failed type coercion, missed the tolerance window, didn't match the regex, etc. Common gotchas:

- **exact**: trailing whitespace, capitalisation, or curly-vs-straight quotes.
- **numeric**: forgot `--tolerance` for floats (`0.1 + 0.2 != 0.3` without one).
- **set**: duplicates in the student's answer become a single element; the `set` comparator ignores multiplicity.
- **regex**: `re.match` anchors at the start but not the end — add `$` if you need a full-string match.

If `%cadence_self_test` says a checkpoint is `fail`, the log will tell you why *before* students ever see it.

#### Docker errors

| Symptom | Cause / fix |
|---|---|
| `Cannot connect to the Docker daemon` / `error during connect` | Docker Desktop isn't running. Open the app and wait for the whale icon to stop animating. On Linux, `sudo systemctl start docker`. |
| `port is already allocated` (8000, 3000, or 5432) | Something else on your machine is using that port. Stop it, or change the host-side port mapping in [docker-compose.yml](docker-compose.yml) (e.g. `"8001:8000"` then visit `localhost:8001`). |
| Build hangs on `npm install` or `pip install` | Slow network on the very first run — the base images can take several minutes. Subsequent `up` calls reuse the cached image and are near-instant. |
| `docker compose: command not found` | You have the old standalone `docker-compose` (with a hyphen) instead of the Compose plugin. Either upgrade Docker, or substitute `docker-compose` for `docker compose` in every command in this README. |
| Container status is `Restart(1)` or `Exit(…)` | Run `docker compose logs <service>` (e.g. `docker compose logs backend`) to see the crash trace. Most often it's a Postgres connection error from starting before the DB was ready — try `docker compose restart backend`. |
| Apple Silicon (M1/M2/M3) warns about `linux/amd64` images | Harmless — the containers run under emulation. If performance matters in production, deploy to a real Linux server. |
| You want to start completely fresh | `docker compose down -v` wipes the Postgres volume; `up -d --build` rebuilds and reseeds. |

#### Cadence errors

| Symptom | Cause / fix |
|---|---|
| `❌ Cadence API not reachable at …` | Backend isn't running, or `CADENCE_API_URL` points somewhere wrong. |
| `❌ No active lesson` when calling `%cadence_register` | Run `%cadence_lesson "…"` or `%cadence_create_lesson "…"` first. |
| `❌ Unknown teacher token` / `Unknown join code` | The lesson was created against a different backend (e.g. a fresh Docker volume). Recreate the lesson and update the join code in the student notebook. |
| `❌ No active session. Run %cadence_session …` when calling `check()` | Student forgot to run `%cadence_session` after `%load_ext`. |
| Dashboard says "No checkpoints registered" | Teacher hasn't run `%cadence_register …` yet, or registered them against a different lesson. |
| Dashboard stays empty of sessions | Check `docker compose logs backend`; confirm the join code students used matches the one in the dashboard header. |
| `❌ --reveal-after needs at least one of --solution-value or --solution-code` | Teacher set a reveal threshold but forgot to provide a solution to reveal. Add `--solution-value "…"` and/or `--solution-code "…"`. |
| `🔒 Solution unlocks after N attempts; you have M.` | Student called `cadence.show_solution(...)` before hitting the configured threshold. Keep trying — the helper will work once `M >= N`. |
| `🔒 No solution configured for this checkpoint` (404) | Teacher never registered `--reveal-after` for this checkpoint. Either configure one or don't surface `show_solution(...)` to students. |
| `❌ This checkpoint doesn't accept code submissions` | Teacher hasn't set `--allow-submissions` on this checkpoint. Either turn it on with `%cadence_register --allow-submissions …` or remove the `%%cadence_submit` cell magic from the student notebook. |
| `❌ Submission too large (50KB limit)` | The cell source exceeds 50 KB. Trim or split the cell. |
| Cold-start lag on Fly.io | Set `min_machines_running = 1` (~$2–3/mo). |

## 📋 Installation

### Option 1: Quick Start (Recommended)
```bash
# Clone the repository
git clone <repository-url>
cd competition_page

# Run the setup script
./setup.sh
```

### Option 2: Manual Installation
```bash
# Install Docker and Docker Compose
# (See QUICKSTART.md for detailed instructions)

# Clone and setup
git clone <repository-url>
cd competition_page
docker compose up -d
```

### Option 3: Jupyter Integration Only
```bash
# Install just the Jupyter extension
pip install cadence-edu

```

## 🎯 Usage

### For Students

#### 1. Web-based Submission
1. **Browse Problems**: View available programming challenges
2. **Write Code**: Use the built-in code editor with syntax highlighting
3. **Submit Solutions**: Get immediate feedback and results
4. **View Results**: See detailed test case results and performance metrics

#### 2. Jupyter-based Submission
1. **Get Problem Notebook**: Teacher provides a `.ipynb` file
2. **Open in Jupyter**: Use Jupyter Lab or Jupyter Notebook
3. **Write Solution**: Code in your preferred environment
4. **Submit with Magic**: Use `%%submit_solution` magic command
5. **Get Results**: See evaluation results inline

#### 3. GitHub-based Submission (if enabled by teacher)
1. **Get Repository Access**: Teacher will provide a GitHub repository URL
2. **Clone the Repository**: `git clone <repository-url>`
3. **Create Your Workspace**: 
   ```bash
   cd problem-name
   mkdir your-name
   cd your-name
   ```
4. **Add Your Solution**: Create your solution files (e.g., `solution.py`, `solution.cpp`)
5. **Commit and Push**:
   ```bash
   git add .
   git commit -m "My solution for [Problem Name]"
   git push origin main
   ```
6. **Wait for Evaluation**: The teacher will sync the repository to evaluate your code

#### 4. Supported Languages and Formats

**Python Solutions**:
```python
# solution.py
def main():
    # Read input
    n = int(input())
    
    # Your solution here
    result = n * 2
    
    # Print output
    print(result)

if __name__ == "__main__":
    main()
```

**C++ Solutions**:
```cpp
// solution.cpp
#include <iostream>
using namespace std;

int main() {
    // Read input
    int n;
    cin >> n;
    
    // Your solution here
    int result = n * 2;
    
    // Print output
    cout << result << endl;
    
    return 0;
}
```

### For Teachers

#### 1. Initial Setup
1. **Login**: Use the default credentials (admin/teacher123)
2. **Create Problems**: Add programming problems with test cases
3. **View Analytics**: Monitor student performance and statistics

#### 2. Jupyter Integration Workflow

**Setting up Jupyter Integration:**

1. **Create Problem Notebooks**:
   ```python
   from cadence import create_problem_notebook
   
   notebook = create_problem_notebook(
       problem_id="fibonacci-001",
       title="Fibonacci Sequence",
       description="Write a function that returns the nth Fibonacci number.",
       difficulty="Medium",
       test_cases=[
           {"input": "10", "output": "55", "points": 2},
           {"input": "20", "output": "6765", "points": 3},
       ]
   )
   notebook.save("fibonacci_problem.ipynb")
   ```

2. **Distribute to Students**:
   - Share the `.ipynb` files
   - Students work in their preferred Jupyter environment
   - Solutions are automatically submitted to the platform

3. **Monitor Submissions**:
   - View all submissions in the teacher dashboard
   - Track student progress and performance
   - Analyze common error patterns

#### 3. GitHub Integration Workflow

**Setting up GitHub Integration:**

1. **Create a GitHub Personal Access Token**:
   - Go to GitHub Settings → Developer settings → Personal access tokens
   - Click "Generate new token (classic)"
   - Select scopes: `repo`, `read:user`, `read:email`
   - Copy the generated token

2. **Configure the Platform**:
   - Add your GitHub token to the `.env` file: `GITHUB_TOKEN=ghp_your_token_here`
   - Restart the backend: `docker-compose restart backend`

3. **Create GitHub Repositories for Problems**:
   - Go to the Teacher Dashboard
   - Click "GitHub Integration" in the navigation
   - Click "Create Repository" for a specific problem
   - The system will create a private GitHub repository for that problem

**Managing Student Submissions via GitHub:**

1. **Repository Structure**: Each repository will have:
   ```
   problem-name/
   ├── README.md (problem description)
   ├── test-cases/ (hidden test cases)
   └── student-submissions/ (where students add their work)
   ```

2. **Student Instructions**: Share these instructions with students:
   - Clone the repository: `git clone <repository-url>`
   - Create a folder with your name: `mkdir your-name`
   - Add your solution files to your folder
   - Commit and push: `git add . && git commit -m "Your solution" && git push`

3. **Automatic Evaluation**:
   - Click "Sync Repository" in the GitHub Integration dashboard
   - The system will automatically:
     - Fetch all student commits
     - Evaluate each student's code against test cases
     - Update the dashboard with results

#### 4. Review and Analytics

1. **View All Submissions**: See all student submissions with detailed results
2. **Individual Review**: Click on any submission to see:
   - Student's code
   - Test case results
   - Execution time and memory usage
   - Error messages (if any)

3. **Analytics Dashboard**: Monitor:
   - Problem success rates
   - Average scores
   - Common error patterns
   - Performance metrics

## 🛠️ Development

### Project Structure
```
competition_page/
├── backend/                 # FastAPI backend
├── frontend/               # React frontend
├── database/               # Database initialization
├── docker/                 # Docker configurations
├── jupyter-integration/    # Jupyter extension
│   ├── cadence/
│   ├── examples/
│   └── setup.py
├── docker-compose.yml      # Main orchestration
├── setup.sh               # Quick setup script
└── README.md              # This file
```

### Running in Development
```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down

# Rebuild after changes
docker compose up -d --build
```

### Jupyter Development
```bash
# Install in development mode
cd jupyter-integration
pip install -e .

# Enable the extension



# Start Jupyter
jupyter lab
```

## 🚀 Production Deployment

**For Students to Access the Platform:**

1. **Deploy to a Cloud Server**:
   - **AWS**: Use EC2 with Docker or ECS
   - **Google Cloud**: Use Compute Engine or Cloud Run
   - **DigitalOcean**: Use Droplets with Docker
   - **Heroku**: Use container deployment
   - **Railway/Render**: Simple container deployment

2. **Configure Domain and SSL**:
   ```bash
   # Example: cadence.yourschool.edu
   # Students access: https://cadence.yourschool.edu
   ```

3. **Update Environment Variables**:
   ```env
   # Production settings
   SECRET_KEY=your-secure-random-string
   DATABASE_URL=postgresql://user:pass@host:5432/db
   REACT_APP_API_URL=https://cadence.yourschool.edu
   ```

4. **Set up Reverse Proxy** (nginx example):
   ```nginx
   server {
       listen 80;
       server_name cadence.yourschool.edu;
       return 301 https://$server_name$request_uri;
   }

   server {
       listen 443 ssl;
       server_name cadence.yourschool.edu;
       
       ssl_certificate /path/to/cert.pem;
       ssl_certificate_key /path/to/key.pem;
       
       location / {
           proxy_pass http://localhost:3000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
       
       location /api {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

5. **Enable HTTPS** with Let's Encrypt:
   ```bash
   sudo certbot --nginx -d cadence.yourschool.edu
   ```

### Quick Deployment Options

**Option 1: Railway (Recommended for beginners)**
```bash
# 1. Fork this repository to your GitHub
# 2. Connect to Railway.app
# 3. Deploy automatically
# 4. Get public URL like: https://your-app.railway.app
```

**Option 2: DigitalOcean App Platform**
```bash
# 1. Push to GitHub
# 2. Connect DigitalOcean App Platform
# 3. Deploy with docker-compose.yml
# 4. Get public URL
```

**Option 3: AWS EC2**
```bash
# 1. Launch EC2 instance
# 2. Install Docker and Docker Compose
# 3. Clone repository
# 4. Run: docker-compose up -d
# 5. Configure security groups and domain
```

## 📚 Documentation

- **Quick Start**: See `QUICKSTART.md` for detailed setup instructions
- **Development**: See `DEVELOPMENT.md` for development guidelines
- **Jupyter Integration**: See `jupyter-integration/README.md` for Jupyter-specific documentation
- **API Documentation**: Available at `http://localhost:8000/docs` when running

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🆘 Support

- **Documentation**: [Link to docs]
- **Issues**: [GitHub Issues]
- **Discussions**: [GitHub Discussions]
- **Email**: support@cadence.example 