"""
Database layer – PostgreSQL (primary) with SQLite fallback.

Set DATABASE_URL in your .env to use PostgreSQL:
  DATABASE_URL=postgresql://user:password@localhost:5432/zerotouch

If DATABASE_URL is not set, falls back to a local SQLite file (zerotouch.db).
This means the demo works out-of-the-box with no database server required,
but you can point it at a real PostgreSQL instance for production.
"""

import os
from sqlalchemy import (
    create_engine, Column, String, Float, Boolean, Text,
    DateTime, Integer, MetaData, Table, text
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
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("customer_id", String(50), nullable=False),
    Column("transaction_id", String(50), nullable=True),
    Column("role", String(20), nullable=False),
    Column("content", Text, nullable=False),
    Column("created_at", String(50), nullable=False),
)


def init_db():
    """Create all tables if they don't already exist."""
    metadata.create_all(engine)
    _seed_transactions()


def _seed_transactions():
    """Insert seed data if the transactions table is empty."""
    from backend.data import ORIGINAL_TRANSACTIONS
    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT COUNT(*) FROM transactions")
        ).scalar()
        if existing == 0:
            for tx in ORIGINAL_TRANSACTIONS.values():
                conn.execute(transactions_table.insert().values(**tx))


# ── CRUD helpers ──────────────────────────────────────────────────────────────

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


def db_add_event(tx_id: str, event_type: str, step: str, status: str, message: str) -> dict:
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).isoformat()
    event = {
        "transaction_id": tx_id,
        "timestamp": ts,
        "type": event_type,
        "step": step,
        "status": status,
        "message": message,
    }
    with engine.begin() as conn:
        conn.execute(audit_events_table.insert().values(**event))
    return event


def db_get_events(tx_id: str) -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(
            audit_events_table.select()
            .where(audit_events_table.c.transaction_id == tx_id)
            .order_by(audit_events_table.c.id)
        ).mappings().all()
        return [dict(r) for r in rows]


def db_reset_all():
    """Truncate all tables and re-seed."""
    with engine.begin() as conn:
        conn.execute(audit_events_table.delete())
        conn.execute(conversation_messages_table.delete())
        conn.execute(transactions_table.delete())
    _seed_transactions()


def db_log_webhook(tx_ref: str, payload: str):
    import json
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


def db_add_message(customer_id: str, role: str, content: str, transaction_id: str | None = None):
    ts = datetime.now(timezone.utc).isoformat()
    with engine.begin() as conn:
        result = conn.execute(conversation_messages_table.insert().values(
            customer_id=customer_id, role=role, content=content,
            transaction_id=transaction_id, created_at=ts,
        ))
        return {"id": result.inserted_primary_key[0], "customer_id": customer_id,
                "transaction_id": transaction_id, "role": role, "content": content,
                "created_at": ts}


def db_get_messages(customer_id: str):
    with engine.connect() as conn:
        rows = conn.execute(conversation_messages_table.select()
            .where(conversation_messages_table.c.customer_id == customer_id)
            .order_by(conversation_messages_table.c.id)).mappings().all()
        return [dict(row) for row in rows]


def db_get_messages_for_transaction(transaction_id: str):
    """Return the persisted conversation attached to one transaction-backed case."""
    with engine.connect() as conn:
        rows = conn.execute(conversation_messages_table.select()
            .where(conversation_messages_table.c.transaction_id == transaction_id)
            .order_by(conversation_messages_table.c.id)).mappings().all()
        return [dict(row) for row in rows]
