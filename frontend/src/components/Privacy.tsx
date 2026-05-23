import React from 'react';
import { Box, Typography, Card, CardContent, Stack, Divider, Link } from '@mui/material';
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

const PRIVACY_EMAIL = 'privacy@cadence-dash.com';

const Privacy: React.FC = () => {
  return (
    <Box sx={{ maxWidth: 760, mx: 'auto', pt: 4, pb: 8 }}>
      <Typography variant="h2" component="h1" sx={{ fontWeight: 700, letterSpacing: '-0.025em', fontSize: { xs: '2rem', sm: '2.4rem' }, mb: 1 }}>
        Privacy
      </Typography>
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 4 }}>
        Last updated: 22 May 2026
      </Typography>

      <Typography variant="body1" color="text.secondary" sx={{ mb: 4, fontSize: '1.05rem' }}>
        Cadence is designed to collect as little personal information as possible. This page
        documents what we collect, why, how long we keep it, and how to delete it. If anything
        is unclear, email <Link href={`mailto:${PRIVACY_EMAIL}`}>{PRIVACY_EMAIL}</Link>.
      </Typography>

      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <SectionLabel>Who we are and our role</SectionLabel>
          <Stack spacing={1.5}>
            <Typography variant="body2">
              When you use Cadence as a <strong>student</strong>, your <strong>teacher</strong>{' '}
              (and where applicable, their institution) is the <strong>data controller</strong>{' '}
              — they decide what's collected and for how long. Cadence is the{' '}
              <strong>data processor</strong>, running the service on their behalf within the
              strict limits in this notice.
            </Typography>
            <Typography variant="body2">
              When you use Cadence as a <strong>teacher</strong>, you are the controller for
              your students' data. Cadence processes data on your behalf.
            </Typography>
            <Typography variant="body2">
              For US educational institutions, Cadence operates under the FERPA "school
              official" exception — using data only for the educational purpose, under the
              institution's direct control, without redisclosure.
            </Typography>
          </Stack>
        </CardContent>
      </Card>

      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <SectionLabel>What we collect from students</SectionLabel>
          <Stack spacing={1.75}>
            <Typography variant="body2">
              <strong>Display name.</strong> Whatever the student types when joining via{' '}
              <code>%cadence_session</code> or the web join page. The join notice encourages
              pseudonyms (like <code>birb_42</code>) — students are free to choose one.
            </Typography>
            <Typography variant="body2">
              <strong>Submitted answers.</strong> The value passed to <code>check("id", value)</code>{' '}
              for each checkpoint.
            </Typography>
            <Typography variant="body2">
              <strong>Attempt metadata.</strong> Per attempt: timestamp, whether it was correct,
              and (when the student used <code>%%cadence_time</code>) elapsed milliseconds.
            </Typography>
            <Typography variant="body2">
              <strong>Code or plot submissions (opt-in per checkpoint).</strong> Only when the
              teacher registered the checkpoint with <code>--allow-submissions</code> AND the
              student explicitly ran <code>%%cadence_submit</code> or{' '}
              <code>cadence.submit_image()</code>. Otherwise we never see student code.
            </Typography>
          </Stack>
        </CardContent>
      </Card>

      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <SectionLabel>What we collect from teachers</SectionLabel>
          <Stack spacing={1.5}>
            <Typography variant="body2">
              When you create a teacher account: <strong>username, email, hashed password</strong>{' '}
              (we never see the plaintext). If you sign in with GitHub, we additionally store your
              GitHub account ID and your verified primary email.
            </Typography>
            <Typography variant="body2">
              Quick one-off lessons do not require an account. They use an opaque teacher token
              cached on your machine; we never see your identity.
            </Typography>
          </Stack>
        </CardContent>
      </Card>

      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <SectionLabel>What we deliberately don't collect</SectionLabel>
          <Stack spacing={1.5}>
            <Typography variant="body2">
              From students: no real-name verification, no email, no password, no phone number,
              no date of birth, no IP-based location, no device fingerprints, no keystroke logging,
              no cell-execution tracking — only the explicit <code>check()</code> calls students
              choose to make.
            </Typography>
            <Typography variant="body2">
              Student code <strong>runs locally on the student's machine</strong>. Cadence only
              receives the value passed to <code>check()</code>, unless the teacher has explicitly
              opted that checkpoint into code/plot submissions.
            </Typography>
            <Typography variant="body2">
              We never train any model on student data, never share between courses or
              institutions, never use student data for advertising or analytics in identifiable
              form, never sell or license student data.
            </Typography>
          </Stack>
        </CardContent>
      </Card>

      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <SectionLabel>Who sees student data</SectionLabel>
          <Stack spacing={1.5}>
            <Typography variant="body2">
              <strong>Your teacher</strong>, in the dashboard. Cadence operators may see data
              when investigating a technical issue, responding to a privacy request, or under
              legal compulsion — every such access is logged.
            </Typography>
            <Typography variant="body2">
              No one else. Not other teachers, not other institutions, not advertisers,
              not researchers, not any third party except the subprocessors listed below.
            </Typography>
          </Stack>
        </CardContent>
      </Card>

      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <SectionLabel>How long we keep it</SectionLabel>
          <Stack spacing={1.5}>
            <Typography variant="body2">
              Retention is set by the teacher at session or course creation and shown to students
              in the join notice. Defaults and bounds:
            </Typography>
            <Typography variant="body2" component="div">
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                <li><strong>Quick session mode:</strong> 24 hours, 7 days, or 30 days. Default 7 days.</li>
                <li><strong>Course mode:</strong> 24 hours to 12 months. Default 3 months, or 30 days after course end.</li>
                <li>Cohort-level aggregates (means/percentages only, cohorts of 10 or more): kept indefinitely in anonymous form.</li>
                <li>Teacher account data: until you close the account, then 30 days.</li>
                <li>Backups: 30 days, encrypted. Deletions propagate within this window.</li>
                <li>Access logs: 12 months for breach forensics and accountability.</li>
              </ul>
            </Typography>
            <Typography variant="body2">
              We never retain data past the teacher-set expiry except where law requires it.
            </Typography>
          </Stack>
        </CardContent>
      </Card>

      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <SectionLabel>Your rights</SectionLabel>
          <Stack spacing={1.5}>
            <Typography variant="body2">
              <strong>Access</strong> — see your data with{' '}
              <code>%cadence_my_data</code> in the notebook, or email{' '}
              <Link href={`mailto:${PRIVACY_EMAIL}`}>{PRIVACY_EMAIL}</Link>.
            </Typography>
            <Typography variant="body2">
              <strong>Portability</strong> — download as JSON with{' '}
              <code>%cadence_export_my_data</code>.
            </Typography>
            <Typography variant="body2">
              <strong>Erasure</strong> — delete with{' '}
              <code>%cadence_delete_my_data</code>. For requests outside an active notebook,
              your teacher (the controller) is the primary verifier.
            </Typography>
            <Typography variant="body2">
              <strong>Rectification</strong> — ask your teacher or email{' '}
              {PRIVACY_EMAIL}.
            </Typography>
            <Typography variant="body2">
              <strong>Restriction</strong> and <strong>objection</strong> —
              email {PRIVACY_EMAIL}.
            </Typography>
            <Typography variant="body2">
              <strong>Complaint to a supervisory authority</strong> —
              you can complain to a data protection authority at any time. UK: ICO (ico.org.uk).
              EU: your national DPA. India: Data Protection Board of India.
              US: FERPA complaints go to the US Department of Education Student Privacy Policy Office.
            </Typography>
          </Stack>
        </CardContent>
      </Card>

      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <SectionLabel>Age and consent</SectionLabel>
          <Typography variant="body2">
            Cadence is intended for students aged 13 or older. Where students under 13 use
            Cadence (US — COPPA), or where local law requires parental consent for older minors
            (India — DPDPA 2023 requires it for all under-18s; some EU member states under GDPR
            Article 8), the school or institution acts as controller and is responsible for the
            consent chain. Teachers attest to this at signup.
          </Typography>
        </CardContent>
      </Card>

      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <SectionLabel>How we secure it</SectionLabel>
          <Stack spacing={1.5}>
            <Typography variant="body2">
              <strong>Encryption in transit.</strong> Every connection — student to API, teacher to
              dashboard, API to database — is HTTPS/TLS.
            </Typography>
            <Typography variant="body2">
              <strong>Encryption at rest.</strong> Database storage is AES-256 encrypted with
              keys managed by Google Cloud. Backups use the same encryption.
            </Typography>
            <Typography variant="body2">
              <strong>Access controls.</strong> The database is not exposed to the public internet
              — only Cadence's own backend can connect via Google's private network. Teacher
              dashboards are gated by an unguessable per-lesson token (rotatable) or a
              JWT tied to a teacher account.
            </Typography>
            <Typography variant="body2">
              <strong>Access logging.</strong> Significant actions on student data —
              deletions, exports, and deletion authorizations — are logged with timestamp,
              actor identifier, and target. Retained 12 months. (We intentionally don't
              log every dashboard read: teacher dashboards poll frequently, so per-read
              logging would be noise without accountability benefit.)
            </Typography>
            <Typography variant="body2">
              <strong>Breach response.</strong> If a personal data breach occurs that poses a
              risk to you, we will notify the relevant supervisory authority within 72 hours
              where required (GDPR Article 33), and notify affected users where the risk is high.
            </Typography>
          </Stack>
        </CardContent>
      </Card>

      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <SectionLabel>Subprocessors</SectionLabel>
          <Typography variant="body2" sx={{ mb: 1.5 }}>
            Cadence uses the following third parties under data processing agreements.
            Each processes data only on Cadence's instructions:
          </Typography>
          <Typography variant="body2" component="div">
            <ul style={{ margin: 0, paddingLeft: 20 }}>
              <li><strong>Google Cloud Platform</strong> (Cloud Run, Cloud SQL) — application and database hosting, region <code>us-central1</code>.</li>
              <li><strong>Firebase Hosting</strong> (Google) — static frontend hosting.</li>
              <li><strong>GitHub</strong> — only for teachers who choose "Continue with GitHub" sign-in. We receive your GitHub ID and verified primary email.</li>
            </ul>
          </Typography>
          <Typography variant="body2" sx={{ mt: 1.5 }}>
            Data sent from outside the US is transferred under Google's Standard Contractual
            Clauses. If you need EU-only data residency for compliance, email {PRIVACY_EMAIL} —
            we can spin up an EU-region deployment for institutional use.
          </Typography>
        </CardContent>
      </Card>

      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <SectionLabel>Cookies & local storage</SectionLabel>
          <Typography variant="body2">
            We don't set tracking cookies. The dashboard uses your browser's{' '}
            <code>localStorage</code> to remember a few things across sessions: your teacher
            JWT (if signed in), the teacher tokens you've added to your library, and which
            lessons you've last viewed. Nothing leaves your browser; clearing site data
            removes it all.
          </Typography>
        </CardContent>
      </Card>

      <Divider sx={{ my: 4 }} />

      <Typography variant="body2" color="text.secondary">
        Questions, deletion requests, or complaints:{' '}
        <Link href={`mailto:${PRIVACY_EMAIL}`}>{PRIVACY_EMAIL}</Link>.
        See also the{' '}
        <RouterLink to="/terms" style={{ color: 'inherit' }}>Terms</RouterLink>,{' '}
        <RouterLink to="/about" style={{ color: 'inherit' }}>About</RouterLink>, and{' '}
        <RouterLink to="/guide" style={{ color: 'inherit' }}>setup guide</RouterLink>.
      </Typography>
    </Box>
  );
};

export default Privacy;
