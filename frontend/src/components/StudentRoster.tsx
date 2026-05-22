import React, { useMemo, useState } from 'react';
import {
  Card,
  CardContent,
  Typography,
  TextField,
  Box,
  Chip,
  IconButton,
  Collapse,
  Stack,
  InputAdornment,
  Tooltip,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import SearchIcon from '@mui/icons-material/Search';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import RadioButtonUncheckedIcon from '@mui/icons-material/RadioButtonUnchecked';
import type { StudentRosterEntry, StudentCheckpointDetail, AttemptLogEntry } from '../services/api';

function fmtMs(ms: number | null): string {
  if (ms == null) return '—';
  if (ms < 1000) return `${ms} ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)} s`;
  return `${(ms / 60_000).toFixed(1)} min`;
}

function StatusIcon({ status }: { status: StudentCheckpointDetail['status'] }) {
  if (status === 'solved') return <CheckCircleIcon fontSize="small" color="success" />;
  if (status === 'attempted') return <HelpOutlineIcon fontSize="small" color="warning" />;
  return <RadioButtonUncheckedIcon fontSize="small" sx={{ color: 'text.disabled' }} />;
}

function parseLabel_(checkpointId: string): string {
  const lastDot = checkpointId.lastIndexOf('.');
  const lastSlash = checkpointId.lastIndexOf('/');
  const sep = Math.max(lastDot, lastSlash);
  if (sep <= 0 || sep >= checkpointId.length - 1) return checkpointId;
  return checkpointId.substring(sep + 1);
}

function formatTime(iso: string): string {
  const t = new Date(iso);
  return `${t.getHours().toString().padStart(2, '0')}:${t.getMinutes().toString().padStart(2, '0')}:${t.getSeconds().toString().padStart(2, '0')}`;
}

function ChronologyView({ chronology }: { chronology: AttemptLogEntry[] }) {
  // chronology is reverse-chronological; show oldest first for readability.
  const ordered = [...chronology].reverse();
  return (
    <Box>
      <Typography
        variant="caption"
        sx={{ display: 'block', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600, color: 'text.secondary', mb: 0.75 }}
      >
        Chronology ({chronology.length}{chronology.length === 50 ? '+' : ''})
      </Typography>
      <Box
        sx={{
          borderLeft: '2px solid',
          borderColor: 'divider',
          pl: 1.5,
          maxHeight: 220,
          overflowY: 'auto',
        }}
      >
        {ordered.map((e, i) => (
          <Box key={i} sx={{ display: 'flex', alignItems: 'center', gap: 1, py: 0.25, fontSize: '0.78rem' }}>
            {e.is_correct ? (
              <CheckCircleIcon fontSize="inherit" color="success" />
            ) : (
              <HelpOutlineIcon fontSize="inherit" color="warning" />
            )}
            <Box component="code" sx={{ fontFamily: '"JetBrains Mono", monospace', fontSize: '0.72rem', color: 'text.secondary', minWidth: 140 }}>
              {parseLabel_(e.checkpoint_id)}
            </Box>
            <Box
              component="code"
              sx={{
                fontFamily: '"JetBrains Mono", monospace',
                fontSize: '0.72rem',
                color: e.is_correct ? 'success.main' : 'text.primary',
                fontWeight: e.is_correct ? 600 : 400,
                maxWidth: 200,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {e.submitted_value ?? '(empty)'}
            </Box>
            <Typography variant="caption" sx={{ color: 'text.disabled', flexGrow: 1 }}>
              attempt #{e.attempt_num}
              {e.elapsed_ms != null && ` · ${e.elapsed_ms < 1000 ? `${e.elapsed_ms}ms` : `${(e.elapsed_ms / 1000).toFixed(1)}s`}`}
            </Typography>
            <Typography variant="caption" sx={{ color: 'text.disabled', fontFamily: '"JetBrains Mono", monospace', fontSize: '0.68rem' }}>
              {formatTime(e.created_at)}
            </Typography>
          </Box>
        ))}
      </Box>
    </Box>
  );
}

function parseLabel(checkpointId: string): string {
  const lastDot = checkpointId.lastIndexOf('.');
  const lastSlash = checkpointId.lastIndexOf('/');
  const sep = Math.max(lastDot, lastSlash);
  if (sep <= 0 || sep >= checkpointId.length - 1) return checkpointId;
  return checkpointId.substring(sep + 1);
}

function StudentRow({ entry }: { entry: StudentRosterEntry }) {
  const [open, setOpen] = useState(false);
  const total = entry.per_checkpoint.length;
  const fullySolved = entry.checkpoints_solved === total && total > 0;
  return (
    <Box sx={{ borderBottom: '1px solid', borderColor: 'divider', py: 0.75, px: 1 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25 }}>
        <IconButton size="small" onClick={() => setOpen((o) => !o)} aria-label="expand" sx={{ p: 0.5 }}>
          {open ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
        </IconButton>
        <Typography sx={{ flexGrow: 1, fontWeight: 500, fontSize: '0.9rem' }}>
          {entry.display_name}
        </Typography>
        {entry.current_checkpoint_id && (
          <Tooltip title="Most recent attempt — where they are right now">
            <Chip
              size="small"
              label={parseLabel(entry.current_checkpoint_id)}
              variant="outlined"
              sx={{
                fontFamily: '"JetBrains Mono", monospace',
                fontSize: '0.72rem',
                color: 'primary.main',
                borderColor: 'primary.main',
                backgroundColor: '#e6f5f3',
                height: 22,
              }}
            />
          </Tooltip>
        )}
        <Typography
          variant="caption"
          sx={{
            color: fullySolved ? 'success.main' : 'text.secondary',
            fontWeight: fullySolved ? 600 : 500,
            fontVariantNumeric: 'tabular-nums',
            minWidth: 70,
            textAlign: 'right',
          }}
        >
          {entry.checkpoints_solved}/{total} solved
        </Typography>
        <Typography variant="caption" sx={{ color: 'text.disabled', fontVariantNumeric: 'tabular-nums', minWidth: 70, textAlign: 'right' }}>
          {entry.total_attempts} tries
        </Typography>
        <Typography variant="caption" sx={{ color: 'text.disabled', fontVariantNumeric: 'tabular-nums', minWidth: 80, textAlign: 'right' }}>
          {entry.fastest_elapsed_ms != null ? `⚡ ${fmtMs(entry.fastest_elapsed_ms)}` : ''}
        </Typography>
      </Box>
      <Collapse in={open} unmountOnExit>
        <Box sx={{ pl: 5, pt: 1, pb: 1.5 }}>
          <Typography
            variant="caption"
            sx={{ display: 'block', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600, color: 'text.secondary', mb: 0.75 }}
          >
            Per checkpoint
          </Typography>
          <Stack spacing={0.5} sx={{ mb: 1.5 }}>
            {entry.per_checkpoint.map((cp) => (
              <Box key={cp.checkpoint_id} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <StatusIcon status={cp.status} />
                <Box component="code" sx={{ minWidth: 180, fontFamily: '"JetBrains Mono", monospace', fontSize: '0.78rem' }}>
                  {cp.checkpoint_id}
                </Box>
                <Typography variant="caption" color="text.secondary" sx={{ flexGrow: 1 }}>
                  {cp.status === 'solved'
                    ? `solved on attempt ${cp.first_correct_attempt} · ${fmtMs(cp.elapsed_ms_first_correct)}`
                    : cp.status === 'attempted'
                      ? `${cp.attempts} wrong attempt${cp.attempts === 1 ? '' : 's'}, no correct yet`
                      : 'not yet attempted'}
                </Typography>
              </Box>
            ))}
          </Stack>
          {entry.chronology && entry.chronology.length > 0 && (
            <ChronologyView chronology={entry.chronology} />
          )}
        </Box>
      </Collapse>
    </Box>
  );
}

const StudentRoster: React.FC<{ roster: StudentRosterEntry[] }> = ({ roster }) => {
  const [filter, setFilter] = useState('');
  const [open, setOpen] = useState(false);

  const filtered = useMemo(() => {
    const needle = filter.trim().toLowerCase();
    if (!needle) return roster;
    return roster.filter((r) => r.display_name.toLowerCase().includes(needle));
  }, [roster, filter]);

  return (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box
            sx={{ display: 'flex', alignItems: 'center', gap: 1, cursor: 'pointer', flexGrow: 1 }}
            onClick={() => setOpen((o) => !o)}
          >
            <IconButton size="small" aria-label="toggle roster">
              {open ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
            <Typography variant="h6">Roster ({roster.length})</Typography>
            {!open && (
              <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                click to expand
              </Typography>
            )}
          </Box>
          {open && (
            <TextField
              size="small"
              placeholder="filter by name…"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              sx={{ width: 240 }}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon fontSize="small" />
                  </InputAdornment>
                ),
              }}
            />
          )}
        </Box>
        <Collapse in={open} unmountOnExit>
          <Box sx={{ mt: 1 }}>
            {filtered.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                {roster.length === 0 ? 'No students yet.' : 'No matches.'}
              </Typography>
            ) : (
              filtered.map((r) => <StudentRow key={r.session_id} entry={r} />)
            )}
          </Box>
        </Collapse>
      </CardContent>
    </Card>
  );
};

export default StudentRoster;
