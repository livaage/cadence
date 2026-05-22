import React, { useEffect, useState } from 'react';
import { Button, Divider, Stack, Tooltip } from '@mui/material';
import GitHubIcon from '@mui/icons-material/GitHub';
import GoogleIcon from '@mui/icons-material/Google';
import { AuthProviders, getAuthProviders, githubAuthorizeUrl } from '../services/api';

const OAuthButtons: React.FC = () => {
  const [providers, setProviders] = useState<AuthProviders | null>(null);

  useEffect(() => {
    getAuthProviders()
      .then(setProviders)
      .catch(() => setProviders({ github: false, google: false }));
  }, []);

  // While we're still asking the server, render nothing rather than flash a
  // button that might disappear.
  if (!providers) return null;
  // If neither provider is on, render nothing — the email/password form covers it.
  if (!providers.github && !providers.google) return null;

  return (
    <>
    <Stack spacing={1.5}>
      {providers.github && (
        <Button
          variant="outlined"
          size="large"
          startIcon={<GitHubIcon />}
          onClick={() => { window.location.href = githubAuthorizeUrl(); }}
          sx={{ textTransform: 'none', justifyContent: 'flex-start', pl: 3 }}
        >
          Continue with GitHub
        </Button>
      )}
      {providers.google ? (
        <Button
          variant="outlined"
          size="large"
          startIcon={<GoogleIcon />}
          sx={{ textTransform: 'none', justifyContent: 'flex-start', pl: 3 }}
        >
          Continue with Google
        </Button>
      ) : (
        <Tooltip title="Coming soon — we're working through Google's app verification.">
          <span>
            <Button
              variant="outlined"
              size="large"
              startIcon={<GoogleIcon />}
              disabled
              fullWidth
              sx={{ textTransform: 'none', justifyContent: 'flex-start', pl: 3 }}
            >
              Continue with Google (coming soon)
            </Button>
          </span>
        </Tooltip>
      )}
    </Stack>
    <Divider sx={{ my: 3 }}>or</Divider>
    </>
  );
};

export default OAuthButtons;
