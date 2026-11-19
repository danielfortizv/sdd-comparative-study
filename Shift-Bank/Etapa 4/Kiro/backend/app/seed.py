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


# --- Fixture experimental de la Etapa 4 (D-02, DK-01, Tarea 6) -----------------
#
# RESET EXPERIMENTAL CONTROLADO (DK-01): la Etapa 4 parte de una fixture SEPARADA con los saldos
# de la decisión D-02. Esto NO es una conversión COP->USD ni una migración que preserve valor
# monetario; es una discontinuidad experimental DECLARADA. El estado y la evidencia de la Etapa 3
# (COP) se preservan sin modificación en su propio árbol; esta siembra no los lee ni los altera.
#
# Las cuatro cuentas usan `kind` distintos para no colisionar con la restricción heredada
# UNIQUE(customer_id, kind) y, a la vez, respetar el índice UNIQUE(customer_id, kind, currency).
# Cada cuenta recibe un identificador público inmutable (D-02) y su moneda fija (D-01).
_STAGE4_ACCOUNTS: list[tuple[str, str, str, str, int]] = [
    # (public_id, kind, display_name, currency, balance_minor)
    ("CHK-1001", "checking", "Checking", "USD", 2_500_00),
    ("SAV-2001", "savings", "Savings", "USD", 10_000_00),
    ("EUR-3001", "eur", "EUR Account", "EUR", 0),
    ("GBP-4001", "gbp", "GBP Account", "GBP", 0),
]


def is_stage4_seeded(conn: sqlite3.Connection) -> bool:
    """True si la fixture D-02 ya existe (idempotencia de `seed_stage4`)."""
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM account WHERE public_id IN ('CHK-1001','SAV-2001','EUR-3001','GBP-4001')"
    ).fetchone()
    return row is not None and row["n"] >= len(_STAGE4_ACCOUNTS)


def seed_stage4(conn: sqlite3.Connection) -> None:
    """Siembra idempotente de la fixture experimental de la Etapa 4 (D-02, DK-01).

    Crea el cliente mock (si falta), las cuatro cuentas D-02 con su `public_id`/moneda/saldo y
    versión inicial 1, un evento de dominio `ACCOUNT_OPENED` por cuenta (saldo inicial) y la
    proyección CQRS inicial coherente. No deriva ni toca datos de la Etapa 3. Idempotente: si las
    cuentas ya existen, no hace nada.

    Nota de no-doble-conteo (D-05, R6-4): el saldo inicial se representa EXACTAMENTE por el evento
    `ACCOUNT_OPENED` (amount_minor = saldo inicial) y la proyección se fija a ese mismo valor; no
    hay transferencias históricas que re-muevan el saldo en esta fixture.
    """
    if is_stage4_seeded(conn):
        return

    row = conn.execute("SELECT id FROM customer LIMIT 1").fetchone()
    if row is None:
        customer_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO customer (id, name) VALUES (?, ?)",
            (customer_id, "Shift Bank Customer"),
        )
    else:
        customer_id = row["id"]

    now = _iso(_now_utc())
    for public_id, kind, display_name, currency, balance_minor in _STAGE4_ACCOUNTS:
        existing = conn.execute(
            "SELECT id FROM account WHERE public_id = ?", (public_id,)
        ).fetchone()
        if existing is not None:
            continue
        account_id = str(uuid.uuid4())
        version = 1  # ACCOUNT_OPENED aplica la versión 1
        conn.execute(
            """INSERT INTO account
               (id, customer_id, kind, display_name, balance_cents, currency, public_id, version)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (account_id, customer_id, kind, display_name, balance_minor, currency, public_id, version),
        )
        # Evento de dominio ACCOUNT_OPENED (saldo inicial como delta +balance_minor).
        conn.execute(
            """INSERT INTO domain_event
               (event_id, event_type, aggregate_id, aggregate_ver, operation_id,
                currency, amount_minor, payload, occurred_at)
               VALUES (?, 'ACCOUNT_OPENED', ?, 1, ?, ?, ?, ?, ?)""",
            (
                str(uuid.uuid4()), account_id, str(uuid.uuid4()), currency, balance_minor,
                f'{{"public_id":"{public_id}","kind":"{kind}"}}', now,
            ),
        )
        # Proyección CQRS inicial coherente (version == account.version).
        conn.execute(
            """INSERT INTO account_projection
               (account_id, public_id, kind, currency, balance_minor, version, updated_at)
               VALUES (?, ?, ?, ?, ?, 1, ?)""",
            (account_id, public_id, kind, currency, balance_minor, now),
        )

    conn.commit()


# --- Siembra de límites por defecto (Etapa 2, Tarea 11) -----------------------

def seed_limits(conn: sqlite3.Connection) -> None:
    """Siembra idempotente de los límites por defecto del cliente mock (E2-KIRO-D01).

    Inserta una fila en `transfer_limit` con los valores por defecto (por transferencia
    500.000.000 centavos; diario 1.000.000.000 centavos) solo si el cliente aún no tiene
    límites configurados. No altera la siembra de la Etapa 1 ni los límites ya existentes.

    Requiere que el cliente mock ya exista (seed() se ejecuta antes en el arranque).
    """
    from .config import DEFAULT_DAILY_LIMIT_CENTS, DEFAULT_PER_TRANSFER_LIMIT_CENTS

    row = conn.execute("SELECT id FROM customer LIMIT 1").fetchone()
    if row is None:
        return  # sin cliente sembrado aún; nada que hacer
    customer_id = row["id"]

    existing = conn.execute(
        "SELECT 1 FROM transfer_limit WHERE customer_id = ?", (customer_id,)
    ).fetchone()
    if existing is not None:
        return  # idempotente: no sobrescribe límites ya configurados

    conn.execute(
        """INSERT INTO transfer_limit (customer_id, per_transfer_cents, daily_cents, updated_at)
           VALUES (?, ?, ?, ?)""",
        (
            customer_id,
            DEFAULT_PER_TRANSFER_LIMIT_CENTS,
            DEFAULT_DAILY_LIMIT_CENTS,
            _iso(_now_utc()),
        ),
    )
    conn.commit()
