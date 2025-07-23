import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  CircularProgress,
  Alert,
  Chip,
  Grid,
  Paper,
  Divider,
} from '@mui/material';
import { 
  CheckCircle, 
  Error, 
  Schedule, 
  ArrowBack, 
  Refresh,
  Timer,
  Memory,
  Code,
  Help
} from '@mui/icons-material';
import { getSubmission, Submission } from '../services/api';

const SubmissionResult: React.FC = () => {
  const { submissionId } = useParams<{ submissionId: string }>();
  const navigate = useNavigate();
  
  const [submission, setSubmission] = useState<Submission | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSubmission = async () => {
      if (!submissionId) return;
      
      try {
        const data = await getSubmission(submissionId);
        setSubmission(data);
      } catch (err) {
        setError('Failed to load submission');
        console.error('Error fetching submission:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchSubmission();
    
    // Poll for updates if submission is still pending or running
    const interval = setInterval(async () => {
      if (submission && submissionId && (submission.status === 'pending' || submission.status === 'running')) {
        try {
          const data = await getSubmission(submissionId);
          setSubmission(data);
          if (data.status === 'completed' || data.status === 'error') {
            clearInterval(interval);
          }
        } catch (err) {
          console.error('Error polling submission:', err);
        }
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [submissionId, submission?.status]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'error':
        return 'error';
      case 'running':
        return 'warning';
      case 'pending':
        return 'info';
      default:
        return 'default';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle />;
      case 'error':
        return <Error />;
      case 'running':
        return <CircularProgress size={20} />;
      case 'pending':
        return <Schedule />;
      default:
        return <Help />;
    }
  };

  const formatScore = () => {
    if (!submission) return '0/0';
    return `${submission.total_score}/${submission.total_points}`;
  };

  const getScorePercentage = () => {
    if (!submission || submission.total_points === 0) return 0;
    return Math.round((submission.total_score / submission.total_points) * 100);
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box>
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
        <Button 
          startIcon={<ArrowBack />} 
          onClick={() => navigate('/')}
          sx={{ mt: 2 }}
        >
          Back to Problems
        </Button>
      </Box>
    );
  }

  if (!submission) {
    return null;
  }

  return (
    <Box>
      <Button 
        startIcon={<ArrowBack />} 
        onClick={() => navigate('/')}
        sx={{ mb: 2 }}
      >
        Back to Problems
      </Button>

      <Grid container spacing={3}>
        {/* Submission Status */}
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
                <Typography variant="h5" component="h1">
                  Submission Result
                </Typography>
                <Chip
                  icon={getStatusIcon(submission.status)}
                  label={submission.status.toUpperCase()}
                  color={getStatusColor(submission.status) as any}
                  size="medium"
                />
              </Box>

              {/* Score Display */}
              <Paper sx={{ p: 3, mb: 3, textAlign: 'center', bgcolor: 'grey.50' }}>
                <Typography variant="h3" component="div" gutterBottom>
                  {formatScore()}
                </Typography>
                <Typography variant="h6" color="text.secondary">
                  {getScorePercentage()}% Score
                </Typography>
              </Paper>

              {/* Performance Metrics */}
              <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={6} md={3}>
                  <Paper sx={{ p: 2, textAlign: 'center' }}>
                    <Timer color="primary" sx={{ fontSize: 40, mb: 1 }} />
                    <Typography variant="h6">
                      {submission.execution_time_ms ? `${submission.execution_time_ms}ms` : 'N/A'}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Execution Time
                    </Typography>
                  </Paper>
                </Grid>
                <Grid item xs={6} md={3}>
                  <Paper sx={{ p: 2, textAlign: 'center' }}>
                    <Memory color="primary" sx={{ fontSize: 40, mb: 1 }} />
                    <Typography variant="h6">
                      {submission.memory_usage_mb ? `${submission.memory_usage_mb}MB` : 'N/A'}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Memory Usage
                    </Typography>
                  </Paper>
                </Grid>
                <Grid item xs={6} md={3}>
                  <Paper sx={{ p: 2, textAlign: 'center' }}>
                    <Code color="primary" sx={{ fontSize: 40, mb: 1 }} />
                    <Typography variant="h6">
                      {submission.language.toUpperCase()}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Language
                    </Typography>
                  </Paper>
                </Grid>
                <Grid item xs={6} md={3}>
                  <Paper sx={{ p: 2, textAlign: 'center' }}>
                    <Typography variant="h6">
                      {new Date(submission.created_at).toLocaleString()}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Submitted
                    </Typography>
                  </Paper>
                </Grid>
              </Grid>

              {/* Error Message */}
              {submission.error_message && (
                <Alert severity="error" sx={{ mb: 3 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    Error:
                  </Typography>
                  <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                    {submission.error_message}
                  </Typography>
                </Alert>
              )}

              {/* Action Buttons */}
              <Box sx={{ display: 'flex', gap: 2 }}>
                <Button
                  variant="contained"
                  onClick={() => navigate('/')}
                  startIcon={<ArrowBack />}
                >
                  Back to Problems
                </Button>
                <Button
                  variant="outlined"
                  onClick={() => window.location.reload()}
                  startIcon={<Refresh />}
                >
                  Refresh
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Submission Details */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Submission Details
              </Typography>
              
              <Divider sx={{ my: 2 }} />
              
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" color="text.secondary">
                  Student Name
                </Typography>
                <Typography variant="body1">
                  {submission.student_name}
                </Typography>
              </Box>

              {submission.student_email && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" color="text.secondary">
                    Email
                  </Typography>
                  <Typography variant="body1">
                    {submission.student_email}
                  </Typography>
                </Box>
              )}

              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" color="text.secondary">
                  Language
                </Typography>
                <Chip label={submission.language.toUpperCase()} size="small" />
              </Box>

              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" color="text.secondary">
                  Status
                </Typography>
                <Chip
                  icon={getStatusIcon(submission.status)}
                  label={submission.status}
                  color={getStatusColor(submission.status) as any}
                  size="small"
                />
              </Box>

              {submission.completed_at && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" color="text.secondary">
                    Completed At
                  </Typography>
                  <Typography variant="body2">
                    {new Date(submission.completed_at).toLocaleString()}
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default SubmissionResult; 