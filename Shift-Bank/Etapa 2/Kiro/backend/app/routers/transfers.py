"""Router de transferencias (Requisitos 2.2, 3, 5, 6, 7, 8).

Expone la creación de transferencias, la confirmación de MFA y el historial. Mapea las
excepciones de dominio a los códigos HTTP de la tabla del diseño.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from .. import repository, service
from ..config import ACCOUNT_DISPLAY_NAMES
from ..db import get_connection
from ..money import format_cents
from ..schemas import (
    CreateTransferRequest,
    CreateTransferResponse,
    MfaRequest,
    MfaResponse,
    TransferDirection,
    TransferHistoryItem,
    TransfersHistoryResponse,
)
from ..service import DomainError

router = APIRouter(prefix="/api", tags=["transfers"])

# Mapa de código de dominio -> HTTP, según la tabla del diseño.
_DOMAIN_HTTP = {
    "SAME_ACCOUNT": 400,
    "NON_POSITIVE_AMOUNT": 400,
    "INVALID_AMOUNT": 400,
    "INSUFFICIENT_FUNDS_CREATE": 400,
    "INVALID_MFA_CODE": 401,
    "EXPIRED": 409,
    "INSUFFICIENT_FUNDS_CONFIRM": 409,
    "NOT_FOUND": 404,
    # Etapa 2 (Fase C): límites dinámicos → 409 (LIM-03/LIM-04).
    "LIMIT_EXCEEDED_PER_TRANSFER": 409,
    "LIMIT_EXCEEDED_DAILY": 409,
}


def _conn():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def _error(code: str, message: str, http_status: int) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content={"error": {"code": code, "message": message}},
    )


@router.post("/transfers", response_model=CreateTransferResponse)
def create_transfer(payload: CreateTransferRequest, conn=Depends(_conn)):
    try:
        result = service.create_transfer(
            conn,
            from_kind=payload.from_,
            to_kind=payload.to,
            amount_raw=payload.amount,
            description=payload.description,
        )
    except DomainError as exc:
        # Fondos insuficientes al crear -> 400 (contexto de creación).
        if exc.code == "INSUFFICIENT_FUNDS":
            return _error(exc.code, exc.message, 400)
        http_status = _DOMAIN_HTTP.get(exc.code, 400)
        return _error(exc.code, exc.message, http_status)

    body = CreateTransferResponse(
        status=result.status,
        mfa_required=result.requires_mfa,
        reference=result.reference,
        expires_at=result.expires_at,
    )
    # El contrato de API del diseño fija 201 para la creación (con y sin MFA).
    return JSONResponse(status_code=201, content=body.model_dump())


@router.post("/transfers/{reference}/mfa", response_model=MfaResponse)
def confirm_mfa(reference: str, payload: MfaRequest, conn=Depends(_conn)):
    try:
        status = service.confirm_mfa(conn, reference=reference, code=payload.code)
    except DomainError as exc:
        if exc.code == "INSUFFICIENT_FUNDS":
            # Fondos insuficientes al confirmar -> 409 (transferencia FAILED).
            return _error(exc.code, exc.message, 409)
        http_status = _DOMAIN_HTTP.get(exc.code, 400)
        return _error(exc.code, exc.message, http_status)

    return JSONResponse(status_code=200, content={"status": status})


@router.get("/transfers")
def get_history(conn=Depends(_conn)) -> JSONResponse:
    """Historial unificado (Etapa 2, Tarea 25).

    Extensión ADITIVA (D03/D05): cada entrada gana `type` ('internal'|'ach'). Las internas
    conservan su representación de Etapa 1 — `direction {from,to}` con nombres amigables y
    estados MAYÚSCULAS — sin renombrar ni eliminar campos. Las ACH añaden `beneficiary`
    (enmascarado) y usan estados en minúsculas. Aplica expiración perezosa a los pendientes
    internos (reutiliza `service.list_history`).
    """
    import json

    # Camino heredado: aplica expiración perezosa a internos PENDING_MFA vencidos.
    service.list_history(conn)

    rows = conn.execute(
        """SELECT created_at, type, from_kind, to_kind, amount_cents, description, status,
                  beneficiary_snapshot
           FROM transfer ORDER BY created_at DESC, rowid DESC"""
    ).fetchall()

    items: list[dict] = []
    for r in rows:
        ttype = r["type"] or "internal"
        if ttype == "ach":
            snap = json.loads(r["beneficiary_snapshot"]) if r["beneficiary_snapshot"] else {}
            items.append({
                "type": "ach",
                "date": r["created_at"],
                "amount": format_cents(r["amount_cents"]),
                "description": r["description"],
                "status": r["status"],
                "beneficiary": {
                    "name": snap.get("name", ""),
                    "bank": snap.get("bank", ""),
                    "account_masked": "••••" + str(snap.get("account_number", ""))[-4:],
                },
            })
        else:
            # Interna: forma heredada EXACTA + campo aditivo `type`.
            items.append({
                "type": "internal",
                "date": r["created_at"],
                "direction": {
                    "from": ACCOUNT_DISPLAY_NAMES.get(r["from_kind"], r["from_kind"]),
                    "to": ACCOUNT_DISPLAY_NAMES.get(r["to_kind"], r["to_kind"]),
                },
                "amount": format_cents(r["amount_cents"]),
                "description": r["description"],
                "status": r["status"],
            })
    return JSONResponse(status_code=200, content={"transfers": items})
