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


class CadenceExtension:
    """Thin handle kept for symmetry with the package __all__."""

    def __init__(self, ipython):
        self.ipython = ipython
        self.magics = CadenceMagic(ipython)
        ipython.register_magics(self.magics)
        _register_completers(ipython)
        _push_student_helpers(ipython)


def load_ipython_extension(ipython):
    CadenceExtension(ipython)


def unload_ipython_extension(ipython):
    pass
