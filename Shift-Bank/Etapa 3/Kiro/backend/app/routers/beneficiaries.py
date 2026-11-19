"""Router de beneficiarios ACH (Etapa 2, Tarea 20).

`GET /api/beneficiaries` (cuenta enmascarada), `POST /api/beneficiaries` (valida formato),
`DELETE /api/beneficiaries/{id}` (borrado lógico). Propiedad restringida al cliente mock.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .. import ach_repository, audit, beneficiaries
from ..db import get_connection
from ..txn import financial_transaction

router = APIRouter(prefix="/api", tags=["beneficiaries"])


def _conn():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def _error(code: str, message: str, http: int) -> JSONResponse:
    return JSONResponse(status_code=http, content={"error": {"code": code, "message": message}})


_HTTP = {"INVALID_ROUTING": 400, "INVALID_ACCOUNT_NUMBER": 400, "INVALID_BENEFICIARY": 400,
         "NOT_FOUND": 404}


class CreateBeneficiaryRequest(BaseModel):
    name: str
    bank: str
    routing_number: str
    account_number: str


def _customer_id(conn):
    row = conn.execute("SELECT id FROM customer LIMIT 1").fetchone()
    return row["id"] if row else None


@router.get("/beneficiaries")
def list_beneficiaries(conn=Depends(_conn)) -> JSONResponse:
    cid = _customer_id(conn)
    rows = ach_repository.list_beneficiaries(conn, cid) if cid else []
    items = [
        {"id": r["id"], **beneficiaries.public_view(
            name=r["name"], bank=r["bank"], account_number=r["account_number"],
            routing_number=r["routing_number"])}
        for r in rows
    ]
    return JSONResponse(status_code=200, content={"beneficiaries": items})


@router.post("/beneficiaries")
def create_beneficiary(payload: CreateBeneficiaryRequest, conn=Depends(_conn)) -> JSONResponse:
    try:
        beneficiaries.validate_fields(
            name=payload.name, bank=payload.bank,
            routing_number=payload.routing_number, account_number=payload.account_number)
    except beneficiaries.BeneficiaryError as exc:
        return _error(exc.code, exc.message, _HTTP.get(exc.code, 400))

    cid = _customer_id(conn)
    if cid is None:
        return _error("NOT_FOUND", "Cliente no encontrado", 404)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    view = beneficiaries.public_view(
        name=payload.name, bank=payload.bank, account_number=payload.account_number,
        routing_number=payload.routing_number)
    # Auditoría atómica (Etapa 3, Tarea 13, design.md §2.7, R5.2): el alta del beneficiario y su
    # entrada `BENEFICIARY_CREATED` se confirman en UNA sola `financial_transaction`. Si el
    # `append` de auditoría falla, el context manager hace ROLLBACK y NO queda beneficiario
    # parcial (fail-closed, R7.2). El payload es NO sensible: banco + cuenta enmascarada (últimos
    # 4, ya expuestos por la API); nunca cuenta/routing en claro ni token `enc:` (R5.6).
    with financial_transaction(conn):
        bid = ach_repository.create_beneficiary_no_commit(
            conn, customer_id=cid, name=payload.name, bank=payload.bank,
            routing_number=payload.routing_number, account_number=payload.account_number,
            created_at=now)
        audit.append_in_tx(
            conn,
            event_type=audit.EVENT_BENEFICIARY_CREATED,
            outcome=audit.OUTCOME_SUCCESS,
            entity_ref=f"beneficiary:{bid}",
            occurred_at=now,
            payload={"bank": payload.bank, "account_masked": view["account_masked"]},
        )
    return JSONResponse(status_code=201, content={"id": bid, **view})


@router.delete("/beneficiaries/{beneficiary_id}")
def delete_beneficiary(beneficiary_id: str, conn=Depends(_conn)) -> JSONResponse:
    cid = _customer_id(conn)
    if cid is None:
        return _error("NOT_FOUND", "Beneficiario no encontrado", 404)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Capturar metadatos NO sensibles ANTES de la baja (para el payload de auditoría): banco y
    # cuenta enmascarada (últimos 4, ya expuestos por la API). La lectura no audita (R5.5); solo
    # la baja efectiva lo hace. `get_beneficiary` descifra en el borde de E/S (design.md §1.5).
    existing = ach_repository.get_beneficiary(conn, cid, beneficiary_id)

    # Auditoría atómica (Etapa 3, Tarea 13, design.md §2.7, R5.2): la baja lógica y su entrada
    # `BENEFICIARY_DELETED` se confirman en UNA sola `financial_transaction` (fail-closed: si el
    # `append` falla, ROLLBACK y la baja no persiste). Se audita SOLO cuando la baja realmente
    # transiciona (un id inexistente/ajeno/ya borrado no genera entrada).
    with financial_transaction(conn):
        ok = ach_repository.soft_delete_beneficiary_no_commit(conn, cid, beneficiary_id, now)
        if not ok:
            # Nada que auditar: el context manager confirma una transacción vacía (sin efecto).
            return _error("NOT_FOUND", "Beneficiario no encontrado", 404)
        payload = {"bank": existing["bank"],
                   "account_masked": beneficiaries.mask_account(existing["account_number"])} \
            if existing is not None else {}
        audit.append_in_tx(
            conn,
            event_type=audit.EVENT_BENEFICIARY_DELETED,
            outcome=audit.OUTCOME_SUCCESS,
            entity_ref=f"beneficiary:{beneficiary_id}",
            occurred_at=now,
            payload=payload,
        )
    return JSONResponse(status_code=200, content={"status": "deleted"})
