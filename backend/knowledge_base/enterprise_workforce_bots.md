# Enterprise Workforce Bots, Domain Pain Points & Governance Policies

## 1. Customer Support & Payments Bot (support_bot)
- **Domain:** Support & Customer Escalations
- **Core Pain Point 1: Stuck UPI Debited Without Credit:**
  - *Trigger Condition:* Customer bank account debited (DEBITED), NPCI network switch indicates SUCCESS, but merchant switch indicates UNCREDITED/PENDING.
  - *Policy & Guardrails:* RULE_PAYMENT_REVERSAL_01. Instant reversal permitted only for Prime tier users (CIBIL >= 750) and transactions <= ₹5,000. Subprime CIBIL (<650) or amounts > ₹5,000 must be held for human specialist sign-off.
  - *Edge Cases:* SHA-256 Idempotency lock on case ID prevents duplicate refund issuance during network timeout retries.
- **Core Pain Point 2: RBI T+1 SLA Breach with Compensation:**
  - *Trigger Condition:* Customer refund exceeds RBI Harmonisation turnaround time (T+1 days).
  - *Policy & Guardrails:* RBI Harmonisation Mandate Section 3. Autonomous ₹100/day statutory customer compensation clock activated; statutory penalty capped at transaction principal.
  - *Edge Cases:* Dispatches NPCI bank chase escalation API. Verifies nodal escrow ledger before escalation.
- **Core Pain Point 3: Bounced Bank Refund due to Frozen Account:**
  - *Trigger Condition:* Core banking webhook reports return code ACCOUNT_FROZEN, DORMANT, or INVALID_IFSC.
  - *Policy & Guardrails:* RULE_WALLET_FALLBACK_CREDIT. Fallback automatically issues instant credit to customer's linked ZeroTouch Digital Wallet.
  - *Edge Cases:* Validates wallet KYC tier and monthly credit limit headroom. Fallback to verified bank account update prompt if wallet KYC is expired.

## 2. Finance Reconciliation Bot (finance_bot)
- **Domain:** Finance & Nodal Statement Reconciliation
- **Core Pain Point 1: 3-Way Nodal Statement Reconciliation Variance:**
  - *Trigger Condition:* Nodal bank payout statement line (e.g., STMT-902, ₹49,000) does not match merchant settlement ledger (₹50,000).
  - *Policy & Guardrails:* SOX Section 404 Nodal Escrow Reconciliation. Decomposes variance into Merchant Discount Rate (MDR ₹847.46 at 1.7%) plus 18% GST (₹152.54), explaining ₹1,000 discrepancy with zero unexplained delta.
  - *Edge Cases:* Discrepancies > ₹5,000 without explanation are marked UNRECONCILED and routed to Financial Controller.
- **Core Pain Point 2: Duplicate Payout Detection & Prevention:**
  - *Trigger Condition:* Identical bank debit line on Vendor Invoice appears twice within 14 seconds.
  - *Policy & Guardrails:* RULE_DUPLICATE_PAYOUT_HALT. Strictly halts autonomous clearing and alerts Senior Accounts Payable Specialist. AI can never self-clear duplicate payout lines.
  - *Edge Cases:* Prepares vendor debit note and offsets duplicate amount against future scheduled payables.
- **Core Pain Point 3: Expired KYC Merchant Settlement Hold:**
  - *Trigger Condition:* Merchant Director PAN or GSTIN expired before daily escrow settlement release.
  - *Policy & Guardrails:* RBI Master Direction Section 4.2 KYC Settlement Gate. Autonomous release is strictly held. Requires dual human sign-off (Compliance Officer & Finance Lead).
  - *Edge Cases:* Auto-dispatches secure re-verification upload link to merchant while holding escrow funds safely.

## 3. IT Access & Service Desk Bot (it_access_bot)
- **Domain:** IT Operations & Identity Access Management (IAM)
- **Core Pain Point 1: Repetitive Standard Software Licensing (Okta):**
  - *Trigger Condition:* Employee requests standard software licenses (Figma Pro for Designers, GitHub Enterprise for Developers).
  - *Policy & Guardrails:* RULE_STANDARD_ROLE_ENTITLEMENT. Verifies role in Okta directory and auto-provisions pre-approved standard bundle licenses via API.
  - *Edge Cases:* Requests for non-standard tools are automatically rerouted to departmental manager for approval.
- **Core Pain Point 2: High-Risk Privileged Access Attempt:**
  - *Trigger Condition:* Request for elevated infrastructure credentials (AWS Root, Production Database Superuser, Vault Admin).
  - *Policy & Guardrails:* RULE_NEVER_AUTOMATE_PRIVILEGED_ACCESS. Hard compliance guardrail; autonomous granting is unconditionally blocked. Requires dual out-of-band signatures (CISO + VP Engineering).
  - *Edge Cases:* Zero-Touch AI cannot grant root access to itself or any employee.
- **Core Pain Point 3: Zero-Touch Deprovisioning on Role Change:**
  - *Trigger Condition:* HRIS event signals employee transfer to another team or department.
  - *Policy & Guardrails:* Principle of Least Privilege. Automatically revokes obsolete SaaS seats (e.g. HubSpot Enterprise when moving to Design) to eliminate subscription waste.
  - *Edge Cases:* Verifies and reassigns shared project assets before seat revocation to prevent orphaned collateral.

## 4. Talent & HR Operations Bot (hiring_bot)
- **Domain:** Human Resources & Talent Acquisition
- **Core Pain Point 1: Unconscious Bias & PII in Candidate Screening:**
  - *Trigger Condition:* New candidate resumes submitted for technical role.
  - *Policy & Guardrails:* RULE_FAIRNESS_ANONYMIZATION & RULE_NEVER_AUTO_REJECT_CANDIDATE. Fairness filter strips gender, age, photo, marital status, and residential address before rubric grading. AI can NEVER autonomously reject a human candidate.
  - *Edge Cases:* Scores only objective technical criteria (System Architecture, Fintech Domain, Coding). All rejection decisions remain with human recruiters.
- **Core Pain Point 2: Interview Panel Scheduling Overhead:**
  - *Trigger Condition:* Candidate qualifies with rubric score >= 80%.
  - *Policy & Guardrails:* Recruiter Consent Gate. Dispatches 4-person technical interview panel calendar invitations.
  - *Edge Cases:* Automatically substitutes backup interviewers if primary interviewer is out of office.
- **Core Pain Point 3: Automated New-Hire Onboarding Roadmap:**
  - *Trigger Condition:* Candidate offer accepted.
  - *Policy & Guardrails:* HR Onboarding Baseline SLA (Day 1 Readiness). Generates 30-60-90 day milestone checklist, pairs onboarding buddy, tracks laptop shipment, and coordinates standard IT software access.
  - *Edge Cases:* Dynamically adapts orientation schedule across remote employee timezones.

## 5. New Joiner Academy Coach (academy_bot)
- **Domain:** Operator Training & Continuous Learning
- **Core Pain Point 1: Slow Operator Ramp-Up on Complex Disputes:**
  - *Trigger Condition:* Trainee begins multi-ledger dispute training.
  - *Policy & Guardrails:* Zero-Risk Production Isolation Guardrail. Replays anonymized historical edge case dispute (REPLAY-UPI-404) with zero financial risk to real customer funds.
  - *Edge Cases:* Multi-ledger conflicts simulate real-world discrepancies for safe operator practice.
- **Core Pain Point 2: Inconsistent Decision-Making Across Operators:**
  - *Trigger Condition:* Trainee submits multi-ledger resolution decision.
  - *Policy & Guardrails:* Policy Adherence Scoring. Evaluates operator reasoning against canonical banking policies and updates competency radar scores.
  - *Edge Cases:* Provides immediate pedagogical feedback if trainee makes risky moves (like premature double-refunding).
- **Core Pain Point 3: Standardizing Expert Workflows into L1 Skills:**
  - *Trigger Condition:* Expert demonstrates workflow actions.
  - *Policy & Guardrails:* Governor Invariant Gate. Synthesizes typed SkillSpec and executes 12-case historical backtest before supervised promotion to Level 1 autonomy.
