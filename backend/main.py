from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import json
import hashlib
import hmac
import os

from dotenv import load_dotenv
load_dotenv()

from backend.database import (
    init_db, db_get_transaction, db_get_all_transactions,
    db_get_events, db_reset_all, db_log_webhook, db_mark_webhook_processed,
    db_update_transaction,
)
from backend.orchestrator import run_resolution
from backend.rag import init_rag

app = FastAPI(title="ZeroTouch Payment Resolution Engine", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
def on_startup():
    init_db()       # Create tables + seed transactions
    init_rag()      # Load knowledge base + generate embeddings


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/")
def health():
    return {
        "status": "ok",
        "service": "ZeroTouch Engine",
        "version": "2.0.0",
        "features": ["LangGraph", "RAG", "PostgreSQL/SQLite", "NPCI Webhook"],
    }


# ── Transactions ──────────────────────────────────────────────────────────────

@app.get("/api/transactions")
def get_transactions():
    return db_get_all_transactions()


@app.get("/api/transactions/{tx_id}")
def get_transaction(tx_id: str):
    tx = db_get_transaction(tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail=f"Transaction {tx_id} not found")
    return tx


# ── Resolution ────────────────────────────────────────────────────────────────

@app.post("/api/resolutions/{tx_id}/run")
def resolve_transaction(tx_id: str):
    tx = db_get_transaction(tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail=f"Transaction {tx_id} not found")
    try:
        result = run_resolution(tx_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/resolutions/{tx_id}/events")
def get_events(tx_id: str):
    if not db_get_transaction(tx_id):
        raise HTTPException(status_code=404, detail=f"Transaction {tx_id} not found")
    return db_get_events(tx_id)


# ── HITL: Human-in-the-Loop Decision ─────────────────────────────────────────

class HumanDecision(BaseModel):
    action: str          # APPROVE_REFUND | REJECT | REQUEST_MORE_INFO
    agent_name: str = "Support Agent"
    notes: Optional[str] = None


@app.post("/api/resolutions/{tx_id}/human-decision")
def human_decision(tx_id: str, decision: HumanDecision):
    tx = db_get_transaction(tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail=f"Transaction {tx_id} not found")
    if tx["resolution_status"] != "ESCALATED":
        raise HTTPException(
            status_code=400,
            detail=f"Transaction {tx_id} is not in ESCALATED state (current: {tx['resolution_status']})"
        )

    from backend.database import db_add_event
    action_map = {
        "APPROVE_REFUND":      ("RESOLVED",  "Refund manually approved by human agent."),
        "REJECT":              ("NO_ACTION", "Case rejected by human agent. No refund issued."),
        "REQUEST_MORE_INFO":   ("ESCALATED", "Agent requested more information from customer."),
    }
    if decision.action not in action_map:
        raise HTTPException(status_code=400, detail=f"Unknown action: {decision.action}")

    new_status, log_msg = action_map[decision.action]

    if decision.action != "REQUEST_MORE_INFO":
        db_update_transaction(tx_id, resolution_status=new_status)

    note_text = f" Note: {decision.notes}" if decision.notes else ""
    db_add_event(tx_id, "ESCALATION", "human_decision", "SUCCESS",
                 f"[{decision.agent_name}] {log_msg}{note_text}")

    return {
        "status": "ok",
        "transaction_id": tx_id,
        "action": decision.action,
        "new_status": new_status,
        "agent": decision.agent_name,
    }


class NPCIWebhookPayload(BaseModel):
    transaction_reference: str           # e.g. "TX9281"
    utr: str                             # Unique Transaction Reference
    status: str                          # e.g. "FAILED", "SUCCESS", "PENDING"
    amount: float
    bank_rrn: Optional[str] = None       # Bank Reference Number
    npci_txn_id: Optional[str] = None
    timestamp: str
    source: str = "NPCI"                 # NPCI | BANK | MERCHANT


WEBHOOK_SECRET = os.getenv("NPCI_WEBHOOK_SECRET", "zerotouch-dev-secret")


def _verify_signature(payload_bytes: bytes, signature: str) -> bool:
    """HMAC-SHA256 signature verification — matches what NPCI/banks use in production."""
    expected = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@app.post("/api/webhook/npci")
async def npci_webhook(
    request: Request,
    x_zerotouch_signature: Optional[str] = Header(None),
):
    """
    Simulated NPCI/Bank webhook endpoint.

    In production, NPCI or the acquiring bank would POST to this endpoint
    every time a transaction status changes (settlement file ingestion,
    bank confirmation, or dispute update).

    For the demo, you can trigger this manually:
      curl -X POST http://localhost:8000/api/webhook/npci \\
        -H "Content-Type: application/json" \\
        -d '{"transaction_reference":"TX9281","utr":"UTR123","status":"FAILED",
             "amount":2500,"timestamp":"2025-10-02T18:00:00Z","source":"NPCI"}'
    """
    body = await request.body()

    # Signature check (skip in dev if header missing)
    if x_zerotouch_signature:
        if not _verify_signature(body, x_zerotouch_signature):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = NPCIWebhookPayload(**json.loads(body))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid payload: {e}")

    tx_ref = payload.transaction_reference

    # Log the raw webhook to the DB
    db_log_webhook(tx_ref, body.decode())

    # Check if the transaction exists
    tx = db_get_transaction(tx_ref)
    if not tx:
        return {
            "status": "ignored",
            "reason": f"Transaction {tx_ref} not found in ZeroTouch system",
        }

    # Map NPCI status → internal fields
    status_map = {
        "FAILED":  {"network_status": "FAILED"},
        "SUCCESS": {"network_status": "SUCCESS"},
        "PENDING": {"network_status": "UNKNOWN"},
        "TIMEOUT": {"network_status": "UNKNOWN"},
        "REVERSED":{"network_status": "SUCCESS", "settlement_status": "REVERSED"},
    }
    update = status_map.get(payload.status.upper(), {})
    if update:
        db_update_transaction(tx_ref, **update)

    db_mark_webhook_processed(tx_ref)

    # Auto-trigger resolution if transaction is still PENDING after webhook update
    tx_fresh = db_get_transaction(tx_ref)
    auto_triggered = False
    resolution_result = None
    if tx_fresh and tx_fresh["resolution_status"] == "PENDING":
        try:
            resolution_result = run_resolution(tx_ref)
            auto_triggered = True
        except Exception as e:
            pass   # Logged inside orchestrator

    return {
        "status": "processed",
        "transaction_reference": tx_ref,
        "npci_status": payload.status,
        "internal_update": update,
        "auto_triggered_resolution": auto_triggered,
        "resolution_decision": resolution_result.decision if resolution_result else None,
        "source": payload.source,
    }


# ── Reset ─────────────────────────────────────────────────────────────────────

@app.post("/api/reset")
def reset_demo():
    db_reset_all()
    return {"status": "reset", "message": "All transactions restored to original state"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
