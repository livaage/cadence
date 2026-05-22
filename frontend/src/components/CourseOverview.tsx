import React, { useEffect, useRef, useState } from 'react';
import { useSearchParams, Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Grid,
  Chip,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  LinearProgress,
  Stack,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
} from '@mui/material';
import LinkOffIcon from '@mui/icons-material/LinkOff';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
} from 'recharts';

import {
  getCourseLive,
  listCourseNotebooks,
  detachNotebookFromCourse,
  deleteLessonByToken,
  formatApiError,
  CourseLive,
  CourseNotebookRef,
} from '../services/api';
import DifficultyChip from './DifficultyChip';
import JoinCodeDisplay from './JoinCodeDisplay';

const POLL_MS = 3000;

function CompletionHistogram({ histogram, max }: { histogram: Record<string, number>; max: number }) {
  const data = Array.from({ length: max + 1 }, (_, i) => ({
    bucket: `${i}`,
    count: histogram[`${i}`] ?? 0,
  }));
  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e7e5e4" />
        <XAxis dataKey="bucket" tick={{ fontSize: 12, fill: '#64748b' }} axisLine={{ stroke: '#e7e5e4' }} tickLine={false}
          label={{ value: 'checkpoints solved across course', position: 'insideBottom', dy: 10, fill: '#94a3b8', fontSize: 11 }} />
        <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: '#64748b' }} axisLine={{ stroke: '#e7e5e4' }} tickLine={false} />
        <RechartsTooltip cursor={{ fill: 'rgba(99, 102, 241, 0.06)' }} />
        <Bar dataKey="count" fill="#7F9081" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

function StatBlock({ label, value, sub }: { label: string; value: React.ReactNode; sub?: React.ReactNode }) {
  return (
    <Box>
      <Typography
        variant="caption"
        sx={{
          display: 'block',
          color: 'text.secondary',
          textTransform: 'uppercase',
          letterSpacing: '0.06em',
          fontSize: '0.7rem',
          fontWeight: 600,
        }}
      >
        {label}
      </Typography>
      <Typography variant="h4" sx={{ fontWeight: 600, mt: 0.25, lineHeight: 1.1 }}>
        {value}
      </Typography>
      {sub && (
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.25 }}>
          {sub}
        </Typography>
      )}
    </Box>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <Typography
      variant="caption"
      sx={{
        display: 'block',
        color: 'text.secondary',
        textTransform: 'uppercase',
        letterSpacing: '0.06em',
        fontSize: '0.7rem',
        fontWeight: 600,
        mb: 1.5,
      }}
    >
      {children}
    </Typography>
  );
}

export default function CourseOverview() {
  const [searchParams, setSearchParams] = useSearchParams();
  const urlToken = searchParams.get('token') || '';
  const [tokenInput, setTokenInput] = useState(urlToken);
  const [activeToken, setActiveToken] = useState<string | null>(urlToken || null);

  const [live, setLive] = useState<CourseLive | null>(null);
  const [notebooks, setNotebooks] = useState<CourseNotebookRef[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<
    | { kind: 'detach' | 'delete'; lessonName: string; teacherToken: string }
    | null
  >(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionBusy, setActionBusy] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!activeToken) return;
    let cancelled = false;

    const tick = async () => {
      try {
        const [l, n] = await Promise.all([
          getCourseLive(activeToken),
          listCourseNotebooks(activeToken),
        ]);
        if (!cancelled) {
          setLive(l);
          setNotebooks(n);
          setError(null);
        }
      } catch (e: any) {
        if (!cancelled) setError(e?.response?.data?.detail || e.message || 'Failed to load');
      }
    };

    tick();
    timerRef.current = setInterval(tick, POLL_MS);
    return () => {
      cancelled = true;
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [activeToken]);

  const start = () => {
    const t = tokenInput.trim();
    if (!t) return;
    setActiveToken(t);
    setSearchParams({ token: t });
  };
  const stop = () => {
    setActiveToken(null);
    setLive(null);
    setNotebooks([]);
    setSearchParams({});
  };

  const tokenByLessonId = new Map(notebooks.map((nb) => [nb.id, nb.teacher_token]));

  const refresh = async () => {
    if (!activeToken) return;
    try {
      const [l, n] = await Promise.all([
        getCourseLive(activeToken),
        listCourseNotebooks(activeToken),
      ]);
      setLive(l);
      setNotebooks(n);
    } catch {
      /* poller will retry */
    }
  };

  const confirmAction = async () => {
    if (!pendingAction || !activeToken) return;
    setActionBusy(true);
    setActionError(null);
    try {
      if (pendingAction.kind === 'detach') {
        await detachNotebookFromCourse(activeToken, pendingAction.teacherToken);
      } else {
        await deleteLessonByToken(pendingAction.teacherToken);
      }
      setPendingAction(null);
      await refresh();
    } catch (err) {
      setActionError(formatApiError(err, 'Action failed.'));
    } finally {
      setActionBusy(false);
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>Course overview</Typography>

      {!activeToken && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Paste the course teacher token. You can get it by running{' '}
          <code>%cadence_create_course "My Course"</code> in a notebook — it prints a clickable dashboard link.
        </Alert>
      )}

      <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
        <TextField
          label="Course teacher token"
          value={tokenInput}
          onChange={(e) => setTokenInput(e.target.value)}
          size="small"
          type="password"
          sx={{ minWidth: 380 }}
        />
        <Button variant="contained" disabled={!tokenInput.trim()} onClick={start}>
          Watch
        </Button>
        {activeToken && <Button onClick={stop}>Stop</Button>}
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {live && (
        <>
          <Box sx={{ mb: 3, display: 'flex', alignItems: 'baseline', gap: 1.5, flexWrap: 'wrap' }}>
            <Typography variant="h5" sx={{ fontWeight: 600, letterSpacing: '-0.01em', mr: 1 }}>
              {live.course_name}
            </Typography>
            <Chip
              label={`join: ${live.join_code}`}
              variant="outlined"
              size="small"
              sx={{ fontFamily: '"JetBrains Mono", monospace' }}
            />
            <JoinCodeDisplay joinCode={live.join_code} contextName={live.course_name} />
            <Typography variant="caption" color="text.secondary">
              polling every {POLL_MS / 1000}s
            </Typography>
          </Box>

          <Card sx={{ mb: 3 }}>
            <CardContent sx={{ pt: 2.5 }}>
              <Grid container spacing={3} sx={{ mb: 3 }}>
                <Grid item xs={6} md={3}>
                  <StatBlock label="Enrolled" value={live.total_enrollments} />
                </Grid>
                <Grid item xs={6} md={3}>
                  <StatBlock label="Not started" value={live.not_started} />
                </Grid>
                <Grid item xs={6} md={3}>
                  <StatBlock label="Notebooks" value={live.notebooks.length} />
                </Grid>
                <Grid item xs={6} md={3}>
                  <StatBlock
                    label="Course-wide solve rate"
                    value={(() => {
                      if (live.notebooks.length === 0) return '—';
                      const avg =
                        live.notebooks.reduce((a, n) => a + n.solved_rate_pct, 0) / live.notebooks.length;
                      return `${avg.toFixed(1)}%`;
                    })()}
                    sub="averaged across notebooks"
                  />
                </Grid>
              </Grid>

              <SectionLabel>Distribution across notebooks</SectionLabel>
              {live.notebooks.length === 0 ? (
                <Alert severity="info" sx={{ mt: 1 }}>
                  No notebooks added yet. Use <code>%cadence_add_notebook "…"</code>.
                </Alert>
              ) : (
                <TableContainer>
                  <Table size="small" sx={{ '& td, & th': { borderColor: 'divider' } }}>
                    <TableHead>
                      <TableRow>
                        <TableCell>Notebook</TableCell>
                        <TableCell align="right">Students here now</TableCell>
                        <TableCell sx={{ minWidth: 180 }}>Distribution</TableCell>
                        <TableCell align="right">Solve rate</TableCell>
                        <TableCell align="right">Attempts</TableCell>
                        <TableCell>Difficulty</TableCell>
                        <TableCell align="right">&nbsp;</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {(() => {
                        const peerAvgs = live.notebooks.map((n) => n.avg_attempts);
                        return live.notebooks.map((nb) => {
                          const pct =
                            live.total_enrollments === 0
                              ? 0
                              : (nb.students_here_now / live.total_enrollments) * 100;
                          const tt = tokenByLessonId.get(nb.lesson_id);
                          const drillUrl = tt
                            ? `/teacher/live?token=${encodeURIComponent(tt)}&scope=course&course_token=${encodeURIComponent(activeToken!)}`
                            : null;
                          const solveColor =
                            nb.solved_rate_pct >= 80
                              ? 'success.main'
                              : nb.solved_rate_pct >= 40
                                ? 'warning.main'
                                : 'text.primary';
                          return (
                            <TableRow key={nb.lesson_id} hover>
                              <TableCell>
                                {drillUrl ? (
                                  <RouterLink
                                    to={drillUrl}
                                    style={{ color: 'inherit', textDecoration: 'none' }}
                                  >
                                    <Box
                                      component="span"
                                      sx={{
                                        fontFamily: '"JetBrains Mono", monospace',
                                        fontSize: '0.88rem',
                                        borderBottom: '1px dashed',
                                        borderColor: 'text.disabled',
                                        cursor: 'pointer',
                                        '&:hover': { color: 'primary.main', borderColor: 'primary.main' },
                                      }}
                                    >
                                      {nb.name}
                                    </Box>
                                  </RouterLink>
                                ) : (
                                  <Box component="span" sx={{ fontFamily: '"JetBrains Mono", monospace', fontSize: '0.88rem' }}>
                                    {nb.name}
                                  </Box>
                                )}
                              </TableCell>
                              <TableCell align="right" sx={{ fontVariantNumeric: 'tabular-nums', color: 'text.secondary' }}>
                                {nb.students_here_now}/{live.total_enrollments}
                              </TableCell>
                              <TableCell>
                                <LinearProgress
                                  variant="determinate"
                                  value={pct}
                                  sx={{
                                    height: 4,
                                    borderRadius: 2,
                                    '& .MuiLinearProgress-bar': { backgroundColor: 'primary.main' },
                                  }}
                                />
                              </TableCell>
                              <TableCell align="right" sx={{ fontVariantNumeric: 'tabular-nums', fontWeight: 600, color: solveColor }}>
                                {nb.solved_rate_pct}%
                              </TableCell>
                              <TableCell align="right" sx={{ fontVariantNumeric: 'tabular-nums', color: 'text.secondary' }}>
                                {nb.total_attempts}
                              </TableCell>
                              <TableCell>
                                <DifficultyChip value={nb.avg_attempts} peers={peerAvgs} />
                              </TableCell>
                              <TableCell align="right">
                                <Stack direction="row" spacing={0.5} justifyContent="flex-end" alignItems="center">
                                  {drillUrl && (
                                    <Button size="small" component={RouterLink} to={drillUrl} sx={{ textTransform: 'none' }}>
                                      Open →
                                    </Button>
                                  )}
                                  {tt && (
                                    <>
                                      <Tooltip title="Remove from this course (lesson keeps its data, stays available standalone)">
                                        <IconButton
                                          size="small"
                                          onClick={() => setPendingAction({ kind: 'detach', lessonName: nb.name, teacherToken: tt })}
                                          sx={{ opacity: 0.4, '&:hover': { opacity: 1 } }}
                                        >
                                          <LinkOffIcon fontSize="small" />
                                        </IconButton>
                                      </Tooltip>
                                      <Tooltip title="Delete this lesson and all its student data — permanent">
                                        <IconButton
                                          size="small"
                                          onClick={() => setPendingAction({ kind: 'delete', lessonName: nb.name, teacherToken: tt })}
                                          sx={{ opacity: 0.4, '&:hover': { opacity: 1, color: 'error.main' } }}
                                        >
                                          <DeleteOutlineIcon fontSize="small" />
                                        </IconButton>
                                      </Tooltip>
                                    </>
                                  )}
                                </Stack>
                              </TableCell>
                            </TableRow>
                          );
                        });
                      })()}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </CardContent>
          </Card>

          <Dialog open={pendingAction !== null} onClose={() => !actionBusy && setPendingAction(null)} maxWidth="sm" fullWidth>
            <DialogTitle>
              {pendingAction?.kind === 'detach'
                ? `Remove "${pendingAction.lessonName}" from this course?`
                : pendingAction?.kind === 'delete'
                  ? `Delete "${pendingAction.lessonName}" and all its data?`
                  : ''}
            </DialogTitle>
            <DialogContent>
              {pendingAction?.kind === 'detach' ? (
                <DialogContentText>
                  The lesson stays available standalone — its own join code keeps working,
                  and student data isn't affected. It just no longer appears under this course.
                </DialogContentText>
              ) : pendingAction?.kind === 'delete' ? (
                <DialogContentText>
                  This permanently wipes the lesson, every session that joined it, every attempt,
                  every code submission, and every solution reveal. <strong>Cannot be undone.</strong>
                </DialogContentText>
              ) : null}
              {actionError && (
                <Alert severity="error" sx={{ mt: 2 }}>{actionError}</Alert>
              )}
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setPendingAction(null)} disabled={actionBusy} sx={{ textTransform: 'none' }}>
                Cancel
              </Button>
              <Button
                onClick={confirmAction}
                disabled={actionBusy}
                variant="contained"
                color={pendingAction?.kind === 'delete' ? 'error' : 'primary'}
                sx={{ textTransform: 'none' }}
              >
                {actionBusy
                  ? 'Working…'
                  : pendingAction?.kind === 'detach'
                    ? 'Remove from course'
                    : 'Delete permanently'}
              </Button>
            </DialogActions>
          </Dialog>

          <Card>
            <CardContent sx={{ pt: 2.5 }}>
              <SectionLabel>Course-wide completion</SectionLabel>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                How many checkpoints each student has solved across every notebook in the course.
              </Typography>
              <CompletionHistogram
                histogram={live.overall_completion_histogram}
                max={Math.max(
                  0,
                  ...Object.keys(live.overall_completion_histogram).map((k) => parseInt(k, 10) || 0),
                )}
              />
            </CardContent>
          </Card>
        </>
      )}
    </Box>
  );
}
