import React, { useState } from 'react';
import { Box, Typography, Card, CardContent, Tabs, Tab, Stack, Divider, Chip, Grid, Table, TableBody, TableCell, TableHead, TableRow } from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

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

const CodeBlock: React.FC<{ children: string; lang?: 'python' | 'yaml' | 'bash' }> = ({ children, lang = 'python' }) => (
  <Box
    sx={{
      borderRadius: 1.5,
      overflow: 'hidden',
      fontSize: '0.83rem',
      '& pre': {
        margin: '0 !important',
        padding: '12px 16px !important',
        background: '#0f172a !important',
        fontFamily: '"JetBrains Mono", Menlo, monospace !important',
        fontSize: '0.83rem !important',
        lineHeight: '1.55 !important',
      },
    }}
  >
    <SyntaxHighlighter
      language={lang}
      style={oneDark}
      customStyle={{ margin: 0, padding: '12px 16px', background: '#0f172a' }}
      codeTagProps={{ style: { fontFamily: '"JetBrains Mono", Menlo, monospace' } }}
    >
      {children}
    </SyntaxHighlighter>
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
  <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start', py: 1.5, borderBottom: '1px dashed', borderColor: 'divider', '&:last-child': { borderBottom: 'none' } }}>
    <Box sx={{ minWidth: 90, flexShrink: 0 }}>
      <Typography variant="body2" sx={{ fontFamily: '"JetBrains Mono", monospace', fontSize: '0.82rem', fontWeight: 600 }}>
        {name}
      </Typography>
      <Typography variant="caption" sx={{ color: required ? 'secondary.main' : 'text.disabled', fontSize: '0.7rem' }}>
        {required ? 'required' : 'optional'}
      </Typography>
    </Box>
    {/* minWidth: 0 lets the flex child shrink below its content size, so the
        nested CodeBlock can scroll horizontally instead of overflowing the card. */}
    <Box sx={{ flex: 1, minWidth: 0 }}>
      <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.6, mb: 1 }}>
        {children}
      </Typography>
    </Box>
  </Box>
);

const FeatureCard: React.FC<{ title: string; subtitle: string; children: React.ReactNode }> = ({ title, subtitle, children }) => (
  <Card sx={{ height: '100%', backgroundColor: '#f5f4ef' }}>
    <CardContent sx={{ p: 2.5 }}>
      <Typography sx={{ fontWeight: 600, fontSize: '0.95rem' }}>{title}</Typography>
      <Typography variant="caption" sx={{ display: 'block', mb: 1.5, fontFamily: '"JetBrains Mono", monospace', color: 'text.secondary' }}>
        {subtitle}
      </Typography>
      {children}
    </CardContent>
  </Card>
);

const CommandRow: React.FC<{ cmd: string; what: string; who: 'teacher' | 'student' | 'both' }> = ({ cmd, what, who }) => (
  <TableRow>
    <TableCell sx={{ fontFamily: '"JetBrains Mono", monospace', fontSize: '0.78rem', whiteSpace: 'nowrap', verticalAlign: 'top', py: 1 }}>
      {cmd}
    </TableCell>
    <TableCell sx={{ fontSize: '0.85rem', py: 1, color: 'text.secondary' }}>{what}</TableCell>
    <TableCell sx={{ py: 1 }}>
      <Chip
        size="small"
        label={who}
        variant="outlined"
        sx={{ fontFamily: '"JetBrains Mono", monospace', fontSize: '0.65rem', height: 18 }}
      />
    </TableCell>
  </TableRow>
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
          features laid out. Roughly 15 minutes the first time.
        </Typography>
      </Box>

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 3, borderBottom: '1px solid', borderColor: 'divider' }}>
        <Tab label="Teacher" />
        <Tab label="Student" />
        <Tab label="Command reference" />
      </Tabs>

      {tab === 0 && (
        <>
          <Step n={1} title="Install the Jupyter extension">
            <Inline>One-time install on the teacher's machine:</Inline>
            <CodeBlock lang="bash">{`pip install cadence-edu`}</CodeBlock>
            <Inline>
              Then sign in from a notebook so the lessons + courses you create belong to your
              account and show up automatically in your library:
            </Inline>
            <CodeBlock>{`%load_ext cadence
%cadence_login --username <your-username>     # prompts for password
# or sign in with GitHub from cadence-dash.com/login`}</CodeBlock>
            <Inline>
              Quick one-off lessons (no roster, ephemeral) don't strictly require an account, but
              creating a course (semester-style) does.
            </Inline>
            <Box sx={{ mt: 2 }}>
              <SectionLabel>Starter notebooks</SectionLabel>
              <Inline>
                Don't want to start from a blank cell? The package ships a CLI that drops a
                pre-wired notebook in the current directory:
              </Inline>
              <CodeBlock lang="bash">{`cadence-cli new teacher --name "Week 3: Fibonacci"
cadence-cli new student --name "Week 3: Fibonacci"`}</CodeBlock>
              <Inline>
                The teacher scaffold already has <code>%load_ext cadence</code>,{' '}
                <code>%cadence_create_lesson</code>, a YAML registration block, and{' '}
                <code>%cadence_self_test</code> in order. The student scaffold has a
                placeholder <code>%cadence_session</code> line and one example{' '}
                <code>check(...)</code>. Both are tiny on purpose — they're a launching pad, not a
                tutorial.
              </Inline>
              <Inline>
                <strong>While you're typing magics</strong>, hit{' '}
                <code>%cadence_<kbd>Tab</kbd></code> to autocomplete the magic name,{' '}
                <code>%cadence_register?</code> for full argument help on any one command, or{' '}
                <code>%cadence_help</code> for a one-page cheatsheet of every magic with its
                syntax. After typing <code>%cadence_lesson{' '}</code> the cached lesson names
                tab-complete too.
              </Inline>
            </Box>
          </Step>

          <Step n={2} title="Create your first lesson">
            <Inline>In a teacher-only notebook (not one you'll send to students):</Inline>
            <CodeBlock>{`%cadence_create_lesson "Week 3: Fibonacci"`}</CodeBlock>
            <Inline>
              The output shows a <code>join_code</code> (short, shareable — e.g.{' '}
              <code>soup-river-42</code>), a dashboard URL, and a pre-filled snippet you can paste
              at the top of the student notebook so they don't have to type the code. The card also
              tells you the per-session data retention (default <strong>7 days</strong>) and how
              to shorten it.
            </Inline>
            <Inline>
              Credentials cache to <code>~/.cadence/lessons.yaml</code> (mode 0600). Tomorrow you
              can reopen the same lesson with <code>%cadence_lesson "Week 3: Fibonacci"</code>{' '}
              from any notebook.
            </Inline>
          </Step>

          <Step n={3} title="Register the expected answers">
            <Inline>
              For each thing you want to grade, you tell Cadence three things:
            </Inline>
            <Box sx={{ pl: 0, py: 0.5 }}>
              <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.8 }}>
                <Box component="span" sx={{ display: 'inline-block', minWidth: 180, fontFamily: '"JetBrains Mono", monospace', fontSize: '0.82rem', color: 'primary.main' }}>
                  checkpoint id
                </Box>
                — your short label for the checkpoint.
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.8 }}>
                <Box component="span" sx={{ display: 'inline-block', minWidth: 180, fontFamily: '"JetBrains Mono", monospace', fontSize: '0.82rem', color: 'primary.main' }}>
                  comparator
                </Box>
                — how to check the answer: <code>exact</code> / <code>numeric</code> /{' '}
                <code>set</code> / <code>regex</code> / <code>manual</code>.
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.8 }}>
                <Box component="span" sx={{ display: 'inline-block', minWidth: 180, fontFamily: '"JetBrains Mono", monospace', fontSize: '0.82rem', color: 'primary.main' }}>
                  expected answer
                </Box>
                — the value to compare against, as JSON.
              </Typography>
            </Box>
            <Inline>
              Two equivalent forms are available — pick whichever fits the cell you're writing.
            </Inline>

            <Box sx={{ mt: 1 }}>
              <SectionLabel>One-liner per checkpoint</SectionLabel>
              <Inline>
                Flag-driven, fits on one line, good when you're sketching out a single checkpoint
                while you write the lab:
              </Inline>
              <CodeBlock>{`%cadence_register array_mean --comparator numeric --expected 49.5`}</CodeBlock>
              <Inline>
                In the student notebook, a cell that ends in <code>check("array_mean", value)</code>{' '}
                will check <code>value</code> against <code>49.5</code> using numeric comparison
                (which tolerates floating-point noise). The student sees ✅ or ❌ inline; you see the
                attempt on the dashboard.
              </Inline>
            </Box>

            <Box sx={{ mt: 2 }}>
              <SectionLabel>Bulk registration with YAML</SectionLabel>
              <Inline>
                Same fields as the flag form, but as a block — multi-line solution code, hints, and
                section structure read more naturally when you have several checkpoints in one place:
              </Inline>
              <CodeBlock lang="yaml">{`%%cadence_register_yaml
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
                Or keep the YAML in a separate file (lives next to your notebook, easy to version
                control) and register from there:
              </Inline>
              <CodeBlock>{`%cadence_register_yaml_file checkpoints/week3.yaml`}</CodeBlock>
              <Inline>
                <strong>Sectioning</strong> is free: dotted IDs like{' '}
                <code>setup.mean-value</code> and <code>discovery.higgs-peak</code> get
                automatically grouped on the dashboard into collapsible section cards.
              </Inline>
            </Box>

            <Box sx={{ mt: 2 }}>
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
          </Step>

          <Step n={4} title="Optional teacher features">
            <Inline>
              All flags on <code>%cadence_register</code> (or fields in the YAML form). None
              required — but they're what makes Cadence feel alive in the classroom.
            </Inline>
            <Grid container spacing={2} sx={{ mt: 0 }}>
              <Grid item xs={12} md={6}>
                <FeatureCard title="Hints (opt-in)" subtitle="--hint … --hint-after-attempts N">
                  <Inline>
                    After <code>N</code> wrong attempts (default <code>1</code>), the student's
                    failure cell shows a <em>"💡 Need a hint?"</em> prompt. They opt in by running{' '}
                    <code>cadence.show_hint("id")</code>.
                  </Inline>
                </FeatureCard>
              </Grid>
              <Grid item xs={12} md={6}>
                <FeatureCard title="Solutions (opt-in)" subtitle="--reveal-after N --solution-value … --solution-code …">
                  <Inline>
                    After <code>N</code> attempts the student can run{' '}
                    <code>cadence.show_solution("id")</code> to see the canonical value, a fully
                    worked code snippet, or both. Every reveal is logged on the dashboard.
                  </Inline>
                </FeatureCard>
              </Grid>
              <Grid item xs={12} md={6}>
                <FeatureCard title="Code submissions" subtitle="--allow-submissions">
                  <Inline>
                    Students can run <code>%%cadence_submit checkpoint_id</code> at the top of a
                    cell — the cell's code is sent verbatim to the dashboard.
                  </Inline>
                </FeatureCard>
              </Grid>
              <Grid item xs={12} md={6}>
                <FeatureCard title="Plot submissions" subtitle="--allow-submissions (same flag)">
                  <Inline>
                    Same flag. When a checkpoint accepts submissions, students can send a
                    matplotlib figure with <code>cadence.submit_image("id", fig)</code>.
                  </Inline>
                </FeatureCard>
              </Grid>
              <Grid item xs={12} md={6}>
                <FeatureCard title="Manual checkpoints" subtitle="--comparator manual">
                  <Inline>
                    For reflections or open-ended work. Students mark themselves done with{' '}
                    <code>mark_done("id")</code>. The dashboard shows completion %, not solve %.
                  </Inline>
                </FeatureCard>
              </Grid>
              <Grid item xs={12} md={6}>
                <FeatureCard title="Display order" subtitle="--order N">
                  <Inline>
                    Within a section, checkpoints sort by <code>order</code> then id. Set it
                    explicitly to match notebook order.
                  </Inline>
                </FeatureCard>
              </Grid>
              <Grid item xs={12} md={6}>
                <FeatureCard title="Timing data" subtitle="%%cadence_time">
                  <Inline>
                    Students prefix a cell with <code>%%cadence_time checkpoint_id</code> — Cadence
                    times the cell and records elapsed ms alongside the attempt.
                  </Inline>
                </FeatureCard>
              </Grid>
              <Grid item xs={12} md={6}>
                <FeatureCard title="Retention" subtitle="%cadence_set_retention --days N">
                  <Inline>
                    Shorten the per-session retention (default 7 days for lessons, 90 for
                    courses). Per the Terms, you can only reduce — never extend.
                  </Inline>
                </FeatureCard>
              </Grid>
            </Grid>
          </Step>

          <Step n={5} title="Self-test, then distribute">
            <Inline>
              Submits the teacher's expected answer for every auto-checked checkpoint — catches
              typos in <code>expected</code> values or tolerance errors before students do.
            </Inline>
            <CodeBlock>{`%cadence_self_test`}</CodeBlock>
            <Inline>
              Save the student version of the notebook (your answer code removed, replaced with{' '}
              <code>check("id", value)</code> calls). Or paste the pre-filled snippet from the
              lesson card at the top so students don't even need to type the join code. The
              dashboard URL updates every ~3 seconds while the class is active.
            </Inline>
          </Step>

          <Step n={6} title="Project the join code in class">
            <Inline>
              When you're at the front of the classroom and want students to type the join code,
              two options:
            </Inline>
            <Inline>
              <strong>In the notebook:</strong>
            </Inline>
            <CodeBlock>{`%cadence_show_join`}</CodeBlock>
            <Inline>
              <strong>On the dashboard:</strong> click the "Display join code" button in the
              header. Fullscreen overlay with the code in huge text. Click anywhere or press Esc
              to dismiss.
            </Inline>
          </Step>

          <Divider sx={{ my: 4 }} />

          <SectionLabel>Grouping multiple lessons into a course</SectionLabel>
          <Card sx={{ mb: 3 }}>
            <CardContent sx={{ p: 3 }}>
              <Inline>
                A <strong>course</strong> is a labelled bucket of lessons that share one roster
                page and one join code. Use it for semester-long teaching rather than one-shot
                sessions. Courses require sign-in (so we can audit deletion requests against a
                named controller).
              </Inline>
              <Box sx={{ mt: 2 }}>
                <Inline><strong>1. Create the course:</strong></Inline>
                <Box sx={{ mt: 1 }}>
                  <CodeBlock>{`%cadence_create_course "Particle Physics Lab — 2026"`}</CodeBlock>
                </Box>
              </Box>
              <Box sx={{ mt: 2 }}>
                <Inline><strong>2. Add a notebook to the active course:</strong></Inline>
                <Box sx={{ mt: 1 }}>
                  <CodeBlock>{`%cadence_add_notebook "Lab 1: NumPy warmup" --order 1`}</CodeBlock>
                </Box>
                <Inline>
                  This creates a lesson <em>and</em> attaches it. Subsequent{' '}
                  <code>%cadence_register</code> calls target the new notebook.
                </Inline>
              </Box>
              <Box sx={{ mt: 2 }}>
                <Inline><strong>3. Or attach an existing lesson:</strong></Inline>
                <Box sx={{ mt: 1 }}>
                  <CodeBlock>{`%cadence_attach_lesson "Last term's lab" --to "Particle Physics Lab — 2026"`}</CodeBlock>
                </Box>
              </Box>
              <Box sx={{ mt: 2 }}>
                <Inline><strong>4. Detach or delete when you're done:</strong></Inline>
                <Box sx={{ mt: 1 }}>
                  <CodeBlock>{`%cadence_detach_lesson "Lab 1: NumPy warmup" --from "Particle Physics Lab — 2026"
%cadence_delete_lesson "Old retired lab" --yes
%cadence_delete_course "Last year's class" --yes`}</CodeBlock>
                </Box>
                <Inline>
                  Or use the inline X / "remove from course" buttons on the course dashboard.
                </Inline>
              </Box>
              <Box sx={{ mt: 2 }}>
                <Inline><strong>5. Re-use a lesson next term:</strong></Inline>
                <Box sx={{ mt: 1 }}>
                  <CodeBlock>{`%cadence_clone_lesson "Lab 1: NumPy warmup" --as "Lab 1: NumPy warmup (2027)"`}</CodeBlock>
                </Box>
                <Inline>
                  Copies all the checkpoints, gives you a fresh join code and a clean session pool.
                  Original stays intact.
                </Inline>
              </Box>
            </CardContent>
          </Card>

          <SectionLabel>Reading the dashboard</SectionLabel>
          <Card sx={{ mb: 3 }}>
            <CardContent sx={{ p: 3 }}>
              <Stack spacing={1.5}>
                <Inline>
                  <strong>Header</strong> — lesson name, join code chip, retention chip, "Display
                  join code" button, active session count, rotate-token + delete buttons.
                </Inline>
                <Inline>
                  <strong>Lesson overview</strong> — Sessions / Checkpoints / Total attempts /
                  Overall solve rate, plus a per-student completion histogram and the top wrong
                  answers across the lesson.
                </Inline>
                <Inline>
                  <strong>Roster</strong> — collapsed by default. Expand for every joined student;
                  click a row for per-checkpoint progress + chronological attempt log.
                </Inline>
                <Inline>
                  <strong>Per-checkpoint cards</strong> — difficulty chip, solve count,
                  attempts-to-first-correct histogram, timing histogram, common wrong answers
                  (hover for names), solution-reveal count, and a submissions panel for{' '}
                  <code>--allow-submissions</code> checkpoints.
                </Inline>
                <Inline>
                  <strong>Three header toggles</strong> — Show student roster (master switch for
                  names), Show outlier names (inline "fewest / most attempts"), Stuck-student
                  alerts (desktop notification when 3+ wrong attempts on the same checkpoint
                  within 5 min).
                </Inline>
                <Inline>
                  <strong>Polling self-pauses</strong> — when your tab is hidden, polling stops.
                  When the class is quiet (no attempts for 5 min), polling slows. After 2 hours
                  idle the dashboard pauses with a "Resume" button.
                </Inline>
              </Stack>
            </CardContent>
          </Card>

          <SectionLabel>Account &amp; data management</SectionLabel>
          <Card sx={{ mb: 3 }}>
            <CardContent sx={{ p: 3 }}>
              <Stack spacing={1.5}>
                <Inline>
                  <strong>Your account</strong> — visit{' '}
                  <RouterLink to="/teacher/account" style={{ color: 'inherit' }}>
                    /teacher/account
                  </RouterLink>{' '}
                  to see your profile and close your account. Closure marks the account inactive;
                  full deletion follows after 30 days.
                </Inline>
                <Inline>
                  <strong>Your library</strong> —{' '}
                  <RouterLink to="/teacher/library" style={{ color: 'inherit' }}>
                    /teacher/library
                  </RouterLink>{' '}
                  shows every course and standalone lesson you own. Pasted tokens (for shared
                  courses) also show up here.
                </Inline>
                <Inline>
                  <strong>Audit the actions taken on your data</strong> — significant actions
                  (deletions, exports) are logged for 12 months. Email{' '}
                  <code>privacy@cadence-dash.com</code> for a copy.
                </Inline>
                <Inline>
                  <strong>Privacy notice, terms, breach response, ROPA, DPA template</strong> —{' '}
                  all linked from the{' '}
                  <RouterLink to="/privacy" style={{ color: 'inherit' }}>Privacy</RouterLink> and{' '}
                  <RouterLink to="/terms" style={{ color: 'inherit' }}>Terms</RouterLink> pages.
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
            <CodeBlock lang="bash">{`pip install cadence-edu`}</CodeBlock>
          </Step>

          <Step n={2} title="Open the notebook your teacher sent">
            <Inline>
              It usually begins with two lines that join you to the class. If your teacher pre-
              filled the join code, just edit your name; otherwise copy the code they gave you:
            </Inline>
            <CodeBlock>{`%load_ext cadence
%cadence_session soup-river-42 "Your name"`}</CodeBlock>
            <Inline>
              The display name can be anything — a pseudonym is fine. Cadence shows a short notice
              at this point explaining what's collected and your rights.
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
              Every attempt is recorded with a timestamp so the teacher can see where the class
              is struggling.
            </Inline>
          </Step>

          <Step n={4} title="Optional: get help when you're stuck">
            <Inline>
              After a few wrong attempts you may see <em>"💡 Need a hint?"</em> prompts. Opt in:
            </Inline>
            <CodeBlock>{`import cadence
cadence.show_hint("discovery.higgs-peak")`}</CodeBlock>
            <Inline>
              Some checkpoints let you reveal a worked solution after more attempts:
            </Inline>
            <CodeBlock>{`cadence.show_solution("discovery.higgs-peak")
# Renders the expected value + a fully worked code snippet.
# Every reveal is logged on the teacher's dashboard.`}</CodeBlock>
          </Step>

          <Step n={5} title="Optional: send your code or plot to the teacher">
            <Inline>
              On some checkpoints the teacher has enabled submissions. To send your code, prefix
              the cell with <code>%%cadence_submit checkpoint_id</code>:
            </Inline>
            <CodeBlock>{`%%cadence_submit discovery.higgs-peak
bin_edges = np.arange(100, 151)
counts, _ = np.histogram(m_gg, bins=bin_edges)
peak = int(bin_edges[np.argmax(counts)])
check("discovery.higgs-peak", peak)
# 📤 Code submitted to discovery.higgs-peak`}</CodeBlock>
            <Inline>For plot-driven checkpoints, send a matplotlib figure:</Inline>
            <CodeBlock>{`from cadence import submit_image
fig, ax = plt.subplots()
ax.hist(m_gg, bins=50)
submit_image("discovery.peak-plot", fig)
# 📤 Image submitted (PNG, 24 KB)`}</CodeBlock>
          </Step>

          <Step n={6} title="Optional: open-ended checkpoints">
            <Inline>
              For reflections or "build a plot, explain what you see" tasks the teacher may use a{' '}
              <strong>manual</strong> checkpoint. No value to send — once you've done the work,
              mark yourself done:
            </Inline>
            <CodeBlock>{`from cadence import mark_done
mark_done("discovery.reflect")
# ✅ Marked done`}</CodeBlock>
          </Step>

          <Step n={7} title="Optional: time how long you took">
            <Inline>
              For speed-sensitive exercises, prefix the cell with <code>%%cadence_time</code>.
              Cadence runs the cell, records elapsed milliseconds, and submits the last expression
              as your answer:
            </Inline>
            <CodeBlock>{`%%cadence_time discovery.fib10
def fib(n):
    return n if n <= 1 else fib(n-1) + fib(n-2)
fib(10)`}</CodeBlock>
          </Step>

          <Step n={8} title="Your data — see, export, or delete">
            <Inline>
              At any time during your session you can ask Cadence what it stores about you,
              download a JSON copy, or wipe everything:
            </Inline>
            <CodeBlock>{`%cadence_my_data            # show everything stored about this session
%cadence_export_my_data     # download as JSON
%cadence_delete_my_data --yes   # wipe permanently`}</CodeBlock>
            <Inline>
              These map to GDPR Article 15 (access), 20 (portability) and 17 (erasure)
              respectively. Outside an active notebook, email{' '}
              <code>privacy@cadence-dash.com</code> and your teacher can authorize the same.
            </Inline>
          </Step>
        </>
      )}

      {tab === 2 && (
        <>
          <Card sx={{ mb: 3 }}>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Every command Cadence ships, who runs it, and what it does. Inside a notebook,
                load the extension once with <code>%load_ext cadence</code>; everything below
                works after that.
              </Typography>

              <SectionLabel>Discovering commands</SectionLabel>
              <Table size="small" sx={{ mb: 3 }}>
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600 }}>Command</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>What it does</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Who</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  <CommandRow cmd="%cadence_help [substr]" what="One-stop cheatsheet of every Cadence magic, with syntax. Optional substring filter." who="both" />
                  <CommandRow cmd="%cadence_register?" what="(works on any magic) Argparse-style help: arguments, defaults, examples." who="both" />
                  <CommandRow cmd="cadence-cli new teacher --name 'X'" what="Drop a starter teacher notebook in the current directory." who="teacher" />
                  <CommandRow cmd="cadence-cli new student --name 'X'" what="Drop a starter student notebook in the current directory." who="teacher" />
                  <CommandRow cmd="cadence-cli lessons list" what="Show every lesson/course cached in ~/.cadence/lessons.yaml." who="teacher" />
                </TableBody>
              </Table>

              <SectionLabel>Authentication and account</SectionLabel>
              <Table size="small" sx={{ mb: 3 }}>
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600 }}>Command</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>What it does</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Who</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  <CommandRow cmd="%cadence_login --username U" what="Sign in with password (prompted). Or --token <jwt> to paste a JWT obtained via web GitHub login." who="teacher" />
                  <CommandRow cmd="%cadence_logout" what="Clear the cached JWT on this machine." who="teacher" />
                  <CommandRow cmd="%cadence_whoami" what="Show the currently signed-in teacher (if any)." who="teacher" />
                  <CommandRow cmd="%cadence_accept_terms" what="Pre-record Terms acceptance for token-only flow. Skipped automatically when logged in." who="teacher" />
                </TableBody>
              </Table>

              <SectionLabel>Lessons (quick mode)</SectionLabel>
              <Table size="small" sx={{ mb: 3 }}>
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600 }}>Command</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>What it does</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Who</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  <CommandRow cmd={`%cadence_create_lesson "name" [--code X] [--force]`} what="Create a new lesson. Re-running with the same name reloads the existing one; --force creates a duplicate." who="teacher" />
                  <CommandRow cmd={`%cadence_lesson "name"`} what="Reactivate a previously-created lesson cached in ~/.cadence/lessons.yaml." who="teacher" />
                  <CommandRow cmd={`%cadence_clone_lesson "name" [--as "new name"]`} what="Duplicate a lesson with all its checkpoints. New join code, new teacher token." who="teacher" />
                  <CommandRow cmd={`%cadence_delete_lesson "name" [--yes]`} what="Wipe the lesson and ALL its student data. Requires --yes." who="teacher" />
                  <CommandRow cmd={`%cadence_rotate_token`} what="Mint a fresh teacher_token for the active lesson. Use when a token leaks." who="teacher" />
                  <CommandRow cmd={`%cadence_set_retention --days N`} what="Shorten the per-session retention (can't extend, per Terms)." who="teacher" />
                </TableBody>
              </Table>

              <SectionLabel>Courses (semester mode, requires sign-in)</SectionLabel>
              <Table size="small" sx={{ mb: 3 }}>
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600 }}>Command</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>What it does</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Who</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  <CommandRow cmd={`%cadence_create_course "name" [--retention-days N]`} what="Create a course. Requires sign-in." who="teacher" />
                  <CommandRow cmd={`%cadence_course "name"`} what="Reactivate a previously-created course." who="teacher" />
                  <CommandRow cmd={`%cadence_add_notebook "name" [--order N]`} what="Create a fresh lesson AND attach it to the active course in one step." who="teacher" />
                  <CommandRow cmd={`%cadence_attach_lesson "lesson" --to "course"`} what="Attach an existing lesson to a course as a notebook." who="teacher" />
                  <CommandRow cmd={`%cadence_detach_lesson "lesson" --from "course"`} what="Remove the course→lesson association (doesn't delete either side)." who="teacher" />
                  <CommandRow cmd={`%cadence_delete_course "name" [--yes]`} what="Wipe the course and its direct sessions. Attached lessons survive." who="teacher" />
                  <CommandRow cmd={`%cadence_rotate_token --course`} what="Rotate the course teacher_token." who="teacher" />
                  <CommandRow cmd={`%cadence_set_retention --course --days N`} what="Shorten the course's per-session retention." who="teacher" />
                </TableBody>
              </Table>

              <SectionLabel>Checkpoints</SectionLabel>
              <Table size="small" sx={{ mb: 3 }}>
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600 }}>Command</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>What it does</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Who</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  <CommandRow cmd={`%cadence_register id --comparator X --expected '<json>'`} what="Register a single checkpoint. See the comparator table above for examples." who="teacher" />
                  <CommandRow cmd={`%%cadence_register_yaml`} what="Bulk-register from an inline YAML body — same fields as the flag form, in block layout." who="teacher" />
                  <CommandRow cmd={`%cadence_register_yaml_file path/to/file.yaml`} what="Bulk-register from a YAML file on disk." who="teacher" />
                  <CommandRow cmd={`%cadence_self_test`} what="Submit the teacher's expected answers to verify they parse and pass." who="teacher" />
                </TableBody>
              </Table>

              <SectionLabel>Sharing &amp; projection</SectionLabel>
              <Table size="small" sx={{ mb: 3 }}>
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600 }}>Command</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>What it does</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Who</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  <CommandRow cmd={`%cadence_show_join`} what="Render the active lesson/course's join code in huge text for projecting in class." who="teacher" />
                </TableBody>
              </Table>

              <SectionLabel>Student-side</SectionLabel>
              <Table size="small" sx={{ mb: 3 }}>
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600 }}>Command</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>What it does</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Who</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  <CommandRow cmd={`%cadence_session <code> "name"`} what="Join a lesson or course by its join code. Shows the privacy notice first." who="student" />
                  <CommandRow cmd={`%cadence_notebook "name"`} what="Switch the active notebook inside a course session." who="student" />
                  <CommandRow cmd={`check("id", value)`} what="Submit an answer for a checkpoint. Returns CheckResult." who="student" />
                  <CommandRow cmd={`%%cadence_time id`} what="Run the cell, time it, then submit the last expression's value as the answer." who="student" />
                  <CommandRow cmd={`%%cadence_submit id`} what="Run the cell normally AND ship the source to the teacher's dashboard. Requires --allow-submissions on the checkpoint." who="student" />
                  <CommandRow cmd={`cadence.show_hint("id")`} what="Render the teacher's hint (unlocks after N wrong attempts)." who="student" />
                  <CommandRow cmd={`cadence.show_solution("id")`} what="Render the worked solution (unlocks after N attempts)." who="student" />
                  <CommandRow cmd={`cadence.mark_done("id")`} what="Self-attest completion for manual (reflection-style) checkpoints." who="student" />
                  <CommandRow cmd={`cadence.submit_image("id", fig)`} what="Send a matplotlib figure / PNG bytes to a submission-enabled checkpoint." who="student" />
                </TableBody>
              </Table>

              <SectionLabel>Student data rights (GDPR)</SectionLabel>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600 }}>Command</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>What it does</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Who</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  <CommandRow cmd={`%cadence_my_data`} what="Right of access (Article 15). Show everything Cadence stores for this session." who="student" />
                  <CommandRow cmd={`%cadence_export_my_data [--path FILE]`} what="Right of portability (Article 20). Download as JSON." who="student" />
                  <CommandRow cmd={`%cadence_delete_my_data --yes`} what="Right to erasure (Article 17). Wipe permanently. Requires --yes." who="student" />
                </TableBody>
              </Table>
            </CardContent>
          </Card>
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
