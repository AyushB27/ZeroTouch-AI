"""
Layer 3 — AI Resolution Agent
Observes payment system states, investigates the discrepancy, and produces
a human-readable investigation narrative.

Architectural boundary:
  This layer OBSERVES and REASONS.
  It does NOT authorize financial actions — that is Layer 4 (policy engine).
"""

import os
from backend.models import Evidence


def investigate_transaction(evidence: Evidence) -> str:
    """
    Call Gemini to generate an investigation narrative for the transaction.
    Falls back to a deterministic template if the API key is missing or the call fails.
    """
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

    if api_key:
        try:
            return _gemini_investigate(evidence, api_key)
        except Exception as e:
            # LLM failure must never break the core workflow
            pass

    return _deterministic_narrative(evidence)


def _gemini_investigate(evidence: Evidence, api_key: str) -> str:
    from google import genai

    client = genai.Client(api_key=api_key)

    prompt = f"""You are ZeroTouch, an autonomous payment resolution agent investigating a payment exception.

Transaction ID: {evidence.transaction_id}
Amount: ₹{evidence.amount:,.0f}
Risk Score: {evidence.risk:.0%}
Prior Refund on Record: {"Yes" if evidence.previous_refund else "No"}

Payment System Investigation Results:
- Bank Ledger:        {evidence.bank}
- Payment Network:    {evidence.network}
- Merchant Ledger:    {evidence.merchant}
- Settlement System:  {evidence.settlement}

Write a concise investigation summary in exactly 2-3 sentences that:
1. States what happened to the customer's money based on the bank status
2. Identifies the specific discrepancy found across the four payment systems
3. States what this means and what follow-up action is warranted

Be precise and factual. Use plain English. Do not recommend or authorize a refund — that decision belongs to the policy engine."""

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )
    return response.text.strip()


def _deterministic_narrative(evidence: Evidence) -> str:
    """Fallback: rule-based narrative that matches what the LLM would produce."""
    parts = []

    if evidence.bank == "DEBITED":
        parts.append(
            f"The customer was debited ₹{evidence.amount:,.0f} from their account."
        )

    if evidence.network == "SUCCESS" and evidence.merchant == "NOT_CREDITED":
        parts.append(
            "The payment network confirms the transaction as successful, "
            "but the merchant ledger shows no corresponding credit was received."
        )
    elif evidence.network == "UNKNOWN":
        parts.append(
            "The payment network status is unresolved — a transaction trace is required "
            "before any reconciliation can be performed."
        )
    elif evidence.network == "FAILED":
        parts.append("The payment network reports the transaction as failed.")
    elif evidence.network == "SUCCESS" and evidence.merchant == "CREDITED":
        parts.append(
            "The payment network confirms success and the merchant ledger "
            "shows the credit was received — the transaction is consistent."
        )

    if evidence.settlement == "NOT_FOUND":
        parts.append(
            "No settlement record exists, confirming the funds did not complete "
            "the payment cycle and are eligible for investigation."
        )
    elif evidence.settlement == "UNKNOWN":
        parts.append(
            "Settlement status is unknown — manual verification against the "
            "settlement system is required before any financial action."
        )
    elif evidence.settlement == "SETTLED":
        parts.append("The settlement system confirms the transaction has settled successfully.")
    elif evidence.settlement == "REVERSED":
        parts.append("The settlement has been reversed and the funds are being returned.")

    return " ".join(parts) if parts else "Investigation complete. All system states have been retrieved."
