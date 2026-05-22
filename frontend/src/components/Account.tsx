import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Stack,
  Typography,
} from '@mui/material';
import { useAuth } from '../contexts/AuthContext';
import { closeMyAccount, formatApiError } from '../services/api';

const Account: React.FC = () => {
  const navigate = useNavigate();
  const { teacher, loading, signOut } = useAuth();
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (loading) return null;
  if (!teacher) {
    navigate('/login', { replace: true });
    return null;
  }

  const handleClose = async () => {
    setError(null);
    setSubmitting(true);
    try {
      await closeMyAccount();
      signOut();
      navigate('/', { replace: true });
    } catch (err: any) {
      setError(formatApiError(err, 'Could not close your account. Try again or email privacy@cadence-dash.com.'));
      setSubmitting(false);
    }
  };

  return (
    <Box sx={{ maxWidth: 640, mx: 'auto', pt: 4, pb: 8 }}>
      <Typography variant="h4" component="h1" sx={{ mb: 3, fontWeight: 700 }}>
        Account
      </Typography>

      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 600 }}>
            Profile
          </Typography>
          <Stack spacing={1}>
            <Typography variant="body2">
              <strong>Username:</strong> {teacher.username}
            </Typography>
            <Typography variant="body2">
              <strong>Email:</strong> {teacher.email}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              <em>Member since {new Date(teacher.created_at).toLocaleDateString()}</em>
            </Typography>
          </Stack>
        </CardContent>
      </Card>

      <Card sx={{ mb: 3, borderColor: 'error.light', borderWidth: 1, borderStyle: 'solid' }}>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="subtitle1" sx={{ mb: 1.5, fontWeight: 600, color: 'error.main' }}>
            Close my account
          </Typography>
          <Stack spacing={1.5}>
            <Typography variant="body2">
              Closing your account signs you out and marks the account for
              deletion. Your account data is permanently removed after 30 days,
              with backups ageing out within a further 30 days.
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Courses you own remain functional via their teacher tokens — the
              dashboard URLs you've shared with co-teachers keep working. If
              you want to wipe the course data too, delete the course from the
              dashboard <em>before</em> closing your account.
            </Typography>
            {error && <Alert severity="error">{error}</Alert>}
            <Box>
              <Button
                variant="outlined"
                color="error"
                onClick={() => setConfirmOpen(true)}
                disabled={submitting}
                sx={{ textTransform: 'none' }}
              >
                Close account
              </Button>
            </Box>
          </Stack>
        </CardContent>
      </Card>

      <Dialog open={confirmOpen} onClose={() => setConfirmOpen(false)}>
        <DialogTitle>Close account?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure? You'll be signed out immediately. Your account data
            will be permanently deleted in 30 days. This cannot be undone after
            that window.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmOpen(false)} sx={{ textTransform: 'none' }}>
            Cancel
          </Button>
          <Button
            onClick={handleClose}
            color="error"
            variant="contained"
            disabled={submitting}
            sx={{ textTransform: 'none' }}
          >
            {submitting ? 'Closing…' : 'Yes, close my account'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Account;
