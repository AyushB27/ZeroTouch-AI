"""
LangGraph Multi-Agent Stateful Orchestration for ZeroTouch.

Segregated Multi-Agent Pipeline:
  1. 🕵️ Ledger Investigator Agent (queries Bank, NPCI, Merchant, Settlement)
  2. 📊 Risk & Credit Profiling Agent (evaluates CIBIL score, First-Time User status, ceilings)
  3. ⚖️ Policy & Compliance Agent (RAG knowledge base + deterministic policy logic + Exception Taxonomy)
  4. 🛡️ Action Gateway (Idempotency, lifecycle tracking, independent verification)
  5. ✍️ Dynamic Communication Agent (NO PRE-BUILT MESSAGES - dynamically writes via LLM)
  6. 🔄 Canonical Case Synchronization (Single source of truth between Customer and Ops)
"""

import json
import operator
from typing import TypedDict, List, Optional, Annotated
from datetime import datetime, timezone

from langgraph.graph import StateGraph, END

from backend.models import (
    Evidence,
    EvidenceMatrix,
    AuditEvent,
    ResolutionResult,
    PolicyDecision,
    RiskAssessment,
    AuditVisibility,
)
from backend.policy import evaluate_policy
from backend.database import (
    db_get_transaction,
    db_update_transaction,
    db_add_event,
    db_get_events,
    case_id_for_tx,
    db_get_case_by_tx,
    db_update_case_by_tx,
)
from backend.action_gateway import ActionGateway
from backend.tools.notifications import create_support_case
from backend.agent import investigate_transaction
from backend.risk_agent import assess_risk_and_credit
from backend.communication_agent import generate_dynamic_message


# ── State schema ──────────────────────────────────────────────────────────────

class ResolutionState(TypedDict):
    tx_id: str
    case_id: str
    tx: dict
    events: Annotated[List[dict], operator.add]   # append-only list
    evidence: Optional[dict]
    evidence_matrix: Optional[dict]
    risk_assessment: Optional[dict]                # Risk & Credit Agent assessment
    policy: Optional[dict]                         # PolicyDecision as dict
    action_id: Optional[str]
    verification_status: Optional[str]
    notification_sent: bool
    dynamic_message: Optional[str]                 # Synthesized by Communication Agent
    support_case: Optional[str]
    escalation_reason: Optional[str]
    suggested_resolution: Optional[str]
    investigation_narrative: Optional[str]
    resolution_status: str                         # final status


# ── Helper ────────────────────────────────────────────────────────────────────

def _log(state: ResolutionState, event_type, step, status, message, visibility="INTERNAL", actor="ZeroTouch Agent") -> dict:
    e = db_add_event(state["tx_id"], event_type, step, status, message, visibility=visibility, actor=actor)
    return e


def _make_log(state):
    """Returns a log callback that appends to DB AND to state events."""
    collected = []
    def log(et, step, st, msg, visibility="INTERNAL", actor="ZeroTouch Agent"):
        e = _log(state, et, step, st, msg, visibility=visibility, actor=actor)
        collected.append(e)
        return e
    return log, collected


# ── Agent 1: Ledger Investigator Agent ────────────────────────────────────────

def node_investigate_ledgers(state: ResolutionState) -> dict:
    tx_id = state["tx_id"]
    tx = state["tx"]
    cid = state.get("case_id") or case_id_for_tx(tx_id)

    log, collected = _make_log(state)
    log("INVESTIGATION", "investigator_agent_start", "INFO",
        f"[Ledger Investigator Agent] Initiating multi-system ledger query for {tx_id} (Case: {cid})",
        actor="Ledger Investigator Agent")
    log("INVESTIGATION", "load_transaction", "SUCCESS",
        f"Transaction {tx_id} loaded: ₹{tx['amount']:,.0f} | Customer: {tx.get('customer_name', 'User')}",
        actor="Ledger Investigator Agent")

    narrative = investigate_transaction(tx_id, tx, log)
    log("INVESTIGATION", "narrative_complete", "SUCCESS",
        "[Ledger Investigator Agent] Multi-ledger query complete. Four systems reconciled.",
        actor="Ledger Investigator Agent")

    now_iso = datetime.now(timezone.utc).isoformat()
    evidence_matrix = EvidenceMatrix(
        transaction_id=tx_id,
        bank_status=tx["bank_status"],
        network_status=tx["network_status"],
        merchant_status=tx["merchant_status"],
        settlement_status=tx["settlement_status"],
        queried_at=now_iso,
        provenance={
            "bank": "CoreBank-NPCI-Gateway",
            "network": "NPCI-UPI-2.0",
            "merchant": "Paytm-Merchant-Ledger",
            "settlement": "Nodal-Settlement-Engine",
        }
    )

    evidence = Evidence(
        transaction_id=tx_id,
        customer_name=tx.get("customer_name", "Paytm User"),
        bank=tx["bank_status"],
        network=tx["network_status"],
        merchant=tx["merchant_status"],
        settlement=tx["settlement_status"],
        amount=tx["amount"],
        risk=tx["risk_score"],
        cibil_score=tx.get("cibil_score", 750),
        is_first_time_user=tx.get("is_first_time_user", False),
        previous_refund=tx["previous_refund"],
    )

    # Sync canonical case state
    db_update_case_by_tx(
        tx_id,
        evidence_matrix=json.dumps(evidence_matrix.model_dump()),
        customer_status="INVESTIGATING",
        ops_status="PENDING",
    )

    return {
        "evidence": evidence.model_dump(),
        "evidence_matrix": evidence_matrix.model_dump(),
        "investigation_narrative": narrative,
        "events": collected,
    }


# ── Agent 2: Risk & Credit Profiling Agent ────────────────────────────────────

def node_risk_and_credit(state: ResolutionState) -> dict:
    tx = state["tx"]
    tx_id = state["tx_id"]
    log, collected = _make_log(state)

    log("RISK_ANALYSIS", "risk_agent_start", "INFO",
        "[Risk & Credit Agent] Profiling customer creditworthiness, CIBIL score, and tenure...",
        actor="Risk & Credit Profiling Agent")

    risk_assessment: RiskAssessment = assess_risk_and_credit(tx, log)

    db_update_case_by_tx(
        tx_id,
        risk_assessment=json.dumps(risk_assessment.model_dump()),
    )

    return {
        "risk_assessment": risk_assessment.model_dump(),
        "events": collected,
    }


# ── Agent 3: Policy & Compliance Agent ────────────────────────────────────────

def node_policy(state: ResolutionState) -> dict:
    evidence = Evidence(**state["evidence"])
    tx_id = state["tx_id"]
    log, collected = _make_log(state)

    log("POLICY", "policy_agent_start", "INFO",
        "[Policy & Compliance Agent] Cross-referencing refund policy with ledger evidence and credit tier...",
        actor="Policy & Compliance Agent")

    decision: PolicyDecision = evaluate_policy(evidence)

    log("POLICY", "evaluate_policy", "SUCCESS",
        f"[Policy Agent] Verdict: {decision.decision} | Rule: {decision.rule_id} (v{decision.rule_version}) | Classification: {decision.classification}",
        actor="Policy & Compliance Agent")

    db_update_case_by_tx(
        tx_id,
        policy_decision=json.dumps(decision.model_dump()),
        classification=decision.classification,
    )

    return {
        "policy": decision.model_dump(),
        "events": collected,
    }


# ── Node: route (conditional edge source) ─────────────────────────────────────

def route_decision(state: ResolutionState) -> str:
    return state["policy"]["decision"]


# ── Action Nodes (Routed through Action Gateway) ──────────────────────────────

def node_act_reverse(state: ResolutionState) -> dict:
    tx_id = state["tx_id"]
    policy = state["policy"]
    log, collected = _make_log(state)

    log("ACTION", "initiate_reversal", "INFO",
        f"Policy authorized auto-reversal for {tx_id} under {policy.get('rule_id', 'RULE_DEFAULT')}",
        actor="Action Gateway")

    res = ActionGateway.execute_action(
        tx_id=tx_id,
        action_type="AUTO_REVERSAL",
        payload={"amount": state["tx"]["amount"]},
        policy_version=policy.get("rule_version", "2.0"),
        rule_id=policy.get("rule_id", "RULE_DEFAULT"),
        actor="Action Gateway",
    )
    action_id = res["action_id"]

    return {
        "action_id": action_id,
        "verification_status": "VERIFIED" if res.get("verified") else "FAILED",
        "events": collected,
    }


def node_verify(state: ResolutionState) -> dict:
    tx_id = state["tx_id"]
    log, collected = _make_log(state)

    # Re-verify via ActionGateway independent verification
    verification = ActionGateway.verify_action(
        tx_id=tx_id,
        action_type="AUTO_REVERSAL",
        action_ref=state.get("action_id", f"REV-{tx_id}"),
        actor="Independent Verifier",
    )

    if verification["verified"]:
        return {"verification_status": "VERIFIED", "events": collected}
    else:
        return {"verification_status": "FAILED", "events": collected}


def node_act_sla(state: ResolutionState) -> dict:
    tx_id = state["tx_id"]
    policy = state["policy"]
    log, collected = _make_log(state)

    res = ActionGateway.execute_action(
        tx_id=tx_id,
        action_type="SLA_CHASE",
        payload={"amount": state["tx"]["amount"]},
        policy_version=policy.get("rule_version", "2.0"),
        rule_id=policy.get("rule_id", "RULE_DEFAULT"),
        actor="Action Gateway",
    )

    return {
        "action_id": res["action_id"],
        "verification_status": "VERIFIED" if res.get("verified") else "FAILED",
        "events": collected,
    }


def node_act_wallet(state: ResolutionState) -> dict:
    tx_id = state["tx_id"]
    tx = state["tx"]
    policy = state["policy"]
    log, collected = _make_log(state)

    res = ActionGateway.execute_action(
        tx_id=tx_id,
        action_type="WALLET_CREDIT_OFFER",
        payload={"amount": tx["amount"]},
        policy_version=policy.get("rule_version", "2.0"),
        rule_id=policy.get("rule_id", "RULE_DEFAULT"),
        actor="Action Gateway",
    )

    return {
        "action_id": res["action_id"],
        "verification_status": "VERIFIED" if res.get("verified") else "FAILED",
        "events": collected,
    }


def node_act_itemize(state: ResolutionState) -> dict:
    tx_id = state["tx_id"]
    tx = state["tx"]
    policy = state["policy"]
    log, collected = _make_log(state)

    try:
        parts = tx["merchant_status"].split("_")
        fee = float(parts[2]) if len(parts) > 2 and parts[1] == "DEDUCTION" else 0.0
        gst = float(parts[4]) if len(parts) > 4 and parts[3] == "GST" else 0.0
    except (ValueError, IndexError):
        fee, gst = 0.0, 0.0

    res = ActionGateway.execute_action(
        tx_id=tx_id,
        action_type="ITEMIZED_EXPLANATION",
        payload={"amount": tx["amount"], "fee": fee, "gst": gst},
        policy_version=policy.get("rule_version", "2.0"),
        rule_id=policy.get("rule_id", "RULE_DEFAULT"),
        actor="Action Gateway",
    )

    return {
        "action_id": res["action_id"],
        "verification_status": "VERIFIED" if res.get("verified") else "FAILED",
        "events": collected,
    }


def node_act_hold(state: ResolutionState) -> dict:
    tx_id = state["tx_id"]
    policy = state["policy"]
    log, collected = _make_log(state)

    reason = policy["reason"]
    res = ActionGateway.execute_action(
        tx_id=tx_id,
        action_type="COMPLIANCE_HOLD",
        payload={"amount": state["tx"]["amount"], "reason": reason},
        policy_version=policy.get("rule_version", "2.0"),
        rule_id=policy.get("rule_id", "RULE_DEFAULT"),
        actor="Action Gateway",
    )

    return {
        "action_id": res["action_id"],
        "escalation_reason": reason,
        "verification_status": "VERIFIED",
        "events": collected,
    }


# ── Agent 4: Dynamic Communication Agent (NO PRE-BUILT MESSAGES) ─────────────

def node_dynamic_communication(state: ResolutionState) -> dict:
    tx_id = state["tx_id"]
    tx = state["tx"]
    action_id = state.get("action_id", "N/A")
    decision = state["policy"]["decision"]
    reason = state["policy"]["reason"]
    log, collected = _make_log(state)

    dynamic_msg = generate_dynamic_message(
        tx_id=tx_id,
        tx=tx,
        decision=decision,
        action_id=action_id,
        reason=reason,
        log_func=log
    )

    db_update_transaction(tx_id, dynamic_message=dynamic_msg)
    db_update_case_by_tx(tx_id, dynamic_message=dynamic_msg)

    log("NOTIFICATION", "send_dynamic_notification", "SUCCESS",
        "Personalized notification dispatched to customer",
        visibility=AuditVisibility.CUSTOMER.value,
        actor="Communication Agent")

    return {
        "notification_sent": True,
        "dynamic_message": dynamic_msg,
        "events": collected,
    }


def node_escalate(state: ResolutionState) -> dict:
    tx_id = state["tx_id"]
    tx = state["tx"]
    log, collected = _make_log(state)

    reason = state.get("escalation_reason") or state["policy"]["reason"]
    evidence = state["evidence"]
    suggested = _generate_suggested_resolution(Evidence(**evidence))

    log("ESCALATION", "escalate", "INFO", f"Escalating to human desk: {reason}", actor="Escalation Node")
    case = create_support_case(tx_id, reason, evidence, suggested)
    log("ESCALATION", "create_support_case", "SUCCESS",
        f"HITL support case created: {case['case_id']} (Priority: HIGH)",
        actor="Escalation Node")

    dynamic_msg = generate_dynamic_message(
        tx_id=tx_id,
        tx=tx,
        decision="HUMAN_ESCALATION",
        action_id=case["case_id"],
        reason=reason,
        log_func=log
    )
    db_update_transaction(tx_id, resolution_status="ESCALATED", dynamic_message=dynamic_msg)
    db_update_case_by_tx(
        tx_id,
        customer_status="HUMAN_REVIEW",
        ops_status="ESCALATED",
        human_review_notes=reason,
        dynamic_message=dynamic_msg,
    )

    return {
        "support_case": case["case_id"],
        "escalation_reason": reason,
        "suggested_resolution": suggested,
        "resolution_status": "ESCALATED",
        "dynamic_message": dynamic_msg,
        "events": collected,
    }


def node_close(state: ResolutionState) -> dict:
    tx_id = state["tx_id"]
    policy_decision = state["policy"]["decision"]
    log, collected = _make_log(state)

    if policy_decision == "NO_ACTION":
        db_update_transaction(tx_id, resolution_status="NO_ACTION")
        db_update_case_by_tx(tx_id, customer_status="NO_ACTION", ops_status="NO_ACTION")
        log("INVESTIGATION", "no_action", "INFO",
            "Transaction is consistent across all systems. No action required.",
            actor="Resolution Engine")
        return {"resolution_status": "NO_ACTION", "events": collected}

    db_update_transaction(tx_id, resolution_status="RESOLVED")
    db_update_case_by_tx(tx_id, customer_status="RESOLVED", ops_status="RESOLVED")
    log("INVESTIGATION", "close", "SUCCESS",
        "Case successfully closed by ZeroTouch. No manual support ticket required.",
        actor="Resolution Engine")
    return {"resolution_status": "RESOLVED", "events": collected}


def route_verification(state: ResolutionState) -> str:
    return "close" if state.get("verification_status") == "VERIFIED" else "escalate"


# ── Build the Multi-Agent Graph ───────────────────────────────────────────────

def build_graph() -> StateGraph:
    g = StateGraph(ResolutionState)

    # Register segregated agent and action nodes
    g.add_node("investigate_ledgers",      node_investigate_ledgers)
    g.add_node("assess_risk_and_credit",   node_risk_and_credit)
    g.add_node("policy",                   node_policy)
    g.add_node("act_reverse",              node_act_reverse)
    g.add_node("verify",                   node_verify)
    g.add_node("act_sla",                  node_act_sla)
    g.add_node("act_wallet",               node_act_wallet)
    g.add_node("act_itemize",              node_act_itemize)
    g.add_node("act_hold",                 node_act_hold)
    g.add_node("dynamic_communication",    node_dynamic_communication)
    g.add_node("escalate",                 node_escalate)
    g.add_node("close",                    node_close)

    # Pipeline: Ledger Investigation ➔ Risk & CIBIL Profiling ➔ Policy Compliance
    g.set_entry_point("investigate_ledgers")
    g.add_edge("investigate_ledgers", "assess_risk_and_credit")
    g.add_edge("assess_risk_and_credit", "policy")

    # Policy Routing
    g.add_conditional_edges(
        "policy",
        route_decision,
        {
            "AUTO_REVERSAL":       "act_reverse",
            "SLA_CHASE":           "act_sla",
            "WALLET_CREDIT_OFFER": "act_wallet",
            "ITEMIZED_EXPLANATION":"act_itemize",
            "COMPLIANCE_HOLD":     "act_hold",
            "HUMAN_ESCALATION":    "escalate",
            "NO_ACTION":           "close",
        },
    )

    # W1: Reverse ➔ Verify ➔ Communication Agent ➔ Close
    g.add_edge("act_reverse", "verify")
    g.add_conditional_edges(
        "verify",
        route_verification,
        {"close": "dynamic_communication", "escalate": "escalate"}
    )

    # W2: Act ➔ Communication Agent ➔ Close
    g.add_edge("act_sla",    "dynamic_communication")
    g.add_edge("act_wallet", "dynamic_communication")
    g.add_edge("dynamic_communication", "close")

    # W3: Itemize ➔ Close (merchant report)
    g.add_edge("act_itemize", "close")

    # W3 compliance: Hold ➔ Escalate
    g.add_edge("act_hold", "escalate")

    # Terminals
    g.add_edge("close",    END)
    g.add_edge("escalate", END)

    return g.compile()


# Compile once at module import
_graph = build_graph()


# ── Public entry point ────────────────────────────────────────────────────────

def run_resolution(tx_id: str) -> ResolutionResult:
    tx = db_get_transaction(tx_id)
    if not tx:
        raise ValueError(f"Transaction {tx_id} not found in database")

    cid = case_id_for_tx(tx_id)

    if tx["resolution_status"] != "PENDING":
        events = db_get_events(tx_id)
        return _state_to_result(tx_id, tx, events, already_done=True)

    initial_state: ResolutionState = {
        "tx_id": tx_id,
        "case_id": cid,
        "tx": tx,
        "events": [],
        "evidence": None,
        "evidence_matrix": None,
        "risk_assessment": None,
        "policy": None,
        "action_id": None,
        "verification_status": None,
        "notification_sent": False,
        "dynamic_message": None,
        "support_case": None,
        "escalation_reason": None,
        "suggested_resolution": None,
        "investigation_narrative": None,
        "resolution_status": "PENDING",
    }

    final_state = _graph.invoke(initial_state)

    # Fetch events from DB (source of truth)
    events = db_get_events(tx_id)
    tx_after = db_get_transaction(tx_id)
    policy_dict = final_state.get("policy") or {}

    return ResolutionResult(
        transaction_id=tx_id,
        customer_name=tx.get("customer_name", "Paytm User"),
        cibil_score=tx.get("cibil_score", 750),
        is_first_time_user=tx.get("is_first_time_user", False),
        decision=policy_dict.get("decision", tx_after["resolution_status"]),
        authorized=policy_dict.get("authorized", False),
        action_id=final_state.get("action_id") or tx_after.get("action_id"),
        verification_status=final_state.get("verification_status"),
        notification_sent=final_state.get("notification_sent", False),
        dynamic_message=final_state.get("dynamic_message") or tx_after.get("dynamic_message"),
        support_case=final_state.get("support_case"),
        resolution_status=tx_after["resolution_status"],
        events=[AuditEvent(**{k: v for k, v in e.items() if k != "id" and k != "transaction_id"})
                for e in events],
        evidence=Evidence(**final_state["evidence"]) if final_state.get("evidence") else None,
        escalation_reason=final_state.get("escalation_reason"),
        suggested_resolution=final_state.get("suggested_resolution"),
        agent_powered=True,
        case_id=cid,
        rule_id=policy_dict.get("rule_id"),
        classification=policy_dict.get("classification"),
    )


def _state_to_result(tx_id, tx, events, already_done=False) -> ResolutionResult:
    evidence = Evidence(
        transaction_id=tx_id,
        customer_name=tx.get("customer_name", "Paytm User"),
        bank=tx["bank_status"],
        network=tx["network_status"],
        merchant=tx["merchant_status"],
        settlement=tx["settlement_status"],
        amount=tx["amount"],
        risk=tx["risk_score"],
        cibil_score=tx.get("cibil_score", 750),
        is_first_time_user=tx.get("is_first_time_user", False),
        previous_refund=tx["previous_refund"],
    )
    cid = case_id_for_tx(tx_id)
    case = db_get_case_by_tx(tx_id)
    rule_id = None
    classification = None
    decision = tx["resolution_status"]
    authorized = False
    if case and case.get("policy_decision"):
        try:
            pd = json.loads(case["policy_decision"])
            rule_id = pd.get("rule_id")
            classification = pd.get("classification")
            decision = pd.get("decision", decision)
            authorized = pd.get("authorized", False)
        except Exception:
            pass

    return ResolutionResult(
        transaction_id=tx_id,
        customer_name=tx.get("customer_name", "Paytm User"),
        cibil_score=tx.get("cibil_score", 750),
        is_first_time_user=tx.get("is_first_time_user", False),
        decision=decision,
        authorized=authorized,
        action_id=tx.get("action_id"),
        verification_status="VERIFIED" if tx.get("action_id") else None,
        notification_sent=False,
        dynamic_message=tx.get("dynamic_message"),
        support_case=None,
        resolution_status=tx["resolution_status"],
        events=[AuditEvent(**{k: v for k, v in e.items() if k not in ("id", "transaction_id")})
                for e in events],
        evidence=evidence,
        escalation_reason=None,
        suggested_resolution=None,
        agent_powered=True,
        case_id=cid,
        rule_id=rule_id,
        classification=classification,
    )


def _generate_suggested_resolution(evidence: Evidence) -> str:
    if evidence.network in ("UNKNOWN", "SLA_BREACHED"):
        return ("Investigate network trace and settlement status before initiating reversal. "
                "Contact issuing bank gateway provider.")
    if evidence.cibil_score < 620:
        return (f"Subprime customer CIBIL score ({evidence.cibil_score}). "
                "Verify customer identity and dispute history before manual refund.")
    if evidence.is_first_time_user and evidence.amount > 5000:
        return ("First-Time User high-value transaction. "
                "Verify user KYC details and device fingerprint before releasing funds.")
    if evidence.risk >= 0.30:
        return ("High fraud risk transaction. Verify authenticity before processing any refund.")
    if "KYC" in evidence.settlement or "HELD" in evidence.settlement:
        return ("Request updated KYC documents from merchant: Aadhaar, PAN Card, and bank statement.")
    return "Manual review required across all four payment system ledgers."
