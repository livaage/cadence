"""Seed a stable, public-facing demo lesson with realistic student activity.

Run once against the target DB; idempotent — re-running wipes the demo lesson's
sessions/attempts and regenerates them so the dashboard URL stays stable across
re-seeds.

Usage:
    DATABASE_URL='postgresql://...' python seed_demo.py

The teacher_token and join_code are intentionally fixed and baked into the
frontend /demo page so visitors can open the dashboard without signing up.
"""
import json
import os
import random
import sys
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Make this script runnable from any cwd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import (
    Lesson,
    Checkpoint,
    LessonSession,
    AttemptEvent,
    CodeSubmission,
    SolutionReveal,
)

DEMO_TEACHER_TOKEN = "demo-particle-physics-readonly-2026"
DEMO_JOIN_CODE = "demo-physics"
DEMO_LESSON_NAME = "Particle Physics Lab — Live Demo"

# Checkpoints mirror demo-teacher-setup.ipynb exactly.
CHECKPOINTS = [
    {
        "checkpoint_id": "setup.mean-value",
        "comparator": "numeric",
        "expected_payload": json.dumps({"value": 49.5, "tolerance": 0.001}),
        "hint": "average of 0..99",
        "order_index": 1,
        "expected_correct": "49.5",
        "common_wrong": ["50.0", "49", "50"],
    },
    {
        "checkpoint_id": "setup.row-sums",
        "comparator": "set",
        "expected_payload": json.dumps({"value": [6, 22, 38]}),
        "hint": "axis=1",
        "order_index": 2,
        "expected_correct": "[6, 22, 38]",
        "common_wrong": ["[18, 22, 26]", "[6, 22, 38, 54]", "[0, 22, 38]"],
    },
    {
        "checkpoint_id": "setup.n-above-100",
        "comparator": "numeric",
        "expected_payload": json.dumps({"value": 150}),
        "hint": "boolean mask + sum, with the seed-42 draw",
        "order_index": 3,
        "expected_correct": "150",
        "common_wrong": ["149", "151", "143", "0"],
    },
    {
        "checkpoint_id": "discovery.m-gg",
        "comparator": "numeric",
        "expected_payload": json.dumps({"value": 163.08, "tolerance": 0.05}),
        "hint": "invariant mass formula — watch the signs",
        "order_index": 4,
        "expected_correct": "163.08",
        "common_wrong": ["162.50", "164.12", "0.0", "121.4"],
    },
    {
        "checkpoint_id": "discovery.higgs-peak",
        "comparator": "exact",
        "expected_payload": "125",
        "hint": "integer centre of the 1-GeV bin with the most events",
        "reveal_after_attempts": 3,
        "solution_value": "125",
        "solution_code": (
            "bin_edges = np.arange(100, 151)\n"
            "counts, _ = np.histogram(m_gamma_gamma, bins=bin_edges)\n"
            "int(bin_edges[np.argmax(counts)])"
        ),
        "allow_submissions": True,
        "order_index": 5,
        "expected_correct": "125",
        "common_wrong": ["124", "126", "127", "120"],
    },
    {
        "checkpoint_id": "discovery.reflect",
        "comparator": "manual",
        "expected_payload": None,
        "hint": "Briefly describe what the peak shape tells you.",
        "order_index": 6,
        "expected_correct": None,
        "common_wrong": [],
    },
]

# Realistic-but-fictional student names. Mix of given names + initials to read like
# a real class roster without resembling any specific person.
STUDENT_NAMES = [
    "Amelia R.",
    "Tomás G.",
    "Priya S.",
    "Marcus L.",
    "Noor A.",
    "Felix M.",
    "Anika P.",
    "Sofia D.",
    "Henrik J.",
    "Yuki K.",
    "Olu A.",
    "Clara V.",
    "Daniel S.",
    "Maya R.",
]

# Higgs-peak code submissions — three different solution styles for the dashboard
# code feed. Real teachers find this useful; we want the demo to showcase it.
CODE_SAMPLES = [
    (
        "Amelia R.",
        """rng = np.random.default_rng(1)
background = rng.uniform(100.0, 150.0, size=450)
signal     = rng.normal(loc=125.0, scale=1.5, size=80)
m_gamma_gamma = np.concatenate([background, signal])

bin_edges = np.arange(100, 151)
counts, _ = np.histogram(m_gamma_gamma, bins=bin_edges)

peak_idx = int(np.argmax(counts))
peak_bin_center = int(bin_edges[peak_idx])
check("discovery.higgs-peak", peak_bin_center)""",
    ),
    (
        "Priya S.",
        """# argmax of histogram counts, picked the left edge as integer centre
counts, edges = np.histogram(m_gamma_gamma, bins=np.arange(100, 151))
ans = int(edges[counts.argmax()])
check("discovery.higgs-peak", ans)""",
    ),
    (
        "Henrik J.",
        """# loop to be explicit about what \"bin centre\" means
counts = [0] * 50
for m in m_gamma_gamma:
    if 100 <= m < 150:
        counts[int(m) - 100] += 1
best = max(range(50), key=lambda i: counts[i])
check(\"discovery.higgs-peak\", 100 + best)""",
    ),
]


def reset_demo(db) -> None:
    """Drop and re-create the demo lesson so the seed is idempotent."""
    existing = db.query(Lesson).filter(Lesson.teacher_token == DEMO_TEACHER_TOKEN).one_or_none()
    if existing:
        lesson_id_str = str(existing.id)
        # Clear attempts/submissions/reveals tied to this lesson's sessions.
        sessions = db.query(LessonSession).filter(LessonSession.lesson_id == lesson_id_str).all()
        for s in sessions:
            db.query(AttemptEvent).filter(AttemptEvent.session_id == s.id).delete()
            db.query(CodeSubmission).filter(CodeSubmission.session_id == s.id).delete()
            db.query(SolutionReveal).filter(SolutionReveal.session_id == s.id).delete()
            db.delete(s)
        db.query(Checkpoint).filter(Checkpoint.lesson_id == lesson_id_str).delete()
        db.delete(existing)
        db.commit()


def create_lesson_and_checkpoints(db) -> Lesson:
    lesson = Lesson(
        name=DEMO_LESSON_NAME,
        join_code=DEMO_JOIN_CODE,
        teacher_token=DEMO_TEACHER_TOKEN,
        session_retention_days=365,  # long horizon — this lesson is on display
    )
    db.add(lesson)
    db.flush()  # populate lesson.id

    for cp in CHECKPOINTS:
        db.add(
            Checkpoint(
                lesson_id=str(lesson.id),
                checkpoint_id=cp["checkpoint_id"],
                comparator=cp["comparator"],
                expected_payload=cp["expected_payload"],
                hint=cp["hint"],
                hint_after_attempts=1,
                reveal_after_attempts=cp.get("reveal_after_attempts"),
                solution_value=cp.get("solution_value"),
                solution_code=cp.get("solution_code"),
                allow_submissions=cp.get("allow_submissions", False),
                order_index=cp["order_index"],
            )
        )
    db.commit()
    return lesson


def simulate_session(
    db,
    lesson_id_str: str,
    display_name: str,
    started_at: datetime,
    rng: random.Random,
) -> None:
    """One student's pass through the lab — mixes solid runs, stuck attempts,
    and the occasional hint/reveal request so the dashboard isn't a flat row of
    green ticks."""
    session = LessonSession(
        lesson_id=lesson_id_str,
        display_name=display_name,
        started_at=started_at,
        last_seen_at=started_at,
    )
    db.add(session)
    db.flush()

    now = started_at
    # How far through the lab this student got. Most finish, some bail.
    finish_index = rng.choices(
        population=[2, 3, 4, 5, 6],
        weights=[0.05, 0.10, 0.15, 0.55, 0.15],
        k=1,
    )[0]

    for i, cp in enumerate(CHECKPOINTS[:finish_index]):
        # Manual checkpoints are mark_done-only — model as a single is_correct=True
        # attempt with submitted_value = None, which matches what /attempts records.
        if cp["comparator"] == "manual":
            attempt = AttemptEvent(
                session_id=session.id,
                lesson_id=lesson_id_str,
                checkpoint_id=cp["checkpoint_id"],
                attempt_num=1,
                submitted_value=None,
                is_correct=True,
                elapsed_ms=rng.randint(30_000, 180_000),
                created_at=now,
            )
            db.add(attempt)
            now += timedelta(seconds=rng.randint(60, 240))
            continue

        # Difficulty per checkpoint — Higgs peak is the toughest, row-sums the easiest.
        difficulty = {
            "setup.mean-value": 0.10,
            "setup.row-sums": 0.20,
            "setup.n-above-100": 0.35,
            "discovery.m-gg": 0.50,
            "discovery.higgs-peak": 0.65,
        }.get(cp["checkpoint_id"], 0.3)

        wrong_attempts = 0
        # Each wrong attempt has probability `difficulty` of happening; cap at 7.
        while rng.random() < difficulty and wrong_attempts < 7:
            wrong_attempts += 1

        # Some students never solve the hardest checkpoint — bail out 25% of the time
        # when they hit 5+ wrong attempts on discovery.higgs-peak.
        gives_up = (
            cp["checkpoint_id"] == "discovery.higgs-peak"
            and wrong_attempts >= 4
            and rng.random() < 0.35
        )

        attempt_num = 0
        for w in range(wrong_attempts):
            attempt_num += 1
            wrong_value = rng.choice(cp["common_wrong"]) if cp["common_wrong"] else "?"
            elapsed = int(rng.gauss(45_000, 18_000))
            elapsed = max(8_000, min(elapsed, 240_000))
            db.add(
                AttemptEvent(
                    session_id=session.id,
                    lesson_id=lesson_id_str,
                    checkpoint_id=cp["checkpoint_id"],
                    attempt_num=attempt_num,
                    submitted_value=wrong_value,
                    is_correct=False,
                    elapsed_ms=elapsed,
                    created_at=now,
                )
            )
            now += timedelta(milliseconds=elapsed + rng.randint(15_000, 90_000))

        # Solution reveal: a few students who get stuck on Higgs ask for the answer.
        if cp["checkpoint_id"] == "discovery.higgs-peak" and wrong_attempts >= 3 and rng.random() < 0.35:
            db.add(
                SolutionReveal(
                    session_id=session.id,
                    lesson_id=lesson_id_str,
                    checkpoint_id=cp["checkpoint_id"],
                    revealed_at=now,
                )
            )
            now += timedelta(seconds=rng.randint(30, 120))

        if gives_up:
            session.last_seen_at = now
            return

        # Correct attempt.
        attempt_num += 1
        elapsed = int(rng.gauss(30_000, 12_000))
        elapsed = max(5_000, min(elapsed, 180_000))
        db.add(
            AttemptEvent(
                session_id=session.id,
                lesson_id=lesson_id_str,
                checkpoint_id=cp["checkpoint_id"],
                attempt_num=attempt_num,
                submitted_value=cp["expected_correct"],
                is_correct=True,
                elapsed_ms=elapsed,
                created_at=now,
            )
        )
        now += timedelta(milliseconds=elapsed + rng.randint(30_000, 120_000))

    session.last_seen_at = now


def add_code_submissions(db, lesson_id_str: str, name_to_session: dict) -> None:
    for name, code in CODE_SAMPLES:
        sess = name_to_session.get(name)
        if not sess:
            continue
        db.add(
            CodeSubmission(
                session_id=sess.id,
                lesson_id=lesson_id_str,
                checkpoint_id="discovery.higgs-peak",
                code=code,
                language="python",
                submitted_at=sess.last_seen_at,
            )
        )


def main() -> None:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not set", file=sys.stderr)
        sys.exit(1)

    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        reset_demo(db)
        lesson = create_lesson_and_checkpoints(db)
        lesson_id_str = str(lesson.id)

        rng = random.Random(20260523)  # stable seed → reproducible demo
        # Stagger start times across the last ~6 hours so the dashboard's
        # "recent activity" timeline isn't a single flat line.
        base = datetime.utcnow() - timedelta(hours=6)
        name_to_session: dict = {}
        for i, name in enumerate(STUDENT_NAMES):
            started = base + timedelta(minutes=rng.randint(0, 300))
            simulate_session(db, lesson_id_str, name, started, rng)
            db.flush()
            # Track the most recent session per name for code submissions.
            sess = (
                db.query(LessonSession)
                .filter(
                    LessonSession.lesson_id == lesson_id_str,
                    LessonSession.display_name == name,
                )
                .order_by(LessonSession.started_at.desc())
                .first()
            )
            if sess:
                name_to_session[name] = sess

        add_code_submissions(db, lesson_id_str, name_to_session)
        db.commit()

        print(f"Seeded demo lesson '{lesson.name}'")
        print(f"  lesson_id      = {lesson.id}")
        print(f"  join_code      = {lesson.join_code}")
        print(f"  teacher_token  = {lesson.teacher_token}")
        print(f"  sessions       = {len(STUDENT_NAMES)}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
