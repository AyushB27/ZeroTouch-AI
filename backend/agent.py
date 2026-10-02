"""
Layer 3 — AI Resolution Agent
Observes payment system states, investigates the discrepancy, and produces
a human-readable investigation narrative using genuine Gemini tool-calling.

Architectural boundary:
  This layer OBSERVES and REASONS using Tool Calling.
  It does NOT authorize financial actions — that is Layer 4 (policy engine).
"""

import os
from dotenv import load_dotenv

# Ensure .env is loaded from both current directory and backend directory
load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from backend.models import Evidence
from backend.tools.bank import check_bank_status
from backend.tools.network import check_network_status
from backend.tools.merchant import check_merchant_ledger
from backend.tools.settlement import check_settlement

# Priority order of stable, non-overloaded Gemini models supporting tool calling
CANDIDATE_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-flash-latest",
    "gemini-3.1-flash-lite",
]


def investigate_transaction(tx_id: str, tx: dict, log_func) -> str:
    """
    Call Gemini to autonomously investigate the transaction using tools.
    Tries candidate stable models in order. If all fail or key is missing,
    smoothly falls back to deterministic ledger checks without crashing.
    """
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

    if api_key:
        for model in CANDIDATE_MODELS:
            try:
                return _gemini_tool_investigate(tx_id, tx, log_func, api_key, model=model)
            except Exception as e:
                # Silently try next model if 503 or 404 occurs
                continue

    # Deterministic fallback: manually fetch and log, then return clear narrative
    return _deterministic_investigate(tx_id, tx, log_func)


def _gemini_tool_investigate(tx_id: str, tx: dict, log_func, api_key: str, model: str = "gemini-3.5-flash-lite") -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    # Wrap tools to include live logging
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

    def tool_search_policy(query: str) -> str:
        """Search the internal Paytm knowledge base and policy rules."""
        from backend.rag import search_policy
        res = search_policy(query)
        log_func("INVESTIGATION", "search_policy", "SUCCESS", f"AI queried policy KB: {query}")
        return res

    tools = [
        tool_check_bank_status,
        tool_check_network_status,
        tool_check_merchant_ledger,
        tool_check_settlement,
        tool_search_policy
    ]

    prompt = f"""You are ZeroTouch, an autonomous payment resolution agent investigating a payment exception.

Transaction ID: {tx_id}
Customer: {tx.get('customer_name', 'Paytm User')}
Amount: ₹{tx['amount']:,.0f}
Risk Score: {tx['risk_score']:.0%}
Prior Refund on Record: {"Yes" if tx['previous_refund'] else "No"}

Your task:
1. Use your tools to check the status of this transaction across all 4 systems (Bank, Network, Merchant, Settlement). You must call all 4 tools.
2. Use the `tool_search_policy` tool to look up the relevant rule or SLA based on what you find.
3. Once you have all the results and policy context, write a concise investigation summary in exactly 3-4 sentences that:
   - States what happened to the customer's money based on the bank status.
   - Identifies the specific discrepancy found across the four payment systems.
   - States the exact policy rule that applies to this situation based on your policy search.

Be precise and factual. Use plain English. Do not recommend or authorize a refund — that decision belongs to the policy engine."""

    log_func("INVESTIGATION", "ai_agent_start", "INFO", f"Agent starting autonomous tool-calling investigation ({model})...")
    
    chat = client.chats.create(
        model=model,
        config=types.GenerateContentConfig(
            temperature=0.0,
            tools=tools
        )
    )
    
    response = chat.send_message(prompt)
    return response.text.strip()


def _deterministic_investigate(tx_id: str, tx: dict, log_func) -> str:
    """Fallback manual tool caller if LLM is temporarily unreachable."""
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
        customer_name=tx.get("customer_name", "Paytm User"),
        bank=bank['status'],
        network=network['status'],
        merchant=merchant['status'],
        settlement=settlement['status'],
        amount=tx['amount'],
        risk=tx['risk_score'],
        cibil_score=tx.get("cibil_score", 750),
        is_first_time_user=tx.get("is_first_time_user", False),
        previous_refund=tx['previous_refund']
    )

    parts = []
    if evidence.bank == "DEBITED":
        parts.append(f"The customer was debited ₹{evidence.amount:,.0f} from their account.")

    if evidence.network == "SUCCESS" and evidence.merchant == "NOT_CREDITED":
        parts.append("The payment network confirms the transaction as successful, but the merchant ledger shows no corresponding credit was received.")
    elif evidence.network in ("UNKNOWN", "SLA_BREACHED"):
        parts.append("The payment network status is unresolved — a transaction trace is required before any reconciliation can be performed.")
    elif evidence.network == "FAILED":
        parts.append("The payment network reports the transaction as failed.")
    elif evidence.network == "SUCCESS" and evidence.merchant == "CREDITED":
        parts.append("The payment network confirms success and the merchant ledger shows the credit was received — the transaction is consistent.")

    if evidence.settlement == "NOT_FOUND":
        parts.append("No settlement record exists, confirming the funds did not complete the payment cycle and are eligible for auto-reversal.")
    elif evidence.settlement == "UNKNOWN":
        parts.append("Settlement status is unknown — manual verification against the settlement system is required.")
    elif evidence.settlement == "SETTLED":
        parts.append("The settlement system confirms the transaction has settled successfully.")
    elif evidence.settlement == "REVERSED":
        parts.append("The settlement has been reversed and the funds are being returned.")

    return " ".join(parts) if parts else "Investigation complete. All system states have been retrieved."
