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

const Terms: React.FC = () => {
  return (
    <Box sx={{ maxWidth: 760, mx: 'auto', pt: 4, pb: 8 }}>
      <Typography variant="h2" component="h1" sx={{ fontWeight: 700, letterSpacing: '-0.025em', fontSize: { xs: '2rem', sm: '2.4rem' }, mb: 1 }}>
        Terms of Service
      </Typography>
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 4 }}>
        Last updated: 22 May 2026
      </Typography>

      <Typography variant="body1" color="text.secondary" sx={{ mb: 4, fontSize: '1.05rem' }}>
        These terms set out the rules for using Cadence. They're shorter and friendlier
        than commercial-platform terms because Cadence is a small open-source project,
        not a SaaS company. We aim to be clear, not to obscure. If anything here is
        unclear, email <Link href={`mailto:${PRIVACY_EMAIL}`}>{PRIVACY_EMAIL}</Link>.
      </Typography>

      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <SectionLabel>Who provides Cadence</SectionLabel>
          <Typography variant="body2">
            Cadence is operated by Liv Vage as an individual, not a company. The source
            code is open source under the MIT License at{' '}
            <Link href="https://github.com/livaage/cadence" target="_blank" rel="noopener">
              github.com/livaage/cadence
            </Link>
            . The hosted service runs on Google Cloud Platform; the privacy notice
            covers data handling in detail.
          </Typography>
        </CardContent>
      </Card>

      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <SectionLabel>What Cadence is</SectionLabel>
          <Stack spacing={1.5}>
            <Typography variant="body2">
              A Jupyter plugin and web dashboard that lets teachers track student
              progress through coding checkpoints in real time. Two modes:
              quick sessions (workshops, one-off lectures) and courses
              (semester-long teaching).
            </Typography>
            <Typography variant="body2">
              Cadence is free to use. It is supported by donations, not by selling
              your data — see the privacy notice for what that means in practice.
            </Typography>
          </Stack>
        </CardContent>
      </Card>

      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <SectionLabel>Acceptance</SectionLabel>
          <Typography variant="body2">
            By creating an account, joining a session, or installing the Jupyter plugin,
            you agree to these terms and the privacy notice. If you don't agree, please
            don't use Cadence.
          </Typography>
        </CardContent>
      </Card>

      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <SectionLabel>Eligibility</SectionLabel>
          <Stack spacing={1.5}>
            <Typography variant="body2">
              Cadence is intended for students aged 13 or older. Teachers attest to
              this at signup. Where students under 13 use Cadence (US — COPPA), or
              where local law requires parental consent for older minors (India —
              DPDPA 2023 for under-18s; some EU member states under GDPR Article 8),
              the school or institution acts as controller and is responsible for
              the consent chain.
            </Typography>
            <Typography variant="body2">
              Teacher accounts are for individuals over the age of majority in their
              jurisdiction.
            </Typography>
          </Stack>
        </CardContent>
      </Card>

      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <SectionLabel>Teacher responsibilities</SectionLabel>
          <Stack spacing={1.5}>
            <Typography variant="body2">
              When you use Cadence to run a session or course, you are the data
              controller for your students' data under GDPR and equivalent laws.
              That means you're responsible for:
            </Typography>
            <Typography variant="body2" component="div">
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                <li>Telling your students you're using Cadence and pointing them at the privacy notice.</li>
                <li>Choosing a retention period appropriate to your teaching context.</li>
                <li>Responding to your students' rights requests (access, export, deletion, rectification, etc.). Cadence helps via the magic commands and dashboard, but you are the primary verifier.</li>
                <li>Not collecting any data from students that you aren't entitled to collect under your institution's policies and local law.</li>
                <li>Not asking students to submit identifiable personal information about themselves or others through Cadence (their submitted answers should be code, math, or short text — not full names of third parties, addresses, health information, etc.).</li>
              </ul>
            </Typography>
            <Typography variant="body2">
              For institutional use, a Data Processing Agreement is available on
              request from <Link href={`mailto:${PRIVACY_EMAIL}`}>{PRIVACY_EMAIL}</Link>.
            </Typography>
          </Stack>
        </CardContent>
      </Card>

      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <SectionLabel>Acceptable use</SectionLabel>
          <Stack spacing={1.5}>
            <Typography variant="body2">
              Don't use Cadence to:
            </Typography>
            <Typography variant="body2" component="div">
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                <li>Attack, probe, or attempt unauthorized access to Cadence or other users' data.</li>
                <li>Submit code or content designed to harm Cadence, other users, or third parties.</li>
                <li>Impersonate another person.</li>
                <li>Scrape, mine, or otherwise extract data beyond what the documented endpoints provide.</li>
                <li>Use Cadence for activities your institution prohibits (e.g., violating an honor code through coordinated copying).</li>
                <li>Send spam, harassment, or harmful content via the privacy contact or any other channel.</li>
              </ul>
            </Typography>
            <Typography variant="body2">
              Student code runs locally on the student's machine, not on Cadence's
              servers. We don't execute student code on our infrastructure, so there
              isn't a way for student submissions to attack us through execution —
              but submitting malicious payloads as text or images is still prohibited.
            </Typography>
          </Stack>
        </CardContent>
      </Card>

      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <SectionLabel>Your content</SectionLabel>
          <Stack spacing={1.5}>
            <Typography variant="body2">
              Lesson content you create, code your students submit, and any images
              they attach remain yours (or your students'). You grant Cadence a
              limited license to process this content solely to operate the service
              for you — show your teacher's dashboard, evaluate checkpoints,
              compute aggregate stats — and for no other purpose.
            </Typography>
            <Typography variant="body2">
              We never train models on student or teacher content. We never sell or
              license it to anyone. The privacy notice covers this in detail and is
              part of these terms by reference.
            </Typography>
          </Stack>
        </CardContent>
      </Card>

      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <SectionLabel>Service availability</SectionLabel>
          <Stack spacing={1.5}>
            <Typography variant="body2">
              Cadence is provided on a best-effort basis. We aim to keep it up, but
              we don't offer an SLA. There may be downtime for maintenance, deploys,
              or because something has broken and we're a small team fixing it.
            </Typography>
            <Typography variant="body2">
              We may change, suspend, or discontinue features. For material changes
              that affect existing users, we'll give reasonable notice via the
              privacy contact, the project repository, and a banner on this site.
            </Typography>
          </Stack>
        </CardContent>
      </Card>

      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <SectionLabel>Account suspension and termination</SectionLabel>
          <Stack spacing={1.5}>
            <Typography variant="body2">
              We may suspend or terminate access if you violate these terms, especially
              the acceptable-use rules. For serious violations (e.g., active attacks)
              this may be immediate; otherwise we'll usually warn first.
            </Typography>
            <Typography variant="body2">
              You can close your teacher account at any time — currently by emailing{' '}
              <Link href={`mailto:${PRIVACY_EMAIL}`}>{PRIVACY_EMAIL}</Link>. A
              self-service close button is on the roadmap. When an account is closed,
              data is deleted per the privacy notice (account data retained 30 days,
              then permanently removed; backups age out within 30 days).
            </Typography>
          </Stack>
        </CardContent>
      </Card>

      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <SectionLabel>No warranty</SectionLabel>
          <Typography variant="body2">
            Cadence is provided "as is," without warranties of any kind, express or
            implied, including merchantability, fitness for a particular purpose,
            and non-infringement. This is standard language for a free service; in
            practice it means we'll do our best but can't guarantee perfection.
          </Typography>
        </CardContent>
      </Card>

      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <SectionLabel>Limitation of liability</SectionLabel>
          <Typography variant="body2">
            To the maximum extent permitted by applicable law, Cadence and its
            operator are not liable for indirect, incidental, special, consequential,
            or punitive damages arising out of your use of the service. Total
            liability for any direct damages is limited to the amount you paid us
            in the prior 12 months — which for a free service is zero. None of
            this limits liability for gross negligence or wilful misconduct.
          </Typography>
        </CardContent>
      </Card>

      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <SectionLabel>Changes to these terms</SectionLabel>
          <Typography variant="body2">
            We'll update these terms when the service changes materially or when
            law requires it. Material changes will be flagged at the top of this
            page for 30 days. Continuing to use Cadence after the change means
            you accept the new terms; if you don't agree, you can close your
            account.
          </Typography>
        </CardContent>
      </Card>

      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <SectionLabel>Governing law and disputes</SectionLabel>
          <Typography variant="body2">
            These terms are governed by the law of the operator's jurisdiction.
            Where you are a consumer with statutory rights in your country of
            residence, those rights apply in addition. We'll try to resolve any
            disagreement directly first — email{' '}
            <Link href={`mailto:${PRIVACY_EMAIL}`}>{PRIVACY_EMAIL}</Link> and we'll
            do our best to sort it out before either of us escalates.
          </Typography>
        </CardContent>
      </Card>

      <Divider sx={{ my: 4 }} />

      <Typography variant="body2" color="text.secondary">
        Privacy questions and data rights: see the{' '}
        <RouterLink to="/privacy" style={{ color: 'inherit' }}>Privacy</RouterLink>{' '}
        page. Setup help: see the{' '}
        <RouterLink to="/guide" style={{ color: 'inherit' }}>Guide</RouterLink>. Anything
        else: <Link href={`mailto:${PRIVACY_EMAIL}`}>{PRIVACY_EMAIL}</Link>.
      </Typography>
    </Box>
  );
};

export default Terms;
