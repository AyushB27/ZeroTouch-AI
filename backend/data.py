import copy
from datetime import datetime

# Original seed data - never mutate this
ORIGINAL_TRANSACTIONS = {
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
    },
}

# Mutable working copy
TRANSACTIONS = copy.deepcopy(ORIGINAL_TRANSACTIONS)

# Audit event store per transaction
AUDIT_EVENTS: dict = {tx_id: [] for tx_id in ORIGINAL_TRANSACTIONS}


def reset_all():
    fresh = copy.deepcopy(ORIGINAL_TRANSACTIONS)
    TRANSACTIONS.clear()
    TRANSACTIONS.update(fresh)
    AUDIT_EVENTS.clear()
    AUDIT_EVENTS.update({tx_id: [] for tx_id in ORIGINAL_TRANSACTIONS})


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
