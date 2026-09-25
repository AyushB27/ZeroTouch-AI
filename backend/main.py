from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.data import TRANSACTIONS, AUDIT_EVENTS, reset_all
from backend.orchestrator import run_resolution
from backend.models import AuditEvent
import copy
from dotenv import load_dotenv
load_dotenv()  # loads backend/.env if present

app = FastAPI(title="ZeroTouch Payment Resolution Engine", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health():
    return {"status": "ok", "service": "ZeroTouch Engine"}


@app.get("/api/transactions")
def get_transactions():
    return list(TRANSACTIONS.values())


@app.get("/api/transactions/{tx_id}")
def get_transaction(tx_id: str):
    tx = TRANSACTIONS.get(tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail=f"Transaction {tx_id} not found")
    return tx


@app.post("/api/resolutions/{tx_id}/run")
def resolve_transaction(tx_id: str):
    tx = TRANSACTIONS.get(tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail=f"Transaction {tx_id} not found")
    try:
        result = run_resolution(tx_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/resolutions/{tx_id}/events")
def get_events(tx_id: str):
    if tx_id not in TRANSACTIONS:
        raise HTTPException(status_code=404, detail=f"Transaction {tx_id} not found")
    return AUDIT_EVENTS.get(tx_id, [])


@app.post("/api/reset")
def reset_demo():
    reset_all()
    return {"status": "reset", "message": "All transactions restored to original state"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
