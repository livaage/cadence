import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Alert, Box, CircularProgress, Stack, Typography } from '@mui/material';
import { useAuth } from '../contexts/AuthContext';
import { formatApiError, whoami } from '../services/api';

const AuthCallback: React.FC = () => {
  const navigate = useNavigate();
  const { signIn } = useAuth();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // The backend redirects us with the JWT in the URL fragment to keep it out
    // of server logs and Referer headers. Format: #token=<jwt>&status=<status>
    const fragment = window.location.hash.replace(/^#/, '');
    const params = new URLSearchParams(fragment);
    const token = params.get('token');
    const status = params.get('status');  // created | signed_in | linked | reactivated
    if (!token) {
      setError('No token in callback URL. The OAuth flow did not complete correctly.');
      return;
    }
    // Stash status across the navigation — the destination page reads it
    // once and clears it. Doing this in sessionStorage instead of the URL so
    // it doesn't sit in the address bar after the redirect.
    if (status) {
      sessionStorage.setItem('auth_status', status);
    }
    // Wipe the fragment so the JWT doesn't sit in the browser's URL bar.
    window.history.replaceState(null, '', window.location.pathname);
    signIn(token)
      .then(async () => {
        // If this is an OAuth-only account (no local password yet), land on
        // the Account page so the user can set one — Jupyter's %cadence_login
        // is much smoother with a password than with a pasted JWT.
        try {
          const me = await whoami();
          if (!me.has_password) {
            navigate('/teacher/account?prompt=password', { replace: true });
            return;
          }
        } catch {
          // Fall through to library — non-blocking.
        }
        navigate('/teacher/library', { replace: true });
      })
      .catch((err) => setError(formatApiError(err, 'Could not validate your sign-in. Please try again.')));
  }, [navigate, signIn]);

  return (
    <Box sx={{ maxWidth: 480, mx: 'auto', pt: 10, textAlign: 'center' }}>
      <Stack spacing={2} alignItems="center">
        {!error && <CircularProgress />}
        <Typography variant="body1" color="text.secondary">
          {error ? 'Sign-in failed' : 'Signing you in…'}
        </Typography>
        {error && <Alert severity="error" sx={{ textAlign: 'left' }}>{error}</Alert>}
      </Stack>
    </Box>
  );
};

export default AuthCallback;
