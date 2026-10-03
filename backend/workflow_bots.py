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
        "id": "support_bot", "name": "Support Bot", "domain": "support",
        "pain_points": ["conflicting payment rails", "refunds past SLA", "repeat or duplicate action risk"],
        "tools": {
            "payment_reconciliation": {"access": "read", "purpose": "Compare bank, network, merchant and settlement records."},
            "payment_resolution": {"access": "write after approval", "purpose": "Run the deterministic payment policy and idempotent resolution pipeline."},
            "support_command": {"access": "read and queue", "purpose": "Run supported support reports and create follow-up review tasks."},
        },
    },
    "hiring_bot": {
        "id": "hiring_bot", "name": "Hiring Bot", "domain": "hr",
        "pain_points": ["manual resume rubric review", "protected attribute bias", "panel scheduling overhead"],
        "tools": {
            "candidate_evaluation": {"access": "read", "purpose": "Score rubric criteria after stripping protected attributes; never reject."},
            "schedule_interview_panel": {"access": "write after recruiter approval", "purpose": "Schedule the panel while leaving every hiring decision with a human."},
        },
    },
    "finance_bot": {
        "id": "finance_bot", "name": "Finance Reconciliation Bot", "domain": "finance",
        "pain_points": ["manual statement matching", "fee and GST variance investigation", "duplicate payment risk"],
        "tools": {
            "query_bank_statement_lines": {"access": "read", "purpose": "Read statement lines and their existing match status."},
            "reconcile_discrepancy": {"access": "write after analyst approval", "purpose": "Post a verified reconciliation adjustment."},
        },
    },
    "it_access_bot": {
        "id": "it_access_bot", "name": "IT Access Bot", "domain": "it",
        "pain_points": ["manual entitlement checks", "non-standard access requests", "privileged access risk"],
        "tools": {
            "lookup_employee_profile": {"access": "read", "purpose": "Check employee role and department."},
            "check_tool_access_policy": {"access": "read", "purpose": "Verify standard role entitlement; escalate exceptions."},
            "grant_tool_license": {"access": "write after approval", "purpose": "Provision approved standard tools; privileged access remains blocked."},
            "teach_skill_spec": {"access": "draft", "purpose": "Turn a recorded standard-access workflow into a versioned skill spec."},
            "backtest_skill": {"access": "simulation", "purpose": "Backtest the skill against 12 historical access cases."},
            "publish_skill_l1": {"access": "write after admin approval", "purpose": "Publish a passing skill at L1; the Governor retains autonomy control."},
        },
    },
    "academy_bot": {
        "id": "academy_bot", "name": "Academy Coach", "domain": "academy",
        "pain_points": ["slow new-joiner ramp", "inconsistent case practice", "unclear readiness"],
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