import React, { useEffect, useMemo, useState } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Stack,
  Tabs,
  Tab,
  Chip,
  Divider,
  CircularProgress,
  Link as MuiLink,
  Button,
} from '@mui/material';
import LaunchIcon from '@mui/icons-material/Launch';
import VisibilityIcon from '@mui/icons-material/Visibility';
import { Link as RouterLink } from 'react-router-dom';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

// Stable token + join code seeded by backend/seed_demo.py. Anyone who opens this
// URL sees the read-only teacher dashboard for the demo lesson — no signup.
const DEMO_TEACHER_TOKEN = 'demo-particle-physics-readonly-2026';
const DEMO_JOIN_CODE = 'demo-physics';
const DEMO_DASHBOARD_URL = `/teacher/live?token=${DEMO_TEACHER_TOKEN}`;

type NotebookCell = {
  cell_type: 'markdown' | 'code' | string;
  source: string[] | string;
};

type Notebook = {
  cells: NotebookCell[];
};

type DemoSpec = {
  slug: string;
  title: string;
  subtitle: string;
  file: string;
  badge: 'student' | 'teacher' | 'plain';
};

const DEMOS: DemoSpec[] = [
  {
    slug: 'before',
    title: 'Before Cadence',
    subtitle: 'A vanilla student notebook — no tracking, no dashboard.',
    file: '/demos/demo-before-cadence.ipynb',
    badge: 'plain',
  },
  {
    slug: 'with',
    title: 'With Cadence (student)',
    subtitle: 'Same lab, two extra lines. Progress goes to the live dashboard.',
    file: '/demos/demo-with-cadence.ipynb',
    badge: 'student',
  },
  {
    slug: 'teacher',
    title: 'Teacher setup',
    subtitle: 'Run once to mint the lesson, register checkpoints, and print the join code.',
    file: '/demos/demo-teacher-setup.ipynb',
    badge: 'teacher',
  },
];

function joinSource(src: string[] | string): string {
  return Array.isArray(src) ? src.join('') : src;
}

const InlineMd: React.FC<{ text: string }> = ({ text }) => {
  // Bold **x**, italic *x*, inline code `x`. Order matters.
  const parts: Array<string | React.ReactNode> = [];
  let remaining = text;
  let key = 0;
  const pattern = /(\*\*[^*]+\*\*|`[^`]+`|\*[^*\n]+\*|\[[^\]]+\]\([^)]+\))/;
  while (remaining.length > 0) {
    const m = remaining.match(pattern);
    if (!m || m.index === undefined) {
      parts.push(remaining);
      break;
    }
    if (m.index > 0) parts.push(remaining.slice(0, m.index));
    const token = m[0];
    if (token.startsWith('**')) {
      parts.push(<strong key={key++}>{token.slice(2, -2)}</strong>);
    } else if (token.startsWith('`')) {
      parts.push(
        <Box
          key={key++}
          component="code"
          sx={{
            fontFamily: '"JetBrains Mono", Menlo, monospace',
            fontSize: '0.85em',
            bgcolor: 'rgba(15, 23, 42, 0.06)',
            px: 0.6,
            py: 0.2,
            borderRadius: 0.5,
          }}
        >
          {token.slice(1, -1)}
        </Box>,
      );
    } else if (token.startsWith('[')) {
      const linkMatch = token.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
      if (linkMatch) {
        parts.push(
          <MuiLink key={key++} href={linkMatch[2]} target="_blank" rel="noopener">
            {linkMatch[1]}
          </MuiLink>,
        );
      } else {
        parts.push(token);
      }
    } else {
      // single-* italic
      parts.push(<em key={key++}>{token.slice(1, -1)}</em>);
    }
    remaining = remaining.slice(m.index + token.length);
  }
  return <>{parts}</>;
};

const Markdown: React.FC<{ source: string }> = ({ source }) => {
  // Split into blocks separated by blank lines; treat $$ blocks specially.
  const lines = source.split('\n');
  const blocks: React.ReactNode[] = [];
  let i = 0;
  let key = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Math block: $$...$$ spanning multiple lines (possibly inline single line).
    if (line.trim().startsWith('$$')) {
      const collected: string[] = [];
      // first line may be just "$$" or "$$ x $$".
      const first = line.trim();
      if (first.length > 2 && first.endsWith('$$') && first !== '$$') {
        collected.push(first.slice(2, -2).trim());
        i++;
      } else {
        // multi-line block
        collected.push(first.slice(2).trim());
        i++;
        while (i < lines.length && !lines[i].trim().endsWith('$$')) {
          collected.push(lines[i]);
          i++;
        }
        if (i < lines.length) {
          collected.push(lines[i].trim().slice(0, -2).trim());
          i++;
        }
      }
      blocks.push(
        <Box
          key={key++}
          sx={{
            my: 1.5,
            p: 1.5,
            borderRadius: 1,
            bgcolor: 'rgba(15, 23, 42, 0.04)',
            fontFamily: '"JetBrains Mono", Menlo, monospace',
            fontSize: '0.9rem',
            whiteSpace: 'pre-wrap',
            overflowX: 'auto',
          }}
        >
          {collected.filter((l) => l !== '').join('\n')}
        </Box>,
      );
      continue;
    }

    // Heading
    const h = line.match(/^(#{1,6})\s+(.*)$/);
    if (h) {
      const level = h[1].length;
      const text = h[2];
      const variant = level === 1 ? 'h4' : level === 2 ? 'h5' : level === 3 ? 'h6' : 'subtitle1';
      const fontSize = level === 1 ? '1.7rem' : level === 2 ? '1.3rem' : level === 3 ? '1.1rem' : '1rem';
      blocks.push(
        <Typography
          key={key++}
          variant={variant as any}
          sx={{ mt: level === 1 ? 1 : 2.5, mb: 1, fontWeight: 600, fontSize, letterSpacing: '-0.01em' }}
        >
          <InlineMd text={text} />
        </Typography>,
      );
      i++;
      continue;
    }

    // Blank line → paragraph break
    if (line.trim() === '') {
      i++;
      continue;
    }

    // Unordered list
    if (/^\s*[-*]\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*[-*]\s+/, ''));
        i++;
      }
      blocks.push(
        <Box component="ul" key={key++} sx={{ pl: 3, my: 1 }}>
          {items.map((it, idx) => (
            <Typography component="li" variant="body2" key={idx} sx={{ mb: 0.5, lineHeight: 1.7 }}>
              <InlineMd text={it} />
            </Typography>
          ))}
        </Box>,
      );
      continue;
    }

    // Ordered list
    if (/^\s*\d+\.\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*\d+\.\s+/, ''));
        i++;
      }
      blocks.push(
        <Box component="ol" key={key++} sx={{ pl: 3, my: 1 }}>
          {items.map((it, idx) => (
            <Typography component="li" variant="body2" key={idx} sx={{ mb: 0.5, lineHeight: 1.7 }}>
              <InlineMd text={it} />
            </Typography>
          ))}
        </Box>,
      );
      continue;
    }

    // Paragraph: collect consecutive non-empty, non-special lines
    const paraLines: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() !== '' &&
      !lines[i].match(/^(#{1,6})\s+/) &&
      !/^\s*[-*]\s+/.test(lines[i]) &&
      !/^\s*\d+\.\s+/.test(lines[i]) &&
      !lines[i].trim().startsWith('$$')
    ) {
      paraLines.push(lines[i]);
      i++;
    }
    blocks.push(
      <Typography key={key++} variant="body2" sx={{ my: 1, lineHeight: 1.75, fontSize: '0.95rem' }}>
        <InlineMd text={paraLines.join(' ')} />
      </Typography>,
    );
  }

  return <>{blocks}</>;
};

const CodeCell: React.FC<{ source: string }> = ({ source }) => (
  <Box
    sx={{
      borderRadius: 1.5,
      overflow: 'hidden',
      my: 1.5,
      border: '1px solid',
      borderColor: 'divider',
      '& pre': {
        margin: '0 !important',
        background: '#0f172a !important',
        fontFamily: '"JetBrains Mono", Menlo, monospace !important',
        fontSize: '0.84rem !important',
        lineHeight: '1.6 !important',
      },
    }}
  >
    <SyntaxHighlighter
      language="python"
      style={oneDark}
      customStyle={{ margin: 0, padding: '14px 18px', background: '#0f172a' }}
      codeTagProps={{ style: { fontFamily: '"JetBrains Mono", Menlo, monospace' } }}
    >
      {source.replace(/\n$/, '')}
    </SyntaxHighlighter>
  </Box>
);

const BadgeChip: React.FC<{ kind: DemoSpec['badge'] }> = ({ kind }) => {
  if (kind === 'student')
    return <Chip size="small" label="Student notebook" color="primary" variant="outlined" />;
  if (kind === 'teacher')
    return <Chip size="small" label="Teacher notebook" color="secondary" variant="outlined" />;
  return <Chip size="small" label="Vanilla notebook" variant="outlined" />;
};

const NotebookView: React.FC<{ spec: DemoSpec }> = ({ spec }) => {
  const [nb, setNb] = useState<Notebook | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setNb(null);
    setErr(null);
    fetch(spec.file)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => {
        if (!cancelled) setNb(data);
      })
      .catch((e) => {
        if (!cancelled) setErr(String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [spec.file]);

  if (err)
    return (
      <Typography variant="body2" color="error">
        Could not load notebook: {err}
      </Typography>
    );
  if (!nb)
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
        <CircularProgress size={28} />
      </Box>
    );

  return (
    <Box>
      <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 1 }}>
        <BadgeChip kind={spec.badge} />
        <Typography variant="caption" color="text.secondary">
          {nb.cells.length} cells ·{' '}
          <MuiLink href={spec.file} download underline="hover">
            download .ipynb
          </MuiLink>
        </Typography>
      </Stack>
      <Typography variant="h5" sx={{ fontWeight: 700, mb: 0.5 }}>
        {spec.title}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {spec.subtitle}
      </Typography>
      <Divider sx={{ mb: 3 }} />
      <Box>
        {nb.cells.map((cell, idx) => {
          const src = joinSource(cell.source);
          if (cell.cell_type === 'markdown') return <Markdown key={idx} source={src} />;
          if (cell.cell_type === 'code') return <CodeCell key={idx} source={src} />;
          return null;
        })}
      </Box>
    </Box>
  );
};

const Demo: React.FC = () => {
  const [tab, setTab] = useState(0);
  const spec = useMemo(() => DEMOS[tab], [tab]);

  return (
    <Box sx={{ maxWidth: 880, mx: 'auto', pb: 8 }}>
      <Box sx={{ textAlign: 'center', mb: 4 }}>
        <Typography
          variant="h3"
          component="h1"
          sx={{ fontWeight: 700, letterSpacing: '-0.02em', fontSize: { xs: '1.8rem', sm: '2.2rem' }, mb: 1 }}
        >
          See it in a real lesson
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ maxWidth: 600, mx: 'auto' }}>
          A particle-physics lab in three notebooks, plus a live teacher
          dashboard pre-populated with student activity. Everything below is
          public — no signup required.
        </Typography>
      </Box>

      <Card
        sx={{
          mb: 3,
          border: '1px solid',
          borderColor: 'primary.main',
          background: 'linear-gradient(135deg, rgba(37, 99, 235, 0.06), rgba(37, 99, 235, 0.02))',
        }}
      >
        <CardContent sx={{ p: { xs: 2.5, sm: 3.5 } }}>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2.5} alignItems={{ sm: 'center' }}>
            <Box sx={{ flexGrow: 1 }}>
              <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                <VisibilityIcon color="primary" fontSize="small" />
                <Typography variant="overline" color="primary.main" sx={{ fontWeight: 600, letterSpacing: '0.08em' }}>
                  Live demo dashboard
                </Typography>
              </Stack>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5 }}>
                Open the teacher view for this lab
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Fourteen seeded students worked through the notebook. See per-checkpoint
                solve rates, common wrong answers, stuck-student alerts, and the code-submission
                feed — exactly what you'd see during a class.
              </Typography>
              <Typography variant="caption" color="text.disabled" sx={{ display: 'block', mt: 1 }}>
                Join code <Box component="code" sx={{ fontFamily: '"JetBrains Mono", Menlo, monospace' }}>{DEMO_JOIN_CODE}</Box> is
                also live — paste it into the student notebook to add yourself to the dashboard.
              </Typography>
            </Box>
            <Button
              variant="contained"
              endIcon={<LaunchIcon />}
              component={RouterLink as any}
              to={DEMO_DASHBOARD_URL}
              size="large"
              sx={{ flexShrink: 0, alignSelf: { sm: 'center' } }}
            >
              Open dashboard
            </Button>
          </Stack>
        </CardContent>
      </Card>

      <Divider sx={{ mb: 3 }}>
        <Typography variant="caption" color="text.secondary" sx={{ px: 1.5 }}>
          The notebooks
        </Typography>
      </Divider>

      <Card sx={{ mb: 3 }}>
        <Tabs
          value={tab}
          onChange={(_, v) => setTab(v)}
          variant="fullWidth"
          sx={{ borderBottom: '1px solid', borderColor: 'divider' }}
        >
          {DEMOS.map((d) => (
            <Tab key={d.slug} label={d.title} sx={{ textTransform: 'none', fontWeight: 500 }} />
          ))}
        </Tabs>
        <CardContent sx={{ p: { xs: 2.5, sm: 4 } }}>
          <NotebookView spec={spec} />
        </CardContent>
      </Card>

      <Box sx={{ textAlign: 'center', mt: 4 }}>
        <Stack direction="row" spacing={1.5} justifyContent="center" sx={{ flexWrap: 'wrap', gap: 1 }}>
          <Chip
            label="Setup guide"
            clickable
            component={RouterLink as any}
            to="/guide"
            color="primary"
          />
          <Chip
            label="What is Cadence?"
            clickable
            component={RouterLink as any}
            to="/about"
            variant="outlined"
          />
          <Chip
            label="Create an account"
            clickable
            component={RouterLink as any}
            to="/signup"
            variant="outlined"
          />
        </Stack>
      </Box>
    </Box>
  );
};

export default Demo;
