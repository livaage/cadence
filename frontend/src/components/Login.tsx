import React, { useState } from 'react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Link,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { useAuth } from '../contexts/AuthContext';
import { formatApiError, loginTeacher } from '../services/api';
import OAuthButtons from './OAuthButtons';

const Login: React.FC = () => {
  const navigate = useNavigate();
  const { signIn } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const { access_token } = await loginTeacher(username, password);
      await signIn(access_token);
      navigate('/teacher/library');
    } catch (err: any) {
      setError(formatApiError(err, 'Login failed. Check your username and password.'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Box sx={{ maxWidth: 440, mx: 'auto', pt: 6 }}>
      <Card>
        <CardContent sx={{ p: 4 }}>
          <Typography variant="h4" component="h1" sx={{ mb: 1 }}>
            Sign in
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Teacher accounts are for courses. For one-off lessons you can keep
            using the join code only — no account needed.
          </Typography>

          <OAuthButtons />

          <Stack component="form" onSubmit={onSubmit} spacing={2}>
            <TextField
              label="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
              fullWidth
            />
            <TextField
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
              fullWidth
            />
            {error && <Alert severity="error">{error}</Alert>}
            <Button
              type="submit"
              variant="contained"
              size="large"
              disabled={submitting}
              sx={{ textTransform: 'none' }}
            >
              {submitting ? 'Signing in…' : 'Sign in'}
            </Button>
          </Stack>

          <Typography variant="body2" sx={{ mt: 3, textAlign: 'center' }}>
            New here?{' '}
            <Link component={RouterLink} to="/signup">
              Create an account
            </Link>
          </Typography>
        </CardContent>
      </Card>
    </Box>
  );
};

export default Login;
