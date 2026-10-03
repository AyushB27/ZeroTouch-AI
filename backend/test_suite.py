"""
Unit & Integration Test Suite for ZeroTouch AI
Validates Canonical Case State, Action Gateway Idempotency, Policy Precedence,
Independent Verification, Customer Data Segregation, and the 8-Scenario Benchmark Matrix.
"""

import pytest
from backend.database import (
    init_db,
    db_reset_all,
    db_get_all_transactions,
    db_get_all_cases,
    db_get_case_by_tx,
    case_id_for_tx,
)
from backend.models import Evidence, ExceptionClassification
from backend.policy import evaluate_policy
from backend.action_gateway import ActionGateway, generate_idempotency_key
from backend.orchestrator import run_resolution
from backend.evaluation import run_full_evaluation


@pytest.fixture(autouse=True)
def reset_database():
    """Ensure a clean database state before each test."""
    init_db()
    db_reset_all()
    yield
    db_reset_all()


def test_canonical_cases_seeded():
    """Verify that all transactions have initialized canonical cases with formatted IDs."""
    txs = db_get_all_transactions()
    cases = db_get_all_cases()
    assert len(txs) == 8
    assert len(cases) == 8

    for tx in txs:
        tx_id = tx["transaction_id"]
        expected_cid = case_id_for_tx(tx_id)
        case = db_get_case_by_tx(tx_id)
        assert case is not None
        assert case["case_id"] == expected_cid
        assert case["amount"] == tx["amount"]


def test_policy_deterministic_rule_ids():
    """Verify that policy engine returns explicit rule IDs and formal exception taxonomy."""
    # 1. Clean W1 stuck debit (Prime CIBIL)
    ev_w1 = Evidence(
        transaction_id="TX9281",
        customer_name="Aarav Sharma",
        bank="DEBITED",
        network="SUCCESS",
        merchant="NOT_CREDITED",
        settlement="NOT_FOUND",
        amount=2500.0,
        risk=0.08,
        cibil_score=785,
        is_first_time_user=False,
        previous_refund=False,
    )
    dec_w1 = evaluate_policy(ev_w1)
    assert dec_w1.decision == "AUTO_REVERSAL"
    assert dec_w1.rule_id == "RULE_W1_AUTO_REVERSAL_01"
    assert dec_w1.classification == ExceptionClassification.W1_DEBIT_NOT_CREDITED.value
    assert dec_w1.authorized is True

    # 2. High-value first-time user (Subprime CIBIL) -> Mandatory Escalate
    ev_ftu = Evidence(
        transaction_id="TX9342",
        customer_name="Kunal Verma",
        bank="DEBITED",
        network="UNKNOWN",
        merchant="NOT_CREDITED",
        settlement="UNKNOWN",
        amount=18000.0,
        risk=0.72,
        cibil_score=590,
        is_first_time_user=True,
        previous_refund=False,
    )
    dec_ftu = evaluate_policy(ev_ftu)
    assert dec_ftu.decision == "HUMAN_ESCALATION"
    assert dec_ftu.rule_id == "RULE_W1_HIGH_RISK_FTU_01"
    assert dec_ftu.classification == ExceptionClassification.W1_HIGH_RISK_FIRST_TIME.value
    assert dec_ftu.authorized is False

    # 3. Compliance expired KYC hold
    ev_kyc = Evidence(
        transaction_id="S306",
        customer_name="QuickBite Cafe",
        bank="HELD",
        network="SUCCESS",
        merchant="EXPECTING_CREDIT",
        settlement="HELD_KYC_EXPIRED",
        amount=45000.0,
        risk=0.88,
        cibil_score=610,
        is_first_time_user=False,
        previous_refund=False,
    )
    dec_kyc = evaluate_policy(ev_kyc)
    assert dec_kyc.decision == "COMPLIANCE_HOLD"
    assert dec_kyc.rule_id == "RULE_W3_KYC_HOLD_01"
    assert dec_kyc.authorized is False


def test_action_gateway_idempotency():
    """Verify that Action Gateway blocks duplicate executions and prevents double money movement."""
    tx_id = "TX9281"
    # First execution
    res1 = ActionGateway.execute_action(
        tx_id=tx_id,
        action_type="AUTO_REVERSAL",
        payload={"amount": 2500.0},
        policy_version="2.0",
        rule_id="RULE_W1_AUTO_REVERSAL_01",
    )
    assert res1["status"] in ("VERIFIED", "EXECUTED")
    assert res1["verified"] is True
    assert res1["action_id"] == "REV-TX9281"

    # Second execution attempt with identical parameters
    res2 = ActionGateway.execute_action(
        tx_id=tx_id,
        action_type="AUTO_REVERSAL",
        payload={"amount": 2500.0},
        policy_version="2.0",
        rule_id="RULE_W1_AUTO_REVERSAL_01",
    )
    assert res2["status"] == "ALREADY_EXECUTED"
    assert res2["action_id"] == "REV-TX9281"


def test_independent_verification_failure_handling():
    """Verify that an independent verification failure flags FAILED instead of completing."""
    res = ActionGateway.verify_action(
        tx_id="TX9281",
        action_type="AUTO_REVERSAL",
        action_ref="REV-TX9281",
        simulate_failure=True,
    )
    assert res["verified"] is False
    assert "simulated_network_partition" in res["checks"]


def test_customer_data_segregation():
    """Verify that customer timeline strips sensitive internal risk scores and raw traces."""
    from backend.main import _customer_timeline
    res = run_resolution("TX9281")
    timeline = _customer_timeline([e.model_dump() for e in res.events])
    assert len(timeline) > 0
    # Customer labels must be user-friendly phrases
    for item in timeline:
        assert "risk_score" not in item["label"].lower()
        assert "cibil" not in item["label"].lower()


def test_full_benchmark_matrix():
    """Run complete 8-scenario benchmark and safety suite (100% pass expected)."""
    report = run_full_evaluation()
    assert report["scenario_summary"]["passed"] == 8
    assert report["scenario_summary"]["total"] == 8
    assert report["scenario_summary"]["pass_rate_percentage"] == 100.0
    assert report["safety_summary"]["passed"] == 3
    assert report["safety_summary"]["all_passed"] is True
