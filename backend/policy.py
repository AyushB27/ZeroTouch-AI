from backend.models import Evidence, PolicyDecision


def evaluate_policy(evidence: Evidence) -> PolicyDecision:
    """Deterministic policy engine. The LLM never makes financial decisions."""

    tx = evidence

    # Scenario: consistent successful transaction — no action needed
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

    # Scenario: safe auto-reversal
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

    # Conflicting states — never automatically reverse
    if tx.bank == "DEBITED" and tx.network == "FAILED" and tx.merchant == "CREDITED":
        return PolicyDecision(
            decision="HUMAN_ESCALATION",
            authorized=False,
            reason="Conflicting transaction states detected. Bank debited but network failed while merchant shows credit. Manual investigation required.",
        )

    # Default: escalate for any ambiguous or high-risk case
    reasons = []
    if tx.network == "UNKNOWN":
        reasons.append("network status could not be confirmed")
    if tx.settlement == "UNKNOWN":
        reasons.append("settlement status is unresolved")
    if tx.risk >= 0.30:
        reasons.append(f"risk score {tx.risk:.2f} exceeds autonomous action threshold (0.30)")
    if tx.amount > 5000:
        reasons.append(f"amount \u20b9{tx.amount:.0f} exceeds autonomous action limit (\u20b95,000)")
    if tx.previous_refund:
        reasons.append("previous refund already issued for this transaction")

    reason_str = "Payment state could not be conclusively reconciled. " + (
        "; ".join(reasons).capitalize() + "." if reasons else "Manual review required."
    )

    return PolicyDecision(
        decision="HUMAN_ESCALATION",
        authorized=False,
        reason=reason_str,
    )
