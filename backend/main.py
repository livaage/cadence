from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
from datetime import datetime

from database import get_db, engine
from models import (
    Base, Problem, TestCase, Submission, TestResult, Teacher,
    GitHubRepo, StudentCommit, CommitTestResult,
    Lesson, Checkpoint, LessonSession, AttemptEvent,
    Course, CourseNotebook,
)
from schemas import (
    Problem as ProblemSchema, ProblemCreate, TestCase as TestCaseSchema,
    Submission as SubmissionSchema, SubmissionCreate, TestResult as TestResultSchema,
    SubmissionResponse, ProblemStats, SubmissionWithResults, Token, TeacherCreate, Teacher as TeacherSchema,
    GitHubRepo as GitHubRepoSchema, GitHubRepoCreate, StudentCommit as StudentCommitSchema,
    GitHubSyncRequest, GitHubSyncResponse, StudentCommitWithResults,
    LessonCreate, LessonSummary, LessonPublicSummary, CheckpointSummary,
    CheckpointRegister, SessionStart, SessionStartResponse,
    CheckRequest, CheckResponse, CheckpointLiveStats, LiveProgressResponse, LessonSummaryStats,
    CourseCreate, CourseSummary, CoursePublicSummary, CourseAddNotebook,
    CourseLiveResponse, CourseNotebookStat, SetCurrentNotebookRequest,
    RotateTokenRequest,
)
import json
import logging
import re
import secrets
from collections import Counter, defaultdict

checkpoint_log = logging.getLogger("checkpoint")
if not checkpoint_log.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[checkpoint] %(message)s"))
    checkpoint_log.addHandler(_h)
    checkpoint_log.setLevel(logging.INFO)
from code_executor import CodeExecutor
from auth import create_access_token, get_current_teacher, verify_password, get_password_hash
from github_integration import GitHubIntegration

# Create database tables
Base.metadata.create_all(bind=engine)

# Lightweight additive migrations so existing deployments pick up new columns
# without needing a full `docker compose down -v`. Safe to run on every boot.
with engine.begin() as _conn:
    from sqlalchemy import text as _sql
    _conn.execute(_sql("ALTER TABLE attempt_events ADD COLUMN IF NOT EXISTS elapsed_ms INTEGER"))
    _conn.execute(_sql("ALTER TABLE lesson_sessions ADD COLUMN IF NOT EXISTS course_id VARCHAR(255)"))
    _conn.execute(_sql("ALTER TABLE lesson_sessions ALTER COLUMN lesson_id DROP NOT NULL"))
    _conn.execute(_sql("CREATE INDEX IF NOT EXISTS ix_lesson_sessions_course_id ON lesson_sessions (course_id)"))

app = FastAPI(title="Cadence", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Initialize services
try:
    code_executor = CodeExecutor()
    code_execution_available = True
except Exception as e:
    print(f"Warning: Code execution not available: {e}")
    code_executor = None
    code_execution_available = False

try:
    github_integration = GitHubIntegration()
    github_available = True
except Exception as e:
    print(f"Warning: GitHub integration not available: {e}")
    github_integration = None
    github_available = False

# Background task to evaluate submission
async def evaluate_submission(submission_id: str, db: Session):
    """Background task to evaluate a submission against all test cases"""
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        return
    
    problem = db.query(Problem).filter(Problem.id == submission.problem_id).first()
    test_cases = db.query(TestCase).filter(TestCase.problem_id == submission.problem_id).all()
    
    total_score = 0
    total_points = 0
    max_execution_time = 0
    max_memory_usage = 0
    
    # Update submission status to running
    submission.status = "running"
    db.commit()
    
    if not code_execution_available:
        # Mark submission as error if code execution is not available
        submission.status = "error"
        submission.error_message = "Code execution service is not available"
        db.commit()
        return
    
    for test_case in test_cases:
        # Execute code against test case
        result = code_executor.execute_code(
            submission.source_code,
            submission.language,
            test_case.input_data,
            str(submission.id)
        )
        
        # Determine if test passed
        if result["status"] == "completed":
            # Normalize output for comparison
            actual_output = result["output"].strip()
            expected_output = test_case.expected_output.strip()
            
            if actual_output == expected_output:
                status = "passed"
                points_earned = test_case.points
                total_score += test_case.points
            else:
                status = "failed"
                points_earned = 0
        else:
            status = "error"
            points_earned = 0
        
        total_points += test_case.points
        
        # Track max execution time and memory
        if result["execution_time_ms"]:
            max_execution_time = max(max_execution_time, result["execution_time_ms"])
        if result["memory_usage_mb"]:
            max_memory_usage = max(max_memory_usage, result["memory_usage_mb"])
        
        # Create test result
        test_result = TestResult(
            submission_id=submission.id,
            test_case_id=test_case.id,
            status=status,
            actual_output=result["output"] if result["status"] == "completed" else None,
            execution_time_ms=result["execution_time_ms"],
            memory_usage_mb=result["memory_usage_mb"],
            error_message=result["error"],
            points_earned=points_earned
        )
        db.add(test_result)
    
    # Update submission with final results
    submission.status = "completed"
    submission.total_score = total_score
    submission.total_points = total_points
    submission.execution_time_ms = max_execution_time
    submission.memory_usage_mb = max_memory_usage
    submission.completed_at = datetime.utcnow()
    
    db.commit()

# Public endpoints
@app.get("/")
async def root():
    return {"message": "Cadence API"}

@app.get("/problems", response_model=List[ProblemSchema])
async def get_problems(db: Session = Depends(get_db)):
    """Get all active problems"""
    problems = db.query(Problem).filter(Problem.is_active == True).all()
    return problems

@app.get("/problems/{problem_id}", response_model=ProblemSchema)
async def get_problem(problem_id: str, db: Session = Depends(get_db)):
    """Get a specific problem"""
    problem = db.query(Problem).filter(Problem.id == problem_id, Problem.is_active == True).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    return problem

@app.post("/submissions", response_model=SubmissionResponse)
async def create_submission(
    submission: SubmissionCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Submit code for evaluation"""
    # Validate problem exists
    problem = db.query(Problem).filter(Problem.id == submission.problem_id, Problem.is_active == True).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    
    # Validate language
    if submission.language.lower() not in ["python", "cpp"]:
        raise HTTPException(status_code=400, detail="Unsupported language")
    
    # Create submission
    db_submission = Submission(
        problem_id=submission.problem_id,
        student_name=submission.student_name,
        student_email=submission.student_email,
        language=submission.language.lower(),
        source_code=submission.source_code
    )
    db.add(db_submission)
    db.commit()
    db.refresh(db_submission)
    
    # Start background evaluation
    background_tasks.add_task(evaluate_submission, str(db_submission.id), db)
    
    return SubmissionResponse(
        submission_id=db_submission.id,
        status="pending",
        message="Submission received and queued for evaluation"
    )

@app.get("/submissions/{submission_id}", response_model=SubmissionSchema)
async def get_submission(submission_id: str, db: Session = Depends(get_db)):
    """Get submission status and results"""
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    return submission

# Teacher endpoints (protected)
from fastapi import Form

@app.post("/auth/login", response_model=Token)
async def login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Teacher login"""
    teacher = db.query(Teacher).filter(Teacher.username == username, Teacher.is_active == True).first()
    if not teacher or not verify_password(password, teacher.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": teacher.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/teacher/problems", response_model=List[ProblemSchema])
async def get_problems_teacher(
    current_teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Get all problems (teacher view)"""
    problems = db.query(Problem).all()
    return problems

@app.post("/teacher/problems", response_model=ProblemSchema)
async def create_problem(
    problem: ProblemCreate,
    current_teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Create a new problem"""
    db_problem = Problem(**problem.dict())
    db.add(db_problem)
    db.commit()
    db.refresh(db_problem)
    return db_problem

@app.get("/teacher/submissions", response_model=List[SubmissionSchema])
async def get_submissions_teacher(
    problem_id: Optional[str] = None,
    current_teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Get all submissions (teacher view)"""
    query = db.query(Submission)
    if problem_id:
        query = query.filter(Submission.problem_id == problem_id)
    submissions = query.order_by(Submission.created_at.desc()).all()
    return submissions

@app.get("/teacher/submissions/{submission_id}", response_model=SubmissionWithResults)
async def get_submission_teacher(
    submission_id: str,
    current_teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Get submission with detailed results (teacher view)"""
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    test_results = db.query(TestResult).filter(TestResult.submission_id == submission_id).all()
    problem = db.query(Problem).filter(Problem.id == submission.problem_id).first()
    
    return SubmissionWithResults(
        submission=submission,
        test_results=test_results,
        problem=problem
    )

@app.get("/teacher/stats", response_model=List[ProblemStats])
async def get_problem_stats(
    current_teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Get statistics for all problems"""
    problems = db.query(Problem).filter(Problem.is_active == True).all()
    stats = []
    
    for problem in problems:
        submissions = db.query(Submission).filter(Submission.problem_id == problem.id).all()
        total_submissions = len(submissions)
        
        if total_submissions == 0:
            stats.append(ProblemStats(
                problem_id=problem.id,
                problem_title=problem.title,
                total_submissions=0,
                correct_submissions=0,
                average_score=0.0,
                average_time_ms=0.0,
                average_memory_mb=0.0
            ))
            continue
        
        correct_submissions = len([s for s in submissions if s.total_score == s.total_points])
        average_score = sum(s.total_score for s in submissions) / total_submissions
        average_time = sum(s.execution_time_ms or 0 for s in submissions) / total_submissions
        average_memory = sum(s.memory_usage_mb or 0 for s in submissions) / total_submissions
        
        stats.append(ProblemStats(
            problem_id=problem.id,
            problem_title=problem.title,
            total_submissions=total_submissions,
            correct_submissions=correct_submissions,
            average_score=average_score,
            average_time_ms=average_time,
            average_memory_mb=average_memory
        ))
    
    return stats

@app.post("/teacher/teachers", response_model=TeacherSchema)
async def create_teacher(
    teacher: TeacherCreate,
    current_teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Create a new teacher account"""
    # Check if username already exists
    existing_teacher = db.query(Teacher).filter(Teacher.username == teacher.username).first()
    if existing_teacher:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Check if email already exists
    existing_email = db.query(Teacher).filter(Teacher.email == teacher.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already exists")
    
    hashed_password = get_password_hash(teacher.password)
    db_teacher = Teacher(
        username=teacher.username,
        email=teacher.email,
        password_hash=hashed_password
    )
    db.add(db_teacher)
    db.commit()
    db.refresh(db_teacher)
    return db_teacher

# GitHub Integration endpoints
@app.post("/teacher/github/repos", response_model=GitHubRepoSchema)
async def create_github_repo(
    repo_data: GitHubRepoCreate,
    current_teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Create a new GitHub repository for a problem"""
    # Validate problem exists
    problem = db.query(Problem).filter(Problem.id == repo_data.problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    
    # Create repository on GitHub
    repo_name = f"{problem.title.lower().replace(' ', '-')}-{datetime.now().strftime('%Y%m%d')}"
    result = github_integration.create_repository(
        repo_name=repo_name,
        description=f"Student submissions for: {problem.title}",
        is_private=True
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=f"Failed to create repository: {result['error']}")
    
    # Create repository record
    db_repo = GitHubRepo(
        problem_id=repo_data.problem_id,
        repo_name=result["repo_name"],
        repo_url=result["repo_url"],
        repo_owner=result["repo_owner"],
        branch=repo_data.branch,
        folder_structure=repo_data.folder_structure
    )
    db.add(db_repo)
    db.commit()
    db.refresh(db_repo)
    
    return db_repo

@app.get("/teacher/github/repos", response_model=List[GitHubRepoSchema])
async def get_github_repos(
    problem_id: Optional[str] = None,
    current_teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Get GitHub repositories (teacher view)"""
    query = db.query(GitHubRepo)
    if problem_id:
        query = query.filter(GitHubRepo.problem_id == problem_id)
    repos = query.order_by(GitHubRepo.created_at.desc()).all()
    return repos

@app.post("/teacher/github/sync", response_model=GitHubSyncResponse)
async def sync_github_repo(
    sync_request: GitHubSyncRequest,
    current_teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Sync a GitHub repository and evaluate student commits"""
    result = github_integration.sync_repository(
        repo_id=str(sync_request.repo_id),
        db=db,
        force_sync=sync_request.force_sync
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return GitHubSyncResponse(
        success=True,
        message=result["message"],
        commits_found=result["commits_found"],
        commits_processed=result["commits_processed"]
    )

@app.get("/teacher/github/repos/{repo_id}/commits", response_model=List[StudentCommitSchema])
async def get_github_commits(
    repo_id: str,
    current_teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Get student commits for a GitHub repository"""
    commits = db.query(StudentCommit).filter(
        StudentCommit.github_repo_id == repo_id
    ).order_by(StudentCommit.commit_date.desc()).all()
    return commits

@app.get("/teacher/github/repos/{repo_id}/commits/{commit_id}", response_model=StudentCommitWithResults)
async def get_github_commit_details(
    repo_id: str,
    commit_id: str,
    current_teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Get detailed commit information with test results"""
    commit = db.query(StudentCommit).filter(
        StudentCommit.id == commit_id,
        StudentCommit.github_repo_id == repo_id
    ).first()
    
    if not commit:
        raise HTTPException(status_code=404, detail="Commit not found")
    
    test_results = db.query(CommitTestResult).filter(
        CommitTestResult.student_commit_id == commit.id
    ).all()
    
    github_repo = db.query(GitHubRepo).filter(GitHubRepo.id == repo_id).first()
    problem = db.query(Problem).filter(Problem.id == github_repo.problem_id).first()
    
    return StudentCommitWithResults(
        student_commit=commit,
        commit_test_results=test_results,
        github_repo=github_repo,
        problem=problem
    )

@app.get("/teacher/github/repos/{repo_id}/stats")
async def get_github_repo_stats(
    repo_id: str,
    current_teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db)
):
    """Get statistics for a GitHub repository"""
    stats = github_integration.get_repository_stats(repo_id, db)
    
    if "error" in stats:
        raise HTTPException(status_code=404, detail=stats["error"])
    
    return stats

# ---------------------------------------------------------------------------
# Lesson progress: checkpoint register / session / check / live dashboard
# ---------------------------------------------------------------------------

MAX_SUBMITTED_VALUE_LEN = 1024


def _evaluate_checkpoint(
    comparator: str,
    expected_payload: str,
    submitted_value: str,
    *,
    checkpoint_id: str = "",
    lesson_id: str = "",
) -> bool:
    """Compare a student's submitted value against the teacher's expected answer.

    Both payloads are JSON strings produced by the client/teacher helpers. The
    shape of `expected_payload` depends on `comparator`. Every call logs the
    parsed values and the final verdict so teachers can diagnose mismatches
    via `docker compose logs backend`.
    """
    try:
        submitted = json.loads(submitted_value)
    except (json.JSONDecodeError, TypeError):
        submitted = submitted_value

    try:
        expected = json.loads(expected_payload)
    except (json.JSONDecodeError, TypeError):
        expected = expected_payload

    reason = ""
    result = False

    if comparator == "exact":
        want = expected.get("value") if isinstance(expected, dict) else expected
        result = str(submitted).strip() == str(want).strip()
        reason = f"str({submitted!r}).strip() {'==' if result else '!='} str({want!r}).strip()"

    elif comparator == "numeric":
        want = expected["value"] if isinstance(expected, dict) else expected
        tol = expected.get("tolerance", 0) if isinstance(expected, dict) else 0
        try:
            diff = abs(float(submitted) - float(want))
            result = diff <= float(tol)
            reason = f"|{submitted} - {want}| = {diff} {'<=' if result else '>'} tolerance {tol}"
        except (TypeError, ValueError) as e:
            reason = f"non-numeric value: {e}"

    elif comparator == "set":
        want = expected.get("value") if isinstance(expected, dict) else expected
        try:
            result = set(submitted) == set(want)
            reason = f"set({submitted!r}) {'==' if result else '!='} set({want!r})"
        except TypeError as e:
            reason = f"non-iterable value: {e}"

    elif comparator == "regex":
        pattern = expected.get("pattern") if isinstance(expected, dict) else expected
        try:
            result = re.match(pattern, str(submitted)) is not None
            reason = f"re.match({pattern!r}, {str(submitted)!r}) -> {'match' if result else 'no match'}"
        except re.error as e:
            reason = f"invalid regex {pattern!r}: {e}"

    else:
        reason = f"unknown comparator {comparator!r}"

    checkpoint_log.info(
        "lesson=%s cp=%s comparator=%s expected=%r submitted=%r result=%s (%s)",
        lesson_id or "?", checkpoint_id or "?", comparator,
        expected, submitted, result, reason,
    )
    return result


def _require_lesson_by_token(db: Session, teacher_token: str) -> Lesson:
    lesson = db.query(Lesson).filter(Lesson.teacher_token == teacher_token).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Unknown teacher token")
    return lesson


def _require_lesson_by_code(db: Session, join_code: str) -> Lesson:
    lesson = db.query(Lesson).filter(Lesson.join_code == join_code).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Unknown join code")
    return lesson


@app.post("/lessons", response_model=LessonSummary, status_code=201)
async def create_lesson(payload: LessonCreate, db: Session = Depends(get_db)):
    """Create a lesson. No auth — the returned teacher_token IS the credential.

    If the caller supplies `join_code` or `teacher_token` and either collides,
    returns 409 so the client can retry with a different value.
    """
    join_code = payload.join_code or _generate_join_code(db)
    teacher_token = payload.teacher_token or secrets.token_urlsafe(24)

    if db.query(Lesson).filter(Lesson.join_code == join_code).first():
        raise HTTPException(status_code=409, detail="join_code already in use")
    if db.query(Lesson).filter(Lesson.teacher_token == teacher_token).first():
        raise HTTPException(status_code=409, detail="teacher_token already in use")

    lesson = Lesson(name=payload.name, join_code=join_code, teacher_token=teacher_token)
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


def _generate_join_code(db: Session) -> str:
    """Random human-readable code; collisions are retried client-side if rare."""
    # Generator lives in the Jupyter client; server just picks a random token
    # as a fallback when the client doesn't supply one.
    for _ in range(8):
        candidate = secrets.token_urlsafe(6).replace("_", "").replace("-", "").lower()[:10]
        if not db.query(Lesson).filter(Lesson.join_code == candidate).first():
            return candidate
    # extremely unlikely; surface as 500
    raise HTTPException(status_code=500, detail="Could not allocate a join code")


@app.get("/lessons/by-token/{teacher_token}", response_model=LessonSummary)
async def lookup_lesson_by_token(teacher_token: str, db: Session = Depends(get_db)):
    """Teacher-side: retrieve lesson metadata for a known token."""
    return _require_lesson_by_token(db, teacher_token)


@app.post("/lessons/by-token/{teacher_token}/rotate", response_model=LessonSummary)
async def rotate_lesson_token(
    teacher_token: str,
    payload: RotateTokenRequest,
    db: Session = Depends(get_db),
):
    """Mint a fresh teacher_token (and optionally a fresh join_code) for a leaked
    or compromised lesson. The old token authorises the call; after a successful
    response it is dead. Student attempts and registered checkpoints survive."""
    lesson = _require_lesson_by_token(db, teacher_token)
    new_token = secrets.token_urlsafe(24)
    while db.query(Lesson).filter(Lesson.teacher_token == new_token).first():
        new_token = secrets.token_urlsafe(24)
    lesson.teacher_token = new_token
    if payload.rotate_join_code:
        new_code = _generate_join_code(db)
        while (
            db.query(Lesson).filter(Lesson.join_code == new_code).first()
            or db.query(Course).filter(Course.join_code == new_code).first()
        ):
            new_code = _generate_join_code(db)
        lesson.join_code = new_code
    db.commit()
    db.refresh(lesson)
    return lesson


@app.get("/lessons/by-code/{join_code}", response_model=LessonPublicSummary)
async def lookup_lesson_by_code(join_code: str, db: Session = Depends(get_db)):
    """Student-side: verify the join code exists and get the lesson name."""
    return _require_lesson_by_code(db, join_code)


@app.post("/lessons/by-token/{teacher_token}/checkpoints", status_code=201)
async def register_checkpoint(
    teacher_token: str,
    payload: CheckpointRegister,
    db: Session = Depends(get_db),
):
    """Teacher registers (or updates) the expected answer for a checkpoint."""
    lesson = _require_lesson_by_token(db, teacher_token)
    if payload.comparator not in {"exact", "numeric", "set", "regex"}:
        raise HTTPException(status_code=400, detail="Invalid comparator")

    lesson_id_str = str(lesson.id)
    existing = (
        db.query(Checkpoint)
        .filter(Checkpoint.lesson_id == lesson_id_str, Checkpoint.checkpoint_id == payload.checkpoint_id)
        .first()
    )
    if existing:
        existing.comparator = payload.comparator
        existing.expected_payload = payload.expected_payload
        existing.hint = payload.hint
        existing.order_index = payload.order_index
    else:
        existing = Checkpoint(
            lesson_id=lesson_id_str,
            checkpoint_id=payload.checkpoint_id,
            comparator=payload.comparator,
            expected_payload=payload.expected_payload,
            hint=payload.hint,
            order_index=payload.order_index,
        )
        db.add(existing)
    db.commit()
    db.refresh(existing)
    return {"id": str(existing.id)}


@app.get("/lessons/by-token/{teacher_token}/checkpoints", response_model=List[CheckpointSummary])
async def list_checkpoints(teacher_token: str, db: Session = Depends(get_db)):
    """Teacher lists all registered checkpoints (used for `%competition_self_test`)."""
    lesson = _require_lesson_by_token(db, teacher_token)
    rows = (
        db.query(Checkpoint)
        .filter(Checkpoint.lesson_id == str(lesson.id))
        .order_by(Checkpoint.order_index.asc(), Checkpoint.created_at.asc())
        .all()
    )
    return [
        CheckpointSummary(
            checkpoint_id=r.checkpoint_id,
            comparator=r.comparator,
            expected_payload=r.expected_payload,
            hint=r.hint,
            order_index=r.order_index,
        )
        for r in rows
    ]


@app.post("/lessons/by-code/{join_code}/sessions", response_model=SessionStartResponse)
async def start_session(
    join_code: str,
    payload: SessionStart,
    db: Session = Depends(get_db),
):
    """Student opens a notebook and joins a lesson via its join code."""
    lesson = _require_lesson_by_code(db, join_code)
    session = LessonSession(
        lesson_id=str(lesson.id),
        display_name=payload.display_name,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return SessionStartResponse(
        session_id=session.id,
        lesson_id=session.lesson_id,
        display_name=session.display_name,
    )


# ---------------------------------------------------------------------------
# Courses (groupings of notebooks for one teaching event)
# ---------------------------------------------------------------------------

def _require_course_by_token(db: Session, teacher_token: str) -> Course:
    course = db.query(Course).filter(Course.teacher_token == teacher_token).first()
    if not course:
        raise HTTPException(status_code=404, detail="Unknown course teacher token")
    return course


def _require_course_by_code(db: Session, join_code: str) -> Course:
    course = db.query(Course).filter(Course.join_code == join_code).first()
    if not course:
        raise HTTPException(status_code=404, detail="Unknown course join code")
    return course


def _course_notebooks(db: Session, course_id) -> List[dict]:
    rows = (
        db.query(CourseNotebook, Lesson)
        .join(Lesson, Lesson.id == CourseNotebook.lesson_id)
        .filter(CourseNotebook.course_id == course_id)
        .order_by(CourseNotebook.order_index.asc(), CourseNotebook.added_at.asc())
        .all()
    )
    return [
        {
            "id": str(lesson.id),
            "name": lesson.name,
            "join_code": lesson.join_code,
            "order_index": cn.order_index,
        }
        for cn, lesson in rows
    ]


@app.post("/courses", response_model=CourseSummary, status_code=201)
async def create_course(payload: CourseCreate, db: Session = Depends(get_db)):
    join_code = payload.join_code or _generate_join_code(db)
    teacher_token = payload.teacher_token or secrets.token_urlsafe(24)

    if db.query(Course).filter(Course.join_code == join_code).first():
        raise HTTPException(status_code=409, detail="join_code already in use")
    if db.query(Lesson).filter(Lesson.join_code == join_code).first():
        raise HTTPException(status_code=409, detail="join_code already used by a lesson")
    if db.query(Course).filter(Course.teacher_token == teacher_token).first():
        raise HTTPException(status_code=409, detail="teacher_token already in use")

    course = Course(name=payload.name, join_code=join_code, teacher_token=teacher_token)
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@app.get("/courses/by-token/{teacher_token}", response_model=CourseSummary)
async def lookup_course_by_token(teacher_token: str, db: Session = Depends(get_db)):
    return _require_course_by_token(db, teacher_token)


@app.post("/courses/by-token/{teacher_token}/rotate", response_model=CourseSummary)
async def rotate_course_token(
    teacher_token: str,
    payload: RotateTokenRequest,
    db: Session = Depends(get_db),
):
    """Course equivalent of /lessons/by-token/{...}/rotate.

    Rotating the join_code disconnects existing students — they'll see
    ``Unknown join code`` next time they run %cadence_session, which is the
    intended behaviour for a hard revocation.
    """
    course = _require_course_by_token(db, teacher_token)
    new_token = secrets.token_urlsafe(24)
    while db.query(Course).filter(Course.teacher_token == new_token).first():
        new_token = secrets.token_urlsafe(24)
    course.teacher_token = new_token
    if payload.rotate_join_code:
        new_code = _generate_join_code(db)
        while (
            db.query(Course).filter(Course.join_code == new_code).first()
            or db.query(Lesson).filter(Lesson.join_code == new_code).first()
        ):
            new_code = _generate_join_code(db)
        course.join_code = new_code
    db.commit()
    db.refresh(course)
    return course


@app.get("/courses/by-code/{join_code}", response_model=CoursePublicSummary)
async def lookup_course_by_code(join_code: str, db: Session = Depends(get_db)):
    course = _require_course_by_code(db, join_code)
    return CoursePublicSummary(
        id=course.id,
        name=course.name,
        join_code=course.join_code,
        notebooks=_course_notebooks(db, course.id),
    )


@app.post("/courses/by-token/{teacher_token}/notebooks", status_code=201)
async def add_notebook_to_course(
    teacher_token: str,
    payload: CourseAddNotebook,
    db: Session = Depends(get_db),
):
    course = _require_course_by_token(db, teacher_token)
    lesson = _require_lesson_by_token(db, payload.lesson_teacher_token)
    existing = (
        db.query(CourseNotebook)
        .filter(CourseNotebook.course_id == course.id, CourseNotebook.lesson_id == lesson.id)
        .first()
    )
    if existing:
        existing.order_index = payload.order_index
    else:
        db.add(CourseNotebook(
            course_id=course.id,
            lesson_id=lesson.id,
            order_index=payload.order_index,
        ))
    db.commit()
    return {"course_id": str(course.id), "lesson_id": str(lesson.id)}


@app.get("/courses/by-token/{teacher_token}/notebooks")
async def list_course_notebooks(teacher_token: str, db: Session = Depends(get_db)):
    """Teacher-only: includes each notebook's teacher_token so the dashboard
    can drill into per-notebook views without requiring a second auth hop."""
    course = _require_course_by_token(db, teacher_token)
    rows = (
        db.query(CourseNotebook, Lesson)
        .join(Lesson, Lesson.id == CourseNotebook.lesson_id)
        .filter(CourseNotebook.course_id == course.id)
        .order_by(CourseNotebook.order_index.asc(), CourseNotebook.added_at.asc())
        .all()
    )
    return [
        {
            "id": str(lesson.id),
            "name": lesson.name,
            "join_code": lesson.join_code,
            "teacher_token": lesson.teacher_token,
            "order_index": cn.order_index,
        }
        for cn, lesson in rows
    ]


@app.post("/courses/by-code/{join_code}/sessions", response_model=SessionStartResponse)
async def start_course_session(
    join_code: str,
    payload: SessionStart,
    db: Session = Depends(get_db),
):
    """Student enrolls in a course. Their current notebook is set later via
    POST /sessions/{id}/current-notebook."""
    course = _require_course_by_code(db, join_code)
    session = LessonSession(
        lesson_id=None,
        course_id=str(course.id),
        display_name=payload.display_name,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return SessionStartResponse(
        session_id=session.id,
        lesson_id=str(course.id),  # reuse field to carry the course id for client
        display_name=session.display_name,
    )


@app.post("/sessions/{session_id}/current-notebook")
async def set_current_notebook(
    session_id: str,
    payload: SetCurrentNotebookRequest,
    db: Session = Depends(get_db),
):
    session = db.query(LessonSession).filter(LessonSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.course_id:
        raise HTTPException(status_code=400, detail="Session is not a course enrollment")

    if payload.lesson_id:
        lesson = db.query(Lesson).filter(Lesson.id == payload.lesson_id).first()
    elif payload.join_code:
        lesson = db.query(Lesson).filter(Lesson.join_code == payload.join_code).first()
    else:
        raise HTTPException(status_code=400, detail="Provide lesson_id or join_code")
    if not lesson:
        raise HTTPException(status_code=404, detail="Notebook not found")

    member = (
        db.query(CourseNotebook)
        .filter(CourseNotebook.course_id == session.course_id, CourseNotebook.lesson_id == lesson.id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=400, detail="Notebook is not part of this course")

    session.lesson_id = str(lesson.id)
    session.last_seen_at = datetime.utcnow()
    db.commit()
    return {"lesson_id": str(lesson.id), "lesson_name": lesson.name}


@app.get("/courses/by-token/{teacher_token}/live", response_model=CourseLiveResponse)
async def get_course_live(teacher_token: str, db: Session = Depends(get_db)):
    course = _require_course_by_token(db, teacher_token)
    course_id_str = str(course.id)

    notebooks = _course_notebooks(db, course.id)
    lesson_id_to_name = {nb["id"]: nb["name"] for nb in notebooks}
    lesson_id_to_order = {nb["id"]: nb["order_index"] for nb in notebooks}

    enrollments = db.query(LessonSession).filter(LessonSession.course_id == course_id_str).all()
    total = len(enrollments)
    not_started = sum(1 for s in enrollments if not s.lesson_id)

    # Students currently on each notebook (by explicit switch)
    here_now: Counter = Counter()
    for s in enrollments:
        if s.lesson_id:
            here_now[s.lesson_id] += 1

    enrollment_ids = {s.id for s in enrollments}
    # Attempts across any notebook in this course, scoped to these enrollments.
    events = []
    if enrollment_ids and lesson_id_to_name:
        events = (
            db.query(AttemptEvent)
            .filter(
                AttemptEvent.session_id.in_(enrollment_ids),
                AttemptEvent.lesson_id.in_(list(lesson_id_to_name.keys())),
            )
            .all()
        )

    # Per-notebook attempt counts and per-(session, checkpoint) solve set.
    attempts_by_notebook: Counter = Counter()
    sessions_solved: dict = defaultdict(set)  # session_id -> {(notebook_id, cp_id)}
    for e in events:
        attempts_by_notebook[e.lesson_id] += 1
        if e.is_correct:
            sessions_solved[e.session_id].add((e.lesson_id, e.checkpoint_id))

    # For each notebook, compute % of sessions-that-touched-it who solved everything.
    # Pre-fetch total checkpoints per notebook.
    cp_counts = {}
    for nb_id in lesson_id_to_name.keys():
        cp_counts[nb_id] = (
            db.query(Checkpoint).filter(Checkpoint.lesson_id == nb_id).count()
        )

    sessions_touching_notebook: dict = defaultdict(set)  # notebook_id -> {session_id}
    for e in events:
        sessions_touching_notebook[e.lesson_id].add(e.session_id)

    notebook_stats: List[CourseNotebookStat] = []
    for nb in notebooks:
        nb_id = nb["id"]
        total_cps = cp_counts.get(nb_id, 0)
        touching = sessions_touching_notebook.get(nb_id, set())
        if total_cps == 0 or not touching:
            solved_rate = 0.0
        else:
            fully_solved = sum(
                1
                for sid in touching
                if len({cp for (nid, cp) in sessions_solved.get(sid, set()) if nid == nb_id}) >= total_cps
            )
            solved_rate = round(fully_solved / len(touching) * 100, 1)

        notebook_stats.append(CourseNotebookStat(
            lesson_id=nb_id,
            name=nb["name"],
            order_index=nb["order_index"],
            students_here_now=here_now.get(nb_id, 0),
            total_attempts=attempts_by_notebook.get(nb_id, 0),
            solved_rate_pct=solved_rate,
        ))

    # Completion histogram: total checkpoints solved per enrollment across the whole course.
    total_course_checkpoints = sum(cp_counts.values())
    completion_counter: Counter = Counter()
    for s in enrollments:
        completion_counter[len(sessions_solved.get(s.id, set()))] += 1
    overall_completion_histogram = {
        str(i): completion_counter.get(i, 0) for i in range(0, total_course_checkpoints + 1)
    }

    return CourseLiveResponse(
        course_id=course_id_str,
        course_name=course.name,
        join_code=course.join_code,
        total_enrollments=total,
        not_started=not_started,
        notebooks=notebook_stats,
        overall_completion_histogram=overall_completion_histogram,
    )


# ---------------------------------------------------------------------------

@app.post("/check", response_model=CheckResponse)
async def check_answer(payload: CheckRequest, db: Session = Depends(get_db)):
    """Student submits an answer for a named checkpoint.

    Accepts either a standalone-lesson session (scoped to session.lesson_id)
    or a course-enrollment session (scoped to any notebook in the course).
    """
    session = db.query(LessonSession).filter(LessonSession.id == payload.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.course_id:
        # Look up the checkpoint in any notebook belonging to this course.
        notebook_ids = [
            str(row.lesson_id)
            for row in db.query(CourseNotebook.lesson_id)
            .filter(CourseNotebook.course_id == session.course_id)
            .all()
        ]
        if not notebook_ids:
            raise HTTPException(status_code=404, detail="Course has no notebooks yet")
        checkpoint = (
            db.query(Checkpoint)
            .filter(
                Checkpoint.lesson_id.in_(notebook_ids),
                Checkpoint.checkpoint_id == payload.checkpoint_id,
            )
            .first()
        )
    else:
        checkpoint = (
            db.query(Checkpoint)
            .filter(
                Checkpoint.lesson_id == session.lesson_id,
                Checkpoint.checkpoint_id == payload.checkpoint_id,
            )
            .first()
        )

    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not registered")

    submitted = (payload.submitted_value or "")[:MAX_SUBMITTED_VALUE_LEN]
    is_correct = _evaluate_checkpoint(
        checkpoint.comparator,
        checkpoint.expected_payload,
        submitted,
        checkpoint_id=checkpoint.checkpoint_id,
        lesson_id=checkpoint.lesson_id,
    )

    prior = (
        db.query(AttemptEvent)
        .filter(AttemptEvent.session_id == session.id, AttemptEvent.checkpoint_id == payload.checkpoint_id)
        .count()
    )
    attempt_num = prior + 1

    elapsed_ms = payload.elapsed_ms if payload.elapsed_ms and payload.elapsed_ms >= 0 else None

    event = AttemptEvent(
        session_id=session.id,
        lesson_id=checkpoint.lesson_id,  # the notebook that owns this checkpoint
        checkpoint_id=payload.checkpoint_id,
        attempt_num=attempt_num,
        submitted_value=submitted,
        is_correct=is_correct,
        elapsed_ms=elapsed_ms,
    )
    db.add(event)
    session.last_seen_at = datetime.utcnow()
    db.commit()

    return CheckResponse(
        is_correct=is_correct,
        attempt_num=attempt_num,
        elapsed_ms=elapsed_ms,
        hint=None if is_correct else checkpoint.hint,
    )


@app.get("/lessons/by-token/{teacher_token}/live", response_model=LiveProgressResponse)
async def get_live_progress(
    teacher_token: str,
    scope: str = "current",
    course_token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Aggregate per-checkpoint stats for the teacher dashboard. Token-scoped.

    Scope modes:
      - `current` (default): standalone mode — sessions that joined this lesson directly.
      - `course`: requires `course_token`; sessions enrolled in that course who
        have this notebook as their current notebook (or have attempted it).
      - `alltime`: every session (any course, plus standalone) that has touched
        this notebook — the cross-class historical view.
    """
    lesson = _require_lesson_by_token(db, teacher_token)
    lesson_id = str(lesson.id)
    checkpoints = (
        db.query(Checkpoint)
        .filter(Checkpoint.lesson_id == lesson_id)
        .order_by(Checkpoint.order_index.asc())
        .all()
    )

    if scope == "alltime":
        # Every attempt against any checkpoint in this notebook, any session.
        events = (
            db.query(AttemptEvent)
            .filter(AttemptEvent.lesson_id == lesson_id)
            .order_by(AttemptEvent.created_at.asc())
            .all()
        )
        session_ids_set = {e.session_id for e in events}
        sessions = db.query(LessonSession).filter(LessonSession.id.in_(session_ids_set)).all() if session_ids_set else []
    elif scope == "course":
        if not course_token:
            raise HTTPException(status_code=400, detail="scope=course requires course_token")
        course = _require_course_by_token(db, course_token)
        sessions = db.query(LessonSession).filter(LessonSession.course_id == str(course.id)).all()
        session_ids_set = {s.id for s in sessions}
        events = (
            db.query(AttemptEvent)
            .filter(
                AttemptEvent.lesson_id == lesson_id,
                AttemptEvent.session_id.in_(session_ids_set),
            )
            .order_by(AttemptEvent.created_at.asc())
            .all()
        ) if session_ids_set else []
    else:  # "current" — standalone joiners only
        sessions = db.query(LessonSession).filter(LessonSession.lesson_id == lesson_id).all()
        session_ids_set = {s.id for s in sessions}
        events = (
            db.query(AttemptEvent)
            .filter(
                AttemptEvent.lesson_id == lesson_id,
                AttemptEvent.session_id.in_(session_ids_set),
            )
            .order_by(AttemptEvent.created_at.asc())
            .all()
        ) if session_ids_set else []

    session_ids = session_ids_set

    # Index events by checkpoint.
    by_checkpoint: dict = defaultdict(list)
    for e in events:
        by_checkpoint[e.checkpoint_id].append(e)

    # Fixed buckets for correct-attempt timing distribution (milliseconds).
    timing_buckets = ["<10ms", "10–100ms", "100ms–1s", "1–5s", "5–30s", ">30s"]

    def _bucket(ms: int) -> str:
        if ms < 10:
            return "<10ms"
        if ms < 100:
            return "10–100ms"
        if ms < 1000:
            return "100ms–1s"
        if ms < 5000:
            return "1–5s"
        if ms < 30000:
            return "5–30s"
        return ">30s"

    # Collect lesson-wide aggregates as we go.
    sessions_solved: dict = defaultdict(set)  # session_id -> set of solved checkpoint_ids
    overall_wrong: List[dict] = []

    stats: List[CheckpointLiveStats] = []
    for cp in checkpoints:
        cp_events = by_checkpoint.get(cp.checkpoint_id, [])
        per_session_attempts: dict = defaultdict(list)
        for e in cp_events:
            per_session_attempts[e.session_id].append(e)

        histogram = {"1": 0, "2": 0, "3+": 0, "unsolved": 0}
        timing_hist = {b: 0 for b in timing_buckets}
        timing_samples = 0
        wrong_counter: Counter = Counter()

        for sid, attempts in per_session_attempts.items():
            first_correct_idx = next((i for i, a in enumerate(attempts) if a.is_correct), None)
            if first_correct_idx is None:
                histogram["unsolved"] += 1
            elif first_correct_idx == 0:
                histogram["1"] += 1
            elif first_correct_idx == 1:
                histogram["2"] += 1
            else:
                histogram["3+"] += 1

            if first_correct_idx is not None:
                sessions_solved[sid].add(cp.checkpoint_id)
                # Timing for the first correct attempt only — avoids gaming by
                # re-running a known-good cell many times.
                correct_attempt = attempts[first_correct_idx]
                if correct_attempt.elapsed_ms is not None:
                    timing_hist[_bucket(correct_attempt.elapsed_ms)] += 1
                    timing_samples += 1

            for a in attempts:
                if not a.is_correct and a.submitted_value:
                    wrong_counter[a.submitted_value] += 1
                    overall_wrong.append({
                        "checkpoint_id": cp.checkpoint_id,
                        "value": a.submitted_value,
                    })

        common_wrong = [
            {"value": v, "count": c} for v, c in wrong_counter.most_common(5)
        ]

        attempted = len(per_session_attempts)
        solved = histogram["1"] + histogram["2"] + histogram["3+"]

        stats.append(CheckpointLiveStats(
            checkpoint_id=cp.checkpoint_id,
            order_index=cp.order_index,
            attempted=attempted,
            solved=solved,
            total_attempts=len(cp_events),
            attempts_histogram=histogram,
            common_wrong=common_wrong,
            timing_histogram=timing_hist,
            timing_samples=timing_samples,
        ))

    # Lesson-wide aggregates
    total_sessions = len(sessions)
    total_checkpoints = len(checkpoints)
    total_attempts = len(events)
    total_solved_pairs = sum(len(v) for v in sessions_solved.values())
    possible_pairs = total_sessions * total_checkpoints
    solve_rate = (total_solved_pairs / possible_pairs * 100) if possible_pairs else 0.0

    # Per-session completion histogram: how many distinct cps each session solved.
    completion_counter: Counter = Counter()
    for s in sessions:
        completion_counter[len(sessions_solved.get(s.id, set()))] += 1
    completion_histogram = {str(i): completion_counter.get(i, 0) for i in range(0, total_checkpoints + 1)}

    # Top wrong answers across the whole lesson (group by (checkpoint_id, value))
    wrong_pair_counter: Counter = Counter()
    for row in overall_wrong:
        wrong_pair_counter[(row["checkpoint_id"], row["value"])] += 1
    top_wrong_overall = [
        {"checkpoint_id": cp_id, "value": val, "count": cnt}
        for (cp_id, val), cnt in wrong_pair_counter.most_common(5)
    ]

    summary = LessonSummaryStats(
        total_sessions=total_sessions,
        total_checkpoints=total_checkpoints,
        total_attempts=total_attempts,
        total_solved_pairs=total_solved_pairs,
        possible_pairs=possible_pairs,
        solve_rate_pct=round(solve_rate, 1),
        completion_histogram=completion_histogram,
        top_wrong_overall=top_wrong_overall,
    )

    return LiveProgressResponse(
        lesson_id=lesson_id,
        lesson_name=lesson.name,
        join_code=lesson.join_code,
        active_sessions=len(session_ids),
        summary=summary,
        checkpoints=stats,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)