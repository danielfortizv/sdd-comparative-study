"""Router de conversión de divisas y transferencias internas multidivisa (Etapa 4, T12/T13).

- `GET  /api/v2/accounts` — cuentas con `public_id`, moneda y saldo (D-01/D-02/D-10).
- `POST /api/conversions` — conversión FX con idempotencia + versión optimista (D-03/D-13/D-14).
- `POST /api/v2/transfers` — transferencia interna misma-moneda (D-04) con idempotencia + versión.

Headers de comando (D-13/D-14): `Idempotency-Key` (UUID) obligatorio en operaciones de cambio de
estado; `Expected-Version` opcional por cuenta como JSON `{public_id: version}` (si se envía, se
valida; si se omite, se usa la versión actual — compatibilidad de clientes simples).
"""

from __future__ import annotations

import json
from fractions import Fraction

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse

from .. import audit, command, conversion_service as cs, idempotency
from ..db import get_connection
from ..money import format_cents

router = APIRouter(prefix="/api", tags=["conversions"])


def _conn():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def _error(code: str, message: str, status: int) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


@router.get("/v2/accounts")
def list_accounts_v2(conn=Depends(_conn)) -> JSONResponse:
    """Cuentas multidivisa: id público, moneda y saldo (sin ids internos; D-01/D-02/D-10)."""
    rows = conn.execute(
        "SELECT public_id, display_name, kind, currency, balance_cents, version FROM account "
        "ORDER BY currency, public_id"
    ).fetchall()
    accounts = [
        {
            "public_id": r["public_id"],
            "name": r["display_name"],
            "currency": r["currency"],
            "balance": format_cents(r["balance_cents"]),
            "version": r["version"],
        }
        for r in rows
        if r["public_id"] is not None
    ]
    return JSONResponse(status_code=200, content={"accounts": accounts})


def _expected_versions(raw: str | None, src, dst) -> dict[str, int]:
    """Construye el mapa account_id->version esperada desde el header `Expected-Version` (JSON por
    public_id). Si no se envía, usa la versión actual de cada cuenta (no fuerza conflicto)."""
    if not raw:
        return {src.id: src.version, dst.id: dst.version}
    try:
        by_public = json.loads(raw)
    except (ValueError, TypeError):
        raise idempotency.IdempotencyError("INVALID_EXPECTED_VERSION",
                                            "Expected-Version debe ser JSON {public_id: version}", 400)
    result = {}
    for acc in (src, dst):
        if acc.public_id in by_public:
            result[acc.id] = int(by_public[acc.public_id])
        else:
            result[acc.id] = acc.version
    return result


async def _json_body(request: Request) -> dict:
    try:
        return await request.json()
    except (ValueError, TypeError):
        return {}


@router.post("/conversions")
async def create_conversion(
    request: Request,
    conn=Depends(_conn),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    expected_version: str | None = Header(default=None, alias="Expected-Version"),
) -> JSONResponse:
    body = await _json_body(request)
    try:
        key = idempotency.require_uuid_key(idempotency_key)
        src, dst, amount_minor, dest_minor, rate = cs.convert_plan(
            conn,
            from_public_id=body.get("from"),
            to_public_id=body.get("to"),
            amount_raw=body.get("amount", ""),
        )
        # MFA en equivalente USD (T14, D-07): si el equivalente USD sin redondear > 1000, no se
        # mueve saldo; se crea un pendiente y se confirma con el código MFA.
        if cs.requires_mfa(amount_minor, src.currency):
            body_pending = cs.create_pending_mfa(
                conn, operation="conversion", src=src, dst=dst, amount_minor=amount_minor,
                dest_minor=dest_minor, rate=rate, idempotency_key=key)
            return JSONResponse(status_code=200, content=body_pending)

        expected = _expected_versions(expected_version, src, dst)
        effects = cs.build_conversion_effects(src, dst, amount_minor, dest_minor, rate)
        occurred_at = cs.now_iso()
        rate_str = f"{rate.numerator}/{rate.denominator}"

        def build_response(event_ids):
            return {
                "status": "COMPLETED",
                "rate": rate_str,
                "from": {"public_id": src.public_id, "currency": src.currency,
                         "amount": format_cents(amount_minor)},
                "to": {"public_id": dst.public_id, "currency": dst.currency,
                       "amount": format_cents(dest_minor)},
                "event_ids": event_ids,
            }

        result = idempotency.execute_idempotent_command(
            conn,
            idempotency_key=key,
            operation="conversion",
            request_payload={"from": src.public_id, "to": dst.public_id,
                             "amount": format_cents(amount_minor)},
            expected_versions=expected,
            effects=effects,
            occurred_at=occurred_at,
            build_response=build_response,
            audit_spec=command.AuditSpec(
                "CONVERSION_COMPLETED", audit.OUTCOME_SUCCESS,
                f"conversion:{src.public_id}->{dst.public_id}",
                {"rate": rate_str, "src_minor": amount_minor, "dst_minor": dest_minor,
                 "src_ccy": src.currency, "dst_ccy": dst.currency}),
        )
        return JSONResponse(status_code=result.status_code, content=result.response)
    except cs.ConversionError as exc:
        return _error(exc.code, exc.message, exc.status)
    except idempotency.IdempotencyError as exc:
        return _error(exc.code, exc.message, exc.status)


@router.post("/v2/mfa/{reference}")
async def confirm_v2_mfa(reference: str, request: Request, conn=Depends(_conn)) -> JSONResponse:
    """Confirma una operación v2 PENDING_MFA (conversión o interna de alto valor, T14/D-07).

    Código correcto y dentro de la ventana -> aplica la operación vía el comando idempotente
    (sin segundo efecto si se reintenta la misma clave). Código incorrecto -> 401 sin mover saldos.
    Vencida -> 409 EXPIRED.
    """
    body = await _json_body(request)
    row = cs.get_pending(conn, reference)
    if row is None:
        return _error("NOT_FOUND", "Referencia de MFA inexistente", 404)
    if cs.expire_pending_if_needed(conn, row):
        return _error("EXPIRED", "La autorización MFA expiró", 409)
    if row["status"] != "PENDING_MFA":
        return _error("EXPIRED", f"La operación no está pendiente (estado {row['status']})", 409)
    if not cs.mfa_code_ok(body.get("code", "")):
        return _error("INVALID_MFA_CODE", "Código MFA incorrecto", 401)

    try:
        src = cs.get_account_by_public_id(conn, row["from_public"])
        dst = cs.get_account_by_public_id(conn, row["to_public"])
        if src is None or dst is None:
            return _error("NOT_FOUND", "Cuenta desconocida", 404)
        amount_minor = int(row["amount_minor"])
        operation = row["operation"]
        key = row["idempotency_key"]
        occurred_at = cs.now_iso()

        if operation == "conversion":
            dest_minor, rate = cs.fx.convert(amount_minor, src.currency, dst.currency)
            effects = cs.build_conversion_effects(src, dst, amount_minor, dest_minor, rate)
            rate_str = f"{rate.numerator}/{rate.denominator}"
            audit_spec = command.AuditSpec(
                "CONVERSION_COMPLETED", audit.OUTCOME_SUCCESS,
                f"conversion:{src.public_id}->{dst.public_id}",
                {"rate": rate_str, "src_minor": amount_minor, "dst_minor": dest_minor, "mfa": True})

            def build_response(event_ids):
                return {"status": "COMPLETED", "rate": rate_str,
                        "from": {"public_id": src.public_id, "currency": src.currency,
                                 "amount": format_cents(amount_minor)},
                        "to": {"public_id": dst.public_id, "currency": dst.currency,
                               "amount": format_cents(dest_minor)},
                        "event_ids": event_ids}
        else:
            effects = cs.build_internal_effects(src, dst, amount_minor)
            audit_spec = command.AuditSpec(
                "INTERNAL_TRANSFER_COMPLETED", audit.OUTCOME_SUCCESS,
                f"internal:{src.public_id}->{dst.public_id}",
                {"amount_minor": amount_minor, "currency": src.currency, "mfa": True})

            def build_response(event_ids):
                return {"status": "COMPLETED",
                        "from": {"public_id": src.public_id, "currency": src.currency,
                                 "amount": format_cents(amount_minor)},
                        "to": {"public_id": dst.public_id, "currency": dst.currency,
                               "amount": format_cents(amount_minor)},
                        "event_ids": event_ids}

        result = idempotency.execute_idempotent_command(
            conn,
            idempotency_key=key,
            operation=operation,
            request_payload={"from": src.public_id, "to": dst.public_id,
                             "amount": format_cents(amount_minor), "mfa": True},
            expected_versions={src.id: src.version, dst.id: dst.version},
            effects=effects,
            occurred_at=occurred_at,
            build_response=build_response,
            audit_spec=audit_spec,
        )
        # Marcar el pendiente CONFIRMED (fuera de la tx del comando; su efecto ya está persistido).
        conn.execute("UPDATE v2_pending_mfa SET status='CONFIRMED' WHERE reference=?", (reference,))
        conn.commit()
        return JSONResponse(status_code=result.status_code, content=result.response)
    except cs.ConversionError as exc:
        return _error(exc.code, exc.message, exc.status)
    except idempotency.IdempotencyError as exc:
        return _error(exc.code, exc.message, exc.status)


@router.post("/v2/transfers")
async def create_internal_transfer_v2(
    request: Request,
    conn=Depends(_conn),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    expected_version: str | None = Header(default=None, alias="Expected-Version"),
) -> JSONResponse:
    body = await _json_body(request)
    try:
        key = idempotency.require_uuid_key(idempotency_key)
        src, dst, amount_minor = cs.internal_transfer_plan(
            conn,
            from_public_id=body.get("from"),
            to_public_id=body.get("to"),
            amount_raw=body.get("amount", ""),
        )
        # MFA en equivalente USD (T14, D-07) para internas de alto valor.
        if cs.requires_mfa(amount_minor, src.currency):
            body_pending = cs.create_pending_mfa(
                conn, operation="internal_transfer", src=src, dst=dst, amount_minor=amount_minor,
                dest_minor=amount_minor, rate=Fraction(1), idempotency_key=key)
            return JSONResponse(status_code=200, content=body_pending)

        expected = _expected_versions(expected_version, src, dst)
        effects = cs.build_internal_effects(src, dst, amount_minor)
        occurred_at = cs.now_iso()

        def build_response(event_ids):
            return {
                "status": "COMPLETED",
                "from": {"public_id": src.public_id, "currency": src.currency,
                         "amount": format_cents(amount_minor)},
                "to": {"public_id": dst.public_id, "currency": dst.currency,
                       "amount": format_cents(amount_minor)},
                "event_ids": event_ids,
            }

        result = idempotency.execute_idempotent_command(
            conn,
            idempotency_key=key,
            operation="internal_transfer",
            request_payload={"from": src.public_id, "to": dst.public_id,
                             "amount": format_cents(amount_minor)},
            expected_versions=expected,
            effects=effects,
            occurred_at=occurred_at,
            build_response=build_response,
            audit_spec=command.AuditSpec(
                "INTERNAL_TRANSFER_COMPLETED", audit.OUTCOME_SUCCESS,
                f"internal:{src.public_id}->{dst.public_id}",
                {"amount_minor": amount_minor, "currency": src.currency}),
        )
        return JSONResponse(status_code=result.status_code, content=result.response)
    except cs.ConversionError as exc:
        return _error(exc.code, exc.message, exc.status)
    except idempotency.IdempotencyError as exc:
        return _error(exc.code, exc.message, exc.status)
