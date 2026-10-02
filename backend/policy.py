"""
Extended policy engine — covers W1, W2, and W3 scenarios.
The LLM never makes financial decisions. All branching is rule-based.
"""
from backend.models import Evidence, PolicyDecision


def evaluate_policy(evidence: Evidence) -> PolicyDecision:
    tx = evidence

    # ── W1: Consistent transaction ────────────────────────────────────────────
    if (
        tx.bank == "DEBITED"
        and tx.network == "SUCCESS"
        and tx.merchant == "CREDITED"
        and tx.settlement == "SETTLED"
    ):
        return PolicyDecision(
            decision="NO_ACTION",
            authorized=False,
            reason="Transaction is consistent across all systems. No anomaly detected.",
        )

    # ── W1: Clean auto-reversal ───────────────────────────────────────────────
    if (
        tx.bank == "DEBITED"
        and tx.network == "SUCCESS"
        and tx.merchant == "NOT_CREDITED"
        and tx.settlement == "NOT_FOUND"
        and tx.amount <= 5000
        and tx.risk < 0.30
        and not tx.previous_refund
    ):
        return PolicyDecision(
            decision="AUTO_REVERSAL",
            authorized=True,
            reason=(
                "Bank debit confirmed. Network success but merchant not credited and "
                "settlement absent. Amount within autonomous action limit. Risk score "
                f"{tx.risk:.2f} below threshold. No prior refund on record."
            ),
        )

    # ── W2: SLA breached — bank acknowledged refund but not yet credited ──────
    if (
        tx.bank == "ACKNOWLEDGED"
        and tx.network == "SLA_BREACHED"
        and tx.merchant == "REVERSED"
        and tx.settlement == "PENDING_CREDIT"
    ):
        return PolicyDecision(
            decision="SLA_CHASE",
            authorized=True,
            reason=(
                "Refund was acknowledged by the bank but has not credited to the customer "
                "within the 5-day SLA window. Autonomous bank escalation API triggered per Rule 2.2."
            ),
        )

    # ── W2: Invalid destination — bounce → offer wallet credit ────────────────
    if (
        tx.bank in ("BOUNCED_INVALID_ACCOUNT", "BOUNCED")
        and tx.network in ("FAILED_RETURN", "FAILED")
        and tx.merchant == "REVERSED"
        and tx.settlement == "FAILED"
    ):
        return PolicyDecision(
            decision="WALLET_CREDIT_OFFER",
            authorized=True,
            reason=(
                "Refund bounced because the destination bank account or card is invalid. "
                "Per Rule 2.3: credit the equivalent amount to the customer's Paytm Wallet."
            ),
        )

    # ── W3: Merchant settlement shortfall explainable by fees ────────────────
    if (
        tx.bank == "SETTLED_TO_NODAL"
        and tx.network == "SUCCESS"
        and tx.merchant.startswith("FEE_DEDUCTION")
        and tx.settlement.startswith("PARTIAL_SETTLED")
        and tx.risk < 0.10
    ):
        fee_parts = tx.merchant.split("_")
        try:
            fee = float(fee_parts[2]) if len(fee_parts) > 2 and fee_parts[1] == "DEDUCTION" else 0.0
            gst = float(fee_parts[4]) if len(fee_parts) > 4 and fee_parts[3] == "GST" else 0.0
        except ValueError:
            fee, gst = 0.0, 0.0
        total_deduction = fee + gst
        return PolicyDecision(
            decision="ITEMIZED_EXPLANATION",
            authorized=True,
            reason=(
                f"Merchant settlement shortfall of Rs.{total_deduction:.0f} is fully explained by "
                "standard platform fees and GST. Per Rule 3.1: generate itemized breakdown "
                "and notify merchant. No ticket required."
            ),
        )

    # ── W3: KYC / compliance hold — never auto-release ───────────────────────
    if "HELD_KYC" in tx.settlement or "COMPLIANCE" in tx.settlement or tx.risk >= 0.85:
        return PolicyDecision(
            decision="COMPLIANCE_HOLD",
            authorized=False,
            reason=(
                "Settlement is held due to expired KYC or compliance risk flag. "
                "Per Rule 3.2: funds MUST NOT be released autonomously. "
                "Routing to compliance team immediately."
            ),
        )

    # ── W1: Conflicting states ────────────────────────────────────────────────
    if tx.bank == "DEBITED" and tx.network == "FAILED" and tx.merchant == "CREDITED":
        return PolicyDecision(
            decision="HUMAN_ESCALATION",
            authorized=False,
            reason=(
                "Conflicting transaction states detected. Bank debited but network failed "
                "while merchant shows credit. Manual investigation required."
            ),
        )

    # ── Default: escalate any ambiguous / high-risk case ─────────────────────
    reasons = []
    if tx.network in ("UNKNOWN", "SLA_BREACHED"):
        reasons.append("network status could not be confirmed")
    if tx.settlement in ("UNKNOWN",):
        reasons.append("settlement status is unresolved")
    if tx.risk >= 0.30:
        reasons.append(f"risk score {tx.risk:.2f} exceeds autonomous action threshold (0.30)")
    if tx.amount > 5000 and tx.bank == "DEBITED" and tx.merchant == "NOT_CREDITED":
        reasons.append(f"amount Rs.{tx.amount:.0f} exceeds autonomous action limit (Rs.5,000)")
    if tx.previous_refund and tx.bank == "DEBITED" and tx.merchant == "NOT_CREDITED":
        reasons.append("previous refund already issued for this transaction")

    reason_str = "Payment state could not be conclusively reconciled. " + (
        "; ".join(reasons).capitalize() + "." if reasons else "Manual review required."
    )

    return PolicyDecision(
        decision="HUMAN_ESCALATION",
        authorized=False,
        reason=reason_str,
    )
