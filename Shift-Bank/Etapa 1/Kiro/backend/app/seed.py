"""Siembra del estado inicial (Requisitos 1 y 4).

Crea exactamente un cliente mock, dos cuentas (Checking/Savings) con saldos iniciales
fijados directamente, y dos transferencias históricas COMPLETED insertadas como registros.

Importante: la siembra NO deriva los saldos a partir de las transferencias históricas.
Los saldos iniciales son los valores de partida definitivos y las históricas se insertan
como datos independientes (Requisitos 1.4 y 4.4). La siembra es idempotente.
"""

import sqlite3
import uuid
from datetime import datetime, timedelta, timezone

# Saldos iniciales en centavos (Requisito 1.3).
_CHECKING_INITIAL_CENTS = 5_000_000_00  # COP 5,000,000.00
_SAVINGS_INITIAL_CENTS = 15_000_000_00  # COP 15,000,000.00

# Transferencias históricas en centavos (Requisito 4.2, 4.3).
_HIST_SAVINGS_TO_CHECKING_CENTS = 500_000_00  # COP 500,000.00
_HIST_CHECKING_TO_SAVINGS_CENTS = 100_000_00  # COP 100,000.00


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    """Formato ISO-8601 UTC con sufijo Z."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_seeded(conn: sqlite3.Connection) -> bool:
    row = conn.execute("SELECT COUNT(*) AS n FROM customer").fetchone()
    return row is not None and row["n"] > 0


def seed(conn: sqlite3.Connection) -> None:
    """Siembra idempotente del estado inicial completo."""
    if is_seeded(conn):
        return

    customer_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO customer (id, name) VALUES (?, ?)",
        (customer_id, "Shift Bank Customer"),
    )

    # Cuentas con saldos iniciales fijados directamente (Requisito 1.2, 1.3).
    conn.execute(
        """INSERT INTO account (id, customer_id, kind, display_name, balance_cents)
           VALUES (?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), customer_id, "checking", "Checking", _CHECKING_INITIAL_CENTS),
    )
    conn.execute(
        """INSERT INTO account (id, customer_id, kind, display_name, balance_cents)
           VALUES (?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), customer_id, "savings", "Savings", _SAVINGS_INITIAL_CENTS),
    )

    # Transferencias históricas como registros COMPLETED, sin aplicar saldos (Requisito 4).
    now = _now_utc()
    hist_savings_to_checking_at = now - timedelta(days=3)
    hist_checking_to_savings_at = now - timedelta(days=1)

    conn.execute(
        """INSERT INTO transfer
           (id, reference, from_kind, to_kind, amount_cents, description,
            status, requires_mfa, created_at, expires_at, completed_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            str(uuid.uuid4()),
            None,
            "savings",
            "checking",
            _HIST_SAVINGS_TO_CHECKING_CENTS,
            "Transferencia histórica de Savings a Checking",
            "COMPLETED",
            0,
            _iso(hist_savings_to_checking_at),
            None,
            _iso(hist_savings_to_checking_at),
        ),
    )
    conn.execute(
        """INSERT INTO transfer
           (id, reference, from_kind, to_kind, amount_cents, description,
            status, requires_mfa, created_at, expires_at, completed_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            str(uuid.uuid4()),
            None,
            "checking",
            "savings",
            _HIST_CHECKING_TO_SAVINGS_CENTS,
            "Transferencia histórica de Checking a Savings",
            "COMPLETED",
            0,
            _iso(hist_checking_to_savings_at),
            None,
            _iso(hist_checking_to_savings_at),
        ),
    )

    conn.commit()
