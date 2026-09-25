def send_customer_notification(tx_id: str, amount: float, action_id: str) -> dict:
    # Simulated notification — no real API
    message = (
        f"Your payment of \u20b9{amount:.0f} (Ref: {tx_id}) could not be processed. "
        f"A refund of \u20b9{amount:.0f} has been initiated (Ref: {action_id}). "
        "This will reflect in your account within 2-3 business days."
    )
    return {
        "status": "SENT",
        "channel": "SMS+EMAIL",
        "message": message,
        "transaction_id": tx_id,
    }


def create_support_case(tx_id: str, reason: str, evidence: dict, suggested_resolution: str) -> dict:
    case_id = f"CASE-ZT{tx_id[2:]}"
    return {
        "case_id": case_id,
        "transaction_id": tx_id,
        "priority": "HIGH",
        "status": "HUMAN_REVIEW",
        "reason": reason,
        "evidence": evidence,
        "suggested_resolution": suggested_resolution,
    }
