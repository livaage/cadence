# Changelog

Versions follow [Semantic Versioning](https://semver.org/). Entries are
added top-of-file as work lands; the version header gets stamped when the
release is actually cut + uploaded to PyPI.

## Unreleased

## 0.2.12 — 2026-05-26

### Fixed
- **No more `Unrecognised runtime 'X'; defaulting to 'python3'`** on
  Colab / Kaggle when the teacher authored locally with a named conda
  / pyenv kernel. Autoregister and scaffold now force a portable
  `python3` kernelspec on the generated registered + student notebooks
  instead of copying the teacher's local kernel name. Teachers can
  still rename the kernel after download if they need a specific
  environment.
- **Grey body text in the student "Before you join" privacy notice and
  several other non-cream cards** (light-blue info cards, pink error
  cards, white empty-state cards) — my 0.2.10 cream/mint sweep didn't
  catch these. All `<div style="…background:…">` wrappers without an
  explicit text colour now declare `color: #1f2937` so child text
  doesn't inherit Jupyter's default grey.

### Changed
- **Demo notebook intro spells out the three-notebook flow** —
  `teacher.ipynb` (what you author) → `teacher_registered.ipynb`
  (canonical "what's registered" snapshot you can commit to git) →
  `teacher_registered_student.ipynb` (the deliverable students get).
  Each file has a single, clear lifetime — re-running autoregister
  regenerates the latter two without ambiguity.

## 0.2.11 — 2026-05-26

### Fixed
- **Pip-install line no longer duplicates in the registered notebook.**
  0.2.7 added pip-install propagation (prepending the teacher's
  `%pip install ...` lines as a fresh cell at the top of the
  registered notebook), but didn't strip those same lines from the
  teacher's original cells when they were copied through — so the
  registered notebook ended up with the pip install twice.
- **`%load_ext cadence` no longer disappears from the registered
  notebook when pip-install propagation is active.** Same root cause:
  `_post_process_cells` was treating `cells[0]` as the structural
  setup cell (leave-alone), but with a pip cell prepended the setup
  cell sits at `cells[1]` — so `%load_ext cadence` got stripped from
  the setup cell, and the registered notebook couldn't load the
  extension on Run All. Now `_post_process_cells` takes an
  `n_structural` arg and leaves the leading pip + setup cells alone,
  while stripping stray `%load_ext cadence` and `%pip install` lines
  from everything downstream.

## 0.2.10 — 2026-05-26

### Added
- **`# cadence:given` / `# cadence:end` block marker.** Code inside the
  block runs normally in the teacher kernel (no input-transformer
  comment-out, unlike `cadence:starter`) AND gets copied verbatim into
  the student notebook above the starter stub. Closes the gap where
  setup data the student needs (loaded arrays, RNG draws, problem
  inputs) was either trapped inside the teacher's reference solution
  (so never reached students) or stuck inside a `cadence:starter` block
  (so couldn't execute in the teacher's kernel for autoregister to
  read the answer from). The student exercise cell now layers cleanly:
  `Given:` block → `Your code here` (or the `starter` stub) →
  `check("id", ...)`.

### Changed
- **Muted-text contrast bump on every cream / mint / off-white card.**
  Slate-600 (`#475569`) → slate-700 (`#334155`) for every "muted" caption
  (lesson card footers, "Other commands:", autoregister/scaffold result
  detail rows, etc.). Also added explicit `color: #1f2937` to every
  card whose outer wrapper was previously inheriting text colour from
  Jupyter's default — on some themes that fallback was a grey close to
  the cream background, which the user reported as hard to read.

## 0.2.9 — 2026-05-26

### Fixed
- **`%cadence_register` no longer chokes on apostrophes / regex literals /
  embedded quotes in `--solution-code`.** 0.2.8 JSON-encoded the value
  and POSIX-shell-quoted it, which works in isolated `shlex.split` but
  breaks somewhere in the .ipynb-storage → IPython-input-pipeline →
  `magic_arguments` chain on real notebooks. Common failure case: a
  teacher's reference solution containing `re.match('e', 'the quick
  brown fox')` or a line like `# teacher's reference` produced a
  `UsageError: unrecognized arguments` when the registered notebook
  ran. Switched to **base64 with a `b64:` prefix** — the payload is
  pure `[A-Za-z0-9+/=]` so no parser at any layer of the chain can
  mis-interpret it. The `cadence_register` magic detects the prefix
  and decodes; hand-written single-line `--solution-code` without the
  prefix continues to pass through unchanged, and 0.2.8's JSON-encoded
  form is still soft-decoded for back-compat.

## 0.2.8 — 2026-05-26

### Changed
- **Solutions are now auto-revealed by default.** Previously
  `%cadence_autoregister` left solutions off unless the teacher
  explicitly answered `yes` at the prompt. Now the default flips:
  the teacher's reference code in each exercise cell becomes the
  `--solution-code` payload, and students unlock it after the global
  default of 3 wrong attempts. The interactive prompt now reads
  "Auto-reveal solutions after N wrong attempts? [empty=default 3,
  0=disable, n=disable]".
- **`--solution-code` values are JSON-encoded** when emitted by
  autoregister so multi-line teacher solutions survive the
  single-line IPython magic constraint. `%cadence_register` soft-
  decodes JSON-encoded values (parses as JSON string → uses decoded;
  otherwise uses raw). Hand-written single-line `--solution-code`
  continues to work unchanged.

### Added
- **`--no-solutions` CLI flag** on `%cadence_autoregister` — global
  opt-out, suppresses every solution payload notebook-wide. Equivalent
  to `--reveal-after 0` or answering `0`/`n` at the prompt.
- **`# cadence:no-solution`** per-cell marker. Drop it into any
  exercise cell and that one checkpoint gets no solution payload
  even when global reveals are on. For the questions where the
  answer is short enough that revealing it gives the whole exercise
  away.
- **`# cadence:reveal-after N`** per-cell marker. Overrides the
  global reveal-after-attempts value for one checkpoint. Use for
  a harder exercise that should wait longer before unlocking.
- **`# cadence:hint-after N`** per-cell marker. Same idea, for the
  hint-unlock threshold (default 1).
- **Solution-code extraction strips the starter block.** When a cell
  has `# cadence:starter` / `# cadence:end`, the code captured as
  `--solution-code` is the teacher's reference *below* `# cadence:end`,
  with the student stub removed. Students see the worked answer when
  they unlock, not their own placeholders.

## 0.2.7 — 2026-05-25

### Added
- **Pip-install propagation.** `%pip install` / `!pip install` lines in
  the teacher's source notebook are now scanned out and prepended as
  the first code cell of both the generated registered notebook and the
  student notebook. Without this, a teacher on Colab/Kaggle who runs
  `%pip install cadence-edu` in their authoring notebook would download
  a registered/student notebook that hits `%load_ext cadence` →
  `ModuleNotFoundError` on its first run (the downloaded file lands in
  a fresh kernel with no cadence-edu). Lines are deduped in first-seen
  order; only `%pip install` and `!pip install` are carried — conda
  invocations are skipped for now.

### Changed
- Bumped muted-caption colour from slate-500 (`#64748b`) to slate-600
  (`#475569`) across every magic-output card. On the cream / mint card
  backgrounds we use for success and warning cards (`#f0fdf4`,
  `#fffbeb`, `#fafafa`), slate-500 sat at ~4.5:1 contrast — borderline
  WCAG AA, hard to read on lower-end laptop screens. Slate-600 sits at
  ~6:1 on the same backgrounds.

## 0.2.6 — 2026-05-25

### Fixed
- **Upload-widget fallback now preserves the original magic args.**
  Previously: `%cadence_autoregister --all --force` on Kaggle fell to
  the widget, and re-running after upload dropped the flags — auto
  mode never engaged, only manually-marked checkpoints registered.
  Now the widget's upload callback immediately re-invokes the magic
  with the user's original `line` (via `shell.run_line_magic`), so
  `--all` / `--force` / `--reveal-after N` carry through verbatim.
- **Kaggle: dropped the dead path-based detection.** The file at
  `/kaggle/working/.virtual_documents/__notebook_source__.ipynb` looked
  promising but is actually JupyterLab's flat Python-source extraction
  (the LSP virtual document) — no JSON, no markdown cells, unusable
  for autoregister. Kaggle now goes straight to the upload widget,
  which is the correct UX (Kaggle doesn't expose the running notebook
  to the kernel filesystem at all).

### Added
- **`FileLink` download handle after `%cadence_autoregister` and
  `%cadence_scaffold`** — clickable across every Jupyter platform.
  Closes the "no easy way to open the generated file" gap on Colab
  and Kaggle, where the file sidebar doesn't double-click-open
  arbitrary `.ipynb` files as new notebooks.
- **Colab: also calls `google.colab.files.download(out_path)`** to
  trigger a real browser save, on top of the FileLink. The teacher
  gets the file in their Downloads folder without extra clicks.
- **Kaggle-tailored upload-widget copy.** When `KAGGLE_KERNEL_RUN_TYPE`
  is set the widget now explicitly walks the teacher through
  `File → Download Notebook (.ipynb)` and notes that the same magic
  will resume automatically after the upload.

## 0.2.5 — 2026-05-25

### Fixed
- Colab `_message.blocking_request("get_ipynb")` returns cell sources as
  JSON list-of-lines (the on-disk form) — `nbformat.from_dict` left
  those as lists, which broke every downstream regex in autoregister
  and scaffold (e.g. `CHECKPOINT_MARKER_RE.search(cell.source)` raised
  `TypeError: expected string or bytes-like object, got 'list'`). Now
  the Colab loader round-trips the dict through `json.dumps` and
  `nbformat.reads(..., as_version=4)` so source-line joining runs
  exactly as it does for an on-disk `.ipynb`, then explicitly calls
  `nbformat.validator.normalize` to inject cell ids (Colab payloads
  routinely arrive without them — nbformat 5+ logs a
  `MissingIDFieldWarning` and may eventually error).

## 0.2.4 — 2026-05-25

(Skipped — same Colab fix as 0.2.5, but without the explicit
`nbformat.validator.normalize` pass; superseded before any wider use.)

## 0.2.3 — 2026-05-25

### Added
- **`cadence:starter` blocks now accept arbitrary free text.** Previously
  the lines between `# cadence:starter` and `# cadence:end` had to be
  valid Python — otherwise the teacher's own `Run All` SyntaxErrored
  before they could even reach `%cadence_autoregister`. The extension
  now registers an IPython input transformer that comments out the
  starter region at execution time, so the kernel never tries to parse
  prose or pseudocode inside it. The on-disk `.ipynb` cell source is
  unchanged, so scaffold still extracts the original starter text into
  the student stub.
- **Auto-detection on Google Colab and Kaggle.** `%cadence_autoregister`
  and `%cadence_scaffold` now find the running notebook on:
  - **Google Colab** — via the frontend bridge
    (`google.colab._message.blocking_request("get_ipynb")`); returns the
    live notebook JSON, no file path needed.
  - **Kaggle** (interactive editing) — via the JupyterLab RTC virtual
    document at `/kaggle/working/.virtual_documents/__notebook_source__.ipynb`,
    gated on the `KAGGLE_KERNEL_RUN_TYPE=Interactive` env var.
  Existing platforms (Jupyter classic, Lab, VSCode, PyCharm, DataSpell)
  continue to be detected by the same `__vsc_ipynb_file__` / env-var /
  `/api/sessions` chain as before.
- **Universal upload-widget fallback.** When detection fails on every
  layer, the magics now render an `ipywidgets.FileUpload` accepting
  `.ipynb` files. The teacher drops their notebook on the widget and
  re-runs the magic; the in-memory notebook flows through scaffold /
  autoregister, writing output to the kernel's CWD with a `FileLink`.
  Works identically on any platform that supports ipywidgets — no
  per-platform fallback strings to maintain.

### Changed
- `scaffold()` and `autoregister()` now accept a pre-parsed
  `nbformat.NotebookNode` via a new `teacher_nb` keyword argument in
  addition to (or instead of) `src_path`. Required for the Colab and
  upload-widget paths, which have no on-disk source. Default output
  filenames fall back to `cadence_registered.ipynb` /
  `cadence_student.ipynb` in CWD when no source path is available.
- New `detect_notebook_source()` returns a `NotebookSource` dataclass
  (`notebook`, optional `path`, `platform` label). The older
  `detect_current_notebook()` remains as a back-compat path-only shim.

## 0.2.2 — 2026-05-24

### Fixed
- **Student notebooks now have explicit imports.** 0.2.1 relied on
  `%load_ext cadence` pushing `check` / `show_hint` / `show_solution` /
  `mark_done` / `submit_image` into the user namespace. That works when
  the freshly-installed cadence module is the one IPython resolves, but
  silently breaks if a stale install is shadowing it (we hit exactly
  this dev-environment quirk locally). The scaffold-generated student
  header now adds an explicit
  `from cadence import check, show_hint, show_solution, mark_done, submit_image`
  line — pythonic, obvious to students reading the cell, and immune to
  loader resolution surprises. The namespace push from 0.2.1 is kept as
  a belt-and-braces fallback so teacher notebooks without the explicit
  import still work.

### Changed
- All user-facing docs and HTML prompts (web Guide, Demo page, Privacy
  page, dashboard tooltips, `%cadence_help` cheatsheet, `CheckResult`
  hint/solution prompts, `submit_image` docstring, student starter
  notebook) now use bare names like `show_hint("id")` instead of the
  mix of `cadence.show_hint("id")` and `from cadence import show_hint`
  that had crept in. Single consistent pattern across the surface.
- `demo-teacher-setup.ipynb` (shipped under `/demo`) trimmed from
  ~1100 words to ~450 words. Dropped the 257-word "rules in 60 seconds"
  reference table (lives in the README) and the "Alternative
  registration paths" section. Multi-paragraph code-cell explainers
  collapsed to single-line comments so the actual `cadence:` markers
  are visible against less prose.

## 0.2.1 — 2026-05-24

### Fixed
- **Student notebooks now actually work.** `%load_ext cadence` was only
  registering magics — it didn't push `check`, `show_hint`,
  `show_solution`, `mark_done`, or `submit_image` into the user namespace.
  Every exercise cell scaffolded by `%cadence_scaffold` calls bare
  `check("id", ...)`, so students would hit `NameError: name 'check' is
  not defined` on their first cell. Now the extension pushes the
  student-side helpers into `ipython.user_ns` at load time (with
  `setdefault`, so an existing user-bound name isn't clobbered).
- Student intro markdown referenced `cadence.show_my_data()` and
  `cadence.delete_my_data()` — neither function exists. Pointed it at
  the actual interface: `%cadence_export_my_data` and
  `%cadence_delete_my_data --yes`.

## 0.2.0 — 2026-05-24

First production release to PyPI. 0.1.x was the TestPyPI iteration line;
0.2.0 collects that work into a single coherent release on real PyPI.

### Highlights since the previous public PyPI version
- **`%cadence_autoregister`** turns a vanilla teaching notebook into a
  Cadence-wired one in one cell — pairs markdown headings with code,
  extracts answer values from the kernel namespace, infers comparators,
  and writes a registered notebook with inline `%cadence_register` lines.
- **`%cadence_scaffold`** generates the student notebook from the
  registered teacher notebook: stubs exercises, keeps imports and helpers,
  fills in the join code, and adds a student intro covering the
  `check` / `submit_image` / `mark_done` / `show_hint` / `show_solution`
  API plus the student data-rights commands.
- **Marker toolkit**: `# cadence:checkpoint`, `# cadence:task`,
  `# cadence:starter` / `# cadence:end`, `# cadence:solution`,
  `# cadence:hide` / `# cadence:end`, `# cadence:hint:`, plus the
  `<!-- cadence:* -->` markdown variants. Documented as a unified table
  in the README.
- **Retention model**: switched from delete-on-expiry to
  de-identify-on-expiry; aggregate dashboards survive the retention
  window. `--retention-days` available on both lesson and course
  creation; course-attach extends a lesson's retention to match.
- **GitHub-OAuth password flow**: OAuth teachers can set a password from
  the web account to unlock `%cadence_login` in Jupyter.
- **Hint markdown**: hints render light markdown (inline code, fenced
  code blocks, bold).
- Quote-stripping fix for `--password "x"` and other flags that used to
  send the literal quoted string.
- Public `/demo` page with notebook walkthroughs and a live demo
  dashboard.

See 0.1.4 – 0.1.20 entries below for the detailed per-bump history.

## 0.1.20 — 2026-05-24

### Changed
- Docs only. New *How autoregister decides — the rules* subsection in
  the README makes the implicit pairing and value-extraction rules
  explicit: which cells become exercises (and when), how the answer is
  read from the kernel namespace (last statement of the cell — bare
  expression evaluated, or named assignment looked up), and a table of
  common notebook shapes mapped to what autoregister will do with each
  one. Also covers the "I have lots of cells and it's not clear what's
  what" case (use manual `# cadence:checkpoint` markers) and how to
  validate the success card before opening the registered notebook.

## 0.1.19 — 2026-05-24

### Added
- **Hide blocks**. `# cadence:hide` / `# cadence:end` in a code cell and
  `<!-- cadence:hide -->` / `<!-- cadence:end -->` in a markdown cell
  delimit a region that gets stripped from **both** the registered
  teacher notebook (via `%cadence_autoregister`) and the student
  notebook (via `%cadence_scaffold`). For the teacher's authoring
  notes that shouldn't end up in front of the class — meta-comments on
  the exercise design, asides about which step trips students up,
  etc. Previously these would either leak into the student version
  (if inside an otherwise-flowing cell) or required restructuring the
  cell to hide them.

### Changed
- README restructured to lead with `%cadence_autoregister` as the
  recommended path, with a new *Alternative registration paths*
  section covering the original YAML / inline / Python entry points.
  Adds a unified **marker toolkit** table covering all the
  `# cadence:*` and `<!-- cadence:* -->` markers in one place, with
  worked examples of the common "ad hoc code/text for students" cases
  (extra student-only code via `# cadence:solution`, extra
  student-only prose via `<!-- cadence:task -->`, teacher-private
  asides via `cadence:hide`).
- Web demo notebook (`demo-teacher-setup.ipynb` shipped under
  `/demo`) rewritten around the autoregister flow as the primary
  path, with the alternatives mentioned briefly at the end.

## 0.1.18 — 2026-05-24

### Added
- **Starter-code blocks** for student scaffolds. Wrap a region of an
  exercise cell in `# cadence:starter` / `# cadence:end` and that region
  becomes the student stub body (instead of the default
  `# Your code here` placeholder), with `check("id", ...)` appended.
  Teachers can put their reference solution outside the markers; it's
  stripped from the student notebook. Good for multi-step problems
  where a blank stub would leave students lost.

### Changed
- Retention prompt in `%cadence_autoregister` now reads
  *"How many days to keep each student's data? (empty = default 7 for
  one-off lesson)"* / *"... (empty = default 90 for course)"* — i.e.
  it states the actual default that empty-input will land on, instead
  of calling it a "recommendation" that the teacher might worry about.
- Student-intro welcome box restyled — soft left-accent stripe instead
  of full border, explicit text colors throughout (slate-800 body,
  navy-900 heading) so it stays legible on both light and dark Jupyter
  themes. Previous version inherited the page text color and washed
  out on darker themes.

## 0.1.17 — 2026-05-24

### Fixed
- Lesson created via `%cadence_add_notebook` (the course path) now
  inherits the course's retention at creation time instead of starting
  at the 7-day default and being silently bumped by the attach step.
  Practical fix: the rendered lesson card and course card no longer
  disagree about how long student data is kept.
- `%cadence_scaffold` now finds the lesson name when the setup cell
  uses `%cadence_add_notebook` (the course path), not just
  `%cadence_(create_)lesson`. Previously, scaffolding a notebook
  generated under a course failed with
  *"Could not auto-detect a join code. No %cadence_create_lesson /
  %cadence_lesson magic found in the notebook."*

### Added
- `%cadence_autoregister` now prompts for **retention** after the
  course-choice prompt, with a sensible default per path (7 days for
  standalone, 90 days for a course). The chosen value is baked into the
  generated setup cell via `--retention-days N` on `%cadence_create_lesson`
  (standalone) or `%cadence_create_course` (new course). The
  existing-course path leaves retention alone — the lesson inherits the
  course's, per the bug fix above.

## 0.1.16 — 2026-05-24

### Changed
- Student-notebook intro is now a **styled HTML box** (border + light
  blue background) so it visually separates from the teacher's prose
  that follows. Plain markdown was easy to confuse with lesson content.
- Section + subsection headings (`## Part A`, `### Setup`, ...) from
  the teacher notebook now **carry through to the student notebook**
  as well. Previously only markdowns explicitly tagged
  `<!-- cadence:task -->` flowed across. The new rule: markdowns with a
  heading OR a task marker reach the student; pure-prose teacher asides
  (no heading, no marker) stay teacher-only.

### Added
- The setup cell produced by `%cadence_autoregister` now includes a
  commented-out `# %cadence_login --username YOUR_USERNAME` line. Teachers
  who want to sign in (e.g. to attach the lesson to a course later) just
  uncomment and fill in the username instead of remembering the syntax.

## 0.1.15 — 2026-05-24

### Added
- Student notebooks generated by `%cadence_scaffold` now start with an
  intro markdown cell that summarises the student-side API in one
  paragraph: `check("id", answer)` for submissions, `submit_image`
  for plots, `mark_done` for free-text reflections, `show_hint` /
  `show_solution` for unstucking, plus a pointer to `cadence.show_my_data`
  / `cadence.delete_my_data` for student data rights.

### Fixed
- `%cadence_autoregister` now marks non-exercise code cells (imports,
  seeded RNGs, helper data) with `# cadence:solution` in the registered
  notebook. Previously those cells were copied to the registered teacher
  notebook but **dropped by scaffold** on the way to the student notebook,
  so students saw exercises referencing `np.arange(...)` with no `import
  numpy as np` in sight. Now they carry through verbatim.

### Behavioural notes
- Heading structure: all markdown cells (`#`, `##`, `###`, ...) flow
  through to the registered teacher notebook. Only markdowns explicitly
  tagged `<!-- cadence:task -->` flow through to the student notebook —
  section / module headings stay teacher-only by design.

## 0.1.14 — 2026-05-24

### Changed
- Autoregister auto-mode is smarter about what counts as an exercise.
  Cells whose value isn't a primitive answer type (numpy `Generator`,
  open files, DataFrames, anything that isn't number / string / bool /
  list / set of those) are now silently treated as setup and copied
  through verbatim, even when they sit under a `## heading`. So a cell
  like `rng = np.random.default_rng(7)` under `## Setup` no longer
  becomes a spurious exercise. Pure-import cells were already skipped;
  this generalizes the rule.
- Subheadings handled: when a markdown cell contains nested headings
  (e.g. `## Part A — Numerics` followed by `### Exercise: mean`), the
  *last* heading wins for the auto-id. Previously the first one won,
  producing too-generic ids like `part-a-numerics` for every exercise
  in the section.
- The generated registered notebook now closes the loop: any
  `%cadence_autoregister` line in the source (typically the cell you
  ran the magic from) is rewritten to `%cadence_scaffold`, and stray
  `%load_ext cadence` lines outside the top setup cell are removed.
  Running "Run All" on the registered notebook now goes
  registrations → student notebook in one pass, no extra steps.

### Added
- `%cadence_autoregister` interactive prompts: after the solutions
  prompt, asks whether to sign in (only if not already signed in), and
  when signed in, asks whether the lesson should be standalone, added
  to an **existing** course, or part of a **new** course. The choice
  is baked into the setup cell of the generated notebook:
  `%cadence_course "..."` + `%cadence_add_notebook "..."` (existing),
  `%cadence_create_course "..."` + `%cadence_add_notebook "..."` (new),
  or plain `%cadence_create_lesson "..."` (standalone).

## 0.1.13 — 2026-05-24

### Changed
- **Autoregister output layout reworked.** Registrations now live
  **inline** at the top of each exercise cell as a `%cadence_register …`
  line, rather than collected in a single `%%cadence_register_yaml` block
  at the top of the notebook. Scanning past an exercise now shows
  `id + comparator + expected` right above the solution code that
  produced them — much friendlier in long notebooks. The top-of-notebook
  setup cell is correspondingly minimal: `%load_ext cadence` +
  `%cadence_create_lesson "..."`.

### Added
- `# cadence:checkpoint <id> <comparator>` — optional second word on the
  marker overrides the auto-inferred comparator. Use `manual` for
  free-text reflections (no value extraction; registers as `manual`); use
  `exact` to force ordered list-matching where `set` would otherwise be
  inferred.

## 0.1.12 — 2026-05-24

### Added
- **`%cadence_autoregister`** — turn a vanilla teaching notebook into a
  Cadence-wired one. Walks the notebook, finds exercise cells (either by
  manual `# cadence:checkpoint <id>` markers or by pairing markdown
  headings with their following code cells in auto mode), reads each
  answer's value from the kernel namespace, infers comparator + expected
  payload from the value type, and writes a new notebook with
  `%cadence_create_lesson` + a pre-filled `%%cadence_register_yaml` block.
  Imports and other setup cells are copied through verbatim — students
  need them too. Pass `--all` to force auto mode even when manual markers
  exist; pass `--reveal-after N` (or `0` for none) to skip the interactive
  solutions prompt.
- `# cadence:hint: <text>` marker — autoregister picks this up and adds
  it as the hint for the checkpoint in the generated YAML.

### Changed
- README now opens its concepts section with an explicit "markers vs
  magics" discipline: comments (`# cadence:...`, `<!-- cadence:... -->`)
  are static metadata that label a cell; magics (`%cadence_...`) are
  actions that do something when run. This rule is what keeps the syntax
  surface coherent as it grows.

## 0.1.11 — 2026-05-24

### Changed
- Hints now render with light markdown — inline backticks become inline
  code, triple-backtick fences become syntax-block code, and `**bold**`
  works. Existing plain-text hints render unchanged. Lets teachers drop
  small code snippets into hints without writing raw HTML:
  ```yaml
  - id: row_sums
    comparator: set
    expected: {value: [6, 22, 38]}
    hint: "use `M.sum(axis=1)` — **axis=1** sums across columns"
  ```

## 0.1.10 — 2026-05-24

### Changed
- **Scaffold no longer requires `check()` calls in the teacher notebook.**
  The previous flow asked teachers to write `check("id", value)` next to
  their reference solution so scaffold could find exercise cells. That
  inverted the mental model — `check()` is the *student's* call, not the
  teacher's. Two new ways to mark a cell as an exercise without writing
  `check()`:
  - `<!-- cadence:task <id> -->` on a markdown cell — the next code cell
    becomes the exercise stub for that checkpoint id. (The bare
    `<!-- cadence:task -->` without an id still works for back-compat.)
  - `# cadence:checkpoint <id>` on its own line in a code cell — that
    code cell becomes the exercise stub. Useful when you don't have a
    paired task markdown.
  The teacher's solution code is dropped from the student version
  regardless; the student gets a `# Your code here` placeholder plus
  `check("<id>", ...)`.
  `check()` in the teacher's cell still works (back-compat) and is
  useful when one cell needs multiple check calls.

## 0.1.9 — 2026-05-24

### Changed
- Retention policy switched from **delete-on-expiry** to **de-identify-on-expiry**.
  When a session passes its retention window, the student's display name is
  cleared and `deidentified_at` is stamped; per-checkpoint aggregate rows
  (attempts, code/image submissions, solution reveals) are kept so the
  teacher's dashboard continues to show solve rates, common wrong answers,
  and timing distributions — they're no longer personal data once the
  link to a named student is broken. To wipe everything immediately, use
  `%cadence_delete_my_data` (student) or `%cadence_delete_lesson "..." --yes`
  (teacher). Requires the matching backend deploy.
- Lesson + course card copy now spells out the de-identification model
  explicitly, the defaults (7 days quick / 90 days course), and the fact
  that **attaching a lesson to a course bumps its retention to the
  course's** (the one place a lesson's retention can be extended).
- Student-side join notice updates the "How long" bullet to mention
  de-identification instead of deletion.

### Added
- Course-attach now auto-extends a notebook's session retention. When you
  run `%cadence_attach_lesson` (or `%cadence_add_notebook` for a fresh
  one), if the course's retention is longer than the lesson's, the lesson
  is bumped up to match. Logged in the audit trail as
  `extend_lesson_retention_via_course_attach`.

## 0.1.8 — 2026-05-24

### Added
- `%cadence_create_lesson "X" --retention-days N` — pick the starting
  retention period (1–365 days) at creation. Previously lessons were
  always created at 7 days with no way to set a longer initial value.
  After creation, retention can still only be shortened (not extended) via
  `%cadence_set_retention` — the chosen value is the upper bound for that
  lesson's life. Matches the existing `--retention-days` flag on
  `%cadence_create_course`. Requires backend with the matching
  `LessonCreate.session_retention_days` field; older backends silently
  ignore the extra field and fall back to the 7-day default.

### Changed
- Lesson + course card retention blurbs now reflect what's actually
  possible: "pass `--retention-days N` on creation to start higher;
  shorten any time" instead of the previous "(extending isn't allowed)"
  which sounded like a hard cap when it was really a defaults-only
  limitation.

## 0.1.7 — 2026-05-24

### Changed
- Lesson + course creation cards in Jupyter output are visually tidier:
  consistent text size, a single muted-text color (slate-600), reduced
  prose. The student snippet stays visible (still a copy-paste target);
  the "Cached in ~/.cadence/lessons.yaml … other commands…" footer is
  smaller and dimmer so it stops competing for attention.
- The pre-login "Signed up with GitHub?" banner that used to appear on
  every `%cadence_login` call (including for password-account users who
  didn't need it) is gone. The hint now only appears in the error
  message after a 401, and it links straight to the password-setting
  page on the web account.
- All muted-grey text in magic output (`#555`, `#666`) is now slate-600
  (`#475569`) for higher contrast on the off-white card backgrounds.

### Fixed
- Quoted arguments are now stripped uniformly across every magic.
  IPython's `magic_arguments` runs `arg_split` in `posix=False` mode and
  preserves outer quote characters, which used to mean `%cadence_login
  --password "x"` sent the literal string `"x"` (3 chars, with quotes)
  to the backend and 401'd as "incorrect username or password". Some
  magics (lesson/course names) already worked around this by manually
  `.strip('"').strip("'")`-ing their values; others (`%cadence_login`,
  `%cadence_register --expected/--hint/--solution-*`, `%cadence_export_my_data
  --path`) didn't, producing a confusing inconsistency where quoting
  worked for one flag and silently broke for another. The strip now
  happens once inside the shared `parse_argstring` helper, so every magic
  accepts both quoted and unquoted forms identically. Unquoted invocations
  are unchanged.

### Added
- `cadence-cli scaffold <teacher.ipynb>` and `%cadence_scaffold` magic:
  auto-generate a student notebook from a teacher's notebook. Picks up
  every `check("id", ...)` call as an exercise (stubs the body, keeps the
  check), copies every markdown cell tagged with `<!-- cadence:task -->`,
  and auto-fills the `%cadence_session` join code from the lesson cached
  in `~/.cadence/lessons.yaml`.
- `%cadence_scaffold` without arguments auto-detects the current notebook
  via VSCode's `__vsc_ipynb_file__`, jupyter_server's `JPY_SESSION_NAME`,
  or a probe of the local server's `/api/sessions`. Falls back to a
  clear error asking for an explicit path when none of those work.
- `# cadence:solution` marker for code cells in the scaffold flow: tagged
  cells are copied verbatim (marker stripped) into the student notebook.
  Use for setup/imports students need, worked reference solutions, or
  anything else you want visible to students. Wins over the implicit
  check-cell stubbing rule when both are present in a cell.

## 0.1.6 — 2026-05-23

Version stamp only; no functional changes vs 0.1.5. Not uploaded to PyPI.

## 0.1.5 — 2026-05-23

### Fixed
- Default `CADENCE_DASHBOARD_URL` / `CADENCE_WEB_URL` fall back to
  `https://cadence-dash.com` instead of `http://localhost:3000`. The
  lesson + course cards rendered by `%cadence_create_lesson` now link
  to the production dashboard out of the box.
- `_copy_button` HTML escapes its JS string after JS-escaping it, so the
  "Copy snippet" button no longer breaks when the snippet contains `"`
  (e.g. the `%cadence_session <code> "your-name"` snippet, which used to
  close the `onclick` attribute mid-string and mangle the lesson card).

## 0.1.4 — 2026-05-23

### Fixed
- `%load_ext cadence` no longer performs a synchronous `GET /` probe on
  load. A transient non-JSON response from the gateway (captive portal,
  corporate proxy, etc.) used to surface as a scary `requests.JSONDecodeError`
  in the load cell *and* wedge `self.api=None` for the rest of the kernel,
  so every magic would say "❌ API not available". Each magic does its own
  network call with a real error message — those are the source of truth.
