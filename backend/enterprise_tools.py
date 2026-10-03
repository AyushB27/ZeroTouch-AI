"""Allowlisted business tools used by ZeroTouch and Grok function calling."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from uuid import uuid4
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select

from backend.action_gateway import ActionGateway
from backend.database import (
    engine, customers_table, employees_table, transactions_table, refunds_table,
    support_tickets_table, expenses_table, leave_requests_table, it_tickets_table,
    access_requests_table, onboarding_plans_table, training_modules_table,
    training_assignments_table, knowledge_documents_table, tasks_table,
    audit_logs_table, cases_table, case_id_for_tx, db_get_case_by_tx, db_get_refund,
    db_get_refund_by_idempotency, db_get_refund_by_transaction, db_add_event,
    sales_leads_table, campaigns_table,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _required_text(value: Any, name: str, limit: int = 160) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
        raise HTTPException(status_code=422, detail=f"{name} must contain 1–{limit} characters")
    return value.strip()


def _get_employee(employee_id: str) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(employees_table.select().where(employees_table.c.employee_id == employee_id)).mappings().first()
    return dict(row) if row else None


def _employee_search(query: str) -> list[dict]:
    phrase = f"%{_required_text(query, 'Query', 100).lower()}%"
    with engine.connect() as conn:
        rows = conn.execute(employees_table.select().where(
            employees_table.c.name.ilike(phrase) | employees_table.c.email.ilike(phrase)
        ).order_by(employees_table.c.name).limit(10)).mappings().all()
    return [{"employee_id": row["employee_id"], "name": row["name"], "email": row["email"],
             "department_id": row["department_id"], "role": row["role"], "status": row["status"]} for row in rows]


def record_audit(context: dict, agent: str, tool: str, action: str, entity_type: str,
                 entity_id: str | None, status: str, summary: str) -> None:
    with engine.begin() as conn:
        conn.execute(audit_logs_table.insert().values(
            audit_id=f"AUD-{uuid4().hex[:14].upper()}", timestamp=_now(),
            user_id=context.get("id", "system"), agent=agent, tool=tool,
            action=action, entity_type=entity_type, entity_id=entity_id,
            status=status, result_summary=str(summary)[:500],
        ))


def _tool_get_customer(args: dict, context: dict) -> dict:
    identifier = _required_text(args.get("customer_id") or args.get("email"), "Customer identifier", 255)
    column = customers_table.c.email if "@" in identifier else customers_table.c.customer_id
    with engine.connect() as conn:
        row = conn.execute(customers_table.select().where(column == identifier.lower() if column.name == "email" else column == identifier)).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Customer not found")
    if context.get("role") == "CUSTOMER" and row["customer_id"] != context.get("id"):
        raise HTTPException(status_code=404, detail="Customer not found")
    return {key: row[key] for key in ("customer_id", "name", "email", "phone", "account_status", "verification_status")}


def _tool_get_employee(args: dict, _context: dict) -> dict:
    identifier = _required_text(args.get("employee_id") or args.get("query"), "Employee identifier", 120)
    rows = _employee_search(identifier)
    if not rows:
        raise HTTPException(status_code=404, detail="Employee not found")
    exact = next((row for row in rows if row["employee_id"] == identifier or row["email"].lower() == identifier.lower()), rows[0])
    return exact


def _tool_search_employees(args: dict, _context: dict) -> dict:
    rows = _employee_search(args.get("query", ""))
    return {"count": len(rows), "employees": rows}


def _tool_get_transaction(args: dict, context: dict) -> dict:
    tx_id = _required_text(args.get("transaction_id"), "Transaction ID", 50).upper()
    with engine.connect() as conn:
        row = conn.execute(transactions_table.select().where(transactions_table.c.transaction_id == tx_id)).mappings().first()
        case = conn.execute(cases_table.select().where(cases_table.c.transaction_id == tx_id)).mappings().first()
    if not row or not case:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if context.get("role") == "CUSTOMER" and case["customer_id"] != context.get("id"):
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {key: row[key] for key in ("transaction_id", "amount", "currency", "bank_status", "network_status",
            "merchant_status", "settlement_status", "resolution_status", "workflow_type", "action_id", "created_at")}


def _tool_search_transactions(args: dict, _context: dict) -> dict:
    minimum = float(args.get("minimum_amount") or 0)
    status_filter = str(args.get("status") or "").upper()
    with engine.connect() as conn:
        rows = conn.execute(transactions_table.select().where(transactions_table.c.amount >= minimum)
                            .order_by(transactions_table.c.created_at.desc())).mappings().all()
    matched = [row for row in rows if not status_filter or status_filter in {
        str(row["bank_status"]).upper(), str(row["network_status"]).upper(), str(row["resolution_status"]).upper()}]
    return {"count": len(matched), "transactions": [{key: row[key] for key in (
        "transaction_id", "amount", "currency", "bank_status", "network_status", "merchant_status",
        "settlement_status", "resolution_status", "created_at")} for row in matched[:100]]}


def _tool_create_refund(args: dict, context: dict) -> dict:
    tx_id = _required_text(args.get("transaction_id"), "Transaction ID", 50).upper()
    reason = _required_text(args.get("reason", "Customer requested refund"), "Reason", 500)
    with engine.connect() as conn:
        tx = conn.execute(transactions_table.select().where(transactions_table.c.transaction_id == tx_id)).mappings().first()
    case = db_get_case_by_tx(tx_id)
    if not tx or not case:
        raise HTTPException(status_code=404, detail="Transaction not found")
    customer_id = case["customer_id"]
    idem = f"{customer_id}:{tx_id}:refund-v1"
    previous = db_get_refund_by_idempotency(idem) or db_get_refund_by_transaction(tx_id)
    if previous:
        return previous
    eligible = (tx["bank_status"] == "DEBITED" and tx["network_status"] == "SUCCESS"
                and tx["merchant_status"] == "NOT_CREDITED" and tx["settlement_status"] == "NOT_FOUND"
                and tx["risk_score"] < 0.30 and tx["amount"] <= 10000 and not tx["previous_refund"])
    if not eligible:
        raise HTTPException(status_code=409, detail="Transaction does not meet automatic refund policy")
    now = _now()
    refund = {"refund_id": f"RFD-{uuid4().hex[:10].upper()}", "idempotency_key": idem,
              "transaction_id": tx_id, "customer_id": customer_id, "amount": tx["amount"],
              "reason": reason, "status": "PROCESSING", "action_ref": None,
              "created_at": now, "completed_at": None}
    try:
        with engine.begin() as conn:
            conn.execute(refunds_table.insert().values(**refund))
    except Exception:
        previous = db_get_refund_by_idempotency(idem) or db_get_refund_by_transaction(tx_id)
        if previous:
            return previous
        raise
    result = ActionGateway.execute_action(tx_id, "AUTO_REVERSAL", {"amount": tx["amount"]},
        rule_id="RULE_W1_AUTO_REVERSAL_01", actor=f"{context.get('name', 'Employee')} via ZeroTouch")
    if not result.get("verified"):
        with engine.begin() as conn:
            conn.execute(refunds_table.update().where(refunds_table.c.refund_id == refund["refund_id"])
                         .values(status="FAILED", action_ref=result.get("action_id")))
        raise HTTPException(status_code=409, detail="Reversal failed independent verification")
    completed = _now()
    with engine.begin() as conn:
        conn.execute(refunds_table.update().where(refunds_table.c.refund_id == refund["refund_id"])
                     .values(status="VERIFIED", action_ref=result["action_id"], completed_at=completed))
    db_add_event(tx_id, "NOTIFICATION", "send_notification", "SUCCESS",
        f"Verified refund {refund['refund_id']} was confirmed to the customer.",
        visibility="CUSTOMER", actor="Finance Agent")
    return {**refund, "status": "VERIFIED", "action_ref": result["action_id"], "completed_at": completed}


def _tool_get_refund(args: dict, context: dict) -> dict:
    refund_id = args.get("refund_id")
    transaction_id = args.get("transaction_id")
    if not refund_id and not transaction_id:
        raise HTTPException(status_code=422, detail="Provide a refund ID or transaction ID")
    row = db_get_refund(_required_text(refund_id, "Refund ID", 60)) if refund_id else db_get_refund_by_transaction(
        _required_text(transaction_id, "Transaction ID", 60).upper())
    if not row or (context.get("role") == "CUSTOMER" and row["customer_id"] != context.get("id")):
        raise HTTPException(status_code=404, detail="Refund not found")
    return row


def _tool_create_ticket(args: dict, context: dict) -> dict:
    summary = _required_text(args.get("summary"), "Ticket summary", 1000)
    tx_id = args.get("transaction_id")
    case = db_get_case_by_tx(tx_id) if tx_id else None
    if tx_id and not case:
        raise HTTPException(status_code=404, detail="Transaction not found")
    customer_id = args.get("customer_id") or (case["customer_id"] if case else None)
    if not customer_id:
        raise HTTPException(status_code=422, detail="A customer or transaction is required")
    now = _now()
    ticket = {"ticket_id": f"TKT-{uuid4().hex[:10].upper()}", "case_id": case["case_id"] if case else None,
              "customer_id": customer_id, "category": str(args.get("category") or "GENERAL").upper()[:50],
              "priority": str(args.get("priority") or "NORMAL").upper(), "status": "OPEN",
              "assigned_team": "Customer Support", "summary": summary, "created_at": now, "resolved_at": None}
    if ticket["priority"] not in ("LOW", "NORMAL", "HIGH", "URGENT"):
        raise HTTPException(status_code=422, detail="Unsupported ticket priority")
    with engine.begin() as conn:
        conn.execute(support_tickets_table.insert().values(**ticket))
    return ticket


def _tool_update_ticket(args: dict, _context: dict) -> dict:
    ticket_id = _required_text(args.get("ticket_id"), "Ticket ID", 60)
    status = _required_text(args.get("status"), "Ticket status", 30).upper()
    if status not in ("OPEN", "IN_PROGRESS", "WAITING_CUSTOMER", "RESOLVED", "CLOSED"):
        raise HTTPException(status_code=422, detail="Unsupported ticket status")
    with engine.begin() as conn:
        found = conn.execute(support_tickets_table.select().where(support_tickets_table.c.ticket_id == ticket_id)).mappings().first()
        if not found:
            raise HTTPException(status_code=404, detail="Ticket not found")
        conn.execute(support_tickets_table.update().where(support_tickets_table.c.ticket_id == ticket_id)
                     .values(status=status, resolved_at=_now() if status in ("RESOLVED", "CLOSED") else None))
        updated = conn.execute(support_tickets_table.select().where(support_tickets_table.c.ticket_id == ticket_id)).mappings().first()
    return dict(updated)


def _tool_create_expense(args: dict, context: dict) -> dict:
    employee_id = _required_text(args.get("employee_id") or context.get("id"), "Employee ID", 60)
    if not _get_employee(employee_id):
        raise HTTPException(status_code=404, detail="Employee not found")
    amount = float(args.get("amount") or 0)
    if amount <= 0 or amount > 500000:
        raise HTTPException(status_code=422, detail="Expense amount must be between ₹1 and ₹5,00,000")
    category = _required_text(args.get("category", "TRAVEL"), "Category", 60).upper()
    purpose = _required_text(args.get("business_purpose"), "Business purpose", 300)
    status = "SUBMITTED" if amount > 5000 else "APPROVED"
    now = _now()
    expense = {"expense_id": f"EXP-{uuid4().hex[:10].upper()}", "employee_id": employee_id,
               "category": category, "amount": amount, "currency": "INR", "status": status,
               "submitted_at": now, "business_purpose": purpose, "receipt_attached": bool(args.get("receipt_attached", False))}
    payload = json.dumps(expense)
    with engine.begin() as conn:
        conn.execute(expenses_table.insert().values(expense_id=expense["expense_id"], employee_id=employee_id,
            category=category, amount=amount, currency="INR", status=status, submitted_at=now, payload=payload))
    expense["approval_note"] = "Auto-approved within the demo limit." if status == "APPROVED" else "Manager approval required above ₹5,000."
    return expense


def _tool_approve_expense(args: dict, context: dict) -> dict:
    if context.get("role") != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin approval is required for expenses")
    expense_id = _required_text(args.get("expense_id"), "Expense ID", 60)
    with engine.begin() as conn:
        row = conn.execute(expenses_table.select().where(expenses_table.c.expense_id == expense_id)).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Expense not found")
        conn.execute(expenses_table.update().where(expenses_table.c.expense_id == expense_id).values(status="APPROVED"))
    payload = json.loads(row["payload"])
    payload["status"] = "APPROVED"
    return payload


def _tool_get_leave_balance(args: dict, context: dict) -> dict:
    employee_id = _required_text(args.get("employee_id") or context.get("id"), "Employee ID", 60)
    employee = _get_employee(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    with engine.connect() as conn:
        used = conn.execute(select(leave_requests_table.c.days).where(
            leave_requests_table.c.employee_id == employee_id,
            leave_requests_table.c.status == "APPROVED")).scalars().all()
        requests = conn.execute(leave_requests_table.select().where(leave_requests_table.c.employee_id == employee_id)).mappings().all()
    taken = sum(used)
    return {"employee_id": employee_id, "employee_name": employee["name"], "annual_allowance": 20,
            "approved_days_used": taken, "days_remaining": max(0, 20 - taken),
            "requests": [dict(row) for row in requests]}


def _tool_create_it_ticket(args: dict, context: dict) -> dict:
    employee_id = _required_text(args.get("employee_id") or context.get("id"), "Employee ID", 60)
    if not _get_employee(employee_id):
        raise HTTPException(status_code=404, detail="Employee not found")
    summary = _required_text(args.get("summary"), "IT request", 800)
    ticket_id = f"IT-{uuid4().hex[:10].upper()}"
    now = _now()
    payload = {"ticket_id": ticket_id, "employee_id": employee_id, "category": str(args.get("category") or "SUPPORT").upper(),
               "priority": str(args.get("priority") or "NORMAL").upper(), "status": "OPEN", "summary": summary}
    with engine.begin() as conn:
        conn.execute(it_tickets_table.insert().values(ticket_id=ticket_id, employee_id=employee_id,
            category=payload["category"], priority=payload["priority"], status="OPEN", summary=summary,
            created_at=now, payload=json.dumps(payload)))
    return payload


def _tool_create_access_request(args: dict, context: dict) -> dict:
    employee_id = _required_text(args.get("employee_id") or context.get("id"), "Employee ID", 60)
    if not _get_employee(employee_id):
        raise HTTPException(status_code=404, detail="Employee not found")
    system_name = _required_text(args.get("system_name"), "System", 100)
    access_level = _required_text(args.get("access_level", "READ_ONLY"), "Access level", 50).upper()
    if access_level in ("ADMIN", "ROOT", "PRODUCTION_ADMIN"):
        raise HTTPException(status_code=409, detail="Privileged access must go through a security review")
    reason = _required_text(args.get("business_reason"), "Business reason", 300)
    with engine.connect() as conn:
        existing = conn.execute(access_requests_table.select().where(
            access_requests_table.c.employee_id == employee_id,
            access_requests_table.c.system_name == system_name,
            access_requests_table.c.status == "PENDING_APPROVAL")).mappings().first()
    if existing:
        return dict(existing)
    request_id = f"AR-{uuid4().hex[:10].upper()}"
    now = _now()
    payload = {"request_id": request_id, "employee_id": employee_id, "system_name": system_name,
               "access_level": access_level, "status": "PENDING_APPROVAL", "business_reason": reason,
               "created_at": now}
    with engine.begin() as conn:
        conn.execute(access_requests_table.insert().values(request_id=request_id, employee_id=employee_id,
            system_name=system_name, access_level=access_level, status="PENDING_APPROVAL",
            business_reason=reason, created_at=now, payload=json.dumps(payload)))
    return payload


def _assign_training(employee_id: str, module_id: str, context: dict, agent: str = "HR Agent") -> dict:
    with engine.begin() as conn:
        existing = conn.execute(training_assignments_table.select().where(
            training_assignments_table.c.employee_id == employee_id,
            training_assignments_table.c.module_id == module_id)).mappings().first()
        if existing:
            return dict(existing)
        assignment = {"assignment_id": f"TA-{uuid4().hex[:10].upper()}", "employee_id": employee_id,
                      "module_id": module_id, "status": "ASSIGNED", "assigned_at": _now(), "completed_at": None}
        conn.execute(training_assignments_table.insert().values(**assignment))
    record_audit(context, agent, "assign_training", "ASSIGN", "training_assignment", assignment["assignment_id"], "SUCCESS", f"Assigned {module_id}")
    return assignment


def _tool_assign_training(args: dict, context: dict) -> dict:
    employee_id = _required_text(args.get("employee_id"), "Employee ID", 60)
    module_id = _required_text(args.get("module_id"), "Training module", 60)
    with engine.connect() as conn:
        module = conn.execute(training_modules_table.select().where(training_modules_table.c.module_id == module_id)).mappings().first()
    if not _get_employee(employee_id) or not module:
        raise HTTPException(status_code=404, detail="Employee or training module not found")
    return _assign_training(employee_id, module_id, context)


def _tool_get_training_progress(args: dict, _context: dict) -> dict:
    employee_id = _required_text(args.get("employee_id"), "Employee ID", 60)
    with engine.connect() as conn:
        rows = conn.execute(select(training_assignments_table, training_modules_table.c.title,
                                  training_modules_table.c.department_id)
                            .join(training_modules_table, training_assignments_table.c.module_id == training_modules_table.c.module_id)
                            .where(training_assignments_table.c.employee_id == employee_id)).mappings().all()
    if not rows and not _get_employee(employee_id):
        raise HTTPException(status_code=404, detail="Employee not found")
    return {"employee_id": employee_id, "assigned": len(rows),
            "completed": sum(row["status"] == "COMPLETED" for row in rows), "modules": [dict(row) for row in rows]}


def _tool_search_knowledge(args: dict, _context: dict) -> dict:
    query = _required_text(args.get("query"), "Knowledge query", 300).lower()
    words = {word for word in re.findall(r"[a-z0-9₹]+", query) if len(word) > 2}
    with engine.connect() as conn:
        rows = conn.execute(knowledge_documents_table.select()).mappings().all()
    scored = []
    for row in rows:
        haystack = f"{row['title']} {row['category']} {row['content']}".lower()
        score = sum(word in haystack for word in words)
        if score:
            scored.append((score, row))
    scored.sort(key=lambda item: (-item[0], item[1]["title"]))
    results = [{"document_id": row["document_id"], "title": row["title"], "category": row["category"],
                "content": row["content"]} for _score, row in scored[:4]]
    return {"count": len(results), "documents": results}


def _tool_generate_report(args: dict, _context: dict) -> dict:
    report_type = _required_text(args.get("report_type", "support"), "Report type", 60).lower()
    minimum = float(args.get("minimum_amount") or 0)
    with engine.connect() as conn:
        txs = conn.execute(transactions_table.select().where(transactions_table.c.amount >= minimum)).mappings().all()
        tickets = conn.execute(support_tickets_table.select()).mappings().all()
        refunds = conn.execute(refunds_table.select()).mappings().all()
        cases = conn.execute(cases_table.select()).mappings().all()
        expenses = conn.execute(expenses_table.select()).mappings().all()
    if report_type in ("failed_payments", "failed_transactions"):
        failed = [tx for tx in txs if tx["bank_status"] == "FAILED" or tx["network_status"] in ("FAILED", "TIMEOUT")
                  or (tx["workflow_type"] == "W1" and tx["bank_status"] == "DEBITED" and tx["network_status"] == "SUCCESS"
                      and tx["merchant_status"] == "NOT_CREDITED" and tx["settlement_status"] == "NOT_FOUND")]
        return {"report_type": "failed_payments", "count": len(failed), "total_amount": sum(row["amount"] for row in failed),
                "transactions": [{key: row[key] for key in ("transaction_id", "amount", "customer_name", "resolution_status", "created_at")} for row in failed[:100]]}
    if report_type in ("high_priority_complaints", "unresolved_complaints"):
        open_tickets = [row for row in tickets if row["status"] not in ("RESOLVED", "CLOSED") and row["priority"] in ("HIGH", "URGENT")]
        return {"report_type": "high_priority_complaints", "count": len(open_tickets), "tickets": [dict(row) for row in open_tickets[:100]]}
    if report_type in ("department", "department_metrics"):
        return {"report_type": "department_metrics", "transaction_count": len(txs), "support_case_count": len(cases),
                "open_tickets": sum(row["status"] not in ("RESOLVED", "CLOSED") for row in tickets),
                "refund_count": len(refunds), "pending_refunds": sum(row["status"] == "PROCESSING" for row in refunds),
                "pending_expenses": sum(row["status"] == "SUBMITTED" for row in expenses)}
    return {"report_type": "support", "transaction_count": len(txs),
            "resolved_cases": sum(row["ops_status"] == "RESOLVED" for row in cases),
            "escalated_cases": sum(row["ops_status"] == "ESCALATED" for row in cases),
            "open_tickets": sum(row["status"] not in ("RESOLVED", "CLOSED") for row in tickets),
            "refund_count": len(refunds)}


def _tool_search_leads(args: dict, _context: dict) -> dict:
    query = str(args.get("query") or "").strip().lower()
    with engine.connect() as conn:
        rows = conn.execute(sales_leads_table.select().order_by(sales_leads_table.c.score.desc())).mappings().all()
    matched = [dict(row) for row in rows if not query or query in f"{row['name']} {row['company']} {row['stage']}".lower()]
    return {"count": len(matched), "leads": matched[:50]}


def _tool_qualify_lead(args: dict, _context: dict) -> dict:
    lead_id = _required_text(args.get("lead_id"), "Lead ID", 60)
    with engine.begin() as conn:
        row = conn.execute(sales_leads_table.select().where(sales_leads_table.c.lead_id == lead_id)).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Lead not found")
        status = "QUALIFIED" if row["consent_status"] == "OPTED_IN" and row["score"] >= 70 else "NEEDS_REVIEW"
        payload = json.loads(row["payload"])
        payload.update({"stage": status, "qualification_note": "Consent and fit score reviewed; no automated rejection."})
        conn.execute(sales_leads_table.update().where(sales_leads_table.c.lead_id == lead_id).values(
            stage=status, payload=json.dumps(payload)))
    return payload


def _tool_sales_summary(_args: dict, _context: dict) -> dict:
    with engine.connect() as conn:
        leads = conn.execute(sales_leads_table.select()).mappings().all()
    return {"total_leads": len(leads), "qualified": sum(row["stage"] == "QUALIFIED" for row in leads),
            "opted_in": sum(row["consent_status"] == "OPTED_IN" for row in leads),
            "pipeline_by_stage": {stage: sum(row["stage"] == stage for row in leads) for stage in sorted({row["stage"] for row in leads})}}


def _tool_campaign_report(args: dict, _context: dict) -> dict:
    query = str(args.get("query") or "").strip().lower()
    with engine.connect() as conn:
        rows = conn.execute(campaigns_table.select().order_by(campaigns_table.c.created_at.desc())).mappings().all()
    campaigns = [dict(row) for row in rows if not query or query in f"{row['name']} {row['channel']} {row['audience']} {row['status']}".lower()]
    for row in campaigns:
        row["click_through_rate_pct"] = round(row["clicks"] / row["impressions"] * 100, 2) if row["impressions"] else 0
        row["conversion_rate_pct"] = round(row["conversions"] / row["clicks"] * 100, 2) if row["clicks"] else 0
        row["roas"] = round(row["revenue"] / row["spend"], 2) if row["spend"] else 0
    return {"count": len(campaigns), "campaigns": campaigns[:50],
            "total_spend": sum(row["spend"] for row in campaigns), "total_revenue": sum(row["revenue"] for row in campaigns)}


def _tool_customer_segments(_args: dict, _context: dict) -> dict:
    with engine.connect() as conn:
        rows = conn.execute(select(cases_table.c.customer_id, transactions_table.c.amount)
            .join(transactions_table, transactions_table.c.transaction_id == cases_table.c.transaction_id)).all()
    segments = {"under_₹5,000": 0, "₹5,000–₹15,000": 0, "over_₹15,000": 0}
    for _customer, amount in rows:
        key = "under_₹5,000" if amount < 5000 else "₹5,000–₹15,000" if amount <= 15000 else "over_₹15,000"
        segments[key] += 1
    return {"transaction_segments": segments, "records_analyzed": len(rows)}


def _tool_create_task(args: dict, context: dict) -> dict:
    title = _required_text(args.get("title"), "Task title", 180)
    description = _required_text(args.get("description", title), "Task description", 1000)
    agent = _required_text(args.get("assigned_agent", "Operations Agent"), "Assigned agent", 100)
    priority = str(args.get("priority", "NORMAL")).upper()
    if priority not in ("LOW", "NORMAL", "HIGH", "URGENT"):
        raise HTTPException(status_code=422, detail="Unsupported task priority")
    with engine.connect() as conn:
        existing = conn.execute(tasks_table.select().where(
            tasks_table.c.title == title, tasks_table.c.requester == context.get("name", "Employee"),
            tasks_table.c.status.in_(("OPEN", "IN_PROGRESS", "WAITING")))).mappings().first()
    if existing:
        return dict(existing)
    now = _now()
    task = {"task_id": f"TASK-{uuid4().hex[:10].upper()}", "title": title, "description": description,
            "requester": context.get("name", "Employee"), "assigned_agent": agent, "priority": priority,
            "status": "OPEN", "created_at": now, "updated_at": now}
    with engine.begin() as conn:
        conn.execute(tasks_table.insert().values(**task, payload=json.dumps(task)))
    return task


def _tool_update_task(args: dict, _context: dict) -> dict:
    task_id = _required_text(args.get("task_id"), "Task ID", 80)
    status = _required_text(args.get("status"), "Task status", 30).upper()
    if status not in ("OPEN", "IN_PROGRESS", "WAITING", "COMPLETED", "FAILED", "ESCALATED"):
        raise HTTPException(status_code=422, detail="Unsupported task status")
    with engine.begin() as conn:
        row = conn.execute(tasks_table.select().where(tasks_table.c.task_id == task_id)).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="Task not found")
        payload = json.loads(row["payload"])
        payload["status"] = status
        payload["updated_at"] = _now()
        conn.execute(tasks_table.update().where(tasks_table.c.task_id == task_id).values(status=status,
            updated_at=payload["updated_at"], payload=json.dumps(payload)))
    return payload


def _tool_escalate_to_human(args: dict, context: dict) -> dict:
    summary = _required_text(args.get("summary"), "Escalation summary", 800)
    ticket = _tool_create_ticket({"customer_id": args.get("customer_id"), "transaction_id": args.get("transaction_id"),
                                  "summary": summary, "category": args.get("category", "ESCALATION"),
                                  "priority": "HIGH"}, context)
    task = _tool_create_task({"title": f"Human review: {summary[:80]}", "description": summary,
                              "assigned_agent": "Escalation Agent", "priority": "HIGH"}, context)
    return {"ticket": ticket, "task": task, "status": "ESCALATED"}


def _tool_create_onboarding_plan(args: dict, context: dict) -> dict:
    name = _required_text(args.get("employee_name"), "Employee name", 100)
    department = _required_text(args.get("department"), "Department", 50).lower()
    if department not in {"finance", "hr", "it", "support", "analytics", "sales", "marketing", "operations"}:
        raise HTTPException(status_code=422, detail="Unknown department")
    matches = _employee_search(name)
    employee = next((row for row in matches if row["name"].lower() == name.lower()), matches[0] if len(matches) == 1 else None)
    now = _now()
    if employee:
        employee_id = employee["employee_id"]
        with engine.begin() as conn:
            conn.execute(employees_table.update().where(employees_table.c.employee_id == employee_id).values(
                department_id=department, status="ACTIVE"))
    else:
        employee_id = f"emp-{uuid4().hex[:8]}"
        email_local = re.sub(r"[^a-z0-9]+", ".", name.lower()).strip(".")
        payload = {"employee_id": employee_id, "name": name, "email": f"{email_local}.{employee_id[-4:]}@zerotouch.demo",
                   "department_id": department, "role": "New Joiner", "status": "ACTIVE", "manager_id": f"emp-{department}"}
        with engine.begin() as conn:
            conn.execute(employees_table.insert().values(employee_id=employee_id, name=name, email=payload["email"],
                department_id=department, role=payload["role"], status="ACTIVE", manager_id=payload["manager_id"],
                created_at=now, payload=json.dumps(payload)))
        employee = payload
    plan_id = f"ONB-{employee_id}-01"
    with engine.begin() as conn:
        plan = conn.execute(onboarding_plans_table.select().where(onboarding_plans_table.c.plan_id == plan_id)).mappings().first()
        if not plan:
            plan_payload = {"plan_id": plan_id, "employee_id": employee_id, "department_id": department,
                            "status": "IN_PROGRESS", "created_at": now,
                            "steps": ["HR profile ready", "Department training assigned", "IT access requested", "Policies assigned", "Manager notified"]}
            conn.execute(onboarding_plans_table.insert().values(plan_id=plan_id, employee_id=employee_id,
                department_id=department, status="IN_PROGRESS", created_at=now, payload=json.dumps(plan_payload)))
    modules = ["TR-HR-01", "TR-HR-02", "TR-IT-01", "TR-OPS-01"]
    department_module = {"finance": "TR-FIN-01", "hr": "TR-HR-01", "it": "TR-IT-01", "support": "TR-SUP-01",
                         "analytics": "TR-AN-01", "sales": "TR-SALES-01", "marketing": "TR-MKT-01", "operations": "TR-OPS-01"}[department]
    modules.append(department_module)
    assignments = [_assign_training(employee_id, module_id, context, "HR Agent" if module_id.startswith("TR-HR") else "Finance Agent" if module_id.startswith("TR-FIN") else "IT Agent" if module_id.startswith("TR-IT") else "Knowledge Agent") for module_id in dict.fromkeys(modules)]
    access = _tool_create_access_request({"employee_id": employee_id, "system_name": "Finance Workspace" if department == "finance" else f"{department.title()} Workspace",
                                          "access_level": "READ_ONLY", "business_reason": f"Least-privilege access for {department} onboarding"}, context)
    steps = [
        {"agent": "HR Agent", "action": "Employee profile and onboarding plan created", "status": "COMPLETED", "entity_id": plan_id},
        {"agent": "Finance Agent", "action": f"{department.title()} training assigned", "status": "COMPLETED", "entity_id": department_module},
        {"agent": "IT Agent", "action": "Least-privilege access request submitted", "status": "WAITING", "entity_id": access["request_id"]},
        {"agent": "Knowledge Agent", "action": "Company policy and onboarding modules assigned", "status": "COMPLETED", "entity_id": assignments[0]["assignment_id"]},
        {"agent": "Operations Agent", "action": "Manager onboarding update queued", "status": "COMPLETED", "entity_id": plan_id},
    ]
    for step in steps:
        if step["agent"] == "Operations Agent":
            _tool_create_task({"title": f"Manager update: onboard {name}", "description": f"Onboarding plan {plan_id} is active; IT access is awaiting approval.", "assigned_agent": "Operations Agent"}, context)
        record_audit(context, step["agent"], "create_onboarding_plan", step["action"], "onboarding", plan_id, "SUCCESS", step["action"])
    return {"plan_id": plan_id, "employee": {"employee_id": employee_id, "name": name, "department": department, "status": "ACTIVE"},
            "status": "IN_PROGRESS", "agents_involved": ["HR Agent", "Finance Agent", "IT Agent", "Knowledge Agent", "Operations Agent"],
            "steps": steps, "training_assignments": assignments, "access_request": access}


def _tool_create_onboarding_wrapper(args: dict, context: dict) -> dict:
    return _tool_create_onboarding_plan(args, context)


TOOL_REGISTRY: dict[str, dict[str, Any]] = {
    "get_customer": {"fn": _tool_get_customer, "agent": "Customer Support Agent", "description": "Look up a customer by customer ID or email.", "parameters": {"type": "object", "properties": {"customer_id": {"type": "string"}, "email": {"type": "string"}}}},
    "get_employee": {"fn": _tool_get_employee, "agent": "HR Agent", "description": "Get one employee by name, email, or employee ID.", "parameters": {"type": "object", "properties": {"employee_id": {"type": "string"}, "query": {"type": "string"}}}},
    "search_employees": {"fn": _tool_search_employees, "agent": "HR Agent", "description": "Search the employee directory by name or email.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    "get_transaction": {"fn": _tool_get_transaction, "agent": "Finance Agent", "description": "Look up transaction ledger status and metadata.", "parameters": {"type": "object", "properties": {"transaction_id": {"type": "string"}}, "required": ["transaction_id"]}},
    "search_transactions": {"fn": _tool_search_transactions, "agent": "Finance Agent", "description": "Search transactions using an optional status and minimum amount.", "parameters": {"type": "object", "properties": {"status": {"type": "string"}, "minimum_amount": {"type": "number"}}}},
    "create_refund": {"fn": _tool_create_refund, "agent": "Finance Agent", "description": "Create and verify an eligible customer refund through the Action Gateway.", "parameters": {"type": "object", "properties": {"transaction_id": {"type": "string"}, "reason": {"type": "string"}}, "required": ["transaction_id", "reason"]}},
    "get_refund": {"fn": _tool_get_refund, "agent": "Finance Agent", "description": "Get refund status by refund ID or transaction ID.", "parameters": {"type": "object", "properties": {"refund_id": {"type": "string"}, "transaction_id": {"type": "string"}}}},
    "create_ticket": {"fn": _tool_create_ticket, "agent": "Customer Support Agent", "description": "Create a customer support ticket.", "parameters": {"type": "object", "properties": {"summary": {"type": "string"}, "customer_id": {"type": "string"}, "transaction_id": {"type": "string"}, "category": {"type": "string"}, "priority": {"type": "string"}}, "required": ["summary"]}},
    "update_ticket": {"fn": _tool_update_ticket, "agent": "Customer Support Agent", "description": "Update a support ticket's status.", "parameters": {"type": "object", "properties": {"ticket_id": {"type": "string"}, "status": {"type": "string"}}, "required": ["ticket_id", "status"]}},
    "create_expense": {"fn": _tool_create_expense, "agent": "Finance Agent", "description": "Submit an employee expense for policy review.", "parameters": {"type": "object", "properties": {"employee_id": {"type": "string"}, "category": {"type": "string"}, "amount": {"type": "number"}, "business_purpose": {"type": "string"}, "receipt_attached": {"type": "boolean"}}, "required": ["category", "amount", "business_purpose"]}},
    "approve_expense": {"fn": _tool_approve_expense, "agent": "Finance Agent", "description": "Approve a submitted expense; admin access required.", "parameters": {"type": "object", "properties": {"expense_id": {"type": "string"}}, "required": ["expense_id"]}},
    "get_leave_balance": {"fn": _tool_get_leave_balance, "agent": "HR Agent", "description": "Read an employee's leave balance and request history.", "parameters": {"type": "object", "properties": {"employee_id": {"type": "string"}}}},
    "create_it_ticket": {"fn": _tool_create_it_ticket, "agent": "IT Agent", "description": "Create an IT support ticket for an employee.", "parameters": {"type": "object", "properties": {"employee_id": {"type": "string"}, "category": {"type": "string"}, "priority": {"type": "string"}, "summary": {"type": "string"}}, "required": ["summary"]}},
    "create_access_request": {"fn": _tool_create_access_request, "agent": "IT Agent", "description": "Create a least-privilege system access request. Privileged access is blocked for human security review.", "parameters": {"type": "object", "properties": {"employee_id": {"type": "string"}, "system_name": {"type": "string"}, "access_level": {"type": "string"}, "business_reason": {"type": "string"}}, "required": ["system_name", "access_level", "business_reason"]}},
    "create_onboarding_plan": {"fn": _tool_create_onboarding_wrapper, "agent": "Supervisor Agent", "description": "Coordinate HR, department training, IT least-privilege request, company knowledge assignments, and manager notification for a new employee.", "parameters": {"type": "object", "properties": {"employee_name": {"type": "string"}, "department": {"type": "string"}}, "required": ["employee_name", "department"]}},
    "assign_training": {"fn": _tool_assign_training, "agent": "HR Agent", "description": "Assign a training module to an employee.", "parameters": {"type": "object", "properties": {"employee_id": {"type": "string"}, "module_id": {"type": "string"}}, "required": ["employee_id", "module_id"]}},
    "get_training_progress": {"fn": _tool_get_training_progress, "agent": "HR Agent", "description": "Get an employee's assigned and completed training.", "parameters": {"type": "object", "properties": {"employee_id": {"type": "string"}}, "required": ["employee_id"]}},
    "search_knowledge": {"fn": _tool_search_knowledge, "agent": "Knowledge Agent", "description": "Search company policies and approved operating guides.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    "generate_report": {"fn": _tool_generate_report, "agent": "Analytics Agent", "description": "Generate a database-backed support, failed-payment, high-priority complaint, or department metrics report.", "parameters": {"type": "object", "properties": {"report_type": {"type": "string"}, "minimum_amount": {"type": "number"}}}},
    "search_leads": {"fn": _tool_search_leads, "agent": "Sales Agent", "description": "Search the opted-in demo sales lead pipeline by name, company, or stage.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}}},
    "qualify_lead": {"fn": _tool_qualify_lead, "agent": "Sales Agent", "description": "Review lead fit and consent. Low-confidence leads are sent to review, never auto-rejected.", "parameters": {"type": "object", "properties": {"lead_id": {"type": "string"}}, "required": ["lead_id"]}},
    "get_sales_summary": {"fn": _tool_sales_summary, "agent": "Sales Agent", "description": "Summarize the demo sales pipeline by lead stage and consent.", "parameters": {"type": "object", "properties": {}}},
    "get_campaign_performance": {"fn": _tool_campaign_report, "agent": "Marketing Agent", "description": "List campaign metrics including reach, click and conversion rates, spend, revenue, and ROAS.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}}},
    "get_customer_segments": {"fn": _tool_customer_segments, "agent": "Marketing Agent", "description": "Summarize customer transaction value segments from linked demo cases.", "parameters": {"type": "object", "properties": {}}},
    "create_task": {"fn": _tool_create_task, "agent": "Operations Agent", "description": "Create a persistent, assigned work task.", "parameters": {"type": "object", "properties": {"title": {"type": "string"}, "description": {"type": "string"}, "assigned_agent": {"type": "string"}, "priority": {"type": "string"}}, "required": ["title"]}},
    "update_task": {"fn": _tool_update_task, "agent": "Operations Agent", "description": "Update the status of a persistent work task.", "parameters": {"type": "object", "properties": {"task_id": {"type": "string"}, "status": {"type": "string"}}, "required": ["task_id", "status"]}},
    "escalate_to_human": {"fn": _tool_escalate_to_human, "agent": "Escalation Agent", "description": "Create a high-priority support case and a human review task.", "parameters": {"type": "object", "properties": {"summary": {"type": "string"}, "customer_id": {"type": "string"}, "transaction_id": {"type": "string"}, "category": {"type": "string"}}, "required": ["summary"]}},
}


def tool_schemas() -> list[dict]:
    return [{"type": "function", "name": name, "description": spec["description"], "parameters": spec["parameters"]}
            for name, spec in TOOL_REGISTRY.items()]


def execute_tool(name: str, arguments: dict, context: dict) -> dict:
    spec = TOOL_REGISTRY.get(name)
    if not spec:
        raise HTTPException(status_code=400, detail="Requested tool is not registered")
    if not isinstance(arguments, dict):
        raise HTTPException(status_code=422, detail="Tool arguments must be an object")
    try:
        result = spec["fn"](arguments, context)
        entity_id = result.get("task_id") or result.get("plan_id") or result.get("refund_id") or result.get("ticket_id") or result.get("transaction_id")
        record_audit(context, spec["agent"], name, name, name.removeprefix("get_").removeprefix("create_"),
                     entity_id, "SUCCESS", f"Tool completed: {name}")
        return result
    except Exception as exc:
        status = getattr(exc, "status_code", 500)
        record_audit(context, spec["agent"], name, name, name, None, "FAILED", str(getattr(exc, "detail", exc)))
        return {"error": str(getattr(exc, "detail", exc)), "status_code": status}
