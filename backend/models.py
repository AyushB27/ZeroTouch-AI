from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class Transaction(BaseModel):
    transaction_id: str
    customer_name: str = "Paytm User"
    amount: float
    currency: str = "INR"
    bank_status: str
    network_status: str
    merchant_status: str
    settlement_status: str
    risk_score: float
    cibil_score: int = 750
    is_first_time_user: bool = False
    previous_refund: bool = False
    action_id: Optional[str] = None
    resolution_status: str = "PENDING"  # PENDING, RESOLVED, ESCALATED, NO_ACTION
    workflow_type: str = "W1"
    dynamic_message: Optional[str] = None

class AuditEvent(BaseModel):
    timestamp: str
    type: str  # INVESTIGATION, RISK_ANALYSIS, POLICY, ACTION, VERIFICATION, NOTIFICATION, ESCALATION, ERROR
    step: str
    status: str  # SUCCESS, FAILED, INFO
    message: str

class RiskAssessment(BaseModel):
    cibil_score: int
    cibil_band: str            # PRIME, GOOD, FAIR, SUBPRIME
    is_first_time_user: bool
    autonomous_limit: float
    trust_tier: str            # TIER_1_HIGH, TIER_2_STANDARD, TIER_3_RESTRICTED
    verdict: str

class Evidence(BaseModel):
    transaction_id: str
    customer_name: str = "Paytm User"
    bank: str
    network: str
    merchant: str
    settlement: str
    amount: float
    risk: float
    cibil_score: int = 750
    is_first_time_user: bool = False
    previous_refund: bool = False

class PolicyDecision(BaseModel):
    decision: str  # AUTO_REVERSAL, SLA_CHASE, WALLET_CREDIT_OFFER, ITEMIZED_EXPLANATION, COMPLIANCE_HOLD, HUMAN_ESCALATION, NO_ACTION
    authorized: bool
    reason: str

class ResolutionResult(BaseModel):
    transaction_id: str
    customer_name: str = "Paytm User"
    cibil_score: int = 750
    is_first_time_user: bool = False
    decision: str
    authorized: bool
    action_id: Optional[str]
    verification_status: Optional[str]
    notification_sent: bool
    support_case: Optional[str]
    resolution_status: str
    events: List[AuditEvent]
    evidence: Optional[Evidence]
    escalation_reason: Optional[str]
    suggested_resolution: Optional[str]
    investigation_narrative: Optional[str] = None
    dynamic_message: Optional[str] = None
    agent_powered: bool = True
