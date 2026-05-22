import React from 'react';
import { Box, Typography, Card, CardContent, Grid, Chip, Stack, Divider } from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import Logo from './Logo';

const SectionLabel: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <Typography
    variant="caption"
    sx={{
      display: 'block',
      color: 'text.secondary',
      textTransform: 'uppercase',
      letterSpacing: '0.08em',
      fontSize: '0.72rem',
      fontWeight: 600,
      mb: 2,
    }}
  >
    {children}
  </Typography>
);

const MetricCard: React.FC<{ title: string; body: string }> = ({ title, body }) => (
  <Card sx={{ height: '100%' }}>
    <CardContent>
      <Typography sx={{ fontWeight: 600, fontSize: '0.95rem', mb: 0.5 }}>{title}</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.55 }}>
        {body}
      </Typography>
    </CardContent>
  </Card>
);

const NotCard: React.FC<{ title: string; body: React.ReactNode }> = ({ title, body }) => (
  <Card sx={{ height: '100%', backgroundColor: '#fdf6f0' }}>
    <CardContent>
      <Typography sx={{ fontWeight: 600, fontSize: '0.95rem', mb: 0.75, color: 'secondary.dark' }}>
        ✗ {title}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.6 }}>
        {body}
      </Typography>
    </CardContent>
  </Card>
);

const About: React.FC = () => {
  return (
    <Box sx={{ maxWidth: 880, mx: 'auto', pt: 4, pb: 8 }}>
      <Box sx={{ textAlign: 'center', mb: 6 }}>
        <Box sx={{ mb: 3, display: 'flex', justifyContent: 'center' }}>
          <Logo height={56} wordmarkColor="#1c1917" showWordmark={false} />
        </Box>
        <Typography variant="h2" component="h1" sx={{ fontWeight: 700, letterSpacing: '-0.025em', fontSize: { xs: '2rem', sm: '2.6rem' } }}>
          What Cadence is
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mt: 2, fontSize: '1.1rem', maxWidth: 620, mx: 'auto' }}>
          A teacher-facing live dashboard for Jupyter classes. Drop two lines into any
          notebook and watch the class solve in real time —{' '}
          <Box component="span" sx={{ color: 'primary.main', fontWeight: 500 }}>
            per-checkpoint solve rates, common wrong answers, who needs help right now.
          </Box>
        </Typography>
      </Box>

      <Card sx={{ mb: 5 }}>
        <CardContent sx={{ p: 4 }}>
          <SectionLabel>The mental model</SectionLabel>
          <Stack spacing={2.5}>
            <Box>
              <Typography sx={{ fontWeight: 600, mb: 0.5 }}>Teacher side</Typography>
              <Typography variant="body2" color="text.secondary">
                Add a one-time setup cell to your notebook with{' '}
                <code>%cadence_create_lesson</code> and a set of expected answers via{' '}
                <code>%cadence_register</code> (or YAML for bulk). Cadence mints a join code +
                a dashboard URL. Bookmark the URL — the token IS the credential, no login page.
              </Typography>
            </Box>
            <Box>
              <Typography sx={{ fontWeight: 600, mb: 0.5 }}>Student side</Typography>
              <Typography variant="body2" color="text.secondary">
                Open the distributed notebook, run two lines (<code>%load_ext cadence</code> +{' '}
                <code>%cadence_session &lt;join_code&gt; "name"</code>), and work through the cells.
                A <code>check("id", value)</code> call after each exercise returns ✅ or ❌ inline.
                No login, no account, no email.
              </Typography>
            </Box>
            <Box>
              <Typography sx={{ fontWeight: 600, mb: 0.5 }}>What crosses the network</Typography>
              <Typography variant="body2" color="text.secondary">
                Just the student's answer (and a display name they chose). Student code executes
                locally on their own machine — Cadence never sees it unless the teacher
                explicitly opts the checkpoint into code submissions.
              </Typography>
            </Box>
          </Stack>
        </CardContent>
      </Card>

      <SectionLabel>What you get on the dashboard</SectionLabel>
      <Grid container spacing={2} sx={{ mb: 5 }}>
        <Grid item xs={12} sm={6} md={4}>
          <MetricCard
            title="Solve rate per checkpoint"
            body="Live count of sessions that got each checkpoint right, with a colour-tiered % chip you can scan across the lesson."
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <MetricCard
            title="Common wrong answers"
            body="Wrong submissions clustered by value (e.g. '124 ×11'). Hover any row to see the students who submitted that value."
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <MetricCard
            title="Attempts-to-first-correct"
            body="Per-checkpoint histogram of how many tries students needed: 1st try / 2nd try / 3+ / unsolved."
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <MetricCard
            title="Timing histogram"
            body="When students wrap a cell in %%cadence_time, you see what time bucket they solved in (<10 ms, 10–100 ms, 100 ms–1 s, …)."
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <MetricCard
            title="Per-student chronology"
            body="Expand any roster row to see every attempt that student has made, with submitted values, timing, and timestamps."
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <MetricCard
            title="Relative difficulty"
            body="Easier / Average / Harder chips per checkpoint and per notebook, computed from avg-attempts-to-resolve."
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <MetricCard
            title="Stuck-student alerts"
            body="Desktop notification when any student has 3+ wrong attempts on a single checkpoint in 5 minutes with no correct answer."
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <MetricCard
            title="Section grouping"
            body="Dotted checkpoint IDs (setup.mean-value, discovery.higgs-peak) collapse into per-section cards with aggregate solve rates."
          />
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <MetricCard
            title="Code & plot submissions"
            body="Opt-in per checkpoint. Students send their full code via %%cadence_submit or a matplotlib figure via submit_image(). Renders inline on the dashboard."
          />
        </Grid>
      </Grid>

      <SectionLabel>What Cadence is NOT</SectionLabel>
      <Grid container spacing={2} sx={{ mb: 5 }}>
        <Grid item xs={12} md={6}>
          <NotCard
            title="Not a code grader"
            body={
              <>
                We check student-submitted <em>answers</em> against teacher-registered values
                — we don't run their code. If you need a test runner that imports their
                solution and asserts against it, look at{' '}
                <a href="https://otter-grader.readthedocs.io/" target="_blank" rel="noreferrer" style={{ color: 'inherit' }}>
                  Otter-Grader
                </a>{' '}or{' '}
                <a href="https://github.com/jupyter/nbgrader" target="_blank" rel="noreferrer" style={{ color: 'inherit' }}>
                  nbgrader
                </a>.
              </>
            }
          />
        </Grid>
        <Grid item xs={12} md={6}>
          <NotCard
            title="Not an exam tool"
            body="No proctoring. No time-locked questions. No randomisation. No identity verification. Cadence is designed for low-stakes practice, not high-stakes assessment. If a student wants to cheat, they can."
          />
        </Grid>
        <Grid item xs={12} md={6}>
          <NotCard
            title="Not an LMS"
            body="No gradebook export. No enrollment management. No Canvas / Blackboard / Moodle integration. Pair it with whatever LMS your institution already uses."
          />
        </Grid>
        <Grid item xs={12} md={6}>
          <NotCard
            title="Not behavioural telemetry"
            body={
              <>
                We capture explicit <code>check()</code> calls (the answers students choose to
                submit), not every cell they run. If you want cell-execution and
                error-stream analytics, look at{' '}
                <a href="https://github.com/chili-epfl/jupyter-analytics" target="_blank" rel="noreferrer" style={{ color: 'inherit' }}>
                  EPFL's Jupyter Analytics
                </a>
                {' '}— a different category of tool. They complement, not compete.
              </>
            }
          />
        </Grid>
      </Grid>

      <Card sx={{ mb: 5 }}>
        <CardContent sx={{ p: 4 }}>
          <SectionLabel>Privacy posture</SectionLabel>
          <Stack spacing={1.5}>
            <Typography variant="body2">
              <Box component="span" sx={{ fontWeight: 600 }}>Student code never leaves their machine.</Box>{' '}
              They execute their solution locally; Cadence only sees the resulting value they pass to <code>check()</code>.
            </Typography>
            <Typography variant="body2">
              <Box component="span" sx={{ fontWeight: 600 }}>Names are pseudonyms by default.</Box>{' '}
              Students pick their display name when they join — anything they want. Cadence never asks for emails or accounts.
            </Typography>
            <Typography variant="body2">
              <Box component="span" sx={{ fontWeight: 600 }}>Teacher controls name visibility.</Box>{' '}
              Three toggles in the dashboard let you hide names entirely (screen-share-safe), surface them on hover only, or show inline "fewest / most attempts" lists. Default = roster on, outlier names off.
            </Typography>
            <Typography variant="body2">
              <Box component="span" sx={{ fontWeight: 600 }}>Code submissions are opt-in per checkpoint.</Box>{' '}
              They never happen unless the teacher explicitly registers the checkpoint with <code>--allow-submissions</code>.
            </Typography>
            <Typography variant="body2">
              <Box component="span" sx={{ fontWeight: 600 }}>Data is deletable and retention is bounded.</Box>{' '}
              Teachers can wipe a lesson and all attached student data with one click ("Delete all
              data" on the dashboard). Sessions auto-expire 12 months after the last attempt.
              Full details on the{' '}
              <RouterLink to="/privacy" style={{ color: 'inherit' }}>privacy page</RouterLink>.
            </Typography>
          </Stack>
        </CardContent>
      </Card>

      <Divider sx={{ my: 5 }} />

      <Box sx={{ textAlign: 'center' }}>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
          Ready to try it?
        </Typography>
        <Stack direction="row" spacing={2} justifyContent="center">
          <Chip component={RouterLink} to="/guide" label="→ Setup guide" clickable color="primary" />
          <Chip component={RouterLink} to="/teacher/library" label="My library" clickable variant="outlined" />
        </Stack>
      </Box>
    </Box>
  );
};

export default About;
