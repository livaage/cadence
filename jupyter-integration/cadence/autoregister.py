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
    strip_hide_blocks,
)

# A `# cadence:hint: ...` line in a cell becomes that checkpoint's hint.
HINT_MARKER_RE = re.compile(
    r"^[ \t]*#\s*cadence:hint:\s*(?P<text>.+?)\s*$", re.MULTILINE
)
# Heading line in markdown — used both to slugify into auto-ids and to
# determine "this markdown cell looks like a task description".
HEADING_RE = re.compile(r"^\s*(#+)\s+(.+?)\s*$", re.MULTILINE)
# Default numeric tolerance for floats with no explicit override.
DEFAULT_FLOAT_TOLERANCE = 0.001


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


@dataclass
class AutoregisterResult:
    out_path: Path
    lesson_name: str
    n_checkpoints: int
    n_failed: int
    checkpoints: List[_Candidate] = field(default_factory=list)
    mode: str = "manual"  # "manual" | "auto"


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
        out.append(_Candidate(
            checkpoint_id=m.group("id"),
            comparator_override=m.group("comparator"),
            code_cell_index=i,
            task_cell_index=last_md_idx,
            hint=_extract_hint(cell.source),
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
        out.append(_Candidate(
            checkpoint_id=cid,
            code_cell_index=i,
            task_cell_index=pending_md_idx,
            hint=_extract_hint(cell.source),
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


def _register_line_for(c: _Candidate, reveal_after: Optional[int]) -> str:
    """Render the inline `%cadence_register …` line that goes at the top of
    each detected exercise cell. Lives WITH the solution code so when the
    teacher scrolls past an exercise they see id + comparator + expected in
    context, instead of hunting up to a YAML block."""
    parts = [f"%cadence_register {c.checkpoint_id}",
             f"--comparator {c.comparator}"]
    # `manual` has no expected payload — student self-attests via mark_done.
    if c.comparator != "manual" and c.expected is not None:
        parts.append(f"--expected {_shell_quote_single(json.dumps(c.expected))}")
    if c.hint:
        parts.append(f"--hint {_shell_quote_single(c.hint)}")
    if reveal_after is not None and c.comparator != "manual" and c.value is not None:
        parts.append(f"--reveal-after {reveal_after}")
        sv = c.expected.get("value") if c.expected else c.value
        parts.append(f"--solution-value {_shell_quote_single(str(sv))}")
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


def _post_process_cells(cells: List[Any]) -> List[Any]:
    """Walk the output cells (excluding the very first setup cell) and:
      * strip `%load_ext cadence` lines — the setup cell at the top has it
      * replace `%cadence_autoregister` lines with `%cadence_scaffold` so the
        teacher's "run all cells" loop in the generated notebook ends up
        producing the student notebook in one go
      * drop cells that become empty after stripping

    Then if no cell contains `%cadence_scaffold`, append a fresh cell with it
    so the student-notebook generation step is always wired in."""
    out = [cells[0]]  # setup cell — leave alone
    scaffold_present = False
    for cell in cells[1:]:
        if cell.cell_type != "code":
            out.append(cell)
            continue
        new_lines = []
        for line in cell.source.splitlines():
            stripped = line.strip()
            if stripped == "%load_ext cadence":
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
    src_path: Path,
    user_ns: Dict[str, Any],
    *,
    lesson_name: Optional[str] = None,
    out_path: Optional[Path] = None,
    reveal_after_attempts: Optional[int] = None,
    force_all: bool = False,
    course_choice: Optional[Tuple[str, str]] = None,
    retention_days: Optional[int] = None,
) -> AutoregisterResult:
    """Generate an enriched teacher notebook from a vanilla one. See module
    docstring for the full flow."""
    src_path = Path(src_path)
    if not src_path.exists():
        raise FileNotFoundError(f"Notebook not found: {src_path}")
    teacher_nb = nbf.read(str(src_path), as_version=4)

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
        except ValueError as e:
            cand.error = str(e)

    # Lesson name: explicit > notebook stem.
    if not lesson_name:
        lesson_name = src_path.stem.replace("_", " ").replace("-", " ").strip().title() or "Cadence Lesson"

    # Build the output notebook.
    out_nb = nbf.v4.new_notebook()
    if "kernelspec" in teacher_nb.metadata:
        out_nb.metadata["kernelspec"] = teacher_nb.metadata["kernelspec"]
    if "language_info" in teacher_nb.metadata:
        out_nb.metadata["language_info"] = teacher_nb.metadata["language_info"]

    # Minimal setup cell at the top — registrations now live INLINE with
    # each exercise, not in a single YAML block.
    out_nb.cells.append(_build_setup_cell(lesson_name, course_choice, retention_days))

    # Map cell index → (checkpoint_id, register_line) for injection.
    md_to_id: Dict[int, str] = {}
    code_to_register: Dict[int, str] = {}
    for c in candidates:
        if c.error is not None or c.skipped_silently:
            continue
        if c.task_cell_index is not None:
            md_to_id[c.task_cell_index] = c.checkpoint_id
        code_to_register[c.code_cell_index] = _register_line_for(
            c, reveal_after_attempts
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

    # Post-process: strip stray %load_ext lines, replace %cadence_autoregister
    # with %cadence_scaffold, and inject a scaffold cell if none ended up there.
    out_nb.cells = _post_process_cells(out_nb.cells)

    _changes, out_nb = nbf.validator.normalize(out_nb)
    out_path = Path(out_path) if out_path else src_path.with_name(
        f"{src_path.stem}_registered.ipynb"
    )
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
    )
