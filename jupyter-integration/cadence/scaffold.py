"""Generate a student notebook from a teacher's notebook.

Teacher's notebook is the source of truth: markdown cells they mark with the
`<!-- cadence:task -->` comment become student-facing task descriptions, and
code cells that contain `check("id", ...)` calls become exercise stubs (the
solution body is dropped; only the `check` calls remain with placeholders).

Shared by `cadence-cli scaffold` and `%cadence_scaffold`.
"""

from __future__ import annotations

import ast
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import nbformat as nbf

from . import lesson_store

# Task marker on a markdown cell. The id is optional. When present, the
# NEXT code cell becomes an exercise stub for that checkpoint id, even if
# the teacher's cell has no `check(...)` call — the teacher's solution
# code is stripped and the student version gets a `check("<id>", ...)` line
# pointing at the registered checkpoint. Without an id we fall back to
# the older "look for check(...) calls in the cell" behavior (back-compat).
TASK_MARKER_RE = re.compile(
    r"<!--\s*cadence:task(?:\s+(?P<id>[A-Za-z0-9_.\-:]+))?\s*-->",
    re.IGNORECASE,
)
# Markdown cells with a heading (any `#`/`##`/`###...`) carry the section
# structure of the teacher notebook over to the student notebook. Cells
# that are pure prose without a heading and without a task marker are
# treated as teacher-private notes and skipped.
_HEADING_LINE_RE = re.compile(r"^\s*#+\s+\S", re.MULTILINE)
# `# cadence:solution` on its own line in a code cell — flags the cell as
# "show this verbatim to students" (worked solution, setup/imports, reference
# code). Wins over the implicit check-cell stubbing rule.
SOLUTION_MARKER_RE = re.compile(r"^[ \t]*#\s*cadence:solution\s*$", re.MULTILINE)
# Code-cell alternative to the markdown-task pairing: put
# `# cadence:checkpoint <id>` at the top of a code cell to mark THAT cell
# as the exercise. Optional second word overrides the comparator that
# %cadence_autoregister would otherwise infer from the answer value — most
# useful for `manual` (free-text reflections) and `exact` (force ordered
# list comparison instead of set).
CHECKPOINT_MARKER_RE = re.compile(
    r"^[ \t]*#\s*cadence:checkpoint\s+(?P<id>[A-Za-z0-9_.\-:]+)"
    r"(?:\s+(?P<comparator>exact|numeric|set|regex|manual))?\s*$",
    re.MULTILINE,
)
# Starter-code block markers: any lines BETWEEN `# cadence:starter` and
# `# cadence:end` in an exercise cell are copied verbatim into the student
# stub (instead of the default `# Your code here` placeholder), giving
# students a scaffolded starting point for multi-step problems.
_STARTER_START_RE = re.compile(r"^[ \t]*#\s*cadence:starter\s*$", re.MULTILINE)
_STARTER_END_RE = re.compile(r"^[ \t]*#\s*cadence:end\s*$", re.MULTILINE)
# Hide-block markers: regions between these are stripped from BOTH the
# student notebook (via scaffold) and the registered teacher notebook (via
# autoregister) — they're for the teacher's own authoring notes. Code uses
# `# cadence:hide` / `# cadence:end`; markdown uses `<!-- cadence:hide -->`
# / `<!-- cadence:end -->`. `cadence:end` is reused; in markdown there's no
# starter marker to worry about, in code we strip hide blocks before
# extracting starter so the markers don't collide in practice.
_HIDE_CODE_RE = re.compile(
    r"^[ \t]*#\s*cadence:hide\s*$"      # opener line
    r"(?:\n.*?)*?"                        # body
    r"^[ \t]*#\s*cadence:end\s*$\n?",     # closer line
    re.MULTILINE,
)
_HIDE_MD_RE = re.compile(
    r"<!--\s*cadence:hide\s*-->"        # opener
    r".*?"                                # body (any chars including newlines via DOTALL)
    r"<!--\s*cadence:end\s*-->\n?",       # closer
    re.DOTALL | re.IGNORECASE,
)


def strip_hide_blocks(source: str, *, kind: str) -> str:
    """Remove `cadence:hide` ... `cadence:end` regions from a cell source.

    `kind` is "code" or "markdown" — picks the right comment style. Unmatched
    open-markers are left alone (defensive — better to leave a region visible
    than silently swallow the whole cell)."""
    if kind == "code":
        return _HIDE_CODE_RE.sub("", source)
    return _HIDE_MD_RE.sub("", source)

# Matches the three magics that name a lesson at the start of a line:
#   %cadence_create_lesson "Name"
#   %cadence_lesson "Name"
#   %cadence_add_notebook "Name"   (course path — lesson lives under a course)
# The name arg can be quoted or unquoted, and trailing --flag args get trimmed.
_LESSON_MAGIC_RE = re.compile(
    r"^\s*%cadence_(?:create_lesson|lesson|add_notebook)\s+(.+?)\s*$",
    re.MULTILINE,
)


def detect_current_notebook() -> Optional[Path]:
    """Best-effort detection of the currently-running notebook's .ipynb path.

    Returns None if we can't figure it out — the caller should then ask the
    user to pass the path explicitly. Tries three sources in order:

    1. `__vsc_ipynb_file__` in the IPython user namespace. VSCode's Jupyter
       extension sets this to the absolute notebook path; nothing else does.
    2. `JPY_SESSION_NAME` env var. jupyter_server >= 2 sets this to the
       session's relative path inside the server root. We resolve it against
       cwd, then sniff for an `.ipynb` suffix.
    3. Local jupyter_server's `/api/sessions` keyed by the running kernel's
       connection file. Works in classic Notebook + JupyterLab when there's
       a reachable server; fails silently otherwise (no exceptions leak).
    """
    # 1. VSCode
    try:
        from IPython import get_ipython
        ip = get_ipython()
        if ip is not None:
            vsc = ip.user_ns.get("__vsc_ipynb_file__")
            if isinstance(vsc, str) and vsc.endswith(".ipynb"):
                p = Path(vsc)
                if p.exists():
                    return p
    except Exception:
        pass

    # 2. JPY_SESSION_NAME (jupyter_server 2.x+)
    session_name = os.environ.get("JPY_SESSION_NAME", "")
    if session_name.endswith(".ipynb"):
        p = Path(session_name)
        if not p.is_absolute():
            p = Path.cwd() / p
        if p.exists():
            return p

    # 3. Local jupyter_server /api/sessions probe via the kernel's connection file
    try:
        import json
        import ipykernel
        import requests as _requests  # local import — keep top-level deps thin

        conn_file = ipykernel.get_connection_file()
        kernel_id = Path(conn_file).stem.removeprefix("kernel-")

        # Try modern jupyter_server first, then legacy notebook.notebookapp.
        servers = []
        try:
            from jupyter_server.serverapp import list_running_servers
            servers = list(list_running_servers())
        except Exception:
            try:
                from notebook.notebookapp import list_running_servers as _legacy
                servers = list(_legacy())
            except Exception:
                servers = []

        for srv in servers:
            try:
                url = srv["url"].rstrip("/") + "/api/sessions"
                params = {"token": srv.get("token", "")} if srv.get("token") else None
                resp = _requests.get(url, params=params, timeout=2)
                if resp.status_code != 200:
                    continue
                for sess in resp.json():
                    kernel = sess.get("kernel") or {}
                    if kernel.get("id") != kernel_id:
                        continue
                    nb_path = (sess.get("notebook") or {}).get("path") or sess.get("path")
                    if not nb_path or not nb_path.endswith(".ipynb"):
                        continue
                    root = srv.get("root_dir") or srv.get("notebook_dir") or "."
                    p = Path(root) / nb_path
                    if p.exists():
                        return p
            except Exception:
                continue
    except Exception:
        pass

    return None


@dataclass
class ScaffoldResult:
    out_path: Path
    n_tasks: int
    n_exercises: int
    n_solutions: int
    checkpoint_ids: List[str]
    lesson_name: Optional[str]
    join_code: str


def _strip_solution_marker(code: str) -> str:
    """Drop the `# cadence:solution` line(s) and any blank gap they leave."""
    out = SOLUTION_MARKER_RE.sub("", code)
    # Collapse the blank line the removed marker left behind, but only at the
    # top of the cell — preserve intentional blank lines elsewhere.
    while out.startswith("\n"):
        out = out[1:]
    return out


def _extract_check_ids(code: str) -> List[str]:
    """Return every `check("id", ...)` id literal found in the cell.

    Walks the AST so `check` calls inside `if`/`for`/`def` bodies are caught,
    not just top-level statements. Skips calls whose first arg isn't a string
    literal (defensive — those wouldn't make sense as checkpoint ids anyway)."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        # IPython magics (`%foo`) and shell (`!cmd`) lines aren't valid Python
        # to `ast.parse`. Strip them and retry once before giving up.
        cleaned = "\n".join(
            line for line in code.splitlines()
            if not line.lstrip().startswith(("%", "!"))
        )
        try:
            tree = ast.parse(cleaned)
        except SyntaxError:
            return []
    ids: List[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        # Accept either `check(...)` or `cadence.check(...)` / `progress.check(...)`.
        func = node.func
        is_check = (isinstance(func, ast.Name) and func.id == "check") or (
            isinstance(func, ast.Attribute) and func.attr == "check"
        )
        if not is_check:
            continue
        if not node.args:
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            ids.append(first.value)
    return ids


def _extract_lesson_name(cells) -> Optional[str]:
    """Find the lesson name from `%cadence_create_lesson`/`%cadence_lesson` magics."""
    for cell in cells:
        if cell.get("cell_type") != "code":
            continue
        m = _LESSON_MAGIC_RE.search(cell.get("source", ""))
        if not m:
            continue
        arg = m.group(1).strip()
        # Quoted name → take everything inside the matching quote.
        if arg and arg[0] in ('"', "'"):
            end = arg.find(arg[0], 1)
            if end > 0:
                return arg[1:end]
        # Unquoted name (single word, no flags) → take up to the first `--flag`.
        return arg.split("--")[0].strip() or None
    return None


def _extract_starter_block(source: str) -> Optional[str]:
    """Return the text between `# cadence:starter` and `# cadence:end` in
    the teacher cell, stripped of surrounding blank lines. None if no
    starter markers are present, or if the markers don't form a valid
    open/close pair."""
    start = _STARTER_START_RE.search(source)
    if not start:
        return None
    end = _STARTER_END_RE.search(source, pos=start.end())
    if not end:
        return None
    return source[start.end():end.start()].strip("\n")


def _stub_for_ids(ids: List[str], teacher_source: Optional[str] = None) -> str:
    """Build the body of a student exercise cell: a placeholder + one check
    call per id. Uses Ellipsis (`...`) as the answer so the cell is at least
    syntactically valid and check() reports "wrong answer" rather than
    NameError.

    If `teacher_source` contains a `# cadence:starter` / `# cadence:end`
    block, that block becomes the placeholder body — giving students a
    scaffolded starting point instead of a blank `# Your code here`."""
    body = "# Your code here"
    if teacher_source is not None:
        starter = _extract_starter_block(teacher_source)
        if starter:
            body = starter
    lines = [body, ""]
    for cid in ids:
        lines.append(f'check("{cid}", ...)')
    return "\n".join(lines)


# Rendered as raw HTML inside a markdown cell. We pick a soft left-accent
# stripe over a full border (less alert-banner, more "informational aside"),
# and set explicit text colors so it reads cleanly on both light and dark
# Jupyter themes — the previous version inherited body color and rendered
# nearly-invisible on a dark background.
_STUDENT_INTRO = (
    '<div style="border-left: 4px solid #2563eb; background: #f8fafc;'
    ' padding: 14px 18px; margin: 6px 0; border-radius: 4px;'
    ' color: #1f2937;">'
    '<div style="font-weight: 600; color: #1e3a8a; margin-bottom: 8px;'
    ' font-size: 1.05em;">'
    '👋 Welcome — quick reference for Cadence'
    '</div>'
    '<ul style="margin: 0; padding-left: 22px; line-height: 1.65;'
    ' color: #1f2937;">'
    '<li><strong>Submit an answer:</strong> each exercise cell ends with '
    '<code>check("id", answer)</code> — replace the placeholder with your '
    'answer and run the cell.</li>'
    '<li><strong>Submit a plot:</strong> <code>submit_image("id", fig)</code> '
    "ships a matplotlib or Plotly figure to your teacher's dashboard.</li>"
    '<li><strong>Free-text / reflections:</strong> write your response, then '
    '<code>mark_done("id")</code> to mark it complete.</li>'
    '<li><strong>Stuck?</strong> <code>show_hint("id")</code> for the '
    "teacher's hint, or <code>show_solution(\"id\")</code> after a few wrong "
    "attempts if your teacher enabled solution reveals.</li>"
    '<li><strong>Your data:</strong> <code>%cadence_export_my_data</code> '
    "to download what's stored about you, "
    '<code>%cadence_delete_my_data --yes</code> to wipe it.</li>'
    '</ul></div>'
)


def _build_student_notebook(
    teacher_nb,
    join_code: str,
    name_placeholder: str,
) -> Tuple[object, int, int, int, List[str]]:
    student = nbf.v4.new_notebook()
    if "kernelspec" in teacher_nb.metadata:
        student.metadata["kernelspec"] = teacher_nb.metadata["kernelspec"]

    # Intro: one-paragraph crib sheet for the student-side API. Renders before
    # the session cell so students see how submission works before they join.
    student.cells.append(nbf.v4.new_markdown_cell(source=_STUDENT_INTRO))

    # Session header — load_ext + auto-filled join code + explicit imports
    # of the student-side helpers. The extension also pushes these into the
    # user namespace at load time (belt-and-braces), but the explicit import
    # is what students see in the cell, makes the source of `check` obvious,
    # and survives in environments where the extension push doesn't fire (or
    # where a stale version of the package is installed and silently shadowed).
    header = (
        f"%load_ext cadence\n"
        f'%cadence_session {join_code} "{name_placeholder}"\n'
        "from cadence import check, show_hint, show_solution, mark_done, submit_image"
    )
    student.cells.append(nbf.v4.new_code_cell(source=header))

    n_tasks = 0
    n_exercises = 0
    n_solutions = 0
    all_ids: List[str] = []
    # When a task marker carries a checkpoint id, the NEXT code cell becomes
    # the exercise stub for that id — even without any check() call in the
    # teacher's cell. This lets teachers keep their solution code clean.
    pending_checkpoint_id: Optional[str] = None

    for cell in teacher_nb.cells:
        if cell.cell_type == "markdown":
            # Strip `<!-- cadence:hide -->`...`<!-- cadence:end -->` regions
            # before any other processing — those are the teacher's authoring
            # notes and shouldn't reach students.
            source = strip_hide_blocks(cell.source, kind="markdown").strip()
            if not source:
                # Whole cell was hidden; drop it.
                continue
            m = TASK_MARKER_RE.search(source)
            if m:
                student.cells.append(nbf.v4.new_markdown_cell(source=source))
                n_tasks += 1
                pending_checkpoint_id = m.group("id")  # may be None
                continue
            # Heading-only markdowns (`## Part A`, `### Setup`, ...) carry
            # the section structure across so the student notebook has the
            # same outline as the teacher's. Pure-prose markdowns without a
            # heading or task marker stay teacher-private.
            if _HEADING_LINE_RE.search(source):
                student.cells.append(nbf.v4.new_markdown_cell(source=source))
            continue
        if cell.cell_type != "code":
            continue
        # Strip hide blocks first — teacher's authoring notes never reach
        # the student notebook regardless of which downstream branch fires.
        source = strip_hide_blocks(cell.source, kind="code")
        if not source.strip():
            continue
        # Solution marker wins: copy the cell verbatim (minus the marker line).
        # Lets teachers show setup/imports, worked solutions, or reference code.
        if SOLUTION_MARKER_RE.search(source):
            student.cells.append(
                nbf.v4.new_code_cell(source=_strip_solution_marker(source))
            )
            n_solutions += 1
            pending_checkpoint_id = None
            continue
        # Code-cell marker takes precedence over a pending task-marker id.
        # Either form means "stub this cell with check('<id>', ...)" — the
        # teacher doesn't need a check() call in their solution.
        cm = CHECKPOINT_MARKER_RE.search(source)
        if cm:
            cid = cm.group("id")
            student.cells.append(nbf.v4.new_code_cell(
                source=_stub_for_ids([cid], teacher_source=source)
            ))
            n_exercises += 1
            all_ids.append(cid)
            pending_checkpoint_id = None
            continue
        if pending_checkpoint_id is not None:
            cid = pending_checkpoint_id
            student.cells.append(nbf.v4.new_code_cell(
                source=_stub_for_ids([cid], teacher_source=source)
            ))
            n_exercises += 1
            all_ids.append(cid)
            pending_checkpoint_id = None
            continue
        # Back-compat: cells with check() calls but no other marker still
        # turn into stubs preserving those exact ids. Older teacher notebooks
        # (and the one-cell-with-multiple-checks pattern) keep working.
        ids = _extract_check_ids(source)
        if not ids:
            continue
        student.cells.append(nbf.v4.new_code_cell(
            source=_stub_for_ids(ids, teacher_source=source)
        ))
        n_exercises += 1
        all_ids.extend(ids)

    return student, n_tasks, n_exercises, n_solutions, all_ids


def scaffold(
    src_path: Path,
    out_path: Optional[Path] = None,
    join_code: Optional[str] = None,
    name_placeholder: str = "your name",
) -> ScaffoldResult:
    """Generate a student notebook from a teacher's notebook.

    Args:
        src_path: Path to the teacher's notebook.
        out_path: Where to write the student notebook. Defaults to
            `<src_stem>_student.ipynb` next to the source.
        join_code: Override the join code. By default we read the lesson name
            from the teacher's `%cadence_(create_)lesson "Name"` magic and look
            up its join code in `~/.cadence/lessons.yaml`.
        name_placeholder: Text put in the `%cadence_session <code> "..."` slot.

    Returns:
        A ScaffoldResult with the output path and counts.

    Raises:
        FileNotFoundError: source notebook missing.
        ValueError: no join code could be determined.
    """
    src_path = Path(src_path)
    if not src_path.exists():
        raise FileNotFoundError(f"Notebook not found: {src_path}")

    teacher_nb = nbf.read(str(src_path), as_version=4)

    lesson_name = _extract_lesson_name(teacher_nb.cells)
    resolved_join_code = join_code
    if resolved_join_code is None:
        if lesson_name:
            cached = lesson_store.get(lesson_name)
            if cached and cached.get("join_code"):
                resolved_join_code = cached["join_code"]
        if resolved_join_code is None:
            hint = (
                f"Lesson '{lesson_name}' isn't cached in ~/.cadence/lessons.yaml."
                if lesson_name
                else "No %cadence_create_lesson / %cadence_lesson magic found in the notebook."
            )
            raise ValueError(
                f"Could not auto-detect a join code. {hint} "
                f"Pass --join-code explicitly, or create the lesson in this kernel first."
            )

    student, n_tasks, n_exercises, n_solutions, ids = _build_student_notebook(
        teacher_nb, resolved_join_code, name_placeholder
    )

    out_path = Path(out_path) if out_path else src_path.with_name(
        f"{src_path.stem}_student.ipynb"
    )
    nbf.write(student, str(out_path))

    return ScaffoldResult(
        out_path=out_path,
        n_tasks=n_tasks,
        n_exercises=n_exercises,
        n_solutions=n_solutions,
        checkpoint_ids=ids,
        lesson_name=lesson_name,
        join_code=resolved_join_code,
    )
