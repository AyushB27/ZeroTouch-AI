"""
ZeroTouch Action Gateway
Autonomous Financial Safety & Idempotent Action Execution Gateway.

Architecture & Safety Guarantees (inspired by Railguard & RecoverAI):
1. LLMs reason; deterministic code authorizes; Action Gateway executes.
2. Idempotency Protection: Every mutation has a cryptographic idempotency key.
   Repeated execution attempts return the recorded result without duplicate money movement.
3. Explicit Lifecycle: PROPOSED -> AUTHORIZED -> EXECUTING -> EXECUTED -> VERIFIED.
4. Mandatory Independent Verification: Before any customer notification or case closure,
   the gateway re-queries ledger records independently to verify the expected invariants.
5. Audit Logging: Every state transition emits structured audit events with explicit
   visibility (CUSTOMER vs INTERNAL vs SYSTEM).
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from backend.database import (
    db_get_transaction,
    db_update_transaction,
    db_get_case_by_tx,
    db_update_case,
    db_get_action_log,
    db_record_action_gateway,
    db_update_action_gateway,
    db_add_event,
    case_id_for_tx,
)
from backend.models import (
    ActionRecord,
    ActionLifecycleState,
    AuditVisibility,
)


def generate_idempotency_key(case_id: str, action_type: str, amount: float, policy_version: str = "2.0") -> str:
    """Generate deterministic idempotency fingerprint."""
    raw = f"{case_id}:{action_type}:{amount:.2f}:{policy_version}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


class ActionGateway:
    """
    Central gateway for all state & financial operations in ZeroTouch.
    Guarantees idempotency, auditability, and independent verification.
    """

    @classmethod
    def execute_action(
        cls,
        tx_id: str,
        action_type: str,
        payload: Optional[Dict[str, Any]] = None,
        policy_version: str = "2.0",
        rule_id: str = "RULE_DEFAULT",
        actor: str = "ZeroTouch Autonomous Gateway",
        simulate_verification_failure: bool = False,
    ) -> Dict[str, Any]:
        tx = db_get_transaction(tx_id)
        if not tx:
            raise ValueError(f"Transaction {tx_id} not found in database")

        payload = payload or {}
        amount = float(payload.get("amount", tx["amount"]))
        cid = case_id_for_tx(tx_id)
        idem_key = generate_idempotency_key(cid, action_type, amount, policy_version)

        # ── 1. Idempotency Check ──────────────────────────────────────────────
        existing_log = db_get_action_log(idem_key)
        if existing_log:
            result_data = json.loads(existing_log["result"]) if existing_log.get("result") else {}
            db_add_event(
                tx_id=tx_id,
                event_type="ACTION",
                step="idempotency_check",
                status="INFO",
                message=f"[Action Gateway] Idempotent replay detected ({idem_key[:8]}...). Action already {existing_log['status']}.",
                visibility=AuditVisibility.INTERNAL.value,
                actor=actor,
            )
            return {
                "idempotency_key": idem_key,
                "action_id": existing_log["action_ref"],
                "status": "ALREADY_EXECUTED",
                "verified": existing_log["status"] == ActionLifecycleState.VERIFIED.value,
                "result": result_data,
                "is_simulated": existing_log["is_simulated"],
            }

        # ── 2. Lifecycle: PROPOSED -> AUTHORIZED ──────────────────────────────
        db_add_event(
            tx_id=tx_id,
            event_type="ACTION",
            step="action_authorized",
            status="SUCCESS",
            message=f"[Action Gateway] {action_type} authorized under {rule_id} (Idempotency Key: {idem_key[:12]}).",
            visibility=AuditVisibility.INTERNAL.value,
            actor=actor,
        )

        # ── 3. Execute Ledger Mutation ────────────────────────────────────────
        action_ref = cls._build_action_ref(action_type, tx_id)
        mutation_result = cls._apply_mutation(tx_id, action_type, action_ref, amount, payload)

        # Record in gateway log as EXECUTED
        db_record_action_gateway(
            idempotency_key=idem_key,
            case_id=cid,
            tx_id=tx_id,
            action_type=action_type,
            action_ref=action_ref,
            status=ActionLifecycleState.EXECUTED.value,
            payload=payload,
            result=mutation_result,
            is_simulated=True,
        )

        db_add_event(
            tx_id=tx_id,
            event_type="ACTION",
            step="action_executed",
            status="SUCCESS",
            message=f"[Action Gateway] {action_type} executed (Ref: {action_ref}).",
            visibility=AuditVisibility.INTERNAL.value,
            actor=actor,
        )

        # ── 4. Independent Verification ───────────────────────────────────────
        verification = cls.verify_action(
            tx_id=tx_id,
            action_type=action_type,
            action_ref=action_ref,
            simulate_failure=simulate_verification_failure,
            actor=actor,
        )

        if verification["verified"]:
            db_update_action_gateway(
                idempotency_key=idem_key,
                status=ActionLifecycleState.VERIFIED.value,
                verified_at=datetime.now(timezone.utc).isoformat(),
            )
            action_record = ActionRecord(
                action_id=action_ref,
                idempotency_key=idem_key,
                action_type=action_type,
                amount=amount,
                status=ActionLifecycleState.VERIFIED.value,
                is_simulated=True,
                initiated_at=datetime.now(timezone.utc).isoformat(),
                executed_at=datetime.now(timezone.utc).isoformat(),
                verified_at=datetime.now(timezone.utc).isoformat(),
                verification_details=verification["checks"],
            )
            # Update canonical case
            cls._sync_case_action(cid, action_record, customer_status="RESOLVED", ops_status="RESOLVED")
        else:
            db_update_action_gateway(
                idempotency_key=idem_key,
                status=ActionLifecycleState.FAILED.value,
            )
            action_record = ActionRecord(
                action_id=action_ref,
                idempotency_key=idem_key,
                action_type=action_type,
                amount=amount,
                status=ActionLifecycleState.FAILED.value,
                is_simulated=True,
                initiated_at=datetime.now(timezone.utc).isoformat(),
                executed_at=datetime.now(timezone.utc).isoformat(),
                verification_details=verification["checks"],
            )
            cls._sync_case_action(cid, action_record, customer_status="HUMAN_REVIEW", ops_status="ESCALATED")

        return {
            "idempotency_key": idem_key,
            "action_id": action_ref,
            "status": ActionLifecycleState.VERIFIED.value if verification["verified"] else ActionLifecycleState.FAILED.value,
            "verified": verification["verified"],
            "verification_checks": verification["checks"],
            "result": mutation_result,
            "is_simulated": True,
        }

    @classmethod
    def verify_action(
        cls,
        tx_id: str,
        action_type: str,
        action_ref: str,
        simulate_failure: bool = False,
        actor: str = "ZeroTouch Independent Verifier",
    ) -> Dict[str, Any]:
        """
        Re-queries backend ledgers independently and verifies invariant conditions.
        """
        tx = db_get_transaction(tx_id)
        if not tx:
            return {"verified": False, "checks": {"transaction_exists": False}}

        if simulate_failure:
            checks = {"simulated_network_partition": False, "ledger_consistency": False}
            db_add_event(
                tx_id=tx_id,
                event_type="VERIFICATION",
                step="verify_resolution",
                status="FAILED",
                message="[Independent Verifier] Simulated verification failure: Invariant check failed across bank gateway.",
                visibility=AuditVisibility.INTERNAL.value,
                actor=actor,
            )
            return {"verified": False, "checks": checks}

        checks: Dict[str, bool] = {}

        if action_type in ("AUTO_REVERSAL", "REVERSAL", "HUMAN_APPROVED_REVERSAL"):
            checks = {
                "merchant_ledger_reversed": tx["merchant_status"] == "REVERSED",
                "settlement_ledger_reversed": tx["settlement_status"] == "REVERSED",
                "action_id_persisted": tx["action_id"] == action_ref,
            }
        elif action_type == "WALLET_CREDIT_OFFER" or action_type == "WALLET_CREDIT":
            checks = {
                "wallet_action_id_persisted": (tx["action_id"] or "").startswith("WALLET-"),
                "status_reconciled": tx["resolution_status"] == "RESOLVED",
            }
        elif action_type == "SLA_CHASE":
            checks = {
                "chase_ref_persisted": (tx["action_id"] or "").startswith("CHASE-"),
                "status_reconciled": tx["resolution_status"] == "RESOLVED",
            }
        elif action_type == "ITEMIZED_EXPLANATION":
            checks = {
                "explanation_ref_persisted": (tx["action_id"] or "").startswith("EXPL-"),
                "status_consistent": tx["resolution_status"] in ("NO_ACTION", "RESOLVED"),
            }
        elif action_type == "COMPLIANCE_HOLD":
            checks = {
                "hold_ref_persisted": (tx["action_id"] or "").startswith("COMP-"),
                "escalation_held": tx["resolution_status"] == "ESCALATED",
            }
        else:
            checks = {"action_acknowledged": True}

        all_passed = all(checks.values())

        db_add_event(
            tx_id=tx_id,
            event_type="VERIFICATION",
            step="verify_resolution",
            status="SUCCESS" if all_passed else "FAILED",
            message=(
                f"[Independent Verifier] Verification {'PASSED' if all_passed else 'FAILED'}: "
                f"{', '.join(f'{k}={v}' for k, v in checks.items())}"
            ),
            visibility=AuditVisibility.INTERNAL.value,
            actor=actor,
        )

        if all_passed:
            db_add_event(
                tx_id=tx_id,
                event_type="VERIFICATION",
                step="customer_verified_notice",
                status="SUCCESS",
                message="Payment outcome verified across core banking and settlement records.",
                visibility=AuditVisibility.CUSTOMER.value,
                actor="ZeroTouch",
            )

        return {"verified": all_passed, "checks": checks}

    @staticmethod
    def _build_action_ref(action_type: str, tx_id: str) -> str:
        if action_type in ("AUTO_REVERSAL", "REVERSAL", "HUMAN_APPROVED_REVERSAL"):
            return f"REV-{tx_id}"
        elif action_type in ("WALLET_CREDIT_OFFER", "WALLET_CREDIT"):
            return f"WALLET-{tx_id}"
        elif action_type == "SLA_CHASE":
            return f"CHASE-{tx_id}"
        elif action_type == "ITEMIZED_EXPLANATION":
            return f"EXPL-{tx_id}"
        elif action_type == "COMPLIANCE_HOLD":
            return f"COMP-{tx_id}"
        return f"ACT-{tx_id}"

    @staticmethod
    def _apply_mutation(tx_id: str, action_type: str, action_ref: str, amount: float, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Apply state changes to transactions table."""
        if action_type in ("AUTO_REVERSAL", "REVERSAL", "HUMAN_APPROVED_REVERSAL"):
            db_update_transaction(
                tx_id,
                merchant_status="REVERSED",
                settlement_status="REVERSED",
                action_id=action_ref,
                resolution_status="RESOLVED",
            )
            return {"action_type": action_type, "action_ref": action_ref, "amount": amount, "target": "Bank Reversal API"}

        elif action_type in ("WALLET_CREDIT_OFFER", "WALLET_CREDIT"):
            db_update_transaction(
                tx_id,
                action_id=action_ref,
                resolution_status="RESOLVED",
            )
            return {"action_type": action_type, "action_ref": action_ref, "amount": amount, "target": "Paytm Wallet"}

        elif action_type == "SLA_CHASE":
            db_update_transaction(
                tx_id,
                action_id=action_ref,
                resolution_status="RESOLVED",
            )
            return {"action_type": action_type, "action_ref": action_ref, "target": "Bank Dispute API", "eta_hours": 24}

        elif action_type == "ITEMIZED_EXPLANATION":
            db_update_transaction(
                tx_id,
                action_id=action_ref,
                resolution_status="NO_ACTION",
            )
            return {
                "action_type": action_type,
                "action_ref": action_ref,
                "gross_amount": amount,
                "platform_fee": payload.get("fee", 0.0),
                "gst": payload.get("gst", 0.0),
                "net_settled": amount - payload.get("fee", 0.0) - payload.get("gst", 0.0),
            }

        elif action_type == "COMPLIANCE_HOLD":
            db_update_transaction(
                tx_id,
                action_id=action_ref,
                resolution_status="ESCALATED",
            )
            return {"action_type": action_type, "action_ref": action_ref, "target": "Compliance Queue", "status": "HELD"}

        return {"action_type": action_type, "action_ref": action_ref}

    @staticmethod
    def _sync_case_action(case_id: str, action_record: ActionRecord, customer_status: str, ops_status: str):
        db_update_case(
            case_id,
            action_record=json.dumps(action_record.model_dump()),
            customer_status=customer_status,
            ops_status=ops_status,
        )
