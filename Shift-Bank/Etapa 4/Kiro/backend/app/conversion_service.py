"""Servicio de conversión de divisas y transferencias internas multidivisa (Etapa 4, T12/T13).

Opera sobre cuentas identificadas por su `public_id` (D-02), usando el motor FX exacto (`fx`),
el patrón de comando atómico con idempotencia y versión optimista (`idempotency`/`command`), y los
eventos de dominio compuestos (D-09). Reglas:

- Conversión (`/api/conversions`, D-03/D-04): debita la cuenta origen y abona la destino con la
  tasa racional exacta y `ROUND_HALF_UP` una sola vez; evento compuesto (debited+credited) con el
  MISMO `operation_id`.
- Transferencia interna (T13, D-04): SOLO misma moneda; cross-currency -> error que remite a
  `/api/conversions`.
- Límites/MFA en equivalente USD se verifican en `limit_service` (T14), reutilizado aquí.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

import uuid
from datetime import timedelta

from . import command, events, fx, limit_service
from .clock import system_clock, iso, parse_iso
from .config import MFA_CODE, MFA_TTL_SECONDS
from .money import InvalidAmountError, decimal_to_cents, parse_amount


class ConversionError(Exception):
    """Error de dominio de conversión/transferencia multidivisa con `code` y `status` HTTP."""

    def __init__(self, code: str, message: str, status: int = 422) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


@dataclass
class AccountRef:
    id: str
    public_id: str
    kind: str
    currency: str
    balance_minor: int
    version: int


def get_account_by_public_id(conn: sqlite3.Connection, public_id: str) -> AccountRef | None:
    row = conn.execute(
        "SELECT id, public_id, kind, currency, balance_cents, version FROM account WHERE public_id = ?",
        (public_id,),
    ).fetchone()
    if row is None:
        return None
    return AccountRef(
        id=row["id"], public_id=row["public_id"], kind=row["kind"],
        currency=row["currency"], balance_minor=row["balance_cents"], version=row["version"],
    )


def _parse_minor(amount_raw: str) -> int:
    try:
        amount = parse_amount(amount_raw)
    except InvalidAmountError as exc:
        raise ConversionError("INVALID_AMOUNT", str(exc), 400) from exc
    if amount <= 0:
        raise ConversionError("NON_POSITIVE_AMOUNT", "El monto debe ser mayor que cero", 400)
    try:
        return decimal_to_cents(amount)
    except InvalidAmountError as exc:
        raise ConversionError("INVALID_AMOUNT", str(exc), 400) from exc


def _check_limits_usd(conn, amount_minor: int, currency: str) -> None:
    """Verifica límites en equivalente USD (D-07), reutilizando `limit_service` (T14)."""
    usd_minor = fx.usd_equivalent_minor(amount_minor, currency)
    try:
        limit_service.check_usd(conn, usd_minor, system_clock.now_utc())
    except limit_service.LimitError as exc:
        raise ConversionError(exc.code, exc.message, 409) from exc


def convert_plan(conn, *, from_public_id, to_public_id, amount_raw):
    """Valida y construye el plan de una conversión (sin aplicar). Devuelve datos para el comando."""
    src = get_account_by_public_id(conn, from_public_id)
    dst = get_account_by_public_id(conn, to_public_id)
    if src is None or dst is None:
        raise ConversionError("NOT_FOUND", "Cuenta desconocida", 404)
    if src.public_id == dst.public_id:
        raise ConversionError("SAME_ACCOUNT", "Origen y destino no pueden ser la misma cuenta", 400)
    if not fx.is_supported(src.currency) or not fx.is_supported(dst.currency):
        raise ConversionError("UNSUPPORTED_CURRENCY", "Moneda no soportada", 422)
    amount_minor = _parse_minor(amount_raw)
    if amount_minor > src.balance_minor:
        raise ConversionError("INSUFFICIENT_FUNDS", "Fondos insuficientes en la cuenta origen", 422)
    _check_limits_usd(conn, amount_minor, src.currency)
    dest_minor, rate = fx.convert(amount_minor, src.currency, dst.currency)
    return src, dst, amount_minor, dest_minor, rate


def internal_transfer_plan(conn, *, from_public_id, to_public_id, amount_raw):
    """Valida un plan de transferencia interna MISMA MONEDA (T13, D-04)."""
    src = get_account_by_public_id(conn, from_public_id)
    dst = get_account_by_public_id(conn, to_public_id)
    if src is None or dst is None:
        raise ConversionError("NOT_FOUND", "Cuenta desconocida", 404)
    if src.public_id == dst.public_id:
        raise ConversionError("SAME_ACCOUNT", "Origen y destino no pueden ser la misma cuenta", 400)
    if src.currency != dst.currency:
        raise ConversionError(
            "CROSS_CURRENCY_NOT_ALLOWED",
            "Las transferencias internas son de una sola moneda; use /api/conversions para "
            "cambios de divisa",
            422,
        )
    amount_minor = _parse_minor(amount_raw)
    if amount_minor > src.balance_minor:
        raise ConversionError("INSUFFICIENT_FUNDS", "Fondos insuficientes en la cuenta origen", 422)
    _check_limits_usd(conn, amount_minor, src.currency)
    return src, dst, amount_minor


def build_conversion_effects(src, dst, amount_minor, dest_minor, rate):
    """Efectos compuestos de una conversión (D-09): débito origen + crédito destino."""
    rate_str = f"{rate.numerator}/{rate.denominator}"
    return [
        command.AccountEffect(
            src.id, events.EVENT_CONVERSION_DEBITED, -amount_minor,
            {"public_id": src.public_id, "rate": rate_str, "to": dst.public_id}),
        command.AccountEffect(
            dst.id, events.EVENT_CONVERSION_CREDITED, +dest_minor,
            {"public_id": dst.public_id, "rate": rate_str, "from": src.public_id}),
    ]


def build_internal_effects(src, dst, amount_minor):
    """Efectos de una transferencia interna misma-moneda (D-04)."""
    return [
        command.AccountEffect(
            src.id, events.EVENT_INTERNAL_TRANSFER_DEBITED, -amount_minor,
            {"public_id": src.public_id, "to": dst.public_id}),
        command.AccountEffect(
            dst.id, events.EVENT_INTERNAL_TRANSFER_CREDITED, +amount_minor,
            {"public_id": dst.public_id, "from": src.public_id}),
    ]


def now_iso() -> str:
    return iso(system_clock.now_utc())


# --- MFA en equivalente USD para operaciones v2 (Tarea 14, D-07) --------------
#
# MFA requerida cuando el equivalente USD SIN redondear de la operación es ESTRICTAMENTE mayor que
# USD 1,000.00. En ese caso la operación NO mueve saldos: se persiste un pendiente
# (`v2_pending_mfa`) con una `reference` y se confirma con el código MFA heredado (`123456`) dentro
# de la ventana de 5 minutos. Al confirmar se aplica vía el comando idempotente.


def requires_mfa(amount_minor: int, currency: str) -> bool:
    """True si el equivalente USD SIN redondear > USD 1,000.00 (D-07)."""
    return fx.requires_mfa_usd(amount_minor, currency)


def create_pending_mfa(conn, *, operation: str, src, dst, amount_minor: int,
                       dest_minor: int, rate, idempotency_key: str) -> dict:
    """Persiste un pendiente de MFA v2 (sin mover saldos) y devuelve la respuesta PENDING_MFA."""
    reference = uuid.uuid4().hex
    now = system_clock.now_utc()
    expires_at = iso(now + timedelta(seconds=MFA_TTL_SECONDS))
    rate_str = f"{rate.numerator}/{rate.denominator}"
    conn.execute(
        """INSERT INTO v2_pending_mfa
           (reference, operation, from_public, to_public, amount_minor, dest_minor, rate,
            idempotency_key, status, created_at, expires_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING_MFA', ?, ?)""",
        (reference, operation, src.public_id, dst.public_id, amount_minor, dest_minor, rate_str,
         idempotency_key, iso(now), expires_at),
    )
    conn.commit()
    return {
        "status": "PENDING_MFA",
        "mfa_required": True,
        "reference": reference,
        "expires_at": expires_at,
        "rate": rate_str,
    }


def get_pending(conn, reference: str):
    return conn.execute(
        "SELECT * FROM v2_pending_mfa WHERE reference = ?", (reference,)).fetchone()


def expire_pending_if_needed(conn, row) -> bool:
    """Marca EXPIRED un pendiente vencido (lazy). Devuelve True si expiró."""
    if row["status"] == "PENDING_MFA" and system_clock.now_utc() > parse_iso(row["expires_at"]):
        conn.execute(
            "UPDATE v2_pending_mfa SET status='EXPIRED' WHERE reference = ?", (row["reference"],))
        conn.commit()
        return True
    return False


def mfa_code_ok(code: str) -> bool:
    return code == MFA_CODE
