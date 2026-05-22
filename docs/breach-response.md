# Breach response — Cadence

**Owner:** Liv Vage
**Last updated:** 2026-05-22
**Status:** v1, solo-operator scale

This is the playbook for handling a personal data breach affecting Cadence
users. It exists because GDPR Article 33 requires notification to the
supervisory authority within 72 hours of becoming aware, and Article 34
requires notifying affected users when the breach poses a high risk to
their rights and freedoms.

---

## What counts as a breach

Any event that compromises the confidentiality, integrity, or availability
of personal data:

- Unauthorized access to the database (e.g., compromised admin account, SQL
  injection, exposed credentials).
- Accidental disclosure (e.g., a teacher's dashboard URL ending up in a
  public log; an export sent to the wrong recipient).
- Loss of access (e.g., ransomware, accidental mass deletion that we cannot
  restore from backups).
- A subprocessor (GCP, GitHub) notifies us of a breach affecting their
  systems that could include our data.

If unsure: assume yes, start the clock, downgrade later if it turns out not
to qualify.

---

## Step-by-step

### Hour 0 — discovery

The clock starts when you become *aware* — not when the breach happened.

1. **Write down what you know** in `incidents/<date>-<short-slug>.md`:
   - What was observed and how (log entry, user report, vendor email).
   - When the underlying event probably occurred.
   - Best guess at what data is affected and how many people.
   - Whether the breach is still ongoing.
2. **Stop the bleeding** if possible: rotate compromised credentials,
   revoke a leaked token, take an affected service offline.

### Hour 0–4 — assess

3. **Scope the affected data**:
   - Students (display name, attempts, code submissions, timing)?
   - Teachers (email, password hash, GitHub ID)?
   - Cohort-level aggregates only?
4. **Assess risk to rights and freedoms** using GDPR's framing:
   - Could this enable identity theft, fraud, financial loss, reputational
     damage, or discrimination?
   - Could this reveal data about minors?
   - Could the data, even if pseudonymous, be linked back to identifiable
     individuals (stylometric attack on submitted code, behavioral
     fingerprinting from timing)?
5. **Decide notification level**:
   - **DPA only** (Article 33): default for any breach involving personal
     data.
   - **DPA + affected users** (Article 34): when the risk to users is high.
     For Cadence, this likely means any unauthorized exfiltration of
     submitted code, timing data, or display names.
   - **No notification**: rare. Only when the risk is genuinely negligible
     (e.g., encrypted backup leaked but key was not compromised).

### Hour 4–48 — notify the DPA

6. **Prepare the notification**. Each launch-market DPA has its own form;
   the substance is the same:
   - Nature of the breach.
   - Categories and approximate number of data subjects.
   - Categories and approximate number of records.
   - Likely consequences.
   - Measures taken or proposed to address it.
   - Contact point for follow-up: `privacy@cadence-dash.com`.

   Launch-market DPAs:
   - **UK**: ICO, ico.org.uk/for-organisations/report-a-breach/.
   - **India**: Data Protection Board of India (under DPDPA 2023).
   - **US**: state-level. Notify the affected user's state AG if required by
     that state's breach-notification law (varies; California's CCPA and
     Massachusetts' 201 CMR 17 are the strictest).
   - **EU**: the lead authority in the country where the data subject lives.
7. **Submit** within 72 hours of awareness. If you miss the window, note
   the reason in the submission — late notification is acceptable with a
   reason, but silently missing the deadline is not.

### Hour 48–72 — notify affected users (if Article 34 applies)

8. **Draft the user notice**:
   - Plain language, no jargon.
   - What happened, when, what data, what we're doing about it.
   - What they can do (rotate passwords if relevant, monitor for misuse).
   - Contact: `privacy@cadence-dash.com`.
9. **Send by email** to affected teacher accounts. Students don't have
   direct contact info — notify via the controller (their teacher) where
   the teacher account is reachable; otherwise via the privacy notice page
   with a prominent banner.

### Day 1+ — fix and post-mortem

10. **Fix the root cause**. Don't just patch the immediate symptom.
11. **Write the post-mortem** in `incidents/<date>-<short-slug>.md`:
    - Timeline.
    - Root cause.
    - What we changed.
    - What we'd do differently next time.
12. **Update this document** if the incident exposed a gap in this
    playbook.

---

## Roles at solo-operator scale

- **Liv Vage** — does everything: discovery, scope, decision to notify,
  DPA notification, user notification, fix, post-mortem.
- **Princeton supervisor** — informed if the breach affects Princeton
  students or course material.
- **Affected institutions** — informed via their named DPA point of
  contact in the DPA they signed (if any).

When you have a co-maintainer, split roles: incident commander, comms,
remediation. Until then, you're all three.

---

## Decision aids

**"Is this a breach?"**
> If a stranger could now see, change, or delete data they had no right to
> — it's a breach. Even if the impact is small.

**"Article 33 or also Article 34?"**
> Article 34 (user notification) kicks in when there's a *high* risk to
> rights and freedoms. For Cadence: any unauthorized access to submitted
> code, behavioral data, or identifiable display names = high risk =
> notify users. Encrypted backup leak with intact key custody = Article
> 33 only.

**"Should I notify a DPA in a country I'm not based in?"**
> Yes if the breach affects data subjects in that country and it's a
> launch market. Use the user's country, not yours.

---

## Templates

### Incident log skeleton

```markdown
# Incident: <short title>
- **Date observed:** YYYY-MM-DD HH:MM UTC
- **Date occurred (best guess):** YYYY-MM-DD
- **Observer:** <name>
- **Status:** open | contained | resolved

## What happened
<plain language description>

## Data affected
- Categories: ...
- Approximate count: ...
- Subprocessors involved: ...

## Risk assessment
- Article 33 trigger: yes/no, why
- Article 34 trigger: yes/no, why
- Affected jurisdictions: ...

## Timeline
- HH:MM UTC — ...

## Notification
- DPA(s) notified: ...
- Users notified: yes/no, when
- Reference numbers: ...

## Root cause
<after fix>

## Remediation
<what we changed>

## Post-mortem learnings
<what we'd do differently>
```

### User notification email skeleton

> Subject: Important notice about your Cadence data
>
> Hi,
>
> We're writing to tell you about a data incident affecting your Cadence
> account.
>
> **What happened:** <plain language, 1–2 sentences>
> **When:** <approximate dates>
> **What data was involved:** <specific categories>
> **What we've done:** <containment + remediation>
> **What you can do:** <specific actions, e.g., rotate password>
>
> We've notified the [relevant DPA(s)] under GDPR Article 33. You have the
> right to lodge a complaint with your national data protection authority
> at any time.
>
> If you have questions, reply to this email or write to
> privacy@cadence-dash.com.
>
> — Liv
