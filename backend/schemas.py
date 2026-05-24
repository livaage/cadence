from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from uuid import UUID

# Problem schemas
class ProblemBase(BaseModel):
    title: str
    description: str
    difficulty: Optional[str] = None
    time_limit: Optional[int] = 30
    memory_limit: Optional[int] = 512

class ProblemCreate(ProblemBase):
    pass

class Problem(ProblemBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        from_attributes = True

# Test case schemas
class TestCaseBase(BaseModel):
    input_data: str
    expected_output: str
    is_hidden: bool = False
    points: int = 1

class TestCaseCreate(TestCaseBase):
    problem_id: UUID

class TestCase(TestCaseBase):
    id: UUID
    problem_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

# Submission schemas
class SubmissionBase(BaseModel):
    student_name: str
    student_email: Optional[str] = None
    language: str
    source_code: str

class SubmissionCreate(SubmissionBase):
    problem_id: UUID

class Submission(SubmissionBase):
    id: UUID
    problem_id: UUID
    status: str
    total_score: int
    total_points: int
    execution_time_ms: Optional[int] = None
    memory_usage_mb: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Test result schemas
class TestResultBase(BaseModel):
    status: str
    actual_output: Optional[str] = None
    execution_time_ms: Optional[int] = None
    memory_usage_mb: Optional[int] = None
    error_message: Optional[str] = None
    points_earned: int = 0

class TestResultCreate(TestResultBase):
    submission_id: UUID
    test_case_id: UUID

class TestResult(TestResultBase):
    id: UUID
    submission_id: UUID
    test_case_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

# Teacher schemas
class TeacherBase(BaseModel):
    username: str
    email: EmailStr

class TeacherCreate(TeacherBase):
    password: str

class Teacher(TeacherBase):
    id: UUID
    is_active: bool
    created_at: datetime
    accepted_terms_at: Optional[datetime] = None
    # True if the teacher has a local password set (can log in via username +
    # password from Jupyter or the web form). False for OAuth-only accounts —
    # the UI uses this to prompt them to set one.
    has_password: bool = False

    class Config:
        from_attributes = True


class SetPasswordRequest(BaseModel):
    # Required when changing an existing password; omitted when setting one
    # for the first time on an OAuth-only account.
    current_password: Optional[str] = None
    new_password: str


# Authentication schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Statistics schemas
class ProblemStats(BaseModel):
    problem_id: UUID
    problem_title: str
    total_submissions: int
    correct_submissions: int
    average_score: float
    average_time_ms: float
    average_memory_mb: float

class SubmissionWithResults(BaseModel):
    submission: Submission
    test_results: List[TestResult]
    problem: Problem

# API Response schemas
class SubmissionResponse(BaseModel):
    submission_id: UUID
    status: str
    message: str

# GitHub Repository schemas
class GitHubRepoBase(BaseModel):
    repo_name: str
    repo_url: str
    repo_owner: str
    branch: str = "main"
    folder_structure: Optional[str] = None

class GitHubRepoCreate(GitHubRepoBase):
    problem_id: UUID
    access_token: Optional[str] = None

class GitHubRepo(GitHubRepoBase):
    id: UUID
    problem_id: UUID
    last_sync: Optional[datetime] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Student Commit schemas
class StudentCommitBase(BaseModel):
    student_name: str
    student_email: Optional[str] = None
    commit_hash: str
    commit_message: str
    commit_date: datetime
    files_changed: Optional[str] = None
    code_content: Optional[str] = None
    language: Optional[str] = None

class StudentCommitCreate(StudentCommitBase):
    github_repo_id: UUID

class StudentCommit(StudentCommitBase):
    id: UUID
    github_repo_id: UUID
    status: str
    total_score: int
    total_points: int
    execution_time_ms: Optional[int] = None
    memory_usage_mb: Optional[int] = None
    error_message: Optional[str] = None
    evaluated_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Commit Test Result schemas
class CommitTestResultBase(BaseModel):
    status: str
    actual_output: Optional[str] = None
    execution_time_ms: Optional[int] = None
    memory_usage_mb: Optional[int] = None
    error_message: Optional[str] = None
    points_earned: int = 0

class CommitTestResultCreate(CommitTestResultBase):
    student_commit_id: UUID
    test_case_id: UUID

class CommitTestResult(CommitTestResultBase):
    id: UUID
    student_commit_id: UUID
    test_case_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

# GitHub Sync schemas
class GitHubSyncRequest(BaseModel):
    repo_id: UUID
    force_sync: bool = False

class GitHubSyncResponse(BaseModel):
    success: bool
    message: str
    commits_found: int
    commits_processed: int

class StudentCommitWithResults(BaseModel):
    student_commit: StudentCommit
    commit_test_results: List[CommitTestResult]
    github_repo: GitHubRepo
    problem: Problem


# Checkpoint / lesson-progress schemas
class LessonCreate(BaseModel):
    name: str
    # Optional preferred codes (teacher can pick memorable ones). Server
    # rejects on collision so the client can retry with its default generator.
    join_code: Optional[str] = None
    teacher_token: Optional[str] = None
    # Override the 7-day default at creation time. After the lesson exists,
    # retention can only be SHORTENED via PATCH /lessons/.../retention — never
    # extended, so the value chosen here is the upper bound for this lesson's
    # life. Must be 1–365 if provided.
    session_retention_days: Optional[int] = None


class LessonSummary(BaseModel):
    id: UUID
    name: str
    join_code: str
    teacher_token: str
    session_retention_days: int = 7
    created_at: datetime

    class Config:
        from_attributes = True


class LessonPublicSummary(BaseModel):
    """What a student's client sees after joining — no teacher_token."""
    id: UUID
    name: str
    join_code: str


class CheckpointSummary(BaseModel):
    checkpoint_id: str
    comparator: str
    expected_payload: Optional[str] = None  # null for `manual` (no expected answer)
    hint: Optional[str] = None
    hint_after_attempts: int = 1
    order_index: int
    reveal_after_attempts: Optional[int] = None
    has_solution_value: bool = False
    has_solution_code: bool = False


class CheckpointRegister(BaseModel):
    checkpoint_id: str
    comparator: str  # "exact" | "numeric" | "set" | "regex" | "manual"
    # JSON-encoded; shape depends on comparator. For `manual`, omit (no auto-check).
    expected_payload: Optional[str] = None
    hint: Optional[str] = None
    # Number of wrong attempts after which the student can run cadence.show_hint().
    # Default 1 = available from the first wrong attempt. No upper bound enforced.
    hint_after_attempts: int = 1
    order_index: int = 0
    # Solution reveal — opt-in per checkpoint. When `reveal_after_attempts` is set,
    # students who have made that many attempts can fetch whichever of
    # `solution_value` / `solution_code` are non-empty.
    reveal_after_attempts: Optional[int] = None
    solution_value: Optional[str] = None
    solution_code: Optional[str] = None
    # Opt-in: when true, students can submit code via `%%cadence_submit` for the teacher to review.
    allow_submissions: bool = False


class CodeSubmissionRequest(BaseModel):
    session_id: UUID
    checkpoint_id: str
    code: Optional[str] = None  # nullable for image-only submissions
    language: str = "python"
    image_data_b64: Optional[str] = None  # base64-encoded image payload
    image_mime: Optional[str] = None      # e.g. 'image/png'


class CodeSubmissionEntry(BaseModel):
    id: str
    checkpoint_id: str
    code: Optional[str] = None
    language: str
    submitted_at: datetime
    display_name: Optional[str] = None  # null when caller is anonymising
    image_data_b64: Optional[str] = None
    image_mime: Optional[str] = None


class SessionStart(BaseModel):
    display_name: str


class SessionStartResponse(BaseModel):
    session_id: UUID
    lesson_id: str
    display_name: str


class CheckRequest(BaseModel):
    session_id: UUID
    checkpoint_id: str
    submitted_value: str  # JSON-encoded representation of the student's answer
    elapsed_ms: Optional[int] = None  # set by %%time_check; None for plain check()


class CheckResponse(BaseModel):
    is_correct: bool
    attempt_num: int
    elapsed_ms: Optional[int] = None
    # True when the checkpoint is `manual` (self-attestation, no automatic check).
    # The Python `CheckResult` repr uses this to render "✅ Marked done" rather
    # than "✅ Correct".
    is_manual: bool = False
    # True once this session's wrong-attempt count for this checkpoint has reached
    # the teacher-configured `hint_after_attempts` threshold AND the checkpoint has
    # a hint configured. The student opts in by running cadence.show_hint("<id>").
    hint_available: bool = False
    # True once this session's attempt count for this checkpoint has reached the
    # teacher-configured `reveal_after_attempts` threshold. The student can then
    # call `cadence.show_solution("<checkpoint_id>")` to fetch the worked solution.
    solution_available: bool = False


class HintResponse(BaseModel):
    """Returned by GET /sessions/{sid}/checkpoints/{cp}/hint once the student
    has made enough wrong attempts. Mirrors SolutionResponse."""
    checkpoint_id: str
    hint: str


class SolutionResponse(BaseModel):
    """Returned by GET /sessions/{sid}/checkpoints/{cp}/solution once the
    student has made enough attempts. Both fields may be set; render whichever
    is non-empty."""
    checkpoint_id: str
    solution_value: Optional[str] = None
    solution_code: Optional[str] = None


class TimingSample(BaseModel):
    """Per-student timing of their first-correct attempt for one checkpoint."""
    display_name: str
    elapsed_ms: int


class CheckpointLiveStats(BaseModel):
    checkpoint_id: str
    order_index: int
    comparator: str  # "exact" | "numeric" | "set" | "regex" | "manual"
    attempted: int  # distinct sessions that tried
    solved: int  # distinct sessions that got it right
    total_attempts: int
    attempts_histogram: dict  # {"1": 10, "2": 4, "3+": 2, "unsolved": 3}
    # common_wrong items are dicts: {"value": str, "count": int, "student_names": [str]}
    common_wrong: List[dict]
    # Correct-attempt timing histogram (only populated when %%time_check was used).
    # Keys are fixed time buckets; value is count of correct attempts in that bucket.
    timing_histogram: dict
    timing_samples: int  # how many attempts contributed to the timing histogram
    # Per-sample detail behind the timing histogram — drives the hover-to-see-who
    # tooltip. Frontend respects the dashboard's "show names" toggle for display.
    timing_samples_detail: List[TimingSample] = []
    # Mean attempts per attempting session — counts up to and including the first
    # correct attempt for solvers, or all attempts for sessions that never solved.
    # Drives the relative difficulty chip on the dashboard. Null if no attempts yet.
    avg_attempts: Optional[float] = None
    # Hint teacher-configuration for the dashboard ("hint at attempt 2", etc).
    has_hint: bool = False
    hint_after_attempts: int = 1
    # Solution-reveal teacher-configuration + viewer count for the dashboard.
    reveal_after_attempts: Optional[int] = None
    has_solution: bool = False
    solution_views: int = 0  # distinct sessions that called show_solution() against this checkpoint
    # Code submissions opt-in + count for the dashboard.
    allow_submissions: bool = False
    submission_count: int = 0  # total submissions (multiple per student allowed)


class AttemptLogEntry(BaseModel):
    """One submitted attempt against any checkpoint, in chronological order.
    Drives the per-student drill-in chronology on the dashboard."""
    checkpoint_id: str
    attempt_num: int
    is_correct: bool
    submitted_value: Optional[str] = None
    elapsed_ms: Optional[int] = None
    created_at: datetime


class StudentCheckpointDetail(BaseModel):
    checkpoint_id: str
    status: str  # 'solved' | 'attempted' | 'untouched'
    attempts: int
    first_correct_attempt: Optional[int] = None
    elapsed_ms_first_correct: Optional[int] = None


class StudentRosterEntry(BaseModel):
    session_id: str
    display_name: str
    last_seen_at: datetime
    total_attempts: int
    checkpoints_solved: int
    checkpoints_attempted: int
    # Fastest first-correct elapsed_ms across every checkpoint this student got right
    fastest_elapsed_ms: Optional[int] = None
    # Checkpoint of the student's most recent attempt — "where they are right now"
    current_checkpoint_id: Optional[str] = None
    per_checkpoint: List[StudentCheckpointDetail]
    # Full chronological log of attempts (capped at 50 most recent) — drives the
    # per-student drill-in. Lets a teacher see exactly what sequence of answers
    # the student tried and how long they spent.
    chronology: List[AttemptLogEntry] = []


class LessonSummaryStats(BaseModel):
    """Lesson-wide aggregates for the top of the dashboard."""
    total_sessions: int
    total_checkpoints: int
    total_attempts: int
    total_solved_pairs: int  # sum of (session, checkpoint) that were solved at least once
    possible_pairs: int  # total_sessions * total_checkpoints
    solve_rate_pct: float  # total_solved_pairs / possible_pairs * 100
    completion_histogram: dict  # {"0": n, "1": n, ... "<total_checkpoints>": n}
    top_wrong_overall: List[dict]  # [{"checkpoint_id": "...", "value": "...", "count": N}]
    # "Where students are" frontier — one bucket per checkpoint, count of students
    # whose current working frontier is that checkpoint. A student's frontier is
    # the checkpoint of their most-recent wrong attempt, OR if their most-recent
    # attempt overall was correct, the next checkpoint in order_index sequence.
    # Students whose most-recent correct attempt was on the LAST checkpoint count
    # under the "done" key. Students with no attempts are omitted.
    # Shape: {"<checkpoint_id>": int, ..., "done": int}
    frontier_histogram: dict = {}


class StuckStudent(BaseModel):
    """A student currently struggling on a specific checkpoint.

    Heuristic: 3+ wrong attempts on a single checkpoint with no correct attempt,
    most-recent attempt within the last 5 minutes (so they're *actively* stuck,
    not just gave up an hour ago).
    """
    session_id: str
    display_name: str
    checkpoint_id: str
    wrong_attempts: int
    minutes_since_first_attempt: int
    minutes_since_last_attempt: int


class NewActivityEntry(BaseModel):
    display_name: str
    attempts: int


class NewActivitySummary(BaseModel):
    """Activity that landed since the caller's `?since=<iso>` timestamp.
    Populates the 'N new attempts since you last looked' banner on the dashboard."""
    new_attempts: int
    new_correct: int
    by_student: List[NewActivityEntry] = []  # capped to 8 most-active
    since: Optional[datetime] = None


class HeartbeatResponse(BaseModel):
    """Cheap last-state endpoint. Frontend polls this every 3s and only refetches
    the heavy /live aggregation when something changed."""
    lesson_id: str
    last_attempt_at: Optional[datetime] = None
    last_session_at: Optional[datetime] = None
    total_attempts: int
    total_sessions: int


class LiveProgressResponse(BaseModel):
    lesson_id: str
    lesson_name: str
    join_code: str
    session_retention_days: int = 7
    active_sessions: int
    summary: LessonSummaryStats
    checkpoints: List[CheckpointLiveStats]
    student_roster: List[StudentRosterEntry] = []
    # Per-scope session counts so the frontend can hide empty tabs and pick a
    # sensible default when the requested scope has no data. `course` is null
    # when no course_token was supplied.
    scope_counts: dict = {}  # {"standalone": int, "course": int | None, "alltime": int}
    # Populated only when the caller passes ?since=<iso>. Tells the dashboard
    # "this much happened while you were away".
    new_activity: Optional[NewActivitySummary] = None
    # Students currently struggling — see StuckStudent docstring. Drives the
    # optional desktop-notification toggle on the dashboard.
    stuck_students: List[StuckStudent] = []


# ---------------------------------------------------------------------------
# Course-level schemas
# ---------------------------------------------------------------------------

class CourseCreate(BaseModel):
    name: str
    join_code: Optional[str] = None
    teacher_token: Optional[str] = None
    # Per-session retention in days. Capped at 365 by the DB check constraint.
    # Default 90 matches the design doc's course-mode default.
    session_retention_days: Optional[int] = None


class CourseSummary(BaseModel):
    id: UUID
    name: str
    join_code: str
    teacher_token: str
    session_retention_days: int = 90
    created_at: datetime

    class Config:
        from_attributes = True


class CoursePublicSummary(BaseModel):
    id: UUID
    name: str
    join_code: str
    notebooks: List[dict]  # [{"id": "...", "name": "...", "join_code": "...", "order_index": N}]


class CourseAddNotebook(BaseModel):
    """Add an existing Lesson (by its teacher_token) to the course."""
    lesson_teacher_token: str
    order_index: int = 0


class SetRetentionRequest(BaseModel):
    session_retention_days: int


class RotateTokenRequest(BaseModel):
    """Mint a fresh teacher_token (and optionally a fresh join_code) for a
    leaked-credential scenario. The old token is what authorises the call."""
    rotate_join_code: bool = False


class CourseNotebookStat(BaseModel):
    lesson_id: str
    name: str
    order_index: int
    students_here_now: int  # enrollments whose current_notebook_id == this lesson
    total_attempts: int
    solved_rate_pct: float  # of sessions that touched this notebook, % who solved every checkpoint
    avg_attempts: Optional[float] = None  # mean attempts-to-first-solve across all (session, checkpoint) pairs in this notebook


class CourseLiveResponse(BaseModel):
    course_id: str
    course_name: str
    join_code: str
    session_retention_days: int = 90
    total_enrollments: int
    not_started: int  # enrolled but no current_notebook_id yet
    notebooks: List[CourseNotebookStat]
    overall_completion_histogram: dict  # keys are # total checkpoints solved across whole course


class SetCurrentNotebookRequest(BaseModel):
    """Student signals which notebook they are on (by lesson join_code or id)."""
    lesson_id: Optional[str] = None
    join_code: Optional[str] = None 