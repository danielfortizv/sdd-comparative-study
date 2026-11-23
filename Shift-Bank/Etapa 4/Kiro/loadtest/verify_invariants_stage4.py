"""Verificación de invariantes multidivisa de la Etapa 4 (Tarea 24; D-05/D-06/D-09).

Complementa `verify_invariants.py` (heredado, legacy) con los invariantes del modelo
event-sourced/CQRS de la Etapa 4. Se ejecuta tras una corrida de operaciones (carga o lote
sintético) contra una DB aislada. Cualquier violación marca la corrida como FALLIDA, con
independencia del rendimiento.

Invariantes verificados (derivados del modelo real `domain_event`/`account_projection`/`account`):

1. **Consistencia de proyección (D-06).** Para cada cuenta, `account_projection.balance_minor`
   == Σ(amount_minor de sus eventos) y `account_projection.version` == `account.version`.
2. **Sin aplicación duplicada de eventos (D-09).** `UNIQUE(aggregate_id, aggregate_ver)`: no hay
   dos eventos con la misma versión por agregado; las versiones por agregado son contiguas 1..N.
3. **Conservación por moneda en operaciones internas (D-03).** La suma de `amount_minor` de los
   eventos de transferencia interna por moneda es 0 (lo que sale de una cuenta entra en otra de
   la MISMA moneda). Las conversiones NO se incluyen aquí (cruzan monedas por diseño).
4. **Reconstrucción determinista (D-06).** Reconstruir las proyecciones desde los eventos
   reproduce exactamente el estado vivo.
"""

from __future__ import annotations

import sqlite3

from app import projections


class InvariantViolation(RuntimeError):
    pass


def check_projection_consistency(conn: sqlite3.Connection) -> None:
    if not projections.verify_consistency(conn):
        raise InvariantViolation("proyección inconsistente con los eventos o la versión de cuenta")


def check_no_duplicate_versions(conn: sqlite3.Connection) -> None:
    dup = conn.execute(
        """SELECT aggregate_id, aggregate_ver, COUNT(*) AS n
           FROM domain_event GROUP BY aggregate_id, aggregate_ver HAVING n > 1"""
    ).fetchall()
    if dup:
        raise InvariantViolation(f"versiones de agregado duplicadas: {len(dup)}")
    # Contigüidad 1..N por agregado.
    for row in conn.execute("SELECT DISTINCT aggregate_id FROM domain_event").fetchall():
        vers = [r["aggregate_ver"] for r in conn.execute(
            "SELECT aggregate_ver FROM domain_event WHERE aggregate_id=? ORDER BY aggregate_ver",
            (row["aggregate_id"],)).fetchall()]
        if vers != list(range(1, len(vers) + 1)):
            raise InvariantViolation(f"versiones no contiguas en {row['aggregate_id']}: {vers}")


def check_internal_conservation_per_currency(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        """SELECT currency, COALESCE(SUM(amount_minor),0) AS s FROM domain_event
           WHERE event_type IN ('INTERNAL_TRANSFER_DEBITED','INTERNAL_TRANSFER_CREDITED')
           GROUP BY currency"""
    ).fetchall()
    for r in rows:
        if r["s"] != 0:
            raise InvariantViolation(
                f"conservación interna rota en {r['currency']}: suma {r['s']} != 0")


def check_rebuild_matches(conn: sqlite3.Connection) -> None:
    live = {r["account_id"]: (r["balance_minor"], r["version"]) for r in conn.execute(
        "SELECT account_id, balance_minor, version FROM account_projection").fetchall()}
    conn.execute("BEGIN")
    try:
        projections.rebuild_projections(conn)
        rebuilt = {r["account_id"]: (r["balance_minor"], r["version"]) for r in conn.execute(
            "SELECT account_id, balance_minor, version FROM account_projection").fetchall()}
    finally:
        conn.rollback()  # no persistir el rebuild de verificación
    if rebuilt != live:
        raise InvariantViolation("el rebuild determinista no reproduce el estado vivo")


def verify_all(conn: sqlite3.Connection) -> list[str]:
    """Ejecuta todos los invariantes. Devuelve la lista de nombres OK; lanza en la 1ª violación."""
    check_projection_consistency(conn)
    check_no_duplicate_versions(conn)
    check_internal_conservation_per_currency(conn)
    check_rebuild_matches(conn)
    return ["projection_consistency", "no_duplicate_versions",
            "internal_conservation_per_currency", "rebuild_matches"]
