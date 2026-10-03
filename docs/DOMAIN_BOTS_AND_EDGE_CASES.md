# ZeroTouch AI Workforce: Domain Bots, Pain Points & Edge Cases Reference Manual

## 1. Executive Summary & Architectural Overview

The ZeroTouch AI Workforce replaces rigid rule scripts and error-prone manual operator queues with **domain-specialized autonomous bots**. Built on a **Least-Privilege Tool Architecture** and powered by **xAI Grok (with deterministic local domain intelligence fallback)**, each bot is scoped to a specific business function with explicit boundaries, hard compliance guardrails, and cryptographic auditability.

```
+----------------------------------------------------------------------------------------------------+
|                                    ZeroTouch Employee Workspace                                     |
+----------------------------------------------------------------------------------------------------+
       |                                |                             |                         |
       v                                v                             v                         v
+------------------+          +-------------------+         +-------------------+     +------------------+
|   Customer       |          |      Finance      |         |     IT Access     |     |   Talent & HR    |
|   Support Bot    |          |  Reconciliation   |         |    Service Desk   |     |  Operations Bot  |
+------------------+          +-------------------+         +-------------------+     +------------------+
| • Stuck UPI      |          | • 3-Way Variance  |         | • Standard Lic.   |     | • Bias-Free Rub. |
| • RBI SLA Chase  |          | • Duplicate Pay.  |         | • Privileged Gate |     | • Panel Sched.   |
| • Bounced Wallet |          | • Expired KYC     |         | • Deprovisioning  |     | • Onboarding     |
+------------------+          +-------------------+         +-------------------+     +------------------+
       |                                |                             |                         |
       +--------------------------------+-----------------------------+-------------------------+
                                        |
                 +---------------------------------------------+
                 |       xAI Grok & Domain Decision Engine     |
                 | • Model: grok-4.7 / grok-2-latest           |
                 | • Structured Tool Calling & PII Redaction   |
                 | • Resilient Offline Deterministic Fallback  |
                 | • Policy & Autonomy Governor Supervision    |
                 +---------------------------------------------+
                                        |
                 +---------------------------------------------+
                 |        Action Gateway (Idempotent API)      |
                 | • Real Banking Rails, Okta, ATS, & Ledgers  |
                 +---------------------------------------------+
```

---

## 2. xAI Grok Integration & Model Orchestration

### 2.1 Model Selection & API Configuration
- **Endpoint**: `https://api.x.ai/v1/chat/completions`
- **Default Model**: `grok-4.7` (configurable via `XAI_MODEL` environment variable, with support for `grok-2-latest` and `grok-beta`).
- **Authentication**: `Bearer ${XAI_API_KEY}` from `backend/.env`.

### 2.2 Security, PII Stripping, & Prompt Boundary Protection
- **PII Filtering**: Case evidence passed to the model undergoes mandatory redaction of sensitive identifiers:
  - `name`, `customer_name`, `email`, `phone`, `cibil_score`, `candidate_id`, `employee_id`, `transaction_id`, `risk_score`.
- **Untrusted Input Protection**: Case evidence is strictly segregated in system prompt delimiters and marked as untrusted data to mitigate indirect prompt injection attacks.
- **Read-Only Model Execution**: In accordance with the Principle of Least Privilege, external LLM calls are strictly restricted to read-only tool introspection. The LLM cannot directly mutate financial ledgers, revoke access, or alter records; every mutation is staged and executed via the **Action Gateway** under human supervisory control.

### 2.3 Resilient Local Domain Fallback & Dual-LLM Routing
- When `XAI_API_KEY` is configured but the team credit quota is pending renewal (`401` / `403 Permission Denied`), the system automatically routes to **Google Gemini 3.8 Flash** with **RAG Knowledge Base Orchestration**.
- The fallback executes identical read-only connector inspection, policy evaluation, and action staging, providing full functionality and zero user disruption.
- UI status pills explicitly differentiate between live `xAI Grok` inference, `Google Gemini 3.8 Flash (RAG Orchestrated)`, and `ZeroTouch Domain Intelligence (Local Engine)`.

### 2.4 RAG (Retrieval-Augmented Generation) Policy Knowledge Orchestrator
- **Knowledge Base Location**: `backend/knowledge_base/` containing markdown policy manuals (`paytm_refund_policy.md`, `enterprise_workforce_bots.md`).
- **Embedding Model**: `gemini-embedding-001` with cosine similarity retrieval.
- **Workflow Orchestration**:
  1. Every incoming operator request or domain bot chat query triggers `search_policy()` across the internal knowledge repository.
  2. Authoritative policy clauses (e.g. RBI T+1 compensation formulas, SOX Section 404 MDR fee itemization, Okta RBAC tool matrix, fair candidate anonymization rules) are dynamically injected into the system instruction prompt.
  3. The response includes structured plan traces, verified invariants, specific edge-case mitigations, and the exact grounding RAG context.
  4. The frontend UI renders a dedicated **RAG Policy Knowledge Base Grounding** view for every response.

---

## 3. Domain Bots: Pain Points & Edge Cases Catalog

---

### 3.1 Customer Support & Payments Bot (`support_bot`)
*Mission: Real-time payment reconciliation, RBI SLA compliance, and failed refund remediation.*

#### Pain Point 1: Stuck UPI Debited Without Credit
- **Problem**: Customer paid via UPI, their bank account debited ₹2,500, but merchant switch shows `NOT_CREDITED` or pending. Customer is stranded at checkout.
- **AI Chatbot Solution**:
  1. Queries 4 internal ledgers: Core Bank (`DEBITED`), NPCI UPI Switch (`SUCCESS`), Merchant Ledger (`NOT_CREDITED`), Settlement Ledger (`NOT_FOUND`).
  2. Pulls customer risk profile: Prime Tier (CIBIL 785, Risk Score 0.08).
  3. Evaluates `RULE_PAYMENT_REVERSAL_01`.
  4. Stages instant reversal via Action Gateway (`REV-TX9281-IDEM`) with cryptographic idempotency key.
- **Edge Cases Handled**:
  - *Subprime Risk Tier*: If CIBIL score is <650 or transaction amount exceeds ₹5,000 threshold, automated reversal is held and routed for manual fraud desk sign-off.
  - *Network Switch Timeout*: If NPCI switch is unresponsive (`TIMEOUT`), bot verifies Core Bank debit confirmation before initiating reversal, preventing uncollected reversals.
  - *Replay & Duplicate Risk*: Reversal key generated using `SHA-256(txn_id + amount + timestamp)` ensures identical retry attempts never execute double refunds.
- **Policy Invariant**: `RULE_PAYMENT_REVERSAL_01 (Prime CIBIL ≥ 750)`.

#### Pain Point 2: RBI T+1 SLA Breach with Mandatory Compensation
- **Problem**: Customer refund delayed beyond the Reserve Bank of India (RBI) Harmonisation of Turnaround Time (T+1 mandate). Customer files formal grievance demanding statutory compensation.
- **AI Chatbot Solution**:
  1. Identifies delayed refund transaction (e.g. `RF202`, ₹1,800).
  2. Queries HDFC acquiring switch and verifies delay exceeds T+1 deadline by 24h+.
  3. Calculates statutory compensation: ₹100 per calendar day of delay beyond T+1.
  4. Dispatches bank escalation chase via NPCI gateway (`CHASE-RF202-HDFC`).
  5. Stages customer communication advisory with real-time tracking link and compensation guarantee.
- **Edge Cases Handled**:
  - *Bank Dispute (Gateway claims refund settled)*: Bot verifies nodal escrow debit line before issuing compensation, preventing double payouts.
  - *Maximum Compensation Cap*: Statutory compensation is automatically capped at the principal transaction value.
  - *Weekend / Bank Holiday Buffer*: Turnaround clock dynamically discounts non-clearing bank settlement holidays per RBI calendar.
- **Policy Invariant**: `RBI Harmonisation Mandate §3 (T+1 Auto-Compensation)`.

#### Pain Point 3: Bounced Bank Refund due to Frozen Account
- **Problem**: Automated refund bounced back with bank return code `ACCOUNT_FROZEN` or `INVALID_IFSC`. Customer cannot receive bank deposits.
- **AI Chatbot Solution**:
  1. Intercepts bounced webhook from beneficiary bank gateway.
  2. Verifies customer's active ZeroTouch Digital Wallet status and KYC limits.
  3. Executes fallback policy `RULE_WALLET_FALLBACK_CREDIT`: credits funds instantly to customer digital wallet.
  4. Dispatches SMS/push alert instructing customer on wallet fund utilization.
- **Edge Cases Handled**:
  - *Wallet KYC Expired / Limit Exceeded*: If wallet monthly credit limit is exhausted, bot suspends automated wallet transfer and sends a verified in-app link to update bank details.
  - *Customer Account Inactive*: Flags case as `ESCALATED_KYC_HOLD` and assigns to senior operations queue.
- **Policy Invariant**: `RULE_WALLET_FALLBACK_CREDIT (ZeroTouch Digital Wallet)`.

---

### 3.2 Finance Reconciliation Bot (`finance_bot`)
*Mission: 3-way nodal statement matching, fee and tax variance isolation, and duplicate payout detection.*

#### Pain Point 1: 3-Way Nodal Statement Reconciliation Variance
- **Problem**: Bank settlement statement line (`STMT-902`) shows payout of ₹49,000, while internal merchant ledger records ₹50,000 (shortfall of ₹1,000). Finance analysts spend hours manually parsing spreadsheets.
- **AI Chatbot Solution**:
  1. Ingests bank statement feed and matches against merchant settlement batch `S302`.
  2. Decomposes ₹1,000 delta into constituent fee components:
     - Base MDR Fee (1.7% on transaction): **₹847.46**
     - GST (18% on MDR): **₹152.54**
     - Total Explained: **₹1,000.00** (Zero unexplained variance).
  3. Stages verified journal adjustment entry `JRNL-STMT-902-EXPENSE_OFFSET`.
- **Edge Cases Handled**:
  - *Unexplained Shortfall*: Discrepancies > ₹5,000 or variances that do not mathematically match MDR + GST are flagged as `UNRECONCILED_MISMATCH` and routed to the Financial Controller.
  - *SOX Compliance*: Every automated offset attaches full audit metadata (value date, bank ref, tax schedule) for external auditor review.
- **Policy Invariant**: `SOX Section 404 Nodal Escrow Reconciliation`.

#### Pain Point 2: Duplicate Payout Detection & Prevention
- **Problem**: Due to network retries or vendor webhook duplicates, identical payout lines (`STMT-904`, ₹12,000) appear on the bank feed within seconds.
- **AI Chatbot Solution**:
  1. Runs hash comparison and timestamp proximity matching across outward bank statement lines.
  2. Flags duplicate payment collision on Vendor Invoice `#4491`.
  3. Enforces `RULE_DUPLICATE_PAYOUT_HALT`: halts automated ledger clearing immediately.
  4. Drafts accounts payable recovery clawback demand letter and alerts Senior AP Analyst.
- **Edge Cases Handled**:
  - *Funds Already Withdrawn*: If beneficiary bank confirms withdrawal, bot places a temporary debit hold on merchant's future daily payables to recover the excess payout.
  - *Legitimate Multiple Payments*: If invoice has legitimate multi-tranche terms, analyst can override hold with dual-approval.
- **Policy Invariant**: `RULE_DUPLICATE_PAYOUT_HALT (Never Auto-Clear Duplicates)`.

#### Pain Point 3: Expired KYC Merchant Settlement Hold
- **Problem**: Merchant settlement batch of ₹145,000 (`S306`) is ready for release, but merchant director PAN and GSTIN verification expired yesterday.
- **AI Chatbot Solution**:
  1. Scans pending escrow settlement batches against corporate compliance directory.
  2. Identifies lapsed KYC status on batch `S306`.
  3. Enforces RBI Payout Direction §4.2: halts autonomous payout and triggers human compliance approval gate.
  4. Dispatches automated re-verification notification to merchant.
- **Edge Cases Handled**:
  - *Emergency Merchant Escalation*: Bot allows partial release only up to ₹10,000 with mandatory AML Officer override, keeping ₹135,000 in secure escrow.
  - *Revoked Business License*: Directs case to Legal & Compliance review desk.
- **Policy Invariant**: `RBI Master Direction §4.2 KYC Settlement Gate`.

---

### 3.3 IT Access & Service Desk Bot (`it_access_bot`)
*Mission: Zero-touch standard software licensing, role deprovisioning, and privileged access guardrails.*

#### Pain Point 1: Repetitive Standard Software Licensing (Okta / GitHub / Figma)
- **Problem**: Employees wait 48 hours for standard software licenses (e.g. Product Designer requesting Figma Pro, or Backend Engineer requesting GitHub Enterprise). IT service desk backlogs swell.
- **AI Chatbot Solution**:
  1. Queries employee profile in Okta / Workday enterprise directory (e.g. `EMP-8821`, Rohan Joshi, Product Designer).
  2. Checks requested tool against Role-Based Access Control (RBAC) standard bundle (`RULE_STANDARD_ROLE_ENTITLEMENT`).
  3. Confirms tool is pre-approved and has zero elevated root privileges.
  4. Calls enterprise license connector gateway and provisions license seat instantly (`GRN-8821-FIGMA`).
- **Edge Cases Handled**:
  - *Non-Standard Tool Request*: If Product Designer requests AWS CloudWatch Admin, bot flags request as out-of-bundle and routes to Departmental Manager for approval.
  - *Seat Limit Exhausted*: If enterprise license pool is full, bot alerts IT Asset Management to purchase seat bundles while queuing the employee request.
- **Policy Invariant**: `RULE_STANDARD_ROLE_ENTITLEMENT (Pre-approved RBAC Matrix)`.

#### Pain Point 2: High-Risk Privileged Access Attempt (AWS Root / Prod DB)
- **Problem**: Contractor or developer requests AWS root credentials, production database admin, or Okta super admin access.
- **AI Chatbot Solution**:
  1. Inspects tool request for privileged permissions.
  2. Evaluates Autonomy Governor rule `RULE_NEVER_AUTOMATE_PRIVILEGED_ACCESS`.
  3. Blocks automated provisioning unconditionally.
  4. Generates high-priority security ticket with mandatory dual-signature requirement (CISO + VP Engineering).
- **Edge Cases Handled**:
  - *P1 Production Outage Emergency*: Bot provides time-bounded (2-hour), read-only observability telemetry access with active session recording, strictly refusing write/root access.
  - *Audit Logging*: Every privileged access request logs origin IP, employee ID, and policy violation details to immutable security logs.
- **Policy Invariant**: `RULE_NEVER_AUTOMATE_PRIVILEGED_ACCESS (Hard Compliance Gate)`.

#### Pain Point 3: Zero-Touch Deprovisioning on Role Change
- **Problem**: When employees transfer departments (e.g. Marketing to Product), expensive SaaS licenses (HubSpot Enterprise, ₹8,200/mo) remain active indefinitely, leading to license sprawl and security risk.
- **AI Chatbot Solution**:
  1. Listens to HRIS role transfer events.
  2. Performs diff of previous department bundle against new role bundle.
  3. Reassigns project asset ownership to prevent orphaned files.
  4. Deprovisions obsolete SaaS seats, returning licenses to the corporate pool.
- **Edge Cases Handled**:
  - *Orphaned Repositories / Campaigns*: Bot verifies no active production pull requests or live marketing campaigns are owned solely by the employee before license revocation.
  - *Immediate Rehire / Sabbatical*: Retains account data in cold archive for 30 days before permanent seat deletion.
- **Policy Invariant**: `Principle of Least Privilege (Zero-Trust Deprovisioning)`.

---

### 3.4 Talent & HR Operations Bot (`hiring_bot`)
*Mission: Bias-free candidate rubric scoring, automated panel scheduling, and onboarding orchestration.*

#### Pain Point 1: Unconscious Bias & PII in Candidate Screening
- **Problem**: Human resume screening is prone to unconscious demographic bias (gender, age, photo, residential location, or non-target university pedigree).
- **AI Chatbot Solution**:
  1. Applies Fairness & Anonymization Filter: strips all protected personal attributes (name, photo, gender, age, marital status, location).
  2. Evaluates candidate against objective job rubric criteria:
     - System Design & Distributed Architecture (9/10)
     - Fintech & Payments Domain Experience (8/10)
     - Python & Microservices Concurrency (9/10)
     - Cultural & Team Leadership (8/10)
     - Overall Rubric Score: **85.0%**
  3. Generates transparent scorecard with explainable evidence citations.
- **Edge Cases Handled**:
  - *Low Candidate Score*: Strict invariant `RULE_NEVER_AUTO_REJECT_CANDIDATE` — the AI bot can **never** autonomously issue a rejection letter. Rejection authority remains exclusively with the human recruiter.
  - *Non-Standard Resume Formats*: Multi-column PDF parsing extracts structured skills without losing context.
- **Policy Invariant**: `RULE_FAIRNESS_ANONYMIZATION & RULE_NEVER_AUTO_REJECT_CANDIDATE`.

#### Pain Point 2: Interview Panel Scheduling Overhead
- **Problem**: Coordinating 4 senior engineering interviewers across calendars takes 3–5 days of back-and-forth emails per qualified candidate.
- **AI Chatbot Solution**:
  1. Confirms candidate scored ≥ 80% on the objective rubric.
  2. Queries Google Calendar / Microsoft Graph API for 4 senior engineering interviewers.
  3. Identifies optimal conflict-free 60-minute interview slot.
  4. Dispatches calendar invitations with anonymized candidate brief (`SCHED-9102-PANEL`).
- **Edge Cases Handled**:
  - *Interviewer Last-Minute Decline*: Bot automatically identifies backup approved interviewers from the designated engineering interview pool and swaps the calendar invite.
  - *Candidate Timezone Mismatch*: Automatically converts and confirms interview time in candidate's local timezone.
- **Policy Invariant**: `Candidate Consent & Recruiter Sign-Off Gate`.

#### Pain Point 3: Automated New-Hire Onboarding Roadmap
- **Problem**: New employees face first-day friction with missing laptops, lack of buddy assignment, and unclear 30-60-90 day milestones.
- **AI Chatbot Solution**:
  1. Synthesizes personalized 30-60-90 day onboarding roadmap based on role level.
  2. Integrates with IT Bot to track laptop shipping and pre-stage software licenses.
  3. Automatically assigns senior onboarding buddy and schedules Day 1 team sync.
- **Edge Cases Handled**:
  - *Remote vs. On-Site Logistics*: Dynamically routes hardware delivery to residential address with verified courier signature tracking.
  - *Delayed Hardware Delivery*: Prepares temporary virtual desktop access (VDI) so the employee can begin orientation without delay.
- **Policy Invariant**: `HR Onboarding Baseline SLA (Day 1 Readiness)`.

---

### 3.5 New Joiner Academy Coach (`academy_bot`)
*Mission: Safe sandbox practice on historical dispute cases, real-time AI grading, and skill synthesis.*

#### Pain Point 1: Slow Operator Ramp-Up on Complex Dispute Scenarios
- **Problem**: New support agents take 4–6 weeks before handling complex UPI payment disputes safely, risking live customer fund loss during onboarding.
- **AI Chatbot Solution**:
  1. Loads anonymized historical production replay cases (`REPLAY-UPI-404`).
  2. Presents realistic edge-case dispute scenario with conflicting ledger telemetry.
  3. Evaluates operator decision step-by-step against canonical policy rules.
  4. Generates real-time pedagogical feedback and updates competency radar chart.
- **Edge Cases Handled**:
  - *Premature Double-Refund Decision*: If trainee chooses to refund before verifying network status, AI Coach immediately intervenes, explains the duplicate debit risk, and logs training intervention.
  - *Zero Production Risk*: Sandbox operates in complete database isolation; zero live customer funds can be touched.
- **Policy Invariant**: `Zero-Risk Production Isolation Guardrail`.

#### Pain Point 2: Inconsistent Decision-Making Across Junior Operators
- **Problem**: Operators apply inconsistent refund thresholds, with some escalating valid prime cases and others auto-approving subprime risks.
- **AI Chatbot Solution**:
  1. Tests operators against boundary scenarios (e.g. CIBIL 649 vs 651, ₹4,999 vs ₹5,001).
  2. Scores decisions on Ledger Reconciliation, Policy Adherence, and Communication Tone.
  3. Grants L1 Autonomous Handling Certification only when operator achieves ≥ 85% score across 12 consecutive cases.
- **Policy Invariant**: `Policy Adherence Scoring Threshold ≥ 85%`.

#### Pain Point 3: Standardizing Expert Workflows into L1 Autonomous Skills
- **Problem**: Expert senior operators repeatedly perform repetitive manual workflows that should be automated, but engineering teams lack bandwidth to code bespoke pipelines.
- **AI Chatbot Solution**:
  1. Captures expert operator action sequence and natural-language "why" annotation.
  2. Synthesizes typed `SkillSpec` with declarative inputs, actions, and safety invariants.
  3. Executes a 12-case historical backtest against previous edge cases.
  4. Publishes skill at L1 supervised autonomy under Autonomy Governor trust scoring.
- **Policy Invariant**: `Autonomy Governor Invariant Verification Gate`.

---

## 4. Comprehensive Guardrail & Policy Invariants Table

| Domain | Policy Invariant Code | Policy Name | Enforcement Mechanism |
| :--- | :--- | :--- | :--- |
| **Support** | `RULE_PAYMENT_REVERSAL_01` | Stuck UPI Prime Reversal | Instant reversal permitted only if CIBIL ≥ 750, amount ≤ ₹5,000, and bank=DEBITED, merchant=NOT_CREDITED. |
| **Support** | `RBI_HARMONISATION_MANDATE_03` | RBI T+1 Auto-Compensation | Calculates statutory ₹100/day penalty for delays past T+1; caps compensation at transaction principal. |
| **Support** | `RULE_WALLET_FALLBACK_CREDIT` | Digital Wallet Fallback | Credits bounced bank refunds to linked digital wallet with unique SHA-256 idempotency hash. |
| **Finance** | `SOX_SEC_404_ESCROW_RECON` | Nodal Escrow Variance Isolation | Decomposes settlement variance into MDR + 18% GST; flags unexplained shortfall > ₹5,000 for Controller sign-off. |
| **Finance** | `RULE_DUPLICATE_PAYOUT_HALT` | Duplicate Payout Circuit Breaker | Halts automated bank clearing immediately upon hash collision; issues clawback hold. |
| **Finance** | `RBI_PAYOUT_DIRECTION_4_2` | Expired KYC Escrow Gate | Forbids autonomous release of settlement funds if merchant PAN/GSTIN verification lapsed. |
| **IT** | `RULE_STANDARD_ROLE_ENTITLEMENT` | Standard Tool Role Bundle | Permits zero-touch license provisioning only for tools within pre-approved role RBAC bundle. |
| **IT** | `RULE_NEVER_AUTOMATE_PRIVILEGED_ACCESS` | Privileged Root Access Gate | Unconditionally blocks automated granting of AWS Root, Prod DB Admin, or Okta Super Admin credentials. |
| **HR** | `RULE_FAIRNESS_ANONYMIZATION` | PII & Demographic Masking | Mandatory stripping of gender, age, photo, and address prior to rubric technical grading. |
| **HR** | `RULE_NEVER_AUTO_REJECT_CANDIDATE` | Human Hiring Authority Gate | AI is strictly prohibited from sending automated rejection notices to candidates. |
| **Academy** | `ZERO_RISK_SANDBOX_ISOLATION` | Training Production Isolation | Isolates trainee case replays in air-gapped sandbox without access to live transaction rails. |

---

## 5. Least-Privilege Bot Tool Matrix

| Bot ID | Permissioned Tool ID | Access Level | Purpose & Hard Boundary |
| :--- | :--- | :--- | :--- |
| `support_bot` | `payment_reconciliation` | Read-Only | Queries Core Bank, NPCI, and Merchant ledgers without modifying state. |
| `support_bot` | `payment_resolution` | Write (Post-Approval) | Executes idempotent state mutation via Action Gateway with cryptographic lock. |
| `support_bot` | `dispatch_bank_chase` | Write (Post-Approval) | Dispatches formal bank escalation API call and activates compensation clock. |
| `support_bot` | `issue_wallet_credit` | Write (Post-Approval) | Credits digital wallet for bounced bank refunds. |
| `finance_bot` | `query_bank_statement_lines` | Read-Only | Ingests nodal statement lines and detects fee matches or duplicate flags. |
| `finance_bot` | `reconcile_discrepancy` | Write (Post-Approval) | Posts verified journal adjustment entry to General Ledger. |
| `it_access_bot` | `lookup_employee_profile` | Read-Only | Inspects employee role and department in Okta / Workday directory. |
| `it_access_bot` | `check_tool_access_policy` | Read-Only | Checks RBAC entitlement matrix and verifies privileged tool boundaries. |
| `it_access_bot` | `grant_tool_license` | Write (Post-Approval) | Provisions SaaS seat in target tool API (Figma, GitHub, Slack). |
| `it_access_bot` | `teach_skill_spec` | Draft Mode | Synthesizes YAML/JSON skill spec from recorded user actions. |
| `it_access_bot` | `backtest_skill` | Simulation Mode | Runs 12 historical test cases against synthesized skill. |
| `it_access_bot` | `publish_skill_l1` | Write (Admin Approval) | Promotes skill to L1 supervised autonomy under Governor trust scoring. |
| `hiring_bot` | `candidate_evaluation` | Read-Only | Scores candidate against transparent rubric criteria with PII stripped. |
| `hiring_bot` | `schedule_interview_panel` | Write (Post-Approval) | Dispatches calendar invites to 4-person technical interview panel. |
| `academy_bot` | `get_replay_case` | Read-Only | Loads anonymized dispute replay case for operator training. |
| `academy_bot` | `evaluate_joiner_run` | Write (Sandbox) | Grades trainee responses and updates readiness radar chart. |

---

## 6. Verification and Testing Runbook

To verify that all domain bots, pain point handlers, and guardrails are operational:

1. **Unit & Integration Suite**:
   ```powershell
   python -m pytest backend/test_workforce.py backend/test_suite.py backend/tests/test_product_flows.py
   ```
   *Expectation*: All 20 test cases pass with 0 failures.

2. **Frontend Build Verification**:
   ```powershell
   npm run build
   ```
   *Expectation*: Clean build with 0 TypeScript/JSX compiler errors.

3. **Live UI Verification in Employee Workspace**:
   - Navigate to each bot tab (`Support`, `Finance`, `IT`, `HR`, `Academy`).
   - Observe the **2–3 Key Pain Points** cards with edge case badges.
   - Click each card to verify instant AI response generation, plan step trace, edge cases handled tags, and policy invariants.
   - Click **'Domain Guide & Edge Cases'** in the top navigation bar to view this complete documentation in-app.
