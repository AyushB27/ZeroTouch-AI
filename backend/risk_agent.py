"""
Sub-Agent 2: Risk & Credit Profiling Agent
Specializes in evaluating customer creditworthiness (CIBIL Score),
tenure/First-Time User risk, and dynamic autonomous refund authorization ceilings.
"""

from backend.models import RiskAssessment

def assess_risk_and_credit(tx: dict, log_func) -> RiskAssessment:
    """
    Evaluates customer profile, CIBIL score, and First-Time User flag
    to determine autonomous authorization ceilings and risk tier.
    """
    customer_name = tx.get("customer_name", "Paytm Customer")
    cibil = tx.get("cibil_score", 750)
    is_first_time = tx.get("is_first_time_user", False)
    risk_score = tx.get("risk_score", 0.0)
    amount = tx.get("amount", 0.0)

    log_func(
        "RISK_ANALYSIS",
        "cibil_credit_check",
        "SUCCESS",
        f"CIBIL Credit Score retrieved: {cibil} | Customer: {customer_name}"
    )

    if is_first_time:
        log_func(
            "RISK_ANALYSIS",
            "first_time_user_check",
            "INFO",
            "Flagged: First-Time Paytm User. Applying First-Time User Protection Protocol."
        )

    # Classify CIBIL Band
    if cibil >= 750:
        cibil_band = "PRIME"
        trust_tier = "TIER_1_HIGH"
        # Prime customers get elevated autonomous limit
        autonomous_limit = 10000.0
        reason = f"Prime credit rating (CIBIL {cibil}) with verified KYC. Autonomous ceiling elevated to ₹10,000."
    elif cibil >= 680:
        cibil_band = "GOOD"
        trust_tier = "TIER_2_STANDARD"
        autonomous_limit = 5000.0
        reason = f"Good credit standing (CIBIL {cibil}). Standard autonomous ceiling ₹5,000."
    elif cibil >= 620:
        cibil_band = "FAIR"
        trust_tier = "TIER_2_STANDARD"
        autonomous_limit = 3000.0
        reason = f"Moderate credit standing (CIBIL {cibil}). Capped autonomous ceiling ₹3,000."
    else:
        cibil_band = "SUBPRIME"
        trust_tier = "TIER_3_RESTRICTED"
        autonomous_limit = 1000.0
        reason = f"Subprime credit score (CIBIL {cibil}). High credit/default risk. Restricted ceiling ₹1,000."

    # First-Time User special considerations
    if is_first_time:
        if amount > 5000.0 and cibil < 650:
            trust_tier = "TIER_3_RESTRICTED"
            autonomous_limit = 0.0  # Require human review for high-ticket subprime first-time transaction
            reason = (
                f"High-value transaction (₹{amount:,.0f}) by First-Time User with subprime CIBIL ({cibil}). "
                "Autonomous action prohibited. Mandatory Human Review required."
            )
        elif amount <= 3000.0 and risk_score < 0.15:
            # First-Time User Retention Shield: Prioritize instant resolution so user doesn't churn
            autonomous_limit = max(autonomous_limit, 3000.0)
            reason = (
                f"First-Time User Onboarding Protection: Transaction within safety threshold (₹{amount:,.0f}). "
                "Fast-track auto-resolution authorized to protect user retention."
            )

    log_func(
        "RISK_ANALYSIS",
        "risk_verdict",
        "SUCCESS",
        f"Risk Agent Verdict: {trust_tier} | CIBIL Band: {cibil_band} | Auto Limit: ₹{autonomous_limit:,.0f}"
    )

    return RiskAssessment(
        cibil_score=cibil,
        cibil_band=cibil_band,
        is_first_time_user=is_first_time,
        autonomous_limit=autonomous_limit,
        trust_tier=trust_tier,
        verdict=reason,
    )
