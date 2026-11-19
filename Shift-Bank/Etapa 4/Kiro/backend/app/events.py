"""Almacén de eventos de dominio (Etapa 4, Tarea 8; D-05, D-09).

Acceso al almacén append-only `domain_event`, SEPARADO de la bitácora de auditoría HMAC
(`audit_log`) tanto física como conceptualmente (D-05). Un evento de dominio registra una
transición de estado de UNA cuenta (agregado); una operación que afecta a varias cuentas emite
VARIAS filas que comparten `operation_id` (evento compuesto, D-09).

Helpers SIN commit, pensados para componerse DENTRO de `txn.financial_transaction` (una sola
transacción por comando). El llamador es dueño de la transacción. La `UNIQUE(aggregate_id,
aggregate_ver)` del esquema impide aplicar dos veces la misma versión de un agregado
(anti-duplicado); un segundo intento lanza `sqlite3.IntegrityError` y aborta la transacción.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from typing import Any

# Catálogo canónico de tipos de evento de dominio (design.md §5). Metadatos NO sensibles.
EVENT_ACCOUNT_OPENED = "ACCOUNT_OPENED"
EVENT_INTERNAL_TRANSFER_DEBITED = "INTERNAL_TRANSFER_DEBITED"
EVENT_INTERNAL_TRANSFER_CREDITED = "INTERNAL_TRANSFER_CREDITED"
EVENT_CONVERSION_DEBITED = "CONVERSION_DEBITED"
EVENT_CONVERSION_CREDITED = "CONVERSION_CREDITED"
EVENT_ACH_DEBITED = "ACH_DEBITED"
EVENT_ACH_SETTLED = "ACH_SETTLED"
EVENT_ACH_REFUNDED = "ACH_REFUNDED"
EVENT_RECURRING_DEBITED = "RECURRING_DEBITED"
EVENT_RECURRING_CREDITED = "RECURRING_CREDITED"


@dataclass
class DomainEvent:
    seq: int
    event_id: str
    event_type: str
    aggregate_id: str
    aggregate_ver: int
    operation_id: str
    currency: str
    amount_minor: int
    payload: dict[str, Any]
    occurred_at: str


def _row_to_event(row: sqlite3.Row) -> DomainEvent:
    return DomainEvent(
        seq=row["seq"],
        event_id=row["event_id"],
        event_type=row["event_type"],
        aggregate_id=row["aggregate_id"],
        aggregate_ver=row["aggregate_ver"],
        operation_id=row["operation_id"],
        currency=row["currency"],
        amount_minor=row["amount_minor"],
        payload=json.loads(row["payload"]) if row["payload"] else {},
        occurred_at=row["occurred_at"],
    )


def current_version(conn: sqlite3.Connection, aggregate_id: str) -> int:
    """Versión actual de un agregado = nº de eventos aplicados (0 si no hay ninguno)."""
    row = conn.execute(
        "SELECT MAX(aggregate_ver) AS v FROM domain_event WHERE aggregate_id = ?",
        (aggregate_id,),
    ).fetchone()
    return int(row["v"]) if row and row["v"] is not None else 0


def append_event_no_commit(
    conn: sqlite3.Connection,
    *,
    event_type: str,
    aggregate_id: str,
    aggregate_ver: int,
    operation_id: str,
    currency: str,
    amount_minor: int,
    payload: dict[str, Any] | None,
    occurred_at: str,
) -> str:
    """Añade un evento de dominio SIN commit (se compone en la transacción del comando).

    `aggregate_ver` DEBE ser la versión resultante de ese agregado (versión previa + 1). La
    `UNIQUE(aggregate_id, aggregate_ver)` rechaza una segunda aplicación de la misma versión.
    Devuelve el `event_id` asignado.
    """
    event_id = str(uuid.uuid4())
    payload_text = json.dumps(payload or {}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    conn.execute(
        """INSERT INTO domain_event
           (event_id, event_type, aggregate_id, aggregate_ver, operation_id,
            currency, amount_minor, payload, occurred_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (event_id, event_type, aggregate_id, aggregate_ver, operation_id,
         currency, amount_minor, payload_text, occurred_at),
    )
    return event_id


def read_events(conn: sqlite3.Connection, aggregate_id: str | None = None) -> list[DomainEvent]:
    """Lee eventos por `seq` ascendente; si `aggregate_id`, solo los de ese agregado."""
    if aggregate_id is None:
        rows = conn.execute("SELECT * FROM domain_event ORDER BY seq ASC").fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM domain_event WHERE aggregate_id = ? ORDER BY aggregate_ver ASC",
            (aggregate_id,),
        ).fetchall()
    return [_row_to_event(r) for r in rows]


def read_operation(conn: sqlite3.Connection, operation_id: str) -> list[DomainEvent]:
    """Lee todas las filas de un evento compuesto (misma `operation_id`), por `seq`."""
    rows = conn.execute(
        "SELECT * FROM domain_event WHERE operation_id = ? ORDER BY seq ASC",
        (operation_id,),
    ).fetchall()
    return [_row_to_event(r) for r in rows]
