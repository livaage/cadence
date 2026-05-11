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
  Paper,
  LinearProgress,
} from '@mui/material';
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
  CourseLive,
  CourseNotebookRef,
} from '../services/api';

const POLL_MS = 3000;

function CompletionHistogram({ histogram, max }: { histogram: Record<string, number>; max: number }) {
  const data = Array.from({ length: max + 1 }, (_, i) => ({
    bucket: `${i}`,
    count: histogram[`${i}`] ?? 0,
  }));
  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="bucket" label={{ value: 'checkpoints solved across course', position: 'insideBottom', dy: 10 }} />
        <YAxis allowDecimals={false} />
        <RechartsTooltip />
        <Bar dataKey="count" fill="#7b1fa2" />
      </BarChart>
    </ResponsiveContainer>
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
          <Box sx={{ mb: 2, display: 'flex', alignItems: 'baseline', gap: 2, flexWrap: 'wrap' }}>
            <Typography variant="h6">{live.course_name}</Typography>
            <Chip label={`join code: ${live.join_code}`} color="primary" variant="outlined" />
            <Chip label={`${live.total_enrollments} students enrolled`} color="primary" />
            <Chip label={`${live.not_started} not started`} variant="outlined" />
            <Typography variant="caption" color="text.secondary">
              polling every {POLL_MS / 1000}s
            </Typography>
          </Box>

          <Card sx={{ mb: 3, backgroundColor: '#faf5ff' }}>
            <CardContent>
              <Typography variant="subtitle1" gutterBottom>Distribution across notebooks</Typography>
              {live.notebooks.length === 0 ? (
                <Alert severity="info">
                  No notebooks added yet. Use <code>%cadence_add_notebook "…"</code>.
                </Alert>
              ) : (
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Notebook</TableCell>
                        <TableCell align="right">Students here now</TableCell>
                        <TableCell>Distribution</TableCell>
                        <TableCell align="right">Solve rate</TableCell>
                        <TableCell align="right">Attempts</TableCell>
                        <TableCell align="right">Drill in</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {live.notebooks.map((nb) => {
                        const pct =
                          live.total_enrollments === 0
                            ? 0
                            : (nb.students_here_now / live.total_enrollments) * 100;
                        const tt = tokenByLessonId.get(nb.lesson_id);
                        return (
                          <TableRow key={nb.lesson_id}>
                            <TableCell>
                              <code>{nb.name}</code>
                            </TableCell>
                            <TableCell align="right">
                              {nb.students_here_now}/{live.total_enrollments}
                            </TableCell>
                            <TableCell sx={{ minWidth: 220 }}>
                              <LinearProgress
                                variant="determinate"
                                value={pct}
                                sx={{ height: 10, borderRadius: 4 }}
                              />
                            </TableCell>
                            <TableCell align="right">{nb.solved_rate_pct}%</TableCell>
                            <TableCell align="right">{nb.total_attempts}</TableCell>
                            <TableCell align="right">
                              {tt ? (
                                <Button
                                  size="small"
                                  component={RouterLink}
                                  to={`/teacher/live?token=${encodeURIComponent(tt)}&scope=course&course_token=${encodeURIComponent(activeToken!)}`}
                                >
                                  Open
                                </Button>
                              ) : null}
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardContent>
              <Typography variant="subtitle1" gutterBottom>Course-wide completion</Typography>
              <Typography variant="caption" color="text.secondary">
                How many checkpoints each student has solved across every notebook in the course.
              </Typography>
              <Grid container sx={{ mt: 1 }}>
                <Grid item xs={12}>
                  <CompletionHistogram
                    histogram={live.overall_completion_histogram}
                    max={Math.max(
                      0,
                      ...Object.keys(live.overall_completion_histogram).map((k) => parseInt(k, 10) || 0),
                    )}
                  />
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </>
      )}
    </Box>
  );
}
