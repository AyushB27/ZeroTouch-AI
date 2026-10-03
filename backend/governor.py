"""
Autonomy Governor for ZeroTouch Workforce
Manages per-skill trust ladder (L0-L3), promotion and demotion rules,
global emergency kill switch, and the never-automate guardrail list.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import json

from backend.workforce_models import AutonomyLevel, GovernorState, TrustEvent


class AutonomyGovernor:
    """
    Central governance engine that makes 'earned autonomy' measurable and safe.
    Enforces that the AI teammate never acts beyond its proven trust level.
    """

    # In-memory singleton state
    _state: GovernorState = GovernorState(
        kill_switch_active=False,
        triggered_by=None,
        triggered_at=None,
        active_skills_count=5,
        overall_trust_score=94.6,
    )

    _trust_history: List[TrustEvent] = []

    # Per-skill trust metrics
    _skill_metrics: Dict[str, Dict[str, Any]] = {
        "refund_sla_chase": {
            "name": "Refund SLA Chase",
            "domain": "support",
            "level": AutonomyLevel.L1,
            "cases_processed": 64,
            "approved_count": 61,
            "edited_count": 3,
            "rejected_count": 0,
            "accuracy_rate": 95.3,
            "status": "ACTIVE",
            "can_promote_l2": True,
        },
        "upi_stuck_reversal": {
            "name": "UPI Stuck Reversal",
            "domain": "support",
            "level": AutonomyLevel.L1,
            "cases_processed": 142,
            "approved_count": 139,
            "edited_count": 3,
            "rejected_count": 0,
            "accuracy_rate": 97.9,
            "status": "ACTIVE",
            "can_promote_l2": True,
        },
        "settlement_fee_breakdown": {
            "name": "Settlement Fee Itemization",
            "domain": "support",
            "level": AutonomyLevel.L2,
            "cases_processed": 210,
            "approved_count": 208,
            "edited_count": 2,
            "rejected_count": 0,
            "accuracy_rate": 99.0,
            "status": "ACTIVE",
            "can_promote_l2": False,
        },
        "bank_statement_match": {
            "name": "Bank Statement Line Matching",
            "domain": "finance",
            "level": AutonomyLevel.L2,
            "cases_processed": 380,
            "approved_count": 376,
            "edited_count": 4,
            "rejected_count": 0,
            "accuracy_rate": 98.9,
            "status": "ACTIVE",
            "can_promote_l2": False,
        },
        "resume_screening_rubric": {
            "name": "Candidate Resume Screening",
            "domain": "hr",
            "level": AutonomyLevel.L1,
            "cases_processed": 88,
            "approved_count": 83,
            "edited_count": 5,
            "rejected_count": 0,
            "accuracy_rate": 94.3,
            "status": "ACTIVE",
            "can_promote_l2": False,  # Always stays L1 per never-automate rule
        },
        "it_tool_access_grant": {
            "name": "IT Standard Tool Provisioning",
            "domain": "it",
            "level": AutonomyLevel.L0,  # Initially L0/un-taught until live taught!
            "cases_processed": 12,
            "approved_count": 11,
            "edited_count": 1,
            "rejected_count": 0,
            "accuracy_rate": 91.7,
            "status": "TRAINING",
            "can_promote_l2": False,
        },
    }

    @classmethod
    def get_state(cls) -> GovernorState:
        return cls._state

    @classmethod
    def toggle_kill_switch(cls, user_name: str = "Rajesh Mehra (Operations Director)") -> GovernorState:
        """Toggles emergency kill switch. Instantly stops all L2/L3 autonomy and forces human review."""
        cls._state.kill_switch_active = not cls._state.kill_switch_active
        now_iso = datetime.now(timezone.utc).isoformat()
        if cls._state.kill_switch_active:
            cls._state.triggered_by = user_name
            cls._state.triggered_at = now_iso
            cls.record_trust_event(
                skill_id="GLOBAL",
                event_type="KILL_SWITCH",
                delta=-50.0,
                approver=user_name,
                notes="EMERGENCY KILL SWITCH ENGAGED: All autonomous executions suspended. Forced 100% human-in-the-loop review.",
            )
        else:
            cls._state.triggered_by = None
            cls._state.triggered_at = None
            cls.record_trust_event(
                skill_id="GLOBAL",
                event_type="KILL_SWITCH_RESET",
                delta=0.0,
                approver=user_name,
                notes="Kill switch disengaged. Autonomous safety boundaries restored.",
            )
        return cls._state

    @classmethod
    def evaluate_governance(
        cls,
        skill_id: str,
        amount: Optional[float] = None,
        is_privileged: bool = False,
        is_hiring_rejection: bool = False,
        is_duplicate_recovery: bool = False,
    ) -> Dict[str, Any]:
        """
        Determines if an action can proceed autonomously or requires human approval.
        Enforces never-automate rules, kill switch, and autonomy ladder policies.
        """
        # 1. Kill Switch Guardrail
        if cls._state.kill_switch_active:
            return {
                "can_auto_execute": False,
                "effective_level": AutonomyLevel.L1.value,
                "guardrail_triggered": "KILL_SWITCH_ACTIVE",
                "reason": "Emergency kill switch is engaged. 100% human sign-off enforced.",
            }

        # 2. Never-Automate Guardrails
        if is_privileged:
            return {
                "can_auto_execute": False,
                "effective_level": AutonomyLevel.L1.value,
                "guardrail_triggered": "NEVER_AUTOMATE_PRIVILEGED_ACCESS",
                "reason": "Privileged or root admin access is on the never-automate list. Strictly requires human approval.",
            }

        if amount and amount > 15000.0:
            return {
                "can_auto_execute": False,
                "effective_level": AutonomyLevel.L1.value,
                "guardrail_triggered": "HIGH_VALUE_THRESHOLD_EXCEEDED",
                "reason": f"Amount ₹{amount:,.0f} exceeds autonomous ceiling (₹15,000). Supervisory review mandatory.",
            }

        if is_hiring_rejection:
            return {
                "can_auto_execute": False,
                "effective_level": AutonomyLevel.L1.value,
                "guardrail_triggered": "NEVER_AUTOMATE_HIRING_REJECTION",
                "reason": "Hiring and candidate rejection decisions always stay human. AI only prepares ranking and explanation.",
            }

        if is_duplicate_recovery:
            return {
                "can_auto_execute": False,
                "effective_level": AutonomyLevel.L1.value,
                "guardrail_triggered": "NEVER_AUTOMATE_DUPLICATE_RECOVERY",
                "reason": "Duplicate vendor payouts require human accounting sign-off before initiating clawback.",
            }

        # 3. Autonomy Ladder Check
        skill = cls._skill_metrics.get(skill_id)
        if not skill:
            return {
                "can_auto_execute": False,
                "effective_level": AutonomyLevel.L1.value,
                "guardrail_triggered": "UNKNOWN_SKILL",
                "reason": "Skill not found in registered catalog. Defaulting to L1 human review.",
            }

        current_level = skill["level"]
        if current_level == AutonomyLevel.L0:
            return {
                "can_auto_execute": False,
                "effective_level": AutonomyLevel.L0.value,
                "guardrail_triggered": "L0_SUGGEST_ONLY",
                "reason": "Skill is in L0 training/backtest mode. Suggests only with pre-gathered evidence.",
            }

        if current_level == AutonomyLevel.L1:
            return {
                "can_auto_execute": False,
                "effective_level": AutonomyLevel.L1.value,
                "guardrail_triggered": None,
                "reason": "Skill operates at L1. AI investigates and drafts everything; human approves in one click.",
            }

        if current_level == AutonomyLevel.L2:
            return {
                "can_auto_execute": True,
                "effective_level": AutonomyLevel.L2.value,
                "guardrail_triggered": None,
                "reason": "Skill earned L2 autonomy. Acts autonomously; 10% sample reviewed by humans.",
            }

        if current_level == AutonomyLevel.L3:
            return {
                "can_auto_execute": True,
                "effective_level": AutonomyLevel.L3.value,
                "guardrail_triggered": None,
                "reason": "Skill earned L3 autonomy. Acts alone; humans see exceptions only.",
            }

        return {
            "can_auto_execute": False,
            "effective_level": AutonomyLevel.L1.value,
            "guardrail_triggered": None,
            "reason": "Defaulting to L1 human approval.",
        }

    @classmethod
    def record_trust_event(cls, skill_id: str, event_type: str, delta: float, approver: str, notes: Optional[str] = None):
        """Records trust modification (e.g. approve=+1, edit=-2, reject=-5, error=-10)."""
        ev = TrustEvent(
            id=len(cls._trust_history) + 1,
            skill_id=skill_id,
            event_type=event_type,
            delta=delta,
            approver=approver,
            notes=notes,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        cls._trust_history.append(ev)

        # Update per-skill stats
        if skill_id in cls._skill_metrics:
            sk = cls._skill_metrics[skill_id]
            sk["cases_processed"] += 1
            if event_type == "APPROVE":
                sk["approved_count"] += 1
            elif event_type == "EDIT":
                sk["edited_count"] += 1
            elif event_type == "REJECT":
                sk["rejected_count"] += 1
            
            total = sk["cases_processed"]
            if total > 0:
                sk["accuracy_rate"] = round((sk["approved_count"] / total) * 100, 1)

            # Check promotion to L2: 50+ cases at >= 95%
            if sk["level"] == AutonomyLevel.L1 and total >= 50 and sk["accuracy_rate"] >= 95.0 and skill_id != "resume_screening_rubric":
                sk["can_promote_l2"] = True

    @classmethod
    def promote_skill(cls, skill_id: str, target_level: AutonomyLevel, approver: str) -> Dict[str, Any]:
        """Promotes skill along the Autonomy Ladder (e.g. L0 -> L1 after backtest, L1 -> L2 after 50 cases)."""
        if skill_id not in cls._skill_metrics:
            raise ValueError(f"Skill {skill_id} not registered.")
        sk = cls._skill_metrics[skill_id]
        old_level = sk["level"]
        sk["level"] = target_level
        sk["status"] = "ACTIVE"
        cls.record_trust_event(
            skill_id=skill_id,
            event_type="PROMOTION",
            delta=10.0,
            approver=approver,
            notes=f"Skill promoted from {old_level.value} to {target_level.value} based on measured accuracy.",
        )
        return {
            "skill_id": skill_id,
            "old_level": old_level.value,
            "new_level": target_level.value,
            "status": "PROMOTED",
        }

    @classmethod
    def get_skill_metrics(cls) -> List[Dict[str, Any]]:
        return [{"skill_id": k, **v} for k, v in cls._skill_metrics.items()]

    @classmethod
    def get_trust_history(cls, limit: int = 30) -> List[Dict[str, Any]]:
        return [e.model_dump() for e in reversed(cls._trust_history[-limit:])]
