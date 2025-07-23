import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Chip,
  Button,
  CircularProgress,
  Alert,
  Container,
} from '@mui/material';
import { Code, Timer, Memory } from '@mui/icons-material';
import { getProblems, Problem } from '../services/api';

const StudentDashboard: React.FC = () => {
  const [problems, setProblems] = useState<Problem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchProblems = async () => {
      try {
        const data = await getProblems();
        setProblems(data);
      } catch (err) {
        setError('Failed to load problems');
        console.error('Error fetching problems:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchProblems();
  }, []);

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty.toLowerCase()) {
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

  const handleProblemClick = (problemId: string) => {
    navigate(`/problem/${problemId}`);
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
      <Container maxWidth="md">
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg">
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Available Problems
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Choose a problem to start coding and submit your solution.
        </Typography>
      </Box>

      <Grid container spacing={3}>
        {problems.map((problem) => (
          <Grid item xs={12} md={6} lg={4} key={problem.id}>
            <Card 
              sx={{ 
                height: '100%', 
                display: 'flex', 
                flexDirection: 'column',
                cursor: 'pointer',
                transition: 'transform 0.2s, box-shadow 0.2s',
                '&:hover': {
                  transform: 'translateY(-4px)',
                  boxShadow: 4,
                }
              }}
              onClick={() => handleProblemClick(problem.id)}
            >
              <CardContent sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                  <Typography variant="h6" component="h2" gutterBottom>
                    {problem.title}
                  </Typography>
                  <Chip 
                    label={problem.difficulty} 
                    color={getDifficultyColor(problem.difficulty) as any}
                    size="small"
                  />
                </Box>
                
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2, flexGrow: 1 }}>
                  {problem.description.length > 150 
                    ? `${problem.description.substring(0, 150)}...` 
                    : problem.description
                  }
                </Typography>

                <Box sx={{ display: 'flex', gap: 2, mt: 'auto' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    <Timer fontSize="small" color="action" />
                    <Typography variant="caption" color="text.secondary">
                      {problem.time_limit}s
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    <Memory fontSize="small" color="action" />
                    <Typography variant="caption" color="text.secondary">
                      {problem.memory_limit}MB
                    </Typography>
                  </Box>
                </Box>

                <Button 
                  variant="contained" 
                  fullWidth 
                  sx={{ mt: 2 }}
                  startIcon={<Code />}
                >
                  Start Coding
                </Button>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {problems.length === 0 && !loading && (
        <Box textAlign="center" py={4}>
          <Typography variant="h6" color="text.secondary">
            No problems available at the moment.
          </Typography>
        </Box>
      )}
    </Container>
  );
};

export default StudentDashboard; 