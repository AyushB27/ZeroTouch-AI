from fastapi import FastAPI, HTTPException, Request, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from typing import Optional, List, Dict, Any
import json
import hashlib
import hmac
import os
import re
import secrets
from datetime import datetime, timezone
from uuid import uuid4

from dotenv import load_dotenv
load_dotenv()

from backend.database import (
    init_db,
    db_get_transaction,
    db_get_all_transactions,
    db_get_events,
    db_add_event,
    db_reset_all,
    db_log_webhook,
    db_mark_webhook_processed,
    db_update_transaction,
    db_add_message,
    db_get_messages,
    db_get_messages_for_transaction,
    db_get_case,
    db_get_case_by_tx,
    db_get_all_cases,
    case_id_for_tx,
    db_update_case_by_tx,
    db_get_customers,
    db_get_customer,
    db_get_tickets,
    db_create_ticket,
    db_get_ticket,
    db_get_ticket_by_case,
    db_update_ticket,
    db_get_refund,
    db_get_refund_by_idempotency,
    db_get_refund_by_transaction,
    db_get_refunds,
    db_create_refund,
    db_update_refund,
    db_get_workforce_tasks,
)
from backend.action_gateway import ActionGateway
from backend.orchestrator import run_resolution
from backend.rag import init_rag
from contextlib import asynccontextmanager
from backend.auth import SESSIONS, current_user, require_customer, require_employee, require_admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()       # Create tables + seed transactions + seed canonical cases
    init_rag()      # Load knowledge base + generate embeddings
    # Seed deterministic static sessions for all demo users so tokens survive backend restarts.
    # The frontend stores these tokens in localStorage and they stay valid forever in demo mode.
    for email, account in DEMO_USERS.items():
        # Use a deterministic stable token derived from the email (safe for demo only)
        import hashlib as _hl
        stable_token = _hl.sha256(f"zerotouch-demo-session-{email}".encode()).hexdigest()
        SESSIONS[stable_token] = {
            "role": account["role"],
            "name": account["name"],
            "id": account["id"],
            "email": email,
        }
    yield

app = FastAPI(title="ZeroTouch Payment Resolution Engine", version="2.0.0", lifespan=lifespan)


# Development identities. Sessions and roles are stored server-side.
DEMO_USERS = {
    "ayush@zerotouch.demo": {"password": "demo123", "role": "CUSTOMER", "name": "Ayush", "id": "cust-ayush", "email": "ayush@zerotouch.demo"},
    "ayush.admin@zerotouch.demo": {"password": "demo123", "role": "ADMIN", "name": "Ayush (Ops)", "id": "admin-ayush", "email": "ayush.admin@zerotouch.demo"},
    "vansh@zerotouch.demo": {"password": "demo123", "role": "CUSTOMER", "name": "Vansh", "id": "cust-vansh", "email": "vansh@zerotouch.demo"},
    "support@zerotouch.demo": {"password": "demo123", "role": "ADMIN", "name": "Support Agent", "id": "admin-support", "email": "support@zerotouch.demo"},
    "admin@zerotouch.demo": {"password": "demo123", "role": "ADMIN", "name": "Ops Admin", "id": "admin-ops", "email": "admin@zerotouch.demo"},
    "employee@zerotouch.demo": {"password": "demo123", "role": "EMPLOYEE", "name": "Aarav Sharma", "id": "emp-support", "email": "employee@zerotouch.demo"},
    "hr@zerotouch.demo": {"password": "demo123", "role": "EMPLOYEE", "name": "Kavita Rao", "id": "emp-hr", "email": "hr@zerotouch.demo"},
}


class LoginRequest(BaseModel):
    email: str
    password: str


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from backend.workforce_router import workforce_router
app.include_router(workforce_router, prefix="/api/workforce", tags=["Workforce"], dependencies=[Depends(require_employee)])

# ── Health ────────────────────────────────────────────────────────────────────


@app.get("/")
def health():
    return {
        "status": "ok",
        "service": "ZeroTouch Engine",
        "version": "2.0.0",
        "features": ["Canonical Case State", "Action Gateway", "LangGraph", "RAG", "NPCI Webhook", "Evaluation Suite"],
    }


@app.post("/api/auth/login")
def login(credentials: LoginRequest):
    import hashlib as _hl
    raw_email = credentials.email.strip().lower()
    account = DEMO_USERS.get(raw_email)

    if not account or not secrets.compare_digest(credentials.password, account["password"]):
        raise HTTPException(status_code=401, detail="Email or password is incorrect")

    # Return the stable deterministic token (pre-seeded at startup).
    # This survives backend restarts — the frontend localStorage token stays valid.
    stable_token = _hl.sha256(f"zerotouch-demo-session-{raw_email}".encode()).hexdigest()
    SESSIONS[stable_token] = {
        "role": account["role"],
        "name": account["name"],
        "id": account["id"],
        "email": account.get("email", raw_email),
    }
    return {"token": stable_token, "user": SESSIONS[stable_token]}


@app.get("/api/auth/me")
def who_am_i(user=Depends(current_user)):
    return user


@app.post("/api/auth/logout")
def logout(authorization: Optional[str] = Header(None)):
    token = authorization.removeprefix("Bearer ") if authorization else ""
    SESSIONS.pop(token, None)
    return {"status": "ok"}


# ── Transactions ──────────────────────────────────────────────────────────────

@app.get("/api/transactions")
def get_transactions(_user=Depends(require_admin)):
    return db_get_all_transactions()


@app.get("/api/transactions/{tx_id}")
def get_transaction(tx_id: str, _user=Depends(require_admin)):
    tx = db_get_transaction(tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail=f"Transaction {tx_id} not found")
    return tx


# ── Resolution ────────────────────────────────────────────────────────────────

@app.post("/api/resolutions/{tx_id}/run")
def resolve_transaction(tx_id: str, _user=Depends(require_admin)):
    tx = db_get_transaction(tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail=f"Transaction {tx_id} not found")
    try:
        result = run_resolution(tx_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/resolutions/{tx_id}/events")
def get_events(tx_id: str, _user=Depends(require_admin)):
    if not db_get_transaction(tx_id):
        raise HTTPException(status_code=404, detail=f"Transaction {tx_id} not found")
    return db_get_events(tx_id)


# ── HITL: Human-in-the-Loop Decision ─────────────────────────────────────────

class HumanDecision(BaseModel):
    action: str          # APPROVE_REFUND | REJECT | REQUEST_MORE_INFO
    agent_name: str = "Support Agent"
    notes: Optional[str] = None


class CustomerChatMessage(BaseModel):
    message: str


class RefundCreateRequest(BaseModel):
    transaction_id: str
    reason: str = "Customer requested refund"
    idempotency_key: Optional[str] = None


class TicketCreateRequest(BaseModel):
    category: str = "GENERAL"
    summary: str
    transaction_id: Optional[str] = None


@app.get("/api/customer/profile")
def customer_profile(user=Depends(require_customer)):
    stored = db_get_customer(user["id"])
    return {
        "id": user["id"],
        "name": stored["name"] if stored else user["name"],
        "email": stored["email"] if stored else user.get("email"),
        "tagline": "Your autonomous payment teammate"
    }


@app.get("/api/customer/transactions")
def customer_transactions(user=Depends(require_customer)):
    # Deliberately return only customer-facing fields, never internal risk scores or fraud flags.
    owned_tx_ids = {case["transaction_id"] for case in db_get_all_cases() if case["customer_id"] == user["id"]}
    return [{key: tx[key] for key in ("transaction_id", "amount", "currency", "bank_status", "network_status", "merchant_status", "settlement_status", "resolution_status", "workflow_type", "action_id")}
            for tx in db_get_all_transactions() if tx["transaction_id"] in owned_tx_ids]


@app.get("/api/customer/cases")
def customer_cases(_user=Depends(require_customer)):
    """Customer-facing case representation with strict internal data segregation."""
    cases = []
    for c in db_get_all_cases():
        if c["customer_id"] != _user["id"]:
            continue
        tx = db_get_transaction(c["transaction_id"])
        if not tx:
            continue
        # Show all investigated or non-pending cases, or all cases
        if tx["resolution_status"] == "PENDING" and not c.get("action_record"):
            continue
        cases.append({
            "case_id": c["case_id"],
            "transaction_id": c["transaction_id"],
            "amount": c["amount"],
            "status": c.get("customer_status") or tx["resolution_status"],
            "ops_status": tx["resolution_status"],
            "issue": _issue_for(tx),
            "action_id": tx.get("action_id"),
            "dynamic_message": c.get("dynamic_message") or tx.get("dynamic_message"),
            "timeline": _customer_timeline(db_get_events(tx["transaction_id"])),
        })
    return cases


@app.get("/api/customer/cases/{case_id}")
def customer_case(case_id: str, _user=Depends(require_customer)):
    case = db_get_case(case_id) or db_get_case_by_tx(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if case["customer_id"] != _user["id"]:
        raise HTTPException(status_code=404, detail="Case not found")
    tx = db_get_transaction(case["transaction_id"])
    return {
        "case_id": case["case_id"],
        "transaction_id": case["transaction_id"],
        "amount": case["amount"],
        "status": case.get("customer_status") or (tx["resolution_status"] if tx else "PENDING"),
        "issue": _issue_for(tx) if tx else "Payment support",
        "action_id": tx.get("action_id") if tx else None,
        "dynamic_message": case.get("dynamic_message"),
        "timeline": _customer_timeline(db_get_events(case["transaction_id"])),
    }


@app.get("/api/customer/messages")
def customer_messages(user=Depends(require_customer)):
    return db_get_messages(user["id"])


def _issue_for(tx):
    return {"W1": "Payment investigation", "W2": "Refund follow-up", "W3": "Merchant settlement review"}.get(tx.get("workflow_type"), "Payment support")


def _customer_timeline(events):
    """Expose progress labels, never raw internal audit messages, fraud risk scores, or policy rules."""
    labels = {
        "investigator_agent_start": "Payment check started",
        "load_transaction": "Payment identified",
        "narrative_complete": "Payment records checked",
        "evaluate_policy": "Resolution options reviewed",
        "initiate_reversal": "Reversal initiated",
        "human_approved_reversal": "Reversal approved by support",
        "verify_resolution": "Payment outcome verified",
        "customer_verified_notice": "Payment outcome verified across ledgers",
        "chase_bank_sla": "Bank follow-up requested",
        "offer_wallet_credit": "Refund return processed to Paytm Wallet",
        "generate_itemized_explanation": "Settlement breakdown prepared",
        "flag_compliance_hold": "Case sent for compliance review",
        "create_support_case": "Support team notified",
        "human_decision": "Support review updated",
        "send_dynamic_notification": "Notification sent",
        "send_notification": "Notification sent",
        "update_customer_case": "Case status updated",
    }
    return [
        {
            "timestamp": event.get("timestamp"),
            "label": labels[event["step"]],
            "status": "FAILED" if event.get("status") == "FAILED" else "DONE"
        }
        for event in events if event.get("step") in labels
    ]


@app.post("/api/chat")
def customer_chat(payload: CustomerChatMessage, user=Depends(require_customer)):
    message = payload.message.strip()
    if not message or len(message) > 1000:
        raise HTTPException(status_code=422, detail="Message must contain 1–1000 characters")

    owned_tx_ids = {case["transaction_id"] for case in db_get_all_cases() if case["customer_id"] == user["id"]}
    transactions = {tx["transaction_id"]: tx for tx in db_get_all_transactions() if tx["transaction_id"] in owned_tx_ids}
    explicit = re.search(r"\b(?:TX\d{4}|RF\d{3}|S\d{3})\b", message.upper())
    tx_id = explicit.group(0) if explicit and explicit.group(0) in transactions else None

    amount_match = re.search(r"(?:₹|rs\.?\s*)?([\d,]+(?:\.\d{1,2})?)", message.lower())
    if not tx_id and amount_match:
        requested_amount = float(amount_match.group(1).replace(",", ""))
        matches = [tid for tid, tx in transactions.items() if tx["amount"] == requested_amount]
        if "settlement" in message.lower() or "merchant" in message.lower():
            matches = [candidate for candidate in matches if transactions[candidate].get("workflow_type") == "W3"] or matches
        elif "refund" in message.lower():
            matches = [candidate for candidate in matches if transactions[candidate].get("workflow_type") == "W2"] or matches
        elif any(word in message.lower() for word in ("payment", "debited", "charged", "deducted", "upi")):
            matches = [candidate for candidate in matches if transactions[candidate].get("workflow_type") == "W1"] or matches
        if len(matches) == 1:
            tx_id = matches[0]

    if not tx_id and (re.search(r"9[, ]?650|10[, ]?000", message.lower()) or any(word in message.lower() for word in ("settlement", "short settlement"))):
        tx_id = "S301"
    elif not tx_id and any(word in message.lower() for word in ("bounced", "invalid account", "wallet")):
        tx_id = "RF204"
    elif not tx_id and "refund" in message.lower() and any(word in message.lower() for word in ("late", "missing", "arrived", "where")):
        tx_id = "RF202"
    elif not tx_id and any(word in message.lower() for word in ("human", "agent", "support person", "high risk")):
        tx_id = "TX9342"

    if tx_id is None:
        previous_case_tx = next((item.get("transaction_id") for item in reversed(db_get_messages(user["id"]))
                                 if item.get("transaction_id") in transactions), None)
        if previous_case_tx and transactions[previous_case_tx]["resolution_status"] in ("PENDING", "ESCALATED"):
            tx_id = previous_case_tx

    if tx_id is None:
        db_add_message(user["id"], "customer", message)
        reply = "I can check that for you. Which recent payment are you asking about?"
        db_add_message(user["id"], "assistant", reply)
        options = [{key: tx[key] for key in ("transaction_id", "amount", "currency", "resolution_status", "workflow_type")}
                   for tx in transactions.values()][:6]
        return {"needs_selection": True, "reply": reply, "options": options}

    db_add_message(user["id"], "customer", message, tx_id)
    tx = transactions[tx_id]
    cid = case_id_for_tx(tx_id)

    if tx["resolution_status"] == "PENDING":
        result = run_resolution(tx_id)
        events = [event.model_dump() for event in result.events]
        decision = result.decision
        action_id = result.action_id
        status = result.resolution_status
        if decision == "AUTO_REVERSAL" and status == "RESOLVED" and action_id:
            refund_key = f"{user['id']}:{tx_id}:refund-v1"
            if not db_get_refund_by_idempotency(refund_key):
                now = datetime.now(timezone.utc).isoformat()
                db_create_refund({
                    "refund_id": f"RFD-{uuid4().hex[:10].upper()}",
                    "idempotency_key": refund_key,
                    "transaction_id": tx_id,
                    "customer_id": user["id"],
                    "amount": tx["amount"],
                    "reason": "Automatic reversal for failed payment",
                    "status": "VERIFIED", "action_ref": action_id,
                    "created_at": now, "completed_at": now,
                })
        if result.dynamic_message:
            reply = result.dynamic_message
        elif decision == "AUTO_REVERSAL":
            reply = f"I investigated {tx_id} across the bank, payment network, merchant ledger and settlement. The bank confirmed your ₹{tx['amount']:,.0f} debit, but the merchant was not credited. The policy engine approved an automatic reversal, and I verified it successfully. Reference: {action_id}."
        elif status == "ESCALATED":
            reply = f"I checked {tx_id} and found a high-risk or unresolved payment state. ZeroTouch has paused any automatic money movement and sent the evidence to our support team for human review. Case {cid} is open."
        elif decision == "SLA_CHASE":
            reply = f"I confirmed your refund is past the bank's service window and opened a follow-up with the bank. Reference: {action_id}; expected update within 24 hours."
        elif decision == "WALLET_CREDIT_OFFER":
            reply = f"The refund return was rejected because the destination account is invalid. The demo workflow placed ₹{tx['amount']:,.0f} in the wallet resolution flow and recorded reference {action_id}."
        elif decision == "ITEMIZED_EXPLANATION":
            if tx_id == "S301":
                reply = f"I reconciled settlement {tx_id}: ₹10,000 gross, less ₹300 platform fee and ₹50 GST, leaves ₹9,650 net. I've sent the itemized explanation. Reference: {action_id}."
            else:
                reply = f"I reconciled settlement {tx_id}. The ₹{tx['amount']:,.0f} gross amount includes a ₹1,000 platform fee, leaving ₹49,000 net. Reference: {action_id}."
        else:
            reply = f"I checked {tx_id} across the payment systems. The records are consistent, so no additional action was needed."
    else:
        events = db_get_events(tx_id)
        status = tx["resolution_status"]
        action_id = tx.get("action_id")
        if tx.get("dynamic_message"):
            reply = tx["dynamic_message"]
        elif status == "ESCALATED":
            reply = f"Case {cid} is awaiting human review. No automatic refund has been issued."
        else:
            reply = f"Case {cid} is already {status.lower().replace('_', ' ')}. {('Action reference: ' + action_id + '.') if action_id else 'No further action is required.'}"

    db_add_message(user["id"], "assistant", reply, tx_id)
    if status == "ESCALATED" and not db_get_ticket_by_case(cid):
        now = datetime.now(timezone.utc).isoformat()
        db_create_ticket({
            "ticket_id": f"TKT-{uuid4().hex[:10].upper()}", "case_id": cid,
            "customer_id": user["id"], "category": _issue_for(tx).upper().replace(" ", "_"),
            "priority": "HIGH", "status": "OPEN", "assigned_team": "Payment Support",
            "summary": message, "created_at": now, "resolved_at": None,
        })
    return {
        "transaction_id": tx_id,
        "case_id": cid,
        "status": status,
        "reply": reply,
        # Internal ledger evidence, risk scores, and policy rules remain segregated in Ops
        "activity": _customer_timeline(events),
    }


# ── Canonical Cases & Support Ops APIs ────────────────────────────────────────

@app.get("/api/cases")
@app.get("/api/ops/cases")
def ops_cases(_user=Depends(require_admin)):
    """Return operational views over canonical cases with full evidence and audit trails."""
    all_cases = db_get_all_cases()
    result = []
    for c in all_cases:
        tx = db_get_transaction(c["transaction_id"])
        if not tx:
            continue
        ev_matrix = json.loads(c["evidence_matrix"]) if c.get("evidence_matrix") else None
        risk_profile = json.loads(c["risk_assessment"]) if c.get("risk_assessment") else None
        policy_dec = json.loads(c["policy_decision"]) if c.get("policy_decision") else None
        action_rec = json.loads(c["action_record"]) if c.get("action_record") else None

        result.append({
            "case_id": c["case_id"],
            "transaction_id": c["transaction_id"],
            "transaction": tx,
            "classification": c.get("classification", "UNKNOWN_PAYMENT_STATE"),
            "workflow_type": c.get("workflow_type", tx.get("workflow_type", "W1")),
            "customer_status": c.get("customer_status", "INVESTIGATING"),
            "ops_status": tx.get("resolution_status", "PENDING"),
            "evidence_matrix": ev_matrix,
            "risk_assessment": risk_profile,
            "policy_decision": policy_dec,
            "action_record": action_rec,
            "timeline": db_get_events(c["transaction_id"]),
            "conversation": db_get_messages_for_transaction(c["transaction_id"]),
        })
    return result


@app.get("/api/cases/{identifier}")
@app.get("/api/ops/cases/{identifier}")
def ops_case(identifier: str, _user=Depends(require_admin)):
    case = db_get_case(identifier) or db_get_case_by_tx(identifier)
    tx_id = case["transaction_id"] if case else identifier
    tx = db_get_transaction(tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail=f"Case / Transaction {identifier} not found")

    cid = case["case_id"] if case else case_id_for_tx(tx_id)
    ev_matrix = json.loads(case["evidence_matrix"]) if case and case.get("evidence_matrix") else None
    risk_profile = json.loads(case["risk_assessment"]) if case and case.get("risk_assessment") else None
    policy_dec = json.loads(case["policy_decision"]) if case and case.get("policy_decision") else None
    action_rec = json.loads(case["action_record"]) if case and case.get("action_record") else None

    return {
        "case_id": cid,
        "transaction_id": tx_id,
        "transaction": tx,
        "classification": case.get("classification") if case else "UNKNOWN_PAYMENT_STATE",
        "evidence_matrix": ev_matrix,
        "risk_assessment": risk_profile,
        "policy_decision": policy_dec,
        "action_record": action_rec,
        "timeline": db_get_events(tx_id),
        "conversation": db_get_messages_for_transaction(tx_id),
    }


@app.post("/api/resolutions/{tx_id}/human-decision")
def human_decision(tx_id: str, decision: HumanDecision, _user=Depends(require_admin)):
    tx = db_get_transaction(tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail=f"Transaction {tx_id} not found")
    if tx["resolution_status"] != "ESCALATED":
        raise HTTPException(
            status_code=400,
            detail=f"Transaction {tx_id} is not in ESCALATED state (current: {tx['resolution_status']})"
        )

    cid = case_id_for_tx(tx_id)
    action_map = {
        "APPROVE_REFUND":    ("RESOLVED",  "Refund manually approved by human agent."),
        "REJECT":            ("NO_ACTION", "Case rejected by human agent. No refund issued."),
        "REQUEST_MORE_INFO": ("ESCALATED", "Agent requested more information from customer."),
    }
    if decision.action not in action_map:
        raise HTTPException(status_code=400, detail=f"Unknown action: {decision.action}")

    new_status, log_msg = action_map[decision.action]

    if decision.action == "APPROVE_REFUND":
        # Route through ActionGateway with idempotency guarantee
        action_result = ActionGateway.execute_action(
            tx_id=tx_id,
            action_type="HUMAN_APPROVED_REVERSAL",
            payload={"amount": tx["amount"]},
            policy_version="2.0",
            rule_id="RULE_HITL_APPROVED_01",
            actor=f"Human Agent: {decision.agent_name}",
        )
        if not action_result.get("verified"):
            raise HTTPException(status_code=409, detail="Approved action could not be verified across core ledgers")

        from backend.tools.notifications import send_customer_notification
        send_customer_notification(tx_id, tx["amount"], action_result["action_id"])
        db_add_event(
            tx_id, "NOTIFICATION", "send_notification", "SUCCESS",
            "Customer notified of human-approved reversal",
            visibility="CUSTOMER", actor="ZeroTouch"
        )
        db_update_case_by_tx(
            tx_id,
            customer_status="RESOLVED",
            ops_status="RESOLVED",
            assigned_agent=decision.agent_name,
            human_review_notes=decision.notes or "Manually approved after supervisory verification.",
        )
    elif decision.action == "REJECT":
        db_update_transaction(tx_id, resolution_status=new_status)
        db_update_case_by_tx(
            tx_id,
            customer_status="NO_ACTION",
            ops_status="NO_ACTION",
            assigned_agent=decision.agent_name,
            human_review_notes=decision.notes or "Manual rejection by human agent.",
        )
    else:  # REQUEST_MORE_INFO
        db_update_case_by_tx(
            tx_id,
            customer_status="HUMAN_REVIEW",
            ops_status="ESCALATED",
            assigned_agent=decision.agent_name,
            human_review_notes=decision.notes or "Requested further documentation from user.",
        )

    note_text = f" Note: {decision.notes}" if decision.notes else ""
    db_add_event(
        tx_id, "ESCALATION", "human_decision", "SUCCESS",
        f"[{decision.agent_name}] {log_msg}{note_text}",
        visibility="INTERNAL", actor=decision.agent_name
    )

    customer_updates = {
        "APPROVE_REFUND": f"A support agent reviewed case {cid} and approved your reversal. The action was verified successfully.",
        "REJECT": f"A support agent reviewed case {cid}. No refund was issued; the case is closed without a payment action.",
        "REQUEST_MORE_INFO": f"A support agent is reviewing case {cid} and needs more information before deciding. Please reply here with any details that may help.",
    }
    case = db_get_case_by_tx(tx_id)
    customer_id = case["customer_id"] if case else "cust-ayush"
    db_add_message(customer_id, "assistant", customer_updates[decision.action], tx_id)
    ticket = db_get_ticket_by_case(case_id_for_tx(tx_id))
    if ticket and decision.action in ("APPROVE_REFUND", "REJECT"):
        db_update_ticket(ticket["ticket_id"], status="RESOLVED", resolved_at=datetime.now(timezone.utc).isoformat())

    db_add_event(
        tx_id, "NOTIFICATION", "update_customer_case", "SUCCESS",
        "Customer conversation updated with the human review outcome",
        visibility="CUSTOMER", actor="ZeroTouch"
    )

    return {
        "status": "ok",
        "case_id": cid,
        "transaction_id": tx_id,
        "action": decision.action,
        "new_status": new_status,
        "agent": decision.agent_name,
    }


@app.get("/api/admin/dashboard")
def admin_dashboard(_user=Depends(require_admin)):
    rows = db_get_all_transactions()
    cases = db_get_all_cases()
    return {
        "total_cases": len(cases),
        "autonomous_resolutions": sum(c.get("ops_status") == "RESOLVED" for c in cases),
        "human_escalations": sum(c.get("ops_status") == "ESCALATED" for c in cases),
        "active_investigations": sum(c.get("ops_status") == "PENDING" for c in cases),
        "refunds_processed": sum(bool(row.get("action_id")) and row["workflow_type"] == "W1" for row in rows),
        "cases": cases,
        "transactions": rows,
    }


@app.get("/api/admin/audit-logs")
def admin_audit_logs(_user=Depends(require_admin)):
    logs = [event for tx in db_get_all_transactions() for event in db_get_events(tx["transaction_id"])]
    return sorted(logs, key=lambda event: event["timestamp"], reverse=True)


@app.get("/api/admin/review-queue")
def admin_review_queue(_user=Depends(require_admin)):
    cases = db_get_all_cases()
    escalated_cases = []
    for c in cases:
        if c.get("ops_status") == "ESCALATED":
            tx = db_get_transaction(c["transaction_id"])
            escalated_cases.append({
                **tx,
                "case_id": c["case_id"],
                "classification": c.get("classification"),
                "human_review_notes": c.get("human_review_notes"),
                "timeline": db_get_events(c["transaction_id"]),
            })
    return escalated_cases


@app.get("/api/admin/customers")
def admin_customers(_user=Depends(require_admin)):
    return db_get_customers()


class AccessDecisionRequest(BaseModel):
    decision: str
    notes: str = ""


class EmployeeAssistantRequest(BaseModel):
    message: str
    department: str = "all"
    conversation_id: Optional[str] = None


@app.get("/api/admin/enterprise-overview")
def admin_enterprise_overview(_user=Depends(require_admin)):
    from sqlalchemy import select, func
    from backend.database import (
        engine, customers_table, employees_table, departments_table,
        conversations_table, tasks_table, support_tickets_table,
        transactions_table, refunds_table, knowledge_documents_table,
        expenses_table, it_tickets_table, access_requests_table,
        onboarding_plans_table, training_assignments_table, audit_logs_table,
        sales_leads_table, campaigns_table
    )
    tables = {
        "customers": customers_table, "employees": employees_table, "departments": departments_table,
        "conversations": conversations_table, "tasks": tasks_table, "tickets": support_tickets_table,
        "transactions": transactions_table, "refunds": refunds_table, "knowledge": knowledge_documents_table,
        "expenses": expenses_table, "it_requests": it_tickets_table, "access_requests": access_requests_table,
        "onboarding": onboarding_plans_table, "training": training_assignments_table, "audit": audit_logs_table,
        "leads": sales_leads_table, "campaigns": campaigns_table,
    }
    with engine.connect() as conn:
        counts = {key: conn.execute(select(func.count()).select_from(table)).scalar_one()
                  for key, table in tables.items()}
        rows = {}
        for key, table in tables.items():
            ordering = table.c.timestamp if key == "audit" else table.c.updated_at if key == "tasks" else table.c.created_at if "created_at" in table.c else None
            query = table.select().order_by(ordering.desc()).limit(100) if ordering is not None else table.select().limit(100)
            rows[key] = [dict(row) for row in conn.execute(query).mappings().all()]
    for row in rows["tasks"]:
        if row.get("payload"):
            try: row.update(json.loads(row["payload"]))
            except (TypeError, json.JSONDecodeError): pass
    agent_names = ["Supervisor Agent", "Finance Agent", "HR Agent", "IT Agent", "Customer Support Agent",
                   "Analytics Agent", "Sales Agent", "Marketing Agent", "Operations Agent", "Knowledge Agent", "Escalation Agent"]
    return {"metrics": counts, "records": rows,
            "agents": [{"name": name, "status": "READY", "mode": "Registered tools"} for name in agent_names],
            "settings": {"grok_enabled": bool(os.getenv("XAI_API_KEY")), "grok_model": os.getenv("XAI_MODEL", "grok-4.7"),
                         "database": "PostgreSQL" if os.getenv("DATABASE_URL", "").startswith("postgres") else "SQLite"}}


@app.post("/api/admin/access-requests/{request_id}/decision")
def admin_access_request_decision(request_id: str, payload: AccessDecisionRequest, user=Depends(require_admin)):
    from backend.database import engine, access_requests_table, audit_logs_table
    decision = payload.decision.strip().upper()
    if decision not in ("APPROVE", "REJECT"):
        raise HTTPException(status_code=422, detail="Decision must be APPROVE or REJECT")
    with engine.begin() as conn:
        row = conn.execute(access_requests_table.select().where(access_requests_table.c.request_id == request_id)).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Access request not found")
        if row["status"] != "PENDING_APPROVAL":
            raise HTTPException(status_code=409, detail="Access request has already been reviewed")
        status = "APPROVED" if decision == "APPROVE" else "REJECTED"
        request_data = json.loads(row["payload"])
        request_data.update({"status": status, "reviewed_by": user["name"], "review_notes": payload.notes[:500],
                             "reviewed_at": datetime.now(timezone.utc).isoformat()})
        conn.execute(access_requests_table.update().where(access_requests_table.c.request_id == request_id).values(
            status=status, payload=json.dumps(request_data)))
        conn.execute(audit_logs_table.insert().values(audit_id=f"AUD-{uuid4().hex[:14].upper()}",
            timestamp=request_data["reviewed_at"], user_id=user["id"], agent="Admin Reviewer", tool="access_request_decision",
            action=decision, entity_type="access_request", entity_id=request_id, status="SUCCESS",
            result_summary=f"{status} least-privilege access request for {row['system_name']}"))
    return request_data


@app.post("/api/assistant")
async def employee_assistant(payload: EmployeeAssistantRequest, user=Depends(require_employee)):
    from backend.enterprise_assistant import handle_employee_message
    return await handle_employee_message(user, payload.message, payload.department, payload.conversation_id)


@app.get("/api/assistant/conversations/{conversation_id}")
def employee_assistant_conversation(conversation_id: str, user=Depends(require_employee)):
    from backend.enterprise_assistant import get_conversation
    return get_conversation(user, conversation_id)


@app.post("/api/refunds/create")
def create_refund(payload: RefundCreateRequest, user=Depends(require_customer)):
    tx = db_get_transaction(payload.transaction_id)
    case = db_get_case_by_tx(payload.transaction_id)
    if not tx or not case or case["customer_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Transaction not found")

    idem_key = (payload.idempotency_key or f"{user['id']}:{payload.transaction_id}:refund-v1").strip()
    if not idem_key or len(idem_key) > 128:
        raise HTTPException(status_code=422, detail="Idempotency key must contain 1–128 characters")
    prior = db_get_refund_by_idempotency(idem_key) or db_get_refund_by_transaction(payload.transaction_id)
    if prior:
        if prior["customer_id"] != user["id"] or prior["transaction_id"] != payload.transaction_id:
            raise HTTPException(status_code=409, detail="Idempotency key is already associated with another refund")
        return prior

    eligible = (
        tx["bank_status"] == "DEBITED" and tx["network_status"] == "SUCCESS"
        and tx["merchant_status"] == "NOT_CREDITED" and tx["settlement_status"] == "NOT_FOUND"
        and tx["risk_score"] < 0.30 and tx["amount"] <= 10000 and not tx["previous_refund"]
    )
    if not eligible:
        raise HTTPException(status_code=409, detail="This transaction is not eligible for an automatic demo refund")

    reason = payload.reason.strip()
    if not reason or len(reason) > 500:
        raise HTTPException(status_code=422, detail="Refund reason must contain 1–500 characters")
    now = datetime.now(timezone.utc).isoformat()
    refund = {
        "refund_id": f"RFD-{uuid4().hex[:10].upper()}", "idempotency_key": idem_key,
        "transaction_id": payload.transaction_id, "customer_id": user["id"],
        "amount": tx["amount"], "reason": reason, "status": "PROCESSING",
        "action_ref": None, "created_at": now, "completed_at": None,
    }
    try:
        db_create_refund(refund)
    except IntegrityError:
        # A concurrent repeat may have won the unique idempotency/transaction race.
        prior = db_get_refund_by_idempotency(idem_key) or db_get_refund_by_transaction(payload.transaction_id)
        if prior and prior["customer_id"] == user["id"]:
            return prior
        raise HTTPException(status_code=409, detail="A refund request for this transaction already exists")
    try:
        result = ActionGateway.execute_action(
            payload.transaction_id, "AUTO_REVERSAL", {"amount": tx["amount"]},
            rule_id="RULE_W1_AUTO_REVERSAL_01", actor=f"Customer {user['id']} via Refund Service",
        )
    except Exception as exc:
        db_update_refund(refund["refund_id"], status="FAILED")
        raise HTTPException(status_code=503, detail="The refund service could not complete this request") from exc
    if not result.get("verified"):
        db_update_refund(refund["refund_id"], status="FAILED", action_ref=result.get("action_id"))
        raise HTTPException(status_code=409, detail="The reversal could not be verified; the case needs support review")
    completed = datetime.now(timezone.utc).isoformat()
    db_update_refund(refund["refund_id"], status="VERIFIED", action_ref=result["action_id"], completed_at=completed)
    return {**refund, "status": "VERIFIED", "action_ref": result["action_id"], "completed_at": completed}


@app.get("/api/refunds/{refund_id}")
def get_refund(refund_id: str, user=Depends(current_user)):
    refund = db_get_refund(refund_id)
    if not refund or (user["role"] == "CUSTOMER" and refund["customer_id"] != user["id"]):
        raise HTTPException(status_code=404, detail="Refund not found")
    return refund


@app.get("/api/admin/refunds")
def admin_refunds(_user=Depends(require_admin)):
    return db_get_refunds()


@app.get("/api/customer/refunds")
def customer_refunds(user=Depends(require_customer)):
    return db_get_refunds(user["id"])


@app.get("/api/tickets")
def list_tickets(user=Depends(current_user)):
    return db_get_tickets(user["id"]) if user["role"] == "CUSTOMER" else db_get_tickets()


@app.post("/api/tickets")
def create_ticket(payload: TicketCreateRequest, user=Depends(require_customer)):
    case = None
    if payload.transaction_id:
        case = db_get_case_by_tx(payload.transaction_id)
        if not case or case["customer_id"] != user["id"]:
            raise HTTPException(status_code=404, detail="Transaction not found")
    summary = payload.summary.strip()
    if not summary:
        raise HTTPException(status_code=422, detail="Ticket summary is required")
    now = datetime.now(timezone.utc).isoformat()
    ticket = db_create_ticket({
        "ticket_id": f"TKT-{uuid4().hex[:10].upper()}",
        "case_id": case["case_id"] if case else None, "customer_id": user["id"],
        "category": payload.category.strip().upper()[:50], "priority": "NORMAL", "status": "OPEN",
        "assigned_team": "Customer Support", "summary": summary[:1000],
        "created_at": now, "resolved_at": None,
    })
    if case:
        db_add_event(case["transaction_id"], "ESCALATION", "support_ticket_created", "SUCCESS",
                     f"Support request {ticket['ticket_id']} created", visibility="INTERNAL", actor=user["name"])
    return ticket


@app.get("/api/admin/evaluation")
def run_evaluation(_user=Depends(require_admin)):
    """Run automated scenario matrix and failure injection test suite."""
    from backend.evaluation import run_full_evaluation
    try:
        report = run_full_evaluation()
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class NPCIWebhookPayload(BaseModel):
    transaction_reference: str           # e.g. "TX9281"
    utr: str                             # Unique Transaction Reference
    status: str                          # e.g. "FAILED", "SUCCESS", "PENDING"
    amount: float
    bank_rrn: Optional[str] = None       # Bank Reference Number
    npci_txn_id: Optional[str] = None
    timestamp: str
    source: str = "NPCI"                 # NPCI | BANK | MERCHANT


WEBHOOK_SECRET = os.getenv("NPCI_WEBHOOK_SECRET", "zerotouch-dev-secret")


def _verify_signature(payload_bytes: bytes, signature: str) -> bool:
    """HMAC-SHA256 signature verification — matches what NPCI/banks use in production."""
    expected = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@app.post("/api/webhook/npci")
async def npci_webhook(
    request: Request,
    x_zerotouch_signature: Optional[str] = Header(None),
):
    body = await request.body()

    if x_zerotouch_signature:
        if not _verify_signature(body, x_zerotouch_signature):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
    elif WEBHOOK_SECRET != "zerotouch-dev-secret":
        raise HTTPException(status_code=401, detail="Webhook signature required")

    try:
        payload = NPCIWebhookPayload(**json.loads(body))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid payload: {e}")

    tx_ref = payload.transaction_reference

    # Log raw webhook
    db_log_webhook(tx_ref, body.decode())

    tx = db_get_transaction(tx_ref)
    if not tx:
        return {
            "status": "ignored",
            "reason": f"Transaction {tx_ref} not found in ZeroTouch system",
        }

    status_map = {
        "FAILED":   {"network_status": "FAILED"},
        "SUCCESS":  {"network_status": "SUCCESS"},
        "PENDING":  {"network_status": "UNKNOWN"},
        "TIMEOUT":  {"network_status": "UNKNOWN"},
        "REVERSED": {"network_status": "SUCCESS", "settlement_status": "REVERSED"},
    }
    update = status_map.get(payload.status.upper(), {})
    if update:
        db_update_transaction(tx_ref, **update)

    db_mark_webhook_processed(tx_ref)

    tx_fresh = db_get_transaction(tx_ref)
    auto_triggered = False
    resolution_result = None
    if tx_fresh and tx_fresh["resolution_status"] == "PENDING":
        try:
            resolution_result = run_resolution(tx_ref)
            auto_triggered = True
        except Exception:
            pass

    return {
        "status": "processed",
        "case_id": case_id_for_tx(tx_ref),
        "transaction_reference": tx_ref,
        "npci_status": payload.status,
        "internal_update": update,
        "auto_triggered_resolution": auto_triggered,
        "resolution_decision": resolution_result.decision if resolution_result else None,
        "source": payload.source,
    }


# ── Reset ─────────────────────────────────────────────────────────────────────

@app.post("/api/reset")
def reset_demo(_user=Depends(require_admin)):
    db_reset_all()
    return {"status": "reset", "message": "All transactions and canonical cases restored to original state"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
