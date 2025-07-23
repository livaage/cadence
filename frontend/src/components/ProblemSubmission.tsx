import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  CircularProgress,
  Paper,
  Grid,
  Chip,
  Divider,
} from '@mui/material';
import { Send, ArrowBack, Code, Timer, Memory } from '@mui/icons-material';
import { getProblem, createSubmission, Problem } from '../services/api';

const ProblemSubmission: React.FC = () => {
  const { problemId } = useParams<{ problemId: string }>();
  const navigate = useNavigate();
  
  const [problem, setProblem] = useState<Problem | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Form state
  const [studentName, setStudentName] = useState('');
  const [studentEmail, setStudentEmail] = useState('');
  const [language, setLanguage] = useState('python');
  const [sourceCode, setSourceCode] = useState('');

  useEffect(() => {
    const fetchProblem = async () => {
      if (!problemId) return;
      
      try {
        const data = await getProblem(problemId);
        setProblem(data);
        
        // Set default code based on language
        if (data.title === 'Hello World') {
          setSourceCode('print("Hello, World!")');
        } else if (data.title === 'Sum of Two Numbers') {
          setSourceCode(`# Read two integers from input
a, b = map(int, input().split())
print(a + b)`);
        } else if (data.title === 'Fibonacci Sequence') {
          setSourceCode(`# Read n from input
n = int(input())

# Generate Fibonacci sequence
fib = [0, 1]
for i in range(2, n):
    fib.append(fib[i-1] + fib[i-2])

# Print first n numbers
print(' '.join(map(str, fib[:n])))`);
        } else if (data.title === 'Sort Array') {
          setSourceCode(`# Read array size and elements
n = int(input())
arr = list(map(int, input().split()))

# Sort the array
arr.sort()

# Print sorted array
print(' '.join(map(str, arr)))`);
        } else if (data.title === 'Prime Number Check') {
          setSourceCode(`# Read number from input
n = int(input())

# Check if prime
def is_prime(num):
    if num < 2:
        return False
    for i in range(2, int(num**0.5) + 1):
        if num % i == 0:
            return False
    return True

print(str(is_prime(n)).lower())`);
        }
      } catch (err) {
        setError('Failed to load problem');
        console.error('Error fetching problem:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchProblem();
  }, [problemId]);

  const handleSubmit = async () => {
    if (!problemId || !studentName.trim() || !sourceCode.trim()) {
      setError('Please fill in all required fields');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const result = await createSubmission({
        problem_id: problemId,
        student_name: studentName.trim(),
        student_email: studentEmail.trim() || undefined,
        language,
        source_code: sourceCode,
      });

      navigate(`/submission/${result.submission_id}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to submit solution');
      console.error('Error submitting solution:', err);
    } finally {
      setSubmitting(false);
    }
  };

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

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (error && !problem) {
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

  if (!problem) {
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
        {/* Problem Description */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h5" component="h1" gutterBottom>
                {problem.title}
              </Typography>
              
              <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                <Chip 
                  label={problem.difficulty} 
                  color={getDifficultyColor(problem.difficulty) as any}
                  size="small"
                />
                <Chip 
                  icon={<Timer />}
                  label={`${problem.time_limit}s`}
                  variant="outlined"
                  size="small"
                />
                <Chip 
                  icon={<Memory />}
                  label={`${problem.memory_limit}MB`}
                  variant="outlined"
                  size="small"
                />
              </Box>

              <Divider sx={{ my: 2 }} />

              <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                {problem.description}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Code Editor and Submission Form */}
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Submit Your Solution
              </Typography>

              {error && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  {error}
                </Alert>
              )}

              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Your Name *"
                    value={studentName}
                    onChange={(e) => setStudentName(e.target.value)}
                    required
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Email (optional)"
                    type="email"
                    value={studentEmail}
                    onChange={(e) => setStudentEmail(e.target.value)}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth>
                    <InputLabel>Programming Language *</InputLabel>
                    <Select
                      value={language}
                      label="Programming Language *"
                      onChange={(e) => setLanguage(e.target.value)}
                    >
                      <MenuItem value="python">Python</MenuItem>
                      <MenuItem value="cpp">C++</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
              </Grid>

              <Box sx={{ mt: 3 }}>
                <Typography variant="subtitle1" gutterBottom>
                  Source Code *
                </Typography>
                <TextField
                  fullWidth
                  multiline
                  rows={15}
                  variant="outlined"
                  value={sourceCode}
                  onChange={(e) => setSourceCode(e.target.value)}
                  placeholder={`Enter your ${language} code here...`}
                  sx={{
                    '& .MuiInputBase-root': {
                      fontFamily: 'monospace',
                      fontSize: '14px',
                    }
                  }}
                />
              </Box>

              <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
                <Button
                  variant="contained"
                  size="large"
                  onClick={handleSubmit}
                  disabled={submitting || !studentName.trim() || !sourceCode.trim()}
                  startIcon={submitting ? <CircularProgress size={20} /> : <Send />}
                >
                  {submitting ? 'Submitting...' : 'Submit Solution'}
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default ProblemSubmission; 