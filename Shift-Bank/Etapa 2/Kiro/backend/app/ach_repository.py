"""Acceso a datos para beneficiarios y transferencias ACH (Etapa 2, Fase D).

SQL puro sobre la conexión heredada (sin ORM). Las mutaciones financieras ACH se exponen como
operaciones SIN commit, pensadas para componerse dentro de `financial_transaction` (punto 4:
creación de la fila ACH + débito en una única transacción; NO se reproduce el patrón interno de
commit-antes-del-efecto-financiero).

Montos en centavos enteros; fechas ISO-8601 UTC.
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass


@dataclass
class Beneficiary:
    id: str
    name: str
    bank: str
    routing_number: str
    account_number: str


# --- Beneficiarios (Tarea 19) --------------------------------------------------

def create_beneficiary(conn: sqlite3.Connection, *, customer_id: str, name: str, bank: str,
                       routing_number: str, account_number: str, created_at: str) -> str:
    bid = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO beneficiary
           (id, customer_id, name, bank, routing_number, account_number, created_at, deleted_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, NULL)""",
        (bid, customer_id, name, bank, routing_number, account_number, created_at),
    )
    conn.commit()
    return bid


def list_beneficiaries(conn: sqlite3.Connection, customer_id: str) -> list[sqlite3.Row]:
    """Lista los beneficiarios NO borrados del cliente (propiedad: filtra por customer_id)."""
    return conn.execute(
        """SELECT id, name, bank, routing_number, account_number
           FROM beneficiary
           WHERE customer_id = ? AND deleted_at IS NULL
           ORDER BY created_at""",
        (customer_id,),
    ).fetchall()


def get_beneficiary(conn: sqlite3.Connection, customer_id: str, beneficiary_id: str):
    """Beneficiario por id, SOLO si pertenece al cliente y no está borrado (aislamiento ACH-02)."""
    return conn.execute(
        """SELECT id, name, bank, routing_number, account_number
           FROM beneficiary
           WHERE id = ? AND customer_id = ? AND deleted_at IS NULL""",
        (beneficiary_id, customer_id),
    ).fetchone()


def soft_delete_beneficiary(conn: sqlite3.Connection, customer_id: str, beneficiary_id: str,
                            deleted_at: str) -> bool:
    """Borrado lógico; devuelve True si se marcó (pertenecía al cliente y no estaba borrado)."""
    cur = conn.execute(
        "UPDATE beneficiary SET deleted_at = ? WHERE id = ? AND customer_id = ? AND deleted_at IS NULL",
        (deleted_at, beneficiary_id, customer_id),
    )
    conn.commit()
    return cur.rowcount > 0


# --- Transferencias ACH --------------------------------------------------------

def create_ach_no_commit(conn: sqlite3.Connection, *, transfer_id: str, reference: str,
                         from_kind: str, amount_cents: int, description: str, status: str,
                         requires_mfa: bool, created_at: str, expires_at: str | None,
                         beneficiary_id: str | None, beneficiary_snapshot: str,
                         schedule_id: str | None = None) -> None:
    """Inserta una fila ACH SIN commit (se compone en la transacción financiera, punto 4).

    `type='ach'`. El débito (cuando aplica) se ejecuta en la MISMA transacción vía
    `debit_source_no_commit`, de modo que nunca se commitea una ACH `pending` sin su débito.
    `schedule_id` (opcional) traza la ocurrencia recurrente que originó la ACH (Tarea 30); es
    `NULL` para las ACH interactivas de la Fase D (compatibilidad hacia atrás).
    """
    conn.execute(
        """INSERT INTO transfer
           (id, reference, from_kind, to_kind, amount_cents, description, status, requires_mfa,
            created_at, expires_at, completed_at, type, beneficiary_id, beneficiary_snapshot,
            settled_at, refunded, schedule_id)
           VALUES (?, ?, ?, '', ?, ?, ?, ?, ?, ?, NULL, 'ach', ?, ?, NULL, 0, ?)""",
        (
            transfer_id, reference, from_kind, amount_cents, description, status,
            1 if requires_mfa else 0, created_at, expires_at, beneficiary_id, beneficiary_snapshot,
            schedule_id,
        ),
    )


def debit_source_no_commit(conn: sqlite3.Connection, *, from_kind: str, amount_cents: int) -> None:
    """Debita la cuenta de origen SIN commit (uso dentro de la transacción financiera)."""
    conn.execute(
        "UPDATE account SET balance_cents = balance_cents - ? WHERE kind = ?",
        (amount_cents, from_kind),
    )


def set_ach_status_no_commit(conn: sqlite3.Connection, *, transfer_id: str, status: str,
                             settled_at: str | None = None) -> None:
    """Fija el estado ACH SIN commit."""
    conn.execute(
        "UPDATE transfer SET status = ?, settled_at = ? WHERE id = ?",
        (status, settled_at, transfer_id),
    )


def get_ach_by_reference(conn: sqlite3.Connection, reference: str):
    return conn.execute(
        """SELECT id, reference, from_kind, amount_cents, description, status, requires_mfa,
                  created_at, expires_at, settled_at, refunded, beneficiary_snapshot
           FROM transfer WHERE reference = ? AND type = 'ach'""",
        (reference,),
    ).fetchone()


def get_ach_by_id(conn: sqlite3.Connection, transfer_id: str):
    return conn.execute(
        """SELECT id, reference, from_kind, amount_cents, status, refunded
           FROM transfer WHERE id = ? AND type = 'ach'""",
        (transfer_id,),
    ).fetchone()


def settle_ach_no_commit(conn: sqlite3.Connection, *, transfer_id: str, settled_at: str) -> int:
    """Transición `pending → settled` con guarda. Devuelve filas afectadas (idempotente)."""
    cur = conn.execute(
        "UPDATE transfer SET status = 'settled', settled_at = ? "
        "WHERE id = ? AND type = 'ach' AND status = 'pending'",
        (settled_at, transfer_id),
    )
    return cur.rowcount


def fail_and_refund_no_commit(conn: sqlite3.Connection, *, transfer_id: str, from_kind: str,
                              amount_cents: int) -> int:
    """Transición `pending → failed` + reembolso exactamente-una-vez (guarda `refunded=0`).

    Devuelve filas afectadas por la transición. Si la guarda no aplica (ya failed/refunded),
    devuelve 0 y NO reembolsa de nuevo. Uso dentro de la transacción financiera.
    """
    cur = conn.execute(
        "UPDATE transfer SET status = 'failed', refunded = 1 "
        "WHERE id = ? AND type = 'ach' AND status = 'pending' AND refunded = 0",
        (transfer_id,),
    )
    if cur.rowcount == 1:
        # Reembolso del monto exacto al origen (una sola vez).
        conn.execute(
            "UPDATE account SET balance_cents = balance_cents + ? WHERE kind = ?",
            (amount_cents, from_kind),
        )
    return cur.rowcount


def list_pending_ach(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """ACH en estado `pending` (para el barrido de settlement del scheduler, Tarea 32)."""
    return conn.execute(
        """SELECT id, from_kind, amount_cents, created_at
           FROM transfer WHERE type = 'ach' AND status = 'pending'"""
    ).fetchall()
