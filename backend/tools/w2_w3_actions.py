"""
W2 and W3 new action tools.
"""
from backend.database import db_update_transaction


# ── Workflow 2 ────────────────────────────────────────────────────────────────

def chase_bank_sla(tx_id: str) -> dict:
    """
    Simulates calling the bank's escalation API to chase an overdue refund.
    Real integration: POST to bank's dispute API with UTR reference.
    """
    chase_ref = f"CHASE-{tx_id}"
    db_update_transaction(tx_id, action_id=chase_ref, resolution_status="RESOLVED")
    return {
        "status": "SUCCESS",
        "chase_ref": chase_ref,
        "message": "Bank SLA escalation ticket raised. Refund expected within 24 hours.",
        "eta_hours": 24,
    }


def offer_wallet_credit(tx_id: str, amount: float) -> dict:
    """
    Simulates crediting the Paytm wallet when the bank account is invalid.
    Real integration: POST to Paytm wallet credit API.
    """
    credit_ref = f"WALLET-{tx_id}"
    db_update_transaction(tx_id, action_id=credit_ref, resolution_status="RESOLVED")
    return {
        "status": "SUCCESS",
        "credit_ref": credit_ref,
        "amount": amount,
        "destination": "Paytm Wallet",
        "message": f"Rs.{amount:.0f} credited to Paytm Wallet as refund return address was invalid.",
    }


# ── Workflow 3 ────────────────────────────────────────────────────────────────

def generate_itemized_explanation(tx_id: str, gross: float, fee: float, gst: float = 0.0) -> dict:
    """
    Auto-generates a settlement reconciliation explanation for a merchant.
    Real integration: POST to merchant notification API with itemized PDF.
    """
    net = gross - fee - gst
    expl_ref = f"EXPL-{tx_id}"
    db_update_transaction(tx_id, action_id=expl_ref, resolution_status="NO_ACTION")
    return {
        "status": "SUCCESS",
        "explanation_ref": expl_ref,
        "gross_amount": gross,
        "platform_fee": fee,
        "gst_on_fee": gst,
        "net_settled": net,
        "message": f"Gross ₹{gross:,.0f} less platform fee ₹{fee:,.0f} and GST ₹{gst:,.0f} equals net settlement ₹{net:,.0f}.",
    }


def flag_compliance_hold(tx_id: str, reason: str) -> dict:
    """
    Raises a compliance hold and routes to the compliance team.
    Real integration: POST to compliance case management system.
    """
    case_ref = f"COMP-{tx_id}"
    db_update_transaction(tx_id, action_id=case_ref, resolution_status="ESCALATED")
    return {
        "status": "HELD",
        "case_ref": case_ref,
        "reason": reason,
        "routed_to": "Compliance Team",
        "message": "Settlement blocked. KYC re-verification required. Merchant notified.",
        "required_docs": ["Aadhaar", "PAN Card", "Bank Statement (last 3 months)"],
    }
