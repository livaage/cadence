# Privacy Notice — Cadence

**Last updated:** [TBD: launch date]
**Plain-language summary at the top, full detail below. If anything is unclear, email privacy@cadence.app.**

---

## Summary

- Cadence is a Jupyter plugin that shows your teacher your real-time progress through coding checkpoints.
- We collect: your display name, progress, attempts, timing, and code you submit.
- Only **your teacher** sees your data. We never train models on it, never sell it, never share it with other teachers or institutions.
- Data is deleted at the end of the period your teacher sets (between 24 hours and 12 months).
- You can see, export, or delete your data at any time using `%cadence_my_data`, `%cadence_export_my_data`, and `%cadence_delete_my_data` in your notebook.
- Questions or complaints: privacy@cadence.app, or your national data protection authority.

---

## 1. Who we are

Cadence is operated by [TBD: legal entity or individual name], established in [TBD: country].

- **Privacy contact**: privacy@cadence.app
- **Postal address**: [TBD]

We do not have a Data Protection Officer (Cadence is below the GDPR Article 37 thresholds), but privacy@ is monitored and we respond within one month.

## 2. Roles: who decides what happens with your data

- When you use Cadence as a **student**, your **teacher** (and their institution where applicable) is the **data controller** — they decide what's collected, why, and for how long. Cadence is the **data processor** — we run the service on their behalf, within strict limits set out in this notice and our DPA.
- When you use Cadence as a **teacher**, *you* are the data controller for your students' data. Cadence processes data on your behalf.

For US educational institutions, Cadence acts under the FERPA "school official" exception — using education records only for the institutional purpose, under the institution's direct control, without redisclosure.

## 3. What we collect

**For students:**
- Display name or alias (you choose at join).
- Checkpoint progress.
- Attempt counts and timing.
- Code you submit at checkpoints.
- A pseudonymous student ID that we generate.

**For teachers:**
- Email address.
- Hashed password (we never see your password).
- Display name.
- Course and session metadata, including your retention settings and roster.

We do **not** collect: IP address for tracking, browser/device fingerprints, location, or anything beyond what is needed to run the service.

## 4. Why we collect it, and our legal basis

The purpose is to show your teacher your progress so they can teach more effectively. Specifically:

- Display your progress on your teacher's dashboard.
- Compute aggregate cohort statistics (means and percentages only, cohorts of 10 or more).
- Honor your data rights (access, export, deletion).

**Legal basis** depends on context — your teacher's institution determines which applies:

- **Public task / official authority** (state institutions).
- **Contract** (private institutions; students enrolled in a course).
- **Legitimate interest** (one-off workshops where no formal institutional relationship applies).

If you would like to know which applies to you, ask your teacher or email privacy@.

**Is provision required?** Providing this data is not a statutory requirement, but it is necessary to use Cadence — if you do not provide it, you cannot participate. Your teacher chose Cadence as part of their teaching; if you prefer not to use it, talk to them about alternatives.

## 5. Who sees your data

- **Your teacher** sees your name, ID, progress, attempts, timing, and submitted code.
- **Cadence operators** may see your data when investigating a technical issue, responding to a privacy request, or under legal compulsion. Every such access is logged.
- **No one else.** We do not share your data with other teachers, other institutions, advertisers, researchers, or any third party except the subprocessors below.

## 6. Subprocessors

Cadence uses the following subprocessors to run the service. Each is bound by a data processing agreement and processes data only on our instructions:

| Subprocessor | Purpose | Region |
|---|---|---|
| [TBD: hosting/DB provider] | Database and application hosting | [TBD] |
| [TBD: email provider] | Privacy contact and transactional email | [TBD] |
| [TBD: error monitoring, if any] | Error tracking | [TBD] |

The current list is always at [TBD URL]. We update it when it changes.

## 7. International transfers

[If all subprocessors are in your region: "All subprocessors are in [TBD region]; no international transfers."]

[If any are not: "Some subprocessors are based outside your country. Where data is transferred internationally, we rely on Standard Contractual Clauses or equivalent safeguards. Details available on request."]

## 8. How long we keep your data

- **Submitted code, attempts, timing, names** are kept for the period your teacher sets, then deleted:
  - **Quick session mode**: 24 hours, 7 days, or 30 days (default 7).
  - **Course mode**: 24 hours to 12 months (default 3 months, or 30 days after course end).
- **Cohort-level aggregates** (means and percentages, cohorts of 10 or more) are kept indefinitely in fully anonymous form. Individual records are removed from the aggregate if you exercise your right to erasure before expiry.
- **Teacher account data**: until you close the account, then 30 days.
- **Backups**: 30 days, encrypted; deletions propagate within this window.
- **Access logs** (who viewed what): 12 months, for breach forensics and accountability.

We never retain data past the teacher-set expiry except where law requires it.

## 9. What we never do

- Never train any model on your code, submissions, or behavior.
- Never sell, license, or transfer your data.
- Never use your data for cross-course or cross-institution analytics.
- Never use your data for advertising.
- Never retain your data past the teacher-set expiry except where law requires it.

## 10. Your rights

You have the following rights under GDPR (and equivalent rights under UK GDPR, India's DPDPA, and other regimes):

| Right | How to exercise |
|---|---|
| **Access** (Article 15) — see what we hold about you | `%cadence_my_data` in your notebook, or email privacy@ |
| **Portability** (Article 20) — download your data | `%cadence_export_my_data` (returns JSON), or email privacy@ |
| **Erasure** (Article 17) — have your data deleted | `%cadence_delete_my_data` in your notebook, or contact your teacher, or email privacy@ |
| **Rectification** (Article 16) — correct your data | Ask your teacher, or email privacy@ |
| **Restriction** (Article 18) — pause processing during a dispute | Email privacy@ |
| **Objection** (Article 21) — object to processing based on legitimate interest | Email privacy@ |

For requests made outside an active notebook, we verify identity through your teacher (the controller) as the primary path, or via your institution if needed.

We respond within one month, extendable to three for complex requests. We will tell you if we extend.

## 11. Right to complain to a supervisory authority

You can complain to a data protection authority at any time. Authorities for our launch markets:

- **UK**: Information Commissioner's Office — ico.org.uk
- **India**: Data Protection Board of India (under DPDPA 2023)
- **US**: state attorneys general handle privacy enforcement; FERPA complaints go to the U.S. Department of Education Student Privacy Policy Office
- **EU** (if you are an EU resident): the national DPA where you live

## 12. Children

Cadence is intended for students aged 13 or older. Where students under 13 use Cadence (US — COPPA), or where local law requires parental consent for older minors (India — DPDPA 2023 requires it for all under-18s; some EU member states under GDPR Article 8), the school or institution acts as controller and is responsible for the consent chain. Teachers attest to this at signup.

## 13. Security

- HTTPS in transit; encryption at rest by default.
- Access controls: only your teacher's authenticated session can fetch your data.
- Access logging: every read of identifiable student data is logged with teacher ID, timestamp, and affected student ID.
- 2FA available for teacher accounts and surfaced during onboarding.

If a personal data breach occurs that poses a risk to you, we will notify the relevant supervisory authority within 72 hours where required (GDPR Article 33), and notify affected users where the risk is high (Article 34).

## 14. Cookies and tracking

The Cadence dashboard uses only strictly-necessary cookies for authentication. We do not use analytics, advertising, or third-party tracking cookies.

[TBD: confirm and update if you add any analytics — even self-hosted Plausible or similar should be declared.]

## 15. Automated decision-making

Cadence does not make automated decisions that produce legal or similarly significant effects about you. Your teacher may use the information Cadence shows them to inform their teaching; any decisions about you (e.g., grading) are made by your teacher, not by Cadence.

## 16. Changes to this notice

When we update this notice we will post the new version at cadence.app/privacy and flag material changes at the top of the page for 30 days.

## 17. Contact

- **Email**: privacy@cadence.app
- **Postal**: [TBD]

---

# Appendix: Just-in-time notice (short form for join page and first magic command)

This is the short notice rendered at point of collection, satisfying GDPR Article 13's "at the time of collection" requirement.

> **Before you join**
>
> Cadence shows your teacher your real-time progress through this lesson.
>
> **What's collected**: your display name, which checkpoints you complete, how many attempts, when, and the code you submit.
> **Who sees it**: your teacher only.
> **How long**: [retention value set by teacher, shown here], then deleted.
> **Your rights**: you can see your data, download it, or delete it at any time with `%cadence_my_data`, `%cadence_export_my_data`, `%cadence_delete_my_data`.
>
> [Full privacy notice](TBD URL) • [Your DPA contact](TBD URL)
>
> By joining, you acknowledge this notice. You can choose not to join.
