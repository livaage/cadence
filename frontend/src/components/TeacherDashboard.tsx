import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
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
  Tabs,
  Tab,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
} from 'recharts';
import {
  Add,
  Visibility,
  Edit,
  Delete,
  FilterList,
  Refresh,
  GitHub,
} from '@mui/icons-material';
import {
  getProblemsTeacher,
  createProblem,
  getSubmissionsTeacher,
  getSubmissionTeacher,
  getProblemStats,
  Problem,
  Submission,
  SubmissionWithResults,
  ProblemStats,
} from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import GitHubIntegration from './GitHubIntegration';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`simple-tabpanel-${index}`}
      aria-labelledby={`simple-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const TeacherDashboard: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const [tabValue, setTabValue] = useState(0);
  const [problems, setProblems] = useState<Problem[]>([]);
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [stats, setStats] = useState<ProblemStats[]>([]);
  const [selectedSubmission, setSelectedSubmission] = useState<SubmissionWithResults | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Dialog states
  const [createProblemDialog, setCreateProblemDialog] = useState(false);
  const [submissionDetailsDialog, setSubmissionDetailsDialog] = useState(false);
  const [newProblem, setNewProblem] = useState({
    title: '',
    description: '',
    difficulty: 'medium',
    time_limit: 30,
    memory_limit: 512,
  });

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/teacher/login');
      return;
    }
    fetchData();
  }, [isAuthenticated, navigate]);

  const fetchData = async () => {
    try {
      const [problemsData, submissionsData, statsData] = await Promise.all([
        getProblemsTeacher(),
        getSubmissionsTeacher(),
        getProblemStats(),
      ]);
      setProblems(problemsData);
      setSubmissions(submissionsData);
      setStats(statsData);
    } catch (err) {
      setError('Failed to load dashboard data');
      console.error('Error fetching data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateProblem = async () => {
    if (!newProblem.title || !newProblem.description) {
      setError('Please fill in all required fields');
      return;
    }

    try {
      const problem = await createProblem(newProblem);
      setProblems([problem, ...problems]);
      setCreateProblemDialog(false);
      setNewProblem({
        title: '',
        description: '',
        difficulty: 'medium',
        time_limit: 30,
        memory_limit: 512,
      });
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create problem');
    }
  };

  const handleViewSubmission = async (submission: Submission) => {
    try {
      const details = await getSubmissionTeacher(submission.id);
      setSelectedSubmission(details);
      setSubmissionDetailsDialog(true);
    } catch (err) {
      setError('Failed to load submission details');
    }
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'easy':
        return 'success';
      case 'medium':
        return 'warning';
      case 'hard':
        return 'error';
      default:
        return 'default';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'running':
        return 'info';
      case 'error':
        return 'error';
      default:
        return 'default';
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
      <Typography variant="h4" component="h1" gutterBottom>
        Teacher Dashboard
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={tabValue} onChange={handleTabChange} aria-label="dashboard tabs">
          <Tab label="Analytics" />
          <Tab label="Submissions" />
          <Tab label="Problems" />
          <Tab label="GitHub Integration" icon={<GitHub />} iconPosition="start" />
        </Tabs>
      </Box>

      {/* Analytics Tab */}
      <TabPanel value={tabValue} index={0}>
        <Grid container spacing={3}>
          {/* Problem Statistics */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Problem Statistics
                </Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={stats}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="problem_title" />
                    <YAxis />
                    <RechartsTooltip />
                    <Bar dataKey="total_submissions" fill="#8884d8" name="Total Submissions" />
                    <Bar dataKey="correct_submissions" fill="#82ca9d" name="Correct Submissions" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </Grid>

          {/* Average Scores */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Average Scores
                </Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={stats}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="problem_title" />
                    <YAxis />
                    <RechartsTooltip />
                    <Line type="monotone" dataKey="average_score" stroke="#8884d8" name="Average Score" />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </Grid>

          {/* Performance Metrics */}
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Performance Metrics
                </Typography>
                <Grid container spacing={2}>
                  {stats.map((stat) => (
                    <Grid item xs={12} sm={6} md={4} key={stat.problem_id}>
                      <Paper sx={{ p: 2, textAlign: 'center' }}>
                        <Typography variant="h6">{stat.problem_title}</Typography>
                        <Typography variant="body2" color="text.secondary">
                          Avg Score: {stat.average_score.toFixed(1)}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Avg Time: {Math.round(stat.average_time_ms)}ms
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Success Rate: {stat.total_submissions > 0 ? ((stat.correct_submissions / stat.total_submissions) * 100).toFixed(1) : 0}%
                        </Typography>
                      </Paper>
                    </Grid>
                  ))}
                </Grid>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </TabPanel>

      {/* Submissions Tab */}
      <TabPanel value={tabValue} index={1}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h6">
            All Submissions ({submissions.length})
          </Typography>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={fetchData}
          >
            Refresh
          </Button>
        </Box>

        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Student</TableCell>
                <TableCell>Problem</TableCell>
                <TableCell>Language</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Score</TableCell>
                <TableCell>Time</TableCell>
                <TableCell>Date</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {submissions.map((submission) => {
                const problem = problems.find(p => p.id === submission.problem_id);
                return (
                  <TableRow key={submission.id}>
                    <TableCell>{submission.student_name}</TableCell>
                    <TableCell>{problem?.title || 'Unknown Problem'}</TableCell>
                    <TableCell>
                      <Chip label={submission.language.toUpperCase()} size="small" />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={submission.status}
                        color={getStatusColor(submission.status) as any}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      {submission.total_score}/{submission.total_points}
                    </TableCell>
                    <TableCell>
                      {submission.execution_time_ms ? `${submission.execution_time_ms}ms` : 'N/A'}
                    </TableCell>
                    <TableCell>
                      {new Date(submission.created_at).toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <Tooltip title="View Details">
                        <IconButton
                          size="small"
                          onClick={() => handleViewSubmission(submission)}
                        >
                          <Visibility />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>

        {submissions.length === 0 && (
          <Box textAlign="center" py={4}>
            <Typography color="text.secondary">
              No submissions found.
            </Typography>
          </Box>
        )}
      </TabPanel>

      {/* Problems Tab */}
      <TabPanel value={tabValue} index={2}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h6">
            Problems ({problems.length})
          </Typography>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => setCreateProblemDialog(true)}
          >
            Create Problem
          </Button>
        </Box>

        <Grid container spacing={3}>
          {problems.map((problem) => (
            <Grid item xs={12} md={6} lg={4} key={problem.id}>
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                    <Typography variant="h6" gutterBottom>
                      {problem.title}
                    </Typography>
                    <Chip
                      label={problem.difficulty}
                      color={getDifficultyColor(problem.difficulty) as any}
                      size="small"
                    />
                  </Box>
                  
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    {problem.description.length > 100
                      ? `${problem.description.substring(0, 100)}...`
                      : problem.description}
                  </Typography>
                  
                  <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                    <Chip label={`${problem.time_limit}s`} size="small" variant="outlined" />
                    <Chip label={`${problem.memory_limit}MB`} size="small" variant="outlined" />
                  </Box>
                  
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    <Button size="small" startIcon={<Visibility />}>
                      View
                    </Button>
                    <Button size="small" startIcon={<Edit />}>
                      Edit
                    </Button>
                    <Button size="small" startIcon={<Delete />} color="error">
                      Delete
                    </Button>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>

        {problems.length === 0 && (
          <Box textAlign="center" py={4}>
            <Typography color="text.secondary">
              No problems created yet.
            </Typography>
          </Box>
        )}
      </TabPanel>

      {/* GitHub Integration Tab */}
      <TabPanel value={tabValue} index={3}>
        <GitHubIntegration />
      </TabPanel>

      {/* Create Problem Dialog */}
      <Dialog open={createProblemDialog} onClose={() => setCreateProblemDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>Create New Problem</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Title"
            value={newProblem.title}
            onChange={(e) => setNewProblem({ ...newProblem, title: e.target.value })}
            sx={{ mb: 2, mt: 1 }}
          />
          
          <TextField
            fullWidth
            multiline
            rows={4}
            label="Description"
            value={newProblem.description}
            onChange={(e) => setNewProblem({ ...newProblem, description: e.target.value })}
            sx={{ mb: 2 }}
          />
          
          <Grid container spacing={2}>
            <Grid item xs={12} md={4}>
              <FormControl fullWidth>
                <InputLabel>Difficulty</InputLabel>
                <Select
                  value={newProblem.difficulty}
                  label="Difficulty"
                  onChange={(e) => setNewProblem({ ...newProblem, difficulty: e.target.value })}
                >
                  <MenuItem value="easy">Easy</MenuItem>
                  <MenuItem value="medium">Medium</MenuItem>
                  <MenuItem value="hard">Hard</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                type="number"
                label="Time Limit (seconds)"
                value={newProblem.time_limit}
                onChange={(e) => setNewProblem({ ...newProblem, time_limit: parseInt(e.target.value) })}
              />
            </Grid>
            
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                type="number"
                label="Memory Limit (MB)"
                value={newProblem.memory_limit}
                onChange={(e) => setNewProblem({ ...newProblem, memory_limit: parseInt(e.target.value) })}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateProblemDialog(false)}>Cancel</Button>
          <Button onClick={handleCreateProblem} variant="contained">Create</Button>
        </DialogActions>
      </Dialog>

      {/* Submission Details Dialog */}
      <Dialog open={submissionDetailsDialog} onClose={() => setSubmissionDetailsDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>Submission Details</DialogTitle>
        <DialogContent>
          {selectedSubmission && (
            <Box>
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <Typography variant="h6" gutterBottom>Submission Information</Typography>
                  <Typography><strong>Student:</strong> {selectedSubmission.submission.student_name}</Typography>
                  <Typography><strong>Problem:</strong> {selectedSubmission.problem.title}</Typography>
                  <Typography><strong>Language:</strong> {selectedSubmission.submission.language}</Typography>
                  <Typography><strong>Status:</strong> {selectedSubmission.submission.status}</Typography>
                  <Typography><strong>Score:</strong> {selectedSubmission.submission.total_score}/{selectedSubmission.submission.total_points}</Typography>
                  <Typography><strong>Time:</strong> {selectedSubmission.submission.execution_time_ms || 'N/A'}ms</Typography>
                  <Typography><strong>Memory:</strong> {selectedSubmission.submission.memory_usage_mb || 'N/A'}MB</Typography>
                  
                  {selectedSubmission.submission.error_message && (
                    <Box sx={{ mt: 2 }}>
                      <Typography variant="h6" gutterBottom>Error</Typography>
                      <Paper sx={{ p: 2, bgcolor: 'error.light', color: 'error.contrastText' }}>
                        <pre style={{ margin: 0, fontSize: '12px' }}>
                          {selectedSubmission.submission.error_message}
                        </pre>
                      </Paper>
                    </Box>
                  )}
                </Grid>
                
                <Grid item xs={12} md={6}>
                  <Typography variant="h6" gutterBottom>Code</Typography>
                  <Paper sx={{ p: 2, bgcolor: 'grey.50', maxHeight: 300, overflow: 'auto' }}>
                    <pre style={{ margin: 0, fontSize: '12px' }}>
                      {selectedSubmission.submission.source_code}
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
                        {selectedSubmission.test_results.map((result) => (
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
          <Button onClick={() => setSubmissionDetailsDialog(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default TeacherDashboard; 