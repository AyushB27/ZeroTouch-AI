"""
Layer 3 — AI Resolution Agent
Observes payment system states, investigates the discrepancy, and produces
a human-readable investigation narrative.

Architectural boundary:
  This layer OBSERVES and REASONS using Tool Calling.
  It does NOT authorize financial actions — that is Layer 4 (policy engine).
"""

import os
from backend.models import Evidence
from backend.tools.bank import check_bank_status
from backend.tools.network import check_network_status
from backend.tools.merchant import check_merchant_ledger
from backend.tools.settlement import check_settlement


def investigate_transaction(tx_id: str, tx: dict, log_func) -> str:
    """
    Call Gemini to autonomously investigate the transaction using tools.
    Falls back to a deterministic template if the API key is missing or the call fails.
    """
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

    if api_key:
        try:
            return _gemini_tool_investigate(tx_id, tx, log_func, api_key)
        except Exception as e:
            # LLM failure must never break the core workflow
            log_func("ERROR", "ai_agent_tools", "FAILED", f"LLM Tool Calling failed: {str(e)}")
            pass

    # Deterministic fallback: manually fetch and log, then return static string
    return _deterministic_investigate(tx_id, tx, log_func)


def _gemini_tool_investigate(tx_id: str, tx: dict, log_func, api_key: str) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    # Wrap tools to include logging
    def tool_check_bank_status() -> dict:
        """Check the customer's bank account ledger status."""
        res = check_bank_status(tx_id)
        log_func("INVESTIGATION", "check_bank_status", "SUCCESS", f"Bank status retrieved by AI: {res['status']}")
        return res

    def tool_check_network_status() -> dict:
        """Check the payment network (NPCI) trace status."""
        res = check_network_status(tx_id)
        log_func("INVESTIGATION", "check_network_status", "SUCCESS", f"Network status retrieved by AI: {res['status']}")
        return res

    def tool_check_merchant_ledger() -> dict:
        """Check the merchant's ledger to see if they received the funds."""
        res = check_merchant_ledger(tx_id)
        log_func("INVESTIGATION", "check_merchant_ledger", "SUCCESS", f"Merchant ledger retrieved by AI: {res['status']}")
        return res

    def tool_check_settlement() -> dict:
        """Check the final settlement system status."""
        res = check_settlement(tx_id)
        log_func("INVESTIGATION", "check_settlement", "SUCCESS", f"Settlement status retrieved by AI: {res['status']}")
        return res

    tools = [
        tool_check_bank_status,
        tool_check_network_status,
        tool_check_merchant_ledger,
        tool_check_settlement
    ]

    prompt = f"""You are ZeroTouch, an autonomous payment resolution agent investigating a payment exception.

Transaction ID: {tx_id}
Amount: ₹{tx['amount']:,.0f}
Risk Score: {tx['risk_score']:.0%}
Prior Refund on Record: {"Yes" if tx['previous_refund'] else "No"}

Your task:
1. Use your tools to check the status of this transaction across all 4 systems (Bank, Network, Merchant, Settlement). You must call all 4 tools.
2. Once you have all the results, write a concise investigation summary in exactly 2-3 sentences that:
   - States what happened to the customer's money based on the bank status.
   - Identifies the specific discrepancy found across the four payment systems.
   - States what this means and what follow-up action is warranted.

Be precise and factual. Use plain English. Do not recommend or authorize a refund — that decision belongs to the policy engine."""

    log_func("INVESTIGATION", "ai_agent_start", "INFO", "Agent starting autonomous tool-calling investigation...")
    
    # We must use chat session to handle multi-turn function calling automatically if configured, 
    # but generate_content with tool config can also handle automatic function calling in python SDK.
    # Let's use the chat abstraction which natively handles the function call loop.
    chat = client.chats.create(
        model="gemini-3.8-flash",
        config=types.GenerateContentConfig(
            temperature=0.0,
            tools=tools
        )
    )
    
    response = chat.send_message(prompt)
    
    return response.text.strip()


def _deterministic_investigate(tx_id: str, tx: dict, log_func) -> str:
    """Fallback: manually call tools, log, and generate rule-based narrative."""
    bank = check_bank_status(tx_id)
    log_func("INVESTIGATION", "check_bank_status", "SUCCESS", f"Bank status retrieved: {bank['status']}")
    
    network = check_network_status(tx_id)
    log_func("INVESTIGATION", "check_network_status", "SUCCESS", f"Network status retrieved: {network['status']}")
    
    merchant = check_merchant_ledger(tx_id)
    log_func("INVESTIGATION", "check_merchant_ledger", "SUCCESS", f"Merchant ledger retrieved: {merchant['status']}")
    
    settlement = check_settlement(tx_id)
    log_func("INVESTIGATION", "check_settlement", "SUCCESS", f"Settlement status retrieved: {settlement['status']}")

    evidence = Evidence(
        transaction_id=tx_id,
        bank=bank['status'],
        network=network['status'],
        merchant=merchant['status'],
        settlement=settlement['status'],
        amount=tx['amount'],
        risk=tx['risk_score'],
        previous_refund=tx['previous_refund']
    )

    parts = []
    if evidence.bank == "DEBITED":
        parts.append(f"The customer was debited ₹{evidence.amount:,.0f} from their account.")

    if evidence.network == "SUCCESS" and evidence.merchant == "NOT_CREDITED":
        parts.append("The payment network confirms the transaction as successful, but the merchant ledger shows no corresponding credit was received.")
    elif evidence.network == "UNKNOWN":
        parts.append("The payment network status is unresolved — a transaction trace is required before any reconciliation can be performed.")
    elif evidence.network == "FAILED":
        parts.append("The payment network reports the transaction as failed.")
    elif evidence.network == "SUCCESS" and evidence.merchant == "CREDITED":
        parts.append("The payment network confirms success and the merchant ledger shows the credit was received — the transaction is consistent.")

    if evidence.settlement == "NOT_FOUND":
        parts.append("No settlement record exists, confirming the funds did not complete the payment cycle and are eligible for investigation.")
    elif evidence.settlement == "UNKNOWN":
        parts.append("Settlement status is unknown — manual verification against the settlement system is required before any financial action.")
    elif evidence.settlement == "SETTLED":
        parts.append("The settlement system confirms the transaction has settled successfully.")
    elif evidence.settlement == "REVERSED":
        parts.append("The settlement has been reversed and the funds are being returned.")

    return " ".join(parts) if parts else "Investigation complete. All system states have been retrieved."
