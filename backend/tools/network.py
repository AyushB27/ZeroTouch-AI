from backend.database import db_get_transaction

def check_network_status(tx_id: str) -> dict:
    tx = db_get_transaction(tx_id)
    if not tx:
        raise ValueError(f"Transaction {tx_id} not found")
    return {"transaction_id": tx_id, "status": tx["network_status"]}
