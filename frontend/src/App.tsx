import React from 'react';
import { Routes, Route, Navigate, Link as RouterLink, useLocation, useNavigate } from 'react-router-dom';
import { Box, AppBar, Toolbar, Container, Stack, Button } from '@mui/material';

import Welcome from './components/Welcome';
import LiveProgress from './components/LiveProgress';
import CourseOverview from './components/CourseOverview';
import Library from './components/Library';
import Guide from './components/Guide';
import About from './components/About';
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
          {navLink('/guide', 'Guide')}
          {navLink('/privacy', 'Privacy')}
          {navLink('/terms', 'Terms')}
          {navLink('/teacher/library', 'Library')}
          {teacher ? (
            <>
              {navLink('/teacher/account', teacher.username)}
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

function App() {
  return (
    <AuthProvider>
      <Box sx={{ flexGrow: 1 }}>
        <Navigation />
        <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
          <Routes>
            <Route path="/" element={<Welcome />} />
            <Route path="/about" element={<About />} />
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
      </Box>
    </AuthProvider>
  );
}

export default App;
