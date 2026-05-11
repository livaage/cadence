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

    class Config:
        from_attributes = True

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


class LessonSummary(BaseModel):
    id: UUID
    name: str
    join_code: str
    teacher_token: str
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
    expected_payload: str
    hint: Optional[str] = None
    order_index: int


class CheckpointRegister(BaseModel):
    checkpoint_id: str
    comparator: str  # "exact" | "numeric" | "set" | "regex"
    expected_payload: str  # JSON-encoded; shape depends on comparator
    hint: Optional[str] = None
    order_index: int = 0


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
    hint: Optional[str] = None


class CheckpointLiveStats(BaseModel):
    checkpoint_id: str
    order_index: int
    attempted: int  # distinct sessions that tried
    solved: int  # distinct sessions that got it right
    total_attempts: int
    attempts_histogram: dict  # {"1": 10, "2": 4, "3+": 2, "unsolved": 3}
    common_wrong: List[dict]  # [{"value": "...", "count": 4}]
    # Correct-attempt timing histogram (only populated when %%time_check was used).
    # Keys are fixed time buckets; value is count of correct attempts in that bucket.
    timing_histogram: dict
    timing_samples: int  # how many attempts contributed to the timing histogram


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


class LiveProgressResponse(BaseModel):
    lesson_id: str
    lesson_name: str
    join_code: str
    active_sessions: int
    summary: LessonSummaryStats
    checkpoints: List[CheckpointLiveStats]


# ---------------------------------------------------------------------------
# Course-level schemas
# ---------------------------------------------------------------------------

class CourseCreate(BaseModel):
    name: str
    join_code: Optional[str] = None
    teacher_token: Optional[str] = None


class CourseSummary(BaseModel):
    id: UUID
    name: str
    join_code: str
    teacher_token: str
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


class CourseLiveResponse(BaseModel):
    course_id: str
    course_name: str
    join_code: str
    total_enrollments: int
    not_started: int  # enrolled but no current_notebook_id yet
    notebooks: List[CourseNotebookStat]
    overall_completion_histogram: dict  # keys are # total checkpoints solved across whole course


class SetCurrentNotebookRequest(BaseModel):
    """Student signals which notebook they are on (by lesson join_code or id)."""
    lesson_id: Optional[str] = None
    join_code: Optional[str] = None 