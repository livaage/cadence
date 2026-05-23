"""
API client for Code Cadence

This module provides a Python client for interacting with the
Code Cadence API.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import requests
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)

@dataclass
class SubmissionResponse:
    """Response from a submission"""
    submission_id: str
    status: str
    message: str
    total_score: Optional[int] = None
    total_points: Optional[int] = None
    execution_time_ms: Optional[int] = None
    memory_usage_mb: Optional[int] = None
    error_message: Optional[str] = None

@dataclass
class Problem:
    """Problem information"""
    id: str
    title: str
    description: str
    difficulty: str
    time_limit: int
    memory_limit: int
    is_active: bool

class CadenceAPI:
    """Client for the Code Cadence API"""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        student_name: Optional[str] = None,
        student_email: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize the API client
        
        Args:
            base_url: API base URL (defaults to environment variable)
            student_name: Student name for submissions
            student_email: Student email for submissions
            timeout: Request timeout in seconds
        """
        # Defaults to the hosted Cadence API so pip-installed users Just Work.
        # Local devs override via CADENCE_API_URL=http://localhost:8000 (set in
        # the docker-compose env block for the dev backend).
        self.base_url = base_url or os.getenv("CADENCE_API_URL", "https://api.cadence-dash.com")
        self.student_name = student_name or os.getenv("CADENCE_STUDENT_NAME", "Anonymous")
        self.student_email = student_email or os.getenv("CADENCE_STUDENT_EMAIL")
        self.timeout = timeout
        self.session = requests.Session()

        # Add default headers
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": f"cadence-jupyter/{__import__('cadence').__version__}"
        })

        # Pick up a stored teacher JWT if there is one. Magic commands that
        # need authenticated endpoints (e.g. /courses/mine) rely on this.
        self._refresh_auth_from_store()
        
        # Validation hooks
        self.validation_hooks = []
        
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make an HTTP request to the API"""
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                timeout=self.timeout,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        except RequestException as e:
            # 404s are routinely used to probe ("is this code a lesson or a
            # course?") — don't shout in the notebook output. Higher-level
            # code re-raises if it actually wants to fail.
            status = getattr(getattr(e, "response", None), "status_code", None)
            if status == 404:
                logger.debug(f"API request returned 404: {endpoint}")
            else:
                logger.error(f"API request failed: {e}")
            raise
    
    def status(self) -> Dict[str, Any]:
        """Check API status"""
        try:
            return self._make_request("GET", "/")
        except Exception:
            return {"status": "error", "message": "API not available"}
    
    def get_problems(self) -> List[Problem]:
        """Get all available problems"""
        data = self._make_request("GET", "/problems")
        return [Problem(**problem) for problem in data]
    
    def get_problem(self, problem_id: str) -> Problem:
        """Get a specific problem"""
        data = self._make_request("GET", f"/problems/{problem_id}")
        return Problem(**data)
    
    def submit_solution(
        self,
        problem_id: str,
        source_code: str,
        language: str = "python"
    ) -> SubmissionResponse:
        """
        Submit a solution for evaluation
        
        Args:
            problem_id: ID of the problem to submit for
            source_code: Source code to submit
            language: Programming language (python, cpp)
            
        Returns:
            SubmissionResponse with results
        """
        # Run validation hooks
        for hook in self.validation_hooks:
            hook(source_code)
        
        # Prepare submission data
        submission_data = {
            "problem_id": problem_id,
            "student_name": self.student_name,
            "student_email": self.student_email,
            "language": language.lower(),
            "source_code": source_code
        }
        
        # Submit solution
        response_data = self._make_request("POST", "/submissions", submission_data)
        
        return SubmissionResponse(
            submission_id=response_data["submission_id"],
            status=response_data["status"],
            message=response_data["message"]
        )
    
    def get_submission(self, submission_id: str) -> SubmissionResponse:
        """Get submission results"""
        data = self._make_request("GET", f"/submissions/{submission_id}")
        
        return SubmissionResponse(
            submission_id=data["id"],
            status=data["status"],
            message="",
            total_score=data.get("total_score"),
            total_points=data.get("total_points"),
            execution_time_ms=data.get("execution_time_ms"),
            memory_usage_mb=data.get("memory_usage_mb"),
            error_message=data.get("error_message")
        )
    
    def wait_for_submission(self, submission_id: str, timeout: int = 60) -> SubmissionResponse:
        """Wait for submission to complete"""
        import time
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            submission = self.get_submission(submission_id)
            if submission.status in ["completed", "error"]:
                return submission
            time.sleep(1)
        
        raise TimeoutError(f"Submission {submission_id} did not complete within {timeout} seconds")
    
    def submit_notebook_cell(
        self,
        problem_id: str,
        cell_source: str,
        language: str = "python"
    ) -> SubmissionResponse:
        """
        Submit a notebook cell as a solution
        
        Args:
            problem_id: ID of the problem
            cell_source: Source code from the cell
            language: Programming language
            
        Returns:
            SubmissionResponse with results
        """
        # Clean up cell source (remove magic commands, etc.)
        cleaned_source = self._clean_cell_source(cell_source)
        
        return self.submit_solution(problem_id, cleaned_source, language)
    
    def _clean_cell_source(self, cell_source: str) -> str:
        """Clean up cell source code"""
        lines = cell_source.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Skip magic commands
            if line.strip().startswith('%') or line.strip().startswith('%%'):
                continue
            # Skip IPython magic
            if line.strip().startswith('!') and not line.strip().startswith('!='):
                continue
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()
    
    def register_validation_hook(self, hook):
        """Register a validation hook for submissions"""
        self.validation_hooks.append(hook)
    
    def batch_submit(
        self,
        submissions: List[tuple],
        wait_for_completion: bool = True
    ) -> List[SubmissionResponse]:
        """
        Submit multiple solutions
        
        Args:
            submissions: List of (problem_id, source_code, language) tuples
            wait_for_completion: Whether to wait for all submissions to complete
            
        Returns:
            List of SubmissionResponse objects
        """
        results = []
        
        for problem_id, source_code, language in submissions:
            try:
                response = self.submit_solution(problem_id, source_code, language)
                results.append(response)
                
                if wait_for_completion and response.status == "pending":
                    # Wait for completion
                    completed = self.wait_for_submission(response.submission_id)
                    results[-1] = completed
                    
            except Exception as e:
                logger.error(f"Failed to submit {problem_id}: {e}")
                results.append(SubmissionResponse(
                    submission_id="",
                    status="error",
                    message=str(e)
                ))
        
        return results
    
    def get_student_progress(self) -> Dict[str, Any]:
        """Get student's progress across all problems"""
        try:
            return self._make_request("GET", f"/students/{self.student_name}/progress")
        except Exception:
            return {"error": "Could not fetch progress"}
    
    # ------------------------------------------------------------------
    # Lesson progress (lesson / checkpoint / session / check)
    # ------------------------------------------------------------------

    def create_lesson(
        self,
        name: str,
        join_code: Optional[str] = None,
        teacher_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {"name": name}
        if join_code:
            body["join_code"] = join_code
        if teacher_token:
            body["teacher_token"] = teacher_token
        return self._make_request("POST", "/lessons", body)

    def get_lesson_by_token(self, teacher_token: str) -> Dict[str, Any]:
        return self._make_request("GET", f"/lessons/by-token/{teacher_token}")

    def get_lesson_by_code(self, join_code: str) -> Dict[str, Any]:
        return self._make_request("GET", f"/lessons/by-code/{join_code}")

    def rotate_lesson_token(
        self,
        teacher_token: str,
        rotate_join_code: bool = False,
    ) -> Dict[str, Any]:
        return self._make_request(
            "POST",
            f"/lessons/by-token/{teacher_token}/rotate",
            {"rotate_join_code": rotate_join_code},
        )

    def register_checkpoint(
        self,
        teacher_token: str,
        checkpoint_id: str,
        comparator: str,
        expected_payload: Optional[Dict[str, Any]],
        hint: Optional[str] = None,
        hint_after_attempts: int = 1,
        order_index: int = 0,
        reveal_after_attempts: Optional[int] = None,
        solution_value: Optional[str] = None,
        solution_code: Optional[str] = None,
        allow_submissions: bool = False,
    ) -> Dict[str, Any]:
        return self._make_request(
            "POST",
            f"/lessons/by-token/{teacher_token}/checkpoints",
            {
                "checkpoint_id": checkpoint_id,
                "comparator": comparator,
                # None for manual; JSON-encoded payload otherwise.
                "expected_payload": json.dumps(expected_payload) if expected_payload is not None else None,
                "hint": hint,
                "hint_after_attempts": hint_after_attempts,
                "order_index": order_index,
                "reveal_after_attempts": reveal_after_attempts,
                "solution_value": solution_value,
                "solution_code": solution_code,
                "allow_submissions": allow_submissions,
            },
        )

    def get_hint(self, session_id: str, checkpoint_id: str) -> Dict[str, Any]:
        return self._make_request(
            "GET",
            f"/sessions/{session_id}/checkpoints/{checkpoint_id}/hint",
        )

    def get_solution(self, session_id: str, checkpoint_id: str) -> Dict[str, Any]:
        return self._make_request(
            "GET",
            f"/sessions/{session_id}/checkpoints/{checkpoint_id}/solution",
        )

    def submit_code(
        self,
        session_id: str,
        checkpoint_id: str,
        code: Optional[str] = None,
        language: str = "python",
        image_data_b64: Optional[str] = None,
        image_mime: Optional[str] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "session_id": session_id,
            "checkpoint_id": checkpoint_id,
            "language": language,
        }
        if code is not None:
            body["code"] = code
        if image_data_b64 is not None:
            body["image_data_b64"] = image_data_b64
            body["image_mime"] = image_mime or "image/png"
        return self._make_request("POST", f"/sessions/{session_id}/submissions", body)

    def list_checkpoints(self, teacher_token: str) -> List[Dict[str, Any]]:
        return self._make_request("GET", f"/lessons/by-token/{teacher_token}/checkpoints")

    def start_session(self, join_code: str, display_name: str) -> Dict[str, Any]:
        return self._make_request(
            "POST",
            f"/lessons/by-code/{join_code}/sessions",
            {"display_name": display_name},
        )

    # ------------------------------------------------------------------
    # Courses (groupings of notebooks)
    # ------------------------------------------------------------------

    def create_course(
        self,
        name: str,
        join_code: Optional[str] = None,
        teacher_token: Optional[str] = None,
        session_retention_days: Optional[int] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {"name": name}
        if join_code:
            body["join_code"] = join_code
        if teacher_token:
            body["teacher_token"] = teacher_token
        if session_retention_days is not None:
            body["session_retention_days"] = session_retention_days
        return self._make_request("POST", "/courses", body)

    def get_course_by_token(self, teacher_token: str) -> Dict[str, Any]:
        return self._make_request("GET", f"/courses/by-token/{teacher_token}")

    def get_course_by_code(self, join_code: str) -> Dict[str, Any]:
        return self._make_request("GET", f"/courses/by-code/{join_code}")

    def rotate_course_token(
        self,
        teacher_token: str,
        rotate_join_code: bool = False,
    ) -> Dict[str, Any]:
        return self._make_request(
            "POST",
            f"/courses/by-token/{teacher_token}/rotate",
            {"rotate_join_code": rotate_join_code},
        )

    def add_notebook_to_course(
        self,
        course_teacher_token: str,
        lesson_teacher_token: str,
        order_index: int = 0,
    ) -> Dict[str, Any]:
        return self._make_request(
            "POST",
            f"/courses/by-token/{course_teacher_token}/notebooks",
            {"lesson_teacher_token": lesson_teacher_token, "order_index": order_index},
        )

    def detach_notebook_from_course(
        self,
        course_teacher_token: str,
        lesson_teacher_token: str,
    ) -> None:
        url = f"{self.base_url}/courses/by-token/{course_teacher_token}/notebooks"
        response = self.session.delete(
            url,
            params={"lesson_teacher_token": lesson_teacher_token},
            timeout=self.timeout,
        )
        response.raise_for_status()

    def delete_lesson(self, teacher_token: str) -> None:
        url = f"{self.base_url}/lessons/by-token/{teacher_token}"
        response = self.session.delete(url, timeout=self.timeout)
        if response.status_code != 404:
            response.raise_for_status()

    def delete_course(self, teacher_token: str) -> None:
        url = f"{self.base_url}/courses/by-token/{teacher_token}"
        response = self.session.delete(url, timeout=self.timeout)
        if response.status_code != 404:
            response.raise_for_status()

    def set_lesson_retention(self, teacher_token: str, days: int) -> Dict[str, Any]:
        return self._make_request(
            "PATCH",
            f"/lessons/by-token/{teacher_token}/retention",
            {"session_retention_days": days},
        )

    def set_course_retention(self, teacher_token: str, days: int) -> Dict[str, Any]:
        return self._make_request(
            "PATCH",
            f"/courses/by-token/{teacher_token}/retention",
            {"session_retention_days": days},
        )

    def clone_lesson(
        self,
        source_teacher_token: str,
        new_name: Optional[str] = None,
        new_join_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {"name": new_name or ""}
        if new_join_code:
            body["join_code"] = new_join_code
        return self._make_request(
            "POST",
            f"/lessons/by-token/{source_teacher_token}/clone",
            body,
        )

    def list_course_notebooks(self, course_teacher_token: str) -> List[Dict[str, Any]]:
        return self._make_request("GET", f"/courses/by-token/{course_teacher_token}/notebooks")

    def start_course_session(self, join_code: str, display_name: str) -> Dict[str, Any]:
        return self._make_request(
            "POST",
            f"/courses/by-code/{join_code}/sessions",
            {"display_name": display_name},
        )

    def set_current_notebook(
        self,
        session_id: str,
        *,
        lesson_id: Optional[str] = None,
        join_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {}
        if lesson_id:
            body["lesson_id"] = lesson_id
        if join_code:
            body["join_code"] = join_code
        return self._make_request("POST", f"/sessions/{session_id}/current-notebook", body)

    def check_answer(
        self,
        session_id: str,
        checkpoint_id: str,
        submitted_value: Any,
        elapsed_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Submit an answer for a checkpoint; returns {is_correct, attempt_num, hint}.

        If `elapsed_ms` is provided the attempt is counted toward the teacher's
        timing histogram.
        """
        body: Dict[str, Any] = {
            "session_id": session_id,
            "checkpoint_id": checkpoint_id,
            "submitted_value": json.dumps(submitted_value, default=str),
        }
        if elapsed_ms is not None:
            body["elapsed_ms"] = int(elapsed_ms)
        return self._make_request("POST", "/check", body)

    def sync_grade(self, assignment_name: str, student_id: str, score: float):
        """Sync grade with external grading system (for teachers)"""
        data = {
            "assignment_name": assignment_name,
            "student_id": student_id,
            "score": score
        }
        return self._make_request("POST", "/sync/grades", data)

    # ------------------------------------------------------------------
    # Teacher authentication (JWT)
    # ------------------------------------------------------------------

    def _refresh_auth_from_store(self) -> None:
        """Set or clear the Authorization header from creds_store."""
        from . import creds_store
        jwt = creds_store.get_jwt()
        if jwt:
            self.session.headers["Authorization"] = f"Bearer {jwt}"
        else:
            self.session.headers.pop("Authorization", None)

    def set_auth_token(self, jwt: str) -> None:
        self.session.headers["Authorization"] = f"Bearer {jwt}"

    def clear_auth_token(self) -> None:
        self.session.headers.pop("Authorization", None)

    def login(self, username: str, password: str) -> Dict[str, Any]:
        """POST /auth/login — returns {access_token, token_type}."""
        url = f"{self.base_url}/auth/login"
        # FastAPI's OAuth2PasswordRequestForm wants form data, not JSON.
        response = self.session.post(
            url,
            data={"username": username, "password": password},
            timeout=self.timeout,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        return response.json()

    def signup(self, username: str, email: str, password: str) -> Dict[str, Any]:
        return self._make_request("POST", "/auth/signup", {
            "username": username, "email": email, "password": password,
        })

    def whoami(self) -> Dict[str, Any]:
        return self._make_request("GET", "/auth/me")

    def list_my_courses(self) -> List[Dict[str, Any]]:
        return self._make_request("GET", "/courses/mine")

    # ------------------------------------------------------------------
    # Student rights (GDPR Articles 15, 17, 20)
    # ------------------------------------------------------------------

    def get_my_data(self, session_id: str) -> Dict[str, Any]:
        """Right of access (Article 15) and portability (Article 20)."""
        return self._make_request("GET", f"/sessions/{session_id}/my-data")

    def delete_my_data(self, session_id: str) -> None:
        """Right to erasure (Article 17). Wipes the session and everything
        referencing it. Idempotent — a 404 means it's already gone."""
        url = f"{self.base_url}/sessions/{session_id}"
        response = self.session.delete(url, timeout=self.timeout)
        if response.status_code != 404:
            response.raise_for_status()
