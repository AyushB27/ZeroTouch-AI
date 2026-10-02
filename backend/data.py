"""
Seed data for the ZeroTouch demo.
Includes customer names, CIBIL credit scores, and first-time user flags.
"""
import copy

ORIGINAL_TRANSACTIONS = {
    # ── Workflow 1: Failed / Stuck Payment ──────────────────────────────────
    "TX9281": {
        "transaction_id": "TX9281",
        "customer_name": "Aarav Sharma",
        "amount": 2500.0,
        "currency": "INR",
        "bank_status": "DEBITED",
        "network_status": "SUCCESS",
        "merchant_status": "NOT_CREDITED",
        "settlement_status": "NOT_FOUND",
        "risk_score": 0.08,
        "cibil_score": 785,
        "is_first_time_user": False,
        "previous_refund": False,
        "action_id": None,
        "resolution_status": "PENDING",
        "workflow_type": "W1",
        "dynamic_message": None,
    },
    "TX9342": {
        "transaction_id": "TX9342",
        "customer_name": "Kunal Verma",
        "amount": 18000.0,
        "currency": "INR",
        "bank_status": "DEBITED",
        "network_status": "UNKNOWN",
        "merchant_status": "NOT_CREDITED",
        "settlement_status": "UNKNOWN",
        "risk_score": 0.72,
        "cibil_score": 590,
        "is_first_time_user": True,  # First-Time User attempting high ticket
        "previous_refund": False,
        "action_id": None,
        "resolution_status": "PENDING",
        "workflow_type": "W1",
        "dynamic_message": None,
    },
    "TX9410": {
        "transaction_id": "TX9410",
        "customer_name": "Pooja Nair",
        "amount": 850.0,
        "currency": "INR",
        "bank_status": "DEBITED",
        "network_status": "SUCCESS",
        "merchant_status": "CREDITED",
        "settlement_status": "SETTLED",
        "risk_score": 0.03,
        "cibil_score": 740,
        "is_first_time_user": False,
        "previous_refund": False,
        "action_id": None,
        "resolution_status": "PENDING",
        "workflow_type": "W1",
        "dynamic_message": None,
    },
    # ── Workflow 2: Refund SLA Chasing ──────────────────────────────────────
    "RF202": {
        "transaction_id": "RF202",
        "customer_name": "Vikramaditya Roy",
        "amount": 1800.0,
        "currency": "INR",
        "bank_status": "ACKNOWLEDGED",
        "network_status": "SLA_BREACHED",
        "merchant_status": "REVERSED",
        "settlement_status": "PENDING_CREDIT",
        "risk_score": 0.05,
        "cibil_score": 810,
        "is_first_time_user": False,
        "previous_refund": True,
        "action_id": None,
        "resolution_status": "PENDING",
        "workflow_type": "W2",
        "dynamic_message": None,
    },
    "RF204": {
        "transaction_id": "RF204",
        "customer_name": "Ananya Iyer",
        "amount": 2500.0,
        "currency": "INR",
        "bank_status": "BOUNCED_INVALID_ACCOUNT",
        "network_status": "FAILED_RETURN",
        "merchant_status": "REVERSED",
        "settlement_status": "FAILED",
        "risk_score": 0.10,
        "cibil_score": 765,
        "is_first_time_user": True,  # First-time user: protect with instant Paytm Wallet credit!
        "previous_refund": True,
        "action_id": None,
        "resolution_status": "PENDING",
        "workflow_type": "W2",
        "dynamic_message": None,
    },
    # ── Workflow 3: Merchant Settlement Mismatch ────────────────────────────
    "S302": {
        "transaction_id": "S302",
        "customer_name": "Sharma Electronics (Merchant)",
        "amount": 50000.0,
        "currency": "INR",
        "bank_status": "SETTLED_TO_NODAL",
        "network_status": "SUCCESS",
        "merchant_status": "FEE_DEDUCTION_1000",
        "settlement_status": "PARTIAL_SETTLED_49000",
        "risk_score": 0.02,
        "cibil_score": 820,
        "is_first_time_user": False,
        "previous_refund": False,
        "action_id": None,
        "resolution_status": "PENDING",
        "workflow_type": "W3",
        "dynamic_message": None,
    },
    "S301": {
        "transaction_id": "S301",
        "amount": 10000.0,
        "currency": "INR",
        "bank_status": "SETTLED_TO_NODAL",
        "network_status": "SUCCESS",
        "merchant_status": "FEE_DEDUCTION_300_GST_50",
        "settlement_status": "PARTIAL_SETTLED_9650",
        "risk_score": 0.02,
        "previous_refund": False,
        "action_id": None,
        "resolution_status": "PENDING",
        "workflow_type": "W3",
    },
    "S306": {
        "transaction_id": "S306",
        "customer_name": "QuickBite Cafe (Merchant)",
        "amount": 45000.0,
        "currency": "INR",
        "bank_status": "HELD",
        "network_status": "SUCCESS",
        "merchant_status": "EXPECTING_CREDIT",
        "settlement_status": "HELD_KYC_EXPIRED",
        "risk_score": 0.88,
        "cibil_score": 610,
        "is_first_time_user": False,
        "previous_refund": False,
        "action_id": None,
        "resolution_status": "PENDING",
        "workflow_type": "W3",
        "dynamic_message": None,
    },
}

# Mutable working copy
TRANSACTIONS = copy.deepcopy(ORIGINAL_TRANSACTIONS)
AUDIT_EVENTS: dict = {tx_id: [] for tx_id in ORIGINAL_TRANSACTIONS}


def reset_all():
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
