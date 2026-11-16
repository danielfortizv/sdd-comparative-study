"""Verificación de la migración de esquema de la Etapa 2 (Tarea 7).

Verificación mínima del andamiaje transaccional e idempotente de `app.db.migrate` y de la
evolución aditiva de la tabla `transfer`. NO es la suite de migración completa (Tarea 13).

Estrategia: cada prueba construye una base de datos SQLite temporal con el **esquema heredado
de la Etapa 1** (vía `init_schema` + `seed`), equivalente a una copia de una DB de Etapa 1, y
aplica `migrate` sobre ella. Nunca se usa la DB histórica como objetivo (es de solo lectura).

_Requisitos: 15.8, 16.3_ · _Diseño: §Migración (DD-5, F11, F12)_
"""

import sqlite3

import app.db as db
from app.seed import seed


def _legacy_db(path):
    """Crea una DB con el esquema y la siembra de la Etapa 1 (sin columnas de Etapa 2)."""
    conn = db.get_connection(path)
    try:
        db.init_schema(conn)   # esquema heredado E1 (sin columnas nuevas)
        seed(conn)             # cliente, 2 cuentas, 2 transferencias históricas
    finally:
        conn.close()


def _columns(path, table):
    conn = db.get_connection(path)
    try:
        return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    finally:
        conn.close()


def _snapshot(path):
    """Captura saldos y transferencias (orden estable) para comparar antes/después."""
    conn = db.get_connection(path)
    try:
        accounts = conn.execute(
            "SELECT kind, display_name, balance_cents FROM account ORDER BY kind"
        ).fetchall()
        transfers = conn.execute(
            "SELECT id, from_kind, to_kind, amount_cents, description, status, created_at "
            "FROM transfer ORDER BY created_at, rowid"
        ).fetchall()
    finally:
        conn.close()
    return (
        [tuple(r) for r in accounts],
        [tuple(r) for r in transfers],
    )


def test_migracion_exitosa_sobre_esquema_heredado(tmp_path):
    """migrate() añade las columnas nuevas a `transfer` sobre un esquema de Etapa 1."""
    path = tmp_path / "legacy.db"
    _legacy_db(path)
    # Antes: la tabla transfer NO tiene las columnas de Etapa 2.
    before_cols = _columns(path, "transfer")
    assert "type" not in before_cols

    conn = db.get_connection(path)
    try:
        db.migrate(conn)
    finally:
        conn.close()

    after_cols = _columns(path, "transfer")
    for col in ("type", "beneficiary_id", "beneficiary_snapshot", "settled_at",
                "refunded", "schedule_id"):
        assert col in after_cols


def test_migracion_idempotente(tmp_path):
    """Ejecutar migrate() dos veces no duplica ni corrompe el esquema."""
    path = tmp_path / "legacy.db"
    _legacy_db(path)
    conn = db.get_connection(path)
    try:
        db.migrate(conn)
        cols_after_first = _columns(path, "transfer")
        db.migrate(conn)  # segunda ejecución
        cols_after_second = _columns(path, "transfer")
    finally:
        conn.close()
    assert cols_after_first == cols_after_second


def test_saldos_y_historicas_preservadas(tmp_path):
    """Los saldos y las transferencias históricas son idénticos antes y después de migrar."""
    path = tmp_path / "legacy.db"
    _legacy_db(path)
    accounts_before, transfers_before = _snapshot(path)

    conn = db.get_connection(path)
    try:
        db.migrate(conn)
    finally:
        conn.close()

    accounts_after, transfers_after = _snapshot(path)
    assert accounts_after == accounts_before          # saldos intactos
    assert transfers_after == transfers_before        # históricas intactas (mismos campos E1)
    # Siguen siendo exactamente dos históricas COMPLETED.
    assert len(transfers_after) == 2
    assert all(t[5] == "COMPLETED" for t in transfers_after)


def test_clasificacion_type_internal(tmp_path):
    """Tras migrar, las filas heredadas quedan clasificadas como `type='internal'`."""
    path = tmp_path / "legacy.db"
    _legacy_db(path)
    conn = db.get_connection(path)
    try:
        db.migrate(conn)
        rows = conn.execute("SELECT type FROM transfer").fetchall()
    finally:
        conn.close()
    assert len(rows) == 2
    assert all(r["type"] == "internal" for r in rows)
    # Ninguna fila queda con type NULL o desconocido.
    assert all(r["type"] is not None for r in rows)


def test_rollback_ante_fallo(tmp_path, monkeypatch):
    """Si una operación de la migración falla, se revierte por completo (sin cambios parciales)."""
    path = tmp_path / "legacy.db"
    _legacy_db(path)
    before_cols = _columns(path, "transfer")

    # Forzar un fallo a mitad de la migración: parchear _column_exists para que, tras permitir
    # añadir la primera columna, lance una excepción en la segunda comprobación.
    original = db._column_exists
    state = {"calls": 0}

    def flaky(conn, table, column):
        state["calls"] += 1
        if state["calls"] >= 2:
            raise sqlite3.OperationalError("fallo simulado a mitad de migración")
        return original(conn, table, column)

    monkeypatch.setattr(db, "_column_exists", flaky)

    conn = db.get_connection(path)
    try:
        import pytest
        with pytest.raises(sqlite3.OperationalError):
            db.migrate(conn)
    finally:
        conn.close()

    # Tras el rollback, el esquema de `transfer` no debe haber cambiado respecto al inicio.
    after_cols = _columns(path, "transfer")
    assert after_cols == before_cols


def test_acceso_tras_migracion_con_conexion_heredada(tmp_path):
    """La app puede acceder a la DB migrada usando get_connection() heredado."""
    path = tmp_path / "legacy.db"
    _legacy_db(path)
    conn = db.get_connection(path)
    try:
        db.migrate(conn)
    finally:
        conn.close()
    # Nueva conexión heredada: consulta normal sigue funcionando.
    conn = db.get_connection(path)
    try:
        n = conn.execute("SELECT COUNT(*) AS n FROM account").fetchone()["n"]
        # La columna nueva es consultable.
        conn.execute("SELECT type FROM transfer LIMIT 1").fetchone()
    finally:
        conn.close()
    assert n == 2
