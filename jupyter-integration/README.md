# Cadence — live student progress dashboards for Jupyter

`cadence-edu` is the Jupyter-side half of [Cadence](https://cadence-dash.com): a tiny set of magics and helpers that let a teacher register **checkpoints** in a notebook, students answer them inline from their own notebooks with `check("id", value)`, and a teacher dashboard shows live solve counts, attempts-to-first-correct, and the most common wrong answers in real time.

No grader. No autograder pipeline. No login required for quick one-off lessons. Just `pip install`, `%load_ext cadence`, and a join code on the projector.

```bash
pip install cadence-edu
```

---

## Quickstart (5 minutes)

The fastest path: let the CLI mint both notebooks for you, then edit in place.

```bash
pip install cadence-edu

cadence-cli new teacher --name "Fibonacci warm-up"   # writes ./teacher-setup.ipynb
cadence-cli new student --name "Fibonacci warm-up"   # writes ./student.ipynb
```

Each starter has the right magics pre-wired — `%load_ext cadence`,
`%cadence_create_lesson` / `%cadence_session`, a YAML registration block, an
example `check(...)` — so you can `jupyter notebook` straight into editing
real content.

If you'd rather copy a cell by hand:

**Teacher notebook** (run once per lesson, keep it private):

```python
%load_ext cadence
%cadence_create_lesson "Fibonacci warm-up"
# → prints a join code (e.g. soup-river-42) and the dashboard URL

%cadence_register fib-10 --comparator numeric --expected '{"value": 55}'
%cadence_register greet  --comparator exact   --expected '"hello"'

%cadence_self_test            # verifies your expected answers parse correctly
%cadence_show_join            # big-text join code for the projector
```

**Student notebook** (distributed to the class — reusable every term):

```python
%load_ext cadence
%cadence_session soup-river-42 "Alice Smith"

from cadence import check
check("greet", "hello")
check("fib-10", fib(10))
```

The teacher's dashboard updates live as students submit. That's the whole product.

> **Discovering commands as you go**: type `%cadence_<Tab>` for autocompletion,
> `%cadence_register?` for argparse-style help on any magic, or
> `%cadence_help` for a one-page cheatsheet of every Cadence magic with its
> exact syntax. After typing `%cadence_lesson` (or `%cadence_course`) the
> names cached in `~/.cadence/lessons.yaml` tab-complete too.

---

## Concepts

| Term | What it is |
|---|---|
| **Lesson** | One notebook's worth of checkpoints. Created with `%cadence_create_lesson`. Has its own join code + teacher token. Anyone can create one — no account required. |
| **Course** | A named group of notebook lessons (e.g. "Fall 2026"). Created with `%cadence_create_course`. **Requires `%cadence_login`.** Students join the course with one code, then pick a notebook. |
| **Checkpoint** | One expected answer in a lesson. Has an ID, a comparator (`exact`/`numeric`/`set`/`regex`/`manual`), an optional hint, and an optional worked solution. Registered with `%cadence_register`. |
| **Session** | A student's enrollment in a lesson or course. Started with `%cadence_session <code> "<name>"`. |

---

## Teacher workflow

### Creating a single lesson (no account needed)

```python
%load_ext cadence
%cadence_create_lesson "Week 3: Fibonacci"
```

The first run creates the lesson and caches the teacher token in `~/.cadence/lessons.yaml`. Re-running with the same name reactivates the cached lesson — safe to run at the top of every notebook session. Use `--force` if you genuinely want a second lesson with the same name (different token, different join code).

### Creating a course of lessons (account required)

```python
%load_ext cadence
%cadence_login                    # prompts for username + password
                                  # or: %cadence_login --token <jwt>
%cadence_whoami                   # confirm who's logged in
                                  # %cadence_logout clears the cached JWT

%cadence_create_course "Fall 2026 Statistics"
%cadence_add_notebook "Week 1 — Variables"
%cadence_add_notebook "Week 2 — Distributions"
```

`%cadence_add_notebook` creates a brand-new lesson *inside* the active course. To pull in a lesson you already created standalone, use `%cadence_attach_lesson "My Lesson" --to "Fall 2026 Statistics"`.

The first lesson or course creation prompts inline to accept the Terms of Service; if you'd rather accept up front in a script, run `%cadence_accept_terms` first.

### Registering checkpoints

```python
%cadence_register fib-10 \
    --comparator numeric \
    --expected '{"value": 55, "tolerance": 0.001}' \
    --hint "Remember: fib(0)=0, fib(1)=1." \
    --order 2
```

Comparators and the `--expected` shape they take:

| Comparator | `--expected` | Match rule |
|---|---|---|
| `exact` | `'"hello"'` or `'{"value": "hello"}'` | `str(submitted).strip() == str(value).strip()` |
| `numeric` | `'{"value": 55}'` or `'{"value": 3.14, "tolerance": 0.001}'` | `abs(submitted - value) <= tolerance` |
| `set` | `'{"value": [1, 2, 3]}'` | `set(submitted) == set(value)` (order-independent) |
| `regex` | `'{"pattern": "^[A-Z].*"}'` | `re.match(pattern, str(submitted))` |
| `manual` | (none) | Student self-attests with `mark_done("id")` |

Re-running `%cadence_register` with the same ID updates the checkpoint in place.

**Bulk registration** for big lessons — drop a whole YAML body into one cell:

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

Or keep the YAML in version control alongside your notebook and load it:

```python
%cadence_register_yaml_file checkpoints/week3.yaml
```

### Verifying before class

```python
%cadence_self_test
```

Submits each checkpoint's own expected answer and prints a pass/fail table. Catches typos in `--expected` and bad tolerance bounds. Regex checkpoints are skipped (can't auto-synthesize a matching string).

### Displaying the join code

```python
%cadence_show_join
```

Big-text rendering of the active lesson or course's join code — designed for projector / screen share.

### Managing existing lessons and courses

```python
%cadence_lesson "Week 3: Fibonacci"           # reactivate a cached lesson
%cadence_course "Fall 2026 Statistics"        # reactivate a cached course

%cadence_clone_lesson "Fall 2026 Week 3" --as "Spring 2027 Week 3"
                                              # duplicate (fresh code + token)

%cadence_attach_lesson "Lab 1" --to "Fall 2026 Statistics"
%cadence_detach_lesson "Lab 1" --from "Fall 2026 Statistics"

%cadence_delete_lesson "Old test lesson" --yes    # wipes the lesson + ALL student data
%cadence_delete_course "Fall 2025" --yes          # wipes the course; attached lessons survive
```

### Rotating a leaked teacher token

```python
%cadence_rotate_token                         # mints a fresh teacher_token
%cadence_rotate_token --also-join-code        # full revocation: also reissues the join code
                                              # (existing student notebooks break)
%cadence_rotate_token --course                # rotate the active course's token
```

The local `~/.cadence/lessons.yaml` is updated in place and a fresh dashboard URL is printed.

### Code submissions (optional)

For checkpoints registered with `--allow-submissions`, students can use `%%cadence_submit <id>` to send the cell's *source code* to your dashboard for review:

```python
%%cadence_submit fib-recursive
def fib(n):
    return n if n <= 1 else fib(n-1) + fib(n-2)
fib(10)
```

The cell still runs normally — the student sees their output. The source is sent alongside.

### Retention controls

```python
%cadence_set_retention --days 30              # active lesson
%cadence_set_retention --days 90 --course     # active course
```

Retention can only be **shortened**, never extended. To lengthen it you'd clone the lesson and migrate fresh students over — a design constraint, not a bug.

---

## Student workflow

### Joining

```python
%load_ext cadence
%cadence_session soup-river-42 "Alice Smith"
```

If the join code belongs to a **course**, the magic prints the list of notebooks and reminds you to pick one:

```python
%cadence_notebook "Week 1 — Variables"
```

### Answering checkpoints

```python
from cadence import check, show_hint, show_solution, mark_done, submit_image

result = check("fib-10", fib(10))       # returns a CheckResult
# result.is_correct, result.attempt_num, result.hint
# Also renders in the cell as a coloured ✅/❌ chip.

show_hint("fib-10")                     # fetches the teacher's hint
show_solution("fib-10")                 # fetches the worked solution if revealed
mark_done("manual-checkpoint")          # self-attest a manual checkpoint
submit_image("plot-1", fig)             # for `--allow-submissions` image checkpoints
```

### Timed answers

```python
%%cadence_time fib-10
def fib(n):
    return n if n <= 1 else fib(n-1) + fib(n-2)
fib(10)
```

Measures wall-clock time and submits the last-expression value as the answer. Only the **first correct** attempt's time contributes to the dashboard histogram, so re-running a known-good cell doesn't pollute the stats. If the cell raises, nothing is submitted.

### Your data rights (GDPR)

`cadence-edu` ships explicit support for the three Article-15/17/20 rights:

```python
%cadence_my_data                # Article 15 — see everything stored about this session
%cadence_export_my_data         # Article 20 — dump it as JSON
%cadence_export_my_data --path ~/my-cadence-data.json
%cadence_delete_my_data --yes   # Article 17 — wipe attempts, submissions, the session itself
```

`%cadence_delete_my_data` cannot be undone and clears the active session from the kernel afterwards.

---

## CLI helpers

The package also installs a `cadence-cli` for two jobs from the shell:

**Scaffold a starter notebook.** Drops a pre-wired `.ipynb` in the current
directory so you don't start from a blank cell:

```bash
cadence-cli new teacher --name "Week 3: Fibonacci"    # writes ./teacher-setup.ipynb
cadence-cli new student --name "Week 3: Fibonacci"    # writes ./student.ipynb
cadence-cli new teacher --out path/to/setup.ipynb --force   # custom location, overwrite
```

The teacher scaffold has `%load_ext cadence` → `%cadence_login` →
`%cadence_create_lesson` → a YAML registration block → `%cadence_self_test`
in order. The student scaffold has a placeholder `%cadence_session` line and
one example `check(...)`. Both are tiny on purpose — they're a launching
pad, not a tutorial. The longer-form particle-physics demos live at
[cadence-dash.com/demo](https://cadence-dash.com/demo).

**Manage locally-cached teacher credentials** — useful when the server-side
lesson has been deleted but the local YAML is stale, or when you suspect a
token leak:

```bash
cadence-cli lessons list                              # every cached lesson + course, tokens masked
cadence-cli lessons forget "Week 3: Fibonacci"        # drop a stale row (local only)
cadence-cli lessons forget "Week 3: Fibonacci" --yes  # skip the confirmation prompt
cadence-cli lessons rotate "Week 3: Fibonacci"        # mint a new teacher_token
cadence-cli lessons rotate "Spring 2026" --also-join-code   # full revocation
```

`forget` only touches the local YAML. `rotate` calls the backend and updates the cache in place.

---

## Configuration

### Files

| Path | What it holds |
|---|---|
| `~/.cadence/lessons.yaml` | Cached teacher tokens + join codes for lessons and courses (mode `0600`) |
| `~/.cadence/credentials.yaml` | Teacher JWT from `%cadence_login` (mode `0600`) |
| `~/.cadence/terms.yaml` | Recorded ToS acceptance from `%cadence_accept_terms` |

### Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `CADENCE_API_URL` | `https://api.cadence-dash.com` | Backend API base URL. Set to `http://localhost:8000` for local dev. |
| `CADENCE_DASHBOARD_URL` | (falls back to `CADENCE_WEB_URL`, then `http://localhost:3000`) | Where the teacher dashboard lives. Used to build the URLs printed by create-lesson. |
| `CADENCE_WEB_URL` | `https://cadence-dash.com` | Public web URL — used for legal-page links. |

For self-hosted setups, set `CADENCE_API_URL` + `CADENCE_DASHBOARD_URL` to your own deployment.

---

## Troubleshooting

**"API not available" / SSL errors on first magic.** The package defaults to the hosted backend at `api.cadence-dash.com`. If you're running locally, point it at your own instance:

```bash
export CADENCE_API_URL=http://localhost:8000
export CADENCE_DASHBOARD_URL=http://localhost:3000
```

**Extension didn't load.** Confirm the install with:

```bash
jupyter server extension list           # Notebook 7 / JupyterLab
```

Then re-run `%load_ext cadence` in the kernel.

**Stale cached lesson.** If you `docker compose down -v`'d your local backend, your `~/.cadence/lessons.yaml` will reference lessons that no longer exist. Drop them with `cadence-cli lessons forget "<name>"`.

**Teacher token leaked.** `%cadence_rotate_token` mints a new one and invalidates the old. Add `--also-join-code` if you also need to lock out existing students.

---

## Other primitives

A few legacy helpers are still exposed for the original code-submission flow:

- `CadenceAPI` — direct API client (`from cadence import CadenceAPI`)
- `ProblemNotebook` / `create_problem_notebook` — pre-formatted problem-notebook templates with embedded metadata and test cases

These predate the live-progress flow and aren't on the happy path; use them only if you're integrating with an external grader.

---

## Links

- **Hosted dashboard & docs:** https://cadence-dash.com
- **Setup guide:** https://cadence-dash.com/guide
- **Source:** https://github.com/livaage/cadence
- **Issues:** https://github.com/livaage/cadence/issues

## License

MIT — see [LICENSE](LICENSE).
