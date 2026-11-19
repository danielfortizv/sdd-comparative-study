"""Shift Bank API: retains Stage 1 routes and exposes simulated Stage 2 banking."""
import asyncio
import os
from contextlib import asynccontextmanager, suppress
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from encryption import EncryptionError, validate_key_configuration as validate_encryption_key
from audit import AuditError, verify_database, validate_key_configuration as validate_audit_key

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
    admin_token = os.environ.get("SHIFT_BANK_AUDIT_ADMIN_TOKEN", "")
    if len(admin_token) < 32:
        raise RuntimeError("Audit verification credentials are unavailable or invalid")
    validate_encryption_key()
    validate_audit_key()
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
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "https://localhost:5173", "https://127.0.0.1:5173"],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.get("/health/live")
def health_live():
    return {"status": "alive"}


@app.get("/health/ready")
def health_ready():
    try:
        if len(os.environ.get("SHIFT_BANK_AUDIT_ADMIN_TOKEN", "")) < 32:
            raise RuntimeError("required configuration is unavailable")
        validate_encryption_key()
        validate_audit_key()
        conn = get_db_connection()
        try:
            conn.execute("SELECT 1").fetchone()
        finally:
            conn.close()
        verification = verify_database()
        if not verification["valid"]:
            raise RuntimeError("persisted integrity check failed")
    except Exception:
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return {"status": "ready"}


@app.middleware("http")
async def require_https_for_sensitive_routes(request: Request, call_next):
    sensitive = ("/api/beneficiaries", "/api/ach-transfers", "/api/recurring-schedules", "/api/history", "/api/admin/audit")
    if request.url.path.startswith(sensitive):
        secure = request.url.scheme == "https"
        trusted = {value.strip() for value in os.environ.get("SHIFT_BANK_TRUSTED_PROXY_IPS", "").split(",") if value.strip()}
        if not secure and request.client and request.client.host in trusted:
            secure = request.headers.get("x-forwarded-proto", "").lower() == "https"
        if not secure:
            return JSONResponse(status_code=400, content={"detail": "Sensitive banking operations require HTTPS."})
    return await call_next(request)


@app.exception_handler(EncryptionError)
async def encryption_error_handler(request: Request, exc: EncryptionError):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(AuditError)
async def audit_error_handler(request: Request, exc: AuditError):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


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


@app.get("/api/admin/audit/verify", responses={401: {"description": "Audit verification authorization is required"}})
def verify_audit_chain(request: Request):
    configured = os.environ.get("SHIFT_BANK_AUDIT_ADMIN_TOKEN", "")
    supplied = request.headers.get("authorization", "")
    expected = f"Bearer {configured}"
    import hmac
    if not configured or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Audit verification authorization is required")
    return verify_database()


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


@app.post("/api/recurring-schedules/{schedule_id}/{action}", responses={404: {"description": "Unknown schedule operation"}})
def control_recurring_schedule(schedule_id: str, action: str):
    if action not in {"pause", "resume", "cancel"}:
        raise HTTPException(status_code=404, detail="Unknown schedule operation")
    return _call(banking.control_schedule, schedule_id, action)
