"""Repositorio: acceso a datos con SQL puro (sqlite3), sin ORM.

Única capa que habla con la base de datos. Convierte filas a dataclasses internas y
ejecuta las mutaciones de saldo dentro de una transacción atómica (Requisito 7.4).
"""

import sqlite3
import uuid
from dataclasses import dataclass


@dataclass
class Account:
    kind: str
    display_name: str
    balance_cents: int


@dataclass
class Transfer:
    id: str
    reference: str | None
    from_kind: str
    to_kind: str
    amount_cents: int
    description: str
    status: str
    requires_mfa: int
    created_at: str
    expires_at: str | None
    completed_at: str | None


def _row_to_account(row: sqlite3.Row) -> Account:
    return Account(
        kind=row["kind"],
        display_name=row["display_name"],
        balance_cents=row["balance_cents"],
    )


def _row_to_transfer(row: sqlite3.Row) -> Transfer:
    return Transfer(
        id=row["id"],
        reference=row["reference"],
        from_kind=row["from_kind"],
        to_kind=row["to_kind"],
        amount_cents=row["amount_cents"],
        description=row["description"],
        status=row["status"],
        requires_mfa=row["requires_mfa"],
        created_at=row["created_at"],
        expires_at=row["expires_at"],
        completed_at=row["completed_at"],
    )


# --- Cuentas (Tarea 6) ---------------------------------------------------------

def list_accounts(conn: sqlite3.Connection) -> list[Account]:
    """Devuelve las cuentas en orden fijo (checking, savings)."""
    rows = conn.execute(
        "SELECT kind, display_name, balance_cents FROM account"
    ).fetchall()
    accounts = [_row_to_account(r) for r in rows]
    order = {"checking": 0, "savings": 1}
    accounts.sort(key=lambda a: order.get(a.kind, 99))
    return accounts


def get_account(conn: sqlite3.Connection, kind: str) -> Account | None:
    row = conn.execute(
        "SELECT kind, display_name, balance_cents FROM account WHERE kind = ?",
        (kind,),
    ).fetchone()
    return _row_to_account(row) if row else None


# --- Transferencias (Tarea 7) --------------------------------------------------

def create_transfer(
    conn: sqlite3.Connection,
    *,
    from_kind: str,
    to_kind: str,
    amount_cents: int,
    description: str,
    status: str,
    requires_mfa: bool,
    created_at: str,
    expires_at: str | None,
    reference: str | None,
    completed_at: str | None = None,
) -> Transfer:
    transfer_id = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO transfer
           (id, reference, from_kind, to_kind, amount_cents, description,
            status, requires_mfa, created_at, expires_at, completed_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            transfer_id,
            reference,
            from_kind,
            to_kind,
            amount_cents,
            description,
            status,
            1 if requires_mfa else 0,
            created_at,
            expires_at,
            completed_at,
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM transfer WHERE id = ?", (transfer_id,)).fetchone()
    return _row_to_transfer(row)


def get_transfer_by_reference(conn: sqlite3.Connection, reference: str) -> Transfer | None:
    row = conn.execute(
        "SELECT * FROM transfer WHERE reference = ?", (reference,)
    ).fetchone()
    return _row_to_transfer(row) if row else None


def list_transfers(conn: sqlite3.Connection) -> list[Transfer]:
    """Historial ordenado por fecha de creación descendente (Requisito 5.1)."""
    rows = conn.execute(
        "SELECT * FROM transfer ORDER BY created_at DESC, rowid DESC"
    ).fetchall()
    return [_row_to_transfer(r) for r in rows]


def update_transfer_status(
    conn: sqlite3.Connection,
    transfer_id: str,
    status: str,
    *,
    completed_at: str | None = None,
) -> None:
    conn.execute(
        "UPDATE transfer SET status = ?, completed_at = ? WHERE id = ?",
        (status, completed_at, transfer_id),
    )
    conn.commit()


def apply_transfer(
    conn: sqlite3.Connection,
    *,
    transfer_id: str,
    from_kind: str,
    to_kind: str,
    amount_cents: int,
    completed_at: str,
) -> None:
    """Aplica el movimiento de saldos y marca COMPLETED de forma atómica (Requisito 7.4).

    Todo ocurre dentro de una única transacción (BEGIN IMMEDIATE ... COMMIT): se descuenta
    del origen, se abona al destino y se actualiza el estado; o no se aplica nada.
    """
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "UPDATE account SET balance_cents = balance_cents - ? WHERE kind = ?",
            (amount_cents, from_kind),
        )
        conn.execute(
            "UPDATE account SET balance_cents = balance_cents + ? WHERE kind = ?",
            (amount_cents, to_kind),
        )
        conn.execute(
            "UPDATE transfer SET status = ?, completed_at = ? WHERE id = ?",
            ("COMPLETED", completed_at, transfer_id),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
