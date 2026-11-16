"""Router de transferencias ACH (Etapa 2, Tarea 22).

`POST /api/ach` crea/autoriza una ACH (guardada o ad hoc). `POST /api/ach/{reference}/mfa`
confirma la MFA de una ACH sensible (`pending_auth` → `pending` + débito).

Montos como cadenas decimales. Errores con la forma heredada `{error:{code,message}}`.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .. import ach_service
from ..db import get_connection

router = APIRouter(prefix="/api", tags=["ach"])


def _conn():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def _error(code: str, message: str, http: int) -> JSONResponse:
    return JSONResponse(status_code=http, content={"error": {"code": code, "message": message}})


_HTTP = {
    "INVALID_ROUTING": 400, "INVALID_ACCOUNT_NUMBER": 400, "INVALID_BENEFICIARY": 400,
    "NON_POSITIVE_AMOUNT": 400, "INVALID_AMOUNT": 400, "INSUFFICIENT_FUNDS": 400,
    "LIMIT_EXCEEDED_PER_TRANSFER": 409, "LIMIT_EXCEEDED_DAILY": 409,
    "INVALID_MFA_CODE": 401, "EXPIRED": 409, "NOT_FOUND": 404,
}


class AdhocBeneficiary(BaseModel):
    name: str
    bank: str
    routing_number: str
    account_number: str


class CreateAchRequest(BaseModel):
    amount: str
    description: str = ""
    from_: str = Field(default="checking", alias="from")
    beneficiary_id: str | None = None
    adhoc: AdhocBeneficiary | None = None
    save_adhoc: bool = False

    model_config = {"populate_by_name": True}


class MfaRequest(BaseModel):
    code: str


@router.post("/ach")
def create_ach(payload: CreateAchRequest, conn=Depends(_conn)) -> JSONResponse:
    try:
        result = ach_service.create_ach(
            conn,
            amount_raw=payload.amount,
            description=payload.description,
            from_kind=payload.from_,
            beneficiary_id=payload.beneficiary_id,
            adhoc=payload.adhoc.model_dump() if payload.adhoc else None,
            save_adhoc=payload.save_adhoc,
        )
    except ach_service.AchError as exc:
        return _error(exc.code, exc.message, _HTTP.get(exc.code, 400))

    body = {
        "status": result.status,
        "mfa_required": result.mfa_required,
        "reference": result.reference,
        "expires_at": result.expires_at,
    }
    return JSONResponse(status_code=201, content=body)


@router.post("/ach/{reference}/mfa")
def confirm_ach_mfa(reference: str, payload: MfaRequest, conn=Depends(_conn)) -> JSONResponse:
    try:
        status = ach_service.confirm_ach_mfa(conn, reference=reference, code=payload.code)
    except ach_service.AchError as exc:
        return _error(exc.code, exc.message, _HTTP.get(exc.code, 400))
    return JSONResponse(status_code=200, content={"status": status})
