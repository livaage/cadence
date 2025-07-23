import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Grid,
  Chip,
  CircularProgress,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Tooltip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import {
  GitHub,
  Sync,
  Visibility,
  Add,
  ExpandMore,
  Code,
  Timer,
  Memory,
  CheckCircle,
  Error,
  Schedule,
  Refresh,
  OpenInNew,
  Help,
} from '@mui/icons-material';
import {
  createGitHubRepo,
  getGitHubRepos,
  syncGitHubRepo,
  getGitHubCommits,
  getGitHubCommitDetails,
  getGitHubRepoStats,
  getProblemsTeacher,
  GitHubRepo,
  StudentCommit,
  StudentCommitWithResults,
  GitHubRepoStats,
  Problem,
} from '../services/api';

const GitHubIntegration: React.FC = () => {
  const [repos, setRepos] = useState<GitHubRepo[]>([]);
  const [problems, setProblems] = useState<Problem[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<GitHubRepo | null>(null);
  const [commits, setCommits] = useState<StudentCommit[]>([]);
  const [selectedCommit, setSelectedCommit] = useState<StudentCommitWithResults | null>(null);
  const [repoStats, setRepoStats] = useState<GitHubRepoStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Dialog states
  const [createRepoDialog, setCreateRepoDialog] = useState(false);
  const [commitDetailsDialog, setCommitDetailsDialog] = useState(false);
  const [newRepoData, setNewRepoData] = useState({
    problem_id: '',
    branch: 'main',
    folder_structure: '',
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [reposData, problemsData] = await Promise.all([
        getGitHubRepos(),
        getProblemsTeacher(),
      ]);
      setRepos(reposData);
      setProblems(problemsData);
    } catch (err) {
      setError('Failed to load GitHub repositories');
      console.error('Error fetching data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateRepo = async () => {
    if (!newRepoData.problem_id) {
      setError('Please select a problem');
      return;
    }

    try {
      const repo = await createGitHubRepo(newRepoData);
      setRepos([repo, ...repos]);
      setCreateRepoDialog(false);
      setNewRepoData({ problem_id: '', branch: 'main', folder_structure: '' });
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create repository');
    }
  };

  const handleSyncRepo = async (repoId: string, forceSync: boolean = false) => {
    setSyncing(true);
    try {
      const result = await syncGitHubRepo(repoId, forceSync);
      if (result.success) {
        // Refresh commits if this repo is selected
        if (selectedRepo && selectedRepo.id === repoId) {
          const commitsData = await getGitHubCommits(repoId);
          setCommits(commitsData);
        }
        // Refresh stats
        if (selectedRepo && selectedRepo.id === repoId) {
          const stats = await getGitHubRepoStats(repoId);
          setRepoStats(stats);
        }
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to sync repository');
    } finally {
      setSyncing(false);
    }
  };

  const handleSelectRepo = async (repo: GitHubRepo) => {
    setSelectedRepo(repo);
    try {
      const [commitsData, stats] = await Promise.all([
        getGitHubCommits(repo.id),
        getGitHubRepoStats(repo.id),
      ]);
      setCommits(commitsData);
      setRepoStats(stats);
    } catch (err) {
      setError('Failed to load repository data');
    }
  };

  const handleViewCommit = async (commit: StudentCommit) => {
    try {
      const details = await getGitHubCommitDetails(selectedRepo!.id, commit.id);
      setSelectedCommit(details);
      setCommitDetailsDialog(true);
    } catch (err) {
      setError('Failed to load commit details');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'evaluated':
        return 'success';
      case 'error':
        return 'error';
      case 'pending':
        return 'info';
      default:
        return 'default';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'evaluated':
        return <CheckCircle />;
      case 'error':
        return <Error />;
      case 'pending':
        return <Schedule />;
      default:
        return <Help />;
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          GitHub Integration
        </Typography>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={() => setCreateRepoDialog(true)}
        >
          Create Repository
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Repository List */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Repositories
              </Typography>
              
              {repos.length === 0 ? (
                <Typography color="text.secondary">
                  No repositories created yet.
                </Typography>
              ) : (
                <Box>
                  {repos.map((repo) => {
                    const problem = problems.find(p => p.id === repo.problem_id);
                    return (
                      <Card
                        key={repo.id}
                        sx={{
                          mb: 2,
                          cursor: 'pointer',
                          border: selectedRepo?.id === repo.id ? 2 : 1,
                          borderColor: selectedRepo?.id === repo.id ? 'primary.main' : 'divider',
                        }}
                        onClick={() => handleSelectRepo(repo)}
                      >
                        <CardContent>
                          <Typography variant="subtitle1" gutterBottom>
                            {problem?.title || 'Unknown Problem'}
                          </Typography>
                          <Typography variant="body2" color="text.secondary" gutterBottom>
                            {repo.repo_name}
                          </Typography>
                          <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
                            <Chip
                              icon={<GitHub />}
                              label="GitHub"
                              size="small"
                              variant="outlined"
                            />
                            <Chip
                              label={repo.branch}
                              size="small"
                              variant="outlined"
                            />
                          </Box>
                          <Typography variant="caption" color="text.secondary">
                            Last sync: {repo.last_sync ? new Date(repo.last_sync).toLocaleString() : 'Never'}
                          </Typography>
                        </CardContent>
                      </Card>
                    );
                  })}
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Repository Details and Commits */}
        <Grid item xs={12} md={8}>
          {selectedRepo ? (
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                  <Typography variant="h6">
                    {problems.find(p => p.id === selectedRepo.problem_id)?.title} - Commits
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    <Button
                      variant="outlined"
                      startIcon={<OpenInNew />}
                      onClick={() => window.open(selectedRepo.repo_url, '_blank')}
                    >
                      View on GitHub
                    </Button>
                    <Button
                      variant="contained"
                      startIcon={syncing ? <CircularProgress size={20} /> : <Sync />}
                      onClick={() => handleSyncRepo(selectedRepo.id)}
                      disabled={syncing}
                    >
                      {syncing ? 'Syncing...' : 'Sync'}
                    </Button>
                  </Box>
                </Box>

                {/* Repository Stats */}
                {repoStats && (
                  <Paper sx={{ p: 2, mb: 3, bgcolor: 'grey.50' }}>
                    <Grid container spacing={2}>
                      <Grid item xs={3}>
                        <Typography variant="h6">{repoStats.total_commits}</Typography>
                        <Typography variant="caption">Total Commits</Typography>
                      </Grid>
                      <Grid item xs={3}>
                        <Typography variant="h6">{repoStats.evaluated_commits}</Typography>
                        <Typography variant="caption">Evaluated</Typography>
                      </Grid>
                      <Grid item xs={3}>
                        <Typography variant="h6">{repoStats.average_score.toFixed(1)}</Typography>
                        <Typography variant="caption">Avg Score</Typography>
                      </Grid>
                      <Grid item xs={3}>
                        <Typography variant="h6">{Math.round(repoStats.average_time_ms)}ms</Typography>
                        <Typography variant="caption">Avg Time</Typography>
                      </Grid>
                    </Grid>
                  </Paper>
                )}

                {/* Commits Table */}
                <TableContainer component={Paper}>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Student</TableCell>
                        <TableCell>Commit Message</TableCell>
                        <TableCell>Language</TableCell>
                        <TableCell>Status</TableCell>
                        <TableCell>Score</TableCell>
                        <TableCell>Date</TableCell>
                        <TableCell>Actions</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {commits.map((commit) => (
                        <TableRow key={commit.id}>
                          <TableCell>{commit.student_name}</TableCell>
                          <TableCell>
                            <Typography variant="body2" noWrap sx={{ maxWidth: 200 }}>
                              {commit.commit_message}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Chip label={commit.language?.toUpperCase() || 'N/A'} size="small" />
                          </TableCell>
                          <TableCell>
                            <Chip
                              icon={getStatusIcon(commit.status)}
                              label={commit.status}
                              color={getStatusColor(commit.status) as any}
                              size="small"
                            />
                          </TableCell>
                          <TableCell>
                            {commit.total_score}/{commit.total_points}
                          </TableCell>
                          <TableCell>
                            {new Date(commit.commit_date).toLocaleString()}
                          </TableCell>
                          <TableCell>
                            <Tooltip title="View Details">
                              <IconButton
                                size="small"
                                onClick={() => handleViewCommit(commit)}
                              >
                                <Visibility />
                              </IconButton>
                            </Tooltip>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>

                {commits.length === 0 && (
                  <Box textAlign="center" py={4}>
                    <Typography color="text.secondary">
                      No commits found. Try syncing the repository.
                    </Typography>
                  </Box>
                )}
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Select a Repository
                </Typography>
                <Typography color="text.secondary">
                  Choose a repository from the list to view commits and details.
                </Typography>
              </CardContent>
            </Card>
          )}
        </Grid>
      </Grid>

      {/* Create Repository Dialog */}
      <Dialog open={createRepoDialog} onClose={() => setCreateRepoDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create GitHub Repository</DialogTitle>
        <DialogContent>
          <FormControl fullWidth sx={{ mt: 1, mb: 2 }}>
            <InputLabel>Problem</InputLabel>
            <Select
              value={newRepoData.problem_id}
              label="Problem"
              onChange={(e) => setNewRepoData({ ...newRepoData, problem_id: e.target.value })}
            >
              {problems.map((problem) => (
                <MenuItem key={problem.id} value={problem.id}>
                  {problem.title}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          
          <TextField
            fullWidth
            label="Branch"
            value={newRepoData.branch}
            onChange={(e) => setNewRepoData({ ...newRepoData, branch: e.target.value })}
            sx={{ mb: 2 }}
          />
          
          <TextField
            fullWidth
            multiline
            rows={3}
            label="Folder Structure (Optional)"
            value={newRepoData.folder_structure}
            onChange={(e) => setNewRepoData({ ...newRepoData, folder_structure: e.target.value })}
            placeholder="Describe the expected folder structure for students..."
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateRepoDialog(false)}>Cancel</Button>
          <Button onClick={handleCreateRepo} variant="contained">Create</Button>
        </DialogActions>
      </Dialog>

      {/* Commit Details Dialog */}
      <Dialog open={commitDetailsDialog} onClose={() => setCommitDetailsDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>Commit Details</DialogTitle>
        <DialogContent>
          {selectedCommit && (
            <Box>
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <Typography variant="h6" gutterBottom>Commit Information</Typography>
                  <Typography><strong>Student:</strong> {selectedCommit.student_commit.student_name}</Typography>
                  <Typography><strong>Message:</strong> {selectedCommit.student_commit.commit_message}</Typography>
                  <Typography><strong>Hash:</strong> {selectedCommit.student_commit.commit_hash}</Typography>
                  <Typography><strong>Date:</strong> {new Date(selectedCommit.student_commit.commit_date).toLocaleString()}</Typography>
                  <Typography><strong>Language:</strong> {selectedCommit.student_commit.language}</Typography>
                  
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="h6" gutterBottom>Performance</Typography>
                    <Typography><strong>Score:</strong> {selectedCommit.student_commit.total_score}/{selectedCommit.student_commit.total_points}</Typography>
                    <Typography><strong>Time:</strong> {selectedCommit.student_commit.execution_time_ms || 'N/A'}ms</Typography>
                    <Typography><strong>Memory:</strong> {selectedCommit.student_commit.memory_usage_mb || 'N/A'}MB</Typography>
                  </Box>
                </Grid>
                
                <Grid item xs={12} md={6}>
                  <Typography variant="h6" gutterBottom>Code</Typography>
                  <Paper sx={{ p: 2, bgcolor: 'grey.50', maxHeight: 300, overflow: 'auto' }}>
                    <pre style={{ margin: 0, fontSize: '12px' }}>
                      {selectedCommit.student_commit.code_content || 'No code content available'}
                    </pre>
                  </Paper>
                </Grid>
                
                <Grid item xs={12}>
                  <Typography variant="h6" gutterBottom>Test Results</Typography>
                  <TableContainer component={Paper}>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Status</TableCell>
                          <TableCell>Expected</TableCell>
                          <TableCell>Actual</TableCell>
                          <TableCell>Points</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {selectedCommit.commit_test_results.map((result) => (
                          <TableRow key={result.id}>
                            <TableCell>
                              <Chip
                                label={result.status}
                                color={result.status === 'passed' ? 'success' : 'error'}
                                size="small"
                              />
                            </TableCell>
                            <TableCell>N/A</TableCell>
                            <TableCell>{result.actual_output || 'N/A'}</TableCell>
                            <TableCell>{result.points_earned}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Grid>
              </Grid>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCommitDetailsDialog(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default GitHubIntegration; 