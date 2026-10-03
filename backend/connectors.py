"""
Universal Connector Layer for ZeroTouch Workforce
Provides typed tool adapters with per-role/per-skill permissions, rate limits,
schema validation, and audit hooks across Support, Finance, IT, and HR domains.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import hashlib


class ConnectorError(Exception):
    pass


class ConnectorRegistry:
    """
    Central registry for mock internal tool adapters.
    Simulates production Paytm internal systems (Bank Gateway, General Ledger, Okta IdP, ATS).
    """

    # ── 1. Support / Payment Domain Connectors ─────────────────────────────────

    @staticmethod
    def get_payment_reconciliation(transaction_id: str) -> Dict[str, Any]:
        """Queries Bank, NPCI, Merchant, and Nodal Ledgers."""
        from backend.database import db_get_transaction
        tx = db_get_transaction(transaction_id)
        if not tx:
            raise ConnectorError(f"Transaction {transaction_id} not found on core banking rail.")
        return {
            "transaction_id": transaction_id,
            "bank_status": tx["bank_status"],
            "network_status": tx["network_status"],
            "merchant_status": tx["merchant_status"],
            "settlement_status": tx["settlement_status"],
            "amount": tx["amount"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "CoreBanking-NPCI-Gateway",
        }

    @staticmethod
    def dispatch_bank_chase(refund_id: str, txn_id: str, reason: str) -> Dict[str, Any]:
        """Dispatches automated escalation to beneficiary bank API."""
        ref = f"CHASE-{refund_id}-{txn_id[:6]}"
        return {
            "action": "BANK_ESCALATION_CHASE",
            "chase_reference": ref,
            "status": "DISPATCHED_TO_NPCI_GATEWAY",
            "expected_eta_hours": 24,
            "compensation_flag": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def issue_wallet_credit(customer_id: str, amount: float, reason: str) -> Dict[str, Any]:
        """Instant credit to customer's Paytm Wallet for bounced refunds."""
        ref = f"WAL-CRED-{hashlib.sha256(f'{customer_id}:{amount}'.encode()).hexdigest()[:8].upper()}"
        return {
            "action": "WALLET_CREDIT",
            "wallet_txn_id": ref,
            "amount": amount,
            "status": "CONFIRMED_LEDGER_POSTED",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ── 2. Finance Domain Connectors ──────────────────────────────────────────

    @staticmethod
    def query_bank_statement_lines() -> List[Dict[str, Any]]:
        """Returns mock incoming bank statement feed for matching."""
        return [
            {
                "line_id": "STMT-901",
                "bank_ref": "HDFC-IN-98210",
                "value_date": "2026-10-02",
                "description": "UPI Payout Nodal Settlement Batch 41",
                "bank_amount": 24500.0,
                "ledger_match_id": "TX-SETTLE-41",
                "ledger_amount": 24500.0,
                "match_type": "EXACT_AUTO_MATCH",
                "status": "MATCHED",
                "rule_applied": "Auto-match, no review required",
            },
            {
                "line_id": "STMT-902",
                "bank_ref": "ICICI-IN-44109",
                "value_date": "2026-10-02",
                "description": "Merchant Settlement QuickBite Cafe",
                "bank_amount": 49000.0,
                "ledger_match_id": "S302",
                "ledger_amount": 50000.0,
                "variance": -1000.0,
                "match_type": "FEE_GST_EXPLAINED",
                "status": "MATCHED_WITH_VARIANCE_NOTE",
                "rule_applied": "Difference explained by MDR fee (₹847) & GST (₹153)",
            },
            {
                "line_id": "STMT-903",
                "bank_ref": "SBI-IN-31002",
                "value_date": "2026-09-28",
                "description": "Unidentified NEFT Inward Payout",
                "bank_amount": 14200.0,
                "ledger_match_id": None,
                "ledger_amount": 0.0,
                "match_type": "UNMATCHED_AGING_OVER_3_DAYS",
                "status": "DRAFT_QUERY_PREPARED",
                "rule_applied": "Aged 5 days beyond SLA. Query drafted to Bank Ops.",
            },
            {
                "line_id": "STMT-904",
                "bank_ref": "AXIS-IN-77123",
                "value_date": "2026-10-01",
                "description": "Vendor Invoice: CloudNet Hosting Inv #4491",
                "bank_amount": 12000.0,
                "ledger_match_id": "VEND-4491",
                "ledger_amount": 12000.0,
                "match_type": "DUPLICATE_PAYMENT_FLAG",
                "status": "FLAGGED_FOR_HUMAN_RECOVERY",
                "rule_applied": "Duplicate payment detected. Never auto-recover; routed to Senior AP Analyst.",
            },
        ]

    # ── 3. IT Access Domain Connectors (The Live-Taught Skill) ────────────────

    @staticmethod
    def lookup_employee_profile(employee_id: str) -> Dict[str, Any]:
        """Queries Okta/Workday employee identity directory."""
        mock_directory = {
            "EMP-8821": {
                "name": "Rohan Joshi",
                "role": "Product Designer",
                "department": "Design",
                "manager": "Ananya Roy",
                "location": "Noida",
                "employment_status": "FULL_TIME",
                "is_probation": False,
            },
            "EMP-8840": {
                "name": "Mansi Gupta",
                "role": "Frontend Developer",
                "department": "Engineering",
                "manager": "Kunal Verma",
                "location": "Bengaluru",
                "employment_status": "FULL_TIME",
                "is_probation": False,
            },
            "EMP-9104": {
                "name": "Devansh Saxena",
                "role": "Intern - Backend",
                "department": "Engineering",
                "manager": "Siddharth Rao",
                "location": "Delhi",
                "employment_status": "INTERN",
                "is_probation": True,
            },
        }
        return mock_directory.get(employee_id, {
            "name": f"Employee {employee_id}",
            "role": "Standard Contributor",
            "department": "General",
            "manager": "Lead",
            "location": "Remote",
            "employment_status": "FULL_TIME",
            "is_probation": False,
        })

    @staticmethod
    def check_tool_access_policy(role: str, tool_name: str) -> Dict[str, Any]:
        """Checks enterprise RBAC entitlement matrix for standard tools."""
        standard_bundles = {
            "Product Designer": ["Figma Pro", "Slack", "Jira", "Notion", "Miro"],
            "Frontend Developer": ["GitHub Enterprise", "Slack", "Jira", "VS Code Cloud", "Figma Viewer"],
            "Backend Developer": ["GitHub Enterprise", "Slack", "Jira", "Datadog Read-Only", "Postman Enterprise"],
            "Intern - Backend": ["GitHub Enterprise Read-Only", "Slack", "Jira"],
        }

        privileged_tools = ["AWS Root Access", "Production DB Admin", "Okta Super Admin", "Vault Root Token"]

        if tool_name in privileged_tools:
            return {
                "allowed": False,
                "is_privileged": True,
                "policy_rule": "RULE_NEVER_AUTOMATE_PRIVILEGED_ACCESS",
                "reason": f"Tool '{tool_name}' grants root/admin permissions. Strictly requires CISO/Security Director approval.",
                "action": "ROUTE_TO_HUMAN_SECURITY_DESK",
            }

        allowed_tools = standard_bundles.get(role, ["Slack", "Google Workspace"])
        if tool_name in allowed_tools:
            return {
                "allowed": True,
                "is_privileged": False,
                "policy_rule": "RULE_STANDARD_ROLE_ENTITLEMENT",
                "reason": f"Tool '{tool_name}' is pre-approved for role '{role}'.",
                "action": "AUTO_PROVISION_ELIGIBLE",
            }

        return {
            "allowed": False,
            "is_privileged": False,
            "policy_rule": "RULE_NON_STANDARD_TOOL_REQUEST",
            "reason": f"Tool '{tool_name}' is not in standard bundle for '{role}'. Manager approval required.",
            "action": "ESCALATE_TO_MANAGER",
        }

    @staticmethod
    def grant_tool_license(employee_id: str, tool_name: str, approver: str, reason: str) -> Dict[str, Any]:
        """Provisions license in target tool API (e.g. Figma / Okta / GitHub)."""
        grant_id = f"GRN-{hashlib.sha256(f'{employee_id}:{tool_name}:{approver}'.encode()).hexdigest()[:8].upper()}"
        return {
            "grant_id": grant_id,
            "employee_id": employee_id,
            "tool_name": tool_name,
            "status": "PROVISIONED_ACTIVE",
            "provisioned_by": approver,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ── 4. HR & Hiring Domain Connectors ──────────────────────────────────────

    @staticmethod
    def get_candidate_evaluation(candidate_id: str, job_title: str) -> Dict[str, Any]:
        """Provides explainable rubric score per criterion. Strips protected attributes."""
        return {
            "candidate_id": candidate_id,
            "name": "Ananya Sundaram",
            "target_role": job_title,
            "protected_attributes_stripped": True,  # Age, gender, photo, marital status removed
            "rubric_scores": [
                {"criterion": "System Design & Architecture", "score": 9, "max": 10, "rationale": "Built distributed payment reconciliation engine at scale."},
                {"criterion": "Fintech / Payments Domain Experience", "score": 8, "max": 10, "rationale": "Strong familiarity with UPI 2.0 specs and ISO 8583."},
                {"criterion": "Python & Async Microservices", "score": 9, "max": 10, "rationale": "Extensive experience with FastAPI, Redis, and LangGraph."},
                {"criterion": "Cultural & Team Leadership", "score": 8, "max": 10, "rationale": "Led sprint squads of 6 engineers effectively."},
            ],
            "total_score_percentage": 85.0,
            "recommendation": "ADVANCE_TO_PANEL_INTERVIEW",
            "never_auto_reject": True,  # System guardrail: never auto-rejects candidates
            "interview_kit_drafted": True,
        }
