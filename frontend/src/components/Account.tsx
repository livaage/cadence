import React, { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom';
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
  TextField,
  Typography,
} from '@mui/material';
import { useAuth } from '../contexts/AuthContext';
import { closeMyAccount, deleteEverything, setMyPassword, formatApiError } from '../services/api';

const Account: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const { teacher, loading, signOut, refresh } = useAuth();
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  // Hard-delete flow uses its own dialog + typed-confirmation guard, separate
  // from the soft-close one because the blast radius is different.
  const [hardOpen, setHardOpen] = useState(false);
  const [hardConfirmText, setHardConfirmText] = useState('');
  const [hardError, setHardError] = useState<string | null>(null);
  const [hardSubmitting, setHardSubmitting] = useState(false);

  // Password form state.
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newPasswordConfirm, setNewPasswordConfirm] = useState('');
  const [pwError, setPwError] = useState<string | null>(null);
  const [pwSuccess, setPwSuccess] = useState<string | null>(null);
  const [pwSubmitting, setPwSubmitting] = useState(false);
  const passwordCardRef = useRef<HTMLDivElement>(null);

  // After GitHub OAuth signup, AuthCallback bounces here with ?prompt=password.
  // Scroll the password card into view + highlight it so the user notices.
  const shouldPrompt = searchParams.get('prompt') === 'password';
  useEffect(() => {
    if (shouldPrompt && passwordCardRef.current) {
      passwordCardRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [shouldPrompt]);

  if (loading) return null;
  if (!teacher) {
    const next = encodeURIComponent(location.pathname + location.search);
    navigate(`/login?next=${next}`, { replace: true });
    return null;
  }

  const handleSetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPwError(null);
    setPwSuccess(null);
    if (newPassword.length < 8) {
      setPwError('New password must be at least 8 characters.');
      return;
    }
    if (newPassword !== newPasswordConfirm) {
      setPwError('Passwords do not match.');
      return;
    }
    setPwSubmitting(true);
    try {
      await setMyPassword(newPassword, teacher.has_password ? currentPassword : null);
      await refresh();
      setCurrentPassword('');
      setNewPassword('');
      setNewPasswordConfirm('');
      setPwSuccess(
        teacher.has_password
          ? 'Password updated. You can keep using %cadence_login from Jupyter.'
          : `Password set! Log in from Jupyter with: %cadence_login --username ${teacher.username}`,
      );
    } catch (err: any) {
      setPwError(formatApiError(err, 'Could not set password. Try again.'));
    } finally {
      setPwSubmitting(false);
    }
  };

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

  const handleHardDelete = async () => {
    setHardError(null);
    setHardSubmitting(true);
    try {
      await deleteEverything();
      signOut();
      navigate('/', { replace: true });
    } catch (err: any) {
      setHardError(formatApiError(err, 'Could not delete everything. Try again or email privacy@cadence-dash.com.'));
      setHardSubmitting(false);
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

      <Card
        ref={passwordCardRef}
        sx={{
          mb: 3,
          ...(shouldPrompt && !teacher.has_password
            ? { borderColor: 'primary.main', borderWidth: 2, borderStyle: 'solid', bgcolor: 'primary.50' }
            : {}),
        }}
      >
        <CardContent sx={{ p: 3 }}>
          <Typography variant="subtitle1" sx={{ mb: 0.5, fontWeight: 600 }}>
            {teacher.has_password ? 'Change password' : 'Set a password for Jupyter login'}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {teacher.has_password
              ? 'Updates the password you use with %cadence_login from Jupyter.'
              : `You signed up with GitHub, so you don't have a password yet. Set one here and you can log in from Jupyter with %cadence_login --username ${teacher.username}.`}
          </Typography>
          <Box component="form" onSubmit={handleSetPassword}>
            <Stack spacing={2}>
              {teacher.has_password && (
                <TextField
                  type="password"
                  label="Current password"
                  size="small"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                  fullWidth
                />
              )}
              <TextField
                type="password"
                label="New password (8+ characters)"
                size="small"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                autoComplete="new-password"
                required
                fullWidth
              />
              <TextField
                type="password"
                label="Confirm new password"
                size="small"
                value={newPasswordConfirm}
                onChange={(e) => setNewPasswordConfirm(e.target.value)}
                autoComplete="new-password"
                required
                fullWidth
              />
              {pwError && <Alert severity="error">{pwError}</Alert>}
              {pwSuccess && <Alert severity="success">{pwSuccess}</Alert>}
              <Box>
                <Button
                  type="submit"
                  variant="contained"
                  disabled={pwSubmitting}
                  sx={{ textTransform: 'none' }}
                >
                  {pwSubmitting
                    ? 'Saving…'
                    : teacher.has_password
                    ? 'Update password'
                    : 'Set password'}
                </Button>
              </Box>
            </Stack>
          </Box>
        </CardContent>
      </Card>

      <Card sx={{ mb: 3, borderColor: 'error.light', borderWidth: 1, borderStyle: 'solid' }}>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="subtitle1" sx={{ mb: 1.5, fontWeight: 600, color: 'error.main' }}>
            Close my account (recoverable for 30 days)
          </Typography>
          <Stack spacing={1.5}>
            <Typography variant="body2">
              Signs you out and marks the account inactive. If you sign in again
              within 30 days (e.g. via GitHub), the account is reactivated.
              After 30 days the data is permanently removed, with backups
              ageing out within a further 30 days.
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Courses you own remain functional via their teacher tokens during
              the grace period — the dashboard URLs you've shared with co-teachers
              keep working. To wipe everything immediately, use <strong>Delete
              everything</strong> below instead.
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

      <Card sx={{ mb: 3, borderColor: 'error.main', borderWidth: 2, borderStyle: 'solid', bgcolor: '#fef2f2' }}>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="subtitle1" sx={{ mb: 1.5, fontWeight: 700, color: 'error.dark' }}>
            ⚠ Delete everything (permanent, immediate)
          </Typography>
          <Stack spacing={1.5}>
            <Typography variant="body2">
              Hard-deletes your account <strong>and</strong> every lesson,
              course, student session, attempt, submission, and solution-reveal
              you own. No grace period, no reactivation — by the time the
              request returns, the data is gone. Dashboard URLs you've shared
              will 404 immediately.
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Use this when you want a clean break: cleaning up a test account,
              ending a course permanently, or exercising your right to erasure
              under GDPR / similar laws.
            </Typography>
            {hardError && <Alert severity="error">{hardError}</Alert>}
            <Box>
              <Button
                variant="contained"
                color="error"
                onClick={() => { setHardConfirmText(''); setHardError(null); setHardOpen(true); }}
                disabled={hardSubmitting}
                sx={{ textTransform: 'none' }}
              >
                Delete everything
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
            will be permanently deleted in 30 days unless you sign in again
            within that window.
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

      <Dialog open={hardOpen} onClose={() => setHardOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ color: 'error.dark' }}>Delete everything — type to confirm</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>
            This wipes your account <strong>and</strong> every lesson, course,
            session, attempt, submission, and solution-reveal you own.
            <strong> There is no undo and no recovery window.</strong>
          </DialogContentText>
          <DialogContentText sx={{ mb: 1 }}>
            Type <code>{teacher.username}</code> below to confirm:
          </DialogContentText>
          <TextField
            value={hardConfirmText}
            onChange={(e) => setHardConfirmText(e.target.value)}
            placeholder={teacher.username}
            size="small"
            fullWidth
            autoFocus
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setHardOpen(false)} sx={{ textTransform: 'none' }}>
            Cancel
          </Button>
          <Button
            onClick={handleHardDelete}
            color="error"
            variant="contained"
            disabled={hardSubmitting || hardConfirmText !== teacher.username}
            sx={{ textTransform: 'none' }}
          >
            {hardSubmitting ? 'Deleting…' : 'Permanently delete everything'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Account;
