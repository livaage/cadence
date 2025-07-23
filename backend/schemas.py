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