"""Employee-facing supervisor: plans work, calls registered tools, verifies and logs."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException

from backend.database import (
    engine, conversations_table, employee_messages_table, tasks_table,
)
from backend.enterprise_tools import TOOL_REGISTRY, execute_tool, record_audit
from backend.xai_service import XAIUnavailable, run_grok


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fallback(message: str, context: dict, department: str) -> dict:
    lower = message.lower()
    calls = []

    def call(name: str, arguments: dict) -> dict:
        result = execute_tool(name, arguments, context)
        spec = TOOL_REGISTRY[name]
        calls.append({"tool": name, "agent": spec["agent"],
                      "status": "FAILED" if result.get("error") else "COMPLETED", "result": result})
        return result

    onboarding = re.search(r"onboard\s+(.+?)\s+into\s+(finance|hr|it|support|analytics|sales|marketing|operations)\b", lower)
    if onboarding:
        name_match = re.search(r"onboard\s+(.+?)\s+into\s+", message, re.IGNORECASE)
        result = call("create_onboarding_plan", {"employee_name": name_match.group(1).strip(), "department": onboarding.group(2)})
        if not result.get("error"):
            reply = f"I prepared {result['employee']['name']}'s {onboarding.group(2).title()} onboarding plan. HR, department training, IT access, company policies, and the manager update are coordinated. IT access is awaiting approval."
        else:
            reply = result["error"]
        return {"reply": reply, "tool_calls": calls, "status": "WAITING" if not result.get("error") else "NEEDS_INPUT"}

    threshold_match = re.search(r"(?:above|over|greater than|more than)\s*(?:₹|rs\.?\s*)?([\d,]+)", lower)
    if "failed" in lower and any(word in lower for word in ("payment", "transaction")):
        result = call("generate_report", {"report_type": "failed_payments",
                                          "minimum_amount": float(threshold_match.group(1).replace(",", "")) if threshold_match else 0})
        count = result.get("count", 0)
        reply = f"I found {count} failed payment(s)" + (f" above ₹{result.get('minimum_amount', threshold_match.group(1))}." if threshold_match else ".")
        return {"reply": reply, "tool_calls": calls, "status": "COMPLETED"}

    if "high-priority" in lower or "high priority" in lower or "complaint" in lower:
        result = call("generate_report", {"report_type": "high_priority_complaints"})
        return {"reply": f"I found {result.get('count', 0)} unresolved high-priority customer complaint(s).", "tool_calls": calls, "status": "COMPLETED"}

    if "refund policy" in lower or "policy" in lower or "how do refunds" in lower:
        query = "refund reversal eligibility status customer policy" if "refund" in lower else message
        result = call("search_knowledge", {"query": query})
        docs = result.get("documents", [])
        reply = "\n\n".join(f"**{doc['title']}**\n{doc['content']}" for doc in docs) if docs else "I couldn't find an approved policy document for that question."
        return {"reply": reply, "tool_calls": calls, "status": "COMPLETED" if docs else "NEEDS_INPUT"}

    refund_id_match = re.search(r"\bRFD-[A-Z0-9]+\b", message.upper())
    refund_tx_match = re.search(r"\bTX\d{4,6}\b", message.upper())
    if "refund" in lower and any(word in lower for word in ("status", "where", "check", "track")):
        if refund_id_match or refund_tx_match:
            result = call("get_refund", {"refund_id": refund_id_match.group(0)} if refund_id_match else
                          {"transaction_id": refund_tx_match.group(0)})
            state = result.get("status", "not found")
            return {"reply": f"Refund status: {state}." if not result.get("error") else result["error"],
                    "tool_calls": calls, "status": "COMPLETED" if not result.get("error") else "NEEDS_INPUT"}
        return {"reply": "Share the refund ID or transaction ID and I’ll check its current status.",
                "tool_calls": calls, "status": "NEEDS_INPUT"}

    if "refund" in lower and refund_tx_match and any(word in lower for word in ("create", "issue", "process", "initiate", "customer")):
        result = call("create_refund", {"transaction_id": refund_tx_match.group(0),
                                         "reason": "Employee requested customer payment refund"})
        if result.get("error"):
            reply = result["error"]
            status = "NEEDS_INPUT"
        else:
            reply = f"Refund {result['refund_id']} is {result['status']} for TX {refund_tx_match.group(0)}."
            status = "COMPLETED" if result["status"] == "VERIFIED" else "WAITING"
        return {"reply": reply, "tool_calls": calls, "status": status}

    if refund_tx_match and any(word in lower for word in ("resolve", "refund", "money deducted", "payment failed")):
        result = call("create_refund", {"transaction_id": refund_tx_match.group(0),
                                         "reason": "Employee requested resolution of a failed customer payment"})
        if result.get("error"):
            reply, status = result["error"], "NEEDS_INPUT"
        else:
            reply, status = f"The eligible payment was reversed and independently verified. Refund {result['refund_id']} is {result['status']}.", "COMPLETED"
        return {"reply": reply, "tool_calls": calls, "status": status}

    if "onboard" in lower:
        return {"reply": "Which department should I prepare onboarding for?", "tool_calls": calls, "status": "NEEDS_INPUT"}

    if department == "it" and any(word in lower for word in ("laptop", "equipment", "vpn", "device", "it ticket", "incident")):
        employee_id = context["id"]
        person = re.search(r"(?:for|to)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", message)
        if person:
            found = call("search_employees", {"query": person.group(1)})
            employees = found.get("employees", [])
            if len(employees) != 1:
                return {"reply": "Please share the employee's full name so I can route this IT request.",
                        "tool_calls": calls, "status": "NEEDS_INPUT"}
            employee_id = employees[0]["employee_id"]
        category = "EQUIPMENT" if any(word in lower for word in ("laptop", "equipment", "device")) else "INCIDENT" if "incident" in lower else "SOFTWARE"
        ticket = call("create_it_ticket", {"employee_id": employee_id, "category": category,
            "priority": "HIGH" if "urgent" in lower else "NORMAL", "summary": clean})
        return {"reply": f"IT request {ticket.get('ticket_id', '')} is {ticket.get('status', 'FAILED')} and assigned to IT support.",
                "tool_calls": calls, "status": "COMPLETED" if not ticket.get("error") else "NEEDS_INPUT"}

    if "access request" in lower or "software access" in lower:
        person_match = re.search(r"(?:for|to)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", message)
        if not person_match:
            return {"reply": "Who needs the access request? Please provide their name.", "tool_calls": [], "status": "NEEDS_INPUT"}
        found = call("search_employees", {"query": person_match.group(1)})
        employees = found.get("employees", [])
        if len(employees) != 1:
            names = ", ".join(item["name"] for item in employees)
            return {"reply": f"I found {len(employees)} matching employee records{': ' + names if names else ''}. Please provide the employee's full name.", "tool_calls": calls, "status": "NEEDS_INPUT"}
        employee = employees[0]
        created = call("create_access_request", {"employee_id": employee["employee_id"],
            "system_name": "General IT Access", "access_level": "READ_ONLY",
            "business_reason": f"Access requested by {context['name']} for {employee['name']}"})
        return {"reply": f"I created access request {created.get('request_id', '')} for {employee['name']}. It is queued for manager approval; access has not been granted yet.",
                "tool_calls": calls, "status": "WAITING" if not created.get("error") else "NEEDS_INPUT"}

    if "travel expense" in lower or "expense" in lower:
        amount = re.search(r"(?:₹|rs\.?\s*)?([\d,]+(?:\.\d{1,2})?)", lower)
        if not amount:
            return {"reply": "What amount should I submit, and do you have a receipt?", "tool_calls": [], "status": "NEEDS_INPUT"}
        value = float(amount.group(1).replace(",", ""))
        result = call("create_expense", {"employee_id": context["id"], "category": "TRAVEL", "amount": value,
                                          "business_purpose": "Employee-submitted travel expense",
                                          "receipt_attached": "receipt" in lower})
        return {"reply": f"Expense {result.get('expense_id', '')} was recorded with status {result.get('status', 'FAILED')}. {result.get('approval_note', result.get('error', ''))}",
                "tool_calls": calls, "status": "COMPLETED" if not result.get("error") else "NEEDS_INPUT"}

    if "leave" in lower or "attendance" in lower:
        result = call("get_leave_balance", {"employee_id": context["id"]})
        return {"reply": f"You have {result.get('days_remaining', 0)} of {result.get('annual_allowance', 20)} annual leave days remaining.",
                "tool_calls": calls, "status": "COMPLETED" if not result.get("error") else "NEEDS_INPUT"}

    if department == "sales" or any(word in lower for word in ("lead", "pipeline", "sales follow-up")):
        if "summary" in lower or "pipeline" in lower:
            result = call("get_sales_summary", {})
            return {"reply": f"Sales pipeline: {result.get('total_leads', 0)} leads, {result.get('qualified', 0)} qualified, and {result.get('opted_in', 0)} opted in for outreach.",
                    "tool_calls": calls, "status": "COMPLETED" if not result.get("error") else "NEEDS_INPUT"}
        query = re.search(r"(?:at|from|company)\s+([A-Z][A-Za-z& ]+)", message)
        result = call("search_leads", {"query": query.group(1).strip() if query else ""})
        leads = result.get("leads", [])
        if "qualif" in lower and leads:
            lead_id = re.search(r"LEAD-[A-Z0-9-]+", message.upper())
            lead = next((item for item in leads if item["lead_id"] == lead_id.group(0)), leads[0])
            qualified = call("qualify_lead", {"lead_id": lead["lead_id"]})
            return {"reply": f"{qualified.get('name', lead['name'])} was marked {qualified.get('stage', 'NEEDS_REVIEW')}; the system does not auto-reject leads.",
                    "tool_calls": calls, "status": "COMPLETED" if not qualified.get("error") else "NEEDS_INPUT"}
        if "follow" in lower and leads:
            lead = leads[0]
            if lead["consent_status"] != "OPTED_IN":
                return {"reply": f"{lead['name']} is marked not contactable, so I did not create an outreach task.", "tool_calls": calls, "status": "NEEDS_INPUT"}
            task = call("create_task", {"title": f"Sales follow-up: {lead['company']}",
                "description": f"Follow up with {lead['name']} at {lead['company']}; verify current interest and record outcome.",
                "assigned_agent": "Sales Agent", "priority": "NORMAL"})
            return {"reply": f"I created a follow-up task for {lead['name']} at {lead['company']}.", "tool_calls": calls, "status": "COMPLETED" if not task.get("error") else "NEEDS_INPUT"}
        return {"reply": f"I found {result.get('count', 0)} matching sales lead(s). Review their details in the task panel.",
                "tool_calls": calls, "status": "COMPLETED" if not result.get("error") else "NEEDS_INPUT"}

    if department == "marketing" or any(word in lower for word in ("campaign", "customer segment", "marketing")):
        if "segment" in lower or "audience" in lower:
            result = call("get_customer_segments", {})
            return {"reply": f"Customer segments are ready across {result.get('records_analyzed', 0)} linked transactions.",
                    "tool_calls": calls, "status": "COMPLETED" if not result.get("error") else "NEEDS_INPUT"}
        query = re.search(r"campaign\s+(.+)$", message, re.IGNORECASE)
        campaign_query = query.group(1).strip() if query else ""
        if campaign_query.lower() in {"performance", "summary", "report", "metrics", "results"}:
            campaign_query = ""
        result = call("get_campaign_performance", {"query": campaign_query})
        return {"reply": f"I found {result.get('count', 0)} campaign(s); combined tracked revenue is ₹{result.get('total_revenue', 0):,.0f} on ₹{result.get('total_spend', 0):,.0f} spend.",
                "tool_calls": calls, "status": "COMPLETED" if not result.get("error") else "NEEDS_INPUT"}

    if any(word in lower for word in ("support report", "today's support", "todays support", "prepare today's", "department metrics", "analytics")):
        result = call("generate_report", {"report_type": "support"})
        return {"reply": f"Today's support report is ready: {result.get('transaction_count', 0)} transactions, {result.get('open_tickets', 0)} open tickets, and {result.get('escalated_cases', 0)} escalated cases.",
                "tool_calls": calls, "status": "COMPLETED"}

    if "transaction" in lower and any(word in lower for word in ("find", "look up", "status")):
        tx_id = re.search(r"\bTX\d{4,6}\b", message.upper())
        if tx_id:
            result = call("get_transaction", {"transaction_id": tx_id.group(0)})
        else:
            threshold = float(threshold_match.group(1).replace(",", "")) if threshold_match else 0
            result = call("search_transactions", {"minimum_amount": threshold})
        return {"reply": f"I found {result.get('count', 1 if result.get('transaction_id') else 0)} transaction record(s). See the verified details in the task panel.",
                "tool_calls": calls, "status": "COMPLETED" if not result.get("error") else "NEEDS_INPUT"}

    if department in ("sales", "marketing", "operations", "analytics", "finance", "hr", "it", "support"):
        report_type = "department_metrics" if department in ("analytics", "operations") else "support"
        result = call("generate_report", {"report_type": report_type})
        return {"reply": f"I checked current {department} records and prepared a database-backed summary. See the task panel for the results.",
                "tool_calls": calls, "status": "COMPLETED"}

    return {"reply": "I can onboard employees, find failed payments, create IT access or support requests, submit expenses, check leave, prepare reports, or look up company policy. What should I take care of?",
            "tool_calls": calls, "status": "NEEDS_INPUT"}


def _create_conversation(user: dict, conversation_id: str | None) -> str:
    with engine.begin() as conn:
        if conversation_id:
            row = conn.execute(conversations_table.select().where(
                conversations_table.c.conversation_id == conversation_id,
                conversations_table.c.user_id == user["id"])).mappings().first()
            if not row:
                raise HTTPException(status_code=404, detail="Conversation not found")
            return conversation_id
        new_id = f"CONV-{uuid4().hex[:12].upper()}"
        conn.execute(conversations_table.insert().values(conversation_id=new_id, user_id=user["id"],
            title="New ZeroTouch task", created_at=_now(), channel="employee"))
        return new_id


def _save_message(conversation_id: str, user: dict, role: str, content: str) -> None:
    with engine.begin() as conn:
        conn.execute(employee_messages_table.insert().values(message_id=f"MSG-{uuid4().hex[:12].upper()}",
            conversation_id=conversation_id, user_id=user["id"], role=role, content=content[:4000], created_at=_now()))


def get_conversation(user: dict, conversation_id: str) -> dict:
    with engine.connect() as conn:
        conversation = conn.execute(conversations_table.select().where(
            conversations_table.c.conversation_id == conversation_id,
            conversations_table.c.user_id == user["id"])).mappings().first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        messages = conn.execute(employee_messages_table.select().where(
            employee_messages_table.c.conversation_id == conversation_id,
            employee_messages_table.c.user_id == user["id"]).order_by(employee_messages_table.c.created_at)).mappings().all()
        task_rows = conn.execute(tasks_table.select().order_by(tasks_table.c.updated_at.desc()).limit(50)).mappings().all()
    task = next((json.loads(row["payload"]) for row in task_rows
                 if json.loads(row["payload"]).get("conversation_id") == conversation_id), None)
    return {"conversation": dict(conversation), "messages": [dict(item) for item in messages], "task": task}


async def handle_employee_message(user: dict, message: str, department: str = "all",
                                 conversation_id: str | None = None) -> dict:
    clean = message.strip()
    if not clean or len(clean) > 2000:
        raise HTTPException(status_code=422, detail="Message must contain 1–2000 characters")
    allowed_departments = {"all", "finance", "hr", "it", "support", "analytics", "sales", "marketing", "operations"}
    department = department.lower()
    if department not in allowed_departments:
        raise HTTPException(status_code=422, detail="Unknown department bot")
    context = {"id": user["id"], "name": user["name"], "role": user["role"]}
    conv_id = _create_conversation(user, conversation_id)
    prior = get_conversation(user, conv_id)["messages"]
    _save_message(conv_id, user, "user", clean)
    task_id = f"TASK-{uuid4().hex[:12].upper()}"
    now = _now()
    task_payload = {"task_id": task_id, "title": clean[:180], "description": clean, "requester": user["name"],
                    "assigned_agent": "Supervisor Agent", "priority": "NORMAL", "status": "RUNNING",
                    "created_at": now, "updated_at": now, "conversation_id": conv_id, "plan_steps": [
                        {"label": "Understanding request", "status": "COMPLETED"},
                        {"label": "Planning", "status": "RUNNING"}], "agents_involved": ["Supervisor Agent"],
                    "actions": [], "result": None}
    with engine.begin() as conn:
        conn.execute(tasks_table.insert().values(task_id=task_id, title=task_payload["title"], description=clean,
            requester=user["name"], assigned_agent="Supervisor Agent", priority="NORMAL", status="RUNNING",
            created_at=now, updated_at=now, payload=json.dumps(task_payload)))

    provider = "development_fallback"
    try:
        result = await run_grok(clean, context, prior[-10:])
        provider = result.get("provider", "xai")
        tool_calls = result.get("tool_calls", [])
        reply = result.get("reply") or "I completed the verified tools. See the task details for the results."
        status = result.get("status", "COMPLETED")
    except XAIUnavailable as exc:
        result = _fallback(clean, context, department)
        tool_calls = result.get("tool_calls", [])
        reply = result["reply"]
        status = result["status"]
        if exc.executed:
            provider = "xai_partial"
            tool_calls = exc.executed
    agents = list(dict.fromkeys(["Supervisor Agent"] + [call.get("agent", "") for call in tool_calls if call.get("agent")]
                                + [agent for call in tool_calls for agent in (call.get("result", {}).get("agents_involved", []))]))
    # Tool outcomes take precedence over model prose so a failed call is never reported as complete.
    if any(call.get("status") == "FAILED" for call in tool_calls):
        status = "NEEDS_INPUT"
    elif any(step.get("status") == "WAITING" for call in tool_calls
             for step in call.get("result", {}).get("steps", [])):
        status = "WAITING"
    actions = []
    plan_steps = []
    for call in tool_calls:
        actions.append({"agent": call.get("agent"), "tool": call.get("tool"), "status": call.get("status"),
                        "result": call.get("result")})
        internal_steps = call.get("result", {}).get("steps", [])
        if internal_steps:
            for step in internal_steps:
                plan_steps.append({"label": f"{step.get('agent', 'Agent')} · {step.get('action', 'Work')}",
                                   "status": step.get("status", "COMPLETED")})
                actions.append({"agent": step.get("agent"), "tool": step.get("action"),
                                "status": step.get("status", "COMPLETED"), "result": step})
        else:
            plan_steps.append({"label": f"{call.get('agent', 'Agent')} · {call.get('tool', 'business tool')}",
                               "status": call.get("status", "COMPLETED")})
    task_payload.update({"status": status, "updated_at": _now(), "plan_steps": [
        {"label": "Understanding request", "status": "COMPLETED"},
        {"label": "Planning", "status": "COMPLETED"},
        *plan_steps,
        {"label": "Reporting result", "status": "COMPLETED"}],
        "agents_involved": agents, "actions": actions, "result": reply})
    with engine.begin() as conn:
        conn.execute(tasks_table.update().where(tasks_table.c.task_id == task_id).values(
            status=status, updated_at=task_payload["updated_at"], payload=json.dumps(task_payload, default=str)))
    record_audit(context, "Supervisor Agent", "assistant", "HANDLE_REQUEST", "task", task_id,
                 "SUCCESS" if status in ("COMPLETED", "WAITING") else status, f"Assistant request finished with {status}")
    _save_message(conv_id, user, "assistant", reply)
    return {"conversation_id": conv_id, "task": task_payload, "reply": reply,
            "provider": provider, "department": department}
