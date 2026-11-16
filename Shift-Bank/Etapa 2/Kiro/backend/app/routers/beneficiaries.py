"""Router de beneficiarios ACH (Etapa 2, Tarea 20).

`GET /api/beneficiaries` (cuenta enmascarada), `POST /api/beneficiaries` (valida formato),
`DELETE /api/beneficiaries/{id}` (borrado lógico). Propiedad restringida al cliente mock.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .. import ach_repository, beneficiaries
from ..db import get_connection

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
    bid = ach_repository.create_beneficiary(
        conn, customer_id=cid, name=payload.name, bank=payload.bank,
        routing_number=payload.routing_number, account_number=payload.account_number,
        created_at=now)
    view = beneficiaries.public_view(
        name=payload.name, bank=payload.bank, account_number=payload.account_number,
        routing_number=payload.routing_number)
    return JSONResponse(status_code=201, content={"id": bid, **view})


@router.delete("/beneficiaries/{beneficiary_id}")
def delete_beneficiary(beneficiary_id: str, conn=Depends(_conn)) -> JSONResponse:
    cid = _customer_id(conn)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ok = ach_repository.soft_delete_beneficiary(conn, cid, beneficiary_id, now) if cid else False
    if not ok:
        return _error("NOT_FOUND", "Beneficiario no encontrado", 404)
    return JSONResponse(status_code=200, content={"status": "deleted"})
