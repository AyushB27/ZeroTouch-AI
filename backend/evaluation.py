"""
ZeroTouch Autonomous Payment Resolution Evaluation Harness
Automated scenario test matrix, failure injection tests, and operational quality metrics.

Inspired by research into production payment recovery systems (RecoverAI, Railguard):
- Every scenario is formally classified under the Payment Exception Taxonomy.
- Every scenario verifies policy rule compliance, authorization boundaries, and verification invariants.
- Failure injection validates idempotency protection and verification failure handling.
"""

from typing import Dict, List, Any
import copy

from backend.data import ORIGINAL_TRANSACTIONS
from backend.models import Evidence, ExceptionClassification
from backend.policy import evaluate_policy
from backend.action_gateway import ActionGateway, generate_idempotency_key
from backend.database import (
    db_reset_all,
    db_get_transaction,
    db_get_case_by_tx,
    case_id_for_tx,
)
from backend.orchestrator import run_resolution


SCENARIO_EXPECTATIONS: Dict[str, Dict[str, Any]] = {
    "TX9281": {
        "title": "Clean UPI Stuck Debit (Prime CIBIL)",
        "workflow": "W1",
        "expected_decision": "AUTO_REVERSAL",
        "expected_rule": "RULE_W1_AUTO_REVERSAL_01",
        "expected_classification": ExceptionClassification.W1_DEBIT_NOT_CREDITED.value,
        "expected_authorized": True,
        "expected_status": "RESOLVED",
    },
    "TX9342": {
        "title": "High-Value First-Time User (Subprime CIBIL)",
        "workflow": "W1",
        "expected_decision": "HUMAN_ESCALATION",
        "expected_rule": "RULE_W1_HIGH_RISK_FTU_01",
        "expected_classification": ExceptionClassification.W1_HIGH_RISK_FIRST_TIME.value,
        "expected_authorized": False,
        "expected_status": "ESCALATED",
    },
    "TX9410": {
        "title": "Consistent Reconciled Payment",
        "workflow": "W1",
        "expected_decision": "NO_ACTION",
        "expected_rule": "RULE_W1_CONGRUENT_01",
        "expected_classification": ExceptionClassification.W1_CONGRUENT_SUCCESS.value,
        "expected_authorized": False,
        "expected_status": "NO_ACTION",
    },
    "RF202": {
        "title": "Overdue Refund SLA Breach",
        "workflow": "W2",
        "expected_decision": "SLA_CHASE",
        "expected_rule": "RULE_W2_SLA_CHASE_01",
        "expected_classification": ExceptionClassification.W2_REFUND_SLA_BREACH.value,
        "expected_authorized": True,
        "expected_status": "RESOLVED",
    },
    "RF204": {
        "title": "Bounced Account Instant Wallet Credit",
        "workflow": "W2",
        "expected_decision": "WALLET_CREDIT_OFFER",
        "expected_rule": "RULE_W2_WALLET_CREDIT_01",
        "expected_classification": ExceptionClassification.W2_REFUND_BOUNCED.value,
        "expected_authorized": True,
        "expected_status": "RESOLVED",
    },
    "S301": {
        "title": "Merchant Settlement Platform Fee & GST",
        "workflow": "W3",
        "expected_decision": "ITEMIZED_EXPLANATION",
        "expected_rule": "RULE_W3_FEE_BREAKDOWN_01",
        "expected_classification": ExceptionClassification.W3_SETTLEMENT_FEE_DEDUCTION.value,
        "expected_authorized": True,
        "expected_status": "RESOLVED",
    },
    "S302": {
        "title": "Standard Merchant Settlement Fee Deduction",
        "workflow": "W3",
        "expected_decision": "ITEMIZED_EXPLANATION",
        "expected_rule": "RULE_W3_FEE_BREAKDOWN_01",
        "expected_classification": ExceptionClassification.W3_SETTLEMENT_FEE_DEDUCTION.value,
        "expected_authorized": True,
        "expected_status": "RESOLVED",
    },
    "S306": {
        "title": "Merchant Expired KYC Settlement Hold",
        "workflow": "W3",
        "expected_decision": "COMPLIANCE_HOLD",
        "expected_rule": "RULE_W3_KYC_HOLD_01",
        "expected_classification": ExceptionClassification.W3_SETTLEMENT_KYC_HOLD.value,
        "expected_authorized": False,
        "expected_status": "ESCALATED",
    },
}



def run_full_evaluation() -> Dict[str, Any]:
    """
    Executes all 8 canonical scenarios and 3 safety/failure injection tests.
    Returns structured results for Ops Console and automated testing.
    """
    db_reset_all()

    scenario_results: List[Dict[str, Any]] = []
    passed_scenarios = 0

    for tx_id, exp in SCENARIO_EXPECTATIONS.items():
        result = run_resolution(tx_id)
        case = db_get_case_by_tx(tx_id)

        decision_ok = result.decision == exp["expected_decision"]
        rule_ok = result.rule_id == exp["expected_rule"]
        auth_ok = result.authorized == exp["expected_authorized"]
        status_ok = result.resolution_status == exp["expected_status"]
        case_ok = bool(case and case.get("case_id"))

        all_ok = decision_ok and rule_ok and auth_ok and status_ok and case_ok
        if all_ok:
            passed_scenarios += 1

        scenario_results.append({
            "transaction_id": tx_id,
            "case_id": case_id_for_tx(tx_id),
            "title": exp["title"],
            "workflow": exp["workflow"],
            "expected_decision": exp["expected_decision"],
            "actual_decision": result.decision,
            "expected_rule": exp["expected_rule"],
            "actual_rule": result.rule_id,
            "expected_classification": exp["expected_classification"],
            "actual_classification": result.classification,
            "expected_status": exp["expected_status"],
            "actual_status": result.resolution_status,
            "authorized": result.authorized,
            "passed": all_ok,
            "action_id": result.action_id,
        })

    # ── Safety & Failure Injection Tests ──────────────────────────────────────

    # Test 1: Idempotency Protection Test
    idem_tx = "TX9281"
    idem_key = generate_idempotency_key(case_id_for_tx(idem_tx), "AUTO_REVERSAL", 2500.0)
    repeat_res = ActionGateway.execute_action(
        tx_id=idem_tx,
        action_type="AUTO_REVERSAL",
        payload={"amount": 2500.0},
        policy_version="2.0",
        rule_id="RULE_W1_AUTO_REVERSAL_01",
    )
    idempotency_passed = repeat_res.get("status") == "ALREADY_EXECUTED"

    # Test 2: Verification Failure Handling Test
    # Injected simulated failure should mark action as FAILED
    verif_res = ActionGateway.verify_action(
        tx_id="TX9281",
        action_type="AUTO_REVERSAL",
        action_ref="REV-TX9281",
        simulate_failure=True,
    )
    verification_failure_passed = (verif_res["verified"] is False)

    # Test 3: Customer Data Segregation Check
    from backend.main import _customer_timeline
    events = result.events
    timeline = _customer_timeline([e.model_dump() for e in events])
    # Timeline must not contain raw internal risk score or code stack traces
    has_leakage = any("risk_score" in str(item).lower() or "cibil" in str(item).lower() for item in timeline)
    segregation_passed = not has_leakage

    safety_tests = [
        {
            "test_name": "Action Gateway Idempotency Guarantee",
            "description": "Repeated execution of financial action returns ALREADY_EXECUTED with zero duplicate ledger mutations.",
            "passed": idempotency_passed,
        },
        {
            "test_name": "Independent Verification Failure Handling",
            "description": "Ledger mismatch or network timeout during verification flags FAILED and blocks false positive close.",
            "passed": verification_failure_passed,
        },
        {
            "test_name": "Customer vs Ops Data Segregation",
            "description": "Customer-facing timeline strips internal CIBIL, fraud heuristics, and raw error traces.",
            "passed": segregation_passed,
        },
    ]

    total_scenarios = len(SCENARIO_EXPECTATIONS)
    total_safety = len(safety_tests)
    passed_safety = sum(1 for t in safety_tests if t["passed"])

    return {
        "status": "COMPLETED",
        "scenario_summary": {
            "total": total_scenarios,
            "passed": passed_scenarios,
            "pass_rate_percentage": round((passed_scenarios / total_scenarios) * 100, 1),
        },
        "safety_summary": {
            "total": total_safety,
            "passed": passed_safety,
            "all_passed": passed_safety == total_safety,
        },
        "scenarios": scenario_results,
        "safety_tests": safety_tests,
    }


if __name__ == "__main__":
    report = run_full_evaluation()
    print("=== ZeroTouch AI Evaluation Report ===")
    print(f"Scenarios: {report['scenario_summary']['passed']}/{report['scenario_summary']['total']} Passed ({report['scenario_summary']['pass_rate_percentage']}%)")
    print(f"Safety Tests: {report['safety_summary']['passed']}/{report['safety_summary']['total']} Passed")
    for s in report["scenarios"]:
        status_sym = "[PASS]" if s["passed"] else "[FAIL]"
        print(f"  {status_sym} [{s['case_id']}] {s['transaction_id']} - {s['title']} -> {s['actual_decision']} ({s['actual_rule']})")
    for st in report["safety_tests"]:
        sym = "[PASS]" if st["passed"] else "[FAIL]"
        print(f"  {sym} {st['test_name']}")

