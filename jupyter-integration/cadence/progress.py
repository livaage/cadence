"""
Student-facing checkpoint helpers.

After `%competition_session` has been run, `check()` submits an answer for
a named checkpoint and returns a small result object the student can inspect.
"""

from dataclasses import dataclass
from typing import Any, Optional

from .api import CadenceAPI


@dataclass
class CheckResult:
    is_correct: bool
    attempt_num: int
    elapsed_ms: Optional[int] = None
    is_manual: bool = False
    hint_available: bool = False
    solution_available: bool = False
    checkpoint_id: Optional[str] = None  # set by check() so the prompts can mention it

    def __bool__(self) -> bool:
        return self.is_correct

    def _format_elapsed(self) -> str:
        if self.elapsed_ms is None:
            return ""
        ms = self.elapsed_ms
        if ms < 1000:
            return f" in {ms} ms"
        return f" in {ms / 1000:.2f} s"

    def _hint_prompt_html(self) -> str:
        if not self.hint_available or not self.checkpoint_id:
            return ""
        return (
            f'<div style="margin-top: 4px; color: #b45309;">💡 Need a hint? '
            f'Run <code>show_hint("{self.checkpoint_id}")</code></div>'
        )

    def _reveal_html(self) -> str:
        if not self.solution_available or not self.checkpoint_id:
            return ""
        return (
            f'<div style="margin-top: 4px; color: #6b21a8;">💡 Show solution? '
            f'Run <code>show_solution("{self.checkpoint_id}")</code></div>'
        )

    def _repr_html_(self) -> str:
        if self.is_manual:
            return (
                f'<div style="color: green;">✅ Marked done '
                f'(attempt {self.attempt_num}{self._format_elapsed()})</div>'
                + self._reveal_html()
            )
        if self.is_correct:
            return (
                f'<div style="color: green;">✅ Correct '
                f'(attempt {self.attempt_num}{self._format_elapsed()})</div>'
                + self._reveal_html()
            )
        return (
            f'<div style="color: #b45309;">❌ Not quite '
            f'(attempt {self.attempt_num}{self._format_elapsed()})</div>'
            + self._hint_prompt_html()
            + self._reveal_html()
        )


_state = {
    "session_id": None,
    "join_code": None,
    "lesson_id": None,
    "display_name": None,
    "api": None,
}

_teacher_state = {
    "teacher_token": None,
    "lesson_id": None,
    "lesson_name": None,
    "join_code": None,
    "api": None,
}

_course_teacher_state = {
    "teacher_token": None,
    "course_id": None,
    "course_name": None,
    "join_code": None,
    "api": None,
}


def set_session(
    session_id: str,
    join_code: str,
    lesson_id: str,
    display_name: str,
    api: CadenceAPI,
) -> None:
    _state["session_id"] = session_id
    _state["join_code"] = join_code
    _state["lesson_id"] = lesson_id
    _state["display_name"] = display_name
    _state["api"] = api


def current_session() -> Optional[dict]:
    if not _state["session_id"]:
        return None
    return dict(_state)


def clear_session() -> None:
    """Drop the active session — used after %cadence_delete_my_data so the
    kernel no longer refers to a session_id that has just been wiped server-side."""
    for k in _state:
        _state[k] = None


def set_teacher(
    teacher_token: str,
    lesson_id: str,
    lesson_name: str,
    join_code: str,
    api: CadenceAPI,
) -> None:
    _teacher_state["teacher_token"] = teacher_token
    _teacher_state["lesson_id"] = lesson_id
    _teacher_state["lesson_name"] = lesson_name
    _teacher_state["join_code"] = join_code
    _teacher_state["api"] = api


def current_teacher() -> Optional[dict]:
    if not _teacher_state["teacher_token"]:
        return None
    return dict(_teacher_state)


def set_course_teacher(
    teacher_token: str,
    course_id: str,
    course_name: str,
    join_code: str,
    api: CadenceAPI,
    session_retention_days: Optional[int] = None,
) -> None:
    _course_teacher_state["teacher_token"] = teacher_token
    _course_teacher_state["course_id"] = course_id
    _course_teacher_state["course_name"] = course_name
    _course_teacher_state["join_code"] = join_code
    _course_teacher_state["api"] = api
    # Lets `%cadence_add_notebook` create lessons that inherit the course's
    # retention immediately, so the course card and the lesson card don't
    # show conflicting day counts.
    _course_teacher_state["session_retention_days"] = session_retention_days


def current_course_teacher() -> Optional[dict]:
    if not _course_teacher_state["teacher_token"]:
        return None
    return dict(_course_teacher_state)


def check(checkpoint_id: str, value: Any, elapsed_ms: Optional[int] = None) -> CheckResult:
    """Submit an answer for `checkpoint_id` and return a CheckResult.

    Requires `%competition_session` to have been run first. If `elapsed_ms`
    is supplied the attempt is recorded toward the teacher's timing histogram
    (normally set by `%%time_check`, not by callers directly).
    """
    api = _state["api"]
    session_id = _state["session_id"]
    if not api or not session_id:
        raise RuntimeError(
            'No active session. Run `%competition_session <join_code> "<your name>"` first.'
        )
    resp = api.check_answer(session_id, checkpoint_id, value, elapsed_ms=elapsed_ms)
    return CheckResult(
        is_correct=bool(resp.get("is_correct")),
        attempt_num=int(resp.get("attempt_num", 0)),
        elapsed_ms=resp.get("elapsed_ms"),
        is_manual=bool(resp.get("is_manual")),
        hint_available=bool(resp.get("hint_available")),
        solution_available=bool(resp.get("solution_available")),
        checkpoint_id=checkpoint_id,
    )


def submit_image(checkpoint_id: str, figure_or_bytes: Any, code: Optional[str] = None) -> None:
    """Submit a plot/image to a checkpoint that has `--allow-submissions`.

    Accepts a matplotlib Figure (or anything with a savefig method), a PIL Image,
    or raw PNG bytes. Optionally also send a code snippet alongside the image —
    useful when the figure is the headline but the code is the receipt.

    Example:
        fig, ax = plt.subplots(); ax.plot(x, y); ax.set_title("My finding")
        submit_image("discovery.plot", fig)
    """
    import io, base64 as _b64
    api = _state["api"]
    session_id = _state["session_id"]
    if not api or not session_id:
        raise RuntimeError('No active session. Run `%cadence_session <join_code> "<your name>"` first.')

    # Coerce common figure objects to raw PNG bytes
    if hasattr(figure_or_bytes, "savefig"):  # matplotlib Figure / Axes
        buf = io.BytesIO()
        figure_or_bytes.savefig(buf, format="png", bbox_inches="tight", dpi=120)
        png_bytes = buf.getvalue()
    elif hasattr(figure_or_bytes, "save") and hasattr(figure_or_bytes, "mode"):  # PIL Image
        buf = io.BytesIO()
        figure_or_bytes.save(buf, format="PNG")
        png_bytes = buf.getvalue()
    elif isinstance(figure_or_bytes, (bytes, bytearray)):
        png_bytes = bytes(figure_or_bytes)
    else:
        raise TypeError(
            f"submit_image expected a matplotlib Figure, PIL Image, or bytes — got {type(figure_or_bytes).__name__}"
        )

    if len(png_bytes) > 1_000_000:
        raise ValueError(f"Image too large ({len(png_bytes) // 1024} KB > 1 MB limit). Lower the dpi or crop the figure.")

    image_b64 = _b64.b64encode(png_bytes).decode("ascii")
    try:
        api.submit_code(
            session_id,
            checkpoint_id,
            code=code,
            language="python",
            image_data_b64=image_b64,
            image_mime="image/png",
        )
    except Exception as e:
        try:
            from IPython.display import HTML, display  # type: ignore
            return display(HTML(f'<div style="color: red;">❌ Image submission failed: {e}</div>'))
        except ImportError:
            raise

    try:
        from IPython.display import HTML, display  # type: ignore
        display(HTML(
            f'<div style="color: #6b21a8;">📤 Plot submitted to '
            f'<code>{checkpoint_id}</code> ({len(png_bytes) // 1024} KB). The teacher can see it on the dashboard.</div>'
        ))
    except ImportError:
        pass


def mark_done(checkpoint_id: str) -> CheckResult:
    """Student-side: mark a manual (self-attested) checkpoint as done.

    Use this for tasks where there's no single right answer — e.g. "plot the
    distribution and describe what you see" or "experiment with three different
    parameter values". The teacher configures the checkpoint with
    `--comparator manual` and the dashboard counts whoever calls this as having
    completed the task. There's no validation; trust is the contract.
    """
    return check(checkpoint_id, "(marked done)")


def _render_hint_markdown(text: str) -> str:
    """Tiny markdown-to-HTML renderer for hint text, so teachers can use
    backticks for inline code, fenced blocks for snippets, and **bold**.

    Not a real markdown parser — just the three constructs that come up in
    hints often enough to matter. Anything that isn't a fence/backtick/bold is
    left alone so existing plain-text hints render unchanged. HTML in the
    source is preserved (it was already rendered raw before this function
    existed; we don't want to silently regress that)."""
    import re as _re
    import html as _html

    out_parts: list = []
    pos = 0
    # Fenced code blocks first (```...```), then inline backticks, then bold.
    # We segment by fences and process each segment.
    fence_re = _re.compile(r"```(?:[a-zA-Z0-9_+-]*)?\n?([\s\S]*?)```", _re.MULTILINE)
    for m in fence_re.finditer(text):
        before = text[pos:m.start()]
        out_parts.append(_render_hint_inline(before))
        code = _html.escape(m.group(1).rstrip("\n"))
        out_parts.append(
            f'<pre style="background: #fff; border: 1px solid #e5d7a5;'
            f' border-radius: 3px; padding: 6px 8px; margin: 4px 0;'
            f' font-size: 0.9em; overflow-x: auto;"><code>{code}</code></pre>'
        )
        pos = m.end()
    out_parts.append(_render_hint_inline(text[pos:]))
    return "".join(out_parts)


def _render_hint_inline(text: str) -> str:
    """Inline backticks and **bold** only; leaves any existing HTML alone."""
    import re as _re
    # Backticks: `code` → <code>code</code>. We escape ONLY the backtick body.
    import html as _html
    parts: list = []
    last = 0
    for m in _re.finditer(r"`([^`\n]+)`", text):
        parts.append(text[last:m.start()])
        parts.append(f"<code>{_html.escape(m.group(1))}</code>")
        last = m.end()
    parts.append(text[last:])
    joined = "".join(parts)
    # Bold: **bold**. Has to come after backticks so we don't ** inside `code`.
    joined = _re.sub(
        r"\*\*([^*\n]+)\*\*", lambda m: f"<strong>{m.group(1)}</strong>", joined
    )
    return joined


def show_hint(checkpoint_id: str):
    """Fetch and render the teacher's hint for `checkpoint_id`.

    Only works once the student has made enough attempts (the threshold is set
    per-checkpoint by the teacher via `--hint-after-attempts N`, default 1).
    """
    api = _state["api"]
    session_id = _state["session_id"]
    if not api or not session_id:
        raise RuntimeError(
            'No active session. Run `%cadence_session <join_code> "<your name>"` first.'
        )
    try:
        from IPython.display import HTML, display  # type: ignore
    except ImportError:
        HTML = None
        display = print
    try:
        resp = api.get_hint(session_id, checkpoint_id)
    except Exception as e:
        msg = str(e)
        if HTML is not None:
            return display(HTML(f'<div style="color: #b45309;">🔒 {msg}</div>'))
        return display(f"🔒 {msg}")

    html = (
        f'<div style="border-left: 3px solid #b45309; padding: 8px 12px; '
        f'background: #fffbeb; margin: 4px 0;">'
        f'<strong>💡 Hint for <code>{checkpoint_id}</code></strong>'
        f'<div style="margin-top: 4px;">{_render_hint_markdown(resp["hint"])}</div>'
        f'</div>'
    )
    if HTML is not None:
        return display(HTML(html))
    return display(html)


def show_solution(checkpoint_id: str):
    """Fetch and render the worked solution for `checkpoint_id`.

    Only works once the student has made enough attempts (the threshold
    is set per-checkpoint by the teacher via `--reveal-after N`).
    """
    api = _state["api"]
    session_id = _state["session_id"]
    if not api or not session_id:
        raise RuntimeError(
            'No active session. Run `%cadence_session <join_code> "<your name>"` first.'
        )
    try:
        from IPython.display import HTML, display  # type: ignore
    except ImportError:
        HTML = None
        display = print
    try:
        resp = api.get_solution(session_id, checkpoint_id)
    except Exception as e:
        msg = str(e)
        if HTML is not None:
            return display(HTML(f'<div style="color: #b45309;">🔒 {msg}</div>'))
        return display(f"🔒 {msg}")

    import html as _html
    parts = [f'<div style="border-left: 3px solid #6b21a8; padding: 8px 12px; '
             f'background: #faf5ff; margin: 4px 0;">'
             f'<strong>💡 Solution for <code>{checkpoint_id}</code></strong>']
    if resp.get("solution_value"):
        parts.append(
            f'<div style="margin-top: 6px;"><em>Expected answer:</em> '
            f'<code>{_html.escape(str(resp["solution_value"]))}</code></div>'
        )
    if resp.get("solution_code"):
        # Teachers sometimes pass `\n` as literal escape sequences when using
        # the line magic (--solution-code "...\n..."); interpret those as real
        # newlines so the code block renders multi-line. HTML-escape the
        # content so any `<`, `>`, `&` in the snippet don't break the layout.
        raw = str(resp["solution_code"]).replace("\\n", "\n").replace("\\t", "\t")
        escaped = _html.escape(raw)
        parts.append(
            f'<div style="margin-top: 6px;"><em>Worked solution:</em></div>'
            f'<pre style="background: #1f2937; color: #f9fafb; padding: 12px; '
            f"border-radius: 4px; overflow: auto; font-size: 0.85em; "
            f"font-family: 'JetBrains Mono', 'Menlo', 'Consolas', monospace; "
            f'line-height: 1.45; white-space: pre-wrap; margin: 4px 0;">'
            f'{escaped}</pre>'
        )
    parts.append('</div>')
    html = ''.join(parts)
    if HTML is not None:
        return display(HTML(html))
    # Fallback for non-IPython environments
    return display(html)
