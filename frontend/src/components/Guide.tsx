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
          <Step n={1} title="Install">
            <Inline>One-time install on the teacher's machine:</Inline>
            <CodeBlock lang="bash">{`pip install cadence-edu`}</CodeBlock>
            <Inline>
              You don't strictly need an account for one-off lessons, but signing in lets your
              lessons + courses persist across machines and show up automatically in your library:
            </Inline>
            <CodeBlock>{`%load_ext cadence
%cadence_login --username <your-username>     # prompts for password
# or: %cadence_login --token <jwt>            # paste a GitHub-OAuth JWT`}</CodeBlock>
          </Step>

          <Step n={2} title="Write your teaching notebook normally">
            <Inline>
              Open a fresh notebook and write it the way you'd write any teaching notebook:
              markdown for explanations, code cells for worked solutions. <strong>You do not
              need to mark anything for Cadence.</strong> Run the cells end-to-end so your
              answer values exist in the kernel.
            </Inline>
            <Inline>
              <strong>Your first cell should be <code>%load_ext cadence</code></strong>. That
              registers the magics, the tab-completion, and the input transformer that lets you
              write free-form prose inside <code># cadence:starter</code> blocks. Cells that run
              before <code>%load_ext cadence</code> skip everything.
            </Inline>
            <Inline>
              When you're ready to wire it for tracking, add (or just acknowledge) two things:
            </Inline>
            <Box sx={{ pl: 0, py: 0.5 }}>
              <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.7 }}>
                <Box component="span" sx={{ display: 'inline-block', minWidth: 24, fontWeight: 600, color: 'primary.main' }}>1.</Box>
                Markdown headings (<code>##</code>, <code>###</code>) above each exercise — these
                pair with the code cell that follows and become the task description in the
                student notebook.
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.7 }}>
                <Box component="span" sx={{ display: 'inline-block', minWidth: 24, fontWeight: 600, color: 'primary.main' }}>2.</Box>
                Each exercise cell ends with the answer — either as a bare expression (e.g.{' '}
                <code>arr.mean()</code> on its own line) or a named assignment (<code>mean_value
                = arr.mean()</code>). That's where Cadence reads the expected value from.
              </Typography>
            </Box>
            <Inline>
              That's it for the recommended (auto) mode. Setup cells, imports, helpers — anything
              that isn't a heading + answer pair — gets copied verbatim and isn't treated as an
              exercise.
            </Inline>

            <Box sx={{ mt: 2 }}>
              <SectionLabel>Optional per-cell markers</SectionLabel>
              <Inline>
                When you need control beyond the defaults, drop comment markers into specific
                cells. All markers are inert (just comments) — the magics are what do the work.
              </Inline>
              <Box sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 1.5, px: 2, py: 0.5, mt: 1 }}>
                <FieldRow name="checkpoint" required={false}>
                  <code># cadence:checkpoint &lt;id&gt; [&lt;comparator&gt;]</code> — set a custom id
                  for the exercise, or override the inferred comparator (e.g. <code>manual</code>{' '}
                  for a free-text reflection, <code>exact</code> to force ordered list match).
                </FieldRow>
                <FieldRow name="hint" required={false}>
                  <code># cadence:hint: &lt;text&gt;</code> inside the exercise cell becomes the
                  hint students can request with <code>show_hint("id")</code>. Markdown allowed.
                </FieldRow>
                <FieldRow name="starter" required={false}>
                  Wrap a region with <code># cadence:starter</code> / <code># cadence:end</code> and
                  that region replaces the default <code># Your code here</code> placeholder in
                  the student stub. The kernel comments out the starter region at execution
                  time, so it can contain prose, pseudocode, or <code>...</code> placeholders
                  that wouldn't otherwise parse as Python.
                </FieldRow>
                <FieldRow name="given" required={false}>
                  <code># cadence:given</code> / <code># cadence:end</code> wraps setup code that
                  both <strong>runs in your kernel</strong> AND is copied verbatim into the
                  student notebook above the starter stub. Use when the teacher reference needs
                  variables that students should start with too (loaded arrays, RNG draws, etc.).
                </FieldRow>
                <FieldRow name="solution" required={false}>
                  <code># cadence:solution</code> at the top of a code cell copies the whole cell
                  verbatim into the student notebook (for helper functions, worked examples, etc.).
                  Mutually exclusive with <code># cadence:checkpoint</code> in the same cell.
                </FieldRow>
                <FieldRow name="no-solution / reveal-after / hint-after" required={false}>
                  Per-checkpoint overrides for the solution-reveal flow:{' '}
                  <code># cadence:no-solution</code> suppresses the auto-revealed solution for
                  just this cell; <code># cadence:reveal-after N</code> and{' '}
                  <code># cadence:hint-after N</code> override the global attempt thresholds.
                </FieldRow>
                <FieldRow name="hide" required={false}>
                  <code># cadence:hide</code> / <code># cadence:end</code> delimits a region that's
                  stripped from <strong>both</strong> the registered teacher notebook and the
                  student notebook — purely teacher-authoring notes.{' '}
                  Markdown form: <code>&lt;!-- cadence:hide --&gt;</code> …{' '}
                  <code>&lt;!-- cadence:end --&gt;</code>.
                </FieldRow>
              </Box>
            </Box>
          </Step>

          <Step n={3} title="Run %cadence_autoregister — generates the teacher notebook">
            <Inline>
              In a fresh cell at the bottom of your authored notebook, after every other cell has
              been run:
            </Inline>
            <CodeBlock>{`%load_ext cadence
%cadence_autoregister`}</CodeBlock>
            <Inline>
              It walks through four prompts (auto-reveal solutions after N attempts? sign in?
              attach to a course? retention days?), then writes{' '}
              <code>&lt;your-notebook&gt;_registered.ipynb</code> next to the source. That second
              file is the one you'll keep around — it has each <code>%cadence_register …</code>{' '}
              line injected at the top of its exercise cell so you can scan id / comparator /
              expected at a glance.{' '}
              <strong>Solutions are revealed by default</strong> (after 3 wrong attempts) using
              your reference code; pass <code>--no-solutions</code> or answer <code>0</code> at
              the prompt to disable.
            </Inline>

            <Box sx={{ mt: 2, p: 2, borderRadius: 1.5, bgcolor: '#f8fafc', borderLeft: '4px solid #2563eb', color: '#1f2937' }}>
              <Typography variant="body2" sx={{ fontWeight: 600, color: '#1e3a8a', mb: 1 }}>
                Three notebooks, two transformations — and why three not one
              </Typography>
              <Typography variant="caption" component="pre" sx={{ fontFamily: '"JetBrains Mono", monospace', fontSize: '0.78rem', color: '#334155', whiteSpace: 'pre', overflowX: 'auto', display: 'block', m: 0 }}>{`(1) teacher.ipynb               ← what you author, edit, re-edit. Plain
        │                         teaching notebook + a few # cadence:
        │                         comments.
        │  %cadence_autoregister
        ▼
(2) teacher_registered.ipynb    ← auto-generated. Canonical "what's
        │                         registered" snapshot — running it
        │                         re-registers the lesson on the
        │                         dashboard. Commit to git alongside (1).
        │  %cadence_scaffold  (already wired in at the bottom)
        ▼
(3) teacher_registered_student.ipynb   ← the deliverable. You only ever
                                  hand this one to students.`}</Typography>
              <Typography variant="caption" component="div" sx={{ color: '#334155', mt: 1.5, lineHeight: 1.5 }}>
                <strong>Each file has a single, clear lifetime.</strong> (1) is the file you keep
                editing as the lesson evolves. (2) is the snapshot that backs the live lesson —
                re-run it to re-register after edits. (3) is the file you distribute. Re-running
                autoregister regenerates (2) and (3) cleanly.
              </Typography>
            </Box>
          </Step>

          <Step n={4} title="Open the registered notebook — generates the student version">
            <Inline>
              Open <code>&lt;your-notebook&gt;_registered.ipynb</code> in Jupyter and do{' '}
              <strong>Run All</strong>. That registers the lesson + every checkpoint on the
              server, then runs the <code>%cadence_scaffold</code> cell at the bottom (added
              for you automatically), which writes{' '}
              <code>&lt;your-notebook&gt;_registered_student.ipynb</code>.
            </Inline>
            <Inline>
              The student notebook has a boxed "Welcome — quick reference" panel at the top, the
              section + exercise headings carried across, your task markdown for each exercise,
              and a stub cell per exercise containing <code>check("id", ...)</code> (with starter
              scaffolding when you used a <code>cadence:starter</code> block). Share that file
              with students.
            </Inline>
            <Inline>
              Both downstream files are derived — re-run autoregister anytime to regenerate them
              cleanly.
            </Inline>
          </Step>

          <Step n={5} title="Optional teacher features">
            <Inline>
              All flags on <code>%cadence_register</code> (or fields in the YAML form). None
              required — but they're what makes Cadence feel alive in the classroom.
            </Inline>
            <Grid container spacing={2} sx={{ mt: 0 }}>
              <Grid item xs={12} md={6}>
                <FeatureCard title="Hints (opt-in)" subtitle="# cadence:hint: ... or --hint">
                  <Inline>
                    Drop <code># cadence:hint: try np.histogram</code> on a line inside your
                    exercise cell. After <code>N</code> wrong attempts (default <code>1</code>,
                    override per-cell with <code># cadence:hint-after N</code>), the student's
                    failure cell shows a <em>"💡 Need a hint?"</em> prompt; they opt in by running{' '}
                    <code>show_hint("id")</code>.
                  </Inline>
                </FeatureCard>
              </Grid>
              <Grid item xs={12} md={6}>
                <FeatureCard title="Solutions (default on)" subtitle="auto: your reference code; opt-out: # cadence:no-solution or --no-solutions">
                  <Inline>
                    Autoregister captures the teacher reference code in each exercise cell as the
                    worked solution. After 3 wrong attempts (override with{' '}
                    <code># cadence:reveal-after N</code> per cell, or{' '}
                    <code>--reveal-after N</code> globally) students can run{' '}
                    <code>show_solution("id")</code>. Suppress per-cell with{' '}
                    <code># cadence:no-solution</code>, or notebook-wide with{' '}
                    <code>--no-solutions</code>.
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
                    matplotlib figure with <code>submit_image("id", fig)</code>.
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

          <Step n={6} title="Self-test before distributing">
            <Inline>
              Inside the registered notebook, before you share the student version, submits the
              teacher's expected answer for every auto-checked checkpoint — catches typos in{' '}
              <code>expected</code> values or tolerance errors before students do.
            </Inline>
            <CodeBlock>{`%cadence_self_test`}</CodeBlock>
            <Inline>
              The student version is already written by <code>%cadence_scaffold</code> (step 4);
              all that's left is to send the file. The dashboard URL updates every ~3 seconds
              while the class is active.
            </Inline>
          </Step>

          <Step n={7} title="Project the join code in class">
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

          <SectionLabel>Alternative registration paths</SectionLabel>
          <Card sx={{ mb: 3 }}>
            <CardContent sx={{ p: 3 }}>
              <Inline>
                <code>%cadence_autoregister</code> is the recommended path, but the original
                registration mechanisms still work — pick whichever fits your workflow:
              </Inline>
              <Box sx={{ mt: 2 }}>
                <Inline>
                  <strong>YAML block in a cell</strong> — type expected values explicitly
                  instead of having them inferred from kernel state. Good when there's no
                  obvious "answer variable" to extract.
                </Inline>
                <Box sx={{ mt: 1 }}>
                  <CodeBlock lang="yaml">{`%%cadence_register_yaml
- id: setup.mean-value
  comparator: numeric
  expected: {value: 49.5, tolerance: 0.001}
  hint: average of 0..99
- id: discovery.higgs-peak
  comparator: exact
  expected: 125
  reveal_after: 3
  solution_value: "125"
  allow_submissions: true`}</CodeBlock>
                </Box>
              </Box>
              <Box sx={{ mt: 2 }}>
                <Inline>
                  <strong>YAML in a file</strong> — keep rubrics in version control across many
                  notebooks.
                </Inline>
                <Box sx={{ mt: 1 }}>
                  <CodeBlock>{`%cadence_register_yaml_file checkpoints/week3.yaml`}</CodeBlock>
                </Box>
              </Box>
              <Box sx={{ mt: 2 }}>
                <Inline>
                  <strong>Inline per-checkpoint</strong> — surgical edits, one-off demos.
                </Inline>
                <Box sx={{ mt: 1 }}>
                  <CodeBlock>{`%cadence_register array_mean --comparator numeric --expected 49.5
%cadence_register reflection --comparator manual --hint "Briefly describe what the peak shape tells you."`}</CodeBlock>
                </Box>
              </Box>
              <Box sx={{ mt: 2 }}>
                <Inline>
                  All four forms (auto-register, YAML block, YAML file, inline) coexist — you
                  can mix them in the same notebook. The five comparator types (<code>exact</code>,{' '}
                  <code>numeric</code>, <code>set</code>, <code>regex</code>, <code>manual</code>)
                  work the same across all paths.
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
            <CodeBlock>{`# Your code:
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
            <CodeBlock>{`show_hint("discovery.higgs-peak")`}</CodeBlock>
            <Inline>
              Some checkpoints let you reveal a worked solution after more attempts:
            </Inline>
            <CodeBlock>{`show_solution("discovery.higgs-peak")
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
            <CodeBlock>{`fig, ax = plt.subplots()
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
            <CodeBlock>{`mark_done("discovery.reflect")
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
                  <CommandRow cmd={`show_hint("id")`} what="Render the teacher's hint (unlocks after N wrong attempts)." who="student" />
                  <CommandRow cmd={`show_solution("id")`} what="Render the worked solution (unlocks after N attempts)." who="student" />
                  <CommandRow cmd={`mark_done("id")`} what="Self-attest completion for manual (reflection-style) checkpoints." who="student" />
                  <CommandRow cmd={`submit_image("id", fig)`} what="Send a matplotlib figure / PNG bytes to a submission-enabled checkpoint." who="student" />
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
