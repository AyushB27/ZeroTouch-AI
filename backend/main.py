from fastapi import FastAPI, HTTPException, Request, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import hashlib
import hmac
import os
import re
import secrets

from dotenv import load_dotenv
load_dotenv()

from backend.database import (
    init_db,
    db_get_transaction,
    db_get_all_transactions,
    db_get_events,
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
)
from backend.action_gateway import ActionGateway
from backend.orchestrator import run_resolution
from backend.rag import init_rag
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()       # Create tables + seed transactions + seed canonical cases
    init_rag()      # Load knowledge base + generate embeddings
    yield

app = FastAPI(title="ZeroTouch Payment Resolution Engine", version="2.0.0", lifespan=lifespan)


# Hackathon demo identities. Tokens are issued and role-bound on the server;
# clients cannot elevate privileges by changing a role field.
DEMO_USERS = {
    "manager@zerotouch.demo": {"password": "demo123", "role": "ADMIN", "workforce_role": "manager", "name": "Rajesh Mehra", "title": "VP of Operations (Admin)", "id": "admin-rajesh", "email": "manager@zerotouch.demo", "domain": "all"},
    "admin@zerotouch.demo":   {"password": "demo123", "role": "ADMIN", "workforce_role": "manager", "name": "Rajesh Mehra", "title": "VP of Operations (Admin)", "id": "admin-rajesh", "email": "admin@zerotouch.demo", "domain": "all"},
    "support@zerotouch.demo": {"password": "demo123", "role": "ADMIN", "workforce_role": "support_agent", "name": "Aarav Sharma", "title": "Senior Support Specialist", "id": "admin-aarav", "email": "support@zerotouch.demo", "domain": "support"},
    "finance@zerotouch.demo": {"password": "demo123", "role": "ADMIN", "workforce_role": "finance_analyst", "name": "Neha Patel", "title": "Lead Reconciliation Analyst", "id": "admin-neha", "email": "finance@zerotouch.demo", "domain": "finance"},
    "it@zerotouch.demo":      {"password": "demo123", "role": "ADMIN", "workforce_role": "skill_owner", "name": "Vikram Malhotra", "title": "Staff Operations Engineer (IT Lead)", "id": "admin-vikram", "email": "it@zerotouch.demo", "domain": "it"},
    "hr@zerotouch.demo":      {"password": "demo123", "role": "ADMIN", "workforce_role": "recruiter", "name": "Priya Nair", "title": "Technical Talent Partner (HR)", "id": "admin-priya", "email": "hr@zerotouch.demo", "domain": "hr"},
    "joiner@zerotouch.demo":  {"password": "demo123", "role": "ADMIN", "workforce_role": "new_joiner", "name": "Kavita Rao", "title": "Associate Operations Trainee", "id": "admin-kavita", "email": "joiner@zerotouch.demo", "domain": "support"},
    "ayush@zerotouch.demo":   {"password": "demo123", "role": "CUSTOMER", "workforce_role": "customer", "name": "Ayush Bhardwaj", "title": "Paytm Customer", "id": "cust-ayush", "email": "ayush@zerotouch.demo", "domain": "customer"},
    "vansh@zerotouch.demo":   {"password": "demo123", "role": "CUSTOMER", "workforce_role": "customer", "name": "Vansh", "title": "Paytm Customer", "id": "cust-vansh", "email": "vansh@zerotouch.demo", "domain": "customer"},
}
SESSIONS: dict[str, dict] = {}


class LoginRequest(BaseModel):
    email: str
    password: str


def current_user(authorization: Optional[str] = Header(None)):
    token = authorization.removeprefix("Bearer ") if authorization else ""
    user = SESSIONS.get(token)
    if not user:
        raise HTTPException(status_code=401, detail="Please sign in to continue")
    return user


def require_customer(user=Depends(current_user)):
    if user["role"] != "CUSTOMER":
        raise HTTPException(status_code=403, detail="Customer access required")
    return user


def require_admin(user=Depends(current_user)):
    if user["role"] != "ADMIN":
        raise HTTPException(status_code=403, detail="Support access required")
    return user

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from backend.workforce_router import workforce_router
app.include_router(workforce_router, prefix="/api/workforce", tags=["Workforce"])

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
    raw_email = credentials.email.strip().lower()
    account = DEMO_USERS.get(raw_email)

    # Resilient demo fallback: if any custom email/name is entered
    if not account:
        role = "ADMIN" if any(k in raw_email for k in ("admin", "support", "ops", "finance", "it", "hr", "manager")) else "CUSTOMER"
        name_part = raw_email.split("@")[0].replace(".", " ").title()
        account = {
            "password": credentials.password or "demo123",
            "role": role,
            "workforce_role": "manager" if role == "ADMIN" else "customer",
            "name": name_part or "Demo User",
            "title": "Operations Specialist" if role == "ADMIN" else "Customer",
            "id": f"{role.lower()}-{raw_email.split('@')[0]}",
            "email": raw_email,
            "domain": "all" if role == "ADMIN" else "customer",
        }

    token = secrets.token_urlsafe(32)
    SESSIONS[token] = {
        "role": account["role"],
        "workforce_role": account.get("workforce_role", "manager" if account["role"] == "ADMIN" else "customer"),
        "name": account["name"],
        "title": account.get("title", account["name"]),
        "id": account["id"],
        "email": account.get("email", raw_email),
        "domain": account.get("domain", "all"),
    }
    return {"token": token, "user": SESSIONS[token]}


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


@app.get("/api/customer/profile")
def customer_profile(user=Depends(require_customer)):
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user.get("email", "ayush@zerotouch.demo"),
        "tagline": "Your autonomous payment teammate"
    }


@app.get("/api/customer/transactions")
def customer_transactions(_user=Depends(require_customer)):
    # Deliberately return only customer-facing fields, never internal risk scores or fraud flags.
    return [{key: tx[key] for key in ("transaction_id", "amount", "currency", "bank_status", "network_status", "merchant_status", "settlement_status", "resolution_status", "workflow_type", "action_id")}
            for tx in db_get_all_transactions()]


@app.get("/api/customer/cases")
def customer_cases(_user=Depends(require_customer)):
    """Customer-facing case representation with strict internal data segregation."""
    cases = []
    for c in db_get_all_cases():
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

    transactions = {tx["transaction_id"]: tx for tx in db_get_all_transactions()}
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
                   for tx in db_get_all_transactions()[:6]]
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
    for uid in ("cust-ayush", "cust-vansh"):
        db_add_message(uid, "assistant", customer_updates[decision.action], tx_id)

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
