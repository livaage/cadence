"""
IPython extension entry point.

Loaded via `%load_ext cadence` inside a notebook.

Beyond registering the Magics class, this also wires up tab-completion hooks
so typing `%cadence_lesson <TAB>` (and friends) surfaces the names cached in
~/.cadence/lessons.yaml — a tactile hint that beats remembering the exact
lesson name a teacher used three weeks ago.
"""

from . import lesson_store
from .magic import CadenceMagic
from .progress import (
    check,
    mark_done,
    show_hint,
    show_solution,
    submit_image,
)


# Student-side helpers that the generated student notebook's intro promises
# work as bare names (`check(...)`, `show_hint(...)`, ...). Pushing them into
# the user namespace at extension-load means students don't need an explicit
# `from cadence import check, ...` line — and the documented one-cell
# `%load_ext cadence` + `%cadence_session` header is all they need.
_STUDENT_HELPERS = {
    "check": check,
    "show_hint": show_hint,
    "show_solution": show_solution,
    "mark_done": mark_done,
    "submit_image": submit_image,
}


# Magics where the (possibly multi-word) positional argument is a *lesson* name
# the teacher has cached locally. Completion sources from list_by_kind("lesson").
_LESSON_NAME_MAGICS = (
    "cadence_lesson",
    "cadence_show_join",
    "cadence_delete_lesson",
    "cadence_clone_lesson",
    "cadence_attach_lesson",
    "cadence_detach_lesson",
)

# Magics whose positional argument is a *course* name from the local cache.
_COURSE_NAME_MAGICS = (
    "cadence_course",
    "cadence_delete_course",
)

# Comparator vocabulary — used to complete `--comparator <TAB>` and the YAML
# `comparator:` key. Order matches the doc rotation in the Guide.
_COMPARATORS = ("exact", "numeric", "set", "regex", "manual")


def _cached_names(kind: str) -> list[str]:
    try:
        return lesson_store.list_by_kind(kind)
    except Exception:
        # Cache may be unreadable on a fresh machine — silently degrade rather
        # than poisoning every tab-press with a traceback.
        return []


def _quote_if_needed(name: str) -> str:
    """Cached names commonly contain spaces (lesson titles), and our magics
    parse arguments with shlex — so completion needs to emit a quoted form
    when whitespace is present."""
    if any(c.isspace() for c in name):
        return f'"{name}"'
    return name


def _lesson_completer(ipython_completer, event):
    return [_quote_if_needed(n) for n in _cached_names("lesson")]


def _course_completer(ipython_completer, event):
    return [_quote_if_needed(n) for n in _cached_names("course")]


def _comparator_completer(ipython_completer, event):
    """Surface comparator vocab after `--comparator` on %cadence_register."""
    # IPython hands us the line up to the cursor in `event.line`. We only
    # offer comparator values when the previous token is `--comparator`.
    line = getattr(event, "line", "") or ""
    tokens = line.rstrip().split()
    if tokens and tokens[-1] == "--comparator":
        return list(_COMPARATORS)
    # Otherwise: don't interfere — let IPython fall back to its default
    # completer for the magic.
    return []


def _register_completers(ipython) -> None:
    set_hook = getattr(ipython, "set_hook", None)
    if set_hook is None:  # pragma: no cover — non-standard IPython shell
        return
    for magic in _LESSON_NAME_MAGICS:
        set_hook("complete_command", _lesson_completer, str_key=f"%{magic}")
    for magic in _COURSE_NAME_MAGICS:
        set_hook("complete_command", _course_completer, str_key=f"%{magic}")
    set_hook("complete_command", _comparator_completer, str_key="%cadence_register")


def _push_student_helpers(ipython) -> None:
    """Inject `check` / `show_hint` / `show_solution` / `mark_done` /
    `submit_image` into the user namespace so they resolve as bare names.

    Only fills in names that aren't already bound — if the user has imported
    a different `check` for their own purposes we don't clobber it."""
    ns = getattr(ipython, "user_ns", None)
    if ns is None:
        return
    for name, fn in _STUDENT_HELPERS.items():
        ns.setdefault(name, fn)


import re as _re

_STARTER_OPEN_RE = _re.compile(r"^([ \t]*)#\s*cadence:starter\s*$")
_STARTER_CLOSE_RE = _re.compile(r"^([ \t]*)#\s*cadence:end\s*$")


def _starter_block_transformer(lines: list) -> list:
    """IPython input transformer that comments out lines inside a
    `# cadence:starter` / `# cadence:end` block before the cell runs.

    The teacher's reference solution lives outside the block and runs as
    normal; the block's contents — which exist only to scaffold the student
    notebook — get a `# ` prefix so the kernel never tries to parse them as
    Python. This lets teachers write free-form prose, pseudocode, or
    intentionally-broken stubs inside the block without their own
    `Run All` SyntaxErroring.

    The on-disk .ipynb cell source is unaffected — scaffold reads from the
    file and still sees the original starter text to copy into the student
    stub.

    Operates on the IPython 7+ line list (each entry already ends in `\\n`).
    """
    out: list = []
    inside = False
    for line in lines:
        stripped_line = line.rstrip("\n")
        if not inside:
            if _STARTER_OPEN_RE.match(stripped_line):
                inside = True
                out.append(line)
                continue
            out.append(line)
        else:
            if _STARTER_CLOSE_RE.match(stripped_line):
                inside = False
                out.append(line)
                continue
            # Inside a starter block: prefix `# ` (preserve original
            # indentation so the cell still parses cleanly if the closer
            # is somehow missing — we degrade to a bunch of comments).
            indent_len = len(line) - len(line.lstrip(" \t"))
            indent = line[:indent_len]
            body = line[indent_len:]
            out.append(f"{indent}# {body}" if body.strip() else line)
    return out


def _register_input_transformers(ipython) -> None:
    """Install Cadence's IPython input transformers. Currently just the
    starter-block comment-out pass; future transformers (e.g. for
    `cadence:hide` if we ever want it stripped at runtime too) would
    hook in here as well.

    Idempotent: if the transformer is already in the list (because the
    extension was reloaded), don't double-register."""
    transformers = getattr(ipython, "input_transformers_cleanup", None)
    if transformers is None:
        return
    if _starter_block_transformer not in transformers:
        transformers.append(_starter_block_transformer)


class CadenceExtension:
    """Thin handle kept for symmetry with the package __all__."""

    def __init__(self, ipython):
        self.ipython = ipython
        self.magics = CadenceMagic(ipython)
        ipython.register_magics(self.magics)
        _register_completers(ipython)
        _push_student_helpers(ipython)
        _register_input_transformers(ipython)


def load_ipython_extension(ipython):
    CadenceExtension(ipython)


def unload_ipython_extension(ipython):
    pass
