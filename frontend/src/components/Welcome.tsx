import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Stack,
  InputAdornment,
  Chip,
  Grid,
} from '@mui/material';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import VpnKeyIcon from '@mui/icons-material/VpnKey';
import CodeIcon from '@mui/icons-material/Code';
import Logo from './Logo';

// Two-panel value-prop block matching the deck. Left column is the
// in-class "communication" pitch (warm terracotta accent — same hex the
// dashboard uses for timing); right column is the longitudinal "improving
// teaching" pitch (teal accent — same hex as the attempts histogram bar).
// Keeping the colour vocabulary consistent across deck + dashboard helps
// teachers anchor on the same mental model when they switch contexts.
const VALUE_PROPS = [
  {
    eyebrow: 'In the moment',
    accent: '#D17753',
    title: 'Improved communication',
    bullets: [
      'Pace your lessons perfectly',
      "See who's stuck in real time",
      'Showcase solutions without pushing files',
      'Monitor student understanding and quick-patch gaps',
      "Optional auto-hints when they're stuck",
      'Built-in solutions after N attempts, no second notebook',
    ],
  },
  {
    eyebrow: 'Over time',
    accent: '#2BA89E',
    title: 'Improving teaching',
    bullets: [
      'Measure your lesson effectiveness',
      'Measure how hard your sessions really are',
      'Surface the common wrong answers',
      'Compare solutions across students',
      'Spot AI use, copy-paste, convergent approaches',
    ],
  },
];

const ValueCard: React.FC<typeof VALUE_PROPS[number]> = ({ eyebrow, accent, title, bullets }) => (
  <Card
    sx={{
      height: '100%',
      bgcolor: '#f5f4ef',
      borderLeft: `4px solid ${accent}`,
      boxShadow: 'none',
      border: '1px solid',
      borderColor: 'divider',
      borderLeftWidth: 4,
      borderLeftColor: accent,
    }}
  >
    <CardContent sx={{ p: { xs: 2.5, sm: 3 } }}>
      <Typography
        sx={{
          color: accent,
          fontSize: '0.7rem',
          fontWeight: 700,
          letterSpacing: '0.18em',
          textTransform: 'uppercase',
          mb: 1.5,
        }}
      >
        {eyebrow}
      </Typography>
      <Typography
        variant="h5"
        component="h3"
        sx={{
          fontWeight: 600,
          letterSpacing: '-0.01em',
          mb: 2,
          fontSize: { xs: '1.35rem', sm: '1.5rem' },
        }}
      >
        {title}
      </Typography>
      <Box component="ul" sx={{ pl: 2.5, m: 0 }}>
        {bullets.map((b) => (
          <Typography
            key={b}
            component="li"
            variant="body2"
            sx={{ mb: 0.75, lineHeight: 1.55, color: 'text.primary' }}
          >
            {b}
          </Typography>
        ))}
      </Box>
    </CardContent>
  </Card>
);

function extractToken(input: string): string {
  const trimmed = input.trim();
  try {
    const url = new URL(trimmed);
    const t = url.searchParams.get('token');
    if (t) return t;
  } catch {
    // not a URL, treat as bare token
  }
  return trimmed;
}

const Welcome: React.FC = () => {
  const navigate = useNavigate();
  const [tokenInput, setTokenInput] = useState('');

  const openDashboard = (e?: React.FormEvent) => {
    e?.preventDefault();
    const token = extractToken(tokenInput);
    if (!token) return;
    navigate(`/teacher/live?token=${encodeURIComponent(token)}`);
  };

  return (
    <Stack spacing={3.5} sx={{ maxWidth: 900, mx: 'auto', pt: 6 }}>
      <Box sx={{ textAlign: 'center', mb: 2 }}>
        <Box sx={{ mb: 3, display: 'flex', justifyContent: 'center' }}>
          <Logo height={80} wordmarkColor="#1c1917" />
        </Box>
        <Typography
          variant="h3"
          component="h1"
          sx={{ fontWeight: 700, letterSpacing: '-0.02em', fontSize: { xs: '1.8rem', sm: '2.2rem' } }}
        >
          Live student{' '}
          <Box component="span" sx={{ color: 'primary.main' }}>progress</Box>
          {' '}for Jupyter teaching.
        </Typography>
        <Typography
          variant="body1"
          color="text.secondary"
          sx={{ mt: 2.5, fontSize: '1.05rem', maxWidth: 520, mx: 'auto' }}
        >
          Drop two lines into any notebook and watch the class solve in{' '}
          <Box component="span" sx={{ color: 'secondary.main', fontWeight: 500 }}>real time</Box>
          {' '}— per-checkpoint solve rates, common wrong answers, who needs help.
        </Typography>
      </Box>

      <Grid container spacing={2.5}>
        {VALUE_PROPS.map((vp) => (
          <Grid item xs={12} md={6} key={vp.eyebrow}>
            <ValueCard {...vp} />
          </Grid>
        ))}
      </Grid>

      <Card>
        <CardContent>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
            <VpnKeyIcon color="primary" />
            <Typography variant="h6">Have a teacher token?</Typography>
          </Stack>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Paste your teacher token, or the full dashboard URL. Opens straight to your live dashboard — no password required.
          </Typography>
          <Box component="form" onSubmit={openDashboard}>
            <TextField
              fullWidth
              placeholder="paste teacher token here"
              value={tokenInput}
              onChange={(e) => setTokenInput(e.target.value)}
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <Button
                      type="submit"
                      variant="contained"
                      endIcon={<ArrowForwardIcon />}
                      disabled={!tokenInput.trim()}
                    >
                      Open
                    </Button>
                  </InputAdornment>
                ),
              }}
            />
          </Box>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
            <CodeIcon color="primary" />
            <Typography variant="h6">New to Cadence?</Typography>
          </Stack>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Install the Jupyter extension, then run two lines in any notebook. Cadence will mint your dashboard URL and print it inline.
          </Typography>
          <Box
            component="pre"
            sx={{
              p: 2.5,
              borderRadius: 1.5,
              bgcolor: '#0f172a',
              color: '#e2e8f0',
              overflow: 'auto',
              fontSize: '0.85rem',
              lineHeight: 1.7,
              m: 0,
            }}
          >
{`pip install cadence-edu
cadence-cli new teacher --name "Week 3: Fibonacci"
# (or write the cells yourself)

%load_ext cadence
%cadence_create_lesson "Week 3: Fibonacci"`}
          </Box>
        </CardContent>
      </Card>

      <Box sx={{ textAlign: 'center', pb: 4 }}>
        <Stack direction="row" spacing={1.5} justifyContent="center" sx={{ flexWrap: 'wrap', gap: 1 }}>
          <Chip
            label="What is Cadence?"
            clickable
            onClick={() => navigate('/about')}
            variant="outlined"
          />
          <Chip
            label="See a real lesson"
            clickable
            onClick={() => navigate('/demo')}
            color="primary"
          />
          <Chip
            label="Setup guide"
            clickable
            onClick={() => navigate('/guide')}
            variant="outlined"
          />
          <Chip
            label="My library"
            clickable
            onClick={() => navigate('/teacher/library')}
            variant="outlined"
          />
        </Stack>
        <Typography variant="caption" display="block" color="text.disabled" sx={{ mt: 1.5 }}>
          Library is per-browser for now; cross-device sync lands with teacher accounts.
        </Typography>
      </Box>
    </Stack>
  );
};

export default Welcome;
