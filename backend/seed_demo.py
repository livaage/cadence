"""Seed a stable, public-facing demo with realistic teacher setup + student activity.

Produces:
  * 1 standalone lesson  — Particle Physics Lab (the headline live-dashboard demo).
  * 2 courses, 2 notebooks each — Intro Stats and Numerical Methods, simulating
    a teacher who runs more than one class.

Run once against the target DB; idempotent — re-running wipes the demo entities'
sessions/attempts and regenerates them so the dashboard URLs stay stable across
re-seeds.

Usage:
    DATABASE_URL='postgresql://...' python seed_demo.py

All teacher_tokens and join codes are intentionally fixed and baked into the
frontend /demo page so visitors can open every dashboard without signing up.
"""
import json
import os
import random
import sys
from datetime import datetime, timedelta
from typing import Optional

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
    Course,
    CourseNotebook,
)

# ------------------------------------------------------------------------------
# Standalone particle-physics lesson — the headline demo dashboard
# ------------------------------------------------------------------------------

DEMO_TEACHER_TOKEN = "demo-particle-physics-readonly-2026"
DEMO_JOIN_CODE = "demo-physics"
DEMO_LESSON_NAME = "Particle Physics Lab — Live Demo"

# Checkpoints mirror demo-teacher-setup.ipynb exactly.
PARTICLE_CHECKPOINTS = [
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
        "allow_submissions": True,
        "order_index": 6,
        "expected_correct": None,
        "common_wrong": [],
    },
]

# Difficulty per particle-physics checkpoint (probability each wrong attempt happens).
PARTICLE_DIFFICULTY = {
    "setup.mean-value": 0.10,
    "setup.row-sums": 0.20,
    "setup.n-above-100": 0.35,
    "discovery.m-gg": 0.50,
    "discovery.higgs-peak": 0.65,
}

# ------------------------------------------------------------------------------
# Course 1: Intro to Statistics — Fall 2026 (2 notebooks)
# ------------------------------------------------------------------------------

STATS_COURSE_TOKEN = "demo-stats-course-readonly-2026"
STATS_COURSE_JOIN = "demo-stats"
STATS_COURSE_NAME = "Intro to Statistics — Fall 2026"

STATS_WEEK1_TOKEN = "demo-stats-week1-readonly-2026"
STATS_WEEK1_JOIN = "demo-stats-w1"
STATS_WEEK1_NAME = "Week 1 — Mean & Median"
STATS_WEEK1_CHECKPOINTS = [
    {
        "checkpoint_id": "mean.basic",
        "comparator": "numeric",
        "expected_payload": json.dumps({"value": 7.0, "tolerance": 0.001}),
        "hint": "sum / count",
        "order_index": 1,
        "expected_correct": "7.0",
        "common_wrong": ["7", "6.5", "7.5", "5.0"],
    },
    {
        "checkpoint_id": "median.odd-n",
        "comparator": "numeric",
        "expected_payload": json.dumps({"value": 8, "tolerance": 0.001}),
        "hint": "middle element of the sorted array",
        "order_index": 2,
        "expected_correct": "8",
        "common_wrong": ["7", "9", "7.5"],
    },
    {
        "checkpoint_id": "median.even-n",
        "comparator": "numeric",
        "expected_payload": json.dumps({"value": 7.5, "tolerance": 0.001}),
        "hint": "average of the two middle elements",
        "order_index": 3,
        "expected_correct": "7.5",
        "common_wrong": ["7", "8", "7.0"],
    },
]
STATS_WEEK1_DIFFICULTY = {
    "mean.basic": 0.10,
    "median.odd-n": 0.25,
    "median.even-n": 0.40,
}

STATS_WEEK2_TOKEN = "demo-stats-week2-readonly-2026"
STATS_WEEK2_JOIN = "demo-stats-w2"
STATS_WEEK2_NAME = "Week 2 — Variance & Spread"
STATS_WEEK2_CHECKPOINTS = [
    {
        "checkpoint_id": "variance.population",
        "comparator": "numeric",
        "expected_payload": json.dumps({"value": 4.0, "tolerance": 0.01}),
        "hint": "ddof=0 for population variance",
        "order_index": 1,
        "expected_correct": "4.0",
        "common_wrong": ["5.0", "2.0", "4"],
    },
    {
        "checkpoint_id": "variance.sample",
        "comparator": "numeric",
        "expected_payload": json.dumps({"value": 5.0, "tolerance": 0.01}),
        "hint": "ddof=1 for sample variance (Bessel's correction)",
        "order_index": 2,
        "expected_correct": "5.0",
        "common_wrong": ["4.0", "6.25", "5"],
    },
    {
        "checkpoint_id": "iqr.basic",
        "comparator": "numeric",
        "expected_payload": json.dumps({"value": 4.0, "tolerance": 0.001}),
        "hint": "Q3 - Q1",
        "order_index": 3,
        "expected_correct": "4.0",
        "common_wrong": ["3.0", "5.0", "2.5"],
    },
]
STATS_WEEK2_DIFFICULTY = {
    "variance.population": 0.20,
    "variance.sample": 0.55,  # ddof trips people up
    "iqr.basic": 0.30,
}

# ------------------------------------------------------------------------------
# Course 2: Numerical Methods — Spring 2026 (2 notebooks)
# ------------------------------------------------------------------------------

NUMERICS_COURSE_TOKEN = "demo-numerics-course-readonly-2026"
NUMERICS_COURSE_JOIN = "demo-numerics"
NUMERICS_COURSE_NAME = "Numerical Methods — Spring 2026"

NUMERICS_ROOTS_TOKEN = "demo-numerics-roots-readonly-2026"
NUMERICS_ROOTS_JOIN = "demo-numerics-w1"
NUMERICS_ROOTS_NAME = "Week 1 — Root Finding"
NUMERICS_ROOTS_CHECKPOINTS = [
    {
        "checkpoint_id": "bisection.iterations",
        "comparator": "numeric",
        "expected_payload": json.dumps({"value": 17, "tolerance": 0.5}),
        "hint": "ceil(log2((b - a) / tol))",
        "order_index": 1,
        "expected_correct": "17",
        "common_wrong": ["16", "18", "20", "10"],
    },
    {
        "checkpoint_id": "bisection.root",
        "comparator": "numeric",
        "expected_payload": json.dumps({"value": 1.414213, "tolerance": 0.001}),
        "hint": "sqrt(2) for f(x) = x² - 2 on [1, 2]",
        "order_index": 2,
        "expected_correct": "1.414213",
        "common_wrong": ["1.41", "1.5", "1.4142"],
    },
    {
        "checkpoint_id": "newton.iterations",
        "comparator": "numeric",
        "expected_payload": json.dumps({"value": 5, "tolerance": 0.5}),
        "hint": "quadratic convergence — count until |f(x)| < 1e-10",
        "order_index": 3,
        "expected_correct": "5",
        "common_wrong": ["6", "4", "10", "7"],
    },
    {
        "checkpoint_id": "newton.root",
        "comparator": "numeric",
        "expected_payload": json.dumps({"value": 1.414213562, "tolerance": 1e-8}),
        "hint": "Newton on x² - 2 from x₀ = 1.5",
        "order_index": 4,
        "expected_correct": "1.414213562",
        "common_wrong": ["1.41421", "1.4142136", "1.5"],
    },
]
NUMERICS_ROOTS_DIFFICULTY = {
    "bisection.iterations": 0.40,
    "bisection.root": 0.20,
    "newton.iterations": 0.55,
    "newton.root": 0.30,
}

NUMERICS_INTEG_TOKEN = "demo-numerics-integ-readonly-2026"
NUMERICS_INTEG_JOIN = "demo-numerics-w2"
NUMERICS_INTEG_NAME = "Week 2 — Numerical Integration"
NUMERICS_INTEG_CHECKPOINTS = [
    {
        "checkpoint_id": "trapezoid.basic",
        "comparator": "numeric",
        "expected_payload": json.dumps({"value": 0.6666, "tolerance": 0.001}),
        "hint": "∫₀¹ x² dx with 100 trapezoids",
        "order_index": 1,
        "expected_correct": "0.6666",
        "common_wrong": ["0.5", "0.6667", "0.333"],
    },
    {
        "checkpoint_id": "simpson.basic",
        "comparator": "numeric",
        "expected_payload": json.dumps({"value": 0.66666666, "tolerance": 1e-6}),
        "hint": "Simpson's 1/3 with 100 subintervals — exact for x²",
        "order_index": 2,
        "expected_correct": "0.66666666",
        "common_wrong": ["0.6666", "0.667", "0.5"],
    },
    {
        "checkpoint_id": "convergence.rate",
        "comparator": "exact",
        "expected_payload": "2",
        "hint": "Trapezoid is O(h^k) — what's k?",
        "order_index": 3,
        "expected_correct": "2",
        "common_wrong": ["4", "1", "3"],
    },
]
NUMERICS_INTEG_DIFFICULTY = {
    "trapezoid.basic": 0.30,
    "simpson.basic": 0.40,
    "convergence.rate": 0.50,
}

# ------------------------------------------------------------------------------
# Shared simulation: student roster + extras only used by the headline lesson.
# ------------------------------------------------------------------------------

# Realistic-but-fictional student names. Mix of given names + initials to read like
# a real class roster without resembling any specific person.
STUDENT_NAMES = [
    "Amelia R.", "Tomás G.", "Priya S.", "Marcus L.", "Noor A.",
    "Felix M.", "Anika P.", "Sofia D.", "Henrik J.", "Yuki K.",
    "Olu A.", "Clara V.", "Daniel S.", "Maya R.",
]

# Extra rosters for the course notebooks so each one has its own feel — same
# teacher, different cohorts. Keeps display_names varied across dashboards.
STATS_W1_ROSTER = [
    "Léa M.", "Karim A.", "Jamie P.", "Bea T.", "Dev S.", "Iris N.", "Owen R.",
    "Hana K.", "Jordan F.", "Linnea S.", "Mateo C.", "Nora H.", "Pia W.",
    "Quentin B.", "Robin L.", "Sasha M.", "Tariq O.", "Uma D.", "Vega P.", "Will F.",
]
STATS_W2_ROSTER = STATS_W1_ROSTER[:18]  # a couple drop the course by week 2
NUMERICS_ROOTS_ROSTER = [
    "Alex C.", "Brynn J.", "Caspar V.", "Devi R.", "Eitan B.", "Frida S.",
    "Goran P.", "Hettie L.", "Ines M.", "Jonas K.", "Kasia W.", "Lior A.",
    "Mira S.", "Niko T.", "Otto F.",
]
NUMERICS_INTEG_ROSTER = NUMERICS_ROOTS_ROSTER[:12]  # a few haven't started week 2 yet

# Pre-rendered student plots for discovery.higgs-peak. Regenerated locally via
# backend/demo_assets/generate_plots.py — the backend container doesn't ship
# matplotlib so we keep the PNGs checked in.
HIGGS_PLOT_SAMPLES = [
    ("Amelia R.", "higgs_amelia.png"),
    ("Priya S.", "higgs_priya.png"),
    ("Henrik J.", "higgs_henrik.png"),
    ("Yuki K.", "higgs_yuki.png"),
]

# Reflection-text submissions for discovery.reflect.
REFLECTION_SAMPLES = [
    (
        "Amelia R.",
        "The bump sits right at 125 GeV on top of an otherwise flat background — "
        "exactly what a narrow resonance looks like. ATLAS and CMS independently "
        "seeing the same peak is what makes it credible as a real particle and "
        "not a statistical fluke.",
    ),
    (
        "Tomás G.",
        "Background is roughly uniform across 100–150 GeV, so the only structure "
        "is the Gaussian-ish excess near 125. The width of the bump in the toy "
        "data is comparable to the bin size, which is the calorimeter resolution "
        "limit in a real analysis.",
    ),
    (
        "Priya S.",
        "Most diphoton pairs are random — they pile up evenly across the mass "
        "range. The Higgs shows up only because its decay always produces the "
        "same invariant mass, so its events stack into a single bin. That's why "
        "high statistics matter: the background averages out, the signal doesn't.",
    ),
    (
        "Marcus L.",
        "If I bin too coarsely the peak smears into the background; too finely "
        "and statistical noise dominates. 1 GeV bins are a decent compromise for "
        "500 events. Real ATLAS uses ~0.5 GeV bins because their detector "
        "resolution is that good and they have 10^9 events to play with.",
    ),
    (
        "Noor A.",
        "The fact that the peak is at an integer GeV value is an artifact of how "
        "I picked the bin edges — the underlying Gaussian is centred at 125.0 in "
        "the toy. Real life: the Higgs mass is measured to be 125.10 ± 0.14 GeV.",
    ),
    (
        "Felix M.",
        "Took me a while to realise that the 'peak' in argmax-of-counts can land "
        "in a neighbouring bin if the random draw happens to fluctuate up there. "
        "More events = more stable peak finder. The look-elsewhere effect is "
        "exactly this problem at the experiment scale.",
    ),
    (
        "Sofia D.",
        "Beautiful that the same recipe — four-vectors, invariant mass, "
        "histogram — gives a textbook discovery plot. The hard part for the "
        "actual experiment is rejecting the QCD diphoton background, not the "
        "histogramming.",
    ),
    (
        "Yuki K.",
        "I plotted with offset bin edges first and got 124, then realised the "
        "bin centre versus left edge ambiguity matters here. Lesson for future "
        "histograms: always print the edges alongside the answer.",
    ),
    (
        "Henrik J.",
        "The signal is a Gaussian with σ ≈ 1.5 GeV sitting on a flat background. "
        "Counting events in a ±3σ window around 125 gives roughly the signal "
        "yield minus the background's share of that window — that's the "
        "simplest 'signal significance' you can compute by hand.",
    ),
    (
        "Olu A.",
        "What surprised me: 80 signal events on 450 background was enough to "
        "see the peak clearly. The real Higgs discovery used about 10⁻⁶ of the "
        "total collision rate, but with 10¹⁰ collisions per second the signal "
        "still racks up fast.",
    ),
]

# Higgs-peak code submissions — three different solution styles.
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


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------

ALL_DEMO_TOKENS = [
    DEMO_TEACHER_TOKEN,
    STATS_WEEK1_TOKEN, STATS_WEEK2_TOKEN,
    NUMERICS_ROOTS_TOKEN, NUMERICS_INTEG_TOKEN,
]
ALL_DEMO_COURSE_TOKENS = [STATS_COURSE_TOKEN, NUMERICS_COURSE_TOKEN]


def reset_demo(db) -> None:
    """Drop every demo lesson + course so the seed is fully idempotent."""
    # Lessons (and everything that references their sessions)
    for tok in ALL_DEMO_TOKENS:
        existing = db.query(Lesson).filter(Lesson.teacher_token == tok).one_or_none()
        if not existing:
            continue
        lid = str(existing.id)
        for s in db.query(LessonSession).filter(LessonSession.lesson_id == lid).all():
            db.query(AttemptEvent).filter(AttemptEvent.session_id == s.id).delete()
            db.query(CodeSubmission).filter(CodeSubmission.session_id == s.id).delete()
            db.query(SolutionReveal).filter(SolutionReveal.session_id == s.id).delete()
            db.delete(s)
        db.query(Checkpoint).filter(Checkpoint.lesson_id == lid).delete()
        db.query(CourseNotebook).filter(CourseNotebook.lesson_id == existing.id).delete()
        db.delete(existing)
    # Courses
    for tok in ALL_DEMO_COURSE_TOKENS:
        course = db.query(Course).filter(Course.teacher_token == tok).one_or_none()
        if not course:
            continue
        # course-level enrollments (sessions joined via course join_code)
        for s in db.query(LessonSession).filter(LessonSession.course_id == str(course.id)).all():
            db.query(AttemptEvent).filter(AttemptEvent.session_id == s.id).delete()
            db.query(CodeSubmission).filter(CodeSubmission.session_id == s.id).delete()
            db.query(SolutionReveal).filter(SolutionReveal.session_id == s.id).delete()
            db.delete(s)
        db.query(CourseNotebook).filter(CourseNotebook.course_id == course.id).delete()
        db.delete(course)
    db.commit()


def create_lesson(
    db,
    *,
    name: str,
    join_code: str,
    teacher_token: str,
    checkpoints: list,
    retention_days: int = 365,
) -> Lesson:
    lesson = Lesson(
        name=name,
        join_code=join_code,
        teacher_token=teacher_token,
        session_retention_days=retention_days,
    )
    db.add(lesson)
    db.flush()
    for cp in checkpoints:
        db.add(Checkpoint(
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
        ))
    return lesson


def create_course(
    db,
    *,
    name: str,
    join_code: str,
    teacher_token: str,
    lesson_ids: list,
) -> Course:
    course = Course(
        name=name,
        join_code=join_code,
        teacher_token=teacher_token,
        session_retention_days=365,
    )
    db.add(course)
    db.flush()
    for order, lesson_id in enumerate(lesson_ids):
        db.add(CourseNotebook(
            course_id=course.id,
            lesson_id=lesson_id,
            order_index=order,
        ))
    return course


def simulate_session(
    db,
    *,
    lesson_id_str: str,
    display_name: str,
    started_at: datetime,
    rng: random.Random,
    checkpoints: list,
    difficulty_map: dict,
    finish_weights: Optional[list] = None,
    course_id_str: Optional[str] = None,
) -> LessonSession:
    """One student's pass through the lab — mixes solid runs, stuck attempts,
    and occasional hint/reveal requests so the dashboard isn't a flat row of
    green ticks. `finish_weights` controls how far through the checkpoints the
    student got (defaults to a slightly-bottom-heavy distribution).

    When `course_id_str` is set, the session is recorded as a course enrollment
    (matches the production flow where a student joins via the course join code
    and then picks a notebook — both lesson_id and course_id end up populated)."""
    session = LessonSession(
        lesson_id=lesson_id_str,
        course_id=course_id_str,
        display_name=display_name,
        started_at=started_at,
        last_seen_at=started_at,
    )
    db.add(session)
    db.flush()

    now = started_at
    n_cp = len(checkpoints)
    if finish_weights is None:
        # Default: most students get most of the way; a few bail early.
        finish_weights = [0.05, 0.10, 0.15, 0.45, 0.25][:n_cp]
        finish_weights = (finish_weights + [0.25] * n_cp)[:n_cp]
    population = list(range(1, n_cp + 1))
    finish_index = rng.choices(population=population, weights=finish_weights, k=1)[0]

    for cp in checkpoints[:finish_index]:
        if cp["comparator"] == "manual":
            db.add(AttemptEvent(
                session_id=session.id,
                lesson_id=lesson_id_str,
                checkpoint_id=cp["checkpoint_id"],
                attempt_num=1,
                submitted_value=None,
                is_correct=True,
                elapsed_ms=rng.randint(30_000, 180_000),
                created_at=now,
            ))
            now += timedelta(seconds=rng.randint(60, 240))
            continue

        difficulty = difficulty_map.get(cp["checkpoint_id"], 0.3)
        wrong_attempts = 0
        while rng.random() < difficulty and wrong_attempts < 7:
            wrong_attempts += 1

        # On the hardest checkpoint (high difficulty), some students give up.
        gives_up = (
            difficulty >= 0.55
            and wrong_attempts >= 4
            and rng.random() < 0.30
        )

        attempt_num = 0
        for _ in range(wrong_attempts):
            attempt_num += 1
            wrong_value = rng.choice(cp["common_wrong"]) if cp["common_wrong"] else "?"
            elapsed = max(8_000, min(int(rng.gauss(45_000, 18_000)), 240_000))
            db.add(AttemptEvent(
                session_id=session.id,
                lesson_id=lesson_id_str,
                checkpoint_id=cp["checkpoint_id"],
                attempt_num=attempt_num,
                submitted_value=wrong_value,
                is_correct=False,
                elapsed_ms=elapsed,
                created_at=now,
            ))
            now += timedelta(milliseconds=elapsed + rng.randint(15_000, 90_000))

        # Reveal: students who struggled on a reveal-enabled checkpoint sometimes ask.
        if (
            cp.get("reveal_after_attempts") is not None
            and wrong_attempts >= cp["reveal_after_attempts"]
            and rng.random() < 0.35
        ):
            db.add(SolutionReveal(
                session_id=session.id,
                lesson_id=lesson_id_str,
                checkpoint_id=cp["checkpoint_id"],
                revealed_at=now,
            ))
            now += timedelta(seconds=rng.randint(30, 120))

        if gives_up:
            session.last_seen_at = now
            return session

        attempt_num += 1
        elapsed = max(5_000, min(int(rng.gauss(30_000, 12_000)), 180_000))
        db.add(AttemptEvent(
            session_id=session.id,
            lesson_id=lesson_id_str,
            checkpoint_id=cp["checkpoint_id"],
            attempt_num=attempt_num,
            submitted_value=cp["expected_correct"],
            is_correct=True,
            elapsed_ms=elapsed,
            created_at=now,
        ))
        now += timedelta(milliseconds=elapsed + rng.randint(30_000, 120_000))

    session.last_seen_at = now
    return session


def seed_lesson_with_roster(
    db,
    *,
    lesson: Lesson,
    roster: list,
    checkpoints: list,
    difficulty_map: dict,
    rng: random.Random,
    hours_window: int = 6,
    course: Optional[Course] = None,
) -> dict:
    """Spread sessions across `hours_window` hours so the dashboard timeline isn't flat.

    Pass `course=` when seeding a notebook inside a course so the LessonSession
    rows get `course_id` set — without it the course-live endpoint reports 0
    enrollments even though attempts are recorded."""
    base = datetime.utcnow() - timedelta(hours=hours_window)
    course_id_str = str(course.id) if course is not None else None
    name_to_session: dict = {}
    for name in roster:
        started = base + timedelta(minutes=rng.randint(0, hours_window * 60 - 10))
        sess = simulate_session(
            db,
            lesson_id_str=str(lesson.id),
            display_name=name,
            started_at=started,
            rng=rng,
            checkpoints=checkpoints,
            difficulty_map=difficulty_map,
            course_id_str=course_id_str,
        )
        name_to_session[name] = sess
    db.flush()
    return name_to_session


def add_code_submissions(db, lesson_id_str: str, name_to_session: dict) -> None:
    for name, code in CODE_SAMPLES:
        sess = name_to_session.get(name)
        if not sess:
            continue
        db.add(CodeSubmission(
            session_id=sess.id,
            lesson_id=lesson_id_str,
            checkpoint_id="discovery.higgs-peak",
            code=code,
            language="python",
            submitted_at=sess.last_seen_at,
        ))


def add_plot_submissions(db, lesson_id_str: str, name_to_session: dict) -> None:
    assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_assets")
    for name, filename in HIGGS_PLOT_SAMPLES:
        sess = name_to_session.get(name)
        if not sess:
            continue
        path = os.path.join(assets_dir, filename)
        if not os.path.exists(path):
            print(f"  warning: plot asset {filename} missing — skipping", file=sys.stderr)
            continue
        with open(path, "rb") as fh:
            png_bytes = fh.read()
        db.add(CodeSubmission(
            session_id=sess.id,
            lesson_id=lesson_id_str,
            checkpoint_id="discovery.higgs-peak",
            code=None,
            language="python",
            image_data=png_bytes,
            image_mime="image/png",
            submitted_at=sess.last_seen_at,
        ))


def add_reflection_submissions(db, lesson_id_str: str, name_to_session: dict) -> None:
    for name, prose in REFLECTION_SAMPLES:
        sess = name_to_session.get(name)
        if not sess:
            continue
        db.add(CodeSubmission(
            session_id=sess.id,
            lesson_id=lesson_id_str,
            checkpoint_id="discovery.reflect",
            code=prose,
            language="text",
            submitted_at=sess.last_seen_at,
        ))


# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------

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

        # ----- Standalone particle physics lesson (the headline dashboard) -----
        physics = create_lesson(
            db,
            name=DEMO_LESSON_NAME,
            join_code=DEMO_JOIN_CODE,
            teacher_token=DEMO_TEACHER_TOKEN,
            checkpoints=PARTICLE_CHECKPOINTS,
        )
        db.commit()
        rng = random.Random(20260523)
        physics_sessions = seed_lesson_with_roster(
            db,
            lesson=physics,
            roster=STUDENT_NAMES,
            checkpoints=PARTICLE_CHECKPOINTS,
            difficulty_map=PARTICLE_DIFFICULTY,
            rng=rng,
        )
        add_code_submissions(db, str(physics.id), physics_sessions)
        add_plot_submissions(db, str(physics.id), physics_sessions)
        add_reflection_submissions(db, str(physics.id), physics_sessions)

        # ----- Course 1: Intro Stats (2 notebooks) -----
        stats_w1 = create_lesson(
            db, name=STATS_WEEK1_NAME, join_code=STATS_WEEK1_JOIN,
            teacher_token=STATS_WEEK1_TOKEN, checkpoints=STATS_WEEK1_CHECKPOINTS,
        )
        stats_w2 = create_lesson(
            db, name=STATS_WEEK2_NAME, join_code=STATS_WEEK2_JOIN,
            teacher_token=STATS_WEEK2_TOKEN, checkpoints=STATS_WEEK2_CHECKPOINTS,
        )
        db.commit()
        stats_course = create_course(
            db, name=STATS_COURSE_NAME, join_code=STATS_COURSE_JOIN,
            teacher_token=STATS_COURSE_TOKEN,
            lesson_ids=[stats_w1.id, stats_w2.id],
        )
        db.flush()
        seed_lesson_with_roster(
            db, lesson=stats_w1, roster=STATS_W1_ROSTER,
            checkpoints=STATS_WEEK1_CHECKPOINTS, difficulty_map=STATS_WEEK1_DIFFICULTY,
            rng=rng, hours_window=72,  # week 1: spread over 3 days
            course=stats_course,
        )
        seed_lesson_with_roster(
            db, lesson=stats_w2, roster=STATS_W2_ROSTER,
            checkpoints=STATS_WEEK2_CHECKPOINTS, difficulty_map=STATS_WEEK2_DIFFICULTY,
            rng=rng, hours_window=24,  # week 2: just started
            course=stats_course,
        )

        # ----- Course 2: Numerical Methods (2 notebooks) -----
        num_roots = create_lesson(
            db, name=NUMERICS_ROOTS_NAME, join_code=NUMERICS_ROOTS_JOIN,
            teacher_token=NUMERICS_ROOTS_TOKEN, checkpoints=NUMERICS_ROOTS_CHECKPOINTS,
        )
        num_integ = create_lesson(
            db, name=NUMERICS_INTEG_NAME, join_code=NUMERICS_INTEG_JOIN,
            teacher_token=NUMERICS_INTEG_TOKEN, checkpoints=NUMERICS_INTEG_CHECKPOINTS,
        )
        db.commit()
        numerics_course = create_course(
            db, name=NUMERICS_COURSE_NAME, join_code=NUMERICS_COURSE_JOIN,
            teacher_token=NUMERICS_COURSE_TOKEN,
            lesson_ids=[num_roots.id, num_integ.id],
        )
        db.flush()
        seed_lesson_with_roster(
            db, lesson=num_roots, roster=NUMERICS_ROOTS_ROSTER,
            checkpoints=NUMERICS_ROOTS_CHECKPOINTS, difficulty_map=NUMERICS_ROOTS_DIFFICULTY,
            rng=rng, hours_window=48,
            course=numerics_course,
        )
        seed_lesson_with_roster(
            db, lesson=num_integ, roster=NUMERICS_INTEG_ROSTER,
            checkpoints=NUMERICS_INTEG_CHECKPOINTS, difficulty_map=NUMERICS_INTEG_DIFFICULTY,
            rng=rng, hours_window=12,
            course=numerics_course,
        )

        db.commit()

        print("Seeded demo:")
        print(f"  standalone lesson '{DEMO_LESSON_NAME}'")
        print(f"    token={DEMO_TEACHER_TOKEN}  join={DEMO_JOIN_CODE}  students={len(STUDENT_NAMES)}")
        print(f"  course '{STATS_COURSE_NAME}'")
        print(f"    token={STATS_COURSE_TOKEN}  join={STATS_COURSE_JOIN}")
        print(f"    notebook '{STATS_WEEK1_NAME}'  students={len(STATS_W1_ROSTER)}")
        print(f"    notebook '{STATS_WEEK2_NAME}'  students={len(STATS_W2_ROSTER)}")
        print(f"  course '{NUMERICS_COURSE_NAME}'")
        print(f"    token={NUMERICS_COURSE_TOKEN}  join={NUMERICS_COURSE_JOIN}")
        print(f"    notebook '{NUMERICS_ROOTS_NAME}'  students={len(NUMERICS_ROOTS_ROSTER)}")
        print(f"    notebook '{NUMERICS_INTEG_NAME}'  students={len(NUMERICS_INTEG_ROSTER)}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
