"""
Academy Training Sandbox & Coach Agent for ZeroTouch Workforce
Allows new joiners to work replayed past cases in a safe sandbox,
grades their reasoning against official playbooks, and maintains a Competency Map.
"""

from typing import Dict, Any, List
from datetime import datetime, timezone

from backend.workforce_models import AcademyRun


class AcademyCoach:
    """
    Simulates the AI Coach guiding a new joiner through an anonymized replayed case.
    Updates the employee's competency map after completion.
    """

    REPLAY_CASE = {
        "case_id": "REPLAY-UPI-404",
        "title": "Anonymized Case: UPI Debit without Credit (₹3,200)",
        "context": "Customer complaints that ₹3,200 was deducted while paying a merchant, but the merchant never received payment. The customer demands an immediate refund.",
        "evidence": {
            "bank_status": "DEBITED (Confirmed)",
            "network_status": "SUCCESS (NPCI Switch)",
            "merchant_status": "NOT_CREDITED",
            "settlement_status": "NOT_FOUND",
            "cibil_score": 740,
            "risk_score": 0.05,
        },
        "questions": [
            {
                "step": 1,
                "title": "Step 1: Ledger Reconciliation",
                "question": "What is the very first step before issuing any refund or messaging the customer?",
                "options": [
                    "Immediately issue a ₹3,200 manual refund to satisfy the customer",
                    "Verify all 4 ledgers (Bank, NPCI, Merchant, Settlement) to confirm money is truly stuck",
                    "Tell the customer to contact the merchant directly without checking",
                    "Escalate immediately to the Head of Support without investigation",
                ],
                "correct_option_index": 1,
                "competency": "ledger_reconciliation",
                "explanation": "Correct! Rule 1.1 dictates checking all 4 system of records to verify the true state of funds before any monetary commitment.",
            },
            {
                "step": 2,
                "title": "Step 2: RBI SLA & Compensation Guidelines",
                "question": "Per RBI Harmonisation of Turnaround Time (TAT), what is the deadline for failed UPI reversals before compensation is due?",
                "options": [
                    "T+5 banking days",
                    "T+1 banking day, after which ₹100/day compensation is auto-payable to the customer",
                    "There is no deadline; it depends on the merchant's bank",
                    "30 calendar days",
                ],
                "correct_option_index": 1,
                "competency": "rbi_sla_compliance",
                "explanation": "Correct! RBI circular DPSS.CO.PD No.629/02.01.014/2019-20 sets T+1 as the hard deadline, mandating ₹100/day compensation thereafter.",
            },
            {
                "step": 3,
                "title": "Step 3: Policy & Credit Ceiling Authorization",
                "question": "The customer has a CIBIL score of 740 and a risk score of 0.05. Does this qualify for autonomous auto-reversal?",
                "options": [
                    "Yes, CIBIL 740 is in the Prime tier with an autonomous ceiling of ₹10,000, and risk 0.05 is below threshold",
                    "No, all payments over ₹1,000 must be manually signed off by a manager",
                    "No, CIBIL score is completely ignored in payment dispute resolutions",
                    "Yes, but only if the customer pays an expedited processing fee",
                ],
                "correct_option_index": 0,
                "competency": "policy_authorization",
                "explanation": "Correct! CIBIL-backed risk profiling grants higher autonomous resolution ceilings to prime customers while protecting against fraud.",
            },
        ],
    }

    @classmethod
    def get_replay_case(cls) -> Dict[str, Any]:
        return cls.REPLAY_CASE

    @classmethod
    def evaluate_joiner_run(cls, joiner_id: str, answers: List[int]) -> AcademyRun:
        questions = cls.REPLAY_CASE["questions"]
        correct_count = 0
        competencies: Dict[str, float] = {
            "ledger_reconciliation": 75.0,
            "rbi_sla_compliance": 70.0,
            "policy_authorization": 65.0,
            "customer_communication": 85.0,
        }

        for i, q in enumerate(questions):
            user_ans = answers[i] if i < len(answers) else -1
            if user_ans == q["correct_option_index"]:
                correct_count += 1
                comp_key = q["competency"]
                competencies[comp_key] = min(100.0, competencies[comp_key] + 20.0)

        total_q = len(questions)
        score = round((correct_count / total_q) * 100, 1)
        passed = score >= 66.0

        if score == 100.0:
            coach_feedback = "Outstanding! You demonstrated mastery of 4-ledger reconciliation, RBI TAT deadlines, and CIBIL risk tiering. Ready for supervised live work."
        elif passed:
            coach_feedback = "Good job! You passed the replay simulation. Review the RBI SLA compensation rules before handling live payment exceptions."
        else:
            coach_feedback = "Review required. Please revisit the core banking ledger reconciliation playbook before re-attempting."

        overall_readiness = round(sum(competencies.values()) / len(competencies), 1)
        competencies["overall_readiness"] = overall_readiness

        run = AcademyRun(
            run_id=f"RUN-{datetime.now(timezone.utc).strftime('%H%M%S')}",
            joiner_id=joiner_id,
            case_id=cls.REPLAY_CASE["case_id"],
            answers=answers,
            score=score,
            passed=passed,
            coach_feedback=coach_feedback,
            competencies=competencies,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        return run
