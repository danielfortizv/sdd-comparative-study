"""Migración de cifrado idempotente y transaccional (Etapa 3, Tarea 8).

Verifica `db.migrate_encryption(conn)` según design.md §1.6 / §8 G3 y R3.1–R3.4.

A diferencia de `test_encryption_at_rest.py` (que ejercita el camino normal de escritura
ya cifrado de la Tarea 7), aquí sembramos **texto en claro** directamente con `sqlite3` crudo
(evitando los bordes de cifrado del repositorio) para simular registros heredados/pre-existentes
y comprobar que la migración:

1. Cifra en su lugar todas las columnas sensibles objetivo → tokens `enc:v1:...` y `crypto.decrypt`
   recupera el claro original (R3.4).
2. Es **idempotente** (R3.1): una 2ª corrida no recifra ni corrompe (mismo token, mismo claro).
3. Es **transaccional con ROLLBACK total** (R3.2): si un valor falla a mitad de camino, se revierte
   por completo — ninguna fila queda cifrada (sin mezcla cifrado/claro).
4. **Preserva** datos no sensibles y contratos (R3.3): nombre/banco/montos y filas no objetivo
   quedan intactos; `is_encrypted` pasa de falso→verdadero solo en las columnas objetivo.

Usa `isolated_db_path` (DB temporal aislada; nunca toca datos históricos ni `SEED-3.md`). El
material de clave SOLO-PRUEBAS lo provee `conftest.py`.
"""

import json
import sqlite3

import pytest

import app.crypto as crypto
import app.db as db


# Identificadores sensibles en claro usados en la siembra.
_ACCOUNT = "9876543210"
_ROUTING = "123456789"
_SNAPSHOT = json.dumps(
    {"name": "ACME SA", "bank": "Banco X",
     "routing_number": _ROUTING, "account_number": _ACCOUNT},
    sort_keys=True,
)
_ENC_PREFIX = "enc:v1:"


def _seed_schema(path):
    """Crea el esquema (init + migrate) en una DB vacía, SIN cifrar nada todavía."""
    conn = db.get_connection(path)
    try:
        db.init_schema(conn)
        db.migrate(conn)
    finally:
        conn.close()


def _raw_conn(path):
    """Conexión sqlite3 cruda (sin pasar por los bordes de cifrado del repositorio)."""
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def _insert_cleartext(path):
    """Inserta registros CON TEXTO EN CLARO en las columnas sensibles (bypass del repositorio).

    Simula datos heredados existentes antes de activar el cifrado en reposo.
    """
    conn = _raw_conn(path)
    try:
        conn.execute(
            "INSERT INTO customer (id, name) VALUES ('c1', 'Cliente Uno')"
        )
        # beneficiary: account_number y routing_number en claro.
        conn.execute(
            "INSERT INTO beneficiary "
            "(id, customer_id, name, bank, routing_number, account_number, created_at) "
            "VALUES ('b1', 'c1', 'ACME SA', 'Banco X', ?, ?, '2024-01-01T00:00:00Z')",
            (_ROUTING, _ACCOUNT),
        )
        # transfer ACH con beneficiary_snapshot en claro.
        conn.execute(
            "INSERT INTO transfer "
            "(id, reference, from_kind, to_kind, amount_cents, description, status, "
            " requires_mfa, created_at, type, beneficiary_snapshot) "
            "VALUES ('t1', 'ref-1', 'savings', 'external', 250000, 'proveedor', 'pending', "
            " 0, '2024-01-01T00:00:00Z', 'ach', ?)",
            (_SNAPSHOT,),
        )
        # transfer interna SIN snapshot: NO debe ser tocada por la migración.
        conn.execute(
            "INSERT INTO transfer "
            "(id, reference, from_kind, to_kind, amount_cents, description, status, "
            " requires_mfa, created_at, type, beneficiary_snapshot) "
            "VALUES ('t2', 'ref-2', 'checking', 'savings', 5000, 'ahorro', 'completed', "
            " 0, '2024-01-02T00:00:00Z', 'internal', NULL)"
        )
        # recurring_schedule con beneficiary_snapshot en claro.
        conn.execute(
            "INSERT INTO recurring_schedule "
            "(id, customer_id, type, from_kind, to_kind, beneficiary_snapshot, amount_cents, "
            " description, frequency, status, next_run_at, created_at) "
            "VALUES ('s1', 'c1', 'ach', 'checking', NULL, ?, 50000, 'rec', 'monthly', "
            " 'active', '2024-02-01T00:00:00Z', '2024-01-01T00:00:00Z')",
            (_SNAPSHOT,),
        )
        conn.commit()
    finally:
        conn.close()


def _read(path, query):
    conn = _raw_conn(path)
    try:
        return conn.execute(query).fetchall()
    finally:
        conn.close()


def _sensitive_values(path):
    """Devuelve la lista de (etiqueta, valor crudo) de las 4 columnas sensibles objetivo."""
    out = []
    ben = _read(path, "SELECT routing_number, account_number FROM beneficiary")[0]
    out.append(("ben.routing", ben["routing_number"]))
    out.append(("ben.account", ben["account_number"]))
    ach = _read(path, "SELECT beneficiary_snapshot FROM transfer WHERE type='ach'")[0]
    out.append(("ach.snapshot", ach["beneficiary_snapshot"]))
    sch = _read(path, "SELECT beneficiary_snapshot FROM recurring_schedule")[0]
    out.append(("sch.snapshot", sch["beneficiary_snapshot"]))
    return out


# --- 1. Cifrado en su lugar + decrypt recupera el claro (R3.4) ----------------

def test_migracion_cifra_claro_y_decrypt_recupera_original(isolated_db_path):
    _seed_schema(isolated_db_path)
    _insert_cleartext(isolated_db_path)

    # Precondición: todo está en CLARO (is_encrypted == False).
    for _label, value in _sensitive_values(isolated_db_path):
        assert not crypto.is_encrypted(value)

    conn = db.get_connection(isolated_db_path)
    try:
        db.migrate_encryption(conn)
    finally:
        conn.close()

    # Postcondición: todas las columnas objetivo son tokens enc: y decrypt recupera el claro.
    expected = {
        "ben.routing": _ROUTING,
        "ben.account": _ACCOUNT,
        "ach.snapshot": _SNAPSHOT,
        "sch.snapshot": _SNAPSHOT,
    }
    for label, value in _sensitive_values(isolated_db_path):
        assert value.startswith(_ENC_PREFIX), f"{label} no quedó cifrado: {value!r}"
        assert crypto.decrypt(value) == expected[label]
        # Ningún identificador sensible en claro embebido en el token (R3.4).
        assert _ACCOUNT not in value and _ROUTING not in value


# --- 2. Idempotencia: la 2ª corrida no recifra (R3.1) -------------------------

def test_migracion_idempotente_segunda_corrida_no_recifra(isolated_db_path):
    _seed_schema(isolated_db_path)
    _insert_cleartext(isolated_db_path)

    conn = db.get_connection(isolated_db_path)
    try:
        db.migrate_encryption(conn)
    finally:
        conn.close()

    first = {label: value for label, value in _sensitive_values(isolated_db_path)}

    # 2ª corrida: no debe cambiar ningún token (ya cifrados → omitidos vía is_encrypted).
    conn = db.get_connection(isolated_db_path)
    try:
        db.migrate_encryption(conn)
    finally:
        conn.close()

    second = {label: value for label, value in _sensitive_values(isolated_db_path)}
    assert second == first, "la 2ª corrida alteró tokens ya cifrados (no idempotente)"

    # decrypt sigue recuperando el claro original (no doble-cifrado).
    assert crypto.decrypt(second["ben.account"]) == _ACCOUNT
    assert crypto.decrypt(second["ben.routing"]) == _ROUTING
    assert crypto.decrypt(second["ach.snapshot"]) == _SNAPSHOT
    assert crypto.decrypt(second["sch.snapshot"]) == _SNAPSHOT


# --- 3. Rollback total ante fallo a mitad de camino (R3.2) --------------------

def test_migracion_rollback_total_ante_fallo(isolated_db_path, monkeypatch):
    _seed_schema(isolated_db_path)
    _insert_cleartext(isolated_db_path)

    before = {label: value for label, value in _sensitive_values(isolated_db_path)}
    # Precondición: todo en claro.
    for value in before.values():
        assert not crypto.is_encrypted(value)

    # Inyectar un fallo en la 2ª invocación de encrypt (a mitad de la migración).
    real_encrypt = crypto.encrypt
    state = {"calls": 0}

    def flaky_encrypt(plaintext):
        state["calls"] += 1
        if state["calls"] == 2:
            raise RuntimeError("fallo inyectado a mitad de migración")
        return real_encrypt(plaintext)

    monkeypatch.setattr(db.crypto, "encrypt", flaky_encrypt)

    conn = db.get_connection(isolated_db_path)
    try:
        with pytest.raises(RuntimeError, match="fallo inyectado"):
            db.migrate_encryption(conn)
    finally:
        conn.close()

    # Se intentó cifrar al menos 2 valores (el 2º falló) → sin rollback habría mezcla.
    assert state["calls"] >= 2

    # ROLLBACK total: NINGUNA columna quedó cifrada; todo sigue en claro e idéntico.
    after = {label: value for label, value in _sensitive_values(isolated_db_path)}
    assert after == before, "rollback incompleto: estado alterado tras el fallo"
    for label, value in after.items():
        assert not crypto.is_encrypted(value), f"{label} quedó cifrado pese al rollback"


# --- 4. Preservación de columnas no sensibles y filas no objetivo (R3.3) ------

def test_migracion_preserva_no_sensibles_y_filas_no_objetivo(isolated_db_path):
    _seed_schema(isolated_db_path)
    _insert_cleartext(isolated_db_path)

    conn = db.get_connection(isolated_db_path)
    try:
        db.migrate_encryption(conn)
    finally:
        conn.close()

    # Columnas NO sensibles del beneficiario intactas (nombre, banco).
    ben = _read(isolated_db_path, "SELECT name, bank FROM beneficiary")[0]
    assert ben["name"] == "ACME SA"
    assert ben["bank"] == "Banco X"

    # La transferencia interna (sin snapshot) NO fue tocada: snapshot sigue NULL, montos iguales.
    internal = _read(
        isolated_db_path,
        "SELECT amount_cents, beneficiary_snapshot, description FROM transfer WHERE id='t2'",
    )[0]
    assert internal["beneficiary_snapshot"] is None
    assert internal["amount_cents"] == 5000
    assert internal["description"] == "ahorro"

    # Montos de la fila ACH y del schedule preservados (solo cambió el snapshot).
    ach_amount = _read(
        isolated_db_path, "SELECT amount_cents FROM transfer WHERE id='t1'"
    )[0]["amount_cents"]
    assert ach_amount == 250000
    sch_amount = _read(
        isolated_db_path, "SELECT amount_cents FROM recurring_schedule WHERE id='s1'"
    )[0]["amount_cents"]
    assert sch_amount == 50000


# --- 5. No-op sobre una DB ya cifrada / vacía (idempotencia de arranque) ------

def test_migracion_noop_en_db_sin_registros(isolated_db_path):
    """Sobre una DB recién migrada (sin registros sensibles) la migración es un no-op seguro."""
    _seed_schema(isolated_db_path)

    conn = db.get_connection(isolated_db_path)
    try:
        # No debe lanzar ni alterar nada.
        db.migrate_encryption(conn)
        db.migrate_encryption(conn)
    finally:
        conn.close()

    assert _read(isolated_db_path, "SELECT COUNT(*) AS n FROM beneficiary")[0]["n"] == 0
