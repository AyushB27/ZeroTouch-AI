"""
LangGraph Stateful Orchestration for ZeroTouch.

Replaces the old linear run_resolution() function with a proper
directed state graph:

    [start]
       |
    [investigate]  <- AI agent (Gemini Function Calling + RAG)
       |
    [policy]       <- Deterministic policy engine (no LLM)
       |
    [route] ──────> AUTO_REVERSAL     -> [act_reverse]  -> [verify] -> [notify] -> [close]
               ├──> SLA_CHASE         -> [act_sla]      -> [notify] -> [close]
               ├──> WALLET_CREDIT     -> [act_wallet]   -> [notify] -> [close]
               ├──> ITEMIZED_EXPL     -> [act_itemize]  -> [close]
               ├──> COMPLIANCE_HOLD   -> [act_hold]     -> [escalate]
               ├──> HUMAN_ESCALATION  -> [escalate]
               └──> NO_ACTION         -> [close]
"""

import operator
from typing import TypedDict, List, Optional, Annotated

from langgraph.graph import StateGraph, END

from backend.models import Evidence, AuditEvent, ResolutionResult, PolicyDecision
from backend.policy import evaluate_policy
from backend.database import (
    db_get_transaction, db_update_transaction, db_add_event, db_get_events
)
from backend.tools.actions import initiate_reversal, verify_resolution
from backend.tools.notifications import send_customer_notification, create_support_case
from backend.tools.w2_w3_actions import (
    chase_bank_sla, offer_wallet_credit,
    generate_itemized_explanation, flag_compliance_hold,
)
from backend.agent import investigate_transaction


# ── State schema ──────────────────────────────────────────────────────────────

class ResolutionState(TypedDict):
    tx_id: str
    tx: dict
    events: Annotated[List[dict], operator.add]   # append-only list
    evidence: Optional[dict]
    policy: Optional[dict]                         # PolicyDecision as dict
    action_id: Optional[str]
    verification_status: Optional[str]
    notification_sent: bool
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


# ── Node: Investigate ─────────────────────────────────────────────────────────

def node_investigate(state: ResolutionState) -> dict:
    tx_id = state["tx_id"]
    tx = state["tx"]

    log, collected = _make_log(state)
    log("INVESTIGATION", "start", "INFO", f"ZeroTouch LangGraph agent started for {tx_id}")
    log("INVESTIGATION", "load_transaction", "SUCCESS",
        f"Transaction {tx_id} loaded from database: Rs.{tx['amount']:.0f}")

    narrative = investigate_transaction(tx_id, tx, log)
    log("INVESTIGATION", "narrative_complete", "SUCCESS",
        "AI investigation narrative produced")

    evidence = Evidence(
        transaction_id=tx_id,
        bank=tx["bank_status"],
        network=tx["network_status"],
        merchant=tx["merchant_status"],
        settlement=tx["settlement_status"],
        amount=tx["amount"],
        risk=tx["risk_score"],
        previous_refund=tx["previous_refund"],
    )
    log("INVESTIGATION", "reconcile", "SUCCESS",
        "Evidence assembled from all four system APIs")

    return {
        "evidence": evidence.model_dump(),
        "investigation_narrative": narrative,
        "events": collected,
    }


# ── Node: Policy ──────────────────────────────────────────────────────────────

def node_policy(state: ResolutionState) -> dict:
    evidence = Evidence(**state["evidence"])
    decision: PolicyDecision = evaluate_policy(evidence)

    log, collected = _make_log(state)
    log("POLICY", "evaluate_policy", "SUCCESS",
        f"Policy decision: {decision.decision} | Authorized: {decision.authorized}")

    return {
        "policy": decision.model_dump(),
        "events": collected,
    }


# ── Node: route (conditional edge source) ─────────────────────────────────────

def route_decision(state: ResolutionState) -> str:
    return state["policy"]["decision"]


# ── Node: act_reverse (W1 auto-reversal) ─────────────────────────────────────

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
            f"Reversal {action_id} created and applied")

    return {"action_id": action_id, "events": collected}


# ── Node: verify ──────────────────────────────────────────────────────────────

def node_verify(state: ResolutionState) -> dict:
    tx_id = state["tx_id"]
    log, collected = _make_log(state)

    log("VERIFICATION", "verify_resolution", "INFO",
        "Independently verifying reversal outcome...")
    result = verify_resolution(tx_id)

    if result["verified"]:
        log("VERIFICATION", "verify_resolution", "SUCCESS",
            "Resolution independently verified across all ledgers")
        return {"verification_status": "VERIFIED", "events": collected}
    else:
        log("VERIFICATION", "verify_resolution", "FAILED",
            "Verification failed — escalating to human review")
        return {"verification_status": "FAILED", "events": collected}


# ── Node: act_sla (W2 SLA chase) ─────────────────────────────────────────────

def node_act_sla(state: ResolutionState) -> dict:
    tx_id = state["tx_id"]
    tx = state["tx"]
    log, collected = _make_log(state)

    log("ACTION", "chase_bank_sla", "INFO",
        f"SLA breach confirmed. Triggering bank escalation API for {tx_id}")
    result = chase_bank_sla(tx_id)
    log("ACTION", "chase_bank_sla", "SUCCESS",
        f"Bank SLA escalation raised: {result['chase_ref']}. ETA: {result['eta_hours']}h")

    return {"action_id": result["chase_ref"], "events": collected}


# ── Node: act_wallet (W2 wallet credit) ──────────────────────────────────────

def node_act_wallet(state: ResolutionState) -> dict:
    tx_id = state["tx_id"]
    tx = state["tx"]
    log, collected = _make_log(state)

    log("ACTION", "offer_wallet_credit", "INFO",
        f"Destination bank account invalid. Initiating Paytm Wallet credit for {tx_id}")
    result = offer_wallet_credit(tx_id, tx["amount"])
    log("ACTION", "offer_wallet_credit", "SUCCESS",
        f"Rs.{tx['amount']:.0f} credited to Paytm Wallet: {result['credit_ref']}")

    return {"action_id": result["credit_ref"], "events": collected}


# ── Node: act_itemize (W3 fee explanation) ───────────────────────────────────

def node_act_itemize(state: ResolutionState) -> dict:
    tx_id = state["tx_id"]
    tx = state["tx"]
    log, collected = _make_log(state)

    # Parse fee and GST from merchant_status, e.g. FEE_DEDUCTION_300_GST_50.
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
        f"Itemized breakdown sent to merchant: gross Rs.{result['gross_amount']:.0f}, platform fee Rs.{fee:.0f}, GST Rs.{gst:.0f}, net Rs.{result['net_settled']:.0f}. Ref {result['explanation_ref']}.")

    return {"action_id": result["explanation_ref"], "events": collected}


# ── Node: act_hold (W3 compliance hold) ──────────────────────────────────────

def node_act_hold(state: ResolutionState) -> dict:
    tx_id = state["tx_id"]
    log, collected = _make_log(state)

    reason = state["policy"]["reason"]
    log("ACTION", "flag_compliance_hold", "INFO",
        f"KYC/compliance hold detected. Routing {tx_id} to compliance team")
    result = flag_compliance_hold(tx_id, reason)
    log("ACTION", "flag_compliance_hold", "SUCCESS",
        f"Compliance case raised: {result['case_ref']}. Merchant notified of required docs.")

    return {
        "action_id": result["case_ref"],
        "escalation_reason": result["reason"],
        "events": collected,
    }


# ── Node: notify ──────────────────────────────────────────────────────────────

def node_notify(state: ResolutionState) -> dict:
    tx_id = state["tx_id"]
    tx = state["tx"]
    action_id = state.get("action_id", "N/A")
    log, collected = _make_log(state)

    notif = send_customer_notification(tx_id, tx["amount"], action_id)
    log("NOTIFICATION", "send_notification", "SUCCESS",
        f"Customer notified via {notif['channel']}")

    return {"notification_sent": True, "events": collected}


# ── Node: escalate ────────────────────────────────────────────────────────────

def node_escalate(state: ResolutionState) -> dict:
    tx_id = state["tx_id"]
    tx = state["tx"]
    log, collected = _make_log(state)

    reason = (
        state.get("escalation_reason")
        or state["policy"]["reason"]
    )
    evidence = state["evidence"]
    suggested = _generate_suggested_resolution(Evidence(**evidence))

    log("ESCALATION", "escalate", "INFO", f"Escalating to human: {reason}")
    case = create_support_case(tx_id, reason, evidence, suggested)
    log("ESCALATION", "create_support_case", "SUCCESS",
        f"Support case created: {case['case_id']} (Priority: HIGH)")

    db_update_transaction(tx_id, resolution_status="ESCALATED")

    return {
        "support_case": case["case_id"],
        "escalation_reason": reason,
        "suggested_resolution": suggested,
        "resolution_status": "ESCALATED",
        "events": collected,
    }


# ── Node: close ───────────────────────────────────────────────────────────────

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
        "Case closed by ZeroTouch. No support ticket created.")
    return {"resolution_status": "RESOLVED", "events": collected}


# ── Node: verify_or_escalate (conditional) ────────────────────────────────────

def route_verification(state: ResolutionState) -> str:
    return "close" if state.get("verification_status") == "VERIFIED" else "escalate"


# ── Build the graph ───────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    g = StateGraph(ResolutionState)

    # Register nodes
    g.add_node("investigate",  node_investigate)
    g.add_node("policy",       node_policy)
    g.add_node("act_reverse",  node_act_reverse)
    g.add_node("verify",       node_verify)
    g.add_node("act_sla",      node_act_sla)
    g.add_node("act_wallet",   node_act_wallet)
    g.add_node("act_itemize",  node_act_itemize)
    g.add_node("act_hold",     node_act_hold)
    g.add_node("notify",       node_notify)
    g.add_node("escalate",     node_escalate)
    g.add_node("close",        node_close)

    # Linear flow: start → investigate → policy → route
    g.set_entry_point("investigate")
    g.add_edge("investigate", "policy")

    # Conditional routing after policy
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

    # W1: reverse → verify → (close or escalate) → END
    g.add_edge("act_reverse", "verify")
    g.add_conditional_edges("verify", route_verification, {
        "close": "close", "escalate": "escalate"
    })

    # W2: act → notify → close
    g.add_edge("act_sla",    "notify")
    g.add_edge("act_wallet", "notify")
    g.add_edge("notify",     "close")

    # W3: itemize → close (no customer notification needed — it's a merchant flow)
    g.add_edge("act_itemize", "close")

    # W3 compliance: hold → escalate
    g.add_edge("act_hold", "escalate")

    # Terminal nodes
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
        # Already processed — return current state
        events = db_get_events(tx_id)
        return _state_to_result(tx_id, tx, events, already_done=True)

    initial_state: ResolutionState = {
        "tx_id": tx_id,
        "tx": tx,
        "events": [],
        "evidence": None,
        "policy": None,
        "action_id": None,
        "verification_status": None,
        "notification_sent": False,
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
        decision=final_state["policy"]["decision"],
        authorized=final_state["policy"]["authorized"],
        action_id=final_state.get("action_id"),
        verification_status=final_state.get("verification_status"),
        notification_sent=final_state.get("notification_sent", False),
        support_case=final_state.get("support_case"),
        resolution_status=tx_after["resolution_status"],
        events=[AuditEvent(**{k: v for k, v in e.items() if k != "id" and k != "transaction_id"})
                for e in events],
        evidence=Evidence(**final_state["evidence"]) if final_state.get("evidence") else None,
        escalation_reason=final_state.get("escalation_reason"),
        suggested_resolution=final_state.get("suggested_resolution"),
    )


def _state_to_result(tx_id, tx, events, already_done=False) -> ResolutionResult:
    """Build a ResolutionResult from the DB state for already-processed transactions."""
    evidence = Evidence(
        transaction_id=tx_id,
        bank=tx["bank_status"],
        network=tx["network_status"],
        merchant=tx["merchant_status"],
        settlement=tx["settlement_status"],
        amount=tx["amount"],
        risk=tx["risk_score"],
        previous_refund=tx["previous_refund"],
    )
    return ResolutionResult(
        transaction_id=tx_id,
        decision=tx["resolution_status"],
        authorized=False,
        action_id=tx.get("action_id"),
        verification_status=None,
        notification_sent=False,
        support_case=None,
        resolution_status=tx["resolution_status"],
        events=[AuditEvent(**{k: v for k, v in e.items() if k not in ("id", "transaction_id")})
                for e in events],
        evidence=evidence,
        escalation_reason=None,
        suggested_resolution=None,
    )


def _generate_suggested_resolution(evidence: Evidence) -> str:
    if evidence.network in ("UNKNOWN", "SLA_BREACHED"):
        return ("Investigate network and settlement status before initiating any reversal. "
                "Contact payment network provider for transaction trace.")
    if evidence.risk >= 0.30:
        return ("High risk transaction. Verify customer identity and transaction "
                "authenticity before processing any refund.")
    if "KYC" in evidence.settlement or "HELD" in evidence.settlement:
        return ("Request updated KYC documents from merchant: Aadhaar, PAN Card, "
                "and last 3 months bank statement.")
    return ("Manual investigation required. Review all four payment system records "
            "before taking financial action.")
