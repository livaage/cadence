import React, { useEffect, useMemo, useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Chip,
  Divider,
  Grid,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  Stack,
} from '@mui/material';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import AddIcon from '@mui/icons-material/Add';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import { getLibrary, addToLibrary, removeFromLibrary, LibraryEntry } from '../library';
import {
  resolveToken,
  getLiveProgress,
  getCourseLive,
  listMyCourses,
  listMyLessons,
} from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import Logo from './Logo';

// Demo tokens — only used when the user clicks "Try with demo data" on an empty library.
const DEMO_TOKENS = [
  { token: 'NEIN2-aVYXoXL1JsduLPMNha1q3ZaYor', kind: 'course' as const },
  { token: '6wXAo1BDx9gwSzGhzRSpmTiduLASzobx', kind: 'course' as const },
  { token: 'dOmz8uvBJZvdyDyRTtPGfnz0EAoYCAdq', kind: 'course' as const },
];

// Lookup for demo tokens. Used to retroactively mark entries that were added
// to localStorage before the `demo` flag existed — without this, an existing
// teacher who'd seeded demo data sees all three forever even after signing in.
const DEMO_TOKEN_SET = new Set(DEMO_TOKENS.map((d) => d.token));

interface CardStats {
  loading: boolean;
  error?: string;
  students?: number;
  attempts?: number;
  solveRate?: number;
}

function LibraryCard({
  entry,
  onRemove,
  removable,
}: {
  entry: LibraryEntry;
  onRemove: (token: string) => void;
  // Server-sourced entries (from /courses/mine) can't be "removed from the
  // library" — they re-appear on next fetch. Hide the X button for those.
  removable: boolean;
}) {
  const [stats, setStats] = useState<CardStats>({ loading: true });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        if (entry.kind === 'course') {
          const data = await getCourseLive(entry.token);
          if (cancelled) return;
          const avgSolve = data.notebooks.length
            ? data.notebooks.reduce((a, n) => a + n.solved_rate_pct, 0) / data.notebooks.length
            : 0;
          const totalAttempts = data.notebooks.reduce((a, n) => a + n.total_attempts, 0);
          setStats({
            loading: false,
            students: data.total_enrollments,
            attempts: totalAttempts,
            solveRate: avgSolve,
          });
        } else {
          const data = await getLiveProgress(entry.token, 'current');
          if (cancelled) return;
          setStats({
            loading: false,
            students: data.summary.total_sessions,
            attempts: data.summary.total_attempts,
            solveRate: data.summary.solve_rate_pct,
          });
        }
      } catch (e: any) {
        if (!cancelled)
          setStats({ loading: false, error: e?.response?.data?.detail || e.message || 'failed' });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [entry.token, entry.kind]);

  const drillUrl =
    entry.kind === 'course'
      ? `/teacher/course?token=${encodeURIComponent(entry.token)}`
      : `/teacher/live?token=${encodeURIComponent(entry.token)}`;

  return (
    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {entry.demo && (
        <Box
          sx={{
            bgcolor: 'warning.light',
            color: 'warning.dark',
            px: 1.5,
            py: 0.5,
            fontSize: '0.68rem',
            fontWeight: 700,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            textAlign: 'center',
            borderBottom: '1px solid',
            borderColor: 'warning.main',
          }}
        >
          Demo course — example data, not yours
        </Box>
      )}
      <CardContent sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
          <Chip
            size="small"
            label={entry.kind === 'course' ? 'course' : 'lesson'}
            variant="outlined"
            sx={{
              fontFamily: '"JetBrains Mono", monospace',
              fontSize: '0.68rem',
              height: 20,
              color: entry.kind === 'course' ? 'primary.main' : 'secondary.main',
              borderColor: entry.kind === 'course' ? 'primary.main' : 'secondary.main',
            }}
          />
          <Box sx={{ flexGrow: 1 }} />
          {removable && (
            <Tooltip title="Remove from library (doesn't delete the lesson/course)">
              <IconButton size="small" onClick={() => onRemove(entry.token)} sx={{ opacity: 0.4, '&:hover': { opacity: 1 } }}>
                <DeleteOutlineIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          )}
        </Box>
        <Typography variant="h6" sx={{ fontWeight: 600, mb: 1, lineHeight: 1.3 }}>
          {entry.name}
        </Typography>
        {entry.join_code && (
          <Typography
            variant="caption"
            sx={{
              color: 'text.secondary',
              fontFamily: '"JetBrains Mono", monospace',
              mb: 1.5,
              fontSize: '0.75rem',
            }}
          >
            join: {entry.join_code}
          </Typography>
        )}
        <Box sx={{ flexGrow: 1 }} />
        {stats.loading ? (
          <Typography variant="caption" color="text.disabled">Loading…</Typography>
        ) : stats.error ? (
          <Typography variant="caption" color="error">
            {stats.error.includes('404') ? 'Token no longer valid' : stats.error}
          </Typography>
        ) : (
          <Box sx={{ display: 'flex', gap: 2, mt: 1, mb: 1.5 }}>
            <Box>
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.04em', fontSize: '0.65rem' }}>
                Students
              </Typography>
              <Typography variant="h6" sx={{ fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>
                {stats.students}
              </Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.04em', fontSize: '0.65rem' }}>
                Attempts
              </Typography>
              <Typography variant="h6" sx={{ fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>
                {stats.attempts}
              </Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.04em', fontSize: '0.65rem' }}>
                Solve rate
              </Typography>
              <Typography
                variant="h6"
                sx={{
                  fontWeight: 600,
                  fontVariantNumeric: 'tabular-nums',
                  color:
                    (stats.solveRate ?? 0) >= 80
                      ? 'success.main'
                      : (stats.solveRate ?? 0) >= 40
                        ? 'warning.main'
                        : 'text.primary',
                }}
              >
                {(stats.solveRate ?? 0).toFixed(1)}%
              </Typography>
            </Box>
          </Box>
        )}
        <Button
          component={RouterLink}
          to={drillUrl}
          variant="contained"
          fullWidth
          sx={{ mt: 'auto' }}
        >
          Open dashboard →
        </Button>
      </CardContent>
    </Card>
  );
}

function AddTokenDialog({
  open,
  onClose,
  onAdded,
  loggedIn,
}: {
  open: boolean;
  onClose: () => void;
  onAdded: (entry: LibraryEntry) => void;
  loggedIn: boolean;
}) {
  const [token, setToken] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Accept either a raw token or the full dashboard URL
  function extractToken(input: string): string {
    const trimmed = input.trim();
    try {
      const url = new URL(trimmed);
      const t = url.searchParams.get('token');
      if (t) return t;
    } catch {
      /* not a URL */
    }
    return trimmed;
  }

  const handleAdd = async () => {
    const t = extractToken(token);
    if (!t) return;
    setBusy(true);
    setError(null);
    try {
      const resolved = await resolveToken(t);
      addToLibrary({
        token: t,
        kind: resolved.kind,
        name: resolved.name,
        join_code: resolved.join_code,
      });
      onAdded({
        token: t,
        kind: resolved.kind,
        name: resolved.name,
        join_code: resolved.join_code,
        added_at: new Date().toISOString(),
      });
      setToken('');
      onClose();
    } catch (e: any) {
      setError(
        e?.response?.status === 404
          ? "We couldn't find a course or lesson with that token. Check the value."
          : e?.message || 'Failed to validate token',
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Add a course or lesson</DialogTitle>
      <DialogContent>
        <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
          Create a new one in your notebook (recommended)
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
          In a Jupyter notebook:
        </Typography>
        <Box
          component="pre"
          sx={{
            bgcolor: 'grey.100',
            p: 1.5,
            borderRadius: 1,
            fontSize: '0.85rem',
            fontFamily: '"JetBrains Mono", monospace',
            overflow: 'auto',
            m: 0,
            mb: 1.5,
          }}
        >
{`%load_ext cadence
%cadence_login --username <you>            # for courses; lessons skip this
%cadence_create_course "Fall 2026 PHY222"  # or %cadence_create_lesson "..."`}
        </Box>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {loggedIn
            ? <>Courses you create while signed in appear here automatically — no copying needed.</>
            : <>Once you've created one, paste the token below, or <RouterLink to="/login">sign in</RouterLink> so future courses appear automatically.</>}
        </Typography>

        <Divider sx={{ my: 2.5 }}>or</Divider>

        <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
          Add an existing one by token
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Useful for token-only quick lessons, or a course someone else made
          and shared with you. Paste a <code>teacher_token</code> or the full
          dashboard URL.
        </Typography>
        <TextField
          autoFocus
          fullWidth
          placeholder="paste token or dashboard URL"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !busy) handleAdd(); }}
          disabled={busy}
          size="medium"
        />
        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={busy}>Cancel</Button>
        <Button onClick={handleAdd} variant="contained" disabled={!token.trim() || busy}>
          {busy ? 'Validating…' : 'Add to library'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

const Library: React.FC = () => {
  const [entries, setEntries] = useState<LibraryEntry[]>(() => getLibrary());
  const [serverCourses, setServerCourses] = useState<LibraryEntry[]>([]);
  const [addOpen, setAddOpen] = useState(false);
  const [seedBusy, setSeedBusy] = useState(false);
  const { teacher } = useAuth();
  const navigate = useNavigate();

  // Pull the logged-in teacher's courses AND standalone lessons from the
  // server so they appear automatically without needing to paste tokens.
  // /lessons/mine intentionally excludes lessons that have been attached to
  // a course — those show up under the course view.
  useEffect(() => {
    if (!teacher) {
      setServerCourses([]);
      return;
    }
    let cancelled = false;
    Promise.all([listMyCourses(), listMyLessons()])
      .then(([courses, lessons]) => {
        if (cancelled) return;
        const courseEntries: LibraryEntry[] = courses.map((c) => ({
          token: c.teacher_token,
          kind: 'course' as const,
          name: c.name,
          join_code: c.join_code,
          added_at: c.created_at,
        }));
        const lessonEntries: LibraryEntry[] = lessons.map((l) => ({
          token: l.teacher_token,
          kind: 'lesson' as const,
          name: l.name,
          join_code: l.join_code,
          added_at: l.created_at,
        }));
        setServerCourses([...courseEntries, ...lessonEntries]);
      })
      .catch(() => {
        if (!cancelled) setServerCourses([]);
      });
    return () => { cancelled = true; };
  }, [teacher]);

  const handleRemove = (token: string) => {
    setEntries(removeFromLibrary(token));
  };

  const handleAdded = (entry: LibraryEntry) => {
    setEntries((prev) => [entry, ...prev.filter((e) => e.token !== entry.token)]);
  };

  const seedDemoData = async () => {
    setSeedBusy(true);
    try {
      for (const { token, kind } of DEMO_TOKENS) {
        try {
          const resolved = await resolveToken(token);
          addToLibrary({
            token,
            kind: resolved.kind,
            name: resolved.name,
            join_code: resolved.join_code,
            demo: true,
          });
        } catch {
          /* skip silently — token may be stale */
        }
      }
      setEntries(getLibrary());
    } finally {
      setSeedBusy(false);
    }
  };

  // Combine server-sourced courses (from /courses/mine) with localStorage
  // entries. Server wins on token collision so the freshest name/join_code
  // shows. When logged in, also clamp demos to at most 1 so the seeded
  // examples don't clutter a real teacher's library.
  const sorted = useMemo(() => {
    const serverTokens = new Set(serverCourses.map((e) => e.token));
    const local = entries.filter((e) => !serverTokens.has(e.token));
    // Stamp `demo` on any entry whose token matches the known demo set —
    // catches localStorage entries that pre-date the `demo` field.
    const withDemoFlag = (e: LibraryEntry): LibraryEntry =>
      e.demo || DEMO_TOKEN_SET.has(e.token) ? { ...e, demo: true } : e;
    let combined: LibraryEntry[] = [
      ...serverCourses.map(withDemoFlag),
      ...local.map(withDemoFlag),
    ];

    if (teacher) {
      let demosSeen = 0;
      combined = combined.filter((e) => {
        if (!e.demo) return true;
        demosSeen += 1;
        return demosSeen <= 1;
      });
    }

    return combined.sort((a, b) => (b.added_at || '').localeCompare(a.added_at || ''));
  }, [entries, serverCourses, teacher]);

  // Server-sourced entries can't be removed from the library (they re-appear
  // on next fetch); their token set drives the per-card `removable` flag.
  const serverTokenSet = useMemo(
    () => new Set(serverCourses.map((e) => e.token)),
    [serverCourses],
  );

  return (
    <Box sx={{ maxWidth: 1100, mx: 'auto', pt: 4 }}>
      <Box sx={{ display: 'flex', alignItems: 'flex-end', mb: 4, gap: 2 }}>
        <Box>
          <Typography variant="h3" component="h1" sx={{ fontWeight: 700, letterSpacing: '-0.02em' }}>
            My library
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mt: 0.75 }}>
            Every course and lesson you've added to this browser. Click a card to open its live dashboard.
          </Typography>
        </Box>
        <Box sx={{ flexGrow: 1 }} />
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setAddOpen(true)}
          sx={{ flexShrink: 0 }}
        >
          Add course / lesson
        </Button>
      </Box>

      {sorted.length === 0 ? (
        <Card sx={{ p: 4, textAlign: 'center' }}>
          <Box sx={{ mb: 2, display: 'flex', justifyContent: 'center' }}>
            <Logo height={48} showWordmark={false} />
          </Box>
          <Typography variant="h6" sx={{ mb: 1 }}>Your library is empty</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            {teacher
              ? "Create a course in your notebook with %cadence_create_course \"...\" — it'll appear here automatically. Or paste a token from a quick lesson / shared course."
              : "Paste a teacher token to add a course or lesson, or load the demo data to see what a populated library looks like."}
          </Typography>
          <Stack direction="row" spacing={1} justifyContent="center">
            <Button variant="contained" startIcon={<AddIcon />} onClick={() => setAddOpen(true)}>
              {teacher ? 'Show notebook instructions' : 'Paste a teacher token'}
            </Button>
            {!teacher && (
              <Button variant="outlined" onClick={seedDemoData} disabled={seedBusy}>
                {seedBusy ? 'Loading demo…' : 'Try with demo data'}
              </Button>
            )}
          </Stack>
        </Card>
      ) : (
        <Grid container spacing={2}>
          {sorted.map((entry) => (
            <Grid item key={entry.token} xs={12} sm={6} md={4}>
              <LibraryCard
                entry={entry}
                onRemove={handleRemove}
                removable={!serverTokenSet.has(entry.token)}
              />
            </Grid>
          ))}
        </Grid>
      )}

      <AddTokenDialog open={addOpen} onClose={() => setAddOpen(false)} onAdded={handleAdded} loggedIn={!!teacher} />

      <Typography variant="caption" sx={{ display: 'block', mt: 4, color: 'text.disabled', textAlign: 'center' }}>
        {teacher
          ? 'Courses you own load from your account; pasted tokens are saved to this browser only.'
          : 'Saved to this browser only. Sign in to load your own courses automatically.'}
      </Typography>
    </Box>
  );
};

export default Library;
