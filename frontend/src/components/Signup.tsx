import React, { useState } from 'react';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  FormControlLabel,
  Link,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { useAuth } from '../contexts/AuthContext';
import { formatApiError, signupTeacher } from '../services/api';
import OAuthButtons from './OAuthButtons';

const Signup: React.FC = () => {
  const navigate = useNavigate();
  const { signIn } = useAuth();
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [accepted, setAccepted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!accepted) {
      setError('Please confirm you agree to the Terms and the age / consent attestation.');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    setSubmitting(true);
    try {
      const { access_token } = await signupTeacher(username, email, password);
      await signIn(access_token);
      navigate('/teacher/library');
    } catch (err: any) {
      setError(formatApiError(err, 'Signup failed. Try a different username or email.'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Box sx={{ maxWidth: 440, mx: 'auto', pt: 6 }}>
      <Card>
        <CardContent sx={{ p: 4 }}>
          <Typography variant="h4" component="h1" sx={{ mb: 1 }}>
            Create your teacher account
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Free for individuals and institutions. Sign in with GitHub for the
            fastest path, or create a username/password account below.
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
              helperText="Visible to students you teach."
            />
            <TextField
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
              fullWidth
            />
            <TextField
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
              required
              fullWidth
              helperText="At least 8 characters."
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={accepted}
                  onChange={(e) => setAccepted(e.target.checked)}
                  size="small"
                />
              }
              sx={{ alignItems: 'flex-start', mt: 0.5, '& .MuiFormControlLabel-label': { fontSize: '0.85rem', lineHeight: 1.45 } }}
              label={
                <>
                  I agree to the{' '}
                  <Link component={RouterLink} to="/terms" target="_blank">Terms</Link>{' '}
                  and{' '}
                  <Link component={RouterLink} to="/privacy" target="_blank">Privacy notice</Link>.
                  I confirm all my students are 13 or older, or that I'm using
                  Cadence under my institution's authority with appropriate
                  parental consent where local law requires it.
                </>
              }
            />
            {error && <Alert severity="error">{error}</Alert>}
            <Button
              type="submit"
              variant="contained"
              size="large"
              disabled={submitting || !accepted}
              sx={{ textTransform: 'none' }}
            >
              {submitting ? 'Creating account…' : 'Create account'}
            </Button>
          </Stack>

          <Typography variant="body2" sx={{ mt: 3, textAlign: 'center' }}>
            Already have an account?{' '}
            <Link component={RouterLink} to="/login">
              Sign in
            </Link>
          </Typography>
        </CardContent>
      </Card>
    </Box>
  );
};

export default Signup;
