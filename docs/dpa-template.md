# Data Processing Agreement — Cadence

**Template version:** 1.0 (2026-05-22)

This is the template Data Processing Agreement (DPA) Cadence offers to
institutions that adopt the platform. Send it on request to
`privacy@cadence-dash.com`.

It is drafted to meet GDPR Article 28(3) and to accommodate FERPA's "school
official" exception for US institutions. The structure follows the EDPB's
standard contractual clauses for processor relationships within the EEA,
with US-specific add-ons in §10.

---

## Parties

This Data Processing Agreement ("**DPA**") is entered into between:

- **The Controller**: ____________________ ("**Institution**"), the
  educational institution or individual teacher whose students use Cadence;
  and
- **The Processor**: Liv Vage, an individual operating Cadence ("**Cadence**"),
  contact: privacy@cadence-dash.com.

This DPA supplements and forms part of the Terms of Service at
`cadence-dash.com/terms`. Where the DPA conflicts with the Terms, the DPA
governs in respect of processing of personal data.

**Effective date:** _________________.

---

## 1. Definitions

- **Personal data**, **data subject**, **processing**, **controller**,
  **processor**, **sub-processor**, and **supervisory authority** have the
  meanings given in GDPR Article 4.
- **Service** means the Cadence Jupyter integration and web dashboard
  described in the Terms.
- **Institution data** means personal data processed by Cadence on the
  Institution's instructions, including student progress, attempts,
  submitted code, display names, and teacher account data created by
  the Institution's staff.

---

## 2. Subject-matter, duration, nature, and purpose

- **Subject-matter**: Cadence's processing of personal data relating to
  the Institution's students and teachers in the course of providing the
  Service.
- **Duration**: For so long as the Institution uses the Service, plus any
  retention period for backups and access logs as set out in §6.
- **Nature**: Storage, retrieval, display, aggregation, deletion of
  educational records and progress telemetry.
- **Purpose**: Enabling the Institution's teachers to see and act on
  student progress through coding checkpoints; supporting institutional
  decisions about teaching only — never used for profiling, marketing,
  research, or product analytics in identifiable form.

---

## 3. Categories of data subjects and data

- **Data subjects**:
  - Students enrolled in lessons or courses operated by the Institution's
    teachers.
  - Teachers and administrators with accounts on Cadence belonging to the
    Institution.
- **Categories of personal data**:
  - Display names (often pseudonymous).
  - Per-checkpoint attempts, timing, and correctness.
  - Submitted code or images (only where the teacher opts a checkpoint
    into submissions).
  - Teacher account data (username, email, hashed password, OAuth
    identifiers, display name).
  - Pseudonymous session identifiers.
- **Special-category data**: none expected. The Institution must not
  instruct Cadence to process special-category data (Article 9) without a
  separate written addendum.

---

## 4. Controller's instructions

- Cadence processes Institution data **only on the Institution's
  documented instructions**, which are: (a) this DPA, (b) the
  configuration the Institution applies through the Service (retention
  periods, checkpoint settings, accounts created), and (c) any additional
  written instructions the Institution sends to
  `privacy@cadence-dash.com`.
- If Cadence reasonably believes an instruction infringes GDPR or other
  data-protection law, Cadence will inform the Institution and may suspend
  the affected processing pending clarification.

---

## 5. Confidentiality

- Cadence will ensure that persons authorised to process Institution data
  (currently: the operator) are under appropriate obligations of
  confidentiality.

---

## 6. Security measures (Article 32)

Cadence applies the following technical and organisational measures:

- **Encryption in transit**: HTTPS / TLS for all client-server
  connections; private networking between application and database.
- **Encryption at rest**: AES-256 via Google Cloud's managed encryption
  for both primary storage and backups.
- **Access control**:
  - The database is not exposed to the public internet.
  - Teacher dashboards are gated by an unguessable per-lesson token
    (rotatable) or by a JWT bound to a teacher account.
  - Cadence operator access requires MFA on the underlying Google
    account; access by the operator is logged.
- **Access logging**: significant actions on student data (deletions,
  exports, deletion authorisations) are recorded with timestamp, actor,
  and target. Logs are retained for 12 months and then automatically
  purged.
- **Retention enforcement**: a daily scheduled job deletes data past its
  teacher-configured retention period. Maximum retention is 365 days; the
  default for course mode is 90 days, for quick mode 7 days.
- **Backups**: automated, encrypted, retained 30 days. Deletions
  propagate to backups within that window.
- **Authentication**: passwords stored with bcrypt; JWTs signed with an
  environment-managed secret with a 7-day TTL.
- **Vulnerability management**: dependencies tracked through GitHub's
  vulnerability alerts; security patches applied within 30 days of
  disclosure (or sooner for critical severity).

These measures may be updated to reflect technical and operational
improvements; material reductions in security require notice to the
Institution.

---

## 7. Sub-processors

- The Institution **generally authorises** Cadence to use the
  sub-processors listed in Schedule A.
- Cadence will notify the Institution at least **30 days** before
  engaging a new sub-processor. The Institution may object in writing
  within 14 days; if the objection cannot be resolved, the Institution
  may terminate this DPA without penalty.
- Each sub-processor is bound by a written data-processing agreement
  imposing obligations no less protective than this DPA.

---

## 8. Data subject rights

- Cadence will, taking into account the nature of the processing, assist
  the Institution by appropriate technical and organisational measures
  in fulfilling the Institution's obligations under GDPR Chapter III
  (rights of the data subject).
- Specifically, Cadence provides:
  - Self-service magic commands for students to view, export, and delete
    their own session data (`%cadence_my_data`,
    `%cadence_export_my_data`, `%cadence_delete_my_data`).
  - A privacy contact (`privacy@cadence-dash.com`) for rights requests
    routed via the controller.
  - Teacher tooling in the dashboard to authorise deletion, rectify
    display names, and restrict processing during disputes.
- The Institution remains the primary verifier of identity for rights
  requests submitted outside of an active student session.

---

## 9. Personal data breach (Article 33 / 34)

- Cadence will notify the Institution of a personal data breach
  affecting Institution data **without undue delay, and in any event
  within 72 hours** of becoming aware.
- The notification will include, to the extent known at the time:
  nature of the breach, categories and approximate number of data
  subjects, categories and approximate number of records affected,
  likely consequences, measures taken or proposed, and Cadence's
  contact point for follow-up.
- Cadence will assist the Institution in meeting its own notification
  obligations to supervisory authorities and data subjects.
- The internal playbook is at `docs/breach-response.md`; the Institution
  may request a copy.

---

## 10. FERPA addendum (US institutions only)

Where the Institution is subject to FERPA (20 U.S.C. § 1232g; 34 CFR
Part 99):

- Cadence acts as a **"school official"** with a legitimate educational
  interest, under the exception at 34 CFR §99.31(a)(1).
- Cadence performs an institutional service or function for which the
  Institution would otherwise use its own employees.
- Cadence is under the **direct control** of the Institution with
  respect to the use and maintenance of education records.
- Cadence is subject to the requirements of 34 CFR §99.33(a) governing
  the use and re-disclosure of personal information from education
  records — specifically, Cadence will not redisclose education records
  to any party without the Institution's prior written consent or as
  otherwise permitted by FERPA.
- The Institution retains direct control over which staff members
  have teacher accounts and which students are enrolled in courses.

---

## 11. International transfers

- All Institution data is stored in `us-central1` (Iowa, USA) under
  the default Cadence deployment. Where the Institution requires
  EU-only storage, Cadence can provision an EU-region deployment;
  see Schedule B for the additional terms.
- Transfers from the EEA, UK, or Switzerland to the United States are
  performed under the **Standard Contractual Clauses (Module Two:
  Controller-to-Processor)** as approved by the European Commission and
  the UK's International Data Transfer Addendum, both incorporated by
  reference into this DPA.

---

## 12. Audit

- Cadence will make available to the Institution all information
  necessary to demonstrate compliance with this DPA and allow for and
  contribute to audits, including inspections, conducted by the
  Institution or another auditor mandated by the Institution.
- For institutions below 1,000 active student users, audit information
  is provided in written form on request (no on-site audit). For larger
  institutions or where law requires on-site audit, the parties will
  agree on scope and timing in advance.
- Audit requests must be reasonable in scope, frequency (no more than
  once per 12 months absent a specific incident), and timing.

---

## 13. Deletion or return of data

- Upon termination of the Service or expiry of this DPA, Cadence will,
  at the Institution's choice, delete or return all Institution data,
  including copies in backups, within 30 days. Logs and metadata
  required by law to be retained may be retained for the period
  required.
- Where the Institution closes a teacher account, that account's data
  is retained for 30 days and then permanently deleted (with backups
  ageing out within a further 30 days).

---

## 14. General

- **Governing law**: as set out in the Terms of Service, supplemented by
  GDPR / UK GDPR / Institutional jurisdiction as applicable.
- **Entire agreement**: this DPA together with the Terms of Service and
  Privacy Notice constitutes the entire agreement between the parties
  in respect of the processing of personal data.
- **Order of precedence**: in case of conflict, the order of precedence
  is (1) this DPA, (2) the Privacy Notice, (3) the Terms of Service.
- **Counterparts**: this DPA may be signed in counterparts, including
  electronically.

---

## Schedule A — Approved sub-processors (as of 2026-05-22)

| Sub-processor | Service | Region | DPA reference |
|---|---|---|---|
| Google Cloud Platform | Cloud Run (compute), Cloud SQL (database), Firebase Hosting (frontend) | `us-central1` | Google Cloud DPA + SCCs (auto-applied) |
| GitHub, Inc. | OAuth identity for teachers who opt in | US | GitHub DPA |
| Cloudflare, Inc. | DNS, email routing for `privacy@cadence-dash.com` | Global edge | Cloudflare DPA |

The current list is also at `cadence-dash.com/privacy` (Subprocessors section).

---

## Schedule B — Optional EU-region deployment

Available on request. Includes:
- Cloud Run + Cloud SQL provisioned in `europe-west4` (Netherlands) or
  another EEA region of the Institution's choice.
- Frontend hosting in the corresponding regional bucket.
- Sub-processor footprint reduced to EEA-region equivalents where
  available (GitHub OAuth remains US — disable OAuth if EU-only
  processing is required).
- Additional setup fee covers infrastructure provisioning; ongoing
  cost reflects the regional managed-database pricing differential.

---

## Signatures

**For the Institution**
Name: ____________________
Role: ____________________
Date: ____________________
Signature: ____________________

**For Cadence**
Name: Liv Vage
Date: ____________________
Signature: ____________________
