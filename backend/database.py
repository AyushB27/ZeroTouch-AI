"""
Database layer – PostgreSQL (primary) with SQLite fallback.
Canonical Case Store, Transactions, Action Gateway Log, and Audit Trail.
"""

import os
import json
from sqlalchemy import (
    create_engine, Column, String, Float, Boolean, Text,
    DateTime, Integer, MetaData, Table, text, inspect
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
    _seed_transactions()
    _seed_customers()
    _seed_workforce_tasks()


def _seed_customers():
    now = datetime.now(timezone.utc).isoformat()
    demo = [
        ("cust-ayush", "Ayush", "ayush@zerotouch.demo", "+91 90000 10001"),
        ("cust-vansh", "Vansh", "vansh@zerotouch.demo", "+91 90000 10002"),
        ("cust-priya", "Priya Shah", "priya@zerotouch.demo", "+91 90000 10003"),
        ("cust-rahul", "Rahul Patil", "rahul@zerotouch.demo", "+91 90000 10004"),
    ]
    with engine.begin() as conn:
        for customer_id, name, email, phone in demo:
            if not conn.execute(customers_table.select().where(customers_table.c.customer_id == customer_id)).first():
                conn.execute(customers_table.insert().values(customer_id=customer_id, name=name, email=email,
                    phone=phone, account_status="ACTIVE", verification_status="VERIFIED", created_at=now))


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
    """Insert seed data if transactions table is empty and ensure cases are initialized."""
    from backend.data import ORIGINAL_TRANSACTIONS
    ts = datetime.now(timezone.utc).isoformat()
    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT COUNT(*) FROM transactions")
        ).scalar()
        if existing == 0:
            for tx in ORIGINAL_TRANSACTIONS.values():
                conn.execute(transactions_table.insert().values(**tx))

        for tx in ORIGINAL_TRANSACTIONS.values():
            tx_id = tx["transaction_id"]
            cid = case_id_for_tx(tx_id)
            case_exists = conn.execute(
                cases_table.select().where(cases_table.c.case_id == cid)
            ).first()
            if not case_exists:
                case_row = {
                    "case_id": cid,
                    "transaction_id": tx_id,
                    "customer_id": "cust-ayush",
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
        conn.execute(cases_table.delete())
        conn.execute(transactions_table.delete())
    _seed_transactions()
    _seed_workforce_tasks()


def db_get_customers() -> list[dict]:
    with engine.connect() as conn:
        return [dict(row) for row in conn.execute(customers_table.select().order_by(customers_table.c.name)).mappings().all()]


def db_get_customer(customer_id: str) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(customers_table.select().where(customers_table.c.customer_id == customer_id)).mappings().first()
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
