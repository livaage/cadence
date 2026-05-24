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

### Markers vs magics — the discipline

Cadence has two kinds of syntax. The rule is simple and worth holding in mind
because every other detail follows from it.

| | Form | Purpose | Examples |
|---|---|---|---|
| **Markers** | Comments — `# cadence:foo` in code cells, `<!-- cadence:foo -->` in markdown cells | *Static metadata.* They label what a cell IS. They never do anything when you run the cell — they sit there waiting for tools to read them. | `# cadence:checkpoint setup.arange`<br>`# cadence:solution`<br>`# cadence:hint: try ...`<br>`<!-- cadence:task setup.arange -->` |
| **Magics** | Jupyter line/cell magics — `%cadence_foo` / `%%cadence_foo` | *Actions.* They DO something now: talk to the server, read your notebook, write a file. | `%cadence_create_lesson "..."`<br>`%cadence_autoregister`<br>`%cadence_scaffold`<br>`%%cadence_register_yaml` |

So when you see `# cadence:checkpoint mean.basic`, it doesn't talk to any
server — it just labels the cell. When you see `%cadence_autoregister`, it's
doing work in real time and might prompt you.

---

## Teacher workflow

### The recommended path: `%cadence_autoregister`

You already have (or are writing) a notebook with worked solutions. The
fastest path from "I have a teaching notebook" to "I have a live class"
is one magic and one prompt-walkthrough — `%cadence_autoregister`.

Concretely: in your existing teaching notebook, run all cells end-to-end
so your answer variables exist in the kernel, then in a new cell at the
bottom run:

```python
%load_ext cadence
%cadence_autoregister
```

It walks you through three prompts:

1. **Reveal solutions to students after N attempts?** Empty → no reveals.
2. **Sign in to track this lesson under your account?** (Only asked if
   you aren't already signed in.) Required for courses, optional otherwise.
3. **Add this lesson to a course?** Only asked if you're signed in. Empty
   for standalone; a course name to attach to an existing one; or
   `new: <name>` to create a new course.
4. **How many days to keep each student's data?** Empty → 7 days for a
   standalone lesson, 90 days for a course.

It writes `<your_notebook>_registered.ipynb`. Open it, do "Run All", and
the final cell — also generated for you — calls `%cadence_scaffold`,
which writes `<your_notebook>_registered_student.ipynb`. That's the file
you share with students.

**Two ways to tell autoregister which cells are exercises**, and you can
mix them:

- **Explicit (recommended for control):** put `# cadence:checkpoint <id>`
  at the top of each solution cell.
- **Implicit (works on a vanilla notebook):** if you have *no* checkpoint
  markers, autoregister pairs every markdown-heading cell with the code
  cell that follows it as an exercise. The id is slugified from the
  heading. Pass `--all` to force this even when manual markers exist.

In either case, the answer value is read from the kernel namespace, the
comparator is inferred from its type, and a `%cadence_register …` line
gets injected at the top of the exercise cell — so when you scroll past
an exercise the registration sits right above the code that produced it.
No giant YAML block at the top to maintain.

Comparator inference:

| Value | Comparator | Notes |
|---|---|---|
| `int`, `float`, numpy scalar | `numeric` (tolerance 0.001) | |
| `str` | `exact` | text answers — punctuation matters |
| `bool` | `exact` | |
| `list`, `tuple`, numpy array | `set` (order-insensitive) | override per-exercise with `# cadence:checkpoint <id> exact` for ordered match |
| `set` | `set` | |
| (override) | `manual` | `# cadence:checkpoint <id> manual` — free-text reflection, no value extracted, student self-attests with `mark_done` |

#### How autoregister decides — the rules

Two questions per cell: *is this an exercise?* and *what's the answer?*
Stated explicitly so you can tell at a glance whether your notebook is
going to autoregister cleanly or whether you need explicit markers.

**Is this cell an exercise?**

- **Explicit mode** (any cell has `# cadence:checkpoint`): exercise iff
  the cell has that marker. Every other code cell is treated as setup
  and copied verbatim. The markdown cell directly above an exercise
  becomes its task description (if there is one).
- **Auto mode** (no checkpoint markers in the notebook): exercise iff
  (a) a markdown cell with a heading sits above it, claimed by no
  earlier code cell, **and** (b) its extracted value is a "primitive
  answer type" (`int`, `float`, `str`, `bool`, list/tuple/set of those,
  numpy scalar / array). If either fails, the cell is treated as
  setup and copied verbatim.
- **Pure-import cells and magic-only cells** are always treated as setup
  regardless of mode.
- **Pass `--all`** to autoregister to force auto mode even when manual
  markers exist (useful for a quick first pass on a notebook you're
  about to add markers to).

**What's the answer?**

Autoregister parses the cell's AST and looks at the **last statement**:

| Last statement | What gets used as the answer |
|---|---|
| A bare expression (Jupyter display style) — e.g. `arr.mean()` on its own line | The value of that expression, looked up in the live kernel namespace. |
| An assignment to a single name — e.g. `mean_value = arr.mean()` | The current value of `mean_value` in the kernel namespace. |
| An augmented assignment — `total += 1` | The current value of `total` in the kernel. |
| Anything else (an `if`/`for`/`def`/import-only ending, multi-target assignment, etc.) | Autoregister errors with a teacher-friendly message asking you to end the cell with the answer on its own line. |

In all cases the value comes from the **live kernel** — you must have
run the cell (and the cells before it) end-to-end before invoking
`%cadence_autoregister`. If a referenced variable isn't defined, you
get a clear error pointing at which cell and which variable.

**Common notebook shapes and what happens:**

| Shape | Outcome |
|---|---|
| Heading → markdown explanation → solution cell → heading → solution cell ... | Clean pairing in auto mode; one exercise per heading. |
| Multiple solution cells under one heading | Only the **first** code cell under each heading becomes the exercise; the rest are treated as setup (copied verbatim). Add explicit `# cadence:checkpoint` markers if you want each one to be a separate checkpoint. |
| Code cells without any preceding heading | Treated as setup, copied verbatim. Most often this is imports, helper functions, or data loading — exactly the right outcome. |
| Lots of cells with no clear heading structure | Auto mode will find few or no exercises and emit *"⚠ Found no exercise cells."* Drop `# cadence:checkpoint <id>` markers on the cells you want, and re-run. Manual mode doesn't need any heading at all. |
| A "Setup" or "Imports" section under a heading | Auto-mode silently treats it as setup because the value isn't a primitive (a Generator / DataFrame / module). No special syntax needed. |
| Exercise that should be free-text (a reflection) | Mark explicitly: `# cadence:checkpoint reflect manual`. Autoregister skips value extraction and registers as `manual`. |

**Validating the result.** The card autoregister prints lists every
detected checkpoint with its inferred id / comparator / expected. Read
it before opening the registered notebook — if anything looks wrong
(an id slugged oddly, a comparator inferred the wrong way), the fix is
usually one explicit `# cadence:checkpoint <id> [<comparator>]` marker
on the offending cell. Re-running autoregister is cheap and
idempotent.

### The marker toolkit

All markers are **comments** (so they're inert at runtime — Cadence just
reads them when scaffolding). They label *what a cell is* for tooling;
magics (`%cadence_*`) are what *do* something. The set you can reach for:

| Marker | Where | What it does |
|---|---|---|
| `# cadence:checkpoint <id> [<comparator>]` | Top of a code cell | Marks this cell as exercise `<id>`. Optional second word overrides the inferred comparator (e.g. `manual`, `exact`). |
| `<!-- cadence:task [<id>] -->` | Markdown cell | Marks the markdown as task prose. If an id is given, the next code cell becomes the exercise stub for that id (and `# cadence:checkpoint` isn't needed). |
| `# cadence:hint: <text>` | Inside an exercise cell | Becomes the hint for that checkpoint. Markdown allowed — backticks, code fences, `**bold**`. |
| `# cadence:starter` … `# cadence:end` | Inside an exercise code cell | The region between becomes the student stub body (instead of `# Your code here`). Good for multi-step problems. Anything outside the markers is treated as the teacher's reference and stripped. |
| `# cadence:solution` | Top of a code cell | Copy this code cell verbatim into the student notebook. Use for shared setup, an explainer snippet, or a worked solution you want students to see. |
| `# cadence:hide` … `# cadence:end` | Inside a code cell | The region between is stripped from **both** the registered teacher notebook and the student notebook — purely teacher-side authoring notes. |
| `<!-- cadence:hide -->` … `<!-- cadence:end -->` | Inside a markdown cell | Same — strips a private aside from inside an otherwise-public markdown cell (e.g. "this trips up students because…" inside an exercise description). |

The "ad hoc content for students" cases all fall out of this toolkit:

- **Extra code only the student sees** → put it in its own cell, top-tag it `# cadence:solution`.
- **Extra prose only the student sees** → markdown cell with `<!-- cadence:task -->` (no id needed) or just a heading.
- **Stuff only the *teacher* sees** → wrap in `cadence:hide` (in either code or markdown).
- **Starter code inside an exercise stub** → wrap your scaffolded structure in `cadence:starter` / `cadence:end`.

### Alternative registration paths

`%cadence_autoregister` is the recommended path. The original mechanisms
all still work, in case one of them fits your workflow better:

- **YAML in a cell** — `%%cadence_register_yaml` followed by a YAML list
  of checkpoints. Good when you want to type expected values explicitly
  rather than have them inferred from kernel state, or when you have no
  obvious "answer variable" to extract:

  ```python
  %%cadence_register_yaml
  - id: setup.mean-value
    comparator: numeric
    expected: {value: 49.5, tolerance: 0.001}
    hint: "average of 0..99"
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

- **YAML in a file** — `%cadence_register_yaml_file checkpoints/week3.yaml`.
  Use when checkpoint definitions belong in version control alongside the
  notebook (PR-reviewable rubric changes; many notebooks sharing one
  rubric).

- **Inline per-checkpoint** — `%cadence_register <id> --comparator … --expected …`.
  Useful for quick fixes mid-class or one-checkpoint demos. The full
  flag set:

  ```python
  %cadence_register fib-10 \
      --comparator numeric \
      --expected '{"value": 55, "tolerance": 0.001}' \
      --hint "Remember: fib(0)=0, fib(1)=1." \
      --reveal-after 3 \
      --solution-value "55" \
      --order 2
  ```

- **Python API** — `cadence.api.CadenceAPI().register_checkpoint(...)`.
  Use when generating checkpoints programmatically (per-student randomized
  variants; CI lesson-prep scripts).

Comparators across all forms:

| Comparator | `--expected` / `expected:` | Match rule |
|---|---|---|
| `exact` | `'"hello"'` or `{value: "hello"}` | `str(submitted).strip() == str(value).strip()` |
| `numeric` | `{value: 55}` or `{value: 3.14, tolerance: 0.001}` | `abs(submitted - value) <= tolerance` |
| `set` | `{value: [1, 2, 3]}` | `set(submitted) == set(value)` (order-independent) |
| `regex` | `{pattern: "^[A-Z].*"}` | `re.match(pattern, str(submitted))` |
| `manual` | (none) | Student self-attests with `mark_done("id")` |

### Creating courses

`%cadence_autoregister`'s third prompt covers the common case (attach this
lesson to a course, or create a new one). If you'd rather do it explicitly:

```python
%load_ext cadence
%cadence_login                    # required for courses

%cadence_create_course "Fall 2026 Statistics"
%cadence_add_notebook "Week 1 — Variables"
%cadence_add_notebook "Week 2 — Distributions"
```

`%cadence_add_notebook` creates a fresh lesson inside the active course
and inherits the course's retention. To pull in a lesson you already
created standalone, use
`%cadence_attach_lesson "My Lesson" --to "Fall 2026 Statistics"`.

### Generating the student notebook (`%cadence_scaffold`)

If you used `%cadence_autoregister`, the generated registered notebook
already has a `%cadence_scaffold` cell at the bottom — running it
produces the student version. You can also run scaffold directly on any
notebook with the marker toolkit applied:

```python
%cadence_scaffold                    # auto-detects the current notebook
%cadence_scaffold teacher.ipynb      # or pass it explicitly
```

Or from the shell:

```bash
cadence-cli scaffold teacher.ipynb
```

Auto-detection works in VSCode's Jupyter extension and in JupyterLab /
classic Notebook served by `jupyter_server` ≥ 2. If it can't figure out
the path, you'll see a clear error asking you to pass it.

The output `<teacher>_student.ipynb` contains:

1. A boxed welcome panel summarising the student-side API (`check`,
   `submit_image`, `mark_done`, `show_hint`, `show_solution`).
2. A `%load_ext cadence` + `%cadence_session <code> "your name"` header,
   join code auto-filled from `~/.cadence/lessons.yaml`.
3. All markdowns with `<!-- cadence:task -->` or a heading, copied
   through (so section structure is preserved).
4. One stub per exercise — placeholder body plus `check("id", ...)`.
   Override the placeholder with a `# cadence:starter` block.
5. Any code cell tagged `# cadence:solution`, copied verbatim.
6. **Nothing inside any `cadence:hide` block** — those are teacher-only.

Pass `--join-code <code>` to override the lookup, `--out path` for a
custom path, or `--force` to overwrite an existing student notebook.

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

**Generate the student notebook from a teacher notebook.** Same logic as
`%cadence_scaffold` (see [above](#generating-the-student-notebook-from-yours))
but runnable from the shell — handy in CI or when prepping multiple lessons
at once:

```bash
cadence-cli scaffold teacher.ipynb                     # writes ./teacher_student.ipynb
cadence-cli scaffold teacher.ipynb --out wk3.ipynb     # custom output path
cadence-cli scaffold teacher.ipynb --join-code abc-def # override the cached lookup
cadence-cli scaffold teacher.ipynb --force             # overwrite
```

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
