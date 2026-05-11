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
    hint: Optional[str] = None
    elapsed_ms: Optional[int] = None

    def __bool__(self) -> bool:
        return self.is_correct

    def _format_elapsed(self) -> str:
        if self.elapsed_ms is None:
            return ""
        ms = self.elapsed_ms
        if ms < 1000:
            return f" in {ms} ms"
        return f" in {ms / 1000:.2f} s"

    def _repr_html_(self) -> str:
        if self.is_correct:
            return (
                f'<div style="color: green;">✅ Correct '
                f'(attempt {self.attempt_num}{self._format_elapsed()})</div>'
            )
        hint_html = f'<br><em>Hint: {self.hint}</em>' if self.hint else ''
        return (
            f'<div style="color: #b45309;">❌ Not quite '
            f'(attempt {self.attempt_num}{self._format_elapsed()}){hint_html}</div>'
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
) -> None:
    _course_teacher_state["teacher_token"] = teacher_token
    _course_teacher_state["course_id"] = course_id
    _course_teacher_state["course_name"] = course_name
    _course_teacher_state["join_code"] = join_code
    _course_teacher_state["api"] = api


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
        hint=resp.get("hint"),
        elapsed_ms=resp.get("elapsed_ms"),
    )
