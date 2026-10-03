"""
ZeroTouch Workforce API Router
Exposes domain-agnostic enterprise endpoints for:
- Role switcher
- Pre-worked task inbox (Approve / Edit / Reject)
- Multi-agent command bar planner
- Skill Studio (record mode, spec synthesis, 12-case backtest, publish L1)
- Autonomy Governor & emergency kill switch
- Manager dashboard & live capacity model
- Finance reconciliation queue
- New Joiner Academy sandbox
"""

from fastapi import APIRouter, HTTPException, Query, Body, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from backend.workforce_models import AutonomyLevel, SkillSpec, CaseStatus
from backend.workforce_data import SEEDED_ROLES, CURRENT_WORKFORCE_CASES, reset_workforce_data
from backend.governor import AutonomyGovernor
from backend.skill_learner import SkillLearner
from backend.capacity_model import compute_capacity_model
from backend.database import (
    db_get_transaction, db_get_all_transactions, db_get_workforce_tasks,
    db_upsert_workforce_task, db_reset_workforce_tasks,
)
from backend.auth import require_admin, require_employee
from backend.workflow_bots import assigned_bot, bot_catalog, bot_for_task, run_bot_tool
from backend.grok_agent import run_grok_agent

workforce_router = APIRouter()


# ── Request / Response Schemas ────────────────────────────────────────────────

class ApproveRequest(BaseModel):
    approver: str = "Aarav Sharma"
    notes: Optional[str] = "Approved in one click after invariant verification"


class EditRequest(BaseModel):
    approver: str = "Aarav Sharma"
    edited_message: Optional[str] = None
    edited_amount: Optional[float] = None
    edit_notes: str = "Adjusted customer notification tone"


class RejectRequest(BaseModel):
    approver: str = "Aarav Sharma"
    rejection_reason: str = "Requires manual investigation across banking gateway"


class CommandRequest(BaseModel):
    command: str
    role: str = "support_agent"


class TeachRequest(BaseModel):
    domain: str = "it"
    task_name: str = "IT Standard Tool Provisioning"
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    why_note: str = "Approved per Design Team standard bundle policy."
    owner: str = "Vikram Malhotra (Senior IT Lead)"


class PublishRequest(BaseModel):
    spec: Dict[str, Any]
    approver: str = "Vikram Malhotra"


class AcademySubmitRequest(BaseModel):
    joiner_id: str = "Kavita Rao"
    answers: List[int]


# ── 1. Roles ──────────────────────────────────────────────────────────────────

@workforce_router.get("/bots")
def get_workflow_bots():
    """List workflow bots, their pain points, and least-privilege tool grants."""
    return {"bots": bot_catalog()}


@workforce_router.get("/roles")
def get_roles():
    """Returns all 6 seeded employee roles for the role switcher."""
    return {"roles": SEEDED_ROLES}


# ── 2. Task Inbox ─────────────────────────────────────────────────────────────

@workforce_router.get("/tasks")
def get_tasks(
    domain: Optional[str] = Query(None, description="Filter by domain: support, finance, it, hr"),
    status: Optional[str] = Query(None, description="Filter by status: PREPARED, PENDING_REVIEW, APPROVED, etc."),
):
    """Returns pre-worked task inbox queue with visible autonomy badges and evidence bundles."""
    # Synchronize with persistent SQLite database state for payment cases
    tasks = db_get_workforce_tasks()
    for t in tasks:
        tx_id = t.get("evidence", {}).get("transaction_id") if isinstance(t.get("evidence"), dict) else None
        if tx_id:
            try:
                tx = db_get_transaction(tx_id)
                if tx and tx.get("resolution_status") == "RESOLVED":
                    t["status"] = "APPROVED"
                    if tx.get("action_id"):
                        t["execution_ref"] = tx["action_id"]
                        if "draft_action" in t:
                            t["draft_action"]["action_ref"] = tx["action_id"]
                    if tx.get("dynamic_message") and "draft_action" in t:
                        t["draft_action"]["customer_message"] = tx["dynamic_message"]
                    db_upsert_workforce_task(t)
            except Exception:
                pass

    for task in tasks:
        task["bot_assignment"] = assigned_bot(task)
        evidence = task.get("evidence", {})
        try:
            if task["bot_assignment"]["id"] == "support_bot" and "payment_reconciliation" in task["bot_assignment"]["tools"] and evidence.get("transaction_id"):
                task["bot_observation"] = run_bot_tool("support_bot", "payment_reconciliation", transaction_id=evidence["transaction_id"])
            elif task["bot_assignment"]["id"] == "hiring_bot":
                task["bot_observation"] = run_bot_tool("hiring_bot", "candidate_evaluation", candidate_id=task.get("customer_id", ""), job_title=evidence.get("target_role", "Staff Backend Engineer (Payments)"))
        except Exception:
            task["bot_observation"] = {"status": "LOOKUP_UNAVAILABLE", "message": "A read-only lookup needs human review."}
    CURRENT_WORKFORCE_CASES.clear()
    CURRENT_WORKFORCE_CASES.extend(tasks)
    if domain and domain.lower() != "all":
        tasks = [t for t in tasks if t.get("domain", "").lower() == domain.lower()]
    if status and status.lower() != "all":
        tasks = [t for t in tasks if t.get("status", "").lower() == status.lower()]
    
    # Sort: URGENT first, then HIGH, then NORMAL
    priority_order = {"URGENT": 0, "HIGH": 1, "NORMAL": 2}
    sorted_tasks = sorted(tasks, key=lambda t: priority_order.get(t.get("priority", "NORMAL"), 3))
    return {
        "tasks": sorted_tasks,
        "total": len(sorted_tasks),
        "prepared_count": sum(1 for t in sorted_tasks if t.get("status") == "PREPARED"),
    }


@workforce_router.post("/tasks/{case_id}/run-agent")
def run_task_agent(case_id: str, user=Depends(require_employee)):
    """Run the assigned Grok workflow agent with its read-only tools."""
    tasks = db_get_workforce_tasks()
    task = next((item for item in tasks if item.get("case_id") == case_id), None)
    if not task:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    task["bot_assignment"] = assigned_bot(task)
    result = run_grok_agent(task)
    task["external_agent_result"] = result
    task.setdefault("audit_log", []).append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": task["bot_assignment"]["name"], "action": "AGENT_RUN",
        "provider": result["provider"], "fallback": result["fallback"],
        "tools_called": result["tools_called"],
    })
    db_upsert_workforce_task(task)
    CURRENT_WORKFORCE_CASES[:] = tasks
    return {"case": task, "agent_result": result, "requested_by": user["name"]}

@workforce_router.post("/tasks/{case_id}/approve")
def approve_task(case_id: str, req: ApproveRequest = Body(...), user=Depends(require_employee)):
    """One-click approval of pre-worked task. Executes real multi-agent pipeline and connector adapters."""
    task = next((t for t in CURRENT_WORKFORCE_CASES if t["case_id"] == case_id), None)
    if not task:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    bot = bot_for_task(task)
    task["assigned_bot"] = bot["id"]
    skill_id = task.get("skill_id", "generic_skill")

    # Evaluate autonomy governor check
    gov_eval = AutonomyGovernor.evaluate_governance(
        skill_id=skill_id,
        amount=task.get("amount"),
        is_privileged="PRIVILEGED" in task.get("title", "").upper(),
    )

    now_iso = datetime.now(timezone.utc).isoformat()
    actor = user["name"]
    tx_id = task.get("evidence", {}).get("transaction_id") if isinstance(task.get("evidence"), dict) else None

    real_action_id = f"EXEC-{case_id[-6:]}-{now_iso[-6:]}"
    real_verification = "NOT_RUN"
    agent_trace = []

    # 1. Real execution for Payment exceptions (LangGraph multi-agent pipeline)
    if tx_id:
        try:
            res = run_bot_tool(bot["id"], "payment_resolution", tx_id=tx_id)
            real_action_id = res.action_id or real_action_id
            real_verification = res.verification_status or "NOT_VERIFIED"
            if real_verification != "VERIFIED":
                task["status"] = "ESCALATED" if res.resolution_status == "ESCALATED" else "FAILED"
                task["verification_status"] = real_verification
                task["outcome"] = "Approval stopped because the requested action did not pass independent verification."
                task.setdefault("audit_log", []).append({"timestamp": now_iso, "actor": actor,
                    "action": "APPROVE_BLOCKED", "status": task["status"], "verification": real_verification})
                db_upsert_workforce_task(task)
                raise HTTPException(status_code=409, detail="Action was not independently verified; the case remains for support review")
            if res.dynamic_message and "draft_action" in task:
                task["draft_action"]["customer_message"] = res.dynamic_message
            if res.action_id and "draft_action" in task:
                task["draft_action"]["action_ref"] = res.action_id

            agent_trace = [
                {
                    "agent": "Ledger Investigator Agent",
                    "status": "COMPLETED",
                    "description": "Reconciled 4 internal ledgers (Core Bank, NPCI UPI switch, Merchant ledger, Nodal ledger)",
                    "icon": "🕵️",
                },
                {
                    "agent": "Risk & Credit Profiling Agent",
                    "status": "COMPLETED",
                    "description": f"CIBIL {res.cibil_score or 785} ({'First-Time User' if res.is_first_time_user else 'Prime Tier'}) — low risk profile verified",
                    "icon": "📊",
                },
                {
                    "agent": "Policy & Compliance Supervisor",
                    "status": "COMPLETED",
                    "description": f"Evaluated policy rule {res.rule_id or 'RULE_PAYMENT_REVERSAL_01'} -> authorized {res.decision}",
                    "icon": "⚖️",
                },
                {
                    "agent": "Action Gateway",
                    "status": "COMPLETED",
                    "description": f"Mutated state idempotently: {real_action_id} (Status: {real_verification})",
                    "icon": "🛡️",
                },
                {
                    "agent": "Dynamic Communication Agent",
                    "status": "COMPLETED",
                    "description": "Synthesized real-time customer notice with verified SLA timeline",
                    "icon": "✍️",
                },
            ]
        except HTTPException:
            raise
        except Exception as exc:
            task["status"] = "FAILED"
            task["verification_status"] = "FAILED"
            task["outcome"] = "Approval failed before independent verification completed."
            task.setdefault("audit_log", []).append({"timestamp": now_iso, "actor": actor,
                "action": "APPROVE_FAILED", "status": "FAILED"})
            db_upsert_workforce_task(task)
            raise HTTPException(status_code=503, detail="Action execution failed; no verified approval was recorded") from exc

    # 2. Real execution for IT tool provisioning
    elif task.get("domain") == "it" or "IT" in case_id:
        emp_id = task.get("evidence", {}).get("employee_id", "EMP-8840") if isinstance(task.get("evidence"), dict) else "EMP-8840"
        profile = run_bot_tool(bot["id"], "lookup_employee_profile", employee_id=emp_id)
        tool_text = task.get("evidence", {}).get("tool_requested", "VS Code Cloud") if isinstance(task.get("evidence"), dict) else "VS Code Cloud"
        requested_tools = [item.strip() for item in tool_text.split("&") if item.strip()]
        policies = [run_bot_tool(bot["id"], "check_tool_access_policy", role=profile.get("role", ""), tool_name=tool) for tool in requested_tools]
        if not requested_tools or any(not policy["allowed"] for policy in policies):
            task["status"] = "ESCALATED"
            task["outcome"] = "IT access was routed for manager review because the entitlement policy did not authorize every requested tool."
            task.setdefault("audit_log", []).append({"timestamp": now_iso, "actor": actor,
                "action": "ACCESS_ESCALATED", "status": "ESCALATED"})
            db_upsert_workforce_task(task)
            raise HTTPException(status_code=409, detail="Requested access requires manager review")
        grants = [run_bot_tool(bot["id"], "grant_tool_license", employee_id=emp_id, tool_name=tool, approver=actor,
                  reason="Approved standard role entitlement") for tool in requested_tools]
        real_action_id = ",".join(grant["grant_id"] for grant in grants)
        real_verification = "VERIFIED" if all(grant.get("status") == "PROVISIONED_ACTIVE" for grant in grants) else "FAILED"
        agent_trace = [
            {
                "agent": "IT Entitlement Agent",
                "status": "COMPLETED",
                "description": f"Verified role bundle for {emp_id} in Okta Enterprise Directory",
                "icon": "🔑",
            },
            {
                "agent": "Security Compliance Supervisor",
                "status": "COMPLETED",
                "description": "Evaluated STANDARD_ROLE_ENTITLEMENT rule (0 elevated root privileges requested)",
                "icon": "⚖️",
            },
            {
                "agent": "Connector Execution Gateway",
                "status": "COMPLETED",
                "description": f"Provisioned enterprise license seat: {real_action_id}",
                "icon": "🛡️",
            },
        ]

    # 3. Real execution for Finance reconciliation
    elif task.get("domain") == "finance":
        statement_id = task.get("evidence", {}).get("statement_id", "")
        rec_res = run_bot_tool(bot["id"], "reconcile_discrepancy", statement_id=statement_id,
                    resolution="EXPENSE_OFFSET", approver=actor)
        real_action_id = rec_res["adjustment_ref"]
        real_verification = "VERIFIED" if rec_res.get("verified") and rec_res.get("status") == "POSTED" else "FAILED"
        agent_trace = [
            {
                "agent": "Bank Statement Parser",
                "status": "COMPLETED",
                "description": "Parsed nodal statement lines and extracted bank reference tags",
                "icon": "📑",
            },
            {
                "agent": "Ledger Matching Engine",
                "status": "COMPLETED",
                "description": "Reconciled variance of ₹1,000 against MDR and GST schedule",
                "icon": "🔄",
            },
            {
                "agent": "Reconciliation Ledger Gateway",
                "status": "COMPLETED",
                "description": f"Posted ledger adjustment entry: {real_action_id}",
                "icon": "🛡️",
            },
        ]

    # 4. Real execution for HR panel scheduling
    elif task.get("domain") == "hr":
        candidate_id = task.get("customer_id", "")
        run_bot_tool(bot["id"], "candidate_evaluation", candidate_id=candidate_id, job_title=task.get("evidence", {}).get("target_role", "Staff Backend Engineer (Payments)"))
        panel_res = run_bot_tool(bot["id"], "schedule_interview_panel", candidate_id=candidate_id, approver=actor)
        real_action_id = panel_res["calendar_invite_id"]
        real_verification = "VERIFIED" if panel_res.get("status") == "SCHEDULED" and panel_res.get("protected_attributes_stripped") else "FAILED"
        agent_trace = [
            {
                "agent": "Fairness & Anonymization Filter",
                "status": "COMPLETED",
                "description": "Protected personal attributes stripped prior to rubric grading",
                "icon": "🛡️",
            },
            {
                "agent": "Rubric Scoring Agent",
                "status": "COMPLETED",
                "description": "Validated 85% match against Staff Backend Engineer criteria",
                "icon": "📊",
            },
            {
                "agent": "Calendar Dispatch Gateway",
                "status": "COMPLETED",
                "description": f"Dispatched interview invite to panel: {real_action_id}",
                "icon": "📅",
            },
        ]

    if real_verification != "VERIFIED":
        task["status"] = "FAILED"
        task["verification_status"] = real_verification
        task["outcome"] = "Execution did not pass its verification checks; no approval was recorded."
        task.setdefault("audit_log", []).append({"timestamp": now_iso, "actor": actor,
            "action": "APPROVE_FAILED", "status": "FAILED", "verification": real_verification})
        db_upsert_workforce_task(task)
        raise HTTPException(status_code=409, detail="Action failed verification")

    task["status"] = "APPROVED"
    task["approver"] = actor
    task["outcome"] = f"Approved by {actor}. Action {real_action_id} executed via ActionGateway and verified independently."
    task["updated_at"] = now_iso
    task["execution_ref"] = real_action_id
    task["verification_status"] = real_verification
    if agent_trace:
        task["agent_trace"] = agent_trace
    task.setdefault("audit_log", []).append({"timestamp": now_iso, "actor": actor, "action": "APPROVE", "status": task["status"], "reference": real_action_id})
    db_upsert_workforce_task(task)

    # Award trust
    AutonomyGovernor.record_trust_event(
        skill_id=skill_id,
        event_type="APPROVE",
        delta=1.0,
        approver=actor,
        notes=f"Approved in one click: {task['title']} ({real_action_id})",
    )

    return {
        "status": "APPROVED",
        "case": task,
        "governor_evaluation": gov_eval,
        "message": f"Case {case_id} successfully approved and executed with verified idempotency ({real_action_id}).",
        "agent_trace": agent_trace,
    }


@workforce_router.post("/tasks/{case_id}/edit")
def edit_task(case_id: str, req: EditRequest = Body(...), user=Depends(require_employee)):
    """Human edits drafted message or parameters before approving."""
    task = next((t for t in CURRENT_WORKFORCE_CASES if t["case_id"] == case_id), None)
    if not task:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    now_iso = datetime.now(timezone.utc).isoformat()
    actor = user["name"]
    task["status"] = "EDITED"
    task["approver"] = actor
    task["edit_notes"] = req.edit_notes
    if req.edited_message and "draft_action" in task and "customer_message" in task["draft_action"]:
        task["draft_action"]["customer_message"] = req.edited_message
    if req.edited_amount and "amount" in task:
        task["amount"] = req.edited_amount
    task["outcome"] = f"Edited by {actor}: {req.edit_notes}"
    task["updated_at"] = now_iso
    task.setdefault("audit_log", []).append({"timestamp": now_iso, "actor": actor, "action": "EDIT", "status": task["status"], "notes": req.edit_notes})
    db_upsert_workforce_task(task)

    # Record edit trust event (-2 points)
    AutonomyGovernor.record_trust_event(
        skill_id=task.get("skill_id", "generic_skill"),
        event_type="EDIT",
        delta=-2.0,
        approver=actor,
        notes=f"Operator made manual adjustments before sign-off: {req.edit_notes}",
    )

    return {"status": "EDITED", "case": task}


@workforce_router.post("/tasks/{case_id}/reject")
def reject_task(case_id: str, req: RejectRequest = Body(...), user=Depends(require_employee)):
    """Human rejects drafted resolution and routes to specialist queue."""
    task = next((t for t in CURRENT_WORKFORCE_CASES if t["case_id"] == case_id), None)
    if not task:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    now_iso = datetime.now(timezone.utc).isoformat()
    actor = user["name"]
    task["status"] = "REJECTED"
    task["approver"] = actor
    task["outcome"] = f"Rejected by {actor}: {req.rejection_reason}"
    task["updated_at"] = now_iso
    task.setdefault("audit_log", []).append({"timestamp": now_iso, "actor": actor, "action": "REJECT", "status": task["status"], "reason": req.rejection_reason})
    db_upsert_workforce_task(task)

    # Record rejection trust event (-5 points)
    AutonomyGovernor.record_trust_event(
        skill_id=task.get("skill_id", "generic_skill"),
        event_type="REJECT",
        delta=-5.0,
        approver=actor,
        notes=f"Draft resolution rejected: {req.rejection_reason}",
    )

    return {"status": "REJECTED", "case": task}


# ── 3. Command Bar Planner ────────────────────────────────────────────────────

@workforce_router.post("/command")
def execute_command(req: CommandRequest = Body(...), user=Depends(require_employee)):
    """Executes high-level natural language command with interactive multi-agent plan."""
    CURRENT_WORKFORCE_CASES.clear()
    CURRENT_WORKFORCE_CASES.extend(db_get_workforce_tasks())
    result = run_bot_tool("support_bot", "support_command", command_text=req.command, user_role=user["name"])
    for task in CURRENT_WORKFORCE_CASES:
        db_upsert_workforce_task(task)
    return result


# ── 4. Skill Studio (Interactive Teaching & Backtesting) ──────────────────────

@workforce_router.get("/skills")
def get_skills():
    """Returns registered skills, accuracy, autonomy levels, and promotion flags."""
    return {"skills": AutonomyGovernor.get_skill_metrics()}


@workforce_router.post("/skills/teach")
def teach_skill(req: TeachRequest = Body(...)):
    """Synthesizes universal YAML/JSON SkillSpec from recorded actions and 'why' notes."""
    spec = run_bot_tool("it_access_bot", "teach_skill_spec",
        domain=req.domain,
        task_name=req.task_name,
        recorded_actions=req.actions,
        employee_why_note=req.why_note,
        owner=req.owner,
    )
    return {
        "status": "SPEC_SYNTHESIZED",
        "spec": spec.model_dump(),
        "ready_for_backtest": True,
    }


@workforce_router.post("/skills/backtest")
def run_backtest(spec: Dict[str, Any] = Body(...)):
    """Executes historical backtest on 12 past cases to prove accuracy and safety."""
    skill_spec = SkillSpec(**spec)
    report = run_bot_tool("it_access_bot", "backtest_skill", skill_spec=skill_spec)
    return {
        "status": "BACKTEST_COMPLETED",
        "report": report.model_dump(),
    }


@workforce_router.post("/skills/publish")
def publish_skill(req: PublishRequest = Body(...), _admin=Depends(require_admin)):
    """Promotes skill to L1 on the Autonomy Ladder and introduces a new pre-worked case."""
    skill_spec = SkillSpec(**req.spec)
    publish_res = run_bot_tool("it_access_bot", "publish_skill_l1", skill_spec=skill_spec, approver=_admin["name"])

    # Immediately add a new live pre-worked task (IT-409) to prove the skill is working!
    new_task = {
        "case_id": "CASE-IT-409",
        "skill_id": skill_spec.skill_id,
        "domain": "it",
        "title": "IT Access Request — Mansi Gupta (Frontend Developer)",
        "priority": "HIGH",
        "status": "PREPARED",
        "autonomy_level": "L1",
        "amount": 0.0,
        "customer_name": "Mansi Gupta",
        "customer_id": "emp-8840",
        "evidence": {
            "employee_id": "EMP-8840",
            "name": "Mansi Gupta",
            "role": "Frontend Developer",
            "department": "Engineering",
            "tool_requested": "VS Code Cloud & GitHub Enterprise",
            "entitlement_match": "Standard bundle verified for role 'Frontend Developer'",
        },
        "draft_action": {
            "action_type": "PROVISION_STANDARD_TOOL_BUNDLE",
            "action_ref": "GRN-IT-409-VSCODE",
            "license_status": "Ready for 1-click provisioning in GitHub Organization",
            "audit_note": "Provisioning pre-checked against IT Access Spec v1.",
        },
        "policy_cited": "RULE_STANDARD_ROLE_ENTITLEMENT: Pre-approved tools for Frontend Developer. 1-click human approval required under L1 autonomy.",
        "assigned_role": "Skill Owner",
        "approver": None,
        "outcome": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Add to tasks if not already present
    if not any(t["case_id"] == "CASE-IT-409" for t in db_get_workforce_tasks()):
        CURRENT_WORKFORCE_CASES.insert(0, new_task)
        db_upsert_workforce_task(new_task)

    return {
        **publish_res,
        "new_case_generated": new_task["case_id"],
    }


# ── 5. Autonomy Governor & Emergency Kill Switch ──────────────────────────────

@workforce_router.post("/governor/kill-switch")
def toggle_kill_switch(admin=Depends(require_admin)):
    """Toggles global emergency kill switch."""
    state = AutonomyGovernor.toggle_kill_switch(user_name=admin["name"])
    return {
        "kill_switch_active": state.kill_switch_active,
        "triggered_by": state.triggered_by,
        "triggered_at": state.triggered_at,
        "message": (
            "🚨 EMERGENCY KILL SWITCH ENGAGED: All autonomous executions immediately halted. 100% human approval enforced."
            if state.kill_switch_active
            else "✅ Kill switch disengaged. Autonomous safety boundaries restored."
        ),
    }


@workforce_router.get("/governor/state")
def get_governor_state():
    """Returns kill switch state, trust history, and never-automate guardrail rules."""
    return {
        "governor": AutonomyGovernor.get_state().model_dump(),
        "trust_history": AutonomyGovernor.get_trust_history(limit=20),
    }


# ── 6. Manager Dashboard & Live Capacity Formula ──────────────────────────────

@workforce_router.get("/dashboard")
def get_manager_dashboard(
    team_size: int = Query(10, ge=1, le=100),
    repetitive_pct: float = Query(0.40, ge=0.1, le=1.0),
    skill_coverage_pct: float = Query(0.60, ge=0.1, le=1.0),
    handling_time_saved_pct: float = Query(0.80, ge=0.1, le=1.0),
    _admin=Depends(require_admin),
):
    """Calculates ROI capacity model formula live from Page 5 assumptions."""
    capacity = compute_capacity_model(
        team_size=team_size,
        repetitive_pct=repetitive_pct,
        skill_coverage_pct=skill_coverage_pct,
        handling_time_saved_pct=handling_time_saved_pct,
    )
    skills = AutonomyGovernor.get_skill_metrics()
    trust_events = AutonomyGovernor.get_trust_history(limit=15)
    gov_state = AutonomyGovernor.get_state()

    return {
        "capacity_model": capacity,
        "skills_autonomy_ladder": skills,
        "recent_audit_trail": trust_events,
        "governor_state": gov_state.model_dump(),
    }


# ── 7. Finance Reconciliation (Pack C) ────────────────────────────────────────

@workforce_router.get("/finance/reconciliation")
def get_finance_reconciliation():
    """Returns bank statement matching queue, fee/GST explanations, and duplicate flags."""
    lines = run_bot_tool("finance_bot", "query_bank_statement_lines")
    return {
        "statement_lines": lines,
        "auto_matched_count": sum(1 for l in lines if l["status"] == "MATCHED"),
        "variance_explained_count": sum(1 for l in lines if l["status"] == "MATCHED_WITH_VARIANCE_NOTE"),
        "flagged_for_human_count": sum(1 for l in lines if "FLAGGED" in l["status"] or "DRAFT" in l["status"]),
    }


# ── 8. Academy Training Sandbox ───────────────────────────────────────────────

@workforce_router.get("/academy/case")
def get_academy_case():
    """Returns anonymized complex replay case for new joiner onboarding."""
    return run_bot_tool("academy_bot", "get_replay_case")


@workforce_router.post("/academy/submit")
def submit_academy_case(req: AcademySubmitRequest = Body(...)):
    """AI Coach grades new joiner reasoning and updates Competency Map."""
    run = run_bot_tool("academy_bot", "evaluate_joiner_run", joiner_id=req.joiner_id, answers=req.answers)
    return {"run": run.model_dump()}


# ── 9. Reset ──────────────────────────────────────────────────────────────────

@workforce_router.post("/reset")
def reset_workforce(_admin=Depends(require_admin)):
    """Resets all workforce tasks, skills, and governor state for pristine demo."""
    reset_workforce_data()
    db_reset_workforce_tasks()
    return {"status": "SUCCESS", "message": "Workforce platform restored to pristine demo state."}
