from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
from datetime import datetime

from database import get_db, engine
from models import Base, Problem, TestCase, Submission, TestResult, Teacher, GitHubRepo, StudentCommit, CommitTestResult
from schemas import (
    Problem as ProblemSchema, ProblemCreate, TestCase as TestCaseSchema,
    Submission as SubmissionSchema, SubmissionCreate, TestResult as TestResultSchema,
    SubmissionResponse, ProblemStats, SubmissionWithResults, Token, TeacherCreate, Teacher as TeacherSchema,
    GitHubRepo as GitHubRepoSchema, GitHubRepoCreate, StudentCommit as StudentCommitSchema,
    GitHubSyncRequest, GitHubSyncResponse, StudentCommitWithResults
)
from code_executor import CodeExecutor
from auth import create_access_token, get_current_teacher, verify_password, get_password_hash
from github_integration import GitHubIntegration

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Code Competition Platform", version="1.0.0")

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
    return {"message": "Code Competition Platform API"}

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 