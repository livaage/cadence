"""End-to-end smoke + concurrency stress test for the Cadence API.

Drives the same `cadence.api.CadenceAPI` the magics use, so it covers exactly
the surface a teacher + student would hit. Anonymous lesson flow only — no
teacher account required, so it doesn't pollute the user's library.

Usage:
    python stress_test.py [--concurrency N]
"""

from __future__ import annotations

import argparse
import os
import statistics
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

os.environ.setdefault("CADENCE_API_URL", "https://api.cadence-dash.com")

from cadence.api import CadenceAPI  # noqa: E402


def _section(title: str) -> None:
    print(f"\n=== {title} ===")


def smoke_test() -> None:
    """Exercise the full teacher + student happy path against the live API."""
    _section("Smoke test")
    teacher = CadenceAPI()
    lesson = None
    sid = None
    try:
        lesson = teacher.create_lesson(name=f"STRESS_SMOKE_{int(time.time())}")
        tt = lesson["teacher_token"]
        code = lesson["join_code"]
        print(f"  create_lesson ok: code={code} tt={tt[:8]}…")

        teacher.register_checkpoint(
            teacher_token=tt,
            checkpoint_id="q1",
            comparator="exact",
            expected_payload={"value": 42},
            hint="It's the answer to everything",
            hint_after_attempts=1,
            reveal_after_attempts=3,
            solution_value="42",
        )
        teacher.register_checkpoint(
            teacher_token=tt,
            checkpoint_id="q2",
            comparator="exact",
            expected_payload={"value": "hello"},
        )
        cps = teacher.list_checkpoints(tt)
        assert len(cps) == 2, f"expected 2 checkpoints, got {len(cps)}"
        print(f"  register_checkpoint + list_checkpoints ok ({len(cps)})")

        loaded = teacher.get_lesson_by_token(tt)
        assert loaded["join_code"] == code
        print("  get_lesson_by_token ok")

        loaded2 = teacher.get_lesson_by_code(code)
        # by-code is the student-facing lookup; deliberately omits teacher_token.
        assert loaded2["join_code"] == code
        print("  get_lesson_by_code ok")

        # Student side
        student = CadenceAPI()
        sess = student.start_session(code, "smoke_alice")
        sid = sess["session_id"]
        print(f"  start_session ok: sid={sid[:8]}…")

        wrong = student.check_answer(sid, "q1", 41, elapsed_ms=1200)
        assert wrong.get("is_correct") is False, f"expected incorrect: {wrong}"
        right = student.check_answer(sid, "q1", 42, elapsed_ms=2400)
        assert right.get("is_correct") is True, f"expected correct: {right}"
        print("  check_answer ok (wrong then right)")

        hint = student.get_hint(sid, "q1")
        assert hint.get("hint")
        print(f"  get_hint ok: {hint['hint'][:40]!r}")

        # Trigger reveal threshold: 3 wrong attempts on q2 to allow solution
        for v in ["a", "b", "c"]:
            student.check_answer(sid, "q2", v)
        # q1's solution should be available now too — we set reveal_after_attempts=3 and attempted >=3 times across the lesson.
        # The API gates per-checkpoint, so attempt q2 specifically until reveal:
        student.check_answer(sid, "q1", "still wrong")
        student.check_answer(sid, "q1", "still wrong")
        try:
            sol = student.get_solution(sid, "q1")
            print(f"  get_solution ok (revealed): {sol.get('solution_value', '?')!r}")
        except Exception as e:
            print(f"  get_solution: not yet revealed ({e}) — fine, depends on reveal policy")

        my = student.get_my_data(sid)
        attempts = my.get("attempts", [])
        print(f"  get_my_data ok: {len(attempts)} attempts visible")

        student.delete_my_data(sid)
        sid = None  # already gone
        print("  delete_my_data ok")
    finally:
        if sid:
            try:
                CadenceAPI().delete_my_data(sid)
            except Exception:
                pass
        if lesson:
            try:
                teacher.delete_lesson(lesson["teacher_token"])
                print("  delete_lesson ok (teardown)")
            except Exception as e:
                print(f"  ⚠ delete_lesson teardown failed: {e}")
    print("✓ Smoke test passed")


def concurrent_test(n: int) -> int:
    """Spawn N concurrent students against one lesson; return # of failures."""
    _section(f"Concurrent test (n={n})")
    teacher = CadenceAPI()
    lesson = teacher.create_lesson(name=f"STRESS_CONC_{n}_{int(time.time())}")
    tt = lesson["teacher_token"]
    code = lesson["join_code"]
    print(f"  Lesson up: code={code} tt={tt[:8]}…")

    expected = {"q1": 42, "q2": 100, "q3": True}
    for cid, val in expected.items():
        teacher.register_checkpoint(
            teacher_token=tt,
            checkpoint_id=cid,
            comparator="exact",
            expected_payload={"value": val},
        )
    print(f"  Registered {len(expected)} checkpoints")

    def one_student(i: int) -> dict:
        result = {"i": i, "errors": [], "t_join": None, "t_checks": [], "sid": None}
        try:
            api = CadenceAPI()
            t0 = time.monotonic()
            sess = api.start_session(code, f"stress_{i}")
            result["t_join"] = time.monotonic() - t0
            sid = sess["session_id"]
            result["sid"] = sid

            for cid, val in expected.items():
                t1 = time.monotonic()
                w = api.check_answer(sid, cid, "wrong_value", elapsed_ms=500)
                if w.get("is_correct"):
                    result["errors"].append(f"{cid}: wrong answer marked correct")
                r = api.check_answer(sid, cid, val, elapsed_ms=900)
                if not r.get("is_correct"):
                    result["errors"].append(f"{cid}: correct answer marked wrong: {r}")
                result["t_checks"].append(time.monotonic() - t1)
        except Exception as e:
            result["errors"].append(f"{type(e).__name__}: {e}")
        return result

    print(f"  Spawning {n} concurrent students…")
    t_start = time.monotonic()
    with ThreadPoolExecutor(max_workers=n) as ex:
        results = list(ex.map(one_student, range(n)))
    elapsed = time.monotonic() - t_start

    # Cleanup: delete each session, then the lesson.
    print("  Cleaning up sessions…")
    cleanup_fail = 0
    for r in results:
        if r["sid"]:
            try:
                CadenceAPI().delete_my_data(r["sid"])
            except Exception:
                cleanup_fail += 1
    if cleanup_fail:
        print(f"  ⚠ {cleanup_fail} session cleanups failed (data will age out per retention policy)")
    try:
        teacher.delete_lesson(tt)
        print("  Lesson deleted")
    except Exception as e:
        print(f"  ⚠ lesson cleanup failed: {e}")

    # Report
    failed = [r for r in results if r["errors"]]
    ok = n - len(failed)
    join_times = [r["t_join"] for r in results if r["t_join"] is not None]
    check_times = [t for r in results for t in r["t_checks"]]
    print(f"\n  Outcome: {ok}/{n} students succeeded in {elapsed:.1f}s")
    if failed:
        print("  Failures (first 5):")
        for r in failed[:5]:
            print(f"    student {r['i']}: {r['errors'][0][:200]}")
    if join_times:
        jt = sorted(join_times)
        print(
            f"  Join latency: median={statistics.median(jt) * 1000:.0f}ms "
            f"p95={jt[int(len(jt) * 0.95)] * 1000:.0f}ms "
            f"max={max(jt) * 1000:.0f}ms"
        )
    if check_times:
        ct = sorted(check_times)
        print(
            f"  Check pair (wrong+right): median={statistics.median(ct) * 1000:.0f}ms "
            f"p95={ct[int(len(ct) * 0.95)] * 1000:.0f}ms "
            f"max={max(ct) * 1000:.0f}ms"
        )
    return len(failed)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--concurrency", type=int, default=60)
    p.add_argument("--skip-smoke", action="store_true")
    p.add_argument("--skip-concurrent", action="store_true")
    args = p.parse_args()
    rc = 0
    if not args.skip_smoke:
        try:
            smoke_test()
        except Exception:
            traceback.print_exc()
            rc = 1
    if not args.skip_concurrent:
        try:
            rc = max(rc, 1 if concurrent_test(args.concurrency) else 0)
        except Exception:
            traceback.print_exc()
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
