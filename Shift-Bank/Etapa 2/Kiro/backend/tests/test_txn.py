"""Pruebas de las utilidades compartidas de transacción financiera (Etapa 2, Tarea 10).

Verifican el límite transaccional reutilizable `financial_transaction`: commit atómico,
rollback ante excepción, atomicidad multi-operación, política de anidamiento, ausencia de
commits intermedios y comportamiento de locking entre conexiones SQLite distintas.

No prueban ACH, recurrentes ni límites (tareas posteriores). Usan una tabla auxiliar propia y
la DB aislada, sin depender de lógica de negocio.

_Requisitos: 15.7_ · _Diseño: §Consistencia transaccional (DD-4, F8/F9, F11)_
"""

import sqlite3

import pytest

import app.db as db
from app.txn import TransactionError, financial_transaction


def _db_with_aux(path):
    """DB temporal con una tabla auxiliar `kv(k PRIMARY KEY, v INTEGER)`."""
    conn = db.get_connection(path)
    conn.execute("CREATE TABLE kv (k TEXT PRIMARY KEY, v INTEGER NOT NULL)")
    conn.commit()
    return conn


def _value(path, key):
    conn = db.get_connection(path)
    try:
        row = conn.execute("SELECT v FROM kv WHERE k = ?", (key,)).fetchone()
        return row["v"] if row else None
    finally:
        conn.close()


def test_commit_exitoso_persiste_cambios(tmp_path):
    path = tmp_path / "t.db"
    conn = _db_with_aux(path)
    try:
        with financial_transaction(conn):
            conn.execute("INSERT INTO kv (k, v) VALUES ('a', 1)")
            conn.execute("INSERT INTO kv (k, v) VALUES ('b', 2)")
    finally:
        conn.close()
    assert _value(path, "a") == 1
    assert _value(path, "b") == 2


def test_rollback_ante_excepcion(tmp_path):
    path = tmp_path / "t.db"
    conn = _db_with_aux(path)
    try:
        with pytest.raises(RuntimeError):
            with financial_transaction(conn):
                conn.execute("INSERT INTO kv (k, v) VALUES ('a', 1)")
                raise RuntimeError("fallo del negocio")
    finally:
        conn.close()
    # Nada se persiste: rollback total.
    assert _value(path, "a") is None


def test_atomicidad_multi_operacion(tmp_path):
    """Varias actualizaciones dentro del bloque se confirman juntas."""
    path = tmp_path / "t.db"
    conn = _db_with_aux(path)
    try:
        conn.execute("INSERT INTO kv (k, v) VALUES ('saldo', 100)")
        conn.commit()
        with financial_transaction(conn):
            conn.execute("UPDATE kv SET v = v - 30 WHERE k = 'saldo'")
            conn.execute("INSERT INTO kv (k, v) VALUES ('destino', 30)")
    finally:
        conn.close()
    assert _value(path, "saldo") == 70
    assert _value(path, "destino") == 30


def test_fallo_en_segunda_operacion_no_preserva_la_primera(tmp_path):
    """Si la 2.ª operación falla, la 1.ª se revierte (sin actualización parcial)."""
    path = tmp_path / "t.db"
    conn = _db_with_aux(path)
    try:
        conn.execute("INSERT INTO kv (k, v) VALUES ('x', 5)")
        conn.commit()
        with pytest.raises(sqlite3.IntegrityError):
            with financial_transaction(conn):
                conn.execute("UPDATE kv SET v = 99 WHERE k = 'x'")      # 1.ª op
                conn.execute("INSERT INTO kv (k, v) VALUES ('x', 1)")   # 2.ª op: PK duplicada
    finally:
        conn.close()
    # La 1.ª operación NO se preserva: `x` mantiene su valor original.
    assert _value(path, "x") == 5


def test_composicion_de_operaciones_de_repositorio(tmp_path):
    """El llamador compone varias funciones bajo una sola transacción compartida."""
    path = tmp_path / "t.db"
    conn = _db_with_aux(path)

    def op_insert(c, k, v):
        c.execute("INSERT INTO kv (k, v) VALUES (?, ?)", (k, v))

    def op_bump(c, k):
        c.execute("UPDATE kv SET v = v + 1 WHERE k = ?", (k,))

    try:
        with financial_transaction(conn):
            op_insert(conn, "c", 10)
            op_bump(conn, "c")
            op_bump(conn, "c")
    finally:
        conn.close()
    assert _value(path, "c") == 12


def test_sin_commits_intermedios(tmp_path):
    """Dentro del bloque los cambios no son visibles para otra conexión hasta el commit."""
    path = tmp_path / "t.db"
    conn = _db_with_aux(path)
    try:
        with financial_transaction(conn):
            conn.execute("INSERT INTO kv (k, v) VALUES ('p', 7)")
            # Otra conexión NO debe ver el cambio aún (no hay commit intermedio).
            other = db.get_connection(path)
            try:
                seen = other.execute("SELECT v FROM kv WHERE k = 'p'").fetchone()
                assert seen is None
            finally:
                other.close()
        # Tras salir del bloque (commit), ya es visible.
        assert _value(path, "p") == 7
    finally:
        conn.close()


def test_anidamiento_rechazado(tmp_path):
    """Abrir una transacción financiera cuando ya hay una activa lanza TransactionError."""
    path = tmp_path / "t.db"
    conn = _db_with_aux(path)
    try:
        with financial_transaction(conn):
            conn.execute("INSERT INTO kv (k, v) VALUES ('n', 1)")
            with pytest.raises(TransactionError):
                with financial_transaction(conn):
                    pass
    finally:
        conn.close()


def test_locking_entre_conexiones_distintas(tmp_path):
    """BEGIN IMMEDIATE en una 2.ª conexión falla mientras la 1.ª tiene la transacción abierta."""
    path = tmp_path / "t.db"
    conn1 = _db_with_aux(path)
    # Conexión 2 con timeout corto para no bloquear la prueba.
    conn2 = sqlite3.connect(str(path), timeout=0.2)
    try:
        with financial_transaction(conn1):
            conn1.execute("INSERT INTO kv (k, v) VALUES ('lock', 1)")
            # Mientras conn1 tiene el write-lock (BEGIN IMMEDIATE), conn2 no puede adquirirlo.
            with pytest.raises(sqlite3.OperationalError):
                conn2.execute("BEGIN IMMEDIATE")
        # Tras el commit de conn1, conn2 ya puede operar.
        conn2.execute("BEGIN IMMEDIATE")
        conn2.execute("INSERT INTO kv (k, v) VALUES ('lock2', 2)")
        conn2.commit()
    finally:
        conn1.close()
        conn2.close()
    assert _value(path, "lock") == 1
    assert _value(path, "lock2") == 2


def test_funciona_con_db_aislada_de_la_app(isolated_db_path):
    """El helper opera sobre la DB aislada estándar de los fixtures."""
    conn = db.get_connection(isolated_db_path)
    try:
        db.init_schema(conn)
        with financial_transaction(conn):
            conn.execute(
                "INSERT INTO customer (id, name) VALUES ('t', 'Test')"
            )
        row = conn.execute("SELECT name FROM customer WHERE id = 't'").fetchone()
        assert row["name"] == "Test"
    finally:
        conn.close()
