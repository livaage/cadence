import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || '';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests if available
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export interface Problem {
  id: string;
  title: string;
  description: string;
  difficulty: string;
  time_limit: number;
  memory_limit: number;
  created_at: string;
  updated_at: string;
  is_active: boolean;
}

export interface Submission {
  id: string;
  problem_id: string;
  student_name: string;
  student_email?: string;
  language: string;
  source_code: string;
  status: string;
  total_score: number;
  total_points: number;
  execution_time_ms?: number;
  memory_usage_mb?: number;
  error_message?: string;
  created_at: string;
  completed_at?: string;
}

export interface TestResult {
  id: string;
  submission_id: string;
  test_case_id: string;
  status: string;
  actual_output?: string;
  execution_time_ms?: number;
  memory_usage_mb?: number;
  error_message?: string;
  points_earned: number;
  created_at: string;
}

export interface ProblemStats {
  problem_id: string;
  problem_title: string;
  total_submissions: number;
  correct_submissions: number;
  average_score: number;
  average_time_ms: number;
  average_memory_mb: number;
}

export interface SubmissionWithResults {
  submission: Submission;
  test_results: TestResult[];
  problem: Problem;
}

export interface GitHubRepo {
  id: string;
  problem_id: string;
  repo_name: string;
  repo_url: string;
  repo_owner: string;
  branch: string;
  folder_structure?: string;
  last_sync?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface StudentCommit {
  id: string;
  github_repo_id: string;
  student_name: string;
  student_email?: string;
  commit_hash: string;
  commit_message: string;
  commit_date: string;
  files_changed?: string;
  code_content?: string;
  language?: string;
  status: string;
  total_score: number;
  total_points: number;
  execution_time_ms?: number;
  memory_usage_mb?: number;
  error_message?: string;
  evaluated_at?: string;
  created_at: string;
}

export interface CommitTestResult {
  id: string;
  student_commit_id: string;
  test_case_id: string;
  status: string;
  actual_output?: string;
  execution_time_ms?: number;
  memory_usage_mb?: number;
  error_message?: string;
  points_earned: number;
  created_at: string;
}

export interface StudentCommitWithResults {
  student_commit: StudentCommit;
  commit_test_results: CommitTestResult[];
  github_repo: GitHubRepo;
  problem: Problem;
}

export interface GitHubSyncResponse {
  success: boolean;
  message: string;
  commits_found: number;
  commits_processed: number;
}

export interface GitHubRepoStats {
  total_commits: number;
  evaluated_commits: number;
  error_commits: number;
  average_score: number;
  average_time_ms: number;
  last_sync?: string;
}

// Public API calls
export const getProblems = async (): Promise<Problem[]> => {
  const response = await api.get('/problems');
  return response.data;
};

export const getProblem = async (problemId: string): Promise<Problem> => {
  const response = await api.get(`/problems/${problemId}`);
  return response.data;
};

export const createSubmission = async (submission: {
  problem_id: string;
  student_name: string;
  student_email?: string;
  language: string;
  source_code: string;
}): Promise<{ submission_id: string; status: string; message: string }> => {
  const response = await api.post('/submissions', submission);
  return response.data;
};

export const getSubmission = async (submissionId: string): Promise<Submission> => {
  const response = await api.get(`/submissions/${submissionId}`);
  return response.data;
};

// Teacher auth
export interface TeacherProfile {
  id: string;
  username: string;
  email: string;
  is_active: boolean;
  created_at: string;
  // True if the teacher has a local password set (i.e. can log in via
  // username + password from Jupyter). False for OAuth-only accounts.
  has_password: boolean;
}

export const setMyPassword = async (
  newPassword: string,
  currentPassword: string | null,
): Promise<void> => {
  await api.post('/auth/me/password', {
    new_password: newPassword,
    current_password: currentPassword,
  });
};

export const loginTeacher = async (username: string, password: string): Promise<{ access_token: string; token_type: string }> => {
  const formData = new FormData();
  formData.append('username', username);
  formData.append('password', password);
  const response = await api.post('/auth/login', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const signupTeacher = async (
  username: string,
  email: string,
  password: string,
): Promise<{ access_token: string; token_type: string }> => {
  const response = await api.post('/auth/signup', { username, email, password });
  return response.data;
};

export const whoami = async (): Promise<TeacherProfile> => {
  const response = await api.get('/auth/me');
  return response.data;
};

export const closeMyAccount = async (): Promise<void> => {
  await api.delete('/auth/me');
};

export const deleteEverything = async (): Promise<void> => {
  // Hard-delete: teacher row + every lesson, course, session, attempt,
  // submission, and solution-reveal owned by this teacher. Irreversible —
  // no grace period (cf. closeMyAccount, which is recoverable for 30 days).
  await api.post('/auth/me/delete-everything');
};

export const listMyCourses = async (): Promise<CourseSummaryEntry[]> => {
  const response = await api.get('/courses/mine');
  return response.data;
};

export const listMyLessons = async (): Promise<LessonSummary[]> => {
  const response = await api.get('/lessons/mine');
  return response.data;
};

// GitHub OAuth: navigate the user here. Backend redirects to GitHub and then
// back to /teacher/auth-callback#token=<jwt> after the user authorizes.
export const githubAuthorizeUrl = (): string => {
  const base = API_BASE_URL || '';
  return `${base}/auth/github/authorize`;
};

export interface AuthProviders {
  github: boolean;
  google: boolean;
}

export const getAuthProviders = async (): Promise<AuthProviders> => {
  const response = await api.get('/auth/providers');
  return response.data;
};

export const getProblemsTeacher = async (): Promise<Problem[]> => {
  const response = await api.get('/teacher/problems');
  return response.data;
};

export const createProblem = async (problem: {
  title: string;
  description: string;
  difficulty?: string;
  time_limit?: number;
  memory_limit?: number;
}): Promise<Problem> => {
  const response = await api.post('/teacher/problems', problem);
  return response.data;
};

export const getSubmissionsTeacher = async (problemId?: string): Promise<Submission[]> => {
  const params = problemId ? { problem_id: problemId } : {};
  const response = await api.get('/teacher/submissions', { params });
  return response.data;
};

export const getSubmissionTeacher = async (submissionId: string): Promise<SubmissionWithResults> => {
  const response = await api.get(`/teacher/submissions/${submissionId}`);
  return response.data;
};

export const getProblemStats = async (): Promise<ProblemStats[]> => {
  const response = await api.get('/teacher/stats');
  return response.data;
};

// GitHub Integration API calls
export const createGitHubRepo = async (repoData: {
  problem_id: string;
  branch?: string;
  folder_structure?: string;
}): Promise<GitHubRepo> => {
  const response = await api.post('/teacher/github/repos', repoData);
  return response.data;
};

export const getGitHubRepos = async (problemId?: string): Promise<GitHubRepo[]> => {
  const params = problemId ? { problem_id: problemId } : {};
  const response = await api.get('/teacher/github/repos', { params });
  return response.data;
};

export const syncGitHubRepo = async (repoId: string, forceSync: boolean = false): Promise<GitHubSyncResponse> => {
  const response = await api.post('/teacher/github/sync', {
    repo_id: repoId,
    force_sync: forceSync
  });
  return response.data;
};

export const getGitHubCommits = async (repoId: string): Promise<StudentCommit[]> => {
  const response = await api.get(`/teacher/github/repos/${repoId}/commits`);
  return response.data;
};

export const getGitHubCommitDetails = async (repoId: string, commitId: string): Promise<StudentCommitWithResults> => {
  const response = await api.get(`/teacher/github/repos/${repoId}/commits/${commitId}`);
  return response.data;
};

export const getGitHubRepoStats = async (repoId: string): Promise<GitHubRepoStats> => {
  const response = await api.get(`/teacher/github/repos/${repoId}/stats`);
  return response.data;
};

// Lesson progress (live dashboard)
export interface TimingSample {
  display_name: string;
  elapsed_ms: number;
}

export interface CheckpointLiveStats {
  checkpoint_id: string;
  order_index: number;
  comparator: 'exact' | 'numeric' | 'set' | 'regex' | 'manual';
  attempted: number;
  solved: number;
  total_attempts: number;
  attempts_histogram: { '1': number; '2': number; '3+': number; unsolved: number };
  common_wrong: Array<{ value: string; count: number; student_names: string[] }>;
  timing_histogram: Record<string, number>;
  timing_samples: number;
  timing_samples_detail: TimingSample[];
  avg_attempts: number | null;
  has_hint: boolean;
  hint_after_attempts: number;
  reveal_after_attempts: number | null;
  has_solution: boolean;
  solution_views: number;
  allow_submissions: boolean;
  submission_count: number;
}

export interface StudentCheckpointDetail {
  checkpoint_id: string;
  status: 'solved' | 'attempted' | 'untouched';
  attempts: number;
  first_correct_attempt: number | null;
  elapsed_ms_first_correct: number | null;
}

export interface AttemptLogEntry {
  checkpoint_id: string;
  attempt_num: number;
  is_correct: boolean;
  submitted_value: string | null;
  elapsed_ms: number | null;
  created_at: string;
}

export interface StudentRosterEntry {
  session_id: string;
  display_name: string;
  last_seen_at: string;
  total_attempts: number;
  checkpoints_solved: number;
  checkpoints_attempted: number;
  fastest_elapsed_ms: number | null;
  current_checkpoint_id: string | null;
  per_checkpoint: StudentCheckpointDetail[];
  chronology: AttemptLogEntry[];
}

export interface LessonSummaryStats {
  total_sessions: number;
  total_checkpoints: number;
  total_attempts: number;
  total_solved_pairs: number;
  possible_pairs: number;
  solve_rate_pct: number;
  completion_histogram: Record<string, number>;
  top_wrong_overall: Array<{ checkpoint_id: string; value: string; count: number; student_names: string[] }>;
  // checkpoint_id -> count of students whose current frontier is that checkpoint.
  // Plus a synthetic "done" key for students who finished the last checkpoint.
  frontier_histogram: Record<string, number>;
}

export interface NewActivitySummary {
  new_attempts: number;
  new_correct: number;
  by_student: Array<{ display_name: string; attempts: number }>;
  since: string | null;
}

export interface LiveProgress {
  lesson_id: string;
  lesson_name: string;
  join_code: string;
  session_retention_days: number;
  active_sessions: number;
  summary: LessonSummaryStats;
  checkpoints: CheckpointLiveStats[];
  student_roster: StudentRosterEntry[];
  scope_counts: { standalone: number; course: number | null; alltime: number };
  new_activity: NewActivitySummary | null;
  stuck_students: StuckStudent[];
}

export interface LessonHeartbeat {
  lesson_id: string;
  last_attempt_at: string | null;
  last_session_at: string | null;
  total_attempts: number;
  total_sessions: number;
}

export const getLessonHeartbeat = async (
  teacherToken: string,
  scope: LiveScope = 'current',
  courseToken?: string,
): Promise<LessonHeartbeat> => {
  const params: Record<string, string> = { scope };
  if (courseToken) params.course_token = courseToken;
  const response = await api.get(
    `/lessons/by-token/${encodeURIComponent(teacherToken)}/heartbeat`,
    { params },
  );
  return response.data;
};

export interface LessonSummary {
  id: string;
  name: string;
  join_code: string;
  teacher_token: string;
  created_at: string;
}

export const rotateLessonToken = async (
  teacherToken: string,
  rotateJoinCode = false,
): Promise<LessonSummary> => {
  const response = await api.post(
    `/lessons/by-token/${encodeURIComponent(teacherToken)}/rotate`,
    { rotate_join_code: rotateJoinCode },
  );
  return response.data;
};

export const getLessonSummary = async (teacherToken: string): Promise<LessonSummary> => {
  const response = await api.get(`/lessons/by-token/${encodeURIComponent(teacherToken)}`);
  return response.data;
};

export const deleteLesson = async (teacherToken: string): Promise<void> => {
  await api.delete(`/lessons/by-token/${encodeURIComponent(teacherToken)}`);
};

export const deleteSession = async (sessionId: string): Promise<void> => {
  await api.delete(`/sessions/${encodeURIComponent(sessionId)}`);
};

export interface CourseSummaryEntry {
  id: string;
  name: string;
  join_code: string;
  teacher_token: string;
  created_at: string;
}

export const getCourseSummary = async (teacherToken: string): Promise<CourseSummaryEntry> => {
  const response = await api.get(`/courses/by-token/${encodeURIComponent(teacherToken)}`);
  return response.data;
};

/**
 * Probe a teacher_token to find out whether it's a course or a lesson.
 * Tries the cheap lesson endpoint first; on 404, tries the course endpoint.
 * Throws if neither matches (invalid token).
 */
export async function resolveToken(teacherToken: string): Promise<
  | { kind: 'lesson'; name: string; join_code: string }
  | { kind: 'course'; name: string; join_code: string }
> {
  try {
    const lesson = await getLessonSummary(teacherToken);
    return { kind: 'lesson', name: lesson.name, join_code: lesson.join_code };
  } catch (e: any) {
    if (e?.response?.status !== 404) throw e;
  }
  const course = await getCourseSummary(teacherToken);
  return { kind: 'course', name: course.name, join_code: course.join_code };
}

export type LiveScope = 'current' | 'course' | 'alltime';

export interface CodeSubmissionEntry {
  id: string;
  checkpoint_id: string;
  code: string | null;
  language: string;
  submitted_at: string;
  display_name: string | null;
  image_data_b64: string | null;
  image_mime: string | null;
}

export interface StuckStudent {
  session_id: string;
  display_name: string;
  checkpoint_id: string;
  wrong_attempts: number;
  minutes_since_first_attempt: number;
  minutes_since_last_attempt: number;
}

export const getCheckpointSubmissions = async (
  teacherToken: string,
  checkpointId: string,
): Promise<CodeSubmissionEntry[]> => {
  const response = await api.get(
    `/lessons/by-token/${encodeURIComponent(teacherToken)}/checkpoints/${encodeURIComponent(checkpointId)}/submissions`,
  );
  return response.data;
};

export const getLiveProgress = async (
  teacherToken: string,
  scope: LiveScope = 'current',
  courseToken?: string,
  since?: string,
): Promise<LiveProgress> => {
  const params: Record<string, string> = { scope };
  if (courseToken) params.course_token = courseToken;
  if (since) params.since = since;
  const response = await api.get(
    `/lessons/by-token/${encodeURIComponent(teacherToken)}/live`,
    { params },
  );
  return response.data;
};

// Courses
export interface CourseNotebookStat {
  lesson_id: string;
  name: string;
  order_index: number;
  students_here_now: number;
  total_attempts: number;
  solved_rate_pct: number;
  avg_attempts: number | null;
}

export interface CourseLive {
  course_id: string;
  course_name: string;
  join_code: string;
  session_retention_days: number;
  total_enrollments: number;
  not_started: number;
  notebooks: CourseNotebookStat[];
  overall_completion_histogram: Record<string, number>;
}

export const getCourseLive = async (courseTeacherToken: string): Promise<CourseLive> => {
  const response = await api.get(`/courses/by-token/${encodeURIComponent(courseTeacherToken)}/live`);
  return response.data;
};

export interface CourseNotebookRef {
  id: string;
  name: string;
  join_code: string;
  teacher_token: string;
  order_index: number;
}

export const listCourseNotebooks = async (
  courseTeacherToken: string,
): Promise<CourseNotebookRef[]> => {
  const response = await api.get(`/courses/by-token/${encodeURIComponent(courseTeacherToken)}/notebooks`);
  return response.data;
};

export const detachNotebookFromCourse = async (
  courseTeacherToken: string,
  lessonTeacherToken: string,
): Promise<void> => {
  await api.delete(`/courses/by-token/${encodeURIComponent(courseTeacherToken)}/notebooks`, {
    params: { lesson_teacher_token: lessonTeacherToken },
  });
};

export const deleteLessonByToken = async (lessonTeacherToken: string): Promise<void> => {
  await api.delete(`/lessons/by-token/${encodeURIComponent(lessonTeacherToken)}`);
};

/**
 * Format an axios error into a user-readable message.
 *
 * Handles the four common shapes:
 *   1. Network error / no response (backend down, CORS blocked) — say so.
 *   2. FastAPI explicit HTTPException — `detail` is a string, use it.
 *   3. FastAPI validation 422 — `detail` is an array of {loc, msg, type}.
 *      Format as `field: msg; field: msg`.
 *   4. Anything else — fall back to the supplied default with status.
 */
export function formatApiError(err: any, fallback: string): string {
  if (!err) return fallback;

  if (!err.response) {
    return `Could not reach the server (${err.message || 'network error'}). ` +
           'Check the backend is running and reachable.';
  }

  const status = err.response.status;
  const detail = err.response.data?.detail;

  if (typeof detail === 'string') return detail;

  if (Array.isArray(detail)) {
    return detail
      .map((e: any) => {
        const field = Array.isArray(e.loc) && e.loc.length > 0
          ? e.loc[e.loc.length - 1]
          : 'field';
        return `${field}: ${e.msg}`;
      })
      .join('; ');
  }

  if (status) return `${fallback} (HTTP ${status})`;
  return fallback;
}

export default api;
