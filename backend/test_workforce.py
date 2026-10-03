"""
Automated Test Suite for ZeroTouch Workforce Platform
Validates:
1. Seeded Roles & Permissions
2. Multi-Domain Connectors (Support, Finance, IT, HR)
3. Autonomy Governor & Emergency Kill Switch
4. Never-Automate Guardrails (Privileged access, high value, hiring decisions)
5. Skill Learner & 12-Case Historical Backtest Harness
6. Live Capacity Model Formula (Page 5: 1.5 FTE freed)
7. Multi-Agent Command Bar Planner
8. New Joiner Academy & AI Coach Competency Map
"""

import pytest
from backend.workforce_models import AutonomyLevel, DomainType
from backend.workforce_data import SEEDED_ROLES, ORIGINAL_WORKFORCE_CASES, reset_workforce_data
from backend.connectors import ConnectorRegistry
from backend.governor import AutonomyGovernor
from backend.skill_learner import SkillLearner
from backend.capacity_model import compute_capacity_model
from backend.planner import CommandBarPlanner
from backend.academy import AcademyCoach


@pytest.fixture(autouse=True)
def reset_state():
    reset_workforce_data()
    # Ensure kill switch is reset
    gov = AutonomyGovernor.get_state()
    if gov.kill_switch_active:
        AutonomyGovernor.toggle_kill_switch("Test Runner")
    yield
    reset_workforce_data()


def test_seeded_roles_configured():
    """Verify all 6 employee roles from the spec are configured with landing pages."""
    assert len(SEEDED_ROLES) == 6
    role_ids = [r["role_id"] for r in SEEDED_ROLES]
    assert "support_agent" in role_ids
    assert "finance_analyst" in role_ids
    assert "recruiter" in role_ids
    assert "skill_owner" in role_ids
    assert "new_joiner" in role_ids
    assert "manager" in role_ids


def test_connectors_multi_domain():
    """Verify connectors return structured responses across Support, Finance, IT, and HR."""
    # 1. Finance connector
    stmt_lines = ConnectorRegistry.query_bank_statement_lines()
    assert len(stmt_lines) == 4
    assert any(l["match_type"] == "EXACT_AUTO_MATCH" for l in stmt_lines)
    assert any(l["match_type"] == "DUPLICATE_PAYMENT_FLAG" for l in stmt_lines)

    # 2. IT connector
    profile = ConnectorRegistry.lookup_employee_profile("EMP-8821")
    assert profile["role"] == "Product Designer"
    pol_allowed = ConnectorRegistry.check_tool_access_policy("Product Designer", "Figma Pro")
    assert pol_allowed["allowed"] is True

    # 3. IT privileged tool check
    pol_priv = ConnectorRegistry.check_tool_access_policy("Frontend Developer", "AWS Root Access")
    assert pol_priv["allowed"] is False
    assert pol_priv["is_privileged"] is True

    # 4. HR candidate evaluation (fairness guardrail: protected attributes stripped)
    cand = ConnectorRegistry.get_candidate_evaluation("cand-8812", "Staff Backend Engineer")
    assert cand["protected_attributes_stripped"] is True
    assert cand["never_auto_reject"] is True
    assert cand["total_score_percentage"] == 85.0


def test_autonomy_governor_kill_switch():
    """Verify toggling emergency kill switch immediately blocks autonomous executions."""
    gov = AutonomyGovernor.get_state()
    assert gov.kill_switch_active is False

    # Check skill at L2 (e.g. settlement_fee_breakdown) normally can auto-execute
    eval_normal = AutonomyGovernor.evaluate_governance("settlement_fee_breakdown", amount=5000.0)
    assert eval_normal["can_auto_execute"] is True

    # Engage kill switch
    AutonomyGovernor.toggle_kill_switch("Rajesh Mehra")
    assert AutonomyGovernor.get_state().kill_switch_active is True

    # Now same skill must be forced to human approval
    eval_killed = AutonomyGovernor.evaluate_governance("settlement_fee_breakdown", amount=5000.0)
    assert eval_killed["can_auto_execute"] is False
    assert eval_killed["guardrail_triggered"] == "KILL_SWITCH_ACTIVE"

    # Disengage kill switch
    AutonomyGovernor.toggle_kill_switch("Rajesh Mehra")
    assert AutonomyGovernor.get_state().kill_switch_active is False


def test_never_automate_guardrails():
    """Verify that privileged access, high amounts, and hiring rejections are never automated."""
    # 1. Privileged access grant -> Never automate
    res_priv = AutonomyGovernor.evaluate_governance("it_tool_access_grant", is_privileged=True)
    assert res_priv["can_auto_execute"] is False
    assert res_priv["guardrail_triggered"] == "NEVER_AUTOMATE_PRIVILEGED_ACCESS"

    # 2. High amount > ₹15,000 -> Supervisory review
    res_amt = AutonomyGovernor.evaluate_governance("settlement_fee_breakdown", amount=45000.0)
    assert res_amt["can_auto_execute"] is False
    assert res_amt["guardrail_triggered"] == "HIGH_VALUE_THRESHOLD_EXCEEDED"

    # 3. Hiring rejection -> Never automate
    res_hire = AutonomyGovernor.evaluate_governance("resume_screening_rubric", is_hiring_rejection=True)
    assert res_hire["can_auto_execute"] is False
    assert res_hire["guardrail_triggered"] == "NEVER_AUTOMATE_HIRING_REJECTION"


def test_skill_studio_spec_and_backtest():
    """Verify live teaching of IT access request: spec synthesis + 12-case backtest + L1 promotion."""
    # Step 1: Synthesize spec
    spec = SkillLearner.synthesize_skill_spec(
        domain="it",
        task_name="IT Standard Tool Provisioning",
        recorded_actions=[{"tool": "okta", "action": "lookup"}],
        employee_why_note="Approved per Design Team standard bundle policy.",
        owner="Vikram Malhotra",
    )
    assert spec.skill_id == "it_tool_access_grant"
    assert spec.autonomy == AutonomyLevel.L0  # Starts L0

    # Step 2: Run historical backtest across 12 requests
    report = SkillLearner.run_historical_backtest(spec)
    assert report.cases_tested == 12
    assert report.passed_count == 12
    assert report.match_rate == 100.0
    assert report.ready_for_l1 is True

    # Step 3: Publish to L1
    pub = SkillLearner.publish_skill_to_l1(spec, approver="Vikram Malhotra")
    assert pub["status"] == "PUBLISHED_ACTIVE"
    assert pub["autonomy_level"] == "L1"


def test_capacity_model_formula():
    """Verify Page 5 capacity model formula calculations."""
    cap = compute_capacity_model(
        team_size=10,
        repetitive_pct=0.40,
        skill_coverage_pct=0.60,
        handling_time_saved_pct=0.80,
        oversight_effort_pct=0.20,
    )
    assert cap["repetitive_fte"] == 4.0
    assert cap["gross_freed_fte"] == 1.92
    assert cap["net_freed_fte"] == 1.54  # "About 1.5 FTE freed by day 100"
    assert cap["hours_saved_per_month"] > 240


def test_command_bar_planner_scenarios():
    """Verify multi-agent planner handles SLA chases and stops at compliance approval gates."""
    # 1. Chase refunds past SLA (Minute 1:30 of demo)
    res_sla = CommandBarPlanner.execute_command("Chase all refunds past SLA")
    assert res_sla["status"] == "SUCCESS"
    assert len(res_sla["plan_steps"]) == 5
    assert "CASE-SPT-202" in res_sla["affected_cases"]

    # 2. Clear settlement holds -> stops at approval gate for S306 expired KYC
    res_holds = CommandBarPlanner.execute_command("Clear yesterday's pending settlement holds")
    assert res_holds["status"] == "APPROVAL_REQUIRED"
    assert res_holds["approval_required"] is True
    assert res_holds["approval_case"]["case_id"] == "CASE-SPT-306"


def test_academy_coach_evaluation():
    """Verify New Joiner Academy replay grading and competency map generation."""
    replay = AcademyCoach.get_replay_case()
    assert replay["case_id"] == "REPLAY-UPI-404"
    assert len(replay["questions"]) == 3

    # Submit 100% correct answers
    correct_answers = [q["correct_option_index"] for q in replay["questions"]]
    run = AcademyCoach.evaluate_joiner_run("Kavita Rao", correct_answers)
    assert run.score == 100.0
    assert run.passed is True
    assert "ledger_reconciliation" in run.competencies
    assert run.competencies["overall_readiness"] >= 85.0
