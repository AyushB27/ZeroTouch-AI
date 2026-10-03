from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum


class ExceptionClassification(str, Enum):
    W1_DEBIT_NOT_CREDITED = "W1_DEBIT_NOT_CREDITED"
    W1_CONGRUENT_SUCCESS = "W1_CONGRUENT_SUCCESS"
    W1_HIGH_RISK_FIRST_TIME = "W1_HIGH_RISK_FIRST_TIME"
    W1_STATE_CONFLICT = "W1_STATE_CONFLICT"
    W2_REFUND_SLA_BREACH = "W2_REFUND_SLA_BREACH"
    W2_REFUND_BOUNCED = "W2_REFUND_BOUNCED"
    W3_SETTLEMENT_FEE_DEDUCTION = "W3_SETTLEMENT_FEE_DEDUCTION"
    W3_SETTLEMENT_KYC_HOLD = "W3_SETTLEMENT_KYC_HOLD"
    UNKNOWN_PAYMENT_STATE = "UNKNOWN_PAYMENT_STATE"
    VERIFICATION_FAILURE = "VERIFICATION_FAILURE"


class ActionLifecycleState(str, Enum):
    NONE = "NONE"
    PROPOSED = "PROPOSED"
    AUTHORIZED = "AUTHORIZED"
    EXECUTING = "EXECUTING"
    EXECUTED = "EXECUTED"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"


class AuditVisibility(str, Enum):
    CUSTOMER = "CUSTOMER"
    INTERNAL = "INTERNAL"
    SYSTEM = "SYSTEM"


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
    visibility: str = "INTERNAL"  # CUSTOMER, INTERNAL, SYSTEM
    actor: str = "ZeroTouch Agent"


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


class EvidenceMatrix(BaseModel):
    transaction_id: str
    bank_status: str
    network_status: str
    merchant_status: str
    settlement_status: str
    queried_at: str
    provenance: Dict[str, str] = Field(default_factory=dict)


class ActionRecord(BaseModel):
    action_id: str
    idempotency_key: str
    action_type: str  # REVERSAL, SLA_CHASE, WALLET_CREDIT, ITEMIZED_EXPLANATION, COMPLIANCE_HOLD
    amount: float
    status: str = "PROPOSED"  # PROPOSED, AUTHORIZED, EXECUTED, VERIFIED, FAILED
    is_simulated: bool = True
    initiated_at: str
    executed_at: Optional[str] = None
    verified_at: Optional[str] = None
    verification_details: Optional[Dict[str, Any]] = None


class PolicyDecision(BaseModel):
    decision: str  # AUTO_REVERSAL, SLA_CHASE, WALLET_CREDIT_OFFER, ITEMIZED_EXPLANATION, COMPLIANCE_HOLD, HUMAN_ESCALATION, NO_ACTION
    authorized: bool
    reason: str
    rule_id: str = "RULE_DEFAULT"
    rule_version: str = "2.0"
    precedence: int = 1  # 3: DENY, 2: ESCALATE, 1: ALLOW
    classification: str = "UNKNOWN_PAYMENT_STATE"


class PaymentCase(BaseModel):
    case_id: str
    transaction_id: str
    customer_id: str = "cust-ayush"
    customer_name: str = "Paytm User"
    workflow_type: str = "W1"
    classification: str = "UNKNOWN_PAYMENT_STATE"
    amount: float
    currency: str = "INR"
    evidence_matrix: Optional[EvidenceMatrix] = None
    risk_assessment: Optional[RiskAssessment] = None
    policy_decision: Optional[PolicyDecision] = None
    action_record: Optional[ActionRecord] = None
    customer_status: str = "INVESTIGATING"  # INVESTIGATING, RESOLVED, HUMAN_REVIEW, NO_ACTION
    ops_status: str = "PENDING"             # PENDING, RESOLVED, ESCALATED, NO_ACTION
    human_review_notes: Optional[str] = None
    assigned_agent: Optional[str] = None
    dynamic_message: Optional[str] = None
    created_at: str
    updated_at: str


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
    case_id: Optional[str] = None
    rule_id: Optional[str] = None
    classification: Optional[str] = None
