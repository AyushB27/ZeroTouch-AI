"""
Sub-Agent 3: Policy & Compliance Agent
Deterministic financial policy engine with explicit Rule IDs, versioning,
precedence hierarchy (DENY > ESCALATE > ALLOW), and formal Exception Taxonomy.

Guiding Principle:
The LLM never makes financial authorization decisions.
All decision branching is deterministic and auditable.
"""

from typing import Tuple
from backend.models import Evidence, PolicyDecision, ExceptionClassification


POLICY_VERSION = "2.0"

# Precedence levels: Strictest rule wins
# 3 = DENY, 2 = ESCALATE, 1 = ALLOW
PRECEDENCE_DENY = 3
PRECEDENCE_ESCALATE = 2
PRECEDENCE_ALLOW = 1


def evaluate_policy(evidence: Evidence) -> PolicyDecision:
    """
    Evaluates ledger evidence and dynamic credit tier ceilings to produce
    a deterministic, auditable PolicyDecision.
    """
    tx = evidence

    # Dynamic autonomous ceiling based on CIBIL and First-Time User status
    cibil = getattr(tx, "cibil_score", 750) if getattr(tx, "cibil_score", None) is not None else 750
    is_first_time = getattr(tx, "is_first_time_user", False) or False

    if cibil >= 750:
        cibil_limit = 10000.0
        tier_note = f"Prime credit rating (CIBIL {cibil}) qualifies for ₹10,000 threshold."
    elif cibil >= 650:
        cibil_limit = 5000.0
        tier_note = f"Standard credit rating (CIBIL {cibil}) capped at ₹5,000 threshold."
    else:
        cibil_limit = 1500.0
        tier_note = f"Subprime credit rating (CIBIL {cibil}) restricted to ₹1,500 threshold."

    # ── RULE 1: First-Time User High-Risk Filter (Precedence: ESCALATE) ─────────
    if is_first_time and tx.amount > 5000.0 and cibil < 650:
        return PolicyDecision(
            decision="HUMAN_ESCALATION",
            authorized=False,
            reason=(
                f"High-value payment (₹{tx.amount:,.0f}) by First-Time User with subprime CIBIL ({cibil}). "
                "Autonomous action prohibited by safety policy. Mandatory human desk investigation required."
            ),
            rule_id="RULE_W1_HIGH_RISK_FTU_01",
            rule_version=POLICY_VERSION,
            precedence=PRECEDENCE_ESCALATE,
            classification=ExceptionClassification.W1_HIGH_RISK_FIRST_TIME.value,
        )

    # ── RULE 2: W3 KYC / Compliance Hold — Never Auto-Release (Precedence: DENY/HOLD) ─
    if "HELD_KYC" in tx.settlement or "COMPLIANCE" in tx.settlement or tx.risk >= 0.85:
        return PolicyDecision(
            decision="COMPLIANCE_HOLD",
            authorized=False,
            reason=(
                "Settlement is held due to expired KYC or compliance risk flag. "
                "Per Rule 3.2: funds MUST NOT be released autonomously. "
                "Routing case to compliance audit desk."
            ),
            rule_id="RULE_W3_KYC_HOLD_01",
            rule_version=POLICY_VERSION,
            precedence=PRECEDENCE_DENY,
            classification=ExceptionClassification.W3_SETTLEMENT_KYC_HOLD.value,
        )

    # ── RULE 3: W1 Conflicting States (Precedence: ESCALATE) ───────────────────
    if tx.bank == "DEBITED" and tx.network == "FAILED" and tx.merchant == "CREDITED":
        return PolicyDecision(
            decision="HUMAN_ESCALATION",
            authorized=False,
            reason=(
                "Conflicting transaction states detected: Bank debited and network marked failed "
                "while merchant shows credit. Manual ledger audit required."
            ),
            rule_id="RULE_W1_CONFLICT_01",
            rule_version=POLICY_VERSION,
            precedence=PRECEDENCE_ESCALATE,
            classification=ExceptionClassification.W1_STATE_CONFLICT.value,
        )

    # ── RULE 4: W1 Consistent Transaction — All Systems Green (Precedence: ALLOW/NO_ACTION) ─
    if (
        tx.bank == "DEBITED"
        and tx.network == "SUCCESS"
        and tx.merchant == "CREDITED"
        and tx.settlement == "SETTLED"
    ):
        return PolicyDecision(
            decision="NO_ACTION",
            authorized=False,
            reason="Transaction is consistent and settled across all systems. No anomaly detected.",
            rule_id="RULE_W1_CONGRUENT_01",
            rule_version=POLICY_VERSION,
            precedence=PRECEDENCE_ALLOW,
            classification=ExceptionClassification.W1_CONGRUENT_SUCCESS.value,
        )

    # ── RULE 5: W1 Clean Auto-Reversal (Precedence: ALLOW) ─────────────────────
    if (
        tx.bank == "DEBITED"
        and tx.network == "SUCCESS"
        and tx.merchant == "NOT_CREDITED"
        and tx.settlement == "NOT_FOUND"
        and tx.amount <= cibil_limit
        and tx.risk < 0.30
        and not tx.previous_refund
    ):
        ft_note = " First-Time User onboarding safety applied." if is_first_time else ""
        return PolicyDecision(
            decision="AUTO_REVERSAL",
            authorized=True,
            reason=(
                f"Bank debit confirmed. Network success but merchant not credited and settlement absent. "
                f"Amount ₹{tx.amount:,.0f} within credit ceiling (₹{cibil_limit:,.0f}). {tier_note}{ft_note}"
            ),
            rule_id="RULE_W1_AUTO_REVERSAL_01",
            rule_version=POLICY_VERSION,
            precedence=PRECEDENCE_ALLOW,
            classification=ExceptionClassification.W1_DEBIT_NOT_CREDITED.value,
        )

    # ── RULE 6: W2 Refund SLA Breached (Precedence: ALLOW) ─────────────────────
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
                "within the 5-day SLA window. Bank escalation API triggered per Rule 2.2."
            ),
            rule_id="RULE_W2_SLA_CHASE_01",
            rule_version=POLICY_VERSION,
            precedence=PRECEDENCE_ALLOW,
            classification=ExceptionClassification.W2_REFUND_SLA_BREACH.value,
        )

    # ── RULE 7: W2 Invalid Destination Account — Bounced (Precedence: ALLOW) ───
    if (
        tx.bank in ("BOUNCED_INVALID_ACCOUNT", "BOUNCED")
        and tx.network in ("FAILED_RETURN", "FAILED")
        and tx.merchant == "REVERSED"
        and tx.settlement == "FAILED"
    ):
        ft_note = " Customer is a First-Time User: prioritized instant Paytm Wallet credit to prevent churn." if is_first_time else ""
        return PolicyDecision(
            decision="WALLET_CREDIT_OFFER",
            authorized=True,
            reason=(
                "Refund bounced because the destination bank account or card is invalid. "
                f"Per Rule 2.3: credit the equivalent amount to the customer's Paytm Wallet.{ft_note}"
            ),
            rule_id="RULE_W2_WALLET_CREDIT_01",
            rule_version=POLICY_VERSION,
            precedence=PRECEDENCE_ALLOW,
            classification=ExceptionClassification.W2_REFUND_BOUNCED.value,
        )

    # ── RULE 8: W3 Merchant Settlement Shortfall Explained by Fees (Precedence: ALLOW) ─
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
        except (ValueError, IndexError):
            fee, gst = 0.0, 0.0
        total_deduction = fee + gst
        return PolicyDecision(
            decision="ITEMIZED_EXPLANATION",
            authorized=True,
            reason=(
                f"Merchant settlement shortfall of ₹{total_deduction:,.0f} is fully explained by "
                f"standard platform fee (₹{fee:,.0f}) and GST (₹{gst:,.0f}). Per Rule 3.1: generate itemized breakdown "
                "and notify merchant. No ticket required."
            ),
            rule_id="RULE_W3_FEE_BREAKDOWN_01",
            rule_version=POLICY_VERSION,
            precedence=PRECEDENCE_ALLOW,
            classification=ExceptionClassification.W3_SETTLEMENT_FEE_DEDUCTION.value,
        )

    # ── RULE 9: Default Fallback — Escalate Ambiguous / High-Risk (Precedence: ESCALATE) ─
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
    if cibil < 620:
        reasons.append(f"customer CIBIL score ({cibil}) requires human supervisory sign-off")

    reason_str = "Payment state could not be conclusively reconciled. " + (
        "; ".join(reasons).capitalize() + "." if reasons else "Manual review required."
    )

    return PolicyDecision(
        decision="HUMAN_ESCALATION",
        authorized=False,
        reason=reason_str,
        rule_id="RULE_DEFAULT_ESCALATE_01",
        rule_version=POLICY_VERSION,
        precedence=PRECEDENCE_ESCALATE,
        classification=ExceptionClassification.UNKNOWN_PAYMENT_STATE.value,
    )
