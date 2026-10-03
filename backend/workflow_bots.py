"""Least-privilege workflow bot catalog and typed tool dispatcher."""
from __future__ import annotations
from copy import deepcopy
from typing import Any

from backend.connectors import ConnectorRegistry
from backend.orchestrator import run_resolution
from backend.academy import AcademyCoach
from backend.skill_learner import SkillLearner
from backend.planner import CommandBarPlanner

BOTS = {
    "support_bot": {
        "id": "support_bot",
        "name": "Customer Support & Payments Bot",
        "domain": "support",
        "tagline": "Real-time payment resolution, RBI SLA compliance, and failed refund remediation",
        "pain_points": [
            "Stuck UPI Debited Without Credit",
            "RBI T+1 SLA Breach with Compensation",
            "Bounced Bank Refund due to Frozen Account",
        ],
        "pain_points_detail": [
            {
                "id": "stuck_upi",
                "title": "Stuck UPI Debited Without Credit",
                "description": "Customer bank account debited but NPCI/merchant switch indicates uncredited or pending.",
                "prompt": "Reconcile stuck UPI payment and execute instant reversal if verified",
                "edge_cases": [
                    "Subprime CIBIL (<650) or transaction > ₹5,000 held for human sign-off",
                    "Idempotent lock prevents duplicate reversal during gateway timeout",
                ],
                "guardrail": "RULE_PAYMENT_REVERSAL_01 (Prime CIBIL >= 750)",
            },
            {
                "id": "rbi_sla_chase",
                "title": "RBI T+1 SLA Breach with Compensation",
                "description": "Refund delayed beyond RBI Harmonisation of Turnaround Time (T+1 SLA) requiring automated bank chase and statutory penalty calculation.",
                "prompt": "Chase all refunds past SLA and calculate RBI penalty compensation",
                "edge_cases": [
                    "Statutory ₹100/day compensation capped at transaction principal",
                    "Disputed bank gateway status verified against nodal ledger before escalation",
                ],
                "guardrail": "RBI Harmonisation Mandate §3 (T+1 Auto-Compensation)",
            },
            {
                "id": "bounced_wallet_credit",
                "title": "Bounced Bank Refund due to Frozen Account",
                "description": "Automated refund bounced because customer bank account is frozen, dormant, or has invalid IFSC.",
                "prompt": "Remediate bounced bank refund by crediting customer digital wallet",
                "edge_cases": [
                    "Instant ZeroTouch Wallet credit with SHA-256 idempotency key",
                    "Fallback to verified in-app bank update request if wallet KYC is expired",
                ],
                "guardrail": "RULE_WALLET_FALLBACK_CREDIT (ZeroTouch Digital Wallet)",
            },
        ],
        "tools": {
            "payment_reconciliation": {"access": "read", "purpose": "Compare bank, network, merchant and settlement records."},
            "payment_resolution": {"access": "write after approval", "purpose": "Run the deterministic payment policy and idempotent resolution pipeline."},
            "support_command": {"access": "read and queue", "purpose": "Run supported support reports and create follow-up review tasks."},
            "dispatch_bank_chase": {"access": "write after approval", "purpose": "Dispatch bank escalation API call and start compensation clock."},
            "issue_wallet_credit": {"access": "write after approval", "purpose": "Credit funds to digital wallet when bank account is frozen."},
        },
    },
    "finance_bot": {
        "id": "finance_bot",
        "name": "Finance Reconciliation Bot",
        "domain": "finance",
        "tagline": "3-way statement matching, MDR & GST variance explanation, and duplicate payout detection",
        "pain_points": [
            "3-Way Nodal Statement Reconciliation Variance",
            "Duplicate Payout Detection & Prevention",
            "Expired KYC Merchant Settlement Hold",
        ],
        "pain_points_detail": [
            {
                "id": "nodal_statement_variance",
                "title": "3-Way Nodal Statement Reconciliation Variance",
                "description": "End-of-day bank settlement statement payout differs from internal merchant ledger.",
                "prompt": "Reconcile nodal bank statement variance against MDR fee and GST schedule",
                "edge_cases": [
                    "Auto-isolates MDR (₹847.46) + 18% GST (₹152.54) vs unexplained shortfall",
                    "Discrepancies > ₹5,000 flagged as UNRECONCILED and routed to Financial Controller",
                ],
                "guardrail": "SOX Section 404 Nodal Escrow Reconciliation",
            },
            {
                "id": "duplicate_payout_detection",
                "title": "Duplicate Payout Detection & Prevention",
                "description": "Bank statement shows identical debit lines for the same merchant batch within seconds (replay/webhook duplicate).",
                "prompt": "Audit bank statement for duplicate payout lines and draft clawback hold",
                "edge_cases": [
                    "Immediate settlement clearing halt on DUPLICATE_PAYMENT_FLAG",
                    "Automated clawback notice and temporary offset on future merchant payables",
                ],
                "guardrail": "RULE_DUPLICATE_PAYOUT_HALT (Never Auto-Clear)",
            },
            {
                "id": "expired_kyc_payout_hold",
                "title": "Expired KYC Merchant Settlement Hold",
                "description": "Merchant settlement blocked because GSTIN or Director PAN compliance expired.",
                "prompt": "Verify compliance holds and check expired merchant KYC settlement eligibility",
                "edge_cases": [
                    "RBI Payout Direction §4.2 prohibits autonomous release of escrow funds",
                    "Mandatory dual-signature compliance sign-off before releasing merchant payouts",
                ],
                "guardrail": "RBI Master Direction §4.2 KYC Settlement Gate",
            },
        ],
        "tools": {
            "query_bank_statement_lines": {"access": "read", "purpose": "Read statement lines and their existing match status."},
            "reconcile_discrepancy": {"access": "write after analyst approval", "purpose": "Post a verified reconciliation adjustment."},
        },
    },
    "it_access_bot": {
        "id": "it_access_bot",
        "name": "IT Access & Service Desk Bot",
        "domain": "it",
        "tagline": "Zero-touch standard software licensing, role deprovisioning, and privileged access guardrails",
        "pain_points": [
            "Repetitive Standard Software Licensing (Okta / GitHub / Figma)",
            "High-Risk Privileged Access Attempt (AWS Root / Prod DB)",
            "Zero-Touch Deprovisioning on Role Change",
        ],
        "pain_points_detail": [
            {
                "id": "standard_tool_licensing",
                "title": "Repetitive Standard Software Licensing (Okta / GitHub / Figma)",
                "description": "Employees waiting 48h for standard software tools already entitled by their role.",
                "prompt": "Verify employee role entitlement in Okta and auto-grant standard tool license",
                "edge_cases": [
                    "Auto-grants Figma Pro for Designers, GitHub Enterprise for Engineers",
                    "Non-standard tools automatically redirected to departmental manager",
                ],
                "guardrail": "RULE_STANDARD_ROLE_ENTITLEMENT (Pre-approved RBAC Matrix)",
            },
            {
                "id": "privileged_access_guardrail",
                "title": "High-Risk Privileged Access Attempt (AWS Root / Prod DB)",
                "description": "Requests for root credentials, production databases, or cloud infrastructure admin keys.",
                "prompt": "Audit access request for high-risk privileged credentials and enforce guardrails",
                "edge_cases": [
                    "Hard guardrail NEVER_AUTOMATE_PRIVILEGED_ACCESS blocks autonomous execution",
                    "Requires dual-signature CISO + Engineering VP approval with full audit log",
                ],
                "guardrail": "RULE_NEVER_AUTOMATE_PRIVILEGED_ACCESS (Hard Compliance Gate)",
            },
            {
                "id": "role_change_deprovisioning",
                "title": "Zero-Touch Deprovisioning on Role Change",
                "description": "Employees transferring departments retain obsolete, expensive, or high-risk licenses.",
                "prompt": "Audit employee role transition and deprovision obsolete software licenses",
                "edge_cases": [
                    "Identifies role change, deprovisions obsolete seats to prevent license waste",
                    "Checks project artifact ownership before license revocation to prevent orphaned repos",
                ],
                "guardrail": "Principle of Least Privilege (Zero-Trust Deprovisioning)",
            },
        ],
        "tools": {
            "lookup_employee_profile": {"access": "read", "purpose": "Check employee role and department."},
            "check_tool_access_policy": {"access": "read", "purpose": "Verify standard role entitlement; escalate exceptions."},
            "grant_tool_license": {"access": "write after approval", "purpose": "Provision approved standard tools; privileged access remains blocked."},
            "teach_skill_spec": {"access": "draft", "purpose": "Turn a recorded standard-access workflow into a versioned skill spec."},
            "backtest_skill": {"access": "simulation", "purpose": "Backtest the skill against 12 historical access cases."},
            "publish_skill_l1": {"access": "write after admin approval", "purpose": "Publish a passing skill at L1; the Governor retains autonomy control."},
        },
    },
    "hiring_bot": {
        "id": "hiring_bot",
        "name": "Talent & HR Operations Bot",
        "domain": "hr",
        "tagline": "Bias-free candidate rubric scoring, automated panel scheduling, and onboarding orchestration",
        "pain_points": [
            "Unconscious Bias & PII in Candidate Screening",
            "Interview Panel Scheduling Overhead",
            "Automated New-Hire Onboarding Roadmap",
        ],
        "pain_points_detail": [
            {
                "id": "unconscious_bias_screening",
                "title": "Unconscious Bias & PII in Candidate Screening",
                "description": "Subjective human screening influenced by candidate demographic attributes, photo, or college pedigree.",
                "prompt": "Run bias-free candidate evaluation with protected attributes stripped",
                "edge_cases": [
                    "Fairness filter strips gender, age, location, and photo before rubric grading",
                    "Strict invariant: AI can NEVER autonomously reject a candidate; human recruiter decides",
                ],
                "guardrail": "RULE_FAIRNESS_ANONYMIZATION & RULE_NEVER_AUTO_REJECT_CANDIDATE",
            },
            {
                "id": "interview_panel_scheduling",
                "title": "Interview Panel Scheduling Overhead",
                "description": "Multiple back-and-forth emails to coordinate 4-person technical interview panels across timezones.",
                "prompt": "Schedule 4-person technical interview panel for qualified candidate",
                "edge_cases": [
                    "Only triggers calendar dispatch for candidates scoring >= 80% on rubric",
                    "Auto-substitutes backup interviewer if primary interviewer is out of office",
                ],
                "guardrail": "Candidate Consent & Recruiter Sign-Off Gate",
            },
            {
                "id": "automated_onboarding_roadmap",
                "title": "Automated New-Hire Onboarding Roadmap",
                "description": "New employees waiting for first-day hardware delivery, buddy assignment, and compliance orientation.",
                "prompt": "Generate 30-60-90 day onboarding roadmap and coordinate IT/HR setup",
                "edge_cases": [
                    "Coordinates with IT Access Bot for Day 1 software and laptop logistics",
                    "Dynamically adapts orientation calendar to candidate local timezone",
                ],
                "guardrail": "HR Onboarding Baseline SLA (Day 1 Readiness)",
            },
        ],
        "tools": {
            "candidate_evaluation": {"access": "read", "purpose": "Score rubric criteria after stripping protected attributes; never reject."},
            "schedule_interview_panel": {"access": "write after recruiter approval", "purpose": "Schedule the panel while leaving every hiring decision with a human."},
        },
    },
    "academy_bot": {
        "id": "academy_bot",
        "name": "New Joiner Academy Coach",
        "domain": "academy",
        "tagline": "Safe sandbox practice on historical dispute cases, real-time AI grading, and skill synthesis",
        "pain_points": [
            "Slow Operator Ramp-Up on Complex Dispute Scenarios",
            "Inconsistent Decision-Making Across Junior Operators",
            "Standardizing Expert Workflows into L1 Autonomous Skills",
        ],
        "pain_points_detail": [
            {
                "id": "slow_joiner_ramp",
                "title": "Slow Operator Ramp-Up on Complex Dispute Scenarios",
                "description": "New support and operations operators take weeks to master payment rails and risk invariants safely.",
                "prompt": "Load anonymized historical dispute replay case and grade joiner decisions",
                "edge_cases": [
                    "100% anonymized production data replay; 0 risk to live customer funds",
                    "Real-time feedback on banking invariants with live competency radar updates",
                ],
                "guardrail": "Zero-Risk Production Isolation Guardrail",
            },
            {
                "id": "inconsistent_decisions",
                "title": "Inconsistent Decision-Making Across Junior Operators",
                "description": "Discrepancy in refund vs escalate decisions without standard policy grounding.",
                "prompt": "Run interactive simulation on conflicting ledger dispute and test invariants",
                "edge_cases": [
                    "Evaluates step-by-step reasoning against gold standard canonical policy",
                    "Highlights boundary conditions like CIBIL 650 threshold and 5000 INR limits",
                ],
                "guardrail": "Policy Adherence Scoring (Threshold ≥ 85% for L1 Certification)",
            },
            {
                "id": "skill_studio_synthesis",
                "title": "Standardizing Expert Workflows into L1 Autonomous Skills",
                "description": "Expert operators repeatedly perform repetitive manual checks that could be safe automated skills.",
                "prompt": "Synthesize versioned skill spec from recorded actions and run 12-case backtest",
                "edge_cases": [
                    "Runs 12-case historical backtest; fails if any safety invariant is violated",
                    "Publishes strictly at L1 (supervised) under Autonomy Governor trust scoring",
                ],
                "guardrail": "Autonomy Governor Invariant Verification Gate",
            },
        ],
        "tools": {
            "get_replay_case": {"access": "read", "purpose": "Load an anonymized support or HR practice case."},
            "evaluate_joiner_run": {"access": "write training record", "purpose": "Score answers and update the competency map; no live customer action."},
        },
    },
}

TOOL_HANDLERS = {
    "payment_reconciliation": ConnectorRegistry.get_payment_reconciliation,
    "payment_resolution": run_resolution,
    "support_command": CommandBarPlanner.execute_command,
    "dispatch_bank_chase": ConnectorRegistry.dispatch_bank_chase,
    "issue_wallet_credit": ConnectorRegistry.issue_wallet_credit,
    "candidate_evaluation": ConnectorRegistry.get_candidate_evaluation,
    "schedule_interview_panel": ConnectorRegistry.schedule_interview_panel,
    "query_bank_statement_lines": ConnectorRegistry.query_bank_statement_lines,
    "reconcile_discrepancy": ConnectorRegistry.reconcile_discrepancy,
    "lookup_employee_profile": ConnectorRegistry.lookup_employee_profile,
    "check_tool_access_policy": ConnectorRegistry.check_tool_access_policy,
    "grant_tool_license": ConnectorRegistry.grant_tool_license,
    "teach_skill_spec": SkillLearner.synthesize_skill_spec,
    "backtest_skill": SkillLearner.run_historical_backtest,
    "publish_skill_l1": SkillLearner.publish_skill_to_l1,
    "get_replay_case": AcademyCoach.get_replay_case,
    "evaluate_joiner_run": AcademyCoach.evaluate_joiner_run,
}
DOMAIN_BOTS = {bot["domain"]: bot_id for bot_id, bot in BOTS.items() if bot["domain"] != "academy"}


def bot_for_task(task: dict[str, Any]) -> dict[str, Any]:
    bot_id = DOMAIN_BOTS.get(str(task.get("domain", "support")).lower(), "support_bot")
    return deepcopy(BOTS[bot_id])


def assigned_bot(task: dict[str, Any]) -> dict[str, Any]:
    bot = bot_for_task(task)
    skill = task.get("skill_id", "")
    priority = {
        "upi_stuck_reversal": ["payment_reconciliation", "payment_resolution"],
        "refund_sla_chase": ["payment_reconciliation", "payment_resolution"],
        "bounced_refund_wallet_credit": ["payment_reconciliation", "payment_resolution"],
        "resume_screening_rubric": ["candidate_evaluation", "schedule_interview_panel"],
        "bank_statement_match": ["query_bank_statement_lines", "reconcile_discrepancy"],
        "it_tool_access_grant": ["lookup_employee_profile", "check_tool_access_policy", "grant_tool_license"],
    }.get(skill, ["payment_reconciliation", "payment_resolution"] if bot["id"] == "support_bot" else list(bot["tools"]))
    return {"id": bot["id"], "name": bot["name"], "domain": bot["domain"],
            "pain_points": bot["pain_points"], "tools": [name for name in priority if name in bot["tools"]]}


def run_bot_tool(bot_id: str, tool_id: str, **kwargs: Any) -> Any:
    """Dispatch only registered tools explicitly granted to the selected workflow bot."""
    bot = BOTS.get(bot_id)
    if not bot or tool_id not in bot["tools"] or tool_id not in TOOL_HANDLERS:
        raise PermissionError(f"Tool {tool_id!r} is not granted to bot {bot_id!r}")
    return TOOL_HANDLERS[tool_id](**kwargs)


def bot_catalog() -> list[dict[str, Any]]:
    return [deepcopy(bot) for bot in BOTS.values()]