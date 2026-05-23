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
  Collapse,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
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
  getLessonHeartbeat,
  rotateLessonToken,
  deleteLesson,
  LiveProgress as LiveProgressData,
  LessonHeartbeat,
  CheckpointLiveStats,
  LessonSummaryStats,
  LiveScope,
  TimingSample,
  StudentRosterEntry,
} from '../services/api';
import DifficultyChip from './DifficultyChip';
import StudentRoster from './StudentRoster';
import SubmissionsPanel from './SubmissionsPanel';
import JoinCodeDisplay from './JoinCodeDisplay';
import FormControlLabel from '@mui/material/FormControlLabel';
import Switch from '@mui/material/Switch';
import Tooltip from '@mui/material/Tooltip';

function useLocalBool(key: string, fallback: boolean): [boolean, (v: boolean) => void] {
  const [value, setValue] = React.useState<boolean>(() => {
    try {
      const stored = localStorage.getItem(key);
      return stored == null ? fallback : stored === 'true';
    } catch {
      return fallback;
    }
  });
  const set = (v: boolean) => {
    setValue(v);
    try { localStorage.setItem(key, String(v)); } catch {}
  };
  return [value, set];
}

const useShowRoster = () => useLocalBool('cadence.showNames', false);
const useShowOutlierNames = () => useLocalBool('cadence.showOutlierNames', false);
const useNotificationsEnabled = () => useLocalBool('cadence.notifications', false);

// A checkpoint_id with the last `.` or `/` interpreted as a section separator:
//   "setup.mean-value" → { section: "setup", label: "mean-value" }
//   "1.1.peak"         → { section: "1.1", label: "peak" }
//   "mean-value"       → { section: null, label: "mean-value" }  // no section
function parseCheckpointId(id: string): { section: string | null; label: string } {
  const lastDot = id.lastIndexOf('.');
  const lastSlash = id.lastIndexOf('/');
  const sep = Math.max(lastDot, lastSlash);
  if (sep <= 0 || sep >= id.length - 1) return { section: null, label: id };
  return { section: id.substring(0, sep), label: id.substring(sep + 1) };
}

// Group an ordered list of checkpoints into [{ section, items }] runs, preserving order.
function groupCheckpointsBySection<T extends { checkpoint_id: string }>(
  cps: T[],
): Array<{ section: string | null; items: T[] }> {
  const out: Array<{ section: string | null; items: T[] }> = [];
  for (const cp of cps) {
    const section = parseCheckpointId(cp.checkpoint_id).section;
    const last = out[out.length - 1];
    if (last && last.section === section) last.items.push(cp);
    else out.push({ section, items: [cp] });
  }
  return out;
}

// Master switch — any student name in this dashboard is gated by this.
// Default ON; flip OFF for a screen-share where you'd rather not surface anyone.
const ShowNamesContext = React.createContext<boolean>(true);
// Sub-toggle: whether the inline "fewest / most attempts" list renders per checkpoint.
// Subordinate to ShowNamesContext.
const OutlierNamesContext = React.createContext<boolean>(false);

// Adaptive polling — the dashboard self-quiesces so a forgotten tab doesn't keep
// hitting the backend forever. Heartbeat is cheap; full /live only runs when the
// heartbeat shows something changed.
const FAST_POLL_MS = 3000;    // active class
const SLOW_POLL_MS = 15000;   // 5+ min since last change
const IDLE_POLL_MS = 60000;   // 30+ min since last change
const SLOW_AFTER_MS = 5 * 60 * 1000;
const IDLE_AFTER_MS = 30 * 60 * 1000;
const PAUSE_AFTER_MS = 2 * 60 * 60 * 1000;
const POLL_MS = FAST_POLL_MS;  // header label uses this

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
        <Bar dataKey="count" fill="#2BA89E" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

const TIMING_BUCKETS = ['<10ms', '10–100ms', '100ms–1s', '1–5s', '5–30s', '>30s'];

function bucketOf(ms: number): string {
  if (ms < 10) return '<10ms';
  if (ms < 100) return '10–100ms';
  if (ms < 1000) return '100ms–1s';
  if (ms < 5000) return '1–5s';
  if (ms < 30_000) return '5–30s';
  return '>30s';
}

function TimingTooltip({ active, payload, samplesByBucket, namesAllowed }: any) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  const bucket: string = row.bucket;
  const samples: TimingSample[] = samplesByBucket[bucket] ?? [];
  const sorted = [...samples].sort((a, b) => a.elapsed_ms - b.elapsed_ms);
  return (
    <div style={{ background: 'white', border: '1px solid #ccc', padding: 8, borderRadius: 4, fontSize: 12, maxWidth: 280 }}>
      <div style={{ fontWeight: 600, marginBottom: 4 }}>{bucket} — {samples.length} {samples.length === 1 ? 'student' : 'students'}</div>
      {namesAllowed ? (
        <>
          {sorted.slice(0, 8).map((s, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
              <span>{s.display_name}</span>
              <span style={{ color: '#666' }}>{s.elapsed_ms < 1000 ? `${s.elapsed_ms} ms` : `${(s.elapsed_ms / 1000).toFixed(1)} s`}</span>
            </div>
          ))}
          {samples.length > 8 && <div style={{ color: '#666', marginTop: 4 }}>… and {samples.length - 8} more</div>}
        </>
      ) : (
        <div style={{ color: '#666', fontStyle: 'italic' }}>Names hidden. Turn on "Show student roster" to reveal.</div>
      )}
    </div>
  );
}

function TimingChart({ histogram, samples }: { histogram: Record<string, number>; samples: TimingSample[] }) {
  const namesAllowed = React.useContext(ShowNamesContext);
  const data = TIMING_BUCKETS.map((b) => ({ bucket: b, count: histogram[b] ?? 0 }));
  const samplesByBucket = React.useMemo(() => {
    const map: Record<string, TimingSample[]> = {};
    for (const s of samples) {
      const b = bucketOf(s.elapsed_ms);
      (map[b] ||= []).push(s);
    }
    return map;
  }, [samples]);
  return (
    <ResponsiveContainer width="100%" height={160}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="bucket" />
        <YAxis allowDecimals={false} />
        <RechartsTooltip
          content={(props) => (
            <TimingTooltip {...props} samplesByBucket={samplesByBucket} namesAllowed={namesAllowed} />
          )}
        />
        <Bar dataKey="count" fill="#D17753" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

function CompletionTooltip({ active, payload, checkpointNames }: any) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  const k = Number(row.bucket);
  const count = row.count as number;
  const through = checkpointNames.slice(0, k);
  return (
    <div style={{ background: 'white', border: '1px solid #ccc', padding: 10, borderRadius: 4, fontSize: 12, maxWidth: 320 }}>
      <div style={{ fontWeight: 600, marginBottom: 6 }}>
        {k} checkpoint{k === 1 ? '' : 's'} solved — {count} student{count === 1 ? '' : 's'}
      </div>
      {through.length === 0 ? (
        <div style={{ color: '#666', fontStyle: 'italic' }}>No checkpoints yet.</div>
      ) : (
        <div>
          <div style={{ color: '#666', marginBottom: 4 }}>If solved in order, these would be done:</div>
          {through.map((name: string, i: number) => (
            <div key={i} style={{ fontFamily: '"JetBrains Mono", monospace', fontSize: 11, lineHeight: 1.5 }}>
              {i + 1}. {name}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function CompletionChart({
  histogram,
  totalCheckpoints,
  checkpointNames,
}: {
  histogram: Record<string, number>;
  totalCheckpoints: number;
  checkpointNames: string[];
}) {
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
        <RechartsTooltip
          cursor={{ fill: 'rgba(127, 144, 129, 0.08)' }}
          content={(props) => <CompletionTooltip {...props} checkpointNames={checkpointNames} />}
        />
        <Bar dataKey="count" fill="#7F9081" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

function FrontierTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  const count = row.count as number;
  return (
    <div style={{ background: 'white', border: '1px solid #ccc', padding: 8, borderRadius: 4, fontSize: 12 }}>
      <div style={{ fontWeight: 600, marginBottom: 2 }}>{row.fullLabel}</div>
      <div style={{ color: '#666' }}>{count} student{count === 1 ? '' : 's'} working here</div>
    </div>
  );
}

function FrontierChart({
  histogram,
  checkpointIds,
}: {
  histogram: Record<string, number>;
  checkpointIds: string[];
}) {
  const data = [
    ...checkpointIds.map((id) => ({
      bucket: parseCheckpointId(id).label,
      fullLabel: id,
      count: histogram[id] ?? 0,
    })),
    { bucket: 'done', fullLabel: 'finished the last checkpoint', count: histogram['done'] ?? 0 },
  ];
  const total = data.reduce((s, d) => s + d.count, 0);
  if (total === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No active frontier yet — once students start attempting checkpoints they'll appear here.
      </Typography>
    );
  }
  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} margin={{ top: 5, right: 8, left: 0, bottom: 30 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis
          dataKey="bucket"
          interval={0}
          angle={-25}
          textAnchor="end"
          tick={{ fontSize: 11, fontFamily: '"JetBrains Mono", monospace' }}
          height={50}
        />
        <YAxis allowDecimals={false} />
        <RechartsTooltip cursor={{ fill: 'rgba(209, 119, 83, 0.08)' }} content={<FrontierTooltip />} />
        <Bar dataKey="count" fill="#D17753" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

function PollStateChip({ state, onResume }: { state: 'fast' | 'slow' | 'idle' | 'paused'; onResume: () => void }) {
  if (state === 'paused') {
    return (
      <Button size="small" variant="outlined" onClick={onResume} sx={{ py: 0, minHeight: 26 }}>
        ▶ Resume polling
      </Button>
    );
  }
  const label =
    state === 'fast' ? 'polling every 3s' :
    state === 'slow' ? 'class quiet — polling every 15s' :
    'lesson idle — polling every 60s';
  const tip =
    state === 'fast' ? 'Dashboard polling at full rate.' :
    state === 'slow' ? 'No recent attempts. Polling slowed to save resources — speeds back up as soon as something happens.' :
    'No activity in 30+ minutes. Polling minimised. The dashboard will fully pause after 2 hours.';
  return (
    <Tooltip title={tip}>
      <Typography
        variant="caption"
        sx={{
          color: state === 'fast' ? 'text.secondary' : 'warning.main',
          fontStyle: state === 'fast' ? 'normal' : 'italic',
        }}
      >
        {label}
      </Typography>
    </Tooltip>
  );
}

function NewActivityBanner({
  activity, onDismiss, showNames,
}: { activity: LiveProgressData['new_activity']; onDismiss: () => void; showNames: boolean }) {
  if (!activity) return null;
  const { new_attempts, new_correct, by_student } = activity;
  return (
    <Alert
      severity="info"
      icon={false}
      onClose={onDismiss}
      sx={{
        mb: 2,
        bgcolor: '#e6f5f3',
        border: '1px solid #b8e0db',
        color: 'text.primary',
        '& .MuiAlert-message': { width: '100%' },
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1.5, flexWrap: 'wrap' }}>
        <Typography variant="body2" sx={{ fontWeight: 600, color: 'primary.main' }}>
          ✨ {new_attempts} new attempt{new_attempts === 1 ? '' : 's'} since you last looked
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {new_correct} correct
        </Typography>
        {showNames && by_student.length > 0 && (
          <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
            from {by_student.slice(0, 5).map((s) => `${s.display_name} (${s.attempts})`).join(', ')}
            {by_student.length > 5 && ` +${by_student.length - 5} more`}
          </Typography>
        )}
      </Box>
    </Alert>
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

function SummaryCard({ summary, checkpoints }: { summary: LessonSummaryStats; checkpoints: CheckpointLiveStats[] }) {
  const checkpointIds = checkpoints.map((c) => c.checkpoint_id);
  const checkpointNames = checkpoints.map((c) => parseCheckpointId(c.checkpoint_id).label);
  return (
    <Card sx={{ mb: 3 }}>
      <CardContent sx={{ pt: 2.5 }}>
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={6} md={3}>
            <StatBlock label="Sessions" value={summary.total_sessions} />
          </Grid>
          <Grid item xs={6} md={3}>
            <StatBlock label="Checkpoints" value={summary.total_checkpoints} />
          </Grid>
          <Grid item xs={6} md={3}>
            <StatBlock label="Total attempts" value={summary.total_attempts} />
          </Grid>
          <Grid item xs={6} md={3}>
            <StatBlock
              label="Overall solve rate"
              value={`${summary.solve_rate_pct}%`}
              sub={`${summary.total_solved_pairs}/${summary.possible_pairs}`}
            />
          </Grid>
        </Grid>
        <Grid container spacing={3}>
          <Grid item xs={12} md={7}>
            <Typography
              variant="caption"
              sx={{
                display: 'block',
                color: 'text.secondary',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                fontSize: '0.7rem',
                fontWeight: 600,
                mb: 1,
              }}
            >
              Checkpoints solved per student
            </Typography>
            {summary.total_checkpoints === 0 ? (
              <Typography variant="body2" color="text.secondary">No checkpoints registered yet.</Typography>
            ) : (
              <CompletionChart
                histogram={summary.completion_histogram}
                totalCheckpoints={summary.total_checkpoints}
                checkpointNames={checkpointNames}
              />
            )}
          </Grid>
          <Grid item xs={12} md={5}>
            <Typography
              variant="caption"
              sx={{
                display: 'block',
                color: 'text.secondary',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                fontSize: '0.7rem',
                fontWeight: 600,
                mb: 1,
              }}
            >
              Top wrong answers across the lesson
            </Typography>
            {summary.top_wrong_overall.length === 0 ? (
              <Typography variant="body2" color="text.secondary">No wrong answers yet.</Typography>
            ) : (
              <Stack divider={<Box sx={{ borderTop: '1px solid', borderColor: 'divider' }} />}>
                {summary.top_wrong_overall.map((w, i) => (
                  <Box key={`${w.checkpoint_id}-${i}`} sx={{ display: 'flex', justifyContent: 'space-between', py: 0.75, gap: 2, alignItems: 'baseline' }}>
                    <Box sx={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', minWidth: 0 }}>
                      <Typography component="span" variant="body2" sx={{ fontFamily: '"JetBrains Mono", monospace', fontSize: '0.82rem', color: 'text.secondary' }}>
                        {w.checkpoint_id}
                      </Typography>
                      <Typography component="span" variant="body2" sx={{ mx: 0.75, color: 'text.disabled' }}>→</Typography>
                      <Typography component="span" variant="body2" sx={{ fontFamily: '"JetBrains Mono", monospace', fontSize: '0.82rem', color: 'text.primary', fontWeight: 500 }}>
                        {w.value}
                      </Typography>
                    </Box>
                    <Typography variant="body2" sx={{ color: 'text.secondary', fontVariantNumeric: 'tabular-nums' }}>
                      ×{w.count}
                    </Typography>
                  </Box>
                ))}
              </Stack>
            )}
          </Grid>
        </Grid>
        {summary.total_checkpoints > 0 && (
          <Box sx={{ mt: 3 }}>
            <Typography
              variant="caption"
              sx={{
                display: 'block',
                color: 'text.secondary',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                fontSize: '0.7rem',
                fontWeight: 600,
                mb: 0.5,
              }}
            >
              Where students are working
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
              One bar per checkpoint: count of students whose current frontier is here. Frontier = their most recent
              wrong attempt, or the next checkpoint after their most recent correct one.
            </Typography>
            <FrontierChart
              histogram={summary.frontier_histogram || {}}
              checkpointIds={checkpointIds}
            />
          </Box>
        )}
      </CardContent>
    </Card>
  );
}

function WrongAnswerRow({ item }: { item: CheckpointLiveStats['common_wrong'][number] }) {
  // Names are never inline — hover the row to reveal. Only available when the master
  // "Show student roster" toggle is ON. With it OFF, no hover affordance at all.
  const namesAllowed = React.useContext(ShowNamesContext);
  const row = (
    <Box
      sx={{
        py: 0.5,
        display: 'flex',
        justifyContent: 'space-between',
        cursor: namesAllowed ? 'help' : 'default',
        borderRadius: 0.5,
        '&:hover': namesAllowed ? { backgroundColor: 'action.hover' } : undefined,
      }}
    >
      <code style={{ maxWidth: '70%', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {item.value}
      </code>
      <Typography variant="body2" color="text.secondary">×{item.count}</Typography>
    </Box>
  );
  if (!namesAllowed || item.student_names.length === 0) return row;
  return (
    <Tooltip
      title={
        <Box>
          {item.student_names.map((n) => <div key={n}>{n}</div>)}
          {item.count > item.student_names.length && (
            <div style={{ marginTop: 4, opacity: 0.7 }}>
              +{item.count - item.student_names.length} more
            </div>
          )}
        </Box>
      }
      placement="left"
      arrow
      enterDelay={200}
      slotProps={{ tooltip: { sx: { fontSize: '0.8rem', maxWidth: 280 } } }}
    >
      {row}
    </Tooltip>
  );
}

function computeOutliers(checkpointId: string, roster: StudentRosterEntry[]) {
  const entries = roster
    .map((r) => {
      const cp = r.per_checkpoint.find((p) => p.checkpoint_id === checkpointId);
      return cp && cp.attempts > 0
        ? { name: r.display_name, attempts: cp.attempts, solved: cp.status === 'solved', elapsed: cp.elapsed_ms_first_correct }
        : null;
    })
    .filter((e): e is { name: string; attempts: number; solved: boolean; elapsed: number | null } => e !== null);

  if (entries.length === 0) return { fewest: [], most: [] };
  const fewest = [...entries]
    .sort((a, b) => a.attempts - b.attempts || (a.elapsed ?? Infinity) - (b.elapsed ?? Infinity))
    .slice(0, 3);
  const most = [...entries]
    .sort((a, b) => b.attempts - a.attempts || (b.elapsed ?? -Infinity) - (a.elapsed ?? -Infinity))
    .slice(0, 3);
  return { fewest, most };
}

function OutlierSection({ checkpointId, roster }: { checkpointId: string; roster: StudentRosterEntry[] }) {
  const enabled = React.useContext(OutlierNamesContext);
  const { fewest, most } = React.useMemo(() => computeOutliers(checkpointId, roster), [checkpointId, roster]);
  if (!enabled) return null;
  if (fewest.length === 0 && most.length === 0) return null;
  const fmt = (e: { name: string; attempts: number }) => `${e.name} (${e.attempts}${e.attempts === 1 ? ' try' : ' tries'})`;
  return (
    <Box sx={{ mt: 1.5, pt: 1.5, borderTop: '1px dashed', borderColor: 'divider' }}>
      {fewest.length > 0 && (
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
          <strong>Fewest attempts:</strong> {fewest.map(fmt).join(', ')}
        </Typography>
      )}
      {most.length > 0 && (
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
          <strong>Most attempts:</strong> {most.map(fmt).join(', ')}
        </Typography>
      )}
    </Box>
  );
}

function SectionGroup({
  section,
  items,
  totalAttempts,
  solved,
  attempted,
  children,
}: {
  section: string;
  items: CheckpointLiveStats[];
  totalAttempts: number;
  solved: number;
  attempted: number;
  children: React.ReactNode;
}) {
  const [open, setOpen] = React.useState(true);
  const solveRate = attempted > 0 ? Math.round((solved / attempted) * 100) : 0;
  return (
    <Box sx={{ mb: 1.5 }}>
      <Box
        onClick={() => setOpen((o) => !o)}
        sx={{
          display: 'flex', alignItems: 'center', gap: 1.5, cursor: 'pointer',
          py: 1, px: 1.5, borderRadius: 1,
          '&:hover': { backgroundColor: 'action.hover' },
        }}
      >
        {open ? <ExpandLessIcon fontSize="small" sx={{ color: 'text.secondary' }} /> : <ExpandMoreIcon fontSize="small" sx={{ color: 'text.secondary' }} />}
        <Typography
          variant="overline"
          sx={{
            flexGrow: 1,
            fontFamily: '"JetBrains Mono", monospace',
            fontWeight: 600,
            color: 'text.primary',
            letterSpacing: '0.04em',
            lineHeight: 1,
          }}
        >
          {section}
          <Typography component="span" variant="caption" sx={{ ml: 1, color: 'text.disabled', fontFamily: 'inherit', textTransform: 'none', letterSpacing: 0 }}>
            · {items.length}
          </Typography>
        </Typography>
        <Typography variant="caption" sx={{ color: 'text.secondary', fontVariantNumeric: 'tabular-nums' }}>
          {solved}/{attempted} solved · {totalAttempts} attempts
        </Typography>
        <Chip
          size="small"
          label={`${solveRate}%`}
          color={solveRate >= 80 ? 'success' : solveRate >= 40 ? 'warning' : 'default'}
          variant="outlined"
          sx={{ minWidth: 56 }}
        />
      </Box>
      <Collapse in={open} unmountOnExit>
        <Box sx={{ pt: 1 }}>{children}</Box>
      </Collapse>
    </Box>
  );
}

function CheckpointCard({ cp, peers, roster, teacherToken, showRoster }: { cp: CheckpointLiveStats; peers: Array<number | null>; roster: StudentRosterEntry[]; teacherToken: string; showRoster: boolean }) {
  const label = parseCheckpointId(cp.checkpoint_id).label;
  const solveRate = cp.attempted === 0 ? 0 : Math.round((cp.solved / cp.attempted) * 100);
  const solveColor: 'success' | 'warning' | 'inherit' =
    solveRate >= 80 ? 'success' : solveRate >= 40 ? 'warning' : 'inherit';
  return (
    <Card sx={{ mb: 1.5 }}>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5, gap: 2, flexWrap: 'wrap' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 0 }}>
            <Typography
              variant="h6"
              sx={{
                fontFamily: '"JetBrains Mono", monospace',
                fontWeight: 600,
                fontSize: '1rem',
              }}
            >
              {label}
            </Typography>
            {cp.comparator === 'manual' && (
              <Tooltip title="Manual checkpoint — student calls cadence.mark_done() to self-attest. No automated check.">
                <Box sx={{ fontSize: '0.95rem', cursor: 'help', opacity: 0.85 }}>✋</Box>
              </Tooltip>
            )}
            {cp.has_hint && (
              <Tooltip
                title={
                  <Box>
                    <div>
                      Hint unlocks for students after{' '}
                      <strong>{cp.hint_after_attempts}</strong>{' '}
                      attempt{cp.hint_after_attempts === 1 ? '' : 's'}. They opt in via{' '}
                      <code>cadence.show_hint()</code>.
                    </div>
                  </Box>
                }
              >
                <Box sx={{ fontSize: '0.95rem', cursor: 'help', opacity: 0.85 }}>💡</Box>
              </Tooltip>
            )}
            {cp.has_solution && (
              <Tooltip
                title={
                  <Box>
                    <div>
                      Solution unlocks for students after{' '}
                      <strong>{cp.reveal_after_attempts}</strong> attempts.
                    </div>
                    {cp.solution_views > 0 && (
                      <div style={{ marginTop: 4 }}>
                        {cp.solution_views} student{cp.solution_views === 1 ? '' : 's'} viewed it so far.
                      </div>
                    )}
                  </Box>
                }
              >
                <Box sx={{ fontSize: '0.95rem', cursor: 'help', opacity: 0.85 }}>
                  🔓{cp.solution_views > 0 && (
                    <Typography component="span" variant="caption" sx={{ ml: 0.5, color: 'secondary.main', fontWeight: 600 }}>
                      {cp.solution_views}
                    </Typography>
                  )}
                </Box>
              </Tooltip>
            )}
            {cp.allow_submissions && (
              <Tooltip title="Students can submit code via %%cadence_submit. Open the panel below to view submissions.">
                <Box sx={{ fontSize: '0.95rem', cursor: 'help', opacity: 0.85 }}>
                  💾{cp.submission_count > 0 && (
                    <Typography component="span" variant="caption" sx={{ ml: 0.5, color: 'primary.main', fontWeight: 600 }}>
                      {cp.submission_count}
                    </Typography>
                  )}
                </Box>
              </Tooltip>
            )}
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            {cp.comparator !== 'manual' && <DifficultyChip value={cp.avg_attempts} peers={peers} />}
            <Typography variant="body2" sx={{ color: 'text.secondary', fontVariantNumeric: 'tabular-nums' }}>
              <Typography component="span" sx={{ color: solveColor === 'inherit' ? 'text.secondary' : `${solveColor}.main`, fontWeight: 600 }}>
                {cp.solved}/{cp.attempted}
              </Typography>
              <Typography component="span" sx={{ color: 'text.disabled', mx: 0.75 }}>
                {cp.comparator === 'manual' ? 'marked' : 'solved'}
              </Typography>
              <Typography component="span" sx={{ color: 'text.disabled', mx: 0.5 }}>·</Typography>
              <Typography component="span">
                {cp.total_attempts} attempt{cp.total_attempts === 1 ? '' : 's'}
              </Typography>
            </Typography>
          </Box>
        </Box>
        <LinearProgress
          variant="determinate"
          value={solveRate}
          sx={{
            mb: 2,
            height: 4,
            borderRadius: 2,
            '& .MuiLinearProgress-bar': { backgroundColor: 'primary.main' },
          }}
        />
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
              <TimingChart histogram={cp.timing_histogram} samples={cp.timing_samples_detail} />
            )}
          </Grid>
          <Grid item xs={12}>
            <Typography variant="subtitle2" gutterBottom>Most common wrong answers</Typography>
            {cp.common_wrong.length === 0 ? (
              <Typography variant="body2" color="text.secondary">No wrong answers yet.</Typography>
            ) : (
              cp.common_wrong.map((w) => <WrongAnswerRow key={w.value} item={w} />)
            )}
            <OutlierSection checkpointId={cp.checkpoint_id} roster={roster} />
          </Grid>
        </Grid>
        {cp.allow_submissions && (
          <SubmissionsPanel
            teacherToken={teacherToken}
            checkpointId={cp.checkpoint_id}
            count={cp.submission_count}
            showNames={showRoster}
          />
        )}
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
  const [showRoster, setShowRoster] = useShowRoster();
  const [showOutlierNames, setShowOutlierNames] = useShowOutlierNames();
  const [notificationsEnabled, setNotificationsEnabled] = useNotificationsEnabled();
  const [notifPermission, setNotifPermission] = useState<NotificationPermission | 'unsupported'>(
    typeof Notification === 'undefined' ? 'unsupported' : Notification.permission
  );
  // Track which (session, checkpoint) we've already notified about so toast spam
  // doesn't happen across polls. Ref so changing it doesn't trigger re-render.
  const notifiedRef = useRef<Set<string>>(new Set());
  const [pollState, setPollState] = useState<'fast' | 'slow' | 'idle' | 'paused'>('fast');
  const [resumeKey, setResumeKey] = useState(0);
  const [bannerDismissed, setBannerDismissed] = useState(false);
  const autoSwitched = useRef(false);

  // Internal scope name → backend scope_counts key
  const countOf = (s: LiveScope, counts: LiveProgressData['scope_counts']): number => {
    if (s === 'current') return counts.standalone ?? 0;
    if (s === 'course') return counts.course ?? 0;
    return counts.alltime ?? 0;
  };

  const lastSeenKey = activeToken ? `cadence.lastSeen.${activeToken}` : null;

  useEffect(() => {
    if (!activeToken) return;
    setBannerDismissed(false);  // reset banner when token/scope changes

    let cancelled = false;
    let timeoutId: ReturnType<typeof setTimeout> | null = null;
    let lastChangeAt = Date.now();
    let lastHeartbeat: LessonHeartbeat | null = null;

    const firstSince = (lastSeenKey && localStorage.getItem(lastSeenKey)) || undefined;

    const fullFetch = async (since?: string) => {
      try {
        const next = await getLiveProgress(activeToken, scope, courseToken || undefined, since);
        if (cancelled) return;
        setData(next);
        setError(null);
      } catch (e: any) {
        if (!cancelled) setError(e?.response?.data?.detail || e.message || 'Failed to load');
      }
    };

    const tick = async () => {
      if (cancelled || document.hidden) return;
      try {
        const hb = await getLessonHeartbeat(activeToken, scope, courseToken || undefined);
        if (cancelled) return;
        const changed =
          !lastHeartbeat ||
          lastHeartbeat.total_attempts !== hb.total_attempts ||
          lastHeartbeat.total_sessions !== hb.total_sessions ||
          lastHeartbeat.last_attempt_at !== hb.last_attempt_at;
        lastHeartbeat = hb;
        if (changed) {
          await fullFetch();
          lastChangeAt = Date.now();
        }
      } catch (e: any) {
        if (!cancelled) setError(e?.response?.data?.detail || e.message || 'Failed to load');
      }
    };

    const schedule = () => {
      if (cancelled) return;
      const sinceChange = Date.now() - lastChangeAt;
      let ms = FAST_POLL_MS;
      if (sinceChange > PAUSE_AFTER_MS) {
        setPollState('paused');
        return;  // stop scheduling — manual Resume re-runs the effect
      }
      if (sinceChange > IDLE_AFTER_MS) {
        ms = IDLE_POLL_MS;
        setPollState('idle');
      } else if (sinceChange > SLOW_AFTER_MS) {
        ms = SLOW_POLL_MS;
        setPollState('slow');
      } else {
        setPollState('fast');
      }
      timeoutId = setTimeout(async () => {
        await tick();
        schedule();
      }, ms);
    };

    // First load — includes ?since=<localStorage> so we can render the banner.
    // Then prime the heartbeat with the real current value so the next tick
    // doesn't see a "change" and refetch (which would wipe new_activity).
    fullFetch(firstSince)
      .then(() => (cancelled ? null : getLessonHeartbeat(activeToken, scope, courseToken || undefined)))
      .then((hb) => {
        if (cancelled) return;
        if (hb) lastHeartbeat = hb;
        schedule();
      })
      .catch(() => { if (!cancelled) schedule(); });

    const onVisibility = () => {
      if (!document.hidden && !cancelled) {
        // Coming back from hidden — tick immediately and resume the loop.
        if (timeoutId) clearTimeout(timeoutId);
        tick().then(() => { if (!cancelled) schedule(); });
      }
    };
    document.addEventListener('visibilitychange', onVisibility);

    return () => {
      cancelled = true;
      if (timeoutId) clearTimeout(timeoutId);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [activeToken, scope, courseToken, resumeKey, lastSeenKey]);

  const handleResume = () => {
    setPollState('fast');
    setResumeKey((k) => k + 1);
  };

  const dismissBanner = () => {
    if (lastSeenKey) localStorage.setItem(lastSeenKey, new Date().toISOString());
    setBannerDismissed(true);
  };

  const handleEnableNotifications = async (enabled: boolean) => {
    if (!enabled) {
      setNotificationsEnabled(false);
      return;
    }
    if (notifPermission === 'unsupported') {
      window.alert("Your browser doesn't support desktop notifications.");
      return;
    }
    if (notifPermission === 'denied') {
      window.alert(
        "Notifications were blocked for this site. Reset the permission in your browser's site settings."
      );
      return;
    }
    if (notifPermission === 'default') {
      const perm = await Notification.requestPermission();
      setNotifPermission(perm);
      if (perm !== 'granted') return;
    }
    setNotificationsEnabled(true);
  };

  // Fire a desktop notification whenever a new stuck student appears in the data.
  useEffect(() => {
    if (!notificationsEnabled || notifPermission !== 'granted' || !data) return;
    for (const s of data.stuck_students) {
      const key = `${s.session_id}::${s.checkpoint_id}`;
      if (notifiedRef.current.has(key)) continue;
      notifiedRef.current.add(key);
      try {
        new Notification(`${s.display_name} is stuck on ${s.checkpoint_id.split('.').pop()}`, {
          body: `${s.wrong_attempts} wrong attempts · last try ${s.minutes_since_last_attempt} min ago`,
          tag: key,  // browser dedup
        });
      } catch {
        // ignore — some browsers throw if site isn't focused
      }
    }
  }, [data, notificationsEnabled, notifPermission]);

  const [rotateResult, setRotateResult] = useState<{ token: string; join_code: string } | null>(null);

  const handleRotateToken = async (rotateJoinCode: boolean) => {
    if (!activeToken) return;
    const ok = window.confirm(
      rotateJoinCode
        ? 'Rotate teacher_token AND join_code? Any URLs you bookmarked AND any student notebooks holding the old join_code will need updating.'
        : 'Rotate this lesson\'s teacher_token? The current dashboard URL stops working immediately; students keep working under the same join_code.'
    );
    if (!ok) return;
    try {
      const fresh = await rotateLessonToken(activeToken, rotateJoinCode);
      setRotateResult({ token: fresh.teacher_token, join_code: fresh.join_code });
      // Swap the URL and active token, which restarts the polling loop.
      const params: Record<string, string> = { token: fresh.teacher_token, scope };
      if (courseToken) params.course_token = courseToken;
      setSearchParams(params);
      setActiveToken(fresh.teacher_token);
      setTokenInput(fresh.teacher_token);
    } catch (e: any) {
      setError(e?.response?.data?.detail || e.message || 'Rotation failed');
    }
  };

  const handleDeleteLesson = async () => {
    if (!activeToken) return;
    const ok = window.confirm(
      'Delete this lesson and ALL associated data — every student session, every attempt, every code/plot submission. ' +
      'This cannot be undone. The dashboard URL will stop working. Continue?'
    );
    if (!ok) return;
    const confirm2 = window.prompt('Type DELETE to confirm:');
    if (confirm2 !== 'DELETE') return;
    try {
      await deleteLesson(activeToken);
      window.location.href = '/teacher/library';
    } catch (e: any) {
      setError(e?.response?.data?.detail || e.message || 'Delete failed');
    }
  };

  const syncUrl = (t: string, s: LiveScope) => {
    const params: Record<string, string> = { token: t, scope: s };
    if (courseToken) params.course_token = courseToken;
    setSearchParams(params);
  };

  // Once the first response arrives, jump away from an empty scope to a non-empty one.
  // Runs once per landing so the user isn't kicked off a scope they later picked.
  useEffect(() => {
    if (!data || autoSwitched.current) return;
    const counts = data.scope_counts;
    if (countOf(scope, counts) > 0) {
      autoSwitched.current = true;
      return;
    }
    const priority: LiveScope[] = courseToken
      ? ['course', 'alltime', 'current']
      : ['current', 'alltime'];
    const next = priority.find((s) => countOf(s, counts) > 0);
    autoSwitched.current = true;
    if (next && next !== scope) {
      setScope(next);
      if (activeToken) syncUrl(activeToken, next);
    }
  }, [data, scope, courseToken, activeToken]);

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
        <ShowNamesContext.Provider value={showRoster}>
          <Box sx={{ mb: 1, display: 'flex', alignItems: 'baseline', gap: 2, flexWrap: 'wrap' }}>
            <Typography variant="h6">{data.lesson_name}</Typography>
            <Chip label={`join code: ${data.join_code}`} color="primary" variant="outlined" />
            <JoinCodeDisplay joinCode={data.join_code} contextName={data.lesson_name} />
            <Chip label={`${data.active_sessions} sessions`} color="primary" />
            <Tooltip title="Each student session is wiped this many days after the student last touches it. Teachers can shorten this (but not extend) via %cadence_set_retention in a notebook.">
              <Chip
                label={`retention: ${data.session_retention_days}d`}
                variant="outlined"
                size="small"
                sx={{ fontFamily: '"JetBrains Mono", monospace', fontSize: '0.72rem' }}
              />
            </Tooltip>
            <PollStateChip state={pollState} onResume={handleResume} />
            {courseToken && (
              <Button
                size="small"
                component={RouterLink}
                to={`/teacher/course?token=${encodeURIComponent(courseToken)}`}
              >
                ← back to course
              </Button>
            )}
            <Tooltip title="Rotate the teacher_token for this lesson. The current dashboard URL stops working immediately — useful if you accidentally screen-shared it. Hold Alt/Option to also rotate the join_code (students need the new one).">
              <Button
                size="small"
                variant="text"
                color="warning"
                onClick={(e) => handleRotateToken(e.altKey)}
                sx={{ ml: 'auto', fontSize: '0.72rem' }}
              >
                Rotate token
              </Button>
            </Tooltip>
            <Tooltip title="Permanently delete this lesson and all student data (sessions, attempts, submissions). Requires confirmation. Use when teaching ends or for a GDPR-style erasure request.">
              <Button
                size="small"
                variant="text"
                color="error"
                onClick={handleDeleteLesson}
                sx={{ fontSize: '0.72rem' }}
              >
                Delete all data
              </Button>
            </Tooltip>
          </Box>

          {rotateResult && (
            <Alert
              severity="success"
              onClose={() => setRotateResult(null)}
              sx={{ mb: 2, borderRadius: 1 }}
            >
              <Typography variant="body2" sx={{ fontWeight: 600, mb: 0.5 }}>
                Token rotated. Old dashboard URL is dead.
              </Typography>
              <Typography variant="caption" sx={{ display: 'block', mt: 0.5 }}>
                New dashboard URL:{' '}
                <Box component="code" sx={{ fontSize: '0.78rem' }}>
                  {window.location.origin}/teacher/live?token={rotateResult.token}
                </Box>
              </Typography>
              <Typography variant="caption" sx={{ display: 'block', mt: 0.25 }}>
                Join code: <code>{rotateResult.join_code}</code>
              </Typography>
            </Alert>
          )}

          {data.new_activity && !bannerDismissed && (
            <NewActivityBanner activity={data.new_activity} onDismiss={dismissBanner} showNames={showRoster} />
          )}
          <Box sx={{ mb: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 2 }}>
            <Box>
              {(() => {
                const show = {
                  current: countOf('current', data.scope_counts) > 0,
                  course: !!courseToken && countOf('course', data.scope_counts) > 0,
                  alltime: countOf('alltime', data.scope_counts) > 0,
                };
                const visibleCount = Number(show.current) + Number(show.course) + Number(show.alltime);
                if (visibleCount <= 1) return null;  // only one scope worth showing — hide the toggle entirely
                return (
                  <ToggleButtonGroup
                    size="small"
                    value={scope}
                    exclusive
                    onChange={(_e: any, next: LiveScope | null) => handleScope(next)}
                  >
                    {show.current && <ToggleButton value="current">Standalone joiners</ToggleButton>}
                    {show.course && <ToggleButton value="course">This course</ToggleButton>}
                    {show.alltime && <ToggleButton value="alltime">All-time (every course)</ToggleButton>}
                  </ToggleButtonGroup>
                );
              })()}
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Tooltip title="Master switch for student names: the roster panel, hover-revealed names on timing bars and wrong-answer rows. Off = a screen-share-safe dashboard.">
                <FormControlLabel
                  control={<Switch size="small" checked={showRoster} onChange={(e) => setShowRoster(e.target.checked)} />}
                  label={<Typography variant="body2">Show student roster</Typography>}
                  sx={{ mr: 1 }}
                />
              </Tooltip>
              <Tooltip title={
                showRoster
                  ? 'Inline list of students with the fewest and most attempts on each checkpoint — the only place names appear without a hover gesture. Off by default.'
                  : 'Turn on "Show student roster" first.'
              }>
                <FormControlLabel
                  control={
                    <Switch
                      size="small"
                      checked={showOutlierNames && showRoster}
                      disabled={!showRoster}
                      onChange={(e) => setShowOutlierNames(e.target.checked)}
                    />
                  }
                  label={<Typography variant="body2" color={showRoster ? 'inherit' : 'text.disabled'}>Show outlier names</Typography>}
                />
              </Tooltip>
              <Tooltip title={
                notifPermission === 'unsupported'
                  ? "Your browser doesn't support desktop notifications."
                  : notifPermission === 'denied'
                    ? 'Notifications blocked. Reset the site permission in your browser to re-enable.'
                    : 'Desktop notification when a student is actively stuck (3+ wrong attempts in 5 min with no correct answer). Tab can be in the background.'
              }>
                <FormControlLabel
                  control={
                    <Switch
                      size="small"
                      checked={notificationsEnabled && notifPermission === 'granted'}
                      disabled={notifPermission === 'unsupported' || notifPermission === 'denied'}
                      onChange={(e) => handleEnableNotifications(e.target.checked)}
                    />
                  }
                  label={
                    <Typography
                      variant="body2"
                      color={notifPermission === 'unsupported' || notifPermission === 'denied' ? 'text.disabled' : 'inherit'}
                    >
                      Stuck-student alerts
                    </Typography>
                  }
                />
              </Tooltip>
            </Box>
          </Box>
          <SummaryCard summary={data.summary} checkpoints={data.checkpoints} />
          {showRoster && data.student_roster.length > 0 && (
            <StudentRoster roster={data.student_roster} />
          )}
          {data.checkpoints.length === 0 ? (
            <Alert severity="info">No checkpoints registered for this lesson yet.</Alert>
          ) : (
            <OutlierNamesContext.Provider value={showOutlierNames && showRoster}>
              {(() => {
                const peerAvgs = data.checkpoints.map((c) => c.avg_attempts);
                const groups = groupCheckpointsBySection(data.checkpoints);
                return groups.map((grp, gi) => {
                  const cards = grp.items.map((cp) => (
                    <CheckpointCard
                      key={cp.checkpoint_id}
                      cp={cp}
                      peers={peerAvgs}
                      roster={data.student_roster}
                      teacherToken={activeToken!}
                      showRoster={showRoster}
                    />
                  ));
                  if (grp.section === null) {
                    return <React.Fragment key={`flat-${gi}`}>{cards}</React.Fragment>;
                  }
                  const totalAttempts = grp.items.reduce((a, b) => a + b.total_attempts, 0);
                  const solved = grp.items.reduce((a, b) => a + b.solved, 0);
                  const attempted = grp.items.reduce((a, b) => a + b.attempted, 0);
                  return (
                    <SectionGroup
                      key={`sec-${grp.section}-${gi}`}
                      section={grp.section}
                      items={grp.items}
                      totalAttempts={totalAttempts}
                      solved={solved}
                      attempted={attempted}
                    >
                      {cards}
                    </SectionGroup>
                  );
                });
              })()}
            </OutlierNamesContext.Provider>
          )}
        </ShowNamesContext.Provider>
      )}
    </Box>
  );
}
