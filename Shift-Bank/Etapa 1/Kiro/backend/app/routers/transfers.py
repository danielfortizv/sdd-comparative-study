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


@router.get("/transfers", response_model=TransfersHistoryResponse)
def get_history(conn=Depends(_conn)) -> TransfersHistoryResponse:
    transfers = service.list_history(conn)
    items: list[TransferHistoryItem] = []
    for t in transfers:
        items.append(
            TransferHistoryItem(
                date=t.created_at,
                direction=TransferDirection(
                    from_=ACCOUNT_DISPLAY_NAMES.get(t.from_kind, t.from_kind),
                    to=ACCOUNT_DISPLAY_NAMES.get(t.to_kind, t.to_kind),
                ),
                amount=format_cents(t.amount_cents),
                description=t.description,
                status=t.status,
            )
        )
    return TransfersHistoryResponse(transfers=items)
