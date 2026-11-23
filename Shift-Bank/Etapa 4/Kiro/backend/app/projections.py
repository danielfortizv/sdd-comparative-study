"""Proyecciones CQRS del lado de lectura (Etapa 4, Tarea 9; D-06).

`account_projection` es la fuente autoritativa de las CONSULTAS de saldo. Se actualiza de forma
**síncrona y atómica** en la MISMA transacción que persiste los eventos de dominio (D-06). La
reconstrucción (`rebuild_projections`) reaplica los eventos desde `domain_event` de forma
**determinista**, obteniendo el mismo estado. Ante una inconsistencia detectada entre eventos y
proyección, el sistema falla de forma cerrada (`ProjectionInconsistencyError`).

Invariante de consistencia (verificable): para cada cuenta,
`account_projection.version == account.version` y
`account_projection.balance_minor == Σ(amount_minor de los eventos de esa cuenta)`.
"""

from __future__ import annotations

import sqlite3

from . import events


class ProjectionInconsistencyError(RuntimeError):
    """Inconsistencia detectada entre eventos y proyección: fail-closed (D-06)."""


def apply_event_to_projection_no_commit(
    conn: sqlite3.Connection,
    *,
    account_id: str,
    public_id: str,
    kind: str,
    currency: str,
    delta_minor: int,
    new_version: int,
    updated_at: str,
) -> None:
    """Aplica el efecto de un evento a la proyección SIN commit (D-06).

    UPSERT: si la proyección no existe (p. ej. ACCOUNT_OPENED), la crea con el saldo = delta;
    si existe, suma el delta y fija la nueva versión. El llamador (patrón de comando) garantiza
    que `new_version` == versión del agregado tras el evento.
    """
    row = conn.execute(
        "SELECT balance_minor FROM account_projection WHERE account_id = ?", (account_id,)
    ).fetchone()
    if row is None:
        conn.execute(
            """INSERT INTO account_projection
               (account_id, public_id, kind, currency, balance_minor, version, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (account_id, public_id, kind, currency, delta_minor, new_version, updated_at),
        )
    else:
        conn.execute(
            """UPDATE account_projection
               SET balance_minor = balance_minor + ?, version = ?, updated_at = ?
               WHERE account_id = ?""",
            (delta_minor, new_version, updated_at, account_id),
        )


def rebuild_projections(conn: sqlite3.Connection) -> None:
    """Reconstruye TODAS las proyecciones de forma determinista desde `domain_event` (D-06).

    Borra `account_projection` y reaplica cada evento por `aggregate_id`/`aggregate_ver`,
    resolviendo los metadatos de cuenta (public_id/kind/currency) desde `account`. Determinista:
    el orden por `(aggregate_id, aggregate_ver)` reproduce exactamente el estado vivo. Se ejecuta
    dentro de la transacción del llamador (sin commit propio) o puede componerse en una propia.
    """
    # Metadatos de cuenta por id (public_id/kind/currency) para poblar la proyección.
    meta = {
        r["id"]: (r["public_id"], r["kind"], r["currency"])
        for r in conn.execute("SELECT id, public_id, kind, currency FROM account").fetchall()
    }
    conn.execute("DELETE FROM account_projection")
    # Acumular saldo y versión por agregado reaplicando eventos en orden determinista.
    state: dict[str, tuple[int, int, str]] = {}  # account_id -> (balance, version, updated_at)
    for ev in events.read_events(conn):  # orden por seq (global, determinista)
        bal, ver, _ = state.get(ev.aggregate_id, (0, 0, ev.occurred_at))
        state[ev.aggregate_id] = (bal + ev.amount_minor, ev.aggregate_ver, ev.occurred_at)
    for account_id, (balance, version, updated_at) in state.items():
        if account_id not in meta:
            # Un evento sin cuenta correspondiente es una inconsistencia estructural.
            raise ProjectionInconsistencyError(
                f"evento sobre agregado desconocido: {account_id}"
            )
        public_id, kind, currency = meta[account_id]
        conn.execute(
            """INSERT INTO account_projection
               (account_id, public_id, kind, currency, balance_minor, version, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (account_id, public_id, kind, currency, balance, version, updated_at),
        )


def verify_consistency(conn: sqlite3.Connection) -> bool:
    """True si cada proyección cuadra con la suma de eventos y con `account.version` (D-06).

    Fuente de verdad: `domain_event`. Comprueba, por cuenta, que el saldo proyectado iguala la
    suma de `amount_minor` de sus eventos y que la versión proyectada iguala la de la cuenta.
    """
    # Suma de eventos por agregado.
    sums = {
        r["aggregate_id"]: (r["s"], r["v"])
        for r in conn.execute(
            "SELECT aggregate_id, COALESCE(SUM(amount_minor),0) AS s, MAX(aggregate_ver) AS v "
            "FROM domain_event GROUP BY aggregate_id"
        ).fetchall()
    }
    projections = conn.execute(
        "SELECT account_id, balance_minor, version FROM account_projection"
    ).fetchall()
    for p in projections:
        exp = sums.get(p["account_id"])
        if exp is None:
            return False
        exp_balance, exp_version = exp
        if p["balance_minor"] != exp_balance or p["version"] != exp_version:
            return False
    # Y versión de proyección == versión de cuenta.
    accounts = conn.execute("SELECT id, version FROM account").fetchall()
    proj_ver = {p["account_id"]: p["version"] for p in projections}
    for a in accounts:
        if a["id"] in proj_ver and proj_ver[a["id"]] != a["version"]:
            return False
    return True
