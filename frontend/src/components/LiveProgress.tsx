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
  LinearProgress,
  Alert,
  Chip,
  ToggleButton,
  ToggleButtonGroup,
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
  getLiveProgress,
  LiveProgress as LiveProgressData,
  CheckpointLiveStats,
  LessonSummaryStats,
  LiveScope,
} from '../services/api';

const POLL_MS = 3000;

function HistogramChart({ histogram }: { histogram: CheckpointLiveStats['attempts_histogram'] }) {
  const data = [
    { bucket: '1st try', count: histogram['1'] },
    { bucket: '2nd try', count: histogram['2'] },
    { bucket: '3+ tries', count: histogram['3+'] },
    { bucket: 'unsolved', count: histogram.unsolved },
  ];
  return (
    <ResponsiveContainer width="100%" height={160}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="bucket" />
        <YAxis allowDecimals={false} />
        <RechartsTooltip />
        <Bar dataKey="count" fill="#1976d2" />
      </BarChart>
    </ResponsiveContainer>
  );
}

const TIMING_BUCKETS = ['<10ms', '10–100ms', '100ms–1s', '1–5s', '5–30s', '>30s'];

function TimingChart({ histogram }: { histogram: Record<string, number> }) {
  const data = TIMING_BUCKETS.map((b) => ({ bucket: b, count: histogram[b] ?? 0 }));
  return (
    <ResponsiveContainer width="100%" height={160}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="bucket" />
        <YAxis allowDecimals={false} />
        <RechartsTooltip />
        <Bar dataKey="count" fill="#2e7d32" />
      </BarChart>
    </ResponsiveContainer>
  );
}

function CompletionChart({ histogram, totalCheckpoints }: { histogram: Record<string, number>; totalCheckpoints: number }) {
  const data = Array.from({ length: totalCheckpoints + 1 }, (_, i) => ({
    bucket: `${i}`,
    count: histogram[`${i}`] ?? 0,
  }));
  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="bucket" label={{ value: 'checkpoints solved', position: 'insideBottom', dy: 10 }} />
        <YAxis allowDecimals={false} />
        <RechartsTooltip />
        <Bar dataKey="count" fill="#7b1fa2" />
      </BarChart>
    </ResponsiveContainer>
  );
}

function SummaryCard({ summary }: { summary: LessonSummaryStats }) {
  return (
    <Card sx={{ mb: 3, backgroundColor: '#f4f9ff' }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>Lesson overview</Typography>
        <Grid container spacing={2} sx={{ mb: 2 }}>
          <Grid item xs={6} md={3}>
            <Typography variant="caption" color="text.secondary">Sessions</Typography>
            <Typography variant="h5">{summary.total_sessions}</Typography>
          </Grid>
          <Grid item xs={6} md={3}>
            <Typography variant="caption" color="text.secondary">Checkpoints</Typography>
            <Typography variant="h5">{summary.total_checkpoints}</Typography>
          </Grid>
          <Grid item xs={6} md={3}>
            <Typography variant="caption" color="text.secondary">Total attempts</Typography>
            <Typography variant="h5">{summary.total_attempts}</Typography>
          </Grid>
          <Grid item xs={6} md={3}>
            <Typography variant="caption" color="text.secondary">Overall solve rate</Typography>
            <Typography variant="h5">
              {summary.solve_rate_pct}%
              <Typography component="span" variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                ({summary.total_solved_pairs}/{summary.possible_pairs})
              </Typography>
            </Typography>
          </Grid>
        </Grid>
        <Grid container spacing={2}>
          <Grid item xs={12} md={7}>
            <Typography variant="subtitle2" gutterBottom>Checkpoints solved per student</Typography>
            {summary.total_checkpoints === 0 ? (
              <Typography variant="body2" color="text.secondary">No checkpoints registered yet.</Typography>
            ) : (
              <CompletionChart
                histogram={summary.completion_histogram}
                totalCheckpoints={summary.total_checkpoints}
              />
            )}
          </Grid>
          <Grid item xs={12} md={5}>
            <Typography variant="subtitle2" gutterBottom>Top wrong answers across the lesson</Typography>
            {summary.top_wrong_overall.length === 0 ? (
              <Typography variant="body2" color="text.secondary">No wrong answers yet.</Typography>
            ) : (
              summary.top_wrong_overall.map((w, i) => (
                <Box key={`${w.checkpoint_id}-${i}`} sx={{ display: 'flex', justifyContent: 'space-between', py: 0.5, gap: 2 }}>
                  <Box sx={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    <code>{w.checkpoint_id}</code>{' '}
                    <Typography component="span" variant="body2" color="text.secondary">→</Typography>{' '}
                    <code>{w.value}</code>
                  </Box>
                  <Typography variant="body2" color="text.secondary">×{w.count}</Typography>
                </Box>
              ))
            )}
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
}

function CheckpointCard({ cp }: { cp: CheckpointLiveStats }) {
  const solveRate = cp.attempted === 0 ? 0 : Math.round((cp.solved / cp.attempted) * 100);
  return (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
          <Typography variant="h6">
            <code>{cp.checkpoint_id}</code>
          </Typography>
          <Box>
            <Chip
              label={`${cp.solved}/${cp.attempted} solved`}
              color={solveRate >= 80 ? 'success' : solveRate >= 40 ? 'warning' : 'default'}
              sx={{ mr: 1 }}
            />
            <Chip label={`${cp.total_attempts} attempts`} variant="outlined" />
          </Box>
        </Box>
        <LinearProgress variant="determinate" value={solveRate} sx={{ mb: 2, height: 8, borderRadius: 4 }} />
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <Typography variant="subtitle2" gutterBottom>Attempts to first-correct</Typography>
            <HistogramChart histogram={cp.attempts_histogram} />
          </Grid>
          <Grid item xs={12} md={6}>
            <Typography variant="subtitle2" gutterBottom>
              Timing for correct answers{' '}
              <Typography component="span" variant="caption" color="text.secondary">
                ({cp.timing_samples} {cp.timing_samples === 1 ? 'sample' : 'samples'})
              </Typography>
            </Typography>
            {cp.timing_samples === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No timed attempts yet. Use <code>%%cadence_time {cp.checkpoint_id}</code> to record timings.
              </Typography>
            ) : (
              <TimingChart histogram={cp.timing_histogram} />
            )}
          </Grid>
          <Grid item xs={12}>
            <Typography variant="subtitle2" gutterBottom>Most common wrong answers</Typography>
            {cp.common_wrong.length === 0 ? (
              <Typography variant="body2" color="text.secondary">No wrong answers yet.</Typography>
            ) : (
              cp.common_wrong.map((w) => (
                <Box key={w.value} sx={{ display: 'flex', justifyContent: 'space-between', py: 0.5 }}>
                  <code style={{ maxWidth: '70%', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {w.value}
                  </code>
                  <Typography variant="body2" color="text.secondary">×{w.count}</Typography>
                </Box>
              ))
            )}
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
}

export default function LiveProgress() {
  const [searchParams, setSearchParams] = useSearchParams();
  const urlToken = searchParams.get('token') || '';
  const urlScope = (searchParams.get('scope') as LiveScope) || 'current';
  const urlCourseToken = searchParams.get('course_token') || '';
  const [tokenInput, setTokenInput] = useState(urlToken);
  const [activeToken, setActiveToken] = useState<string | null>(urlToken || null);
  const [scope, setScope] = useState<LiveScope>(urlScope);
  const [courseToken] = useState<string>(urlCourseToken);
  const [data, setData] = useState<LiveProgressData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!activeToken) return;

    let cancelled = false;
    const tick = async () => {
      try {
        const next = await getLiveProgress(activeToken, scope, courseToken || undefined);
        if (!cancelled) {
          setData(next);
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
  }, [activeToken, scope, courseToken]);

  const syncUrl = (t: string, s: LiveScope) => {
    const params: Record<string, string> = { token: t, scope: s };
    if (courseToken) params.course_token = courseToken;
    setSearchParams(params);
  };

  const startWatching = () => {
    const t = tokenInput.trim();
    if (!t) return;
    setActiveToken(t);
    syncUrl(t, scope);
  };

  const handleScope = (next: LiveScope | null) => {
    if (!next) return;
    // "course" requires a course_token; if we don't have one, fall back to "current".
    if (next === 'course' && !courseToken) next = 'current';
    setScope(next);
    if (activeToken) syncUrl(activeToken, next);
  };

  const stop = () => {
    setActiveToken(null);
    setData(null);
    setSearchParams({});
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>Live Lesson Progress</Typography>

      {!activeToken && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Paste the teacher token for your lesson below. You can get it by running{' '}
          <code>%cadence_create_lesson "My Lesson"</code> in a notebook — it prints a clickable dashboard link.
        </Alert>
      )}

      <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
        <TextField
          label="Teacher token"
          value={tokenInput}
          onChange={(e) => setTokenInput(e.target.value)}
          size="small"
          type="password"
          sx={{ minWidth: 380 }}
        />
        <Button variant="contained" disabled={!tokenInput.trim()} onClick={startWatching}>
          Watch
        </Button>
        {activeToken && <Button onClick={stop}>Stop</Button>}
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {data && (
        <>
          <Box sx={{ mb: 2, display: 'flex', alignItems: 'baseline', gap: 2, flexWrap: 'wrap' }}>
            <Typography variant="h6">{data.lesson_name}</Typography>
            <Chip label={`join code: ${data.join_code}`} color="primary" variant="outlined" />
            <Chip label={`${data.active_sessions} sessions`} color="primary" />
            <Typography variant="caption" color="text.secondary">polling every {POLL_MS / 1000}s</Typography>
            {courseToken && (
              <Button
                size="small"
                component={RouterLink}
                to={`/teacher/course?token=${encodeURIComponent(courseToken)}`}
              >
                ← back to course
              </Button>
            )}
          </Box>
          <Box sx={{ mb: 2 }}>
            <ToggleButtonGroup
              size="small"
              value={scope}
              exclusive
              onChange={(_e: any, next: LiveScope | null) => handleScope(next)}
            >
              <ToggleButton value="current">Standalone joiners</ToggleButton>
              <ToggleButton value="course" disabled={!courseToken}>
                This course
              </ToggleButton>
              <ToggleButton value="alltime">All-time (every course)</ToggleButton>
            </ToggleButtonGroup>
            {!courseToken && scope !== 'alltime' && (
              <Typography variant="caption" color="text.secondary" sx={{ ml: 2 }}>
                Open this notebook from a course overview to enable the "this course" scope.
              </Typography>
            )}
          </Box>
          <SummaryCard summary={data.summary} />
          {data.checkpoints.length === 0 ? (
            <Alert severity="info">No checkpoints registered for this lesson yet.</Alert>
          ) : (
            data.checkpoints.map((cp) => <CheckpointCard key={cp.checkpoint_id} cp={cp} />)
          )}
        </>
      )}
    </Box>
  );
}
