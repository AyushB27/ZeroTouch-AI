"""
Database layer – PostgreSQL (primary) with SQLite fallback.
Canonical Case Store, Transactions, Action Gateway Log, and Audit Trail.
"""

import os
import json
from sqlalchemy import (
    create_engine, Column, String, Float, Boolean, Text,
    DateTime, Integer, MetaData, Table, text, inspect, select, func
)
from sqlalchemy.pool import StaticPool
from datetime import datetime, timezone

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./zerotouch.db")

# SQLite needs special connect_args for thread safety
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    engine = create_engine(DATABASE_URL)

metadata = MetaData()

# ── Transactions table ────────────────────────────────────────────────────────
transactions_table = Table(
    "transactions",
    metadata,
    Column("transaction_id",    String(50),  primary_key=True),
    Column("amount",            Float,       nullable=False),
    Column("currency",          String(10),  default="INR"),
    Column("bank_status",       String(50),  nullable=False),
    Column("network_status",    String(50),  nullable=False),
    Column("merchant_status",   String(100), nullable=False),
    Column("settlement_status", String(100), nullable=False),
    Column("risk_score",        Float,       default=0.0),
    Column("previous_refund",   Boolean,     default=False),
    Column("customer_name",     String(100), default="Paytm User"),
    Column("cibil_score",       Integer,     default=750),
    Column("is_first_time_user",Boolean,     default=False),
    Column("dynamic_message",   Text,        nullable=True),
    Column("action_id",         String(100), nullable=True),
    Column("resolution_status", String(50),  default="PENDING"),
    Column("workflow_type",     String(20),  default="W1"),
    Column("created_at",        DateTime,    default=datetime.now),
)

# ── Cases table (Canonical Case State) ────────────────────────────────────────
cases_table = Table(
    "cases",
    metadata,
    Column("case_id",            String(50),  primary_key=True),
    Column("transaction_id",     String(50),  nullable=False, index=True),
    Column("customer_id",        String(50),  nullable=False, default="cust-ayush"),
    Column("customer_name",      String(100), default="Paytm User"),
    Column("workflow_type",      String(20),  default="W1"),
    Column("classification",     String(100), default="UNKNOWN_PAYMENT_STATE"),
    Column("amount",             Float,       nullable=False),
    Column("currency",           String(10),  default="INR"),
    Column("evidence_matrix",    Text,        nullable=True),   # JSON string
    Column("risk_assessment",    Text,        nullable=True),   # JSON string
    Column("policy_decision",    Text,        nullable=True),   # JSON string
    Column("action_record",      Text,        nullable=True),   # JSON string
    Column("customer_status",    String(50),  default="INVESTIGATING"),
    Column("ops_status",         String(50),  default="PENDING"),
    Column("human_review_notes", Text,        nullable=True),
    Column("assigned_agent",     String(100), nullable=True),
    Column("dynamic_message",    Text,        nullable=True),
    Column("created_at",         String(50),  nullable=False),
    Column("updated_at",         String(50),  nullable=False),
)

# ── Action Gateway Log table (Idempotency & Safe Financial Execution) ─────────
action_gateway_log_table = Table(
    "action_gateway_log",
    metadata,
    Column("id",              Integer,     primary_key=True, autoincrement=True),
    Column("idempotency_key", String(128), unique=True, nullable=False),
    Column("case_id",         String(50),  nullable=False),
    Column("transaction_id",  String(50),  nullable=False),
    Column("action_type",     String(50),  nullable=False),
    Column("action_ref",      String(100), nullable=False),
    Column("status",          String(50),  nullable=False), # AUTHORIZED, EXECUTED, VERIFIED, FAILED
    Column("is_simulated",    Boolean,     default=True),
    Column("payload",         Text,        nullable=True),  # JSON string
    Column("result",          Text,        nullable=True),  # JSON string
    Column("created_at",      String(50),  nullable=False),
    Column("verified_at",     String(50),  nullable=True),
)

# ── Audit events table ────────────────────────────────────────────────────────
audit_events_table = Table(
    "audit_events",
    metadata,
    Column("id",             Integer,     primary_key=True, autoincrement=True),
    Column("transaction_id", String(50),  nullable=False),
    Column("timestamp",      String(50),  nullable=False),
    Column("type",           String(50),  nullable=False),
    Column("step",           String(100), nullable=False),
    Column("status",         String(20),  nullable=False),
    Column("message",        Text,        nullable=False),
    Column("visibility",     String(20),  default="INTERNAL"), # CUSTOMER, INTERNAL, SYSTEM
    Column("actor",          String(100), default="ZeroTouch Agent"),
)

# ── NPCI Webhooks log ─────────────────────────────────────────────────────────
webhooks_table = Table(
    "npci_webhooks",
    metadata,
    Column("id",             Integer,  primary_key=True, autoincrement=True),
    Column("received_at",    DateTime, default=datetime.now),
    Column("transaction_ref",String(50)),
    Column("payload",        Text),
    Column("processed",      Boolean, default=False),
)

# Customer messages are persisted so a demo conversation survives page refreshes.
conversation_messages_table = Table(
    "conversation_messages",
    metadata,
    Column("id",             Integer,    primary_key=True, autoincrement=True),
    Column("customer_id",    String(50), nullable=False),
    Column("transaction_id", String(50), nullable=True),
    Column("role",           String(20), nullable=False),
    Column("content",        Text,       nullable=False),
    Column("created_at",     String(50), nullable=False),
)

# Demo customer directory, transaction-linked refunds, support tickets, and persistent workforce tasks.
customers_table = Table(
    "customers", metadata,
    Column("customer_id", String(50), primary_key=True),
    Column("name", String(100), nullable=False),
    Column("email", String(255), unique=True, nullable=False),
    Column("phone", String(30)),
    Column("account_status", String(30), default="ACTIVE"),
    Column("verification_status", String(30), default="VERIFIED"),
    Column("created_at", String(50), nullable=False),
)

refunds_table = Table(
    "refunds", metadata,
    Column("refund_id", String(60), primary_key=True),
    Column("idempotency_key", String(128), unique=True, nullable=False),
    Column("transaction_id", String(50), nullable=False, unique=True, index=True),
    Column("customer_id", String(50), nullable=False),
    Column("amount", Float, nullable=False),
    Column("reason", Text, nullable=False),
    Column("status", String(30), nullable=False),
    Column("action_ref", String(100)),
    Column("created_at", String(50), nullable=False),
    Column("completed_at", String(50)),
)

support_tickets_table = Table(
    "support_tickets", metadata,
    Column("ticket_id", String(60), primary_key=True),
    Column("case_id", String(50), nullable=True),
    Column("customer_id", String(50), nullable=False),
    Column("category", String(50), nullable=False),
    Column("priority", String(20), nullable=False),
    Column("status", String(30), nullable=False),
    Column("assigned_team", String(80), nullable=False),
    Column("summary", Text, nullable=False),
    Column("created_at", String(50), nullable=False),
    Column("resolved_at", String(50)),
)

workforce_tasks_table = Table(
    "workforce_tasks", metadata,
    Column("task_id", String(80), primary_key=True),
    Column("domain", String(40), nullable=False),
    Column("status", String(40), nullable=False),
    Column("payload", Text, nullable=False),
    Column("updated_at", String(50), nullable=False),
)

# Department work records; payloads keep the demo extensible while indexed fields
# support safe, direct queries without exposing arbitrary SQL to agents.
departments_table = Table("departments", metadata,
    Column("department_id", String(40), primary_key=True), Column("name", String(100), nullable=False),
    Column("manager", String(100), nullable=False), Column("description", Text, nullable=False))
employees_table = Table("employees", metadata,
    Column("employee_id", String(60), primary_key=True), Column("name", String(100), nullable=False),
    Column("email", String(255), unique=True, nullable=False), Column("department_id", String(40), nullable=False),
    Column("role", String(100), nullable=False), Column("status", String(30), nullable=False),
    Column("manager_id", String(60)), Column("created_at", String(50), nullable=False), Column("payload", Text, nullable=False))
expenses_table = Table("expenses", metadata,
    Column("expense_id", String(60), primary_key=True), Column("employee_id", String(60), nullable=False),
    Column("category", String(60), nullable=False), Column("amount", Float, nullable=False), Column("currency", String(10), nullable=False),
    Column("status", String(40), nullable=False), Column("submitted_at", String(50), nullable=False), Column("payload", Text, nullable=False))
leave_requests_table = Table("leave_requests", metadata,
    Column("request_id", String(60), primary_key=True), Column("employee_id", String(60), nullable=False),
    Column("start_date", String(20), nullable=False), Column("end_date", String(20), nullable=False),
    Column("days", Integer, nullable=False), Column("status", String(30), nullable=False), Column("payload", Text, nullable=False))
it_tickets_table = Table("it_tickets", metadata,
    Column("ticket_id", String(60), primary_key=True), Column("employee_id", String(60), nullable=False),
    Column("category", String(60), nullable=False), Column("priority", String(20), nullable=False),
    Column("status", String(30), nullable=False), Column("summary", Text, nullable=False),
    Column("created_at", String(50), nullable=False), Column("payload", Text, nullable=False))
access_requests_table = Table("access_requests", metadata,
    Column("request_id", String(60), primary_key=True), Column("employee_id", String(60), nullable=False),
    Column("system_name", String(100), nullable=False), Column("access_level", String(50), nullable=False),
    Column("status", String(40), nullable=False), Column("business_reason", Text, nullable=False),
    Column("created_at", String(50), nullable=False), Column("payload", Text, nullable=False))
onboarding_plans_table = Table("onboarding_plans", metadata,
    Column("plan_id", String(60), primary_key=True), Column("employee_id", String(60), nullable=False),
    Column("department_id", String(40), nullable=False), Column("status", String(30), nullable=False),
    Column("created_at", String(50), nullable=False), Column("payload", Text, nullable=False))
training_modules_table = Table("training_modules", metadata,
    Column("module_id", String(60), primary_key=True), Column("title", String(160), nullable=False),
    Column("department_id", String(40), nullable=False), Column("description", Text, nullable=False))
training_assignments_table = Table("training_assignments", metadata,
    Column("assignment_id", String(60), primary_key=True), Column("employee_id", String(60), nullable=False),
    Column("module_id", String(60), nullable=False), Column("status", String(30), nullable=False),
    Column("assigned_at", String(50), nullable=False), Column("completed_at", String(50)))
knowledge_documents_table = Table("knowledge_documents", metadata,
    Column("document_id", String(60), primary_key=True), Column("title", String(160), nullable=False),
    Column("category", String(60), nullable=False), Column("content", Text, nullable=False), Column("keywords", Text, nullable=False))
tasks_table = Table("tasks", metadata,
    Column("task_id", String(80), primary_key=True), Column("title", String(180), nullable=False),
    Column("description", Text, nullable=False), Column("requester", String(100), nullable=False),
    Column("assigned_agent", String(100), nullable=False), Column("priority", String(20), nullable=False),
    Column("status", String(30), nullable=False), Column("created_at", String(50), nullable=False),
    Column("updated_at", String(50), nullable=False), Column("payload", Text, nullable=False))
audit_logs_table = Table("audit_logs", metadata,
    Column("audit_id", String(80), primary_key=True), Column("timestamp", String(50), nullable=False),
    Column("user_id", String(80), nullable=False), Column("agent", String(80), nullable=False),
    Column("tool", String(100), nullable=False), Column("action", String(100), nullable=False),
    Column("entity_type", String(60), nullable=False), Column("entity_id", String(80)),
    Column("status", String(30), nullable=False), Column("result_summary", Text, nullable=False))
conversations_table = Table("conversations", metadata,
    Column("conversation_id", String(80), primary_key=True), Column("user_id", String(80), nullable=False),
    Column("title", String(200), nullable=False), Column("created_at", String(50), nullable=False),
    Column("channel", String(30), nullable=False, default="employee"))
employee_messages_table = Table("employee_messages", metadata,
    Column("message_id", String(80), primary_key=True), Column("conversation_id", String(80), nullable=False),
    Column("user_id", String(80), nullable=False), Column("role", String(20), nullable=False),
    Column("content", Text, nullable=False), Column("created_at", String(50), nullable=False))
sales_leads_table = Table("sales_leads", metadata,
    Column("lead_id", String(60), primary_key=True), Column("name", String(120), nullable=False),
    Column("company", String(160), nullable=False), Column("email", String(255), nullable=False),
    Column("stage", String(40), nullable=False), Column("score", Integer, nullable=False),
    Column("consent_status", String(30), nullable=False), Column("created_at", String(50), nullable=False),
    Column("payload", Text, nullable=False))
campaigns_table = Table("campaigns", metadata,
    Column("campaign_id", String(60), primary_key=True), Column("name", String(180), nullable=False),
    Column("channel", String(50), nullable=False), Column("status", String(40), nullable=False),
    Column("audience", String(100), nullable=False), Column("impressions", Integer, nullable=False),
    Column("clicks", Integer, nullable=False), Column("conversions", Integer, nullable=False),
    Column("spend", Float, nullable=False), Column("revenue", Float, nullable=False),
    Column("created_at", String(50), nullable=False), Column("payload", Text, nullable=False))


def case_id_for_tx(tx_id: str) -> str:
    """Generate a clean canonical case ID: e.g. TX9281 -> ZT-09281"""
    import re
    digits = re.findall(r"\d+", tx_id)
    if digits:
        num = digits[-1].zfill(5)
        return f"ZT-{num}"
    return f"ZT-{tx_id}"



def init_db():
    """Create all tables if they don't already exist and run safe migrations."""
    metadata.create_all(engine)
    _migrate_schema()
    _seed_customers()
    _seed_department_directory()
    _seed_training_and_knowledge()
    _seed_transactions()
    _seed_enterprise_records()
    _seed_workforce_tasks()


def _seed_customers():
    from backend.enterprise_data import CUSTOMERS
    now = datetime.now(timezone.utc).isoformat()
    with engine.begin() as conn:
        for index, (customer_id, name, email) in enumerate(CUSTOMERS, start=1):
            if not conn.execute(customers_table.select().where(customers_table.c.customer_id == customer_id)).first():
                conn.execute(customers_table.insert().values(customer_id=customer_id, name=name, email=email,
                    phone=f"+91 90000 {10000 + index:05d}", account_status="ACTIVE",
                    verification_status="VERIFIED", created_at=now))


def _seed_department_directory():
    from backend.enterprise_data import DEPARTMENTS, EMPLOYEE_NAMES
    now = datetime.now(timezone.utc).isoformat()
    with engine.begin() as conn:
        for item in DEPARTMENTS:
            if not conn.execute(departments_table.select().where(departments_table.c.department_id == item["department_id"])).first():
                conn.execute(departments_table.insert().values(**item))
        for employee_id, name, email, department_id in EMPLOYEE_NAMES:
            if conn.execute(employees_table.select().where(employees_table.c.employee_id == employee_id)).first():
                continue
            role = "Department Manager" if employee_id in {"emp-meera", "emp-nisha", "emp-dev", "emp-ishita", "emp-kabir", "emp-tara", "emp-rajesh"} else "Associate"
            status = "PREBOARDING" if employee_id == "emp-rahul" else "ACTIVE"
            payload = {"employee_id": employee_id, "name": name, "email": email, "department_id": department_id,
                       "role": role, "status": status, "manager_id": f"emp-{department_id}", "created_at": now}
            conn.execute(employees_table.insert().values(employee_id=employee_id, name=name, email=email,
                department_id=department_id, role=role, status=status, manager_id=payload["manager_id"],
                created_at=now, payload=json.dumps(payload)))


def _seed_training_and_knowledge():
    from backend.enterprise_data import TRAINING_MODULES, KNOWLEDGE_DOCUMENTS
    with engine.begin() as conn:
        for module_id, title, department_id, description in TRAINING_MODULES:
            if not conn.execute(training_modules_table.select().where(training_modules_table.c.module_id == module_id)).first():
                conn.execute(training_modules_table.insert().values(module_id=module_id, title=title,
                    department_id=department_id, description=description))
        for document_id, title, category, content in KNOWLEDGE_DOCUMENTS:
            if not conn.execute(knowledge_documents_table.select().where(knowledge_documents_table.c.document_id == document_id)).first():
                keywords = " ".join(sorted(set((title + " " + category + " " + content).lower().split())))
                conn.execute(knowledge_documents_table.insert().values(document_id=document_id, title=title,
                    category=category, content=content, keywords=keywords))


def _extended_demo_transactions():
    from backend.enterprise_data import CUSTOMERS
    rows = []
    customers = [row[0:2] for row in CUSTOMERS]
    for index in range(50):
        customer_id, customer_name = customers[(index + 1) % len(customers)]
        amount = float(1800 + (index * 675) % 24500)
        mode = index % 5
        if mode == 0:
            bank, network, merchant, settlement, status = "FAILED", "FAILED", "NOT_CREDITED", "NOT_FOUND", "PENDING"
        elif mode == 1:
            bank, network, merchant, settlement, status = "DEBITED", "SUCCESS", "CREDITED", "SETTLED", "RESOLVED"
        elif mode == 2:
            bank, network, merchant, settlement, status = "PENDING", "UNKNOWN", "PENDING_CREDIT", "PENDING", "PENDING"
        elif mode == 3:
            bank, network, merchant, settlement, status = "DEBITED", "SUCCESS", "NOT_CREDITED", "NOT_FOUND", "PENDING"
        else:
            bank, network, merchant, settlement, status = "DEBITED", "SUCCESS", "NOT_CREDITED", "NOT_FOUND", "PENDING"
        rows.append({
            "transaction_id": f"TX{10000 + index}", "customer_id": customer_id, "customer_name": customer_name,
            "amount": amount, "currency": "INR", "bank_status": bank, "network_status": network,
            "merchant_status": merchant, "settlement_status": settlement,
            "risk_score": 0.08 if mode == 4 else round(((index * 7) % 45) / 100, 2),
            "previous_refund": False, "cibil_score": 700 + (index * 13) % 180,
            "is_first_time_user": index % 9 == 0, "dynamic_message": None, "action_id": None,
            "resolution_status": status, "workflow_type": "W1",
            "created_at": datetime.now(timezone.utc).replace(tzinfo=None),
        })
    return rows


def _seed_enterprise_records():
    from backend.enterprise_data import CUSTOMERS, EMPLOYEE_NAMES
    now = datetime.now(timezone.utc).isoformat()
    with engine.begin() as conn:
        if conn.execute(select(func.count()).select_from(sales_leads_table)).scalar_one() == 0:
            for index in range(12):
                lead = {"lead_id": f"LEAD-DEMO-{index + 1:03d}", "name": ["Aditi Mehra", "Rohit Bansal", "Sana Merchant", "Karan Shah"][index % 4],
                        "company": ["Northstar Retail", "BluePeak Logistics", "Cedar Finance", "Riverstone Foods"][index % 4],
                        "email": f"partner{index + 1}@example.demo", "stage": ["NEW", "CONTACTED", "QUALIFIED", "DISCOVERY"][index % 4],
                        "score": 58 + (index * 7) % 41, "consent_status": "OPTED_IN" if index % 5 != 0 else "NOT_CONTACTABLE", "created_at": now}
                conn.execute(sales_leads_table.insert().values(**lead, payload=json.dumps(lead)))
        if conn.execute(select(func.count()).select_from(campaigns_table)).scalar_one() == 0:
            for index in range(10):
                campaign = {"campaign_id": f"CMP-DEMO-{index + 1:03d}", "name": ["Monsoon Rewards", "Merchant Growth", "UPI Safety Week", "Festive Wallet Offers", "Small Business Spotlight"][index % 5],
                            "channel": ["EMAIL", "IN_APP", "SMS", "WEB"][index % 4], "status": "ACTIVE" if index % 3 else "COMPLETED",
                            "audience": ["New users", "Active merchants", "Small businesses"][index % 3],
                            "impressions": 12000 + index * 1750, "clicks": 850 + index * 125,
                            "conversions": 105 + index * 18, "spend": float(18000 + index * 4200),
                            "revenue": float(43000 + index * 9100), "created_at": now}
                conn.execute(campaigns_table.insert().values(**campaign, payload=json.dumps(campaign)))
        if conn.execute(text("SELECT COUNT(*) FROM support_tickets")).scalar() == 0:
            for index in range(20):
                tx_id = f"TX{10000 + index}"
                case_id = case_id_for_tx(tx_id)
                customer_id = conn.execute(cases_table.select().with_only_columns(cases_table.c.customer_id).where(cases_table.c.transaction_id == tx_id)).scalar_one()
                status = "OPEN" if index % 4 else "RESOLVED"
                conn.execute(support_tickets_table.insert().values(ticket_id=f"TKT-DEMO-{index + 1:03d}",
                    case_id=case_id, customer_id=customer_id, category="PAYMENT" if index % 2 else "REFUND",
                    priority=("HIGH" if index % 3 == 0 else "NORMAL"), status=status, assigned_team="Payment Support",
                    summary=f"Customer reported a {'failed payment' if index % 2 else 'refund status'} issue for {tx_id}.",
                    created_at=now, resolved_at=now if status == "RESOLVED" else None))
        if conn.execute(text("SELECT COUNT(*) FROM refunds")).scalar() == 0:
            for index in range(10):
                tx_id = f"TX{10004 + index * 5}"
                case = conn.execute(cases_table.select().where(cases_table.c.transaction_id == tx_id)).mappings().first()
                tx = conn.execute(transactions_table.select().where(transactions_table.c.transaction_id == tx_id)).mappings().first()
                if not case or not tx:
                    continue
                status = "VERIFIED" if index < 7 else "PROCESSING" if index < 9 else "FAILED"
                conn.execute(refunds_table.insert().values(refund_id=f"RFD-DEMO-{index + 1:03d}",
                    idempotency_key=f"demo-seed:{tx_id}:refund-v1", transaction_id=tx_id,
                    customer_id=case["customer_id"], amount=tx["amount"], reason="Seeded demo refund record",
                    status=status, action_ref=f"DEMO-REV-{tx_id}", created_at=now,
                    completed_at=now if status == "VERIFIED" else None))
                conn.execute(transactions_table.update().where(transactions_table.c.transaction_id == tx_id)
                             .values(previous_refund=True, resolution_status="RESOLVED" if status == "VERIFIED" else "PENDING"))
        if conn.execute(text("SELECT COUNT(*) FROM expenses")).scalar() == 0:
            for index in range(15):
                employee_id = f"emp-{['meera','neha','aman','rahul','tanya'][index % 5]}"
                payload = {"expense_id": f"EXP-DEMO-{index + 1:03d}", "employee_id": employee_id,
                           "category": ["TRAVEL", "MEALS", "EQUIPMENT"][index % 3], "amount": float(1200 + index * 850),
                           "currency": "INR", "status": "APPROVED" if index % 3 == 0 else "SUBMITTED",
                           "submitted_at": now, "business_purpose": "Customer and partner operations", "receipt_attached": True}
                conn.execute(expenses_table.insert().values(expense_id=payload["expense_id"], employee_id=employee_id,
                    category=payload["category"], amount=payload["amount"], currency="INR", status=payload["status"],
                    submitted_at=now, payload=json.dumps(payload)))
        if conn.execute(text("SELECT COUNT(*) FROM leave_requests")).scalar() == 0:
            for index in range(15):
                employee_id = EMPLOYEE_NAMES[index % len(EMPLOYEE_NAMES)][0]
                status = "APPROVED" if index % 3 == 0 else "PENDING" if index % 3 == 1 else "REJECTED"
                payload = {"request_id": f"LV-DEMO-{index + 1:03d}", "employee_id": employee_id,
                           "start_date": f"2026-11-{index + 1:02d}", "end_date": f"2026-11-{index + 1:02d}",
                           "days": 1, "status": status, "reason": "Personal leave"}
                conn.execute(leave_requests_table.insert().values(request_id=payload["request_id"], employee_id=employee_id,
                    start_date=payload["start_date"], end_date=payload["end_date"], days=1, status=status, payload=json.dumps(payload)))
        if conn.execute(text("SELECT COUNT(*) FROM it_tickets")).scalar() == 0:
            for index in range(12):
                employee_id = EMPLOYEE_NAMES[index][0]
                status = "OPEN" if index % 3 else "RESOLVED"
                payload = {"ticket_id": f"IT-DEMO-{index + 1:03d}", "employee_id": employee_id,
                           "category": ["DEVICE", "SOFTWARE", "ACCESS"][index % 3],
                           "priority": "HIGH" if index % 4 == 0 else "NORMAL", "status": status,
                           "summary": f"{['Laptop setup', 'Software access', 'VPN support'][index % 3]} request"}
                conn.execute(it_tickets_table.insert().values(ticket_id=payload["ticket_id"], employee_id=employee_id,
                    category=payload["category"], priority=payload["priority"], status=status,
                    summary=payload["summary"], created_at=now, payload=json.dumps(payload)))
        if conn.execute(text("SELECT COUNT(*) FROM access_requests")).scalar() == 0:
            for index in range(12):
                employee_id = EMPLOYEE_NAMES[index][0]
                payload = {"request_id": f"AR-DEMO-{index + 1:03d}", "employee_id": employee_id,
                           "system_name": ["Expense Platform", "Core Ledger Read-Only", "Analytics Workspace"][index % 3],
                           "access_level": "READ_ONLY", "status": "PENDING_APPROVAL" if index % 4 == 0 else "APPROVED",
                           "business_reason": "Role-based business access"}
                conn.execute(access_requests_table.insert().values(request_id=payload["request_id"], employee_id=employee_id,
                    system_name=payload["system_name"], access_level=payload["access_level"], status=payload["status"],
                    business_reason=payload["business_reason"], created_at=now, payload=json.dumps(payload)))
        if conn.execute(text("SELECT COUNT(*) FROM onboarding_plans")).scalar() == 0:
            for index in range(10):
                employee_id = EMPLOYEE_NAMES[index + 8][0]
                payload = {"plan_id": f"ONB-DEMO-{index + 1:03d}", "employee_id": employee_id,
                           "department_id": EMPLOYEE_NAMES[index + 8][3], "status": "IN_PROGRESS" if index % 3 else "COMPLETED",
                           "steps": ["HR profile", "Department training", "IT access request", "Policy reading", "Manager update"]}
                conn.execute(onboarding_plans_table.insert().values(plan_id=payload["plan_id"], employee_id=employee_id,
                    department_id=payload["department_id"], status=payload["status"], created_at=now, payload=json.dumps(payload)))
        if conn.execute(text("SELECT COUNT(*) FROM training_assignments")).scalar() == 0:
            modules = conn.execute(training_modules_table.select()).mappings().all()
            for index in range(24):
                employee_id = EMPLOYEE_NAMES[index % len(EMPLOYEE_NAMES)][0]
                module = modules[index % len(modules)]
                status = "COMPLETED" if index % 4 == 0 else "ASSIGNED"
                conn.execute(training_assignments_table.insert().values(assignment_id=f"TA-DEMO-{index + 1:03d}",
                    employee_id=employee_id, module_id=module["module_id"], status=status,
                    assigned_at=now, completed_at=now if status == "COMPLETED" else None))
        if conn.execute(text("SELECT COUNT(*) FROM tasks")).scalar() == 0:
            for index in range(16):
                payload = {"task_id": f"TASK-DEMO-{index + 1:03d}", "title": ["Review payment exception", "Complete onboarding checklist", "Confirm least-privilege access"][index % 3],
                           "description": "Seeded cross-department work item", "requester": "ZeroTouch Demo",
                           "assigned_agent": ["Finance Agent", "HR Agent", "IT Agent", "Operations Agent"][index % 4],
                           "priority": "HIGH" if index % 5 == 0 else "NORMAL", "status": "COMPLETED" if index % 3 == 0 else "OPEN",
                           "created_at": now, "updated_at": now}
                conn.execute(tasks_table.insert().values(task_id=payload["task_id"], title=payload["title"],
                    description=payload["description"], requester=payload["requester"], assigned_agent=payload["assigned_agent"],
                    priority=payload["priority"], status=payload["status"], created_at=now, updated_at=now, payload=json.dumps(payload)))
        if conn.execute(text("SELECT COUNT(*) FROM conversations")).scalar() == 0:
            for index, (customer_id, name, _email) in enumerate(CUSTOMERS):
                conn.execute(conversations_table.insert().values(conversation_id=f"CONV-DEMO-{index + 1:03d}",
                    user_id=customer_id, title=f"Payment and account support for {name}", created_at=now, channel="customer"))
        if conn.execute(text("SELECT COUNT(*) FROM audit_logs")).scalar() == 0:
            for index in range(30):
                conn.execute(audit_logs_table.insert().values(audit_id=f"AUDIT-DEMO-{index + 1:03d}", timestamp=now,
                    user_id="system-seed", agent=["HR Agent", "IT Agent", "Finance Agent", "Support Agent"][index % 4],
                    tool=["assign_training", "create_access_request", "get_transaction", "create_ticket"][index % 4],
                    action="SEED_RECORD", entity_type="demo", entity_id=f"DEMO-{index + 1:03d}", status="SUCCESS",
                    result_summary="Seeded audit example; no external action was performed."))


def _seed_workforce_tasks():
    from backend.workforce_data import ORIGINAL_WORKFORCE_CASES
    now = datetime.now(timezone.utc).isoformat()
    with engine.begin() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM workforce_tasks")).scalar()
        if count:
            return
        for task in ORIGINAL_WORKFORCE_CASES:
            task_data = dict(task)
            task_data.setdefault("audit_log", [{"timestamp": now, "actor": "ZeroTouch", "action": "SEEDED", "status": task_data.get("status", "PREPARED")}])
            conn.execute(workforce_tasks_table.insert().values(
                task_id=task_data["case_id"], domain=task_data.get("domain", "support"),
                status=task_data.get("status", "QUEUED"), payload=json.dumps(task_data), updated_at=now))


def _migrate_schema():
    """Add columns if missing in existing SQLite database."""
    try:
        insp = inspect(engine)
        columns = [c["name"] for c in insp.get_columns("audit_events")]
        with engine.begin() as conn:
            if "visibility" not in columns:
                conn.execute(text("ALTER TABLE audit_events ADD COLUMN visibility VARCHAR(20) DEFAULT 'INTERNAL'"))
            if "actor" not in columns:
                conn.execute(text("ALTER TABLE audit_events ADD COLUMN actor VARCHAR(100) DEFAULT 'ZeroTouch Agent'"))
    except Exception as e:
        # Table might be freshly created or engine doesn't need ALTER
        pass


def _seed_transactions():
    """Insert original and extended fictional transactions and link each to its owner."""
    from backend.data import ORIGINAL_TRANSACTIONS
    all_rows = list(ORIGINAL_TRANSACTIONS.values()) + _extended_demo_transactions()
    ts = datetime.now(timezone.utc).isoformat()
    with engine.begin() as conn:
        for source in all_rows:
            tx = dict(source)
            customer_id = tx.pop("customer_id", "cust-ayush")
            tx_id = tx["transaction_id"]
            exists = conn.execute(transactions_table.select().where(transactions_table.c.transaction_id == tx_id)).first()
            if not exists:
                tx.pop("customer_id", None)
                conn.execute(transactions_table.insert().values(**tx))
            cid = case_id_for_tx(tx_id)
            case_exists = conn.execute(
                cases_table.select().where(cases_table.c.case_id == cid)
            ).first()
            if not case_exists:
                case_row = {
                    "case_id": cid,
                    "transaction_id": tx_id,
                    "customer_id": customer_id,
                    "customer_name": tx.get("customer_name", "Paytm User"),
                    "workflow_type": tx.get("workflow_type", "W1"),
                    "classification": "PENDING_INVESTIGATION",
                    "amount": tx["amount"],
                    "currency": tx.get("currency", "INR"),
                    "evidence_matrix": None,
                    "risk_assessment": None,
                    "policy_decision": None,
                    "action_record": None,
                    "customer_status": "INVESTIGATING",
                    "ops_status": tx.get("resolution_status", "PENDING"),
                    "human_review_notes": None,
                    "assigned_agent": None,
                    "dynamic_message": None,
                    "created_at": ts,
                    "updated_at": ts,
                }
                conn.execute(cases_table.insert().values(**case_row))



# ── Canonical Case CRUD ───────────────────────────────────────────────────────

def db_get_case(case_id: str) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(
            cases_table.select().where(cases_table.c.case_id == case_id)
        ).mappings().first()
        return dict(row) if row else None


def db_get_case_by_tx(tx_id: str) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(
            cases_table.select().where(cases_table.c.transaction_id == tx_id)
        ).mappings().first()
        if not row:
            # Fallback check by calculated case_id
            cid = case_id_for_tx(tx_id)
            row = conn.execute(
                cases_table.select().where(cases_table.c.case_id == cid)
            ).mappings().first()
        return dict(row) if row else None


def db_get_all_cases() -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(cases_table.select()).mappings().all()
        return [dict(r) for r in rows]


def db_upsert_case(case_dict: dict) -> dict:
    case_id = case_dict["case_id"]
    ts = datetime.now(timezone.utc).isoformat()
    case_dict["updated_at"] = ts
    with engine.begin() as conn:
        existing = conn.execute(
            cases_table.select().where(cases_table.c.case_id == case_id)
        ).mappings().first()
        if existing:
            conn.execute(
                cases_table.update()
                .where(cases_table.c.case_id == case_id)
                .values(**case_dict)
            )
        else:
            if "created_at" not in case_dict:
                case_dict["created_at"] = ts
            conn.execute(cases_table.insert().values(**case_dict))
    return case_dict


def db_update_case(case_id: str, **kwargs):
    kwargs["updated_at"] = datetime.now(timezone.utc).isoformat()
    with engine.begin() as conn:
        conn.execute(
            cases_table.update()
            .where(cases_table.c.case_id == case_id)
            .values(**kwargs)
        )


def db_update_case_by_tx(tx_id: str, **kwargs):
    case = db_get_case_by_tx(tx_id)
    if case:
        db_update_case(case["case_id"], **kwargs)


# ── Action Gateway Log CRUD (Idempotency) ─────────────────────────────────────

def db_get_action_log(idempotency_key: str) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(
            action_gateway_log_table.select().where(
                action_gateway_log_table.c.idempotency_key == idempotency_key
            )
        ).mappings().first()
        return dict(row) if row else None


def db_get_action_by_tx(tx_id: str) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(
            action_gateway_log_table.select()
            .where(action_gateway_log_table.c.transaction_id == tx_id)
            .order_by(action_gateway_log_table.c.id.desc())
        ).mappings().first()
        return dict(row) if row else None


def db_record_action_gateway(
    idempotency_key: str,
    case_id: str,
    tx_id: str,
    action_type: str,
    action_ref: str,
    status: str,
    payload: dict | None = None,
    result: dict | None = None,
    is_simulated: bool = True,
) -> dict:
    ts = datetime.now(timezone.utc).isoformat()
    record = {
        "idempotency_key": idempotency_key,
        "case_id": case_id,
        "transaction_id": tx_id,
        "action_type": action_type,
        "action_ref": action_ref,
        "status": status,
        "is_simulated": is_simulated,
        "payload": json.dumps(payload or {}),
        "result": json.dumps(result or {}),
        "created_at": ts,
        "verified_at": ts if status == "VERIFIED" else None,
    }
    with engine.begin() as conn:
        conn.execute(action_gateway_log_table.insert().values(**record))
    return record


def db_update_action_gateway(idempotency_key: str, **kwargs):
    if "result" in kwargs and isinstance(kwargs["result"], dict):
        kwargs["result"] = json.dumps(kwargs["result"])
    with engine.begin() as conn:
        conn.execute(
            action_gateway_log_table.update()
            .where(action_gateway_log_table.c.idempotency_key == idempotency_key)
            .values(**kwargs)
        )


# ── Transactions CRUD ─────────────────────────────────────────────────────────

def db_get_transaction(tx_id: str) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(
            transactions_table.select().where(
                transactions_table.c.transaction_id == tx_id
            )
        ).mappings().first()
        return dict(row) if row else None


def db_get_all_transactions() -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(
            transactions_table.select()
        ).mappings().all()
        return [dict(r) for r in rows]


def db_update_transaction(tx_id: str, **kwargs):
    with engine.begin() as conn:
        conn.execute(
            transactions_table.update()
            .where(transactions_table.c.transaction_id == tx_id)
            .values(**kwargs)
        )


# ── Audit Events CRUD ─────────────────────────────────────────────────────────

def db_add_event(
    tx_id: str,
    event_type: str,
    step: str,
    status: str,
    message: str,
    visibility: str = "INTERNAL",
    actor: str = "ZeroTouch Agent"
) -> dict:
    ts = datetime.now(timezone.utc).isoformat()
    event = {
        "transaction_id": tx_id,
        "timestamp": ts,
        "type": event_type,
        "step": step,
        "status": status,
        "message": message,
        "visibility": visibility,
        "actor": actor,
    }
    with engine.begin() as conn:
        conn.execute(audit_events_table.insert().values(**event))
    return event


def db_get_events(tx_id: str, visibility: str | None = None) -> list[dict]:
    with engine.connect() as conn:
        query = audit_events_table.select().where(audit_events_table.c.transaction_id == tx_id)
        if visibility:
            query = query.where(audit_events_table.c.visibility == visibility)
        rows = conn.execute(query.order_by(audit_events_table.c.id)).mappings().all()
        return [dict(r) for r in rows]


def db_reset_all():
    """Restore transaction, refund, ticket, conversation, and workforce demo state."""
    with engine.begin() as conn:
        conn.execute(audit_events_table.delete())
        conn.execute(conversation_messages_table.delete())
        conn.execute(action_gateway_log_table.delete())
        conn.execute(refunds_table.delete())
        conn.execute(support_tickets_table.delete())
        conn.execute(workforce_tasks_table.delete())
        conn.execute(tasks_table.delete())
        conn.execute(audit_logs_table.delete())
        conn.execute(employee_messages_table.delete())
        conn.execute(conversations_table.delete())
        conn.execute(expenses_table.delete())
        conn.execute(leave_requests_table.delete())
        conn.execute(it_tickets_table.delete())
        conn.execute(access_requests_table.delete())
        conn.execute(onboarding_plans_table.delete())
        conn.execute(training_assignments_table.delete())
        conn.execute(sales_leads_table.delete())
        conn.execute(campaigns_table.delete())
        conn.execute(employees_table.delete())
        conn.execute(cases_table.delete())
        conn.execute(transactions_table.delete())
    _seed_department_directory()
    _seed_transactions()
    _seed_enterprise_records()
    _seed_workforce_tasks()


def db_get_customers() -> list[dict]:
    with engine.connect() as conn:
        return [dict(row) for row in conn.execute(customers_table.select().order_by(customers_table.c.name)).mappings().all()]


def db_get_customer(customer_id: str) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(customers_table.select().where(customers_table.c.customer_id == customer_id)).mappings().first()
        return dict(row) if row else None


def db_get_customer_by_email(email: str) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(customers_table.select().where(customers_table.c.email == email.lower())).mappings().first()
        return dict(row) if row else None


def db_get_employee_by_email(email: str) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(employees_table.select().where(employees_table.c.email == email.lower())).mappings().first()
        return dict(row) if row else None


def db_get_refund(refund_id: str) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(refunds_table.select().where(refunds_table.c.refund_id == refund_id)).mappings().first()
        return dict(row) if row else None


def db_get_refund_by_idempotency(key: str) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(refunds_table.select().where(refunds_table.c.idempotency_key == key)).mappings().first()
        return dict(row) if row else None


def db_get_refund_by_transaction(transaction_id: str) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(refunds_table.select().where(refunds_table.c.transaction_id == transaction_id)
                           .order_by(refunds_table.c.created_at.desc())).mappings().first()
        return dict(row) if row else None


def db_get_refunds(customer_id: str | None = None) -> list[dict]:
    with engine.connect() as conn:
        query = refunds_table.select()
        if customer_id:
            query = query.where(refunds_table.c.customer_id == customer_id)
        rows = conn.execute(query.order_by(refunds_table.c.created_at.desc())).mappings().all()
        return [dict(row) for row in rows]


def db_create_refund(refund: dict) -> dict:
    with engine.begin() as conn:
        conn.execute(refunds_table.insert().values(**refund))
    return refund


def db_update_refund(refund_id: str, **values):
    with engine.begin() as conn:
        conn.execute(refunds_table.update().where(refunds_table.c.refund_id == refund_id).values(**values))


def db_get_tickets(customer_id: str | None = None) -> list[dict]:
    with engine.connect() as conn:
        query = support_tickets_table.select()
        if customer_id:
            query = query.where(support_tickets_table.c.customer_id == customer_id)
        return [dict(row) for row in conn.execute(query.order_by(support_tickets_table.c.created_at.desc())).mappings().all()]


def db_create_ticket(ticket: dict) -> dict:
    with engine.begin() as conn:
        conn.execute(support_tickets_table.insert().values(**ticket))
    return ticket


def db_get_ticket(ticket_id: str) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(support_tickets_table.select().where(support_tickets_table.c.ticket_id == ticket_id)).mappings().first()
        return dict(row) if row else None


def db_get_ticket_by_case(case_id: str) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(support_tickets_table.select().where(support_tickets_table.c.case_id == case_id)
                           .order_by(support_tickets_table.c.created_at.desc())).mappings().first()
        return dict(row) if row else None


def db_update_ticket(ticket_id: str, **values):
    with engine.begin() as conn:
        conn.execute(support_tickets_table.update().where(support_tickets_table.c.ticket_id == ticket_id).values(**values))


def db_get_workforce_tasks() -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(workforce_tasks_table.select().order_by(workforce_tasks_table.c.updated_at)).mappings().all()
        return [json.loads(row["payload"]) for row in rows]


def db_upsert_workforce_task(task: dict) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    task["updated_at"] = now
    with engine.begin() as conn:
        exists = conn.execute(workforce_tasks_table.select().where(workforce_tasks_table.c.task_id == task["case_id"])).first()
        values = {"domain": task.get("domain", "support"), "status": task.get("status", "QUEUED"),
                  "payload": json.dumps(task), "updated_at": now}
        if exists:
            conn.execute(workforce_tasks_table.update().where(workforce_tasks_table.c.task_id == task["case_id"]).values(**values))
        else:
            conn.execute(workforce_tasks_table.insert().values(task_id=task["case_id"], **values))
    return task


def db_reset_workforce_tasks():
    with engine.begin() as conn:
        conn.execute(workforce_tasks_table.delete())
    _seed_workforce_tasks()


# ── NPCI Webhooks ─────────────────────────────────────────────────────────────

def db_log_webhook(tx_ref: str, payload: str):
    with engine.begin() as conn:
        conn.execute(webhooks_table.insert().values(
            transaction_ref=tx_ref,
            payload=payload,
            received_at=datetime.now(timezone.utc),
            processed=False,
        ))


def db_mark_webhook_processed(tx_ref: str):
    with engine.begin() as conn:
        conn.execute(
            webhooks_table.update()
            .where(webhooks_table.c.transaction_ref == tx_ref)
            .values(processed=True)
        )


# ── Messages ──────────────────────────────────────────────────────────────────

def db_add_message(customer_id: str, role: str, content: str, transaction_id: str | None = None):
    ts = datetime.now(timezone.utc).isoformat()
    with engine.begin() as conn:
        result = conn.execute(conversation_messages_table.insert().values(
            customer_id=customer_id, role=role, content=content,
            transaction_id=transaction_id, created_at=ts,
        ))
        return {
            "id": result.inserted_primary_key[0],
            "customer_id": customer_id,
            "transaction_id": transaction_id,
            "role": role,
            "content": content,
            "created_at": ts,
        }


def db_get_messages(customer_id: str):
    with engine.connect() as conn:
        rows = conn.execute(
            conversation_messages_table.select()
            .where(conversation_messages_table.c.customer_id == customer_id)
            .order_by(conversation_messages_table.c.id)
        ).mappings().all()
        return [dict(row) for row in rows]


def db_get_messages_for_transaction(transaction_id: str):
    """Return the persisted conversation attached to one transaction-backed case."""
    with engine.connect() as conn:
        rows = conn.execute(
            conversation_messages_table.select()
            .where(conversation_messages_table.c.transaction_id == transaction_id)
            .order_by(conversation_messages_table.c.id)
        ).mappings().all()
        return [dict(row) for row in rows]
