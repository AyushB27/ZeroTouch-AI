"""
Seed data for the ZeroTouch demo.

This module is the single source of truth for ORIGINAL_TRANSACTIONS.
The database.py seeder reads from here and inserts rows on first boot.
The in-memory TRANSACTIONS dict is kept for legacy compatibility only
(some older tools still reference it as a fallback).
"""
import copy

ORIGINAL_TRANSACTIONS = {
    # ── Workflow 1: Failed / Stuck Payment ──────────────────────────────────
    "TX9281": {
        "transaction_id": "TX9281",
        "amount": 2500.0,
        "currency": "INR",
        "bank_status": "DEBITED",
        "network_status": "SUCCESS",
        "merchant_status": "NOT_CREDITED",
        "settlement_status": "NOT_FOUND",
        "risk_score": 0.08,
        "previous_refund": False,
        "action_id": None,
        "resolution_status": "PENDING",
        "workflow_type": "W1",
    },
    "TX9342": {
        "transaction_id": "TX9342",
        "amount": 18000.0,
        "currency": "INR",
        "bank_status": "DEBITED",
        "network_status": "UNKNOWN",
        "merchant_status": "NOT_CREDITED",
        "settlement_status": "UNKNOWN",
        "risk_score": 0.72,
        "previous_refund": False,
        "action_id": None,
        "resolution_status": "PENDING",
        "workflow_type": "W1",
    },
    "TX9410": {
        "transaction_id": "TX9410",
        "amount": 850.0,
        "currency": "INR",
        "bank_status": "DEBITED",
        "network_status": "SUCCESS",
        "merchant_status": "CREDITED",
        "settlement_status": "SETTLED",
        "risk_score": 0.03,
        "previous_refund": False,
        "action_id": None,
        "resolution_status": "PENDING",
        "workflow_type": "W1",
    },
    # ── Workflow 2: Refund SLA Chasing ──────────────────────────────────────
    "RF202": {
        "transaction_id": "RF202",
        "amount": 1800.0,
        "currency": "INR",
        "bank_status": "ACKNOWLEDGED",
        "network_status": "SLA_BREACHED",
        "merchant_status": "REVERSED",
        "settlement_status": "PENDING_CREDIT",
        "risk_score": 0.05,
        "previous_refund": True,
        "action_id": None,
        "resolution_status": "PENDING",
        "workflow_type": "W2",
    },
    "RF204": {
        "transaction_id": "RF204",
        "amount": 2500.0,
        "currency": "INR",
        "bank_status": "BOUNCED_INVALID_ACCOUNT",
        "network_status": "FAILED_RETURN",
        "merchant_status": "REVERSED",
        "settlement_status": "FAILED",
        "risk_score": 0.10,
        "previous_refund": True,
        "action_id": None,
        "resolution_status": "PENDING",
        "workflow_type": "W2",
    },
    # ── Workflow 3: Merchant Settlement Mismatch ────────────────────────────
    "S302": {
        "transaction_id": "S302",
        "amount": 50000.0,
        "currency": "INR",
        "bank_status": "SETTLED_TO_NODAL",
        "network_status": "SUCCESS",
        "merchant_status": "FEE_DEDUCTION_1000",
        "settlement_status": "PARTIAL_SETTLED_49000",
        "risk_score": 0.02,
        "previous_refund": False,
        "action_id": None,
        "resolution_status": "PENDING",
        "workflow_type": "W3",
    },
    "S306": {
        "transaction_id": "S306",
        "amount": 45000.0,
        "currency": "INR",
        "bank_status": "HELD",
        "network_status": "SUCCESS",
        "merchant_status": "EXPECTING_CREDIT",
        "settlement_status": "HELD_KYC_EXPIRED",
        "risk_score": 0.88,
        "previous_refund": False,
        "action_id": None,
        "resolution_status": "PENDING",
        "workflow_type": "W3",
    },
}

# Mutable working copy (used by legacy tool imports as fallback)
TRANSACTIONS = copy.deepcopy(ORIGINAL_TRANSACTIONS)
AUDIT_EVENTS: dict = {tx_id: [] for tx_id in ORIGINAL_TRANSACTIONS}


def reset_all():
    """Legacy reset — real reset goes through database.db_reset_all()."""
    global TRANSACTIONS, AUDIT_EVENTS
    TRANSACTIONS = copy.deepcopy(ORIGINAL_TRANSACTIONS)
    AUDIT_EVENTS = {tx_id: [] for tx_id in ORIGINAL_TRANSACTIONS}


def add_event(tx_id: str, event_type: str, step: str, status: str, message: str):
    from datetime import datetime, timezone
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        "step": step,
        "status": status,
        "message": message,
    }
    if tx_id not in AUDIT_EVENTS:
        AUDIT_EVENTS[tx_id] = []
    AUDIT_EVENTS[tx_id].append(event)
    return event
