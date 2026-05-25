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
from typing import Any, List, Optional, Tuple

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
# `# cadence:given` / `# cadence:end` marks code that runs in the teacher
# kernel AND is carried verbatim into the student notebook above the
# starter stub. Closes the gap where setup data the student needs
# (loaded arrays, seeded RNG draws, etc.) can't live in `cadence:starter`
# (which the input transformer comments out so prose-style stubs work)
# but also shouldn't be dropped on the way to the student.
_GIVEN_START_RE = re.compile(r"^[ \t]*#\s*cadence:given\s*$", re.MULTILINE)
_GIVEN_END_RE = _STARTER_END_RE  # same closer; markers all share `cadence:end`
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


@dataclass
class NotebookSource:
    """A located teacher notebook + how we located it.

    `notebook` is always populated (already parsed). `path` is the on-disk
    file if there is one; None on platforms where the notebook lives only
    in the frontend (Colab) or where the caller uploaded bytes directly.

    Callers should write output files relative to `path` when available;
    when None they should default to the kernel's CWD with a sensible
    fixed name and surface a download link.
    """

    notebook: Any  # nbformat.NotebookNode — typed as Any to keep nbformat import-light
    path: Optional[Path]
    platform: str  # one of: vscode, jpy_session_name, jupyter_server, colab, kaggle, upload


# Module-level cache populated by the upload-widget fallback. When the user
# drops an .ipynb on the FileUpload widget, its callback stashes the parsed
# notebook here; the next call to detect_notebook_source() picks it up and
# consumes it (single-shot — re-runs after a fresh detection attempt).
_uploaded_notebook_cache: List["NotebookSource"] = []


def _try_vscode() -> Optional[NotebookSource]:
    try:
        from IPython import get_ipython
        ip = get_ipython()
        if ip is None:
            return None
        vsc = ip.user_ns.get("__vsc_ipynb_file__")
        if not isinstance(vsc, str) or not vsc.endswith(".ipynb"):
            return None
        p = Path(vsc)
        if not p.exists():
            return None
        return NotebookSource(nbf.read(str(p), as_version=4), p, "vscode")
    except Exception:
        return None


def _try_jpy_session_name() -> Optional[NotebookSource]:
    session_name = os.environ.get("JPY_SESSION_NAME", "")
    if not session_name.endswith(".ipynb"):
        return None
    p = Path(session_name)
    if not p.is_absolute():
        p = Path.cwd() / p
    if not p.exists():
        return None
    try:
        return NotebookSource(nbf.read(str(p), as_version=4), p, "jpy_session_name")
    except Exception:
        return None


def _try_jupyter_server_api() -> Optional[NotebookSource]:
    try:
        import ipykernel
        import requests as _requests
    except Exception:
        return None
    try:
        conn_file = ipykernel.get_connection_file()
        kernel_id = Path(conn_file).stem.removeprefix("kernel-")
        servers: List[dict] = []
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
                        return NotebookSource(
                            nbf.read(str(p), as_version=4), p, "jupyter_server"
                        )
            except Exception:
                continue
    except Exception:
        return None
    return None


def _try_colab() -> Optional[NotebookSource]:
    """Pull the live notebook JSON from Colab's frontend via the undocumented
    `_message.blocking_request("get_ipynb")` API. Returns a path-less source
    — Colab notebooks live in Drive, not on the VM filesystem."""
    try:
        from google.colab import _message
    except ImportError:
        return None
    try:
        resp = _message.blocking_request("get_ipynb", request="", timeout_sec=8)
    except Exception:
        return None
    if not isinstance(resp, dict):
        return None
    ipynb = resp.get("ipynb")
    if ipynb is None:
        return None
    try:
        # _message hands back a dict-shaped notebook where cell sources are
        # the on-disk JSON list-of-lines form. nbf.from_dict alone leaves
        # those as lists — downstream code (autoregister, scaffold) expects
        # joined strings. Round-trip through JSON so nbformat's reader
        # normalizes everything (sources, cell ids, kernelspec) exactly as
        # it would for a real .ipynb on disk.
        import json as _json
        text = _json.dumps(ipynb) if isinstance(ipynb, dict) else (
            ipynb if isinstance(ipynb, str) else ipynb.decode("utf-8")
        )
        nb = nbf.reads(text, as_version=4)
        # Colab notebooks routinely arrive without per-cell id fields; recent
        # nbformat versions warn ("MissingIDFieldWarning") and may eventually
        # error. Run the normalizer to inject ids before downstream code
        # touches the cells.
        try:
            _changes, nb = nbf.validator.normalize(nb)
        except Exception:
            pass
        return NotebookSource(nb, None, "colab")
    except Exception:
        return None


def _try_kaggle() -> Optional[NotebookSource]:
    """No-op: Kaggle's `/kaggle/working/.virtual_documents/__notebook_source__.ipynb`
    looks like an .ipynb by name but is actually JupyterLab's flat Python-source
    extraction (the LSP "virtual document"). It contains the kernel's view of
    cell code only — no JSON structure, no markdown cells — so autoregister
    can't use it (markdown is how it finds exercise headings).

    Kept as a stub so future Kaggle changes can be re-enabled here without
    touching call sites. For now `is_kaggle()` triggers a Kaggle-tailored
    upload-widget message instead."""
    return None


# Pip install lines we want to propagate from the teacher notebook into
# the generated registered + student notebooks. Matches both magic and
# shell forms, with optional leading whitespace inside a cell. Conda
# isn't included — most teaching environments use pip, and conda calls
# inside Colab/Kaggle frequently misbehave anyway.
_PIP_INSTALL_LINE_RE = re.compile(
    r"^[ \t]*[%!]pip\s+install\s+.+?\s*$", re.MULTILINE
)


def _extract_pip_install_lines(cells) -> List[str]:
    """Return `%pip install` / `!pip install` lines from the teacher's
    notebook, deduped, in first-seen order.

    Carrying these into the generated registered + student notebooks fixes
    the Colab/Kaggle gap where the teacher installed cadence-edu in their
    source notebook but the *downloaded* registered/student notebook lands
    in a fresh kernel where the package isn't there yet.
    """
    seen: List[str] = []
    seen_set: set = set()
    for cell in cells:
        if getattr(cell, "cell_type", None) != "code":
            continue
        for m in _PIP_INSTALL_LINE_RE.finditer(getattr(cell, "source", "") or ""):
            line = m.group(0).strip()
            if line in seen_set:
                continue
            seen_set.add(line)
            seen.append(line)
    return seen


def is_kaggle() -> bool:
    """Heuristic platform sniff for the upload-widget's tailored copy."""
    return os.environ.get("KAGGLE_KERNEL_RUN_TYPE") == "Interactive"


def is_colab() -> bool:
    try:
        import google.colab  # noqa: F401
        return True
    except ImportError:
        return False


def detect_notebook_source() -> Optional[NotebookSource]:
    """Layered, best-effort detection of the running teacher notebook. Tries:

    1. VSCode (`__vsc_ipynb_file__`)
    2. `JPY_SESSION_NAME` env var (jupyter_server 2.x)
    3. Local jupyter_server `/api/sessions` (Classic, Lab, PyCharm, DataSpell)
    4. Google Colab — frontend bridge returns notebook JSON, no on-disk path
    5. Kaggle — JupyterLab RTC virtual-document path
    6. A pending widget upload cached by `_consume_uploaded()` (re-run path)

    Returns the first hit, or None. None means the caller should render the
    upload-widget fallback and ask the teacher for the .ipynb directly."""
    # Cached upload takes priority — if the user just dropped a file on the
    # widget and re-ran the magic, that's the canonical "they told us where
    # to look" signal.
    if _uploaded_notebook_cache:
        return _uploaded_notebook_cache.pop()
    for finder in (_try_vscode, _try_jpy_session_name, _try_jupyter_server_api,
                   _try_colab, _try_kaggle):
        src = finder()
        if src is not None:
            return src
    return None


def stash_uploaded_notebook(content: bytes) -> NotebookSource:
    """Park an uploaded .ipynb bytestream so the next detect_notebook_source()
    call returns it. Used by the FileUpload widget callback in magic.py."""
    nb = nbf.reads(content.decode("utf-8") if isinstance(content, (bytes, bytearray))
                   else content, as_version=4)
    src = NotebookSource(nb, None, "upload")
    _uploaded_notebook_cache.append(src)
    return src


def detect_current_notebook() -> Optional[Path]:
    """Back-compat shim: returns the on-disk path if we located a file-backed
    notebook, else None. Callers that can work with in-memory notebooks should
    use `detect_notebook_source()` directly to also cover Colab / upload.

    Deliberately skips the Colab and upload-cache branches — those produce
    path-less sources, and we don't want this shim to silently consume a
    pending widget upload when callers can't use it anyway."""
    for finder in (_try_vscode, _try_jpy_session_name,
                   _try_jupyter_server_api, _try_kaggle):
        try:
            src = finder()
        except Exception:
            continue
        if src is not None and src.path is not None:
            return src.path
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


def _extract_given_block(source: str) -> Optional[str]:
    """Return the text between `# cadence:given` and `# cadence:end` in
    the teacher cell, stripped of surrounding blank lines. None if no
    given markers are present, or no valid pair."""
    start = _GIVEN_START_RE.search(source)
    if not start:
        return None
    end = _GIVEN_END_RE.search(source, pos=start.end())
    if not end:
        return None
    return source[start.end():end.start()].strip("\n")


def _stub_for_ids(ids: List[str], teacher_source: Optional[str] = None) -> str:
    """Build the body of a student exercise cell.

    Layered, in order:
      1. **Given block** (optional, from `# cadence:given` / `# cadence:end`):
         setup code/data the teacher wants the student to have verbatim.
         Runs in the teacher kernel too — that's why it's separate from
         `cadence:starter`, which the input transformer comments out.
      2. **Starter stub** (optional, from `# cadence:starter` / `# cadence:end`):
         scaffolded placeholder code for the student to fill in. Falls back
         to a `# Your code here` line if no starter block is provided.
      3. **`check(...)` call** for every id, with `...` (Ellipsis) as the
         placeholder so the cell is at least syntactically valid before the
         student fills it in.
    """
    sections: List[str] = []
    if teacher_source is not None:
        given = _extract_given_block(teacher_source)
        if given:
            sections.append("# Given (carried over from the teacher):\n" + given)

    body = "# Your code here"
    if teacher_source is not None:
        starter = _extract_starter_block(teacher_source)
        if starter:
            body = starter
    sections.append(body)
    check_calls = "\n".join(f'check("{cid}", ...)' for cid in ids)
    sections.append(check_calls)
    return "\n\n".join(sections)


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
    # Use a portable Python 3 kernelspec instead of copying the teacher's
    # local kernel name — students opening this on Colab/Kaggle/binder shouldn't
    # see "Unrecognised runtime" warnings about the teacher's local env.
    student.metadata["kernelspec"] = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }

    # Carry `%pip install` / `!pip install` lines from the teacher source over
    # to the student notebook. Without this, a student opening the downloaded
    # notebook on Colab/Kaggle hits `%load_ext cadence` → ModuleNotFoundError
    # because their fresh kernel doesn't have cadence-edu yet. Goes BEFORE the
    # student intro so the install runs before any other cell.
    pip_lines = _extract_pip_install_lines(teacher_nb.cells)
    if pip_lines:
        student.cells.append(nbf.v4.new_code_cell(source="\n".join(pip_lines)))

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
    src_path: Optional[Path] = None,
    out_path: Optional[Path] = None,
    join_code: Optional[str] = None,
    name_placeholder: str = "your name",
    *,
    teacher_nb: Any = None,
) -> ScaffoldResult:
    """Generate a student notebook from a teacher's notebook.

    Args:
        src_path: Path to the teacher's notebook on disk. Pass either this OR
            `teacher_nb` (the latter is for callers that already hold the
            parsed notebook — e.g. Colab where the .ipynb has no file path).
        out_path: Where to write the student notebook. Defaults to
            `<src_stem>_student.ipynb` next to the source when a path was
            given; otherwise `cadence_student.ipynb` in the kernel's CWD.
        join_code: Override the join code. By default we read the lesson name
            from the teacher's `%cadence_(create_)lesson "Name"` magic and look
            up its join code in `~/.cadence/lessons.yaml`.
        name_placeholder: Text put in the `%cadence_session <code> "..."` slot.
        teacher_nb: Pre-parsed `nbformat.NotebookNode`. When supplied, skips
            reading from disk — required for path-less sources (Colab, upload).

    Returns:
        A ScaffoldResult with the output path and counts.

    Raises:
        FileNotFoundError: src_path was given but the file is missing.
        ValueError: neither src_path nor teacher_nb was supplied; or no join
            code could be determined.
    """
    if teacher_nb is None:
        if src_path is None:
            raise ValueError("scaffold() requires either src_path or teacher_nb")
        src_path = Path(src_path)
        if not src_path.exists():
            raise FileNotFoundError(f"Notebook not found: {src_path}")
        teacher_nb = nbf.read(str(src_path), as_version=4)
    elif src_path is not None:
        src_path = Path(src_path)

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

    if out_path is not None:
        out_path = Path(out_path)
    elif src_path is not None:
        out_path = src_path.with_name(f"{src_path.stem}_student.ipynb")
    else:
        # Path-less source (Colab / upload). Fall back to CWD with a fixed
        # name; the magic surfaces a FileLink so the teacher can download.
        out_path = Path.cwd() / "cadence_student.ipynb"
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
