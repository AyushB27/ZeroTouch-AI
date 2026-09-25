from backend.data import TRANSACTIONS


def initiate_reversal(tx_id: str) -> dict:
    tx = TRANSACTIONS.get(tx_id)
    if not tx:
        raise ValueError(f"Transaction {tx_id} not found")

    # Idempotency: if action already exists, return existing
    if tx["action_id"]:
        return {
            "status": "ALREADY_EXECUTED",
            "action_id": tx["action_id"],
        }

    action_id = f"REV-{tx_id}"

    # Mutate state
    tx["merchant_status"] = "REVERSED"
    tx["settlement_status"] = "REVERSED"
    tx["action_id"] = action_id
    tx["resolution_status"] = "RESOLVED"

    return {
        "status": "SUCCESS",
        "action_id": action_id,
    }


def verify_resolution(tx_id: str) -> dict:
    tx = TRANSACTIONS.get(tx_id)
    if not tx:
        raise ValueError(f"Transaction {tx_id} not found")

    checks = {
        "merchant_reversed": tx["merchant_status"] == "REVERSED",
        "settlement_reversed": tx["settlement_status"] == "REVERSED",
        "action_id_exists": tx["action_id"] is not None,
    }

    verified = all(checks.values())

    return {
        "transaction_id": tx_id,
        "verified": verified,
        "checks": checks,
        "action_id": tx["action_id"],
    }
