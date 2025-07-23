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

// Teacher API calls
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

export default api; 