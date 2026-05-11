import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Box, AppBar, Toolbar, Typography, Button, Container } from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';

// Components
import StudentDashboard from './components/StudentDashboard';
import TeacherDashboard from './components/TeacherDashboard';
import TeacherLogin from './components/TeacherLogin';
import ProblemSubmission from './components/ProblemSubmission';
import SubmissionResult from './components/SubmissionResult';
import LiveProgress from './components/LiveProgress';
import CourseOverview from './components/CourseOverview';

// Context
import { AuthProvider, useAuth } from './contexts/AuthContext';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function Navigation() {
  const { isAuthenticated, logout } = useAuth();

  return (
    <AppBar position="static">
      <Toolbar>
        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          <RouterLink to="/" style={{ color: 'white', textDecoration: 'none' }}>
            Cadence
          </RouterLink>
        </Typography>
        <Button color="inherit" component={RouterLink} to="/">
          Problems
        </Button>
        {isAuthenticated ? (
          <>
            <Button color="inherit" component={RouterLink} to="/teacher">
              Teacher Dashboard
            </Button>
            <Button color="inherit" component={RouterLink} to="/teacher/course">
              Course Overview
            </Button>
            <Button color="inherit" component={RouterLink} to="/teacher/live">
              Notebook View
            </Button>
            <Button color="inherit" onClick={logout}>
              Logout
            </Button>
          </>
        ) : (
          <Button color="inherit" component={RouterLink} to="/teacher/login">
            Teacher Login
          </Button>
        )}
      </Toolbar>
    </AppBar>
  );
}

function AppContent() {
  return (
    <Box sx={{ flexGrow: 1 }}>
      <Navigation />
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Routes>
          <Route path="/" element={<StudentDashboard />} />
          <Route path="/problem/:problemId" element={<ProblemSubmission />} />
          <Route path="/submission/:submissionId" element={<SubmissionResult />} />
          <Route path="/teacher/login" element={<TeacherLogin />} />
          <Route path="/teacher" element={<TeacherDashboard />} />
          <Route path="/teacher/live" element={<LiveProgress />} />
          <Route path="/teacher/course" element={<CourseOverview />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Container>
    </Box>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App; 