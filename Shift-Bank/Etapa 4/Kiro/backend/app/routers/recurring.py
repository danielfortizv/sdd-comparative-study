"""Router de pagos recurrentes (Etapa 2, Fase E, Tarea 33).

Expone la gestión de schedules sobre el servicio de recurrentes (Tareas 27–30):

- `GET  /api/recurring`             Lista los schedules del cliente con su estado y su
                                    **próxima fecha de vencimiento** (`next_run_at`). (Req. 12.1)
- `POST /api/recurring`             Crea un schedule interno o ACH; delega en
                                    `recurring_service.create_schedule`, incluida la
                                    autorización MFA de montos sensibles (Req. 8.x, REC-09).
- `POST /api/recurring/{id}/pause`  Pausa (`active → paused`).                     (Req. 9.1)
- `POST /api/recurring/{id}/resume` Reanuda sin catch-up (`paused → active`).  (Req. 9.2, 9.6)
- `POST /api/recurring/{id}/cancel` Cancela (terminal).                       (Req. 9.3, 9.7)

Los montos viajan como cadenas decimales (convención heredada). Los errores de dominio se
traducen al mismo formato `{error:{code,message}}` y al mapa de HTTP del diseño: las
transiciones ilegales (`INVALID_STATE_TRANSITION`) devuelven 409, y un schedule inexistente
`NOT_FOUND` devuelve 404, de forma consistente con el resto de routers.

_Requisitos: 12.1, 12.2_ · _Contrato: REC-12_
"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .. import recurring_service, repository
from ..db import get_connection
from ..money import format_cents
from ..recurring_service import RecurringError

router = APIRouter(prefix="/api", tags=["recurring"])

# Mapa de código de dominio -> HTTP, consistente con el mapa de errores del diseño (extiende E1).
# Validaciones de entrada → 400; MFA incorrecta/ausente → 401; transición ilegal → 409;
# schedule/beneficiario inexistente → 404.
_HTTP = {
    "INVALID_TYPE": 400,
    "INVALID_FREQUENCY": 400,
    "INVALID_AMOUNT": 400,
    "NON_POSITIVE_AMOUNT": 400,
    "INVALID_SOURCE": 400,
    "INVALID_DESTINATION": 400,
    "INVALID_BENEFICIARY": 400,
    "INVALID_ROUTING": 400,
    "INVALID_ACCOUNT_NUMBER": 400,
    "INVALID_START_DATE": 400,
    "MFA_REQUIRED": 401,
    "INVALID_MFA_CODE": 401,
    "INVALID_STATE_TRANSITION": 409,
    "NOT_FOUND": 404,
}


def _conn():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def _error(code: str, message: str, http: int) -> JSONResponse:
    return JSONResponse(status_code=http, content={"error": {"code": code, "message": message}})


def _customer_id(conn):
    row = conn.execute("SELECT id FROM customer LIMIT 1").fetchone()
    return row["id"] if row else None


class AdhocBeneficiary(BaseModel):
    name: str
    bank: str
    routing_number: str
    account_number: str


class CreateRecurringRequest(BaseModel):
    type: str
    amount: str
    frequency: str
    from_: str = Field(default="checking", alias="from")
    to: str | None = None
    beneficiary_id: str | None = None
    adhoc: AdhocBeneficiary | None = None
    description: str = ""
    start_at: str | None = None
    mfa_code: str | None = None

    model_config = {"populate_by_name": True}


@router.get("/recurring")
def list_recurring(conn=Depends(_conn)) -> JSONResponse:
    """Lista los schedules del cliente con estado + próxima fecha de vencimiento (Req. 12.1).

    Cada entrada expone lo que el panel necesita para renderizar estado y próxima fecha:
    `status` (`active`/`paused`/`cancelled`) y `next_run_at` (ISO-8601 UTC). Se añade el monto
    formateado, la frecuencia y el tipo para mostrar el schedule de forma comprensible.
    """
    cid = _customer_id(conn)
    schedules = repository.list_schedules(conn, cid) if cid else []
    items = [
        {
            "id": s.id,
            "type": s.type,
            "status": s.status,
            "frequency": s.frequency,
            "amount": format_cents(s.amount_cents),
            "description": s.description,
            "next_run_at": s.next_run_at,
            "requires_mfa": bool(s.requires_mfa),
            "authorized": bool(s.authorized),
        }
        for s in schedules
    ]
    return JSONResponse(status_code=200, content={"recurring": items})


@router.post("/recurring")
def create_recurring(payload: CreateRecurringRequest, conn=Depends(_conn)) -> JSONResponse:
    """Crea un schedule interno o ACH (Req. 8.x, REC-01..04/09/11).

    Delega íntegramente en `recurring_service.create_schedule`, que valida origen/destino/monto/
    frecuencia, fija el estado inicial `active`, calcula la primera fecha de vencimiento y exige
    la autorización MFA si el monto es sensible (≥ umbral). No se duplica lógica aquí.
    """
    try:
        result = recurring_service.create_schedule(
            conn,
            type=payload.type,
            amount_raw=payload.amount,
            frequency=payload.frequency,
            from_kind=payload.from_,
            to_kind=payload.to,
            beneficiary_id=payload.beneficiary_id,
            adhoc=payload.adhoc.model_dump() if payload.adhoc else None,
            description=payload.description,
            start_at=payload.start_at,
            mfa_code=payload.mfa_code,
        )
    except RecurringError as exc:
        return _error(exc.code, exc.message, _HTTP.get(exc.code, 400))

    body = {
        "id": result.id,
        "type": result.type,
        "status": result.status,
        "frequency": result.frequency,
        "next_run_at": result.next_run_at,
        "requires_mfa": result.requires_mfa,
        "authorized": result.authorized,
    }
    return JSONResponse(status_code=201, content=body)


def _lifecycle_response(result: recurring_service.ScheduleLifecycleResult) -> JSONResponse:
    return JSONResponse(
        status_code=200,
        content={"id": result.id, "status": result.status, "next_run_at": result.next_run_at},
    )


@router.post("/recurring/{schedule_id}/pause")
def pause_recurring(schedule_id: str, conn=Depends(_conn)) -> JSONResponse:
    """Pausa un schedule `active` (Req. 9.1). Transición ilegal → 409; inexistente → 404."""
    try:
        result = recurring_service.pause_schedule(conn, schedule_id)
    except RecurringError as exc:
        return _error(exc.code, exc.message, _HTTP.get(exc.code, 400))
    return _lifecycle_response(result)


@router.post("/recurring/{schedule_id}/resume")
def resume_recurring(schedule_id: str, conn=Depends(_conn)) -> JSONResponse:
    """Reanuda un schedule `paused` sin catch-up (Req. 9.2, 9.6). Ilegal → 409; inexistente → 404."""
    try:
        result = recurring_service.resume_schedule(conn, schedule_id)
    except RecurringError as exc:
        return _error(exc.code, exc.message, _HTTP.get(exc.code, 400))
    return _lifecycle_response(result)


@router.post("/recurring/{schedule_id}/cancel")
def cancel_recurring(schedule_id: str, conn=Depends(_conn)) -> JSONResponse:
    """Cancela un schedule (terminal; Req. 9.3, 9.7). Ya `cancelled` → 409; inexistente → 404."""
    try:
        result = recurring_service.cancel_schedule(conn, schedule_id)
    except RecurringError as exc:
        return _error(exc.code, exc.message, _HTTP.get(exc.code, 400))
    return _lifecycle_response(result)
