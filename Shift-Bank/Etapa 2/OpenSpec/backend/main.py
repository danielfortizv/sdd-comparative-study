"""Shift Bank API: retains Stage 1 routes and exposes simulated Stage 2 banking."""
import asyncio
from contextlib import asynccontextmanager, suppress
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from database import get_db_connection, init_db
import banking


class ConfirmRequest(BaseModel):
    code: str


class TransferRequest(BaseModel):
    source_account_id: str
    destination_account_id: str
    amount: str


async def _processor():
    while True:
        try:
            await asyncio.to_thread(banking.expire_pending_mfa)
            await asyncio.to_thread(banking.process_ach)
            await asyncio.to_thread(banking.process_schedules)
        except Exception as exc:
            # Persisted states are retried on the next polling iteration.
            print(f"Background banking processor error: {exc}")
        await asyncio.sleep(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    await asyncio.to_thread(banking.recover_schedules)
    task = asyncio.create_task(_processor())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="Shift Bank API", version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


def _call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except banking.BankingError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


@app.get("/api/accounts")
def get_accounts():
    conn = get_db_connection()
    try:
        return [dict(r) for r in conn.execute("SELECT id,name,balance FROM accounts ORDER BY CASE id WHEN 'acc_checking' THEN 0 ELSE 1 END")]
    finally:
        conn.close()


@app.get("/api/history")
def get_history(account_id: str | None = None):
    return banking.all_history(account_id)


@app.post("/api/transfers")
def create_transfer(req: TransferRequest):
    result = _call(banking.create_internal, req.model_dump())
    if result.get("status") == "PENDING_MFA":
        return JSONResponse(status_code=202, content=result)
    return result


@app.post("/api/transfers/{tx_id}/confirm")
def confirm_transfer(tx_id: str, req: ConfirmRequest):
    conn = get_db_connection()
    try:
        is_internal = conn.execute("SELECT 1 FROM transactions WHERE id=?", (tx_id,)).fetchone() is not None
    finally:
        conn.close()
    return _call(banking.confirm_internal if is_internal else banking.confirm_ach, tx_id, req.code)


@app.get("/api/limits")
def read_limits():
    return banking.get_limits()


@app.put("/api/limits")
def update_limits(req: dict):
    return _call(banking.save_limits, req.get("per_transfer"), req.get("daily"))


@app.get("/api/beneficiaries")
def get_beneficiaries():
    return banking.beneficiaries()


@app.post("/api/beneficiaries", status_code=201)
def create_beneficiary(req: dict):
    return _call(banking.beneficiary_create, req)


@app.put("/api/beneficiaries/{beneficiary_id}")
def update_beneficiary(beneficiary_id: str, req: dict):
    return _call(banking.beneficiary_update, beneficiary_id, req)


@app.delete("/api/beneficiaries/{beneficiary_id}")
def delete_beneficiary(beneficiary_id: str):
    return _call(banking.beneficiary_delete, beneficiary_id)


@app.post("/api/ach-transfers", status_code=202)
def create_ach_transfer(req: dict):
    # HTTP 202 represents pending MFA as well as accepted simulated ACH.
    return _call(banking.submit_ach, req)


@app.post("/api/ach-transfers/{transfer_id}/confirm")
def confirm_ach_transfer(transfer_id: str, req: ConfirmRequest):
    return _call(banking.confirm_ach, transfer_id, req.code)


@app.get("/api/ach-transfers")
def get_ach_transfers():
    return banking.ach_history()


@app.post("/api/recurring-schedules")
def create_recurring_schedule(req: dict):
    return _call(banking.create_schedule, req)


@app.post("/api/recurring-schedules/{schedule_id}/confirm")
def confirm_recurring_schedule(schedule_id: str, req: ConfirmRequest):
    return _call(banking.confirm_schedule, schedule_id, req.code)


@app.get("/api/recurring-schedules")
def get_recurring_schedules():
    return banking.list_schedules()


@app.post("/api/recurring-schedules/{schedule_id}/{action}")
def control_recurring_schedule(schedule_id: str, action: str):
    if action not in {"pause", "resume", "cancel"}:
        raise HTTPException(status_code=404, detail="Unknown schedule operation")
    return _call(banking.control_schedule, schedule_id, action)
