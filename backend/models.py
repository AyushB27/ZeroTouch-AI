from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class Transaction(BaseModel):
    transaction_id: str
    amount: float
    currency: str = "INR"
    bank_status: str
    network_status: str
    merchant_status: str
    settlement_status: str
    risk_score: float
    previous_refund: bool = False
    action_id: Optional[str] = None
    resolution_status: str = "PENDING"  # PENDING, RESOLVED, ESCALATED, NO_ACTION

class AuditEvent(BaseModel):
    timestamp: str
    type: str  # INVESTIGATION, POLICY, ACTION, VERIFICATION, NOTIFICATION, ESCALATION, ERROR
    step: str
    status: str  # SUCCESS, FAILED, INFO
    message: str

class Evidence(BaseModel):
    transaction_id: str
    bank: str
    network: str
    merchant: str
    settlement: str
    amount: float
    risk: float
    previous_refund: bool

class PolicyDecision(BaseModel):
    decision: str  # AUTO_REVERSAL, HUMAN_ESCALATION, NO_ACTION
    authorized: bool
    reason: str

class ResolutionResult(BaseModel):
    transaction_id: str
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
    # Layer 3 — AI Agent output
    investigation_narrative: Optional[str] = None
    agent_powered: bool = False
