import React, { useState } from 'react';
import { Box, Typography, Card, CardContent, Tabs, Tab, Stack, Divider, Chip, Grid } from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';

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
      mb: 1.5,
    }}
  >
    {children}
  </Typography>
);

const CodeBlock: React.FC<{ children: string; lang?: string }> = ({ children, lang }) => (
  <Box
    component="pre"
    sx={{
      backgroundColor: '#0f172a',
      color: '#e2e8f0',
      p: 2,
      borderRadius: 1.5,
      overflow: 'auto',
      fontSize: '0.83rem',
      lineHeight: 1.6,
      m: 0,
      fontFamily: '"JetBrains Mono", monospace',
    }}
    aria-label={lang}
  >
    {children}
  </Box>
);

const Step: React.FC<{ n: number; title: string; children: React.ReactNode }> = ({ n, title, children }) => (
  <Card sx={{ mb: 2.5 }}>
    <CardContent sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
        <Box
          sx={{
            width: 32, height: 32, borderRadius: '50%',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            backgroundColor: 'primary.main', color: '#fff',
            fontWeight: 600, fontSize: '0.9rem',
            fontFamily: '"JetBrains Mono", monospace',
          }}
        >
          {n}
        </Box>
        <Typography variant="h6" sx={{ fontWeight: 600 }}>{title}</Typography>
      </Box>
      <Stack spacing={2}>{children}</Stack>
    </CardContent>
  </Card>
);

const Inline: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.65 }}>
    {children}
  </Typography>
);

const FieldRow: React.FC<{ name: string; required?: boolean; children: React.ReactNode }> = ({ name, required, children }) => (
  <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start', py: 1, borderBottom: '1px dashed', borderColor: 'divider', '&:last-child': { borderBottom: 'none' } }}>
    <Box sx={{ minWidth: 170, flexShrink: 0 }}>
      <Typography variant="body2" sx={{ fontFamily: '"JetBrains Mono", monospace', fontSize: '0.82rem', fontWeight: 600 }}>
        {name}
      </Typography>
      <Typography variant="caption" sx={{ color: required ? 'secondary.main' : 'text.disabled', fontSize: '0.7rem' }}>
        {required ? 'required' : 'optional'}
      </Typography>
    </Box>
    <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.6, flex: 1 }}>
      {children}
    </Typography>
  </Box>
);

const FeatureCard: React.FC<{ title: string; subtitle: string; children: React.ReactNode }> = ({ title, subtitle, children }) => (
  <Card sx={{ height: '100%', backgroundColor: '#f5f4ef' }}>
    <CardContent sx={{ p: 2.5 }}>
      <Typography sx={{ fontWeight: 600, fontSize: '0.95rem' }}>{title}</Typography>
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1.5 }}>
        {subtitle}
      </Typography>
      {children}
    </CardContent>
  </Card>
);

const Guide: React.FC = () => {
  const [tab, setTab] = useState(0);
  return (
    <Box sx={{ maxWidth: 820, mx: 'auto', pt: 4, pb: 8 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h2" component="h1" sx={{ fontWeight: 700, letterSpacing: '-0.025em', fontSize: { xs: '2rem', sm: '2.4rem' } }}>
          Setup guide
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mt: 1.5, fontSize: '1.05rem' }}>
          From <code>pip install</code> to a live dashboard, with all the optional teacher
          features laid out. Roughly 15 minutes the first time. Assumes a Cadence backend is
          already running (this site).
        </Typography>
      </Box>

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 3, borderBottom: '1px solid', borderColor: 'divider' }}>
        <Tab label="Teacher" />
        <Tab label="Student" />
      </Tabs>

      {tab === 0 && (
        <>
          <Step n={1} title="Install the Jupyter extension">
            <Inline>One-time install on the teacher's machine:</Inline>
            <CodeBlock>{`pip install cadence-edu`}</CodeBlock>
            <Inline>
              Point the package at this backend (set this once in your shell profile, or per-session
              with a notebook cell — the URL of this site is the value):
            </Inline>
            <CodeBlock>{`export CADENCE_API_URL=https://<your-cadence-host>`}</CodeBlock>
          </Step>

          <Step n={2} title="Create your first lesson">
            <Inline>In a teacher-only notebook (not one you'll send to students):</Inline>
            <CodeBlock>{`%load_ext cadence
%cadence_create_lesson "Week 3: Fibonacci"`}</CodeBlock>
            <Inline>
              Output shows a <code>join_code</code> (short, shareable — e.g. <code>soup-river-42</code>)
              and a clickable <code>dashboard URL</code>. Bookmark the URL — that's your live view.
              Credentials are also cached to <code>~/.cadence/lessons.yaml</code> (mode 0600), so
              tomorrow you can reopen the same lesson with{' '}
              <code>%cadence_lesson "Week 3: Fibonacci"</code> from any notebook.
            </Inline>
          </Step>

          <Step n={3} title="Register the expected answers">
            <Inline>
              For each thing you want to grade, you tell Cadence three things: a{' '}
              <strong>checkpoint id</strong> (your label for it), the{' '}
              <strong>type of comparison</strong> to use, and the <strong>expected answer</strong>.
              That's it. The simplest possible registration looks like this:
            </Inline>
            <CodeBlock>{`%cadence_register array_mean --comparator numeric --expected 49.5
#                  └───────┬──────┘ └─────────┬─────────┘ └──────┬──────┘
#                          │                  │                  │
#                checkpoint id    comparator type            expected answer`}</CodeBlock>
            <Inline>
              Now in the student notebook, a cell that ends in{' '}
              <code>check("array_mean", value)</code> will check <code>value</code> against{' '}
              <code>49.5</code> using the numeric comparator (which tolerates floating-point noise).
              The student sees ✅ or ❌ inline; you see the attempt on the dashboard.
            </Inline>
            <Box sx={{ mt: 1 }}>
              <SectionLabel>The five comparator types</SectionLabel>
              <Box sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 1.5, px: 2, py: 0.5 }}>
                <FieldRow name="exact" required>
                  Strings or simple values, whitespace-trimmed equality.
                  <CodeBlock>{`%cadence_register greeting --comparator exact --expected '"Hello, World!"'`}</CodeBlock>
                </FieldRow>
                <FieldRow name="numeric" required>
                  Numbers with float tolerance. Pass either a bare number (default tolerance 1e-6) or{' '}
                  <code>{`{"value": …, "tolerance": …}`}</code>.
                  <CodeBlock>{`%cadence_register circle_area --comparator numeric \\
    --expected '{"value": 78.5398, "tolerance": 0.001}'`}</CodeBlock>
                </FieldRow>
                <FieldRow name="set" required>
                  Order-independent collections. Student's list/tuple/set is compared as a set.
                  <CodeBlock>{`%cadence_register vowels --comparator set \\
    --expected '{"value": ["a","e","i","o","u"]}'`}</CodeBlock>
                </FieldRow>
                <FieldRow name="regex" required>
                  Full-match Python regex on the stringified value.
                  <CodeBlock>{`%cadence_register email --comparator regex \\
    --expected '{"pattern": "^[^@]+@[^@]+\\\\.[^@]+$"}'`}</CodeBlock>
                </FieldRow>
                <FieldRow name="manual" required>
                  No auto-check. Student self-attests with <code>mark_done(...)</code>. Use this
                  for reflections, open-ended writeups, or "build a plot" tasks. No{' '}
                  <code>--expected</code> needed.
                  <CodeBlock>{`%cadence_register reflection --comparator manual \\
    --hint "Briefly describe what the peak shape tells you."`}</CodeBlock>
                </FieldRow>
              </Box>
            </Box>
            <Box sx={{ mt: 1 }}>
              <SectionLabel>Doing many at once (recommended)</SectionLabel>
              <Inline>
                Once you have more than three or four checkpoints, the per-line form gets noisy.
                The bulk YAML form is the same fields in a tidier shape:
              </Inline>
              <CodeBlock>{`%%cadence_register_yaml
- id: setup.mean-value
  comparator: numeric
  expected: {value: 49.5, tolerance: 0.001}
  hint: average of 0..99
  hint_after: 2              # show_hint() unlocks after 2 wrong attempts
  order: 1

- id: discovery.higgs-peak
  comparator: exact
  expected: 125
  reveal_after: 3            # show_solution becomes available after 3 attempts
  solution_value: "125"
  solution_code: |
    bin_edges = np.arange(100, 151)
    counts, _ = np.histogram(m_gg, bins=bin_edges)
    int(bin_edges[np.argmax(counts)])
  allow_submissions: true    # students may send their code via %%cadence_submit`}</CodeBlock>
              <Inline>
                <strong>Sectioning</strong> is free: dotted IDs like{' '}
                <code>setup.mean-value</code> and <code>discovery.higgs-peak</code> are
                automatically grouped on the dashboard into collapsible section cards.
              </Inline>
            </Box>
          </Step>

          <Step n={4} title="Add the optional teacher features">
            <Inline>
              These are all flags on <code>%cadence_register</code> (or fields in the YAML form).
              You don't need any of them to ship a working lesson — but they're what makes Cadence
              feel alive in the classroom.
            </Inline>
            <Grid container spacing={2} sx={{ mt: 0 }}>
              <Grid item xs={12} md={6}>
                <FeatureCard
                  title="Hints (opt-in)"
                  subtitle="--hint … --hint-after-attempts N"
                >
                  <Inline>
                    After <code>N</code> wrong attempts (default <code>1</code>), the student's
                    failure cell shows a <em>"💡 Need a hint?"</em> prompt. They opt in by
                    running <code>cadence.show_hint("id")</code> — the hint never auto-displays.
                  </Inline>
                  <Box sx={{ mt: 1.5 }}>
                    <CodeBlock>{`--hint "Try axis=1" \\
--hint-after-attempts 2`}</CodeBlock>
                  </Box>
                </FeatureCard>
              </Grid>
              <Grid item xs={12} md={6}>
                <FeatureCard
                  title="Solutions (opt-in)"
                  subtitle="--reveal-after N --solution-value … --solution-code …"
                >
                  <Inline>
                    After <code>N</code> attempts the student's failure cell shows a{' '}
                    <em>"💡 Show solution?"</em> prompt; they opt in with{' '}
                    <code>cadence.show_solution("id")</code>, which prints the canonical value, a
                    fully worked code cell, or both. Every reveal is logged on the dashboard.
                  </Inline>
                  <Box sx={{ mt: 1.5 }}>
                    <CodeBlock>{`--reveal-after 3 \\
--solution-value "125" \\
--solution-code "bin_edges = np.arange(100, 151)\\n..."`}</CodeBlock>
                  </Box>
                </FeatureCard>
              </Grid>
              <Grid item xs={12} md={6}>
                <FeatureCard
                  title="Code submissions"
                  subtitle="--allow-submissions"
                >
                  <Inline>
                    Students can run <code>%%cadence_submit checkpoint_id</code> at the top of a
                    cell — the cell's code is sent verbatim to the dashboard so you can see how
                    different students approached the problem.
                  </Inline>
                  <Box sx={{ mt: 1.5 }}>
                    <CodeBlock>{`--allow-submissions`}</CodeBlock>
                  </Box>
                </FeatureCard>
              </Grid>
              <Grid item xs={12} md={6}>
                <FeatureCard
                  title="Plot submissions"
                  subtitle="--allow-submissions  (same flag)"
                >
                  <Inline>
                    Same flag as above. When a checkpoint accepts submissions, students can also
                    send a matplotlib figure with{' '}
                    <code>cadence.submit_image("id", fig)</code>. The figure renders inline on
                    the dashboard.
                  </Inline>
                  <Box sx={{ mt: 1.5 }}>
                    <CodeBlock>{`# Same --allow-submissions flag
# enables both code and image uploads.`}</CodeBlock>
                  </Box>
                </FeatureCard>
              </Grid>
              <Grid item xs={12} md={6}>
                <FeatureCard
                  title="Manual checkpoints"
                  subtitle="--comparator manual"
                >
                  <Inline>
                    For reflections or open-ended work where there's no single right answer.
                    Students mark themselves done with <code>mark_done("id")</code>. The
                    dashboard shows completion %, not solve %.
                  </Inline>
                </FeatureCard>
              </Grid>
              <Grid item xs={12} md={6}>
                <FeatureCard
                  title="Display order"
                  subtitle="--order N"
                >
                  <Inline>
                    Within a section, checkpoints sort by <code>order</code> then by id. Set it
                    explicitly when you want the dashboard order to match the notebook order.
                  </Inline>
                </FeatureCard>
              </Grid>
            </Grid>
          </Step>

          <Step n={5} title="Self-test before class">
            <Inline>
              Submits the teacher's expected answer for every auto-checked checkpoint — catches
              typos in <code>expected</code> values or tolerance errors before students do. Regex
              and manual checkpoints are skipped (they need real student input).
            </Inline>
            <CodeBlock>{`%cadence_self_test`}</CodeBlock>
          </Step>

          <Step n={6} title="Distribute & watch the dashboard">
            <Inline>
              Save the student version of the notebook (one with your answer code <em>removed</em>{' '}
              and replaced with <code>check("id", value)</code> calls). Tell students the{' '}
              <code>join_code</code> from step 2. They run the notebook; you watch the dashboard
              URL update every ~3 seconds while the class is active, then slower when it's quiet.
            </Inline>
            <Inline>
              The <RouterLink to="/teacher/library" style={{ color: 'inherit' }}><strong>library page</strong></RouterLink>{' '}
              shows cards for every course and lesson you've added — handy when you're teaching
              multiple things at once.
            </Inline>
          </Step>

          <Divider sx={{ my: 4 }} />

          <SectionLabel>Grouping multiple notebooks into a course</SectionLabel>
          <Card sx={{ mb: 3 }}>
            <CardContent sx={{ p: 3 }}>
              <Inline>
                A <strong>course</strong> is just a labelled bucket of lessons that share one
                roster page and one URL. Use it when you're teaching a whole semester (10 weekly
                labs) rather than a one-shot session.
              </Inline>
              <Box sx={{ mt: 2 }}>
                <Inline><strong>1. Create the course</strong> (once per term):</Inline>
                <Box sx={{ mt: 1 }}>
                  <CodeBlock>{`%load_ext cadence
%cadence_create_course "Particle Physics Lab — 2026"`}</CodeBlock>
                </Box>
              </Box>
              <Box sx={{ mt: 2 }}>
                <Inline><strong>2. Add a notebook to the active course:</strong></Inline>
                <Box sx={{ mt: 1 }}>
                  <CodeBlock>{`%cadence_add_notebook "Lab 1: NumPy warmup" --order 1`}</CodeBlock>
                </Box>
                <Inline>
                  This creates a lesson <em>and</em> attaches it to the active course in one step.
                  After running it, subsequent <code>%cadence_register</code> calls target the
                  new notebook. Repeat for each lab; bump <code>--order</code> by 1 each time.
                </Inline>
              </Box>
              <Box sx={{ mt: 2 }}>
                <Inline><strong>3. Reopen the course later</strong> (e.g. next week):</Inline>
                <Box sx={{ mt: 1 }}>
                  <CodeBlock>{`%cadence_course "Particle Physics Lab — 2026"
%cadence_add_notebook "Lab 2: Four-vectors" --order 2`}</CodeBlock>
                </Box>
              </Box>
              <Box sx={{ mt: 2 }}>
                <Inline>
                  The course gets its own dashboard URL (one row per student across <em>all</em>{' '}
                  notebooks, with a difficulty rating per notebook). Each notebook also keeps its
                  own per-lesson dashboard. Both URLs show up in your{' '}
                  <RouterLink to="/teacher/library" style={{ color: 'inherit' }}>library</RouterLink>.
                </Inline>
              </Box>
            </CardContent>
          </Card>

          <SectionLabel>Reading the dashboard</SectionLabel>
          <Card sx={{ mb: 3 }}>
            <CardContent sx={{ p: 3 }}>
              <Stack spacing={1.5}>
                <Inline>
                  <strong>Lesson overview</strong> — Sessions / Checkpoints / Total attempts /
                  Overall solve rate, plus a per-student completion histogram and the top wrong
                  answers across the lesson.
                </Inline>
                <Inline>
                  <strong>Roster</strong> — collapsed by default. Expand to see every joined student,
                  click an individual row for their per-checkpoint progress + chronological log
                  of every attempt with timestamps.
                </Inline>
                <Inline>
                  <strong>Per-checkpoint cards</strong> — Easier / Harder difficulty chip, solve count,
                  attempts-to-first-correct histogram, timing histogram, common wrong answers
                  (hover for names), solution-reveal count, and a submissions panel showing
                  syntax-highlighted code or rendered plots when{' '}
                  <code>--allow-submissions</code> is set.
                </Inline>
                <Inline>
                  <strong>Three header toggles</strong> — <em>Show student roster</em> (master switch
                  for names everywhere), <em>Show outlier names</em> (inline "fewest / most
                  attempts" lists), and <em>Stuck-student alerts</em> (desktop notifications when
                  any student has 3+ wrong attempts on the same checkpoint within 5 minutes).
                </Inline>
                <Inline>
                  <strong>Polling self-pauses</strong> — when your tab is hidden, polling stops.
                  When the class is quiet (no attempts for 5 min), polling slows. After 2 hours
                  idle the dashboard pauses entirely with a "Resume" button. Backend load stays low.
                </Inline>
              </Stack>
            </CardContent>
          </Card>
        </>
      )}

      {tab === 1 && (
        <>
          <Step n={1} title="Install the Jupyter extension">
            <Inline>On a fresh machine, one-time:</Inline>
            <CodeBlock>{`pip install cadence-edu`}</CodeBlock>
            <Inline>Point it at the right backend (your teacher will tell you which):</Inline>
            <CodeBlock>{`export CADENCE_API_URL=https://<teacher-provided-host>`}</CodeBlock>
          </Step>

          <Step n={2} title="Open the notebook your teacher sent">
            <Inline>It begins with two lines that join you to the class:</Inline>
            <CodeBlock>{`%load_ext cadence
%cadence_session soup-river-42 "Your name"`}</CodeBlock>
            <Inline>
              The <code>join_code</code> is whatever your teacher gave you. The display name can
              be anything — Cadence doesn't ask for email or password.
            </Inline>
          </Step>

          <Step n={3} title="Work through the cells">
            <Inline>
              Cells include normal Python code plus a <code>check("checkpoint-id", value)</code>{' '}
              call at the end. The cell output shows ✅ or ❌ inline:
            </Inline>
            <CodeBlock>{`from cadence import check

# Your code:
mean_value = arr.mean()

# This call sends your answer to the teacher's dashboard:
check("setup.mean-value", mean_value)
# ✅ Correct (attempt 1)`}</CodeBlock>
            <Inline>
              Get it wrong? The cell shows ❌ with the attempt number. Every attempt is recorded
              with a timestamp so the teacher can see where the class is struggling.
            </Inline>
          </Step>

          <Step n={4} title="Optional: get help when you're stuck">
            <Inline>
              When the teacher has configured a hint, after a few wrong attempts you'll see a
              prompt below the ❌ — <em>"💡 Need a hint? Run cadence.show_hint(id)"</em>. You
              choose whether to read it; nothing auto-displays.
            </Inline>
            <CodeBlock>{`import cadence
cadence.show_hint("discovery.higgs-peak")
# Prints the teacher's hint in a coloured box.`}</CodeBlock>
            <Inline>
              Some checkpoints also let you reveal a fully worked solution after even more
              attempts. When that's available, a second prompt appears —{' '}
              <em>"💡 Show solution? Run cadence.show_solution(id)"</em>. Same idea, more
              detailed payload:
            </Inline>
            <CodeBlock>{`cadence.show_solution("discovery.higgs-peak")
# Renders the expected value + a fully worked code snippet.
# Every reveal is logged on the teacher's dashboard.`}</CodeBlock>
          </Step>

          <Step n={5} title="Optional: send your code or plot to the teacher">
            <Inline>
              On some checkpoints the teacher has enabled submissions — that means they want to
              <em> see your approach</em>, not just your answer. To send your code, prefix the
              cell with <code>%%cadence_submit checkpoint_id</code>:
            </Inline>
            <CodeBlock>{`%%cadence_submit discovery.higgs-peak
bin_edges = np.arange(100, 151)
counts, _ = np.histogram(m_gg, bins=bin_edges)
peak = int(bin_edges[np.argmax(counts)])
check("discovery.higgs-peak", peak)
# 📤 Code submitted to discovery.higgs-peak`}</CodeBlock>
            <Inline>
              For plot-driven checkpoints (matplotlib figures), use{' '}
              <code>submit_image</code> with the figure object:
            </Inline>
            <CodeBlock>{`from cadence import submit_image
fig, ax = plt.subplots()
ax.hist(m_gg, bins=50)
submit_image("discovery.peak-plot", fig)
# 📤 Image submitted (PNG, 24 KB)`}</CodeBlock>
            <Inline>
              If the checkpoint doesn't accept submissions, the magic will say so politely and
              do nothing.
            </Inline>
          </Step>

          <Step n={6} title="Optional: open-ended checkpoints">
            <Inline>
              For reflections or "build a plot, explain what you see" tasks the teacher may use
              a <strong>manual</strong> checkpoint. There's no value to send — once you've done
              the work, mark yourself done:
            </Inline>
            <CodeBlock>{`from cadence import mark_done
mark_done("discovery.reflect")
# ✅ Marked done`}</CodeBlock>
          </Step>

          <Step n={7} title="Re-running later">
            <Inline>
              Notebooks stay live indefinitely. If you reopen one a month later and re-run{' '}
              <code>check()</code>, it works — Cadence keeps the lesson and your old session
              around so you can verify your own understanding any time. The teacher's dashboard
              still shows your post-hoc attempts in the "all-time" scope.
            </Inline>
          </Step>
        </>
      )}

      <Divider sx={{ my: 4 }} />

      <Box sx={{ textAlign: 'center' }}>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
          Want the conceptual picture instead?
        </Typography>
        <Chip component={RouterLink} to="/about" label="→ What Cadence is (and isn't)" clickable color="primary" />
      </Box>
    </Box>
  );
};

export default Guide;
