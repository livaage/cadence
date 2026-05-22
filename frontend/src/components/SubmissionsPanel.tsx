import React, { useEffect, useState } from 'react';
import { Box, Typography, IconButton, Collapse, Tooltip } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
// @ts-ignore — module ships JS at .esm.js, types only cover the named export
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { getCheckpointSubmissions, CodeSubmissionEntry } from '../services/api';

function formatRelative(iso: string): string {
  const t = new Date(iso).getTime();
  const diffSec = Math.max(0, (Date.now() - t) / 1000);
  if (diffSec < 60) return 'just now';
  if (diffSec < 3600) return `${Math.round(diffSec / 60)} min ago`;
  if (diffSec < 86400) return `${Math.round(diffSec / 3600)} hr ago`;
  return new Date(iso).toLocaleString();
}

interface Props {
  teacherToken: string;
  checkpointId: string;
  count: number;
  showNames: boolean;
}

interface RowProps {
  sub: CodeSubmissionEntry;
  showNames: boolean;
  defaultOpen: boolean;
  onCopy: (code: string | null) => void;
}

function SubmissionRow({ sub, showNames, defaultOpen, onCopy }: RowProps) {
  const [open, setOpen] = useState(defaultOpen);
  const hasImage = !!sub.image_data_b64;
  const hasCode = !!sub.code;
  return (
    <Box>
      {/* Header — plain inline row, no background strip */}
      <Box
        onClick={() => setOpen((o) => !o)}
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          py: 1,
          cursor: 'pointer',
          '&:hover .submission-name': { color: 'primary.main' },
        }}
      >
        <Box
          className="submission-name"
          component="span"
          sx={{
            fontWeight: 500,
            fontSize: '0.88rem',
            transition: 'color 120ms',
          }}
        >
          {showNames && sub.display_name ? sub.display_name : 'anonymous'}
        </Box>
        <Typography variant="caption" color="text.disabled" sx={{ flexGrow: 1 }}>
          · {formatRelative(sub.submitted_at)}{' '}
          {hasImage && hasCode ? '· plot + code' : hasImage ? '· plot' : '· code'}
        </Typography>
        {hasCode && (
          <Tooltip title="Copy code to clipboard">
            <IconButton
              size="small"
              onClick={(e) => { e.stopPropagation(); onCopy(sub.code); }}
              sx={{ opacity: 0.6, '&:hover': { opacity: 1 } }}
            >
              <ContentCopyIcon fontSize="inherit" sx={{ fontSize: '0.95rem' }} />
            </IconButton>
          </Tooltip>
        )}
        <IconButton size="small" aria-label="toggle submission" sx={{ p: 0.25 }}>
          {open ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
        </IconButton>
      </Box>
      <Collapse in={open} unmountOnExit>
        <Box sx={{ pb: 1.5 }}>
          {hasImage && (
            <Box
              sx={{
                background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)',
                borderRadius: 1,
                p: 2,
                display: 'flex',
                justifyContent: 'center',
                mb: hasCode ? 1 : 0,
              }}
            >
              <img
                src={`data:${sub.image_mime || 'image/png'};base64,${sub.image_data_b64}`}
                alt={`Submission from ${sub.display_name || 'anonymous'}`}
                style={{
                  maxWidth: '100%',
                  maxHeight: 540,
                  borderRadius: 4,
                  boxShadow:
                    '0 4px 12px rgba(0, 0, 0, 0.25), 0 1px 2px rgba(0, 0, 0, 0.3)',
                  display: 'block',
                }}
              />
            </Box>
          )}
          {hasCode && (
            <Box sx={{ borderRadius: 1, overflow: 'hidden' }}>
              <SyntaxHighlighter
                language={sub.language || 'python'}
                style={vscDarkPlus}
                customStyle={{ margin: 0, fontSize: '0.82em', padding: 12, lineHeight: 1.5 }}
                wrapLongLines
              >
                {sub.code as string}
              </SyntaxHighlighter>
            </Box>
          )}
        </Box>
      </Collapse>
    </Box>
  );
}

const SubmissionsPanel: React.FC<Props> = ({ teacherToken, checkpointId, count, showNames }) => {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<CodeSubmissionEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    getCheckpointSubmissions(teacherToken, checkpointId)
      .then((data) => { if (!cancelled) setItems(data); })
      .catch((e) => { if (!cancelled) setError(e?.message || 'Failed to load'); });
    return () => { cancelled = true; };
  }, [open, teacherToken, checkpointId]);

  const copy = (code: string | null) => {
    if (!code) return;
    navigator.clipboard?.writeText(code).catch(() => {});
  };

  // Flat layout, no nested cards. A single top divider, then a stream of rows
  // separated by hairlines. Only the first row is open by default — the rest
  // are headers-only so the teacher can scan names + relative timestamps quickly.
  return (
    <Box sx={{ mt: 2, pt: 1.5, borderTop: '1px solid', borderColor: 'divider' }}>
      <Box
        onClick={() => setOpen((o) => !o)}
        sx={{
          display: 'flex', alignItems: 'center', gap: 0.5,
          cursor: 'pointer', mb: open ? 1 : 0,
          '&:hover': { color: 'primary.main' },
        }}
      >
        <IconButton size="small" sx={{ p: 0.25 }} aria-label="toggle submissions">
          {open ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
        </IconButton>
        <Typography
          variant="caption"
          sx={{
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
            fontSize: '0.7rem',
            fontWeight: 600,
            color: 'inherit',
          }}
        >
          Submissions ({count})
        </Typography>
        {!open && count > 0 && (
          <Typography variant="caption" color="text.disabled" sx={{ ml: 1 }}>
            click to view {count === 1 ? 'the submission' : 'all submissions'}
          </Typography>
        )}
      </Box>
      <Collapse in={open} unmountOnExit>
        {error && <Typography variant="body2" color="error">{error}</Typography>}
        {!items && !error && <Typography variant="body2" color="text.secondary">Loading…</Typography>}
        {items && items.length === 0 && (
          <Typography variant="body2" color="text.secondary">No submissions yet.</Typography>
        )}
        {items && items.length > 0 && (
          <Box sx={{
            '& > div': { borderBottom: '1px solid', borderColor: 'divider' },
            '& > div:last-of-type': { borderBottom: 'none' },
          }}>
            {items.map((sub, i) => (
              <SubmissionRow
                key={sub.id}
                sub={sub}
                showNames={showNames}
                defaultOpen={i === 0}
                onCopy={copy}
              />
            ))}
          </Box>
        )}
      </Collapse>
    </Box>
  );
};

export default SubmissionsPanel;
