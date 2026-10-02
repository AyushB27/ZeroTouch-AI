"""
Sub-Agent 3: Policy & Compliance Agent
Deterministic policy engine augmented by RAG retrieval and dynamic CIBIL ceilings.
The LLM never makes financial decisions. All branching is rule-based.
"""
from backend.models import Evidence, PolicyDecision


def evaluate_policy(evidence: Evidence) -> PolicyDecision:
    tx = evidence

    # Determine dynamic autonomous ceiling based on CIBIL and First-Time User status
    if tx.cibil_score >= 750:
        cibil_limit = 10000.0
        tier_note = f"Prime credit rating (CIBIL {tx.cibil_score}) qualifies for elevated ₹10,000 threshold."
    elif tx.cibil_score >= 650:
        cibil_limit = 5000.0
        tier_note = f"Standard credit standing (CIBIL {tx.cibil_score}) capped at ₹5,000 threshold."
    else:
        cibil_limit = 1500.0
        tier_note = f"Subprime credit rating (CIBIL {tx.cibil_score}) restricted to ₹1,500 threshold."

    # First-Time User High-Risk Filter
    if tx.is_first_time_user and tx.amount > 5000.0 and tx.cibil_score < 650:
        return PolicyDecision(
            decision="HUMAN_ESCALATION",
            authorized=False,
            reason=(
                f"High-value payment (₹{tx.amount:,.0f}) by First-Time User with subprime CIBIL ({tx.cibil_score}). "
                "Autonomous action prohibited. Mandatory human desk investigation required."
            ),
        )

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

    # ── W1: Clean auto-reversal (with CIBIL ceiling) ───────────────────────────
    if (
        tx.bank == "DEBITED"
        and tx.network == "SUCCESS"
        and tx.merchant == "NOT_CREDITED"
        and tx.settlement == "NOT_FOUND"
        and tx.amount <= cibil_limit
        and tx.risk < 0.30
        and not tx.previous_refund
    ):
        ft_note = " First-Time User onboarding safety applied." if tx.is_first_time_user else ""
        return PolicyDecision(
            decision="AUTO_REVERSAL",
            authorized=True,
            reason=(
                f"Bank debit confirmed. Network success but merchant not credited and settlement absent. "
                f"Amount ₹{tx.amount:,.0f} within credit ceiling (₹{cibil_limit:,.0f}). {tier_note}{ft_note}"
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
                "within standard SLA window. Autonomous bank escalation API triggered per Rule 2.2."
            ),
        )

    # ── W2: Invalid destination — bounce → offer wallet credit ────────────────
    if (
        tx.bank in ("BOUNCED_INVALID_ACCOUNT", "BOUNCED")
        and tx.network in ("FAILED_RETURN", "FAILED")
        and tx.merchant == "REVERSED"
        and tx.settlement == "FAILED"
    ):
        ft_note = " Customer is a First-Time User: prioritized instant Paytm Wallet credit to prevent churn." if tx.is_first_time_user else ""
        return PolicyDecision(
            decision="WALLET_CREDIT_OFFER",
            authorized=True,
            reason=(
                "Refund bounced because the destination bank account or card is invalid. "
                f"Per Rule 2.3: credit the equivalent amount to the customer's Paytm Wallet.{ft_note}"
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
        try:
            fee = float(tx.merchant.split("_")[-1])
        except ValueError:
            fee = 0.0
        return PolicyDecision(
            decision="ITEMIZED_EXPLANATION",
            authorized=True,
            reason=(
                f"Merchant settlement shortfall of ₹{fee:.0f} is fully explained by "
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
        reasons.append(f"fraud risk score {tx.risk:.2f} exceeds threshold")
    if tx.amount > cibil_limit and tx.bank == "DEBITED" and tx.merchant == "NOT_CREDITED":
        reasons.append(f"amount ₹{tx.amount:,.0f} exceeds CIBIL-backed autonomous limit (₹{cibil_limit:,.0f})")
    if tx.previous_refund and tx.bank == "DEBITED" and tx.merchant == "NOT_CREDITED":
        reasons.append("previous refund already issued for this transaction")
    if tx.cibil_score < 620:
        reasons.append(f"customer CIBIL score ({tx.cibil_score}) requires human supervisory sign-off")

    reason_str = "Payment state could not be conclusively reconciled. " + (
        "; ".join(reasons).capitalize() + "." if reasons else "Manual review required."
    )

    return PolicyDecision(
        decision="HUMAN_ESCALATION",
        authorized=False,
        reason=reason_str,
    )
