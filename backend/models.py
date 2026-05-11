from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

class Problem(Base):
    __tablename__ = "problems"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    difficulty = Column(String(50), nullable=True)
    time_limit = Column(Integer, default=30)
    memory_limit = Column(Integer, default=512)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    test_cases = relationship("TestCase", back_populates="problem", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="problem")
    github_repos = relationship("GitHubRepo", back_populates="problem")

class TestCase(Base):
    __tablename__ = "test_cases"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    problem_id = Column(UUID(as_uuid=True), ForeignKey("problems.id"), nullable=False)
    input_data = Column(Text, nullable=False)
    expected_output = Column(Text, nullable=False)
    is_hidden = Column(Boolean, default=False)
    points = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    problem = relationship("Problem", back_populates="test_cases")
    test_results = relationship("TestResult", back_populates="test_case")

class Submission(Base):
    __tablename__ = "submissions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    problem_id = Column(UUID(as_uuid=True), ForeignKey("problems.id"), nullable=False)
    student_name = Column(String(255), nullable=False)
    student_email = Column(String(255), nullable=True)
    language = Column(String(20), nullable=False)
    source_code = Column(Text, nullable=False)
    status = Column(String(50), default="pending")
    total_score = Column(Integer, default=0)
    total_points = Column(Integer, default=0)
    execution_time_ms = Column(Integer, nullable=True)
    memory_usage_mb = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    problem = relationship("Problem", back_populates="submissions")
    test_results = relationship("TestResult", back_populates="submission")

class TestResult(Base):
    __tablename__ = "test_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id = Column(UUID(as_uuid=True), ForeignKey("submissions.id"), nullable=False)
    test_case_id = Column(UUID(as_uuid=True), ForeignKey("test_cases.id"), nullable=False)
    status = Column(String(50), nullable=False)
    actual_output = Column(Text, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    memory_usage_mb = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    points_earned = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    submission = relationship("Submission", back_populates="test_results")
    test_case = relationship("TestCase", back_populates="test_results")

class Teacher(Base):
    __tablename__ = "teachers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class GitHubRepo(Base):
    __tablename__ = "github_repos"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    problem_id = Column(UUID(as_uuid=True), ForeignKey("problems.id"), nullable=False)
    repo_name = Column(String(255), nullable=False)
    repo_url = Column(String(500), nullable=False)
    repo_owner = Column(String(255), nullable=False)
    access_token = Column(String(500), nullable=True)  # Encrypted GitHub token
    branch = Column(String(100), default="main")
    folder_structure = Column(Text, nullable=True)  # JSON structure for student folders
    last_sync = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    problem = relationship("Problem", back_populates="github_repos")
    student_commits = relationship("StudentCommit", back_populates="github_repo")

class StudentCommit(Base):
    __tablename__ = "student_commits"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    github_repo_id = Column(UUID(as_uuid=True), ForeignKey("github_repos.id"), nullable=False)
    student_name = Column(String(255), nullable=False)
    student_email = Column(String(255), nullable=True)
    commit_hash = Column(String(100), nullable=False)
    commit_message = Column(Text, nullable=False)
    commit_date = Column(DateTime, nullable=False)
    files_changed = Column(Text, nullable=True)  # JSON list of changed files
    code_content = Column(Text, nullable=True)  # Main solution code
    language = Column(String(20), nullable=True)
    status = Column(String(50), default="pending")  # pending, evaluated, error
    total_score = Column(Integer, default=0)
    total_points = Column(Integer, default=0)
    execution_time_ms = Column(Integer, nullable=True)
    memory_usage_mb = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    evaluated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    github_repo = relationship("GitHubRepo", back_populates="student_commits")
    commit_test_results = relationship("CommitTestResult", back_populates="student_commit")

class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    join_code = Column(String(64), nullable=False, unique=True, index=True)
    teacher_token = Column(String(128), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Course(Base):
    __tablename__ = "courses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    join_code = Column(String(64), nullable=False, unique=True, index=True)
    teacher_token = Column(String(128), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class CourseNotebook(Base):
    """Many-to-many join: a notebook (Lesson) can belong to multiple courses.
    Needed because the all-time stats view aggregates across every course a
    notebook has appeared in."""
    __tablename__ = "course_notebooks"

    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), primary_key=True)
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("lessons.id"), primary_key=True)
    order_index = Column(Integer, default=0)
    added_at = Column(DateTime, default=datetime.utcnow)


class Checkpoint(Base):
    __tablename__ = "checkpoints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lesson_id = Column(String(255), nullable=False, index=True)
    checkpoint_id = Column(String(255), nullable=False)
    comparator = Column(String(50), nullable=False)
    expected_payload = Column(Text, nullable=False)
    hint = Column(Text, nullable=True)
    order_index = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("comparator IN ('exact', 'numeric', 'set', 'regex')", name="ck_checkpoint_comparator"),
    )


class LessonSession(Base):
    __tablename__ = "lesson_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # For standalone notebooks: the lesson the student joined directly.
    # For course enrollments: the notebook they most recently switched to
    # via `%competition_notebook`; nullable until they pick one.
    lesson_id = Column(String(255), nullable=True, index=True)
    course_id = Column(String(255), nullable=True, index=True)
    display_name = Column(String(255), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.utcnow)


class AttemptEvent(Base):
    __tablename__ = "attempt_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("lesson_sessions.id"), nullable=False, index=True)
    lesson_id = Column(String(255), nullable=False, index=True)
    checkpoint_id = Column(String(255), nullable=False, index=True)
    attempt_num = Column(Integer, nullable=False)
    submitted_value = Column(Text, nullable=True)
    is_correct = Column(Boolean, nullable=False)
    elapsed_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class CommitTestResult(Base):
    __tablename__ = "commit_test_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_commit_id = Column(UUID(as_uuid=True), ForeignKey("student_commits.id"), nullable=False)
    test_case_id = Column(UUID(as_uuid=True), ForeignKey("test_cases.id"), nullable=False)
    status = Column(String(50), nullable=False)
    actual_output = Column(Text, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    memory_usage_mb = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    points_earned = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    student_commit = relationship("StudentCommit", back_populates="commit_test_results")
    test_case = relationship("TestCase") 