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

    def _result_html(self) -> str:
        """The result line itself (correct / not quite / marked done) without
        any hint or solution prompts. Used by both the widget-based display
        path and the plain `_repr_html_` fallback."""
        if self.is_manual:
            return (
                f'<div style="color: green;">✅ Marked done '
                f'(attempt {self.attempt_num}{self._format_elapsed()})</div>'
            )
        if self.is_correct:
            return (
                f'<div style="color: green;">✅ Correct '
                f'(attempt {self.attempt_num}{self._format_elapsed()})</div>'
            )
        return (
            f'<div style="color: #b45309;">❌ Not quite '
            f'(attempt {self.attempt_num}{self._format_elapsed()})</div>'
        )

    def _hint_prompt_html(self) -> str:
        # Plain-text fallback used only when ipywidgets isn't available.
        if not self.hint_available or not self.checkpoint_id:
            return ""
        return (
            f'<div style="margin-top: 4px; color: #b45309;">💡 Need a hint? '
            f'Run <code>show_hint("{self.checkpoint_id}")</code></div>'
        )

    def _reveal_html(self) -> str:
        # Plain-text fallback used only when ipywidgets isn't available.
        if not self.solution_available or not self.checkpoint_id:
            return ""
        return (
            f'<div style="margin-top: 4px; color: #6b21a8;">💡 Show solution? '
            f'Run <code>show_solution("{self.checkpoint_id}")</code></div>'
        )

    def _repr_html_(self) -> str:
        # Fallback path: any IPython front-end that doesn't invoke
        # `_ipython_display_` (rare) gets the plain-HTML version with
        # `Run show_hint("...")` style text prompts.
        return self._result_html() + self._hint_prompt_html() + self._reveal_html()

    def _ipython_display_(self):
        """IPython display hook. Renders the result line, then — when hint /
        solution thresholds are unlocked — real `ipywidgets.Button`s that
        invoke `show_hint(id)` / `show_solution(id)` on click. Falls back to
        the text-prompt HTML when ipywidgets isn't importable."""
        try:
            from IPython.display import display, HTML
        except ImportError:
            print(self._result_html())
            return

        display(HTML(self._result_html()))

        if not (self.hint_available or self.solution_available) or not self.checkpoint_id:
            return

        try:
            import ipywidgets as widgets
        except ImportError:
            # No widgets — fall back to text prompts (original behaviour).
            if self.hint_available and self.checkpoint_id:
                display(HTML(self._hint_prompt_html()))
            if self.solution_available and self.checkpoint_id:
                display(HTML(self._reveal_html()))
            return

        cid = self.checkpoint_id
        # Hint button (only when the student has hit the hint threshold and
        # the teacher actually wrote a hint). Amber/warning styling so it's
        # visually distinct from the solution button — at attempt 3+ both
        # are visible at once, and the colour difference (amber vs blue)
        # makes it obvious which is the gentler nudge vs the worked answer.
        if self.hint_available:
            hint_btn = widgets.Button(
                description="💡 Show hint",
                tooltip=f"Reveal the hint for {cid}",
                button_style="warning",
                layout=widgets.Layout(width="auto", margin="6px 6px 6px 0"),
            )
            hint_out = widgets.Output()

            def _on_hint(_btn, cid=cid, out=hint_out):
                out.clear_output()
                with out:
                    show_hint(cid)
            hint_btn.on_click(_on_hint)
            display(hint_btn, hint_out)

        if self.solution_available:
            sol_btn = widgets.Button(
                description="🔑 Show worked solution",
                tooltip=f"Reveal the worked solution for {cid}",
                button_style="primary",
                layout=widgets.Layout(width="auto", margin="6px 6px 6px 0"),
            )
            sol_out = widgets.Output()

            def _on_solution(_btn, cid=cid, out=sol_out):
                out.clear_output()
                with out:
                    show_solution(cid)
            sol_btn.on_click(_on_solution)
            display(sol_btn, sol_out)


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


def _display_code_block(code: str) -> None:
    """Display a code snippet with Python syntax highlighting.

    Uses Pygments with `noclasses=True` to emit inline-styled highlighted
    HTML — works regardless of whether the Jupyter front-end has a code
    highlighter wired up (the Markdown ```python``` fence path relies on
    front-end CSS, which isn't always there). Wraps the output in a dark
    container with explicit `!important` styling so JupyterLab's stock
    `.rendered_html pre` rule can't override the dark background.

    Falls back to a plain dark `<pre>` if Pygments isn't installed (rare —
    IPython depends on it transitively), and finally to bare `print()` if
    even `IPython.display` is missing."""
    try:
        from IPython.display import display, HTML
    except ImportError:
        print(code)
        return
    import html as _h
    try:
        from pygments import highlight
        from pygments.lexers import PythonLexer
        from pygments.formatters import HtmlFormatter
        formatter = HtmlFormatter(
            style="monokai",      # dark theme — good contrast on either bg
            noclasses=True,       # inline styles, no external stylesheet needed
            nowrap=False,
        )
        highlighted = highlight(code, PythonLexer(stripnl=False), formatter)
        # Pygments emits `<div class="highlight"><pre>...</pre></div>`. Wrap
        # in our own div and override the inner <pre> styling with
        # !important — JupyterLab's `.rendered_html pre` would otherwise
        # paint over Monokai's background with its light-grey default.
        body = (
            '<div style="background: #272822 !important;'
            ' border-radius: 4px !important;'
            ' padding: 4px 12px !important;'
            ' margin: 4px 0 !important;'
            ' overflow-x: auto !important;">'
            '<style scoped>'
            ' .cadence-code pre {'
            '   background: transparent !important;'
            '   border: none !important;'
            '   color: #f8f8f2 !important;'
            "   font-family: 'JetBrains Mono', 'Menlo', 'Consolas', monospace !important;"
            '   font-size: 0.85em !important;'
            '   line-height: 1.5 !important;'
            '   white-space: pre !important;'
            '   margin: 0 !important;'
            '   padding: 8px 0 !important;'
            ' }'
            '</style>'
            f'<div class="cadence-code">{highlighted}</div>'
            '</div>'
        )
        display(HTML(body))
    except Exception:
        # Fallback: plain dark pre without highlighting. Still readable.
        escaped = _h.escape(code)
        display(HTML(
            '<pre style="background: #1f2937 !important;'
            ' color: #f9fafb !important;'
            ' padding: 12px !important;'
            ' border: none !important;'
            ' border-radius: 4px !important;'
            ' overflow-x: auto !important;'
            ' font-size: 0.85em !important;'
            " font-family: 'JetBrains Mono', 'Menlo', 'Consolas', monospace !important;"
            ' line-height: 1.45 !important;'
            ' white-space: pre-wrap !important;'
            ' margin: 4px 0 !important;">'
            f'{escaped}</pre>'
        ))


def _display_copy_button(text: str, label: str = "📋 Copy") -> None:
    """Render an ipywidgets.Button that copies `text` to the clipboard on
    click. The on_click handler calls `display(Javascript(...))` directly
    against the cell's output area (NOT captured in a widget Output —
    Javascript routed through a captured Output sometimes doesn't reach
    the browser's JS context). Tries the synchronous
    `document.execCommand('copy')` path first since it works without a
    live user-gesture window (which the kernel round-trip usually exhausts),
    and falls back to `navigator.clipboard.writeText` only if execCommand
    is disabled. Silently no-ops without ipywidgets."""
    try:
        from IPython.display import display, Javascript
        import ipywidgets as widgets
        import threading
    except ImportError:
        return
    btn = widgets.Button(
        description=label,
        tooltip="Copy this code to your clipboard",
        button_style="info",
        layout=widgets.Layout(width="auto", margin="4px 4px 8px 0"),
    )

    def _on_click(_btn, code=text, original_label=label):
        safe = (
            code.replace("\\", "\\\\")
                .replace("'", "\\'")
                .replace("\n", "\\n")
                .replace("\r", "\\r")
        )
        # Display Javascript directly to the cell's output area — NOT
        # captured in a widgets.Output, which can swallow JS payloads.
        display(Javascript(
            "(function(text){"
            "var ok=false;"
            "try{"
            "var ta=document.createElement('textarea');"
            "ta.value=text;"
            "ta.style.position='fixed';ta.style.left='-9999px';"
            "document.body.appendChild(ta);ta.select();"
            "ok=document.execCommand('copy');"
            "document.body.removeChild(ta);"
            "}catch(e){}"
            "if(!ok&&navigator.clipboard&&navigator.clipboard.writeText){"
            "navigator.clipboard.writeText(text).catch(function(e){"
            "console.error('cadence copy failed',e);});"
            "}"
            f"}})('{safe}');"
        ))
        # Visible confirmation via the button label itself — survives
        # whether the JS executed or not, and gives the student a clear
        # "your click did something" signal.
        btn.description = "✓ Copied"
        threading.Timer(1.6, lambda: setattr(btn, "description", original_label)).start()
    btn.on_click(_on_click)
    display(btn)


def show_hint(checkpoint_id: str):
    """Fetch and render the teacher's hint for `checkpoint_id`.

    Only works once the student has made enough attempts (the threshold is set
    per-checkpoint by the teacher via `--hint-after-attempts N`, default 2).
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

    hint_text = resp["hint"]
    rendered = _render_hint_markdown(hint_text)
    html = (
        f'<div style="border-left: 3px solid #b45309; padding: 8px 12px; '
        f'background: #fffbeb; margin: 4px 0; color: #1f2937;">'
        f'<strong>💡 Hint for <code style="color: #1f2937; background: #fef3c7;'
        f' padding: 1px 5px; border-radius: 3px;">{checkpoint_id}</code></strong>'
        f'<div style="margin-top: 4px;">{rendered}</div>'
        f'</div>'
    )
    if HTML is not None:
        display(HTML(html))
        _display_copy_button(hint_text, label="📋 Copy hint")
    else:
        display(html)


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

    # Inline-styled <code> chips for the light-purple solution box. Jupyter's
    # default `.rendered_html code` rule paints code rose-pink on faint-pink,
    # which reads as low-contrast grey against this card's background; force
    # a dark-on-light-purple chip that matches the rest of the card.
    code_chip = (
        'background: #ede9fe; color: #1f2937; padding: 1px 5px;'
        ' border-radius: 3px;'
        " font-family: 'JetBrains Mono', 'Menlo', 'Consolas', monospace;"
    )
    parts = [f'<div style="border-left: 3px solid #6b21a8; padding: 8px 12px; '
             f'background: #faf5ff; margin: 4px 0; color: #1f2937;">'
             f'<strong>💡 Solution for <code style="{code_chip}">'
             f'{checkpoint_id}</code></strong>']
    if resp.get("solution_value"):
        import html as _html
        sv = _html.escape(str(resp["solution_value"]))
        parts.append(
            f'<div style="margin-top: 6px; color: #1f2937;">'
            f'<strong style="color: #1f2937;">Expected answer:</strong> '
            f'<code style="{code_chip}">{sv}</code>'
            f'</div>'
        )
    solution_code_raw: str = ""
    if resp.get("solution_code"):
        raw = str(resp["solution_code"])
        # Belt-and-braces decode of `b64:` payloads. Autoregister wraps the
        # teacher's reference code in base64 to survive the IPython magic
        # parser; `%cadence_register` decodes before sending to the server.
        # If a teacher ever Run-Alled the registered notebook with an older
        # cadence-edu in the kernel (<0.2.9), the server stored the literal
        # `b64:...` string — decoding here means students still see the
        # readable code even before the teacher re-registers with current.
        if raw.startswith("b64:"):
            try:
                import base64 as _b64
                raw = _b64.b64decode(raw[4:].encode("ascii")).decode("utf-8")
            except Exception:
                pass
        # Teachers sometimes pass `\n` as literal escape sequences when using
        # the line magic (--solution-code "...\n..."); interpret those as real
        # newlines so the code block renders multi-line.
        raw = raw.replace("\\n", "\n").replace("\\t", "\t")
        solution_code_raw = raw
        parts.append(
            f'<div style="margin-top: 8px; color: #1f2937;">'
            f'<strong style="color: #1f2937;">Worked solution:</strong>'
            f'</div>'
        )
    parts.append('</div>')
    html = ''.join(parts)
    if HTML is not None:
        display(HTML(html))
        # Display the worked solution as Python-fenced Markdown so Jupyter's
        # renderer applies syntax highlighting (keywords red, strings green,
        # etc.) — much nicer than a plain `<pre>` and the same colours
        # students see in their own cells.
        if solution_code_raw:
            _display_code_block(solution_code_raw)
            _display_copy_button(solution_code_raw, label="📋 Copy code")
        return
    # Fallback for non-IPython environments
    return display(html)
