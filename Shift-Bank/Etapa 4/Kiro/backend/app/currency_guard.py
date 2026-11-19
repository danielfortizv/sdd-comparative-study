"""Guardias de divisa para ACH y pagos recurrentes (Etapa 4, Tarea 15; D-08, R12).

Reglas de moneda de la Etapa 4 que se aplican en el borde de los servicios ACH y recurrente, sin
reescribir su lógica financiera (preservación DK-05):

- ACH DEBE originarse SOLO desde una cuenta USD (D-08, R12-1).
- Recurrentes INTERNOS: origen y destino en la MISMA moneda (D-08, R12-2).
- Recurrentes ACH: SOLO USD (D-08, R12-3).

Una violación lanza `CurrencyGuardError` (error de dominio con `code`/`status`), sin mover saldos
ni crear schedules. El ciclo de vida ACH (débito en `pending`, settlement sin doble débito, un
único reembolso) y la ejecución recurrente idempotente (único scheduler) se preservan intactos.
"""

from __future__ import annotations

import sqlite3


class CurrencyGuardError(Exception):
    """Violación de una restricción de divisa de la Etapa 4 (D-08)."""

    def __init__(self, code: str, message: str, status: int = 422) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def account_currency(conn: sqlite3.Connection, *, public_id: str | None = None,
                     kind: str | None = None) -> str | None:
    """Devuelve la moneda de una cuenta por `public_id` o por `kind` (o None si no existe)."""
    if public_id is not None:
        row = conn.execute(
            "SELECT currency FROM account WHERE public_id = ?", (public_id,)).fetchone()
    elif kind is not None:
        row = conn.execute(
            "SELECT currency FROM account WHERE kind = ?", (kind,)).fetchone()
    else:
        return None
    return row["currency"] if row else None


def require_ach_origin_usd(conn: sqlite3.Connection, *, public_id: str | None = None,
                           kind: str | None = None) -> None:
    """ACH solo desde USD (D-08, R12-1). Lanza si la cuenta origen no es USD."""
    ccy = account_currency(conn, public_id=public_id, kind=kind)
    if ccy is None:
        raise CurrencyGuardError("NOT_FOUND", "Cuenta de origen desconocida", 404)
    if ccy != "USD":
        raise CurrencyGuardError(
            "ACH_ORIGIN_NOT_USD", "Las transferencias ACH solo pueden originarse desde USD", 422)


def require_recurring_internal_same_currency(conn: sqlite3.Connection, *,
                                             from_public_id: str, to_public_id: str) -> None:
    """Recurrente interno: misma moneda origen/destino (D-08, R12-2)."""
    src = account_currency(conn, public_id=from_public_id)
    dst = account_currency(conn, public_id=to_public_id)
    if src is None or dst is None:
        raise CurrencyGuardError("NOT_FOUND", "Cuenta desconocida", 404)
    if src != dst:
        raise CurrencyGuardError(
            "CROSS_CURRENCY_NOT_ALLOWED",
            "Un recurrente interno debe mantener la misma moneda en origen y destino", 422)


def require_recurring_ach_usd(conn: sqlite3.Connection, *, from_public_id: str | None = None,
                              kind: str | None = None) -> None:
    """Recurrente ACH: solo USD (D-08, R12-3)."""
    ccy = account_currency(conn, public_id=from_public_id, kind=kind)
    if ccy is None:
        raise CurrencyGuardError("NOT_FOUND", "Cuenta de origen desconocida", 404)
    if ccy != "USD":
        raise CurrencyGuardError(
            "RECURRING_ACH_NOT_USD", "Un recurrente ACH solo puede originarse desde USD", 422)
