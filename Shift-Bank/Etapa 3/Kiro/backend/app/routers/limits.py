"""Router de límites de transacción dinámicos (Etapa 2, Tarea 17).

`GET /api/limits` devuelve los límites vigentes y el consumo/disponibilidad del día UTC.
`PUT /api/limits` actualiza los límites validando la entrada (LIM-09).

Montos en la API como cadenas decimales (decimal-string), coherente con la Etapa 1.

_Requisitos: 13.2, 13.3, 13.4_ · _Contrato: LIM-01, LIM-02, LIM-09; A10_
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .. import limit_service
from ..db import get_connection
from ..money import format_cents

router = APIRouter(prefix="/api", tags=["limits"])


def _conn():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def _error(code: str, message: str, http_status: int) -> JSONResponse:
    return JSONResponse(status_code=http_status, content={"error": {"code": code, "message": message}})


_LIMIT_HTTP = {"INVALID_LIMIT": 400, "NOT_FOUND": 404}


class UpdateLimitsRequest(BaseModel):
    # Montos como decimal-string; ambos opcionales (actualización parcial).
    per_transfer: str | None = None
    daily: str | None = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


@router.get("/limits")
def get_limits(conn=Depends(_conn)) -> JSONResponse:
    limits = limit_service.get_limits(conn)
    consumed = limit_service.daily_consumption_cents(conn, _now())
    remaining = max(0, limits.daily_cents - consumed)
    body = {
        "per_transfer": format_cents(limits.per_transfer_cents),
        "daily": format_cents(limits.daily_cents),
        "daily_consumed": format_cents(consumed),
        "daily_remaining": format_cents(remaining),
    }
    return JSONResponse(status_code=200, content=body)


@router.put("/limits")
def update_limits(payload: UpdateLimitsRequest, conn=Depends(_conn)) -> JSONResponse:
    try:
        updated = limit_service.update_limits(
            conn,
            per_transfer_raw=payload.per_transfer,
            daily_raw=payload.daily,
            now=_now(),
        )
    except limit_service.LimitError as exc:
        return _error(exc.code, exc.message, _LIMIT_HTTP.get(exc.code, 400))

    return JSONResponse(
        status_code=200,
        content={
            "per_transfer": format_cents(updated.per_transfer_cents),
            "daily": format_cents(updated.daily_cents),
        },
    )
