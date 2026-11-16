"""Servicio de límites de transacción dinámicos (Etapa 2, Fase C: Tareas 14–16).

Gestiona los límites configurables del cliente mock (por transferencia y diario acumulado,
E2-KIRO-D01), calcula el consumo diario en la ventana de día UTC (LIM-06) y verifica los
límites. La verificación autoritativa está pensada para ejecutarse DENTRO de la transacción
financiera (`financial_transaction`), de modo que lectura de consumo y débito sean atómicos
(F8/F9, sin TOCTOU).

Montos en centavos enteros. Sin ORM; SQL puro sobre la conexión heredada.

_Requisitos: 13.x, 14.x_ · _Contrato: LIM-01..09_ · _Diseño: §Límites (DD-6, F8/F9)_
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime

from . import clock
from .config import DEFAULT_DAILY_LIMIT_CENTS, DEFAULT_PER_TRANSFER_LIMIT_CENTS
from .money import InvalidAmountError, decimal_to_cents, parse_amount


class LimitError(Exception):
    """Error de dominio de límites con un `code` estable para el mapeo a HTTP."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class Limits:
    per_transfer_cents: int
    daily_cents: int


def _customer_id(conn: sqlite3.Connection) -> str | None:
    row = conn.execute("SELECT id FROM customer LIMIT 1").fetchone()
    return row["id"] if row else None


def get_limits(conn: sqlite3.Connection) -> Limits:
    """Devuelve los límites vigentes del cliente mock (o los defaults si no hay fila)."""
    row = conn.execute(
        "SELECT per_transfer_cents, daily_cents FROM transfer_limit LIMIT 1"
    ).fetchone()
    if row is None:
        return Limits(DEFAULT_PER_TRANSFER_LIMIT_CENTS, DEFAULT_DAILY_LIMIT_CENTS)
    return Limits(row["per_transfer_cents"], row["daily_cents"])


def daily_consumption_cents(conn: sqlite3.Connection, now: datetime) -> int:
    """Suma el consumo del día UTC actual (LIM-06).

    Cuenta: transferencias internas `COMPLETED` + ACH `pending`/`settled`. Excluye ACH `failed`
    (tras reembolso) y estados no consumidos (`PENDING_MFA`, `EXPIRED`, `pending_auth`). El
    filtro por tipo usa la columna `type` ('internal'/'ach'); las internas COMPLETED y las ACH
    pending/settled suman, lo demás no.
    """
    start, end = clock.utc_day_bounds(now)
    start_iso, end_iso = clock.iso(start), clock.iso(end)
    row = conn.execute(
        """
        SELECT COALESCE(SUM(amount_cents), 0) AS total
        FROM transfer
        WHERE created_at >= ? AND created_at < ?
          AND (
                (type = 'internal' AND status = 'COMPLETED')
             OR (type = 'ach' AND status IN ('pending', 'settled'))
          )
        """,
        (start_iso, end_iso),
    ).fetchone()
    return int(row["total"])


def check(conn: sqlite3.Connection, amount_cents: int, now: datetime) -> None:
    """Verifica los límites por transferencia y diario. Lanza `LimitError` si se exceden.

    Debe invocarse DENTRO de la transacción financiera (misma conexión), antes de aplicar el
    débito y antes de completar cualquier MFA (LIM-07). Permite igualdad exacta (LIM-05).
    """
    limits = get_limits(conn)
    # Por transferencia (LIM-03): rechaza si supera el máximo por operación.
    if amount_cents > limits.per_transfer_cents:
        raise LimitError("LIMIT_EXCEEDED_PER_TRANSFER",
                         "El monto supera el límite por transferencia")
    # Diario (LIM-04): rechaza si el consumo del día + este monto supera el límite diario.
    consumed = daily_consumption_cents(conn, now)
    if consumed + amount_cents > limits.daily_cents:
        raise LimitError("LIMIT_EXCEEDED_DAILY",
                         "El monto supera el límite diario acumulado")


def update_limits(conn: sqlite3.Connection, *, per_transfer_raw: str | None,
                  daily_raw: str | None, now: datetime) -> Limits:
    """Actualiza los límites validando la entrada (LIM-09).

    Rechaza valores no decimales, negativos o con más de 2 decimales, sin modificar los vigentes
    ante entrada inválida. Acepta actualización parcial (solo uno de los dos campos).
    """
    current = get_limits(conn)
    new_per = current.per_transfer_cents
    new_daily = current.daily_cents

    def _to_cents(raw: str) -> int:
        try:
            value = parse_amount(raw)
        except InvalidAmountError as exc:
            raise LimitError("INVALID_LIMIT", str(exc)) from exc
        if value < 0:
            raise LimitError("INVALID_LIMIT", "El límite no puede ser negativo")
        try:
            return decimal_to_cents(value)
        except InvalidAmountError as exc:
            raise LimitError("INVALID_LIMIT", str(exc)) from exc

    if per_transfer_raw is not None:
        new_per = _to_cents(per_transfer_raw)
    if daily_raw is not None:
        new_daily = _to_cents(daily_raw)

    cid = _customer_id(conn)
    if cid is None:
        raise LimitError("NOT_FOUND", "Cliente no encontrado")

    # Upsert idempotente (la fila se siembra en el arranque, pero se cubre el caso general).
    conn.execute(
        """INSERT INTO transfer_limit (customer_id, per_transfer_cents, daily_cents, updated_at)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(customer_id) DO UPDATE SET
             per_transfer_cents = excluded.per_transfer_cents,
             daily_cents = excluded.daily_cents,
             updated_at = excluded.updated_at""",
        (cid, new_per, new_daily, clock.iso(now)),
    )
    conn.commit()
    return Limits(new_per, new_daily)
