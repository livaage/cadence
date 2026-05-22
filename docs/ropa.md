# Records of Processing Activities (ROPA) — Cadence

**Owner:** Liv Vage
**Last updated:** 2026-05-22
**Maintained under:** GDPR Article 30(2) (as processor) and 30(1) (where
Cadence is itself controller, e.g. teacher accounts).

This is the internal record of all processing activities Cadence performs.
Article 30 requires controllers and processors to maintain a record of
processing activities and make it available to the supervisory authority
on request. It does not need to be public.

Update this document whenever a processing activity is added, removed, or
materially changed (new data categories, new subprocessors, new purposes,
new retention).

---

## 1. Controller information

For activities where Cadence is the **controller** (teacher accounts and
infrastructure operations):

- **Name:** Liv Vage (operating Cadence as an individual)
- **Country of establishment:** [TBD — confirm before publishing]
- **Contact:** privacy@cadence-dash.com
- **DPO:** none required (Article 37 thresholds not met)
- **EU representative:** none. Cadence does not target EU users and the
  monitoring-of-behavior trigger in Article 3(2)(b) is contestable (see
  design doc Section 7). Revisit if EU institutional adoption occurs.

For activities where Cadence is the **processor** (student data), the
controllers are individual teachers and their institutions. They are
identified by the JWT account (auth flow) or teacher token (anonymous
flow). DPA template covers their controller obligations.

---

## 2. Processing activities

### 2.1 Teacher accounts (Cadence as controller)

| | |
|---|---|
| **Purpose** | Authenticate teachers; tie courses to a named owner; enable rights requests against a controller. |
| **Legal basis** | Contract (Article 6(1)(b)) — the user signs up to use the service. |
| **Categories of data subjects** | Teachers (adults; account creation requires acceptance of age attestation). |
| **Categories of personal data** | Username, email, hashed password (nullable for OAuth-only accounts), GitHub ID, GitHub primary email, display name, account creation timestamp. |
| **Recipients** | Cadence operators (Liv). GCP as hosting subprocessor. |
| **Transfers** | Data stored in `us-central1`. Standard Contractual Clauses with GCP. |
| **Retention** | Until account closure; then 30 days; backups age out in 30 days. |
| **Security measures** | bcrypt password hashing, JWT with 7-day TTL, env-managed signing key, HTTPS in transit, encryption at rest. |

### 2.2 GitHub OAuth identification (Cadence as controller)

| | |
|---|---|
| **Purpose** | Verify the teacher's identity at sign-in; link a GitHub identity to their Cadence account. |
| **Legal basis** | Contract (Article 6(1)(b)). |
| **Categories of data subjects** | Teachers who choose "Continue with GitHub". |
| **Categories of personal data** | GitHub user ID, GitHub username, verified primary email. We do not store the GitHub access token after the OAuth callback completes. |
| **Recipients** | Cadence operators. GitHub as subprocessor for the OAuth call. |
| **Transfers** | GitHub (US) — Standard Contractual Clauses. |
| **Retention** | Until account closure; same as 2.1. |
| **Security measures** | OAuth state handled server-side; GitHub client secret in env. |

### 2.3 Student progress data (Cadence as processor; teacher is controller)

| | |
|---|---|
| **Purpose** | Render real-time progress to the student's teacher. |
| **Legal basis** | Depends on the teacher's institution: public task (state), contract (private enrolment), legitimate interest (one-off workshops). Determined by the teacher; documented in their DPA where applicable. |
| **Categories of data subjects** | Students aged 13+. Where local law requires consent for older minors (India DPDPA, EU Article 8), the school is controller and provides the consent chain. |
| **Categories of personal data** | Display name (often pseudonymous), pseudonymous session ID, per-checkpoint attempts and timing, submitted code (when checkpoint opt-in), submitted images (when checkpoint opt-in). |
| **Recipients** | The student's teacher, via their dashboard. Cadence operators when investigating a technical issue or rights request (logged). |
| **Transfers** | `us-central1`. Standard Contractual Clauses with GCP. |
| **Retention** | Teacher-set, capped at 365 days. Defaults: 7 days (quick mode) / 90 days (course mode). Cohort aggregates (n ≥ 10): indefinite, anonymous. Backups: 30 days. |
| **Security measures** | HTTPS in transit, encryption at rest, scoped access (teacher token or JWT), 12-month access log, scheduled deletion job (daily). |

### 2.4 Cohort-level aggregates (Cadence as controller of anonymous derivative)

| | |
|---|---|
| **Purpose** | Improve checkpoint quality across all uses; informational stats per checkpoint. |
| **Legal basis** | N/A — aggregated to anonymity (k ≥ 10 per cohort), no longer personal data. |
| **Categories of data subjects** | N/A (anonymized). |
| **Categories of personal data** | None. Counts, means, completion rates only. |
| **Recipients** | Cadence operators; potentially other teachers viewing checkpoint-quality stats. |
| **Transfers** | `us-central1`. |
| **Retention** | Indefinite. |
| **Security measures** | Inherits database security. |

### 2.5 Access logs (Cadence as controller for accountability)

| | |
|---|---|
| **Purpose** | Article 5(2) accountability; breach forensics; rights-request audit trail. |
| **Legal basis** | Legal obligation (Article 6(1)(c)) — Article 5(2) and Article 33–34. |
| **Categories of data subjects** | Teachers and operators whose reads/exports/deletions are logged; the affected student is referenced by pseudonymous session ID. |
| **Categories of personal data** | Teacher ID, timestamp, action type, affected student session ID. |
| **Recipients** | Cadence operators. DPA on lawful request. |
| **Transfers** | `us-central1`. |
| **Retention** | 12 months. |
| **Security measures** | Same as application data; no direct teacher access. |

### 2.6 Privacy contact correspondence (Cadence as controller)

| | |
|---|---|
| **Purpose** | Receive and respond to rights requests, privacy questions, complaints. |
| **Legal basis** | Legal obligation (Articles 12, 15–22). |
| **Categories of data subjects** | Anyone who emails `privacy@cadence-dash.com`. |
| **Categories of personal data** | Whatever they include. Typically: email address, name, account or session identifier, the substance of the request. |
| **Recipients** | Cadence operators. |
| **Transfers** | Cloudflare Email Routing → personal Gmail inbox (US). SCCs in place. |
| **Retention** | 3 years after the request is closed (for audit purposes if the data subject later disputes how we responded). |
| **Security measures** | Inbox access protected by Google's account security; 2FA recommended. |

---

## 3. Subprocessors

| Subprocessor | Purpose | Region | DPA |
|---|---|---|---|
| Google Cloud Platform (Cloud Run, Cloud SQL, Firebase Hosting) | Application + database hosting | `us-central1` | Google's DPA + SCCs (auto-applied) |
| GitHub | OAuth identity for teachers who opt in | US | GitHub's DPA |
| Cloudflare | DNS for cadence-dash.com; email routing for privacy@ | Global edge; routing to US inbox | Cloudflare's DPA |
| Personal Gmail (during v1 only) | Inbox that receives forwarded privacy@ mail | US | N/A (operator's personal account, not a subprocessor relationship). Migrate to Workspace or Migadu when affordable. |

---

## 4. Cross-border transfers

All operational data lives in `us-central1`. EU and UK users' data is
transferred to the US under:
- Google Cloud's Standard Contractual Clauses (covers all GCP services).
- GitHub's published SCCs (covers OAuth user info exchange).
- Cloudflare's SCCs.

If an EU institution adopts Cadence and requires EU data residency, the
deploy plan supports spinning up an EU-region Cloud Run + Cloud SQL pair.
See `docs/deploy-plan.md`.

---

## 5. Retention summary

| Data category | Maximum retention | Mechanism |
|---|---|---|
| Student session data (attempts, code, timing, display name) | Teacher-set, 1–365 days; default 7 (quick) / 90 (course) | Scheduled deletion job, daily |
| Cohort aggregates (n ≥ 10) | Indefinite | Anonymous; not personal data |
| Teacher account | Until account closure + 30 days | Self-service DELETE /auth/me marks closure; daily cleanup hard-deletes after 30 days |
| Access logs | 12 months | Time-based purge (not yet implemented — TODO) |
| Backups | 30 days | GCP automatic retention |
| Privacy contact correspondence | 3 years from closure | Manual inbox housekeeping |
| Incident records | Indefinite (post-mortem value > minimization risk; no identifiable victim data) | Manual review |

---

## 6. Outstanding gaps

Tracked separately in the pre-launch checklist (`docs/cadence_design_doc.md`
§10). Items affecting this ROPA:

- Access-log purge job (12-month TTL) — schema exists, scheduled deletion
  not yet implemented.
- Course-mode deletion grace period (7-day teacher window) — deferred.
- Privacy@ inbox monitoring — pending Cloudflare Email Routing setup.

Update this ROPA when each is resolved.
