from datetime import datetime, timezone
from backend.data import TRANSACTIONS, AUDIT_EVENTS, add_event
from backend.models import Evidence, ResolutionResult, AuditEvent
from backend.policy import evaluate_policy
from backend.tools.bank import check_bank_status
from backend.tools.network import check_network_status
from backend.tools.merchant import check_merchant_ledger
from backend.tools.settlement import check_settlement
from backend.tools.actions import initiate_reversal, verify_resolution
from backend.tools.notifications import send_customer_notification, create_support_case
from backend.agent import investigate_transaction


def run_resolution(tx_id: str) -> ResolutionResult:
    tx = TRANSACTIONS.get(tx_id)
    if not tx:
        raise ValueError(f"Transaction {tx_id} not found")

    # --- IDEMPOTENCY GUARD ---
    # If already processed, replay existing result without re-executing
    if tx["resolution_status"] != "PENDING":
        existing_events = [AuditEvent(**e) for e in AUDIT_EVENTS.get(tx_id, [])]
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
        status = tx["resolution_status"]
        return ResolutionResult(
            transaction_id=tx_id,
            decision=("AUTO_REVERSAL" if status == "RESOLVED"
                      else "HUMAN_ESCALATION" if status == "ESCALATED"
                      else "NO_ACTION"),
            authorized=(status == "RESOLVED"),
            action_id=tx.get("action_id"),
            verification_status=("VERIFIED" if status == "RESOLVED" else None),
            notification_sent=(status == "RESOLVED"),
            support_case=(f"CASE-ZT{tx_id[2:]}" if status == "ESCALATED" else None),
            resolution_status=status,
            events=existing_events,
            evidence=evidence,
            escalation_reason=("Transaction was previously escalated." if status == "ESCALATED" else None),
            suggested_resolution=None,
            investigation_narrative="[Cached from previous run] " + (
                "The customer was debited, but the payment network and merchant ledger show inconsistencies." 
                if status == "AUTO_REVERSAL" else "Investigation details have been escalated."
            ),
            agent_powered=False,
        )

    events = AUDIT_EVENTS.setdefault(tx_id, [])

    def log(event_type, step, status, message):
        e = add_event(tx_id, event_type, step, status, message)
        return e

    # --- INVESTIGATION ---
    log("INVESTIGATION", "start", "INFO", f"Agent started investigation for {tx_id}")
    log("INVESTIGATION", "load_transaction", "SUCCESS", f"Transaction {tx_id} loaded: \u20b9{tx['amount']:.0f}")

    # --- LAYER 3: AI RESOLUTION AGENT ---
    # Agent autonomously fetches data via tools and reasons over it.
    api_key_present = bool(__import__("os").getenv("GEMINI_API_KEY") or __import__("os").getenv("GOOGLE_API_KEY"))
    narrative = investigate_transaction(tx_id, tx, log)
    
    log(
        "INVESTIGATION", "ai_agent", "SUCCESS",
        f"Agent investigation complete {'(Gemini Tool-Calling)' if api_key_present else '(deterministic fallback)'}"
    )

    # --- RECONCILE (For Policy Engine) ---
    # After the agent fetches the data, we build the immutable Evidence object for Layer 4
    # The tools updated the in-memory 'tx' object indirectly? Wait!
    # No, the tools return the status, but they don't mutate `TRANSACTIONS`.
    # Wait, check_bank_status(tx_id) reads from TRANSACTIONS. TRANSACTIONS ALREADY HAS THE DATA.
    # The whole system is mocked with pre-existing data in `tx`.
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
    log("INVESTIGATION", "reconcile", "SUCCESS", "Evidence assembled for Policy Engine")

    # --- LAYER 4: POLICY & RISK CONTROL ---
    policy = evaluate_policy(evidence)
    log(
        "POLICY",
        "evaluate_policy",
        "SUCCESS",
        f"Policy decision: {policy.decision} | Authorized: {policy.authorized}",
    )

    # --- BRANCH: NO ACTION ---
    if policy.decision == "NO_ACTION":
        tx["resolution_status"] = "NO_ACTION"
        log("INVESTIGATION", "no_action", "INFO", "Transaction is consistent. No action required.")
        return ResolutionResult(
            transaction_id=tx_id,
            decision="NO_ACTION",
            authorized=False,
            action_id=None,
            verification_status=None,
            notification_sent=False,
            support_case=None,
            resolution_status="NO_ACTION",
            events=[AuditEvent(**e) for e in AUDIT_EVENTS[tx_id]],
            evidence=evidence,
            escalation_reason=None,
            suggested_resolution=None,
            investigation_narrative=narrative,
            agent_powered=api_key_present,
        )

    # --- BRANCH: HUMAN ESCALATION ---
    if policy.decision == "HUMAN_ESCALATION":
        tx["resolution_status"] = "ESCALATED"
        log("ESCALATION", "escalate", "INFO", f"Escalating to human: {policy.reason}")
        suggested = _generate_suggested_resolution(evidence)
        case = create_support_case(
            tx_id,
            policy.reason,
            evidence.model_dump(),
            suggested,
        )
        log("ESCALATION", "create_support_case", "SUCCESS", f"Support case created: {case['case_id']}")
        return ResolutionResult(
            transaction_id=tx_id,
            decision="HUMAN_ESCALATION",
            authorized=False,
            action_id=None,
            verification_status=None,
            notification_sent=False,
            support_case=case["case_id"],
            resolution_status="ESCALATED",
            events=[AuditEvent(**e) for e in AUDIT_EVENTS[tx_id]],
            evidence=evidence,
            escalation_reason=policy.reason,
            suggested_resolution=suggested,
            investigation_narrative=narrative,
            agent_powered=api_key_present,
        )

    # --- BRANCH: AUTO REVERSAL ---
    log("ACTION", "initiate_reversal", "INFO", f"Policy approved. Initiating reversal for {tx_id}")
    reversal = initiate_reversal(tx_id)

    if reversal["status"] == "ALREADY_EXECUTED":
        log("ACTION", "initiate_reversal", "INFO", f"Reversal already executed: {reversal['action_id']}")
    else:
        log("ACTION", "initiate_reversal", "SUCCESS", f"{reversal['action_id']} created")

    action_id = reversal["action_id"]

    # --- VERIFICATION ---
    log("VERIFICATION", "verify_resolution", "INFO", "Independently verifying resolution...")
    verification = verify_resolution(tx_id)

    if not verification["verified"]:
        log("VERIFICATION", "verify_resolution", "FAILED", "Verification failed. Escalating to human.")
        tx["resolution_status"] = "ESCALATED"
        return _build_escalation_result(
            tx_id, tx,
            "Reversal executed but verification failed. Immediate human review required.",
            AUDIT_EVENTS[tx_id],
        )

    log("VERIFICATION", "verify_resolution", "SUCCESS", "Resolution independently verified")

    # --- NOTIFICATION ---
    notification = send_customer_notification(tx_id, tx["amount"], action_id)
    log("NOTIFICATION", "send_notification", "SUCCESS", f"Customer notified via {notification['channel']}")

    # --- CLOSE ---
    tx["resolution_status"] = "RESOLVED"
    log("INVESTIGATION", "close", "SUCCESS", "Case closed. No support ticket required.")

    return ResolutionResult(
        transaction_id=tx_id,
        decision="AUTO_REVERSAL",
        authorized=True,
        action_id=action_id,
        verification_status="VERIFIED",
        notification_sent=True,
        support_case=None,
        resolution_status="RESOLVED",
        events=[AuditEvent(**e) for e in AUDIT_EVENTS[tx_id]],
        evidence=evidence,
        escalation_reason=None,
        suggested_resolution=None,
        investigation_narrative=narrative,
        agent_powered=api_key_present,
    )


def _build_escalation_result(tx_id, tx, reason, events_list):
    from backend.models import AuditEvent, Evidence, ResolutionResult
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
    suggested = _generate_suggested_resolution(evidence)
    case = create_support_case(tx_id, reason, evidence.model_dump(), suggested)
    tx["resolution_status"] = "ESCALATED"
    return ResolutionResult(
        transaction_id=tx_id,
        decision="HUMAN_ESCALATION",
        authorized=False,
        action_id=None,
        verification_status=None,
        notification_sent=False,
        support_case=case["case_id"],
        resolution_status="ESCALATED",
        events=[AuditEvent(**e) for e in events_list] if events_list else [],
        evidence=evidence,
        escalation_reason=reason,
        suggested_resolution=suggested,
        investigation_narrative="Investigation failed or was interrupted early.",
        agent_powered=False,
    )


def _generate_suggested_resolution(evidence: Evidence) -> str:
    if evidence.network == "UNKNOWN" or evidence.settlement == "UNKNOWN":
        return "Investigate network and settlement status before initiating any reversal. Contact payment network provider for transaction trace."
    if evidence.risk >= 0.30:
        return "High risk transaction. Verify customer identity and transaction authenticity before processing any refund."
    return "Manual investigation required. Review all four payment system records before taking financial action."
