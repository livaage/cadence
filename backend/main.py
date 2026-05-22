from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import os
import uuid
from datetime import datetime, timedelta

from database import get_db, engine
from models import (
    Base, Problem, TestCase, Submission, TestResult, Teacher,
    GitHubRepo, StudentCommit, CommitTestResult,
    Lesson, Checkpoint, LessonSession, AttemptEvent, SolutionReveal, CodeSubmission,
    Course, CourseNotebook, AccessLog,
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
    RotateTokenRequest, TimingSample, StudentRosterEntry, StudentCheckpointDetail,
    SolutionResponse, HintResponse, CodeSubmissionRequest, CodeSubmissionEntry,
    HeartbeatResponse, NewActivitySummary, NewActivityEntry, AttemptLogEntry,
    StuckStudent,
)
import json
import base64
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
from auth import create_access_token, get_current_teacher, optional_teacher, verify_password, get_password_hash
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
    _conn.execute(_sql("ALTER TABLE checkpoints ADD COLUMN IF NOT EXISTS hint_after_attempts INTEGER NOT NULL DEFAULT 1"))
    # Teacher auth columns — see backend/migrations/001_add_teacher_auth.sql for prod.
    _conn.execute(_sql("ALTER TABLE teachers ADD COLUMN IF NOT EXISTS github_id VARCHAR(64) UNIQUE"))
    _conn.execute(_sql("ALTER TABLE teachers ADD COLUMN IF NOT EXISTS google_id VARCHAR(64) UNIQUE"))
    _conn.execute(_sql("ALTER TABLE teachers ADD COLUMN IF NOT EXISTS display_name VARCHAR(255)"))
    _conn.execute(_sql("ALTER TABLE teachers ALTER COLUMN password_hash DROP NOT NULL"))
    _conn.execute(_sql("ALTER TABLE courses ADD COLUMN IF NOT EXISTS teacher_id UUID REFERENCES teachers(id) ON DELETE SET NULL"))
    _conn.execute(_sql("ALTER TABLE teachers ADD COLUMN IF NOT EXISTS closed_at TIMESTAMP"))
    _conn.execute(_sql("CREATE INDEX IF NOT EXISTS idx_teachers_closed_at ON teachers(closed_at)"))
    _conn.execute(_sql("ALTER TABLE teachers ADD COLUMN IF NOT EXISTS accepted_terms_at TIMESTAMP"))
    _conn.execute(_sql("UPDATE teachers SET accepted_terms_at = COALESCE(accepted_terms_at, created_at)"))
    _conn.execute(_sql("ALTER TABLE lessons ADD COLUMN IF NOT EXISTS teacher_id UUID REFERENCES teachers(id) ON DELETE SET NULL"))
    _conn.execute(_sql("CREATE INDEX IF NOT EXISTS idx_lessons_teacher_id ON lessons(teacher_id)"))
    # Retention columns — see backend/migrations/002_add_retention.sql for prod.
    _conn.execute(_sql("ALTER TABLE lessons ADD COLUMN IF NOT EXISTS session_retention_days INTEGER NOT NULL DEFAULT 7"))
    _conn.execute(_sql("ALTER TABLE courses ADD COLUMN IF NOT EXISTS session_retention_days INTEGER NOT NULL DEFAULT 90"))
    # Access log table for accountability — see backend/migrations/003_add_access_log.sql.
    _conn.execute(_sql("CREATE INDEX IF NOT EXISTS idx_access_log_occurred_at ON access_log(occurred_at)"))
    _conn.execute(_sql("CREATE INDEX IF NOT EXISTS idx_access_log_target ON access_log(target_kind, target_id)"))
    _conn.execute(_sql("CREATE INDEX IF NOT EXISTS idx_access_log_actor ON access_log(actor_kind, actor_id)"))

app = FastAPI(title="Cadence", version="1.0.0")

# CORS — defaults to local dev origins; comma-separated env var overrides for deploy.
#   CADENCE_CORS_ORIGINS=https://cadence.school.edu,https://stage.cadence.school.edu
_default_origins = "http://localhost:3000,http://127.0.0.1:3000"
_origins_env = os.getenv("CADENCE_CORS_ORIGINS", _default_origins)
ALLOWED_ORIGINS = [o.strip() for o in _origins_env.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

def log_access(
    db: Session,
    *,
    action: str,
    actor_kind: str,
    actor_id: Optional[str],
    target_kind: str,
    target_id: str,
    details: Optional[str] = None,
) -> None:
    """Append an access log entry. Caller's db.commit() writes it.

    Used for Article 5(2) accountability — significant actions on student
    data (deletions, exports). Not for high-frequency reads (dashboard polls)."""
    db.add(AccessLog(
        action=action,
        actor_kind=actor_kind,
        actor_id=actor_id,
        target_kind=target_kind,
        target_id=target_id,
        details=details,
    ))


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

@app.post("/auth/signup", response_model=Token, status_code=201)
async def signup(payload: TeacherCreate, db: Session = Depends(get_db)):
    """Public teacher signup with username/password.

    Returns a JWT directly so the client doesn't need a second round-trip.
    OAuth signups follow the same path through /auth/github/callback."""
    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if db.query(Teacher).filter(Teacher.username == payload.username).first():
        raise HTTPException(status_code=409, detail="Username already taken")
    if db.query(Teacher).filter(Teacher.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    teacher = Teacher(
        username=payload.username,
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        display_name=payload.username,
        # Signup form text says "you also agree to the Terms and Privacy notice",
        # so submission is acceptance — record the timestamp.
        accepted_terms_at=datetime.utcnow(),
    )
    db.add(teacher)
    db.commit()
    db.refresh(teacher)

    access_token = create_access_token(data={"sub": teacher.username})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/auth/login", response_model=Token)
async def login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Teacher login with username/password."""
    teacher = db.query(Teacher).filter(Teacher.username == username, Teacher.is_active == True).first()
    # password_hash is nullable for OAuth-only accounts; treat them as
    # "no local password set" rather than 500-ing on verify_password(None).
    if not teacher or not teacher.password_hash or not verify_password(password, teacher.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": teacher.username})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/auth/me", response_model=TeacherSchema)
async def whoami(current_teacher: Teacher = Depends(get_current_teacher)):
    """Return the authenticated teacher. Used by the frontend to check
    whether the stored JWT is still valid and to render the user menu."""
    return current_teacher


@app.delete("/auth/me", status_code=204)
async def close_my_account(
    current_teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    """Self-service teacher account closure. Marks the account inactive
    immediately; hard-deletion follows in ~30 days via the cleanup job. Courses
    the teacher owned remain functional via their teacher_token — the
    teacher_id FK falls to NULL when the row is finally deleted."""
    current_teacher.is_active = False
    current_teacher.closed_at = datetime.utcnow()
    log_access(
        db,
        action="close_teacher_account",
        actor_kind="teacher",
        actor_id=str(current_teacher.id),
        target_kind="teacher",
        target_id=str(current_teacher.id),
        details="self-service closure; hard-delete in 30d",
    )
    db.commit()
    return None


@app.get("/auth/providers")
async def auth_providers():
    """Which OAuth providers this deployment has credentials for. The frontend
    uses this to hide buttons that would 503 (e.g. GitHub before the OAuth app
    has been registered)."""
    return {
        "github": bool(os.getenv("GITHUB_OAUTH_CLIENT_ID") and os.getenv("GITHUB_OAUTH_CLIENT_SECRET")),
        "google": False,  # awaiting Google OAuth verification — see design doc Section 7
    }


# ---------------------------------------------------------------------------
# GitHub OAuth
# ---------------------------------------------------------------------------

import httpx
from urllib.parse import urlencode

GITHUB_CLIENT_ID = os.getenv("GITHUB_OAUTH_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_OAUTH_CLIENT_SECRET")
# Our own callback URL. Must match what's registered in the GitHub OAuth app.
GITHUB_REDIRECT_URI = os.getenv(
    "GITHUB_OAUTH_REDIRECT_URI",
    "http://localhost:8000/auth/github/callback",
)
# Where the frontend lives. After OAuth we bounce back with the JWT in the URL fragment.
FRONTEND_URL = os.getenv("CADENCE_WEB_URL", "http://localhost:3000")


@app.get("/auth/github/authorize")
async def github_authorize():
    """Kick off the GitHub OAuth flow by redirecting to GitHub."""
    if not GITHUB_CLIENT_ID:
        raise HTTPException(503, "GitHub OAuth is not configured on this server")
    params = {
        "client_id": GITHUB_CLIENT_ID,
        "redirect_uri": GITHUB_REDIRECT_URI,
        # user:email lets us see the verified primary email even when private.
        "scope": "read:user user:email",
    }
    return RedirectResponse(url=f"https://github.com/login/oauth/authorize?{urlencode(params)}")


@app.get("/auth/github/callback")
async def github_callback(code: str, db: Session = Depends(get_db)):
    """GitHub redirects here after the user authorizes. We exchange the code
    for an access token, fetch the user's profile + verified primary email,
    find-or-create a Teacher row matched by email, and bounce back to the
    frontend with our own JWT in the URL fragment."""
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        raise HTTPException(503, "GitHub OAuth is not configured on this server")

    async with httpx.AsyncClient(timeout=10) as client:
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": GITHUB_REDIRECT_URI,
            },
        )
        token_data = token_resp.json()
        if "access_token" not in token_data:
            raise HTTPException(
                400,
                f"GitHub did not return an access token: {token_data.get('error_description', 'unknown error')}",
            )
        gh_token = token_data["access_token"]
        gh_headers = {
            "Authorization": f"Bearer {gh_token}",
            "Accept": "application/vnd.github+json",
        }

        user_resp = await client.get("https://api.github.com/user", headers=gh_headers)
        user_resp.raise_for_status()
        user = user_resp.json()
        github_id = str(user["id"])

        # GitHub emails are often private; /user/emails returns the verified primary.
        emails_resp = await client.get("https://api.github.com/user/emails", headers=gh_headers)
        emails_resp.raise_for_status()
        emails = emails_resp.json()
        primary = next((e for e in emails if e.get("primary") and e.get("verified")), None)
        if not primary:
            raise HTTPException(
                400,
                "No verified primary email on your GitHub account. Add one in GitHub settings and retry.",
            )
        email = primary["email"]

    # Find-or-create: prefer github_id match (returning user), fall back to email
    # (auto-link to an existing password account), else create fresh.
    teacher = db.query(Teacher).filter(Teacher.github_id == github_id).first()
    if not teacher:
        teacher = db.query(Teacher).filter(Teacher.email == email).first()
        if teacher:
            teacher.github_id = github_id
        else:
            base_username = (user.get("login") or email.split("@")[0]).lower()
            username = base_username
            suffix = 1
            while db.query(Teacher).filter(Teacher.username == username).first():
                suffix += 1
                username = f"{base_username}{suffix}"
            teacher = Teacher(
                username=username,
                email=email,
                github_id=github_id,
                display_name=user.get("name") or base_username,
                # password_hash stays None — OAuth-only account.
                # GitHub sign-in implies Terms acceptance (the sign-in button
                # is on a page that links to /terms above the button).
                accepted_terms_at=datetime.utcnow(),
            )
            db.add(teacher)
    db.commit()
    db.refresh(teacher)

    our_jwt = create_access_token(data={"sub": teacher.username})
    # Fragment (#) keeps the JWT out of server logs and Referer headers.
    return RedirectResponse(url=f"{FRONTEND_URL}/teacher/auth-callback#token={our_jwt}")

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

    elif comparator == "manual":
        # Student self-attests completion — no automated check, always counts as done.
        result = True
        reason = "manual self-attestation"

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
async def create_lesson(
    payload: LessonCreate,
    db: Session = Depends(get_db),
    teacher: Optional[Teacher] = Depends(optional_teacher),
):
    """Create a lesson. The returned teacher_token IS the credential — anyone
    holding it can manage the lesson. If the request is authenticated we also
    stamp the teacher_id so the lesson shows up in /lessons/mine.

    If the caller supplies `join_code` or `teacher_token` and either collides,
    returns 409 so the client can retry with a different value.
    """
    join_code = payload.join_code or _generate_join_code(db)
    teacher_token = payload.teacher_token or secrets.token_urlsafe(24)

    if db.query(Lesson).filter(Lesson.join_code == join_code).first():
        raise HTTPException(status_code=409, detail="join_code already in use")
    if db.query(Lesson).filter(Lesson.teacher_token == teacher_token).first():
        raise HTTPException(status_code=409, detail="teacher_token already in use")

    lesson = Lesson(
        name=payload.name,
        join_code=join_code,
        teacher_token=teacher_token,
        teacher_id=teacher.id if teacher else None,
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


@app.get("/lessons/mine", response_model=List[LessonSummary])
async def list_my_lessons(
    current_teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    """Lessons created by the authenticated teacher. Excludes lessons that
    have been attached to a course (those show up via the course view instead)."""
    attached_lesson_ids = db.query(CourseNotebook.lesson_id).distinct().subquery()
    return (
        db.query(Lesson)
        .filter(Lesson.teacher_id == current_teacher.id)
        .filter(~Lesson.id.in_(attached_lesson_ids))
        .order_by(Lesson.created_at.desc())
        .all()
    )


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
    if payload.comparator not in {"exact", "numeric", "set", "regex", "manual"}:
        raise HTTPException(status_code=400, detail="Invalid comparator")
    if payload.comparator != "manual" and not payload.expected_payload:
        raise HTTPException(
            status_code=400,
            detail=f"`expected_payload` is required for comparator={payload.comparator}",
        )

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
        existing.hint_after_attempts = payload.hint_after_attempts
        existing.order_index = payload.order_index
        existing.reveal_after_attempts = payload.reveal_after_attempts
        existing.solution_value = payload.solution_value
        existing.solution_code = payload.solution_code
        existing.allow_submissions = payload.allow_submissions
    else:
        existing = Checkpoint(
            lesson_id=lesson_id_str,
            checkpoint_id=payload.checkpoint_id,
            comparator=payload.comparator,
            expected_payload=payload.expected_payload,
            hint=payload.hint,
            hint_after_attempts=payload.hint_after_attempts,
            order_index=payload.order_index,
            reveal_after_attempts=payload.reveal_after_attempts,
            solution_value=payload.solution_value,
            solution_code=payload.solution_code,
            allow_submissions=payload.allow_submissions,
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
            hint_after_attempts=r.hint_after_attempts or 1,
            order_index=r.order_index,
            reveal_after_attempts=r.reveal_after_attempts,
            has_solution_value=bool(r.solution_value),
            has_solution_code=bool(r.solution_code),
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
async def create_course(
    payload: CourseCreate,
    db: Session = Depends(get_db),
    teacher: Optional[Teacher] = Depends(optional_teacher),
):
    """Create a course. If the request is authenticated, the course is owned
    by that teacher; otherwise it's a token-only course (legacy / quick flow)."""
    join_code = payload.join_code or _generate_join_code(db)
    teacher_token = payload.teacher_token or secrets.token_urlsafe(24)

    if db.query(Course).filter(Course.join_code == join_code).first():
        raise HTTPException(status_code=409, detail="join_code already in use")
    if db.query(Lesson).filter(Lesson.join_code == join_code).first():
        raise HTTPException(status_code=409, detail="join_code already used by a lesson")
    if db.query(Course).filter(Course.teacher_token == teacher_token).first():
        raise HTTPException(status_code=409, detail="teacher_token already in use")

    retention = payload.session_retention_days
    if retention is not None and not (1 <= retention <= 365):
        raise HTTPException(400, "session_retention_days must be between 1 and 365")

    course = Course(
        name=payload.name,
        join_code=join_code,
        teacher_token=teacher_token,
        teacher_id=teacher.id if teacher else None,
        **({"session_retention_days": retention} if retention is not None else {}),
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@app.get("/courses/mine", response_model=List[CourseSummary])
async def list_my_courses(
    current_teacher: Teacher = Depends(get_current_teacher),
    db: Session = Depends(get_db),
):
    """List all courses owned by the authenticated teacher."""
    return (
        db.query(Course)
        .filter(Course.teacher_id == current_teacher.id)
        .order_by(Course.created_at.desc())
        .all()
    )


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


@app.delete("/courses/by-token/{teacher_token}/notebooks", status_code=204)
async def detach_notebook_from_course(
    teacher_token: str,
    lesson_teacher_token: str,
    db: Session = Depends(get_db),
):
    """Remove the course→lesson association without deleting either side.
    The lesson keeps its own teacher_token, join_code, and student data — it
    just no longer shows up under this course's dashboard."""
    course = _require_course_by_token(db, teacher_token)
    lesson = _require_lesson_by_token(db, lesson_teacher_token)
    db.query(CourseNotebook).filter(
        CourseNotebook.course_id == course.id,
        CourseNotebook.lesson_id == lesson.id,
    ).delete(synchronize_session=False)
    db.commit()
    return None


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
    # Per-notebook difficulty input: for each (session, checkpoint) pair within a
    # notebook, track {first_correct_attempt_num | None, max_attempt_num}. A pair's
    # resolution cost is first_correct (solved) or max_attempt (gave up).
    pair_state: dict = defaultdict(dict)  # notebook_id -> (sid, cp_id) -> {fc, max}
    for e in events:
        sessions_touching_notebook[e.lesson_id].add(e.session_id)
        key = (e.session_id, e.checkpoint_id)
        cur = pair_state[e.lesson_id].get(key, {"fc": None, "max": 0})
        if e.attempt_num > cur["max"]:
            cur["max"] = e.attempt_num
        if e.is_correct and (cur["fc"] is None or e.attempt_num < cur["fc"]):
            cur["fc"] = e.attempt_num
        pair_state[e.lesson_id][key] = cur

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

        pairs = pair_state.get(nb_id, {})
        if pairs:
            cost_sum = sum(p["fc"] if p["fc"] is not None else p["max"] for p in pairs.values())
            avg_attempts = round(cost_sum / len(pairs), 2)
        else:
            avg_attempts = None

        notebook_stats.append(CourseNotebookStat(
            lesson_id=nb_id,
            name=nb["name"],
            order_index=nb["order_index"],
            students_here_now=here_now.get(nb_id, 0),
            total_attempts=attempts_by_notebook.get(nb_id, 0),
            solved_rate_pct=solved_rate,
            avg_attempts=avg_attempts,
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

    # Rate limit: prevent runaway notebooks (e.g. a check() inside a loop) and
    # casual abuse. 100 attempts per (session, checkpoint) in any 60s window is
    # generous enough that no real student hits it, tight enough that a bug stops fast.
    recent = (
        db.query(AttemptEvent)
        .filter(
            AttemptEvent.session_id == session.id,
            AttemptEvent.checkpoint_id == payload.checkpoint_id,
            AttemptEvent.created_at >= datetime.utcnow() - timedelta(seconds=60),
        )
        .count()
    )
    if recent >= 100:
        raise HTTPException(
            status_code=429,
            detail=(
                "Too many attempts on this checkpoint in the last minute. "
                "Check that you're not running check() inside a loop, then try again shortly."
            ),
        )

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

    # Hint availability: teacher set a hint AND attempts >= hint_after_attempts.
    # Student opts in by running cadence.show_hint() — we don't inline the text.
    hint_threshold = checkpoint.hint_after_attempts or 1
    hint_available = bool(
        not is_correct
        and checkpoint.hint
        and attempt_num >= hint_threshold
    )

    # Solution-reveal availability: only when the teacher configured a threshold
    # AND at least one of solution_value/solution_code is set AND attempts >= N.
    solution_available = bool(
        checkpoint.reveal_after_attempts is not None
        and (checkpoint.solution_value or checkpoint.solution_code)
        and attempt_num >= checkpoint.reveal_after_attempts
    )

    return CheckResponse(
        is_correct=is_correct,
        attempt_num=attempt_num,
        elapsed_ms=elapsed_ms,
        is_manual=(checkpoint.comparator == "manual"),
        hint_available=hint_available,
        solution_available=solution_available,
    )


def _find_checkpoint_for_session(db: Session, session: LessonSession, checkpoint_id: str):
    """Resolve a checkpoint id within a session's scope (course-wide or single lesson)."""
    if session.course_id:
        notebook_ids = [
            str(row.lesson_id)
            for row in db.query(CourseNotebook.lesson_id)
            .filter(CourseNotebook.course_id == session.course_id)
            .all()
        ]
        return (
            db.query(Checkpoint)
            .filter(Checkpoint.lesson_id.in_(notebook_ids), Checkpoint.checkpoint_id == checkpoint_id)
            .first()
        )
    return (
        db.query(Checkpoint)
        .filter(Checkpoint.lesson_id == session.lesson_id, Checkpoint.checkpoint_id == checkpoint_id)
        .first()
    )


@app.get(
    "/sessions/{session_id}/checkpoints/{checkpoint_id}/hint",
    response_model=HintResponse,
)
async def get_hint(session_id: str, checkpoint_id: str, db: Session = Depends(get_db)):
    """Student fetches the hint for a checkpoint they're stuck on.

    Gated on: the teacher set a hint AND this session has logged at least
    `hint_after_attempts` attempts (default 1)."""
    session = db.query(LessonSession).filter(LessonSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    cp = _find_checkpoint_for_session(db, session, checkpoint_id)
    if not cp:
        raise HTTPException(status_code=404, detail="Checkpoint not registered")
    if not cp.hint:
        raise HTTPException(status_code=404, detail="No hint configured for this checkpoint")
    attempts = (
        db.query(AttemptEvent)
        .filter(AttemptEvent.session_id == session.id, AttemptEvent.checkpoint_id == checkpoint_id)
        .count()
    )
    threshold = cp.hint_after_attempts or 1
    if attempts < threshold:
        raise HTTPException(
            status_code=403,
            detail=f"Hint unlocks after {threshold} attempts; you have {attempts}.",
        )
    return HintResponse(checkpoint_id=checkpoint_id, hint=cp.hint)


@app.get(
    "/sessions/{session_id}/checkpoints/{checkpoint_id}/solution",
    response_model=SolutionResponse,
)
async def get_solution(session_id: str, checkpoint_id: str, db: Session = Depends(get_db)):
    """Student fetches the worked solution for a checkpoint they've been working on.

    Gated on: the teacher has configured `reveal_after_attempts` for this checkpoint
    AND this session has logged at least that many attempts against it.
    """
    session = db.query(LessonSession).filter(LessonSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Find the checkpoint via the same scoping rules as /check.
    if session.course_id:
        notebook_ids = [
            str(row.lesson_id)
            for row in db.query(CourseNotebook.lesson_id)
            .filter(CourseNotebook.course_id == session.course_id)
            .all()
        ]
        cp = (
            db.query(Checkpoint)
            .filter(Checkpoint.lesson_id.in_(notebook_ids), Checkpoint.checkpoint_id == checkpoint_id)
            .first()
        )
    else:
        cp = (
            db.query(Checkpoint)
            .filter(Checkpoint.lesson_id == session.lesson_id, Checkpoint.checkpoint_id == checkpoint_id)
            .first()
        )
    if not cp:
        raise HTTPException(status_code=404, detail="Checkpoint not registered")
    if cp.reveal_after_attempts is None or (cp.solution_value is None and cp.solution_code is None):
        raise HTTPException(status_code=404, detail="No solution configured for this checkpoint")

    attempts = (
        db.query(AttemptEvent)
        .filter(AttemptEvent.session_id == session.id, AttemptEvent.checkpoint_id == checkpoint_id)
        .count()
    )
    if attempts < cp.reveal_after_attempts:
        raise HTTPException(
            status_code=403,
            detail=f"Solution unlocks after {cp.reveal_after_attempts} attempts; you have {attempts}.",
        )

    # Log the reveal (first time only — UNIQUE constraint on (session_id, checkpoint_id)
    # makes repeat reveals a no-op for counter purposes).
    existing_reveal = (
        db.query(SolutionReveal)
        .filter(
            SolutionReveal.session_id == session.id,
            SolutionReveal.checkpoint_id == checkpoint_id,
        )
        .first()
    )
    if not existing_reveal:
        db.add(SolutionReveal(
            session_id=session.id,
            lesson_id=cp.lesson_id,
            checkpoint_id=checkpoint_id,
        ))
        db.commit()

    return SolutionResponse(
        checkpoint_id=checkpoint_id,
        solution_value=cp.solution_value,
        solution_code=cp.solution_code,
    )


@app.get("/sessions/{session_id}/my-data")
async def get_session_my_data(session_id: str, db: Session = Depends(get_db)):
    """Student's right of access (GDPR Article 15) and portability (Article 20):
    everything Cadence stores for this session, in machine-readable JSON.

    The student knows their own session_id from the join flow; we never surface
    it beyond the owner. Binary image attachments are summarized as `has_image`
    (request the raw image via privacy@ if you need it exported)."""
    session = db.query(LessonSession).filter(LessonSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    attempts = db.query(AttemptEvent).filter(AttemptEvent.session_id == session.id).all()
    submissions = db.query(CodeSubmission).filter(CodeSubmission.session_id == session.id).all()
    reveals = db.query(SolutionReveal).filter(SolutionReveal.session_id == session.id).all()

    log_access(
        db,
        action="export_my_data",
        actor_kind="student",
        actor_id=str(session.id),
        target_kind="session",
        target_id=str(session.id),
        details=f"counts: attempts={len(attempts)} submissions={len(submissions)} reveals={len(reveals)}",
    )
    db.commit()

    return {
        "session": {
            "id": str(session.id),
            "display_name": session.display_name,
            "lesson_id": session.lesson_id,
            "course_id": session.course_id,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "last_seen_at": session.last_seen_at.isoformat() if session.last_seen_at else None,
        },
        "attempts": [
            {
                "id": str(a.id),
                "lesson_id": a.lesson_id,
                "checkpoint_id": a.checkpoint_id,
                "attempt_num": a.attempt_num,
                "submitted_value": a.submitted_value,
                "is_correct": a.is_correct,
                "elapsed_ms": a.elapsed_ms,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in attempts
        ],
        "code_submissions": [
            {
                "id": str(s.id),
                "lesson_id": s.lesson_id,
                "checkpoint_id": s.checkpoint_id,
                "code": s.code,
                "language": s.language,
                "has_image": s.image_data is not None,
                "image_mime": s.image_mime,
                "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
            }
            for s in submissions
        ],
        "solution_reveals": [
            {
                "id": str(r.id),
                "lesson_id": r.lesson_id,
                "checkpoint_id": r.checkpoint_id,
                "revealed_at": r.revealed_at.isoformat() if r.revealed_at else None,
            }
            for r in reveals
        ],
        "_meta": {
            "exported_at": datetime.utcnow().isoformat(),
            "purpose": "Right of access (GDPR Article 15) and portability (Article 20).",
            "recipients": "Your teacher only; no other party.",
            "retention": "Deleted at the teacher-configured expiry for this session.",
            "rights": "To delete this data, run %cadence_delete_my_data or DELETE /sessions/{session_id}.",
            "contact": "privacy@cadence-dash.com",
        },
    }


@app.delete("/sessions/{session_id}", status_code=204)
async def delete_session(session_id: str, db: Session = Depends(get_db)):
    """Student-initiated GDPR-style deletion: wipe a session and everything that
    references it (attempts, submissions, solution-reveals). The student knows their
    own session_id from the join flow; no other credential needed because we never
    surface the session_id beyond the student who owns it."""
    session = db.query(LessonSession).filter(LessonSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    attempt_count = db.query(AttemptEvent).filter(AttemptEvent.session_id == session.id).delete(synchronize_session=False)
    sub_count = db.query(CodeSubmission).filter(CodeSubmission.session_id == session.id).delete(synchronize_session=False)
    rev_count = db.query(SolutionReveal).filter(SolutionReveal.session_id == session.id).delete(synchronize_session=False)
    # Log first — the session row is about to disappear. log_access lives in
    # the same transaction so it's all-or-nothing with the deletion.
    log_access(
        db,
        action="delete_session",
        actor_kind="student",
        actor_id=str(session.id),
        target_kind="session",
        target_id=str(session.id),
        details=f"wiped: attempts={attempt_count} submissions={sub_count} reveals={rev_count}",
    )
    db.delete(session)
    db.commit()
    return None


@app.delete("/courses/by-token/{teacher_token}", status_code=204)
async def delete_course(teacher_token: str, db: Session = Depends(get_db)):
    """Teacher-initiated deletion: wipe a course, every session that joined it,
    every attempt, every submission. Requires the course teacher_token (the
    course's owner credential). Attached lessons are detached but kept — they
    remain available standalone unless deleted separately."""
    course = _require_course_by_token(db, teacher_token)
    cid = str(course.id)

    # Sessions joined directly via the course join code.
    session_ids = [s.id for s in db.query(LessonSession.id).filter(LessonSession.course_id == cid).all()]
    if session_ids:
        db.query(AttemptEvent).filter(AttemptEvent.session_id.in_(session_ids)).delete(synchronize_session=False)
        db.query(CodeSubmission).filter(CodeSubmission.session_id.in_(session_ids)).delete(synchronize_session=False)
        db.query(SolutionReveal).filter(SolutionReveal.session_id.in_(session_ids)).delete(synchronize_session=False)
        db.query(LessonSession).filter(LessonSession.id.in_(session_ids)).delete(synchronize_session=False)
    # Detach the join rows but keep the lessons themselves — they may still
    # be in use standalone or in other courses.
    db.query(CourseNotebook).filter(CourseNotebook.course_id == course.id).delete(synchronize_session=False)
    log_access(
        db,
        action="delete_course",
        actor_kind="teacher",
        actor_id=f"token:{teacher_token[:8]}...",
        target_kind="course",
        target_id=cid,
        details=f"wiped: course_sessions={len(session_ids)}",
    )
    db.delete(course)
    db.commit()
    return None


@app.post("/lessons/by-token/{teacher_token}/clone", response_model=LessonSummary, status_code=201)
async def clone_lesson(
    teacher_token: str,
    payload: LessonCreate,
    db: Session = Depends(get_db),
    teacher: Optional[Teacher] = Depends(optional_teacher),
):
    """Duplicate a lesson with all its checkpoints. The new lesson gets a fresh
    join_code and teacher_token; checkpoints are copied 1:1 (including hints,
    solutions, comparators). Useful for re-running the same lesson next term
    without polluting last term's data."""
    source = _require_lesson_by_token(db, teacher_token)
    new_name = payload.name or f"{source.name} (copy)"
    new_join = payload.join_code or _generate_join_code(db)
    new_tok = payload.teacher_token or secrets.token_urlsafe(24)

    if db.query(Lesson).filter(Lesson.join_code == new_join).first():
        raise HTTPException(status_code=409, detail="join_code already in use")
    if db.query(Lesson).filter(Lesson.teacher_token == new_tok).first():
        raise HTTPException(status_code=409, detail="teacher_token already in use")

    clone = Lesson(
        name=new_name,
        join_code=new_join,
        teacher_token=new_tok,
        teacher_id=teacher.id if teacher else None,
        session_retention_days=source.session_retention_days,
    )
    db.add(clone)
    db.flush()  # need clone.id for the checkpoint rows

    for cp in db.query(Checkpoint).filter(Checkpoint.lesson_id == str(source.id)).all():
        db.add(Checkpoint(
            lesson_id=str(clone.id),
            checkpoint_id=cp.checkpoint_id,
            comparator=cp.comparator,
            expected_payload=cp.expected_payload,
            hint=cp.hint,
            hint_after_attempts=cp.hint_after_attempts,
            reveal_after_attempts=cp.reveal_after_attempts,
            solution_value=cp.solution_value,
            solution_code=cp.solution_code,
            allow_submissions=cp.allow_submissions,
            order_index=cp.order_index,
        ))
    db.commit()
    db.refresh(clone)
    return clone


@app.delete("/lessons/by-token/{teacher_token}", status_code=204)
async def delete_lesson(teacher_token: str, db: Session = Depends(get_db)):
    """Teacher-initiated deletion: wipe a lesson, every session that joined it,
    every attempt, every submission, every solution-reveal. Requires the teacher
    token (the lesson's owner credential)."""
    lesson = _require_lesson_by_token(db, teacher_token)
    lid = str(lesson.id)

    session_ids = [s.id for s in db.query(LessonSession.id).filter(LessonSession.lesson_id == lid).all()]
    if session_ids:
        db.query(AttemptEvent).filter(AttemptEvent.session_id.in_(session_ids)).delete(synchronize_session=False)
        db.query(CodeSubmission).filter(CodeSubmission.session_id.in_(session_ids)).delete(synchronize_session=False)
        db.query(SolutionReveal).filter(SolutionReveal.session_id.in_(session_ids)).delete(synchronize_session=False)
        db.query(LessonSession).filter(LessonSession.id.in_(session_ids)).delete(synchronize_session=False)
    db.query(Checkpoint).filter(Checkpoint.lesson_id == lid).delete(synchronize_session=False)
    db.query(CourseNotebook).filter(CourseNotebook.lesson_id == lesson.id).delete(synchronize_session=False)
    log_access(
        db,
        action="delete_lesson",
        actor_kind="teacher",
        # We don't have a teacher account on lessons (token-only), so the
        # token holder IS the identifier. Truncate to avoid leaking the full
        # token into logs — first 8 chars are plenty to correlate.
        actor_id=f"token:{teacher_token[:8]}...",
        target_kind="lesson",
        target_id=lid,
        details=f"wiped: sessions={len(session_ids)}",
    )
    db.delete(lesson)
    db.commit()
    return None


@app.post("/sessions/{session_id}/submissions", status_code=201)
async def submit_code(session_id: str, payload: CodeSubmissionRequest, db: Session = Depends(get_db)):
    """Student submits a code snippet for a checkpoint that has `allow_submissions=true`.

    Multiple submissions per (session, checkpoint) are allowed; the dashboard
    shows the chronological feed (most recent first).
    """
    if str(payload.session_id) != session_id:
        raise HTTPException(status_code=400, detail="session_id in path and body must match")
    session = db.query(LessonSession).filter(LessonSession.id == payload.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Find the checkpoint via the same scoping rules as /check.
    if session.course_id:
        notebook_ids = [
            str(row.lesson_id)
            for row in db.query(CourseNotebook.lesson_id)
            .filter(CourseNotebook.course_id == session.course_id)
            .all()
        ]
        cp = (
            db.query(Checkpoint)
            .filter(Checkpoint.lesson_id.in_(notebook_ids), Checkpoint.checkpoint_id == payload.checkpoint_id)
            .first()
        )
    else:
        cp = (
            db.query(Checkpoint)
            .filter(Checkpoint.lesson_id == session.lesson_id, Checkpoint.checkpoint_id == payload.checkpoint_id)
            .first()
        )
    if not cp:
        raise HTTPException(status_code=404, detail="Checkpoint not registered")
    if not cp.allow_submissions:
        raise HTTPException(
            status_code=400,
            detail="This checkpoint doesn't accept code submissions. Ask the teacher to register it with --allow-submissions.",
        )

    code = (payload.code or "").strip() or None
    image_bytes: Optional[bytes] = None
    if payload.image_data_b64:
        try:
            image_bytes = base64.b64decode(payload.image_data_b64, validate=True)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid base64 in image_data_b64")
        if len(image_bytes) > 1_000_000:
            raise HTTPException(status_code=400, detail="Image too large (1 MB limit)")

    if not code and not image_bytes:
        raise HTTPException(status_code=400, detail="Empty submission — provide code, image, or both")
    if code and len(code) > 50_000:
        raise HTTPException(status_code=400, detail="Code too large (50KB limit)")

    sub = CodeSubmission(
        session_id=session.id,
        lesson_id=cp.lesson_id,
        checkpoint_id=payload.checkpoint_id,
        code=code,
        language=payload.language or "python",
        image_data=image_bytes,
        image_mime=payload.image_mime if image_bytes else None,
    )
    db.add(sub)
    session.last_seen_at = datetime.utcnow()
    db.commit()
    db.refresh(sub)
    return {"id": str(sub.id), "submitted_at": sub.submitted_at.isoformat()}


@app.get(
    "/lessons/by-token/{teacher_token}/checkpoints/{checkpoint_id}/submissions",
    response_model=List[CodeSubmissionEntry],
)
async def list_submissions(
    teacher_token: str,
    checkpoint_id: str,
    db: Session = Depends(get_db),
):
    """Teacher fetches all code submissions for one checkpoint, newest first."""
    lesson = _require_lesson_by_token(db, teacher_token)
    rows = (
        db.query(CodeSubmission, LessonSession.display_name)
        .join(LessonSession, LessonSession.id == CodeSubmission.session_id)
        .filter(
            CodeSubmission.lesson_id == str(lesson.id),
            CodeSubmission.checkpoint_id == checkpoint_id,
        )
        .order_by(CodeSubmission.submitted_at.desc())
        .all()
    )
    return [
        CodeSubmissionEntry(
            id=str(sub.id),
            checkpoint_id=sub.checkpoint_id,
            code=sub.code,
            language=sub.language,
            submitted_at=sub.submitted_at,
            display_name=display_name,
            image_data_b64=(
                base64.b64encode(sub.image_data).decode("ascii") if sub.image_data else None
            ),
            image_mime=sub.image_mime,
        )
        for sub, display_name in rows
    ]


@app.get(
    "/lessons/by-token/{teacher_token}/heartbeat",
    response_model=HeartbeatResponse,
)
async def get_lesson_heartbeat(
    teacher_token: str,
    scope: str = "current",
    course_token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Cheap freshness probe. Returns max(created_at) over relevant attempts +
    sessions plus current counts. Frontend polls this every few seconds and
    only refetches the heavy /live endpoint when one of these numbers changes."""
    lesson = _require_lesson_by_token(db, teacher_token)
    lesson_id = str(lesson.id)

    if scope == "alltime":
        session_filter = None
    elif scope == "course":
        if not course_token:
            raise HTTPException(status_code=400, detail="scope=course requires course_token")
        course = _require_course_by_token(db, course_token)
        session_filter = lambda q: q.filter(LessonSession.course_id == str(course.id))
    else:
        session_filter = lambda q: q.filter(
            LessonSession.lesson_id == lesson_id, LessonSession.course_id.is_(None)
        )

    sessions_q = db.query(LessonSession)
    if session_filter is not None:
        sessions_q = session_filter(sessions_q)
    total_sessions = sessions_q.count()
    last_session_at = sessions_q.with_entities(func.max(LessonSession.last_seen_at)).scalar()

    if scope == "alltime":
        attempts_q = db.query(AttemptEvent).filter(AttemptEvent.lesson_id == lesson_id)
    else:
        # Restrict attempts to the relevant session set.
        session_ids_subq = sessions_q.with_entities(LessonSession.id)
        attempts_q = db.query(AttemptEvent).filter(
            AttemptEvent.lesson_id == lesson_id,
            AttemptEvent.session_id.in_(session_ids_subq),
        )
    total_attempts = attempts_q.count()
    last_attempt_at = attempts_q.with_entities(func.max(AttemptEvent.created_at)).scalar()

    return HeartbeatResponse(
        lesson_id=lesson_id,
        last_attempt_at=last_attempt_at,
        last_session_at=last_session_at,
        total_attempts=total_attempts,
        total_sessions=total_sessions,
    )


@app.get("/lessons/by-token/{teacher_token}/live", response_model=LiveProgressResponse)
async def get_live_progress(
    teacher_token: str,
    scope: str = "current",
    course_token: Optional[str] = None,
    since: Optional[datetime] = None,
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
    else:  # "current" — standalone joiners only (joined this notebook directly, no course)
        sessions = (
            db.query(LessonSession)
            .filter(
                LessonSession.lesson_id == lesson_id,
                LessonSession.course_id.is_(None),
            )
            .all()
        )
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
    session_id_to_name: dict = {s.id: s.display_name for s in sessions}

    # Distinct sessions that revealed the solution per checkpoint, scoped to the
    # current session set so the counter respects the active scope (standalone /
    # course / alltime).
    reveal_rows = (
        db.query(SolutionReveal.checkpoint_id, SolutionReveal.session_id)
        .filter(
            SolutionReveal.lesson_id == lesson_id,
            SolutionReveal.session_id.in_(session_ids_set) if session_ids_set else False,
        )
        .all()
    ) if session_ids_set else []
    reveals_by_cp: dict = defaultdict(set)
    for cp_id, sid in reveal_rows:
        reveals_by_cp[cp_id].add(sid)

    # Per-checkpoint submission counts, scoped to active sessions.
    submission_counts: dict = defaultdict(int)
    if session_ids_set:
        sub_rows = (
            db.query(CodeSubmission.checkpoint_id)
            .filter(
                CodeSubmission.lesson_id == lesson_id,
                CodeSubmission.session_id.in_(session_ids_set),
            )
            .all()
        )
        for (cp_id,) in sub_rows:
            submission_counts[cp_id] += 1

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
        timing_samples_detail: List[TimingSample] = []
        wrong_counter: Counter = Counter()
        wrong_names: dict = defaultdict(list)  # value -> [display_name, ...]
        # For the difficulty metric: sum attempts-to-first-solve across sessions
        # (counts up to and including the first correct attempt for solvers,
        # or all attempts for sessions that never solved).
        sum_attempts_to_resolve = 0

        for sid, attempts in per_session_attempts.items():
            first_correct_idx = next((i for i, a in enumerate(attempts) if a.is_correct), None)
            if first_correct_idx is None:
                histogram["unsolved"] += 1
                sum_attempts_to_resolve += len(attempts)
            else:
                sum_attempts_to_resolve += first_correct_idx + 1
                if first_correct_idx == 0:
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
                    timing_samples_detail.append(TimingSample(
                        display_name=session_id_to_name.get(sid, "(anonymous)"),
                        elapsed_ms=correct_attempt.elapsed_ms,
                    ))

            for a in attempts:
                if not a.is_correct and a.submitted_value:
                    wrong_counter[a.submitted_value] += 1
                    wrong_names[a.submitted_value].append(
                        session_id_to_name.get(sid, "(anonymous)")
                    )
                    overall_wrong.append({
                        "checkpoint_id": cp.checkpoint_id,
                        "value": a.submitted_value,
                        "display_name": session_id_to_name.get(sid, "(anonymous)"),
                    })

        common_wrong = [
            {
                "value": v,
                "count": c,
                # de-dup names while preserving order; cap to 8 for payload size
                "student_names": list(dict.fromkeys(wrong_names[v]))[:8],
            }
            for v, c in wrong_counter.most_common(5)
        ]

        attempted = len(per_session_attempts)
        solved = histogram["1"] + histogram["2"] + histogram["3+"]
        avg_attempts = round(sum_attempts_to_resolve / attempted, 2) if attempted else None

        stats.append(CheckpointLiveStats(
            checkpoint_id=cp.checkpoint_id,
            order_index=cp.order_index,
            comparator=cp.comparator,
            attempted=attempted,
            solved=solved,
            total_attempts=len(cp_events),
            attempts_histogram=histogram,
            common_wrong=common_wrong,
            timing_histogram=timing_hist,
            timing_samples=timing_samples,
            timing_samples_detail=timing_samples_detail,
            avg_attempts=avg_attempts,
            has_hint=bool(cp.hint),
            hint_after_attempts=cp.hint_after_attempts or 1,
            reveal_after_attempts=cp.reveal_after_attempts,
            has_solution=bool(cp.solution_value or cp.solution_code),
            solution_views=len(reveals_by_cp.get(cp.checkpoint_id, set())),
            allow_submissions=cp.allow_submissions,
            submission_count=submission_counts.get(cp.checkpoint_id, 0),
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
    wrong_pair_names: dict = defaultdict(list)
    for row in overall_wrong:
        key = (row["checkpoint_id"], row["value"])
        wrong_pair_counter[key] += 1
        wrong_pair_names[key].append(row["display_name"])
    top_wrong_overall = [
        {
            "checkpoint_id": cp_id,
            "value": val,
            "count": cnt,
            "student_names": list(dict.fromkeys(wrong_pair_names[(cp_id, val)]))[:8],
        }
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

    # Per-session roster: one entry per student with per-checkpoint detail.
    # Group events first.
    sid_cp_events: dict = defaultdict(list)
    chronology_by_sid: dict = defaultdict(list)  # session_id -> [events in chronological order]
    for e in events:
        sid_cp_events[(e.session_id, e.checkpoint_id)].append(e)
        chronology_by_sid[e.session_id].append(e)

    # Most recent attempt per session (by created_at), for the "currently on" chip
    most_recent_cp: dict = {}
    for e in events:
        prev = most_recent_cp.get(e.session_id)
        if prev is None or e.created_at > prev[0]:
            most_recent_cp[e.session_id] = (e.created_at, e.checkpoint_id)

    roster: List[StudentRosterEntry] = []
    for s in sessions:
        per_cp: List[StudentCheckpointDetail] = []
        cp_solved = 0
        cp_attempted = 0
        total_atts = 0
        fastest_ms: Optional[int] = None
        for cp in checkpoints:
            cp_attempts = sid_cp_events.get((s.id, cp.checkpoint_id), [])
            if not cp_attempts:
                per_cp.append(StudentCheckpointDetail(
                    checkpoint_id=cp.checkpoint_id,
                    status="untouched",
                    attempts=0,
                ))
                continue
            cp_attempted += 1
            total_atts += len(cp_attempts)
            first_correct = next((a for a in cp_attempts if a.is_correct), None)
            if first_correct is None:
                per_cp.append(StudentCheckpointDetail(
                    checkpoint_id=cp.checkpoint_id,
                    status="attempted",
                    attempts=len(cp_attempts),
                ))
            else:
                cp_solved += 1
                elapsed = first_correct.elapsed_ms
                if elapsed is not None and (fastest_ms is None or elapsed < fastest_ms):
                    fastest_ms = elapsed
                per_cp.append(StudentCheckpointDetail(
                    checkpoint_id=cp.checkpoint_id,
                    status="solved",
                    attempts=len(cp_attempts),
                    first_correct_attempt=first_correct.attempt_num,
                    elapsed_ms_first_correct=elapsed,
                ))
        recent = most_recent_cp.get(s.id)
        # Most recent 50 attempts in reverse-chronological order — drives the drill-in
        student_events = sorted(chronology_by_sid.get(s.id, []), key=lambda e: e.created_at, reverse=True)[:50]
        chronology = [
            AttemptLogEntry(
                checkpoint_id=e.checkpoint_id,
                attempt_num=e.attempt_num,
                is_correct=e.is_correct,
                submitted_value=e.submitted_value,
                elapsed_ms=e.elapsed_ms,
                created_at=e.created_at,
            )
            for e in student_events
        ]
        roster.append(StudentRosterEntry(
            session_id=str(s.id),
            display_name=s.display_name,
            last_seen_at=s.last_seen_at,
            total_attempts=total_atts,
            checkpoints_solved=cp_solved,
            checkpoints_attempted=cp_attempted,
            fastest_elapsed_ms=fastest_ms,
            current_checkpoint_id=recent[1] if recent else None,
            per_checkpoint=per_cp,
            chronology=chronology,
        ))
    # Sort by most recently active first
    roster.sort(key=lambda r: r.last_seen_at, reverse=True)

    # Per-scope counts so the frontend can hide empty tabs.
    standalone_count = (
        db.query(LessonSession)
        .filter(LessonSession.lesson_id == lesson_id, LessonSession.course_id.is_(None))
        .count()
    )
    course_count = None
    if course_token:
        course_obj = _require_course_by_token(db, course_token)
        course_count = (
            db.query(LessonSession).filter(LessonSession.course_id == str(course_obj.id)).count()
        )
    alltime_count = (
        db.query(AttemptEvent.session_id)
        .filter(AttemptEvent.lesson_id == lesson_id)
        .distinct()
        .count()
    )
    scope_counts = {
        "standalone": standalone_count,
        "course": course_count,
        "alltime": alltime_count,
    }

    # Stuck-student detection — surfaces students likely needing 1:1 help.
    # Heuristic: per (session, checkpoint), 3+ wrong attempts with no correct,
    # and the most-recent attempt happened in the last 5 minutes.
    now = datetime.utcnow()
    STUCK_WRONG_THRESHOLD = 3
    STUCK_RECENT_MINUTES = 5
    stuck_pairs: dict = defaultdict(list)  # (sid, cp) -> list[AttemptEvent]
    for e in events:
        stuck_pairs[(e.session_id, e.checkpoint_id)].append(e)
    stuck_students: List[StuckStudent] = []
    for (sid, cp_id), evs in stuck_pairs.items():
        if any(e.is_correct for e in evs):
            continue
        wrong = len(evs)
        if wrong < STUCK_WRONG_THRESHOLD:
            continue
        last_at = max(e.created_at for e in evs)
        if (now - last_at).total_seconds() > STUCK_RECENT_MINUTES * 60:
            continue
        first_at = min(e.created_at for e in evs)
        stuck_students.append(StuckStudent(
            session_id=str(sid),
            display_name=session_id_to_name.get(sid, "(anonymous)"),
            checkpoint_id=cp_id,
            wrong_attempts=wrong,
            minutes_since_first_attempt=int((now - first_at).total_seconds() / 60),
            minutes_since_last_attempt=int((now - last_at).total_seconds() / 60),
        ))
    # Most-recently-stuck first
    stuck_students.sort(key=lambda s: s.minutes_since_last_attempt)

    # Build the "new since you last looked" summary if the client provided a timestamp.
    new_activity: Optional[NewActivitySummary] = None
    if since is not None:
        # Normalize to naive UTC — DB stores naive timestamps but the client sends ISO with `Z`.
        since_naive = since.replace(tzinfo=None) if since.tzinfo else since
        new_events = [e for e in events if e.created_at and e.created_at > since_naive]
        if new_events:
            by_student_counts: Counter = Counter()
            new_correct = 0
            for e in new_events:
                by_student_counts[session_id_to_name.get(e.session_id, "(anonymous)")] += 1
                if e.is_correct:
                    new_correct += 1
            top = by_student_counts.most_common(8)
            new_activity = NewActivitySummary(
                new_attempts=len(new_events),
                new_correct=new_correct,
                by_student=[NewActivityEntry(display_name=n, attempts=c) for n, c in top],
                since=since,
            )

    return LiveProgressResponse(
        lesson_id=lesson_id,
        lesson_name=lesson.name,
        join_code=lesson.join_code,
        active_sessions=len(session_ids),
        summary=summary,
        checkpoints=stats,
        student_roster=roster,
        scope_counts=scope_counts,
        new_activity=new_activity,
        stuck_students=stuck_students,
    )


# ---------------------------------------------------------------------------
# Retention enforcement: wipe sessions past their teacher-set retention.
#
# Triggered two ways:
#   1. On app startup (so a freshly-warmed instance does one sweep).
#   2. POST /admin/cleanup (called by Cloud Scheduler daily; protected by a
#      shared secret so it isn't world-callable). The startup sweep alone is
#      insufficient on Cloud Run with min-instances=0 — if no traffic, no
#      sweep happens. Cloud Scheduler ping covers that case.
# ---------------------------------------------------------------------------

import asyncio
from fastapi import Header
from database import SessionLocal

CLEANUP_SECRET = os.getenv("CLEANUP_SECRET")
# Used when a session points at a lesson/course that's been deleted — wipe
# under a conservative default rather than keeping forever.
_DEFAULT_RETENTION_DAYS = 90


_ACCESS_LOG_RETENTION_DAYS = 365  # design doc + ROPA: 12 months


def cleanup_expired_sessions_once() -> dict:
    """Wipe sessions past their teacher-set retention AND access log entries
    past their 12-month retention. Returns counts of each.

    Session retention is read from the parent Lesson or Course; last_seen_at
    is the reference point with a fallback to started_at for sessions that
    joined but never submitted.
    """
    db = SessionLocal()
    try:
        # Build retention maps so we don't query per session.
        lesson_retention = {
            str(lid): days for lid, days in
            db.query(Lesson.id, Lesson.session_retention_days).all()
        }
        course_retention = {
            str(cid): days for cid, days in
            db.query(Course.id, Course.session_retention_days).all()
        }

        now = datetime.utcnow()
        expired_ids = []
        for session in db.query(LessonSession).all():
            if session.course_id:
                days = course_retention.get(session.course_id, _DEFAULT_RETENTION_DAYS)
            elif session.lesson_id:
                days = lesson_retention.get(session.lesson_id, _DEFAULT_RETENTION_DAYS)
            else:
                days = _DEFAULT_RETENTION_DAYS
            reference = session.last_seen_at or session.started_at or now
            if reference + timedelta(days=days) < now:
                expired_ids.append(session.id)

        sessions_wiped = 0
        if expired_ids:
            db.query(AttemptEvent).filter(AttemptEvent.session_id.in_(expired_ids)).delete(synchronize_session=False)
            db.query(CodeSubmission).filter(CodeSubmission.session_id.in_(expired_ids)).delete(synchronize_session=False)
            db.query(SolutionReveal).filter(SolutionReveal.session_id.in_(expired_ids)).delete(synchronize_session=False)
            db.query(LessonSession).filter(LessonSession.id.in_(expired_ids)).delete(synchronize_session=False)
            sessions_wiped = len(expired_ids)

        # Purge access log entries past the 12-month retention.
        log_cutoff = now - timedelta(days=_ACCESS_LOG_RETENTION_DAYS)
        logs_wiped = db.query(AccessLog).filter(AccessLog.occurred_at < log_cutoff).delete(synchronize_session=False)

        # Hard-delete closed teacher accounts past the 30-day grace.
        # courses.teacher_id falls to NULL via ON DELETE SET NULL — the
        # courses remain accessible by their teacher_token (legacy path).
        teacher_cutoff = now - timedelta(days=30)
        teachers_wiped = (
            db.query(Teacher)
            .filter(Teacher.closed_at.isnot(None), Teacher.closed_at < teacher_cutoff)
            .delete(synchronize_session=False)
        )

        db.commit()
        return {
            "sessions": sessions_wiped,
            "access_log_entries": logs_wiped,
            "closed_teachers": teachers_wiped,
        }
    finally:
        db.close()


@app.on_event("startup")
async def _startup_cleanup_sweep():
    """One sweep on instance start — handles backlog after a long downtime."""
    try:
        result = await asyncio.to_thread(cleanup_expired_sessions_once)
        if any(result.values()):
            logging.getLogger("cadence").info("startup cleanup: %s", result)
    except Exception:
        logging.getLogger("cadence").exception("startup cleanup failed")


@app.post("/admin/cleanup")
async def admin_cleanup(authorization: Optional[str] = Header(None)):
    """Trigger a retention sweep. Cloud Scheduler should hit this daily with:
        Authorization: Bearer <CLEANUP_SECRET>

    Wipes sessions past their teacher-set retention AND access log entries
    past their 12-month retention.
    """
    if not CLEANUP_SECRET:
        raise HTTPException(503, "Cleanup is not configured (CLEANUP_SECRET unset)")
    if authorization != f"Bearer {CLEANUP_SECRET}":
        raise HTTPException(401, "Invalid cleanup credentials")
    return await asyncio.to_thread(cleanup_expired_sessions_once)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)