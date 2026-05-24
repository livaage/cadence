import React, { useEffect, useState } from 'react';
import { Routes, Route, Navigate, Link as RouterLink, useLocation, useNavigate } from 'react-router-dom';
import { Alert, Box, AppBar, Toolbar, Container, Stack, Button, IconButton, Tooltip, Typography, Link as MuiLink } from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';

import Welcome from './components/Welcome';
import LiveProgress from './components/LiveProgress';
import CourseOverview from './components/CourseOverview';
import Library from './components/Library';
import Guide from './components/Guide';
import About from './components/About';
import Demo from './components/Demo';
import Privacy from './components/Privacy';
import Terms from './components/Terms';
import Logo from './components/Logo';
import Login from './components/Login';
import Signup from './components/Signup';
import AuthCallback from './components/AuthCallback';
import Account from './components/Account';
import { AuthProvider, useAuth } from './contexts/AuthContext';

function Navigation() {
  const location = useLocation();
  const navigate = useNavigate();
  const { teacher, signOut } = useAuth();
  const navLink = (to: string, label: string) => {
    const active = location.pathname === to || (to !== '/' && location.pathname.startsWith(to));
    return (
      <Button
        key={to}
        component={RouterLink}
        to={to}
        size="small"
        sx={{
          color: active ? 'primary.main' : 'text.secondary',
          fontWeight: active ? 600 : 500,
          textTransform: 'none',
          fontSize: '0.875rem',
          minWidth: 'auto',
          px: 1.25,
          '&:hover': { color: 'primary.main', backgroundColor: 'transparent' },
        }}
      >
        {label}
      </Button>
    );
  };
  return (
    <AppBar position="static">
      <Toolbar sx={{ minHeight: { xs: 56, sm: 60 }, gap: 2 }}>
        <RouterLink to="/" style={{ display: 'inline-flex', alignItems: 'center', textDecoration: 'none' }}>
          <Logo height={28} wordmarkColor="#1c1917" />
        </RouterLink>
        <Box sx={{ flexGrow: 1 }} />
        <Stack direction="row" spacing={0.5} alignItems="center">
          {navLink('/about', 'About')}
          {navLink('/demo', 'Demo')}
          {navLink('/guide', 'Guide')}
          {navLink('/privacy', 'Privacy')}
          {navLink('/terms', 'Terms')}
          {navLink('/teacher/library', 'Library')}
          {teacher ? (
            <>
              <Tooltip title={`Signed in as ${teacher.username}`} arrow>
                <span>{navLink('/teacher/account', 'Profile')}</span>
              </Tooltip>
              <Button
                size="small"
                onClick={() => { signOut(); navigate('/'); }}
                sx={{ textTransform: 'none', fontSize: '0.875rem', minWidth: 'auto', px: 1.25, color: 'text.secondary' }}
              >
                Sign out
              </Button>
            </>
          ) : (
            navLink('/login', 'Sign in')
          )}
        </Stack>
      </Toolbar>
    </AppBar>
  );
}

// One-shot banner after an OAuth round-trip. AuthCallback stashes the status
// in sessionStorage so this component can render the right message on the
// page the user actually lands on (account or library) — and then clear it.
function AuthStatusBanner() {
  const { teacher } = useAuth();
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    // Read once. Defer the clear until the user has seen it (next mount).
    const s = sessionStorage.getItem('auth_status');
    if (s) {
      setStatus(s);
      sessionStorage.removeItem('auth_status');
    }
  }, []);

  if (!status || !teacher) return null;

  let severity: 'success' | 'info' | 'warning' = 'success';
  let message: React.ReactNode = null;
  switch (status) {
    case 'created':
      message = <>Welcome to Cadence! Account <strong>{teacher.username}</strong> created via GitHub.</>;
      break;
    case 'linked':
      message = <>Linked your GitHub identity to the existing account <strong>{teacher.username}</strong>. You can sign in either way now.</>;
      severity = 'info';
      break;
    case 'reactivated':
      message = (
        <>
          Your account <strong>{teacher.username}</strong> was previously closed — signing in just reactivated it.
          If this wasn't you, <RouterLink to="/teacher/account" style={{ textDecoration: 'underline' }}>close or permanently delete it</RouterLink> now.
        </>
      );
      severity = 'warning';
      break;
    case 'signed_in':
    default:
      message = <>Signed in as <strong>{teacher.username}</strong> — your existing account.</>;
      severity = 'info';
      break;
  }

  return (
    <Alert
      severity={severity}
      sx={{ borderRadius: 0, justifyContent: 'center' }}
      action={
        <IconButton size="small" onClick={() => setStatus(null)} aria-label="dismiss">
          <CloseIcon fontSize="small" />
        </IconButton>
      }
    >
      {message}
    </Alert>
  );
}

// Reminds OAuth-only teachers (no local password) to set one so they can use
// %cadence_login from Jupyter. Hidden on the account page itself (where they'd
// already be setting one) and on auth pages (where teacher is briefly null).
function SetPasswordBanner() {
  const { teacher } = useAuth();
  const location = useLocation();
  if (!teacher || teacher.has_password) return null;
  if (location.pathname.startsWith('/teacher/account')) return null;
  return (
    <Alert
      severity="info"
      sx={{ borderRadius: 0, justifyContent: 'center' }}
      action={
        <Button
          component={RouterLink}
          to="/teacher/account?prompt=password"
          size="small"
          sx={{ textTransform: 'none' }}
        >
          Set password
        </Button>
      }
    >
      You haven't set a Jupyter password yet — needed for <code>%cadence_login</code>.
    </Alert>
  );
}

function Footer() {
  return (
    <Box
      component="footer"
      sx={{
        borderTop: '1px solid',
        borderColor: 'divider',
        py: 3,
        px: 2,
        mt: 4,
      }}
    >
      <Container maxWidth="lg">
        <Stack
          direction={{ xs: 'column', sm: 'row' }}
          spacing={{ xs: 1, sm: 3 }}
          justifyContent="space-between"
          alignItems={{ xs: 'flex-start', sm: 'center' }}
        >
          <Typography variant="caption" color="text.secondary">
            © Cadence · MIT licensed
          </Typography>
          <Stack direction="row" spacing={2.5} flexWrap="wrap" useFlexGap>
            <MuiLink component={RouterLink} to="/about" variant="caption" color="text.secondary" underline="hover">
              About
            </MuiLink>
            <MuiLink component={RouterLink} to="/guide" variant="caption" color="text.secondary" underline="hover">
              Guide
            </MuiLink>
            <MuiLink component={RouterLink} to="/privacy" variant="caption" color="text.secondary" underline="hover">
              Privacy
            </MuiLink>
            <MuiLink component={RouterLink} to="/terms" variant="caption" color="text.secondary" underline="hover">
              Terms
            </MuiLink>
            <MuiLink href="mailto:contact@cadence-dash.com" variant="caption" color="text.secondary" underline="hover">
              contact@cadence-dash.com
            </MuiLink>
          </Stack>
        </Stack>
      </Container>
    </Box>
  );
}

function App() {
  return (
    <AuthProvider>
      <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        <Navigation />
        <AuthStatusBanner />
        <SetPasswordBanner />
        <Container maxWidth="lg" sx={{ mt: 4, mb: 4, flexGrow: 1 }}>
          <Routes>
            <Route path="/" element={<Welcome />} />
            <Route path="/about" element={<About />} />
            <Route path="/demo" element={<Demo />} />
            <Route path="/guide" element={<Guide />} />
            <Route path="/privacy" element={<Privacy />} />
            <Route path="/terms" element={<Terms />} />
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route path="/teacher/auth-callback" element={<AuthCallback />} />
            <Route path="/teacher/account" element={<Account />} />
            <Route path="/teacher/library" element={<Library />} />
            <Route path="/teacher/live" element={<LiveProgress />} />
            <Route path="/teacher/course" element={<CourseOverview />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Container>
        <Footer />
      </Box>
    </AuthProvider>
  );
}

export default App;
