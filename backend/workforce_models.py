"""
Domain-Agnostic Data Models for ZeroTouch Workforce
Platform core data models: SkillSpec, AutonomyLevel (L0-L3), WorkforceCase,
TrustEvent, BacktestReport, AcademyRun, and GovernorState.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum


class AutonomyLevel(str, Enum):
    L0 = "L0"  # Suggests only during backtest. Evidence pre-gathered.
    L1 = "L1"  # Investigates & drafts everything, human approves in one click (Default).
    L2 = "L2"  # Acts, with a sample of cases reviewed (50+ cases at 95%+).
    L3 = "L3"  # Acts alone, humans see exceptions only (Sustained accuracy).


class DomainType(str, Enum):
    SUPPORT = "support"
    FINANCE = "finance"
    IT = "it"
    HR = "hr"


class CaseStatus(str, Enum):
    PREPARED = "PREPARED"              # AI pre-worked, awaiting human 1-click approval
    PENDING_REVIEW = "PENDING_REVIEW"  # Flagged/escalated for review
    APPROVED = "APPROVED"              # Approved by human operator
    EDITED = "EDITED"                  # Edited by human operator before approval
    REJECTED = "REJECTED"              # Rejected by human operator
    AUTO_EXECUTED = "AUTO_EXECUTED"    # Executed autonomously under L2/L3


class SkillSpec(BaseModel):
    skill_id: str
    version: int = 1
    domain: DomainType
    name: str
    description: str
    trigger: str
    inputs: List[str] = Field(default_factory=list)
    steps: List[str] = Field(default_factory=list)
    rules: List[str] = Field(default_factory=list)
    exceptions: List[str] = Field(default_factory=list)
    success_criteria: str
    autonomy: AutonomyLevel = AutonomyLevel.L1
    backtest_match_rate: float = 0.0
    cases_tested: int = 0
    owner: str = "senior_lead"
    status: str = "ACTIVE"  # ACTIVE, TRAINING, DEMOTED, KILLED
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class WorkforceCase(BaseModel):
    case_id: str
    skill_id: str
    domain: DomainType
    title: str
    priority: str = "NORMAL"  # URGENT, HIGH, NORMAL
    status: CaseStatus = CaseStatus.PREPARED
    autonomy_level: AutonomyLevel = AutonomyLevel.L1
    evidence: Dict[str, Any] = Field(default_factory=dict)
    draft_action: Dict[str, Any] = Field(default_factory=dict)
    policy_cited: str
    assigned_role: str
    approver: Optional[str] = None
    outcome: Optional[str] = None
    edit_notes: Optional[str] = None
    execution_ref: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TrustEvent(BaseModel):
    id: Optional[int] = None
    skill_id: str
    event_type: str  # APPROVE, EDIT, REJECT, ERROR, PROMOTION, DEMOTION, KILL_SWITCH
    delta: float
    approver: str
    notes: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class BacktestCase(BaseModel):
    case_id: str
    inputs: Dict[str, Any]
    expected_output: Dict[str, Any]
    actual_output: Optional[Dict[str, Any]] = None
    passed: bool = False
    failure_reason: Optional[str] = None


class BacktestReport(BaseModel):
    skill_id: str
    skill_version: int
    cases_tested: int
    passed_count: int
    match_rate: float
    failures: List[Dict[str, Any]] = Field(default_factory=list)
    ready_for_l1: bool = False
    completed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AcademyQuestion(BaseModel):
    step_number: int
    question: str
    options: List[str]
    correct_option_index: int
    explanation: str
    competency_tagged: str


class AcademyRun(BaseModel):
    run_id: str
    joiner_id: str
    case_id: str
    answers: List[int] = Field(default_factory=list)
    score: float = 0.0
    passed: bool = False
    coach_feedback: str = ""
    competencies: Dict[str, float] = Field(default_factory=dict)
    completed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class GovernorState(BaseModel):
    kill_switch_active: bool = False
    triggered_by: Optional[str] = None
    triggered_at: Optional[str] = None
    never_automate_list: List[str] = Field(default_factory=lambda: [
        "PRIVILEGED_ROOT_ADMIN_ACCESS",
        "HIGH_VALUE_THRESHOLD_EXCEEDED",
        "HIRING_REJECTION_DECISIONS",
        "REGULATORY_COMPLIANCE_SUBMISSIONS",
        "DUPLICATE_PAYMENT_AUTO_RECOVERY",
    ])
    active_skills_count: int = 5
    overall_trust_score: float = 94.6
