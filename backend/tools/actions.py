"""
Updated tools/actions.py — now writes to the database instead of in-memory dicts.
"""
from backend.database import db_get_transaction, db_update_transaction


def initiate_reversal(tx_id: str) -> dict:
    tx = db_get_transaction(tx_id)
    if not tx:
        raise ValueError(f"Transaction {tx_id} not found")

    if tx["action_id"]:
        return {"status": "ALREADY_EXECUTED", "action_id": tx["action_id"]}

    action_id = f"REV-{tx_id}"
    db_update_transaction(
        tx_id,
        merchant_status="REVERSED",
        settlement_status="REVERSED",
        action_id=action_id,
        resolution_status="RESOLVED",
    )
    return {"status": "SUCCESS", "action_id": action_id}


def verify_resolution(tx_id: str) -> dict:
    tx = db_get_transaction(tx_id)
    if not tx:
        raise ValueError(f"Transaction {tx_id} not found")

    checks = {
        "merchant_reversed":   tx["merchant_status"] == "REVERSED",
        "settlement_reversed":  tx["settlement_status"] == "REVERSED",
        "action_id_exists":     tx["action_id"] is not None,
    }
    return {
        "transaction_id": tx_id,
        "verified": all(checks.values()),
        "checks": checks,
        "action_id": tx["action_id"],
    }
