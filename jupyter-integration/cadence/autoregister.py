"""Turn a vanilla teacher notebook into a Cadence-wired one.

Given a teacher's normal teaching notebook (markdown + reference solutions),
walk through it, identify the exercise cells, read the answer values out of
the kernel's namespace, and write a new notebook with:

  * a setup cell at the top containing %load_ext, %cadence_create_lesson and
    a %%cadence_register_yaml block listing every detected checkpoint
  * task markers injected on the markdown cells that describe each exercise
  * everything else copied unchanged (imports, setup cells, narrative prose)

Two modes for finding exercise cells:

  * Manual: code cells tagged with `# cadence:checkpoint <id>` are checkpoints.
    Markdown cells immediately above them become the task descriptions.
  * Auto: when no manual markers exist (or --all is passed), every markdown
    cell with a heading + its following code cell are paired as a task +
    exercise. Code cells without a paired markdown are treated as setup
    (imports etc.) and copied verbatim — teachers don't have to mark imports.

The discipline:
  * Markers (`# cadence:checkpoint`, `<!-- cadence:task -->`, etc) are static
    metadata — comments that label what a cell IS.
  * Magics (`%cadence_autoregister`, `%cadence_scaffold`, ...) are actions
    that DO something.
"""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import nbformat as nbf

from .scaffold import (
    CHECKPOINT_MARKER_RE,
    SOLUTION_MARKER_RE,
    TASK_MARKER_RE,
    _extract_pip_install_lines,
    strip_hide_blocks,
)

# A `# cadence:hint <text>` (or back-compat `# cadence:hint: <text>`) line
# in a cell becomes that checkpoint's hint. The optional trailing colon
# matches the original syntax shipped in 0.1.12; the no-colon form is
# the preferred new shape — consistent with every other `# cadence:NAME
# <args>` marker. Regex stays unambiguous against `# cadence:hint-after N`
# because `:?` doesn't match the `-` and `\s+` requires whitespace after.
HINT_MARKER_RE = re.compile(
    r"^[ \t]*#\s*cadence:hint:?\s+(?P<text>.+?)\s*$", re.MULTILINE
)
# Per-cell opt-out of the default solution reveal. When present, this
# specific checkpoint gets no `--solution-code` / `--solution-value` /
# `--reveal-after` even when global reveals are on. Use sparingly — best
# when the answer is short enough that revealing it is basically giving
# the question away.
NO_SOLUTION_MARKER_RE = re.compile(
    r"^[ \t]*#\s*cadence:no-solution\s*$", re.MULTILINE
)
# Per-cell override of the global `--reveal-after-attempts` value.
# `# cadence:reveal-after 5` makes solutions unlock after 5 wrong tries
# on this checkpoint specifically. 0 = never reveal for this cell.
REVEAL_AFTER_MARKER_RE = re.compile(
    r"^[ \t]*#\s*cadence:reveal-after\s+(?P<n>\d+)\s*$", re.MULTILINE
)
# Per-cell override of the hint-unlock threshold (number of wrong
# attempts before the hint becomes available). Default is 1.
HINT_AFTER_MARKER_RE = re.compile(
    r"^[ \t]*#\s*cadence:hint-after\s+(?P<n>\d+)\s*$", re.MULTILINE
)
# Region pair used by scaffold to scaffold the student stub. We strip it
# from the teacher's reference solution before sending the rest as
# `--solution-code` — the student stub is what the student already has,
# the reveal should show them the teacher's actual answer.
_STARTER_REGION_RE = re.compile(
    r"^[ \t]*#\s*cadence:starter\s*$(?:\n.*?)*?^[ \t]*#\s*cadence:end\s*$\n?",
    re.MULTILINE,
)
# Any line starting with `# cadence:` (after optional whitespace) — used
# to clean cadence-specific markers out of the solution code so it reads
# like vanilla Python to students. Doesn't touch `<!-- cadence:* -->`
# (those only appear in markdown cells, not code).
_CADENCE_MARKER_LINE_RE = re.compile(
    r"^[ \t]*#\s*cadence:[^\n]*\n?", re.MULTILINE
)
# Heading line in markdown — used both to slugify into auto-ids and to
# determine "this markdown cell looks like a task description".
HEADING_RE = re.compile(r"^\s*(#+)\s+(.+?)\s*$", re.MULTILINE)
# Default numeric tolerance for floats with no explicit override.
DEFAULT_FLOAT_TOLERANCE = 0.001
# When solutions are on globally and the teacher didn't pass an explicit
# `--reveal-after N`, this is the number of wrong attempts students need
# before the worked solution unlocks.
DEFAULT_REVEAL_AFTER_ATTEMPTS = 3
# Default number of wrong attempts before the hint button appears. Set
# to 2 so students always get one try on their own before a nudge — 1
# was too eager (button flashes up on the very first wrong attempt,
# before the student has had a chance to reread).
DEFAULT_HINT_AFTER_ATTEMPTS = 2


@dataclass
class _Candidate:
    """One exercise we detected in the teacher notebook."""
    checkpoint_id: str
    code_cell_index: int  # index in teacher_nb.cells
    task_cell_index: Optional[int]  # index of paired markdown, if any
    hint: Optional[str] = None
    value: Any = None
    comparator: Optional[str] = None
    expected: Optional[Dict[str, Any]] = None
    error: Optional[str] = None  # populated if value extraction failed
    # When the teacher writes `# cadence:checkpoint <id> manual` (or any
    # other comparator), we honor that and skip auto-inference.
    comparator_override: Optional[str] = None
    # True when the auto-mode scan picked this cell up because it sits under
    # a heading, but the extracted value isn't a sensible exercise answer
    # (e.g. a numpy Generator or DataFrame). Such cells are silently dropped
    # from the output — they're treated as setup and copied through verbatim
    # rather than being reported as errors.
    skipped_silently: bool = False
    # Per-cell `# cadence:no-solution` opt-out. Takes precedence over the
    # global solutions-on default.
    no_solution_local: bool = False
    # Per-cell `# cadence:reveal-after N` / `# cadence:hint-after N`
    # overrides. None means "use the global default".
    reveal_after_local: Optional[int] = None
    hint_after_local: Optional[int] = None
    # Cleaned teacher source for this checkpoint — starter block + all
    # cadence markers stripped — used as the `--solution-code` payload
    # students see when they unlock the solution.
    solution_code: Optional[str] = None


@dataclass
class AutoregisterResult:
    out_path: Path
    lesson_name: str
    n_checkpoints: int
    n_failed: int
    checkpoints: List[_Candidate] = field(default_factory=list)
    mode: str = "manual"  # "manual" | "auto"
    # Non-fatal advisories surfaced in the autoregister success card. Lists
    # things like "hint unlocks at the same time as the solution" — registered
    # successfully but probably not what the teacher intended.
    warnings: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Value extraction
# ---------------------------------------------------------------------------

def _strip_magic_lines(source: str) -> str:
    """Drop %magic and !shell lines so `ast.parse` succeeds on the cell body."""
    return "\n".join(
        line for line in source.splitlines()
        if not line.lstrip().startswith(("%", "!"))
    )


def _is_pure_imports(source: str) -> bool:
    """True if the cell only contains import statements (and blanks/comments)."""
    try:
        tree = ast.parse(_strip_magic_lines(source))
    except SyntaxError:
        return False
    if not tree.body:
        return False
    return all(isinstance(node, (ast.Import, ast.ImportFrom)) for node in tree.body)


def _is_magic_only(source: str) -> bool:
    """True if the cell is just %magic / !shell commands and blanks."""
    return all(
        (not line.strip())
        or line.lstrip().startswith(("%", "!", "#"))
        for line in source.splitlines()
    )


def _extract_target_value(source: str, user_ns: Dict[str, Any]) -> Any:
    """Find the cell's answer value by inspecting the last meaningful statement
    and reading from the kernel's user namespace.

    Last statement is either:
      * a bare expression (Jupyter display style — `arr.mean()` at end of cell)
        → evaluate it against user_ns
      * an assignment (`mean_value = arr.mean()`) → look up the target name in
        user_ns

    Raises ValueError with a teacher-friendly message if extraction fails."""
    cleaned = _strip_magic_lines(source)
    try:
        tree = ast.parse(cleaned)
    except SyntaxError as e:
        raise ValueError(f"syntax error in cell: {e}")
    if not tree.body:
        raise ValueError("cell has no executable code")

    # Walk past trailing import-only statements — common pattern is
    # `from foo import bar; bar(...)`.
    last = tree.body[-1]

    if isinstance(last, ast.Expr):
        try:
            return eval(
                compile(ast.Expression(body=last.value), "<cadence:cell>", "eval"),
                user_ns,
            )
        except Exception as e:
            raise ValueError(
                f"couldn't evaluate the cell's final expression: {e}. "
                "Make sure you've run the cell (and the cells before it) in this kernel."
            )

    if isinstance(last, ast.Assign):
        target = last.targets[0]
        if isinstance(target, ast.Name):
            name = target.id
            if name not in user_ns:
                raise ValueError(
                    f"`{name}` isn't defined in this kernel yet — run the cell "
                    f"first so autoregister can read its value."
                )
            return user_ns[name]
        if isinstance(target, ast.Tuple):
            # `a, b = ...` — take the whole tuple from user_ns where possible.
            names = [t.id for t in target.elts if isinstance(t, ast.Name)]
            if names and all(n in user_ns for n in names):
                return tuple(user_ns[n] for n in names)
        raise ValueError(
            f"unsupported assignment target type {type(target).__name__}; "
            f"use a simple `name = expression` form."
        )

    if isinstance(last, ast.AugAssign):  # e.g. `total += 1`
        target = last.target
        if isinstance(target, ast.Name) and target.id in user_ns:
            return user_ns[target.id]

    raise ValueError(
        f"can't tell what the answer is for this cell (last statement is "
        f"{type(last).__name__}). End the cell with the answer expression "
        f"on its own line, or assign it to a named variable."
    )


# ---------------------------------------------------------------------------
# Comparator inference
# ---------------------------------------------------------------------------

def _coerce_numpy(value: Any) -> Any:
    """Turn numpy scalars/arrays into native Python equivalents so json.dumps
    works and the comparator inference sees a normal type."""
    try:
        import numpy as np
    except ImportError:
        return value
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    return value


def _is_answer_type(value: Any) -> bool:
    """True if `value` looks like an exercise answer (primitive or container
    of primitives), not a setup-time object like a numpy Generator, an open
    file, a DataFrame, or a Module. Used in auto mode to silently skip
    cells like `rng = np.random.default_rng(7)` even when they appear under
    a heading."""
    value = _coerce_numpy(value)
    if isinstance(value, (bool, int, float, str)):
        return True
    if isinstance(value, (list, tuple, set)):
        return all(_is_answer_type(x) for x in value)
    return False


def _infer_comparator(value: Any) -> Tuple[str, Dict[str, Any]]:
    """Return (comparator, expected_payload_dict) for a Python value.
    `bool` is checked BEFORE `int` because bool is a subclass of int."""
    value = _coerce_numpy(value)
    if isinstance(value, bool):
        return "exact", {"value": value}
    if isinstance(value, int):
        return "numeric", {"value": value, "tolerance": DEFAULT_FLOAT_TOLERANCE}
    if isinstance(value, float):
        return "numeric", {"value": value, "tolerance": DEFAULT_FLOAT_TOLERANCE}
    if isinstance(value, str):
        return "exact", {"value": value}
    if isinstance(value, (list, tuple)):
        # Coerce nested numpy values too — common for arr.tolist() outputs.
        items = [_coerce_numpy(x) for x in value]
        return "set", {"value": items}
    if isinstance(value, set):
        items = sorted(value) if all(isinstance(x, (int, float, str)) for x in value) else list(value)
        return "set", {"value": items}
    # Fallback: stringify.
    return "exact", {"value": str(value)}


# ---------------------------------------------------------------------------
# Slug / id generation for auto mode
# ---------------------------------------------------------------------------

def _slugify(text: str, fallback: str) -> str:
    """`## Exercise 1: Find the mean` → `exercise-1-find-the-mean`. Used to
    derive checkpoint ids from markdown headings in auto mode."""
    text = text.strip()
    text = re.sub(r"[^\w\s.-]+", "", text).lower()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or fallback


def _heading_text(markdown_source: str) -> Optional[str]:
    """Return the LAST heading line in the cell — when teachers nest
    headings like `## Part A` followed by `### Exercise 1` in the same
    markdown cell, the deepest/most-specific one is what we want for the
    auto-id. Falls back to None if the cell has no headings."""
    matches = HEADING_RE.findall(markdown_source)
    if not matches:
        return None
    _, text = matches[-1]
    return text


# ---------------------------------------------------------------------------
# Hint extraction
# ---------------------------------------------------------------------------

def _extract_hint(source: str) -> Optional[str]:
    m = HINT_MARKER_RE.search(source)
    if m:
        return m.group("text").strip()
    return None


# ---------------------------------------------------------------------------
# Cell scanning — manual vs auto
# ---------------------------------------------------------------------------

def _read_per_cell_overrides(source: str) -> Dict[str, Any]:
    """Pull the per-cell `# cadence:no-solution` / `:reveal-after N` /
    `:hint-after N` markers out of a cell's source, returning a dict of
    optional overrides for the _Candidate fields."""
    overrides: Dict[str, Any] = {
        "no_solution_local": bool(NO_SOLUTION_MARKER_RE.search(source)),
        "reveal_after_local": None,
        "hint_after_local": None,
    }
    m = REVEAL_AFTER_MARKER_RE.search(source)
    if m:
        overrides["reveal_after_local"] = int(m.group("n"))
    m = HINT_AFTER_MARKER_RE.search(source)
    if m:
        overrides["hint_after_local"] = int(m.group("n"))
    return overrides


def _extract_solution_code(source: str) -> str:
    """Build the `--solution-code` payload from a checkpoint cell's source.

    We strip:
      * the `# cadence:starter` / `# cadence:end` region (that's the student
        stub — students already see it, the reveal should show the teacher's
        actual answer);
      * every `# cadence:*` marker line (checkpoint, hint, reveal-after, etc.
        — those are metadata, not code to teach with).

    Leading and trailing whitespace are collapsed so the snippet renders
    cleanly when the student opens it."""
    # 1. Drop the starter region entirely (block + its bracket markers).
    cleaned = _STARTER_REGION_RE.sub("", source)
    # 2. Drop any remaining stand-alone cadence marker lines.
    cleaned = _CADENCE_MARKER_LINE_RE.sub("", cleaned)
    # 3. Collapse runs of >2 blank lines that the strips can leave behind.
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _scan_manual(cells: List[Any]) -> List[_Candidate]:
    """Find every code cell with `# cadence:checkpoint <id>`. Pair each with
    the most recent preceding markdown cell (used for task-marker injection
    later). The optional second word in the marker is a comparator override
    (`manual`, `exact`, etc.) that wins over auto-inference."""
    out: List[_Candidate] = []
    last_md_idx: Optional[int] = None
    for i, cell in enumerate(cells):
        if cell.cell_type == "markdown":
            last_md_idx = i
            continue
        if cell.cell_type != "code":
            continue
        m = CHECKPOINT_MARKER_RE.search(cell.source)
        if not m:
            continue
        overrides = _read_per_cell_overrides(cell.source)
        out.append(_Candidate(
            checkpoint_id=m.group("id"),
            comparator_override=m.group("comparator"),
            code_cell_index=i,
            task_cell_index=last_md_idx,
            hint=_extract_hint(cell.source),
            **overrides,
        ))
        last_md_idx = None
    return out


def _scan_auto(cells: List[Any]) -> List[_Candidate]:
    """No manual markers — pair each markdown cell (with a heading) with the
    following code cell. Skip imports + magic-only cells; they fall through
    as untouched setup cells in the output."""
    out: List[_Candidate] = []
    pending_md_idx: Optional[int] = None
    used_ids: set = set()
    auto_counter = 0
    for i, cell in enumerate(cells):
        if cell.cell_type == "markdown":
            if HEADING_RE.search(cell.source):
                pending_md_idx = i
            continue
        if cell.cell_type != "code":
            pending_md_idx = None
            continue
        if not cell.source.strip():
            continue
        if _is_pure_imports(cell.source) or _is_magic_only(cell.source):
            # Setup-like — leave it for verbatim copy. Don't claim the pending
            # markdown; the NEXT real code cell might be the actual exercise.
            continue
        if pending_md_idx is None:
            # Code cell with no preceding heading — treat as setup, skip.
            continue
        heading = _heading_text(cells[pending_md_idx].source) or ""
        base = _slugify(heading, fallback=f"exercise.{len(out) + 1}")
        cid = base
        suffix = 2
        while cid in used_ids:
            cid = f"{base}-{suffix}"
            suffix += 1
        used_ids.add(cid)
        overrides = _read_per_cell_overrides(cell.source)
        out.append(_Candidate(
            checkpoint_id=cid,
            code_cell_index=i,
            task_cell_index=pending_md_idx,
            hint=_extract_hint(cell.source),
            **overrides,
        ))
        pending_md_idx = None
        auto_counter += 1
    return out


# ---------------------------------------------------------------------------
# Output notebook construction
# ---------------------------------------------------------------------------

def _shell_quote_single(s: str) -> str:
    """Wrap a string in single quotes for use as a magic argument value,
    escaping any embedded single quotes."""
    return "'" + s.replace("'", "'\\''") + "'"


def _register_line_for(
    c: _Candidate,
    reveal_after: Optional[int],
    *,
    no_solutions: bool = False,
) -> str:
    """Render the inline `%cadence_register …` line that goes at the top of
    each detected exercise cell. Lives WITH the solution code so when the
    teacher scrolls past an exercise they see id + comparator + expected in
    context, instead of hunting up to a YAML block.

    `reveal_after` is the global reveal-after-attempts value. Per-cell
    `# cadence:reveal-after N` / `# cadence:hint-after N` overrides on the
    candidate win over the global value. `no_solutions=True` (the
    `--no-solutions` CLI flag) suppresses solution payloads everywhere;
    `c.no_solution_local=True` (the `# cadence:no-solution` marker)
    suppresses for just this checkpoint.
    """
    parts = [f"%cadence_register {c.checkpoint_id}",
             f"--comparator {c.comparator}"]
    # `manual` has no expected payload — student self-attests via mark_done.
    if c.comparator != "manual" and c.expected is not None:
        parts.append(f"--expected {_shell_quote_single(json.dumps(c.expected))}")
    if c.hint:
        parts.append(f"--hint {_shell_quote_single(c.hint)}")
    # Hint-after threshold: per-cell override wins; otherwise emit the
    # global default so the registered notebook is self-contained (won't
    # silently flip when the package default changes).
    effective_hint_after = (
        c.hint_after_local
        if c.hint_after_local is not None
        else DEFAULT_HINT_AFTER_ATTEMPTS
    )
    if c.hint:  # only emit the flag when there's actually a hint to gate
        parts.append(f"--hint-after-attempts {effective_hint_after}")
    # Resolve effective reveal-after: per-cell wins over global, with the
    # no-solution opt-outs short-circuiting to "off".
    effective_reveal = (
        c.reveal_after_local if c.reveal_after_local is not None else reveal_after
    )
    suppress = no_solutions or c.no_solution_local
    if (
        not suppress
        and effective_reveal is not None
        and effective_reveal > 0
        and c.comparator != "manual"
        and c.value is not None
    ):
        parts.append(f"--reveal-after {effective_reveal}")
        sv = c.expected.get("value") if c.expected else c.value
        parts.append(f"--solution-value {_shell_quote_single(str(sv))}")
        if c.solution_code:
            # Base64-encode the code with a `b64:` prefix. This sidesteps every
            # quoting headache: real Python code has apostrophes (regex literals,
            # docstrings, "teacher's reference") that, even when properly POSIX-
            # escaped (`'\''`), interact badly with the actual chain from .ipynb
            # storage → IPython input pipeline → magic_arguments parser. Base64
            # produces a pure [A-Za-z0-9+/=] payload with no chars the parser
            # could mis-interpret. The receiver strips `b64:` and decodes.
            import base64 as _b64
            encoded = "b64:" + _b64.b64encode(
                c.solution_code.encode("utf-8")
            ).decode("ascii")
            parts.append(f"--solution-code {_shell_quote_single(encoded)}")
    return " ".join(parts)


def _build_setup_cell(
    lesson_name: str,
    course_choice: Optional[Tuple[str, str]] = None,
    retention_days: Optional[int] = None,
) -> Any:
    """Minimal top-of-notebook setup. The registrations have moved inline
    into each exercise cell.

    `course_choice` is one of:
        None                     → standalone lesson, no course magic
        ("existing", "<name>")   → activate an existing course and add this lesson
        ("new", "<name>")        → create a new course and add this lesson

    `retention_days`, if set, becomes `--retention-days N` on either
    `%cadence_create_lesson` (standalone) or `%cadence_create_course`
    (new course). For the existing-course path we leave retention alone:
    the lesson inherits the course's, and the course was already set up
    elsewhere with its own retention.
    """
    retention_arg = f" --retention-days {retention_days}" if retention_days else ""
    lines = [
        "%load_ext cadence",
        "# Optional — uncomment + fill in to sign in (needed for courses,",
        "# optional for standalone lessons):",
        "# %cadence_login --username YOUR_USERNAME",
    ]
    if course_choice is None:
        lines.append(f'%cadence_create_lesson "{lesson_name}"{retention_arg}')
    else:
        kind, course_name = course_choice
        if kind == "existing":
            lines.append(f'%cadence_course "{course_name}"')
        else:
            lines.append(f'%cadence_create_course "{course_name}"{retention_arg}')
        lines.append(f'%cadence_add_notebook "{lesson_name}"')
    return nbf.v4.new_code_cell(source="\n".join(lines))


_PIP_INSTALL_INLINE_RE = re.compile(r"^[ \t]*[%!]pip\s+install\s+")


def _post_process_cells(cells: List[Any], n_structural: int = 1) -> List[Any]:
    """Walk the output cells, skipping the first `n_structural` cells (the
    pip-install cell if present + the setup cell), and:
      * strip `%load_ext cadence` lines — the structural setup cell has it
      * strip `%pip install` / `!pip install` lines — the structural pip
        cell at the top has them; otherwise the teacher's original pip
        cell would duplicate
      * replace `%cadence_autoregister` lines with `%cadence_scaffold` so the
        teacher's "run all cells" loop in the generated notebook ends up
        producing the student notebook in one go
      * drop cells that become empty after stripping

    Then if no cell contains `%cadence_scaffold`, append a fresh cell with it
    so the student-notebook generation step is always wired in."""
    out = list(cells[:n_structural])  # structural cells — leave alone
    scaffold_present = False
    for cell in cells[n_structural:]:
        if cell.cell_type != "code":
            out.append(cell)
            continue
        new_lines = []
        for line in cell.source.splitlines():
            stripped = line.strip()
            if stripped == "%load_ext cadence":
                continue
            if _PIP_INSTALL_INLINE_RE.match(line):
                continue
            if stripped.startswith("%cadence_autoregister"):
                new_lines.append("%cadence_scaffold")
                scaffold_present = True
                continue
            new_lines.append(line)
        new_source = "\n".join(new_lines).strip()
        if new_source:
            out.append(nbf.v4.new_code_cell(source=new_source))
    if not scaffold_present:
        out.append(nbf.v4.new_code_cell(
            source=(
                "# Generate the student notebook from this teacher notebook.\n"
                "%cadence_scaffold"
            )
        ))
    return out


def _ensure_task_marker(md_source: str, checkpoint_id: str) -> str:
    """If the markdown already has a `<!-- cadence:task ... -->` marker, leave
    it. Otherwise inject one with the checkpoint id at the very top."""
    if TASK_MARKER_RE.search(md_source):
        return md_source
    return f"<!-- cadence:task {checkpoint_id} -->\n{md_source}"


def autoregister(
    src_path: Optional[Path] = None,
    user_ns: Optional[Dict[str, Any]] = None,
    *,
    teacher_nb: Any = None,
    lesson_name: Optional[str] = None,
    out_path: Optional[Path] = None,
    reveal_after_attempts: Optional[int] = None,
    no_solutions: bool = False,
    force_all: bool = False,
    course_choice: Optional[Tuple[str, str]] = None,
    retention_days: Optional[int] = None,
) -> AutoregisterResult:
    """Generate an enriched teacher notebook from a vanilla one. See module
    docstring for the full flow.

    Pass `src_path` for the normal on-disk flow, OR `teacher_nb` (a parsed
    `nbformat.NotebookNode`) for callers that already hold the notebook —
    e.g. Colab where the .ipynb has no file path on the VM.

    Solutions are auto-revealed by default. `reveal_after_attempts=None`
    falls back to `DEFAULT_REVEAL_AFTER_ATTEMPTS` (currently 3). Pass
    `no_solutions=True` to suppress every solution payload notebook-wide,
    or drop a `# cadence:no-solution` marker in any cell to suppress for
    that one checkpoint."""
    if user_ns is None:
        user_ns = {}
    if teacher_nb is None:
        if src_path is None:
            raise ValueError("autoregister() requires either src_path or teacher_nb")
        src_path = Path(src_path)
        if not src_path.exists():
            raise FileNotFoundError(f"Notebook not found: {src_path}")
        teacher_nb = nbf.read(str(src_path), as_version=4)
    elif src_path is not None:
        src_path = Path(src_path)

    # Pick a mode.
    candidates = _scan_manual(teacher_nb.cells)
    mode = "manual"
    if force_all or not candidates:
        candidates = _scan_auto(teacher_nb.cells)
        mode = "auto"

    # Extract values + infer comparators.
    seen_ids: Dict[str, int] = {}
    for cand in candidates:
        if cand.checkpoint_id in seen_ids:
            cand.error = (
                f"duplicate checkpoint id `{cand.checkpoint_id}` "
                f"(also at cell {seen_ids[cand.checkpoint_id]})"
            )
            continue
        seen_ids[cand.checkpoint_id] = cand.code_cell_index
        # Manual comparator: register as free-text / self-attestation. No
        # value extraction needed — the teacher's cell is just a prompt.
        if cand.comparator_override == "manual":
            cand.comparator = "manual"
            cand.expected = None
            continue
        try:
            value = _extract_target_value(
                teacher_nb.cells[cand.code_cell_index].source, user_ns
            )
            # Auto mode: if the value is a non-answer type (numpy Generator,
            # DataFrame, open file, etc.), this cell is really setup — drop
            # it silently so it's copied through verbatim rather than stubbed.
            # Manual mode respects the teacher's marker even for odd types.
            if mode == "auto" and cand.comparator_override is None and not _is_answer_type(value):
                cand.skipped_silently = True
                continue
            inferred_comparator, expected = _infer_comparator(value)
            cand.value = value
            # Honor explicit override (e.g. `exact` to force ordered list match),
            # otherwise use the auto-inferred comparator.
            cand.comparator = cand.comparator_override or inferred_comparator
            cand.expected = expected
            # Capture the teacher's reference code as the solution payload.
            # Strips the starter block (that's the student stub) and any
            # `# cadence:*` marker lines, so what we send to `--solution-code`
            # reads like a clean reference answer.
            cand.solution_code = _extract_solution_code(
                teacher_nb.cells[cand.code_cell_index].source
            ) or None
        except ValueError as e:
            cand.error = str(e)

    # Lesson name: explicit > notebook stem (when we have one) > generic fallback.
    if not lesson_name:
        if src_path is not None:
            lesson_name = src_path.stem.replace("_", " ").replace("-", " ").strip().title() or "Cadence Lesson"
        else:
            # Path-less source (Colab / upload): try the notebook's own metadata
            # title, then fall back to a generic name. Teachers can rename the
            # output file freely; lesson_name is only used as a display label.
            meta_title = (teacher_nb.metadata or {}).get("title") if hasattr(teacher_nb, "metadata") else None
            lesson_name = (meta_title or "Cadence Lesson").strip() or "Cadence Lesson"

    # Build the output notebook.
    out_nb = nbf.v4.new_notebook()
    # Force a portable Python 3 kernelspec rather than copying the teacher's
    # local kernel name. Teachers often author in named conda/pyenv kernels
    # (`icmltrend`, `myresearch-py311`, etc.) — copying that name into the
    # registered notebook means anyone who opens the file in Colab/Kaggle
    # gets "Unrecognised runtime 'X'; defaulting to 'python3'". `python3`
    # works everywhere; teachers can still rename it after download if they
    # want to.
    out_nb.metadata["kernelspec"] = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    if "language_info" in teacher_nb.metadata:
        out_nb.metadata["language_info"] = teacher_nb.metadata["language_info"]

    # Carry `%pip install` / `!pip install` lines from the source notebook
    # to the top of the registered output. Teachers on Colab/Kaggle install
    # cadence-edu (and friends) in their authoring notebook; the downloaded
    # registered file opens in a fresh kernel where those packages aren't
    # there yet — without this propagation, `%load_ext cadence` ModuleNotFound's.
    pip_lines = _extract_pip_install_lines(teacher_nb.cells)
    n_structural = 1  # the setup cell
    if pip_lines:
        out_nb.cells.append(nbf.v4.new_code_cell(source="\n".join(pip_lines)))
        n_structural += 1  # +1 for the pip cell now sitting above setup

    # Minimal setup cell — registrations now live INLINE with each exercise,
    # not in a single YAML block. When pip-install lines are also at the top,
    # this sits at index 1; otherwise index 0.
    out_nb.cells.append(_build_setup_cell(lesson_name, course_choice, retention_days))

    # Solutions are on by default — only an explicit `no_solutions=True`
    # or `reveal_after_attempts == 0` turns them off globally.
    effective_reveal = reveal_after_attempts
    if effective_reveal == 0:
        effective_reveal = None
        no_solutions = True
    elif effective_reveal is None and not no_solutions:
        effective_reveal = DEFAULT_REVEAL_AFTER_ATTEMPTS

    # Map cell index → (checkpoint_id, register_line) for injection.
    md_to_id: Dict[int, str] = {}
    code_to_register: Dict[int, str] = {}
    warnings_list: List[str] = []

    # Marker validation: catch two common authoring mistakes that otherwise
    # silently fail (the bad line is treated as a plain comment and the
    # surrounding region just disappears).
    #   1. Wrong prefix: `#candece:given` (typo) — keyword is right, prefix
    #      isn't `cadence`.
    #   2. Unknown keyword: `# cadence:rebeal-after` (typo on the keyword
    #      side) — prefix is right, keyword isn't in our set.
    _KNOWN_MARKERS = {
        "checkpoint", "task", "hint", "hint-after", "reveal-after",
        "no-solution", "starter", "given", "solution", "hide", "end",
    }
    # Match `#PREFIX<SEP>KEYWORD` where SEP is `:` (correct), `_` (a
    # typo — confusion with the magic naming style `%cadence_register`),
    # or `-` (also a typo). We then post-filter:
    #   * `cadence:foo` → check `foo` is a known keyword
    #   * `cadence_foo` / `cadence-foo` → flag the separator if `foo` is
    #     a known keyword
    #   * `candece:foo` (etc) → flag the prefix if `foo` is a known keyword
    _COMMENT_MARKER_RE = re.compile(
        r"^[ \t]*#\s*([A-Za-z][A-Za-z0-9]*)([:_-])([A-Za-z][A-Za-z0-9_-]*)",
        re.MULTILINE,
    )
    seen_warnings: set = set()
    for cell in teacher_nb.cells:
        if getattr(cell, "cell_type", None) != "code":
            continue
        src = getattr(cell, "source", "") or ""
        for m in _COMMENT_MARKER_RE.finditer(src):
            prefix, sep, keyword = m.group(1).lower(), m.group(2), m.group(3).lower()
            line = m.group(0).strip()
            if prefix == "cadence" and sep == ":":
                # Right prefix + right separator — just check the keyword.
                if keyword not in _KNOWN_MARKERS:
                    msg = (
                        f"unknown marker `{line}` — not one of "
                        f"{', '.join(sorted(_KNOWN_MARKERS))}. Treated as a "
                        f"plain comment, so it has no effect."
                    )
                    if msg not in seen_warnings:
                        seen_warnings.add(msg)
                        warnings_list.append(msg)
            elif prefix == "cadence" and keyword in _KNOWN_MARKERS:
                # Right prefix + known keyword but wrong separator (`_` or
                # `-` instead of `:`). Easy to confuse with the magic naming
                # style `%cadence_register`.
                msg = (
                    f"line `{line}` uses `{sep}` between `cadence` and "
                    f"`{keyword}` — markers use a colon, so this should be "
                    f"`# cadence:{keyword}`. As written it's a plain comment "
                    f"and the marker has no effect."
                )
                if msg not in seen_warnings:
                    seen_warnings.add(msg)
                    warnings_list.append(msg)
            elif keyword in _KNOWN_MARKERS and sep == ":":
                # Wrong prefix (typo) but right separator + known keyword.
                msg = (
                    f"line `{line}` looks like a typo'd `# cadence:` marker "
                    f"— did you mean `# cadence:{keyword}`? Typos are treated "
                    f"as plain comments, so the marker has no effect and any "
                    f"region it was meant to delimit will be dropped."
                )
                if msg not in seen_warnings:
                    seen_warnings.add(msg)
                    warnings_list.append(msg)

    for c in candidates:
        if c.error is not None or c.skipped_silently:
            continue
        if c.task_cell_index is not None:
            md_to_id[c.task_cell_index] = c.checkpoint_id
        code_to_register[c.code_cell_index] = _register_line_for(
            c, effective_reveal, no_solutions=no_solutions,
        )
        # Hint-vs-solution advisories.
        sol_threshold = (
            c.reveal_after_local
            if c.reveal_after_local is not None
            else effective_reveal
        )
        sol_suppressed = no_solutions or c.no_solution_local
        sol_active = bool(sol_threshold) and not sol_suppressed
        if c.hint:
            hint_threshold = (
                c.hint_after_local
                if c.hint_after_local is not None
                else DEFAULT_HINT_AFTER_ATTEMPTS
            )
            # Ordering check: hint unlocks at the same or later attempt as
            # the solution → hint is useless. Default is hint=2 / reveal=3
            # so this only fires when the teacher actively raised hint-after
            # or lowered reveal-after.
            if sol_active and hint_threshold >= sol_threshold:
                warnings_list.append(
                    f"checkpoint `{c.checkpoint_id}`: hint unlocks at attempt "
                    f"{hint_threshold} but solution unlocks at attempt {sol_threshold} — "
                    f"the hint won't appear before the solution. Lower "
                    f"`# cadence:hint-after N` to less than {sol_threshold} so students "
                    f"see the hint first."
                )
        elif sol_active:
            # Solution will reveal at attempt N, but no hint exists at all
            # — student gets the answer with no intermediate help. Flag so
            # the teacher knows to add `# cadence:hint <text>` if they want
            # a gentler progression.
            warnings_list.append(
                f"checkpoint `{c.checkpoint_id}`: solution reveals at attempt "
                f"{sol_threshold} but no hint is registered — students go straight "
                f"from wrong → worked solution with nothing in between. Add "
                f"`# cadence:hint <text>` in the same cell for a gentler nudge first."
            )

    for i, cell in enumerate(teacher_nb.cells):
        if cell.cell_type == "markdown":
            # Strip teacher-only `<!-- cadence:hide -->` regions so the
            # registered notebook doesn't carry the teacher's authoring
            # asides into the class-time view.
            source = strip_hide_blocks(cell.source, kind="markdown").strip()
            if not source:
                continue
            if i in md_to_id:
                out_nb.cells.append(nbf.v4.new_markdown_cell(
                    source=_ensure_task_marker(source, md_to_id[i])
                ))
            else:
                out_nb.cells.append(nbf.v4.new_markdown_cell(source=source))
            continue
        if cell.cell_type == "code":
            # Strip hide blocks from code cells too — authoring notes the
            # teacher doesn't want sitting in front of the class.
            stripped = strip_hide_blocks(cell.source, kind="code")
            if not stripped.strip():
                continue
            if i in code_to_register:
                # Inject `%cadence_register …` as the first line of the cell,
                # so when teachers scroll past an exercise the registration
                # sits right above the solution it describes.
                new_source = code_to_register[i] + "\n" + stripped
                out_nb.cells.append(nbf.v4.new_code_cell(source=new_source))
            elif _is_magic_only(stripped) or SOLUTION_MARKER_RE.search(stripped):
                # Magic-only cells (e.g. `%cadence_autoregister`, `%load_ext`)
                # and cells the teacher already tagged stay as-is. Magic-only
                # cells get cleaned up later in _post_process_cells; we don't
                # want to mark them as solution because they shouldn't flow
                # through to the student notebook.
                out_nb.cells.append(nbf.v4.new_code_cell(source=stripped))
            else:
                # Real setup code (imports, seeded RNG, helper data) — the
                # student needs it to run their exercises. Mark as solution
                # so scaffold copies it verbatim into the student notebook
                # instead of dropping it as "unmarked".
                out_nb.cells.append(nbf.v4.new_code_cell(
                    source=f"# cadence:solution\n{stripped}"
                ))
            continue
        out_nb.cells.append(cell)

    # Post-process: strip stray %load_ext + %pip install lines (already at the
    # top), replace %cadence_autoregister with %cadence_scaffold, and inject a
    # scaffold cell if none ended up there. Skip the leading `n_structural`
    # cells (pip + setup) so we don't strip from the ones that need those lines.
    out_nb.cells = _post_process_cells(out_nb.cells, n_structural)

    _changes, out_nb = nbf.validator.normalize(out_nb)
    if out_path is not None:
        out_path = Path(out_path)
    elif src_path is not None:
        out_path = src_path.with_name(f"{src_path.stem}_registered.ipynb")
    else:
        # Path-less source: default to CWD with a fixed name. On Colab CWD
        # is /content; on Kaggle /kaggle/working — both reachable from the
        # platform's file browser, plus the magic prints a FileLink.
        out_path = Path.cwd() / "cadence_registered.ipynb"
    nbf.write(out_nb, str(out_path))

    # Skipped-silently candidates are not "successes" or "failures" — they
    # were never really exercises in the first place. Count them separately
    # for the success summary.
    return AutoregisterResult(
        out_path=out_path,
        lesson_name=lesson_name,
        n_checkpoints=sum(1 for c in candidates if c.error is None and not c.skipped_silently),
        n_failed=sum(1 for c in candidates if c.error is not None),
        checkpoints=candidates,
        mode=mode,
        warnings=warnings_list,
    )
