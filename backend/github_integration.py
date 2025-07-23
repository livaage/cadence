import os
import json
import tempfile
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from github import Github, GithubException
import git
from sqlalchemy.orm import Session

from models import GitHubRepo, StudentCommit, CommitTestResult, TestCase, Problem
from code_executor import CodeExecutor

class GitHubIntegration:
    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.github_client = Github(self.github_token) if self.github_token else None
        self.code_executor = CodeExecutor()
    
    def create_repository(self, repo_name: str, description: str = "", is_private: bool = True) -> Dict:
        """Create a new GitHub repository for a problem"""
        if not self.github_client:
            raise Exception("GitHub token not configured")
        
        try:
            # Create repository
            repo = self.github_client.get_user().create_repo(
                name=repo_name,
                description=description,
                private=is_private,
                auto_init=True
            )
            
            # Create README with instructions
            readme_content = f"""# {repo_name}

## Instructions for Students

1. Clone this repository
2. Create a folder with your name (e.g., `students/john_doe/`)
3. Add your solution files in your folder
4. Commit and push your changes

## File Structure
```
students/
├── student1/
│   ├── solution.py
│   └── README.md
├── student2/
│   ├── solution.cpp
│   └── README.md
└── ...
```

## Supported Languages
- Python (.py files)
- C++ (.cpp files)

## Important Notes
- Make sure your solution reads from stdin and writes to stdout
- Test your code locally before pushing
- Each student should work in their own folder
"""
            
            repo.create_file(
                path="README.md",
                message="Initial commit: Add README with instructions",
                content=readme_content,
                branch="main"
            )
            
            # Create students directory
            repo.create_file(
                path="students/.gitkeep",
                message="Create students directory",
                content="",
                branch="main"
            )
            
            return {
                "success": True,
                "repo_url": repo.html_url,
                "repo_name": repo.name,
                "repo_owner": repo.owner.login
            }
            
        except GithubException as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def sync_repository(self, repo_id: str, db: Session, force_sync: bool = False) -> Dict:
        """Sync a GitHub repository and extract student commits"""
        repo = db.query(GitHubRepo).filter(GitHubRepo.id == repo_id).first()
        if not repo:
            return {"success": False, "error": "Repository not found"}
        
        try:
            # Get repository
            github_repo = self.github_client.get_repo(f"{repo.repo_owner}/{repo.repo_name}")
            
            # Get commits since last sync
            since_date = None
            if not force_sync and repo.last_sync:
                since_date = repo.last_sync
            
            commits = github_repo.get_commits(since=since_date)
            
            commits_found = 0
            commits_processed = 0
            
            for commit in commits:
                commits_found += 1
                
                # Skip if commit already processed
                existing_commit = db.query(StudentCommit).filter(
                    StudentCommit.github_repo_id == repo.id,
                    StudentCommit.commit_hash == commit.sha
                ).first()
                
                if existing_commit and not force_sync:
                    continue
                
                # Extract student information and code
                student_info = self._extract_student_info(commit, github_repo)
                if not student_info:
                    continue
                
                # Extract code content
                code_content = self._extract_code_content(commit, github_repo)
                if not code_content:
                    continue
                
                # Create or update student commit record
                if existing_commit:
                    student_commit = existing_commit
                else:
                    student_commit = StudentCommit(
                        github_repo_id=repo.id,
                        student_name=student_info["name"],
                        student_email=student_info.get("email"),
                        commit_hash=commit.sha,
                        commit_message=commit.commit.message,
                        commit_date=commit.commit.author.date,
                        files_changed=json.dumps([f.filename for f in commit.files]),
                        code_content=code_content["code"],
                        language=code_content["language"]
                    )
                    db.add(student_commit)
                    db.flush()  # Get the ID
                
                # Evaluate the code if not already evaluated
                if student_commit.status == "pending":
                    self._evaluate_commit(student_commit, db)
                
                commits_processed += 1
            
            # Update last sync time
            repo.last_sync = datetime.utcnow()
            db.commit()
            
            return {
                "success": True,
                "message": f"Synced {commits_processed} new commits",
                "commits_found": commits_found,
                "commits_processed": commits_processed
            }
            
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
    
    def _extract_student_info(self, commit, repo) -> Optional[Dict]:
        """Extract student information from commit"""
        try:
            # Try to get student name from commit author
            author_name = commit.commit.author.name
            author_email = commit.commit.author.email
            
            # Look for student folder in changed files
            student_folder = None
            for file in commit.files:
                if file.filename.startswith("students/"):
                    parts = file.filename.split("/")
                    if len(parts) >= 2:
                        student_folder = parts[1]
                        break
            
            if student_folder:
                return {
                    "name": student_folder.replace("_", " ").title(),
                    "email": author_email
                }
            elif author_name:
                return {
                    "name": author_name,
                    "email": author_email
                }
            
            return None
            
        except Exception:
            return None
    
    def _extract_code_content(self, commit, repo) -> Optional[Dict]:
        """Extract code content from commit"""
        try:
            # Look for solution files in the commit
            solution_files = []
            
            for file in commit.files:
                filename = file.filename.lower()
                if (filename.endswith('.py') or filename.endswith('.cpp') or 
                    filename.endswith('.c') or filename.endswith('.java')):
                    solution_files.append(file.filename)
            
            if not solution_files:
                return None
            
            # Get the content of the first solution file
            solution_file = solution_files[0]
            try:
                file_content = repo.get_contents(solution_file, ref=commit.sha)
                code = file_content.decoded_content.decode('utf-8')
                
                # Determine language
                if solution_file.endswith('.py'):
                    language = 'python'
                elif solution_file.endswith('.cpp') or solution_file.endswith('.c'):
                    language = 'cpp'
                elif solution_file.endswith('.java'):
                    language = 'java'
                else:
                    language = 'unknown'
                
                return {
                    "code": code,
                    "language": language,
                    "filename": solution_file
                }
                
            except Exception:
                return None
                
        except Exception:
            return None
    
    def _evaluate_commit(self, student_commit: StudentCommit, db: Session):
        """Evaluate a student commit against test cases"""
        try:
            # Get the problem and test cases
            github_repo = student_commit.github_repo
            problem = db.query(Problem).filter(Problem.id == github_repo.problem_id).first()
            test_cases = db.query(TestCase).filter(TestCase.problem_id == problem.id).all()
            
            if not test_cases:
                student_commit.status = "error"
                student_commit.error_message = "No test cases found for this problem"
                return
            
            total_score = 0
            total_points = 0
            max_execution_time = 0
            max_memory_usage = 0
            
            # Evaluate against each test case
            for test_case in test_cases:
                result = self.code_executor.execute_code(
                    student_commit.code_content,
                    student_commit.language,
                    test_case.input_data,
                    str(student_commit.id)
                )
                
                # Determine if test passed
                if result["status"] == "completed":
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
                test_result = CommitTestResult(
                    student_commit_id=student_commit.id,
                    test_case_id=test_case.id,
                    status=status,
                    actual_output=result["output"] if result["status"] == "completed" else None,
                    execution_time_ms=result["execution_time_ms"],
                    memory_usage_mb=result["memory_usage_mb"],
                    error_message=result["error"],
                    points_earned=points_earned
                )
                db.add(test_result)
            
            # Update commit with results
            student_commit.status = "evaluated"
            student_commit.total_score = total_score
            student_commit.total_points = total_points
            student_commit.execution_time_ms = max_execution_time
            student_commit.memory_usage_mb = max_memory_usage
            student_commit.evaluated_at = datetime.utcnow()
            
        except Exception as e:
            student_commit.status = "error"
            student_commit.error_message = str(e)
    
    def get_repository_stats(self, repo_id: str, db: Session) -> Dict:
        """Get statistics for a GitHub repository"""
        repo = db.query(GitHubRepo).filter(GitHubRepo.id == repo_id).first()
        if not repo:
            return {"error": "Repository not found"}
        
        commits = db.query(StudentCommit).filter(StudentCommit.github_repo_id == repo.id).all()
        
        total_commits = len(commits)
        evaluated_commits = len([c for c in commits if c.status == "evaluated"])
        error_commits = len([c for c in commits if c.status == "error"])
        
        if evaluated_commits > 0:
            average_score = sum(c.total_score for c in commits if c.status == "evaluated") / evaluated_commits
            average_time = sum(c.execution_time_ms or 0 for c in commits if c.status == "evaluated") / evaluated_commits
        else:
            average_score = 0
            average_time = 0
        
        return {
            "total_commits": total_commits,
            "evaluated_commits": evaluated_commits,
            "error_commits": error_commits,
            "average_score": average_score,
            "average_time_ms": average_time,
            "last_sync": repo.last_sync
        } 