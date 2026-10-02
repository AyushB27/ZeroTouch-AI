"""
LangGraph Multi-Agent Stateful Orchestration for ZeroTouch.

Segregated Multi-Agent Pipeline:
  1. 🕵️ Ledger Investigator Agent (queries Bank, NPCI, Merchant, Settlement)
  2. 📊 Risk & Credit Profiling Agent (evaluates CIBIL score, First-Time User status, ceilings)
  3. ⚖️ Policy & Compliance Agent (RAG knowledge base + deterministic policy logic)
  4. ✍️ Dynamic Communication Agent (NO PRE-BUILT MESSAGES - dynamically writes via LLM)
  5. ⚙️ Action & Verification Nodes (executes ledger updates and independent verification)
"""

import operator
from typing import TypedDict, List, Optional, Annotated

from langgraph.graph import StateGraph, END

from backend.models import Evidence, AuditEvent, ResolutionResult, PolicyDecision, RiskAssessment
from backend.policy import evaluate_policy
from backend.database import (
    db_get_transaction, db_update_transaction, db_add_event, db_get_events
)
from backend.tools.actions import initiate_reversal, verify_resolution
from backend.tools.notifications import create_support_case
from backend.tools.w2_w3_actions import (
    chase_bank_sla, offer_wallet_credit,
    generate_itemized_explanation, flag_compliance_hold,
)
from backend.agent import investigate_transaction
from backend.risk_agent import assess_risk_and_credit
from backend.communication_agent import generate_dynamic_message


# ── State schema ──────────────────────────────────────────────────────────────

class ResolutionState(TypedDict):
    tx_id: str
    tx: dict
    events: Annotated[List[dict], operator.add]   # append-only list
    evidence: Optional[dict]
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

def _log(state: ResolutionState, event_type, step, status, message) -> dict:
    e = db_add_event(state["tx_id"], event_type, step, status, message)
    return e


def _make_log(state):
    """Returns a log callback that appends to DB AND to state events."""
    collected = []
    def log(et, step, st, msg):
        e = _log(state, et, step, st, msg)
        collected.append(e)
        return e
    return log, collected


# ── Agent 1: Ledger Investigator Agent ────────────────────────────────────────

def node_investigate_ledgers(state: ResolutionState) -> dict:
    tx_id = state["tx_id"]
    tx = state["tx"]

    log, collected = _make_log(state)
    log("INVESTIGATION", "investigator_agent_start", "INFO",
        f"[Ledger Investigator Agent] Initiating multi-system ledger query for {tx_id}")
    log("INVESTIGATION", "load_transaction", "SUCCESS",
        f"Transaction {tx_id} loaded: ₹{tx['amount']:,.0f} | Customer: {tx.get('customer_name', 'User')}")

    narrative = investigate_transaction(tx_id, tx, log)
    log("INVESTIGATION", "narrative_complete", "SUCCESS",
        "[Ledger Investigator Agent] Ledger reconciliation complete. Discrepancy isolated.")

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

    return {
        "evidence": evidence.model_dump(),
        "investigation_narrative": narrative,
        "events": collected,
    }


# ── Agent 2: Risk & Credit Profiling Agent ────────────────────────────────────

def node_risk_and_credit(state: ResolutionState) -> dict:
    tx = state["tx"]
    log, collected = _make_log(state)

    log("RISK_ANALYSIS", "risk_agent_start", "INFO",
        "[Risk & Credit Agent] Profiling customer creditworthiness, CIBIL score, and tenure...")

    risk_assessment: RiskAssessment = assess_risk_and_credit(tx, log)

    return {
        "risk_assessment": risk_assessment.model_dump(),
        "events": collected,
    }


# ── Agent 3: Policy & Compliance Agent ────────────────────────────────────────

def node_policy(state: ResolutionState) -> dict:
    evidence = Evidence(**state["evidence"])
    log, collected = _make_log(state)

    log("POLICY", "policy_agent_start", "INFO",
        "[Policy & Compliance Agent] Cross-referencing RAG refund policy with ledger evidence and credit tier...")

    decision: PolicyDecision = evaluate_policy(evidence)

    log("POLICY", "evaluate_policy", "SUCCESS",
        f"[Policy Agent] Verdict: {decision.decision} | Authorized: {decision.authorized}")

    return {
        "policy": decision.model_dump(),
        "events": collected,
    }


# ── Node: route (conditional edge source) ─────────────────────────────────────

def route_decision(state: ResolutionState) -> str:
    return state["policy"]["decision"]


# ── Action Nodes ──────────────────────────────────────────────────────────────

def node_act_reverse(state: ResolutionState) -> dict:
    tx_id = state["tx_id"]
    log, collected = _make_log(state)

    log("ACTION", "initiate_reversal", "INFO",
        f"Policy authorized auto-reversal for {tx_id}")
    reversal = initiate_reversal(tx_id)
    action_id = reversal["action_id"]

    if reversal["status"] == "ALREADY_EXECUTED":
        log("ACTION", "initiate_reversal", "INFO",
            f"Reversal already executed: {action_id}")
    else:
        log("ACTION", "initiate_reversal", "SUCCESS",
            f"Reversal {action_id} created and applied to bank ledger")

    return {"action_id": action_id, "events": collected}


def node_verify(state: ResolutionState) -> dict:
    tx_id = state["tx_id"]
    log, collected = _make_log(state)

    log("VERIFICATION", "verify_resolution", "INFO",
        "Independently verifying reversal across core ledgers...")
    result = verify_resolution(tx_id)

    if result["verified"]:
        log("VERIFICATION", "verify_resolution", "SUCCESS",
            "Resolution independently verified across all ledgers")
        return {"verification_status": "VERIFIED", "events": collected}
    else:
        log("VERIFICATION", "verify_resolution", "FAILED",
            "Verification failed — escalating to human review")
        return {"verification_status": "FAILED", "events": collected}


def node_act_sla(state: ResolutionState) -> dict:
    tx_id = state["tx_id"]
    log, collected = _make_log(state)

    log("ACTION", "chase_bank_sla", "INFO",
        f"Refund SLA exceeded. Triggering bank escalation API for {tx_id}")
    result = chase_bank_sla(tx_id)
    log("ACTION", "chase_bank_sla", "SUCCESS",
        f"Bank SLA escalation raised: {result['chase_ref']}. ETA: {result['eta_hours']}h")

    return {"action_id": result["chase_ref"], "events": collected}


def node_act_wallet(state: ResolutionState) -> dict:
    tx_id = state["tx_id"]
    tx = state["tx"]
    log, collected = _make_log(state)

    ft_text = " (First-Time User priority)" if tx.get("is_first_time_user") else ""
    log("ACTION", "offer_wallet_credit", "INFO",
        f"Destination account bounced. Crediting Paytm Wallet for {tx_id}{ft_text}")
    result = offer_wallet_credit(tx_id, tx["amount"])
    log("ACTION", "offer_wallet_credit", "SUCCESS",
        f"₹{tx['amount']:,.0f} credited to Paytm Wallet: {result['credit_ref']}")

    return {"action_id": result["credit_ref"], "events": collected}


def node_act_itemize(state: ResolutionState) -> dict:
    tx_id = state["tx_id"]
    tx = state["tx"]
    log, collected = _make_log(state)

    try:
        parts = tx["merchant_status"].split("_")
        fee = float(parts[2]) if len(parts) > 2 and parts[1] == "DEDUCTION" else 0.0
        gst = float(parts[4]) if len(parts) > 4 and parts[3] == "GST" else 0.0
    except (ValueError, IndexError):
        fee, gst = 0.0, 0.0

    log("ACTION", "generate_itemized_explanation", "INFO",
        f"Settlement shortfall detected. Generating itemized reconciliation for {tx_id}")
    result = generate_itemized_explanation(tx_id, tx["amount"], fee, gst)
    log("ACTION", "generate_itemized_explanation", "SUCCESS",
        f"Itemized breakdown sent to merchant: gross ₹{result['gross_amount']:,.0f}, platform fee ₹{fee:,.0f}, GST ₹{gst:,.0f}, net ₹{result['net_settled']:,.0f}. Ref {result['explanation_ref']}.")

    return {"action_id": result["explanation_ref"], "events": collected}


def node_act_hold(state: ResolutionState) -> dict:
    tx_id = state["tx_id"]
    log, collected = _make_log(state)

    reason = state["policy"]["reason"]
    log("ACTION", "flag_compliance_hold", "INFO",
        f"KYC/compliance hold detected. Routing {tx_id} to compliance team")
    result = flag_compliance_hold(tx_id, reason)
    log("ACTION", "flag_compliance_hold", "SUCCESS",
        f"Compliance case raised: {result['case_ref']}. Merchant notified to upload renewed KYC.")

    return {
        "action_id": result["case_ref"],
        "escalation_reason": result["reason"],
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

    # Call Dynamic Communication Agent (Gemini synthesis with zero boilerplate)
    dynamic_msg = generate_dynamic_message(
        tx_id=tx_id,
        tx=tx,
        decision=decision,
        action_id=action_id,
        reason=reason,
        log_func=log
    )

    db_update_transaction(tx_id, dynamic_message=dynamic_msg)
    log("NOTIFICATION", "send_dynamic_notification", "SUCCESS",
        f"Personalized notification dispatched via SMS & Paytm In-App Push")

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

    log("ESCALATION", "escalate", "INFO", f"Escalating to human desk: {reason}")
    case = create_support_case(tx_id, reason, evidence, suggested)
    log("ESCALATION", "create_support_case", "SUCCESS",
        f"HITL support case created: {case['case_id']} (Priority: HIGH)")

    # Synthesize escalation note
    dynamic_msg = generate_dynamic_message(
        tx_id=tx_id,
        tx=tx,
        decision="HUMAN_ESCALATION",
        action_id=case["case_id"],
        reason=reason,
        log_func=log
    )
    db_update_transaction(tx_id, resolution_status="ESCALATED", dynamic_message=dynamic_msg)

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
        log("INVESTIGATION", "no_action", "INFO",
            "Transaction is consistent across all systems. No action required.")
        return {"resolution_status": "NO_ACTION", "events": collected}

    db_update_transaction(tx_id, resolution_status="RESOLVED")
    log("INVESTIGATION", "close", "SUCCESS",
        "Case successfully closed by ZeroTouch. No manual support ticket required.")
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

    if tx["resolution_status"] != "PENDING":
        events = db_get_events(tx_id)
        return _state_to_result(tx_id, tx, events, already_done=True)

    initial_state: ResolutionState = {
        "tx_id": tx_id,
        "tx": tx,
        "events": [],
        "evidence": None,
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

    return ResolutionResult(
        transaction_id=tx_id,
        customer_name=tx.get("customer_name", "Paytm User"),
        cibil_score=tx.get("cibil_score", 750),
        is_first_time_user=tx.get("is_first_time_user", False),
        decision=final_state["policy"]["decision"],
        authorized=final_state["policy"]["authorized"],
        action_id=final_state.get("action_id"),
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
    return ResolutionResult(
        transaction_id=tx_id,
        customer_name=tx.get("customer_name", "Paytm User"),
        cibil_score=tx.get("cibil_score", 750),
        is_first_time_user=tx.get("is_first_time_user", False),
        decision=tx["resolution_status"],
        authorized=False,
        action_id=tx.get("action_id"),
        verification_status=None,
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
