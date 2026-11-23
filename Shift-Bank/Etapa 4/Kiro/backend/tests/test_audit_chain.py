"""Cadena de auditoría: append encadenado, canonicalización y ancla (Etapa 3, Tarea 10).

Verifica el núcleo de `app/audit.py` (design.md §2.2, §2.3, §2.9):

- Append de varias entradas dentro de una transacción → `verify_chain` devuelve ok.
- Serialización canónica estable/determinista: mismo input → mismos bytes; el orden de las
  claves (de primer nivel y del payload) NO afecta el resultado.
- El ancla de cola (`audit_anchor`) se actualiza y queda coherente con la última entrada.
- `load_key` fail-closed: `AuditConfigError` si la clave HMAC está ausente/vacía.
- Prueba básica de manipulación: alterar un `entry_hmac` hace fallar `verify_chain` en el seq
  correcto (los negativos exhaustivos —reorden/borrado/truncación— son la Tarea 11).

Cada prueba usa una DB temporal con el esquema migrado (Tarea 9); nunca la DB histórica ni
`SEED-3.md`.

_Requisitos: R5.4, R6.3, R6.4_ · _Diseño: §2.2, §2.3, §2.9_ · _AC: AC-05_
"""

import pytest

import app.audit as audit
import app.db as db
from app.seed import seed
from app.txn import financial_transaction


def _migrated_conn(path):
    """Crea una DB temporal con esquema heredado + migración (incluye audit_log/anchor)."""
    conn = db.get_connection(path)
    db.init_schema(conn)
    seed(conn)
    db.migrate(conn)
    return conn


def _append(conn, *, event_type, outcome="success", entity_ref="ref", occurred_at="2026-11-16T00:00:00Z", payload=None):
    """Append dentro de una transacción financiera (como harían los servicios reales)."""
    with financial_transaction(conn):
        return audit.append_in_tx(
            conn,
            event_type=event_type,
            outcome=outcome,
            entity_ref=entity_ref,
            occurred_at=occurred_at,
            payload=payload,
        )


# --- Cadena válida: append + verify ------------------------------------------

def test_append_varias_entradas_verify_ok(tmp_path):
    """Varias entradas encadenadas dentro de transacciones → verify_chain ok."""
    conn = _migrated_conn(tmp_path / "m.db")
    try:
        s1 = _append(conn, event_type="INTERNAL_TRANSFER_COMPLETED", payload={"amount_cents": 100})
        s2 = _append(conn, event_type="ACH_SETTLED", payload={"reference": "ACH-1"})
        s3 = _append(conn, event_type="MFA_FAILED", outcome="rejected", payload={"reason": "bad_pin"})

        assert (s1, s2, s3) == (1, 2, 3)

        result = audit.verify_chain(conn)
        assert result.ok is True
        assert result.failed_seq is None
        assert result.reason is None
    finally:
        conn.close()


def test_cadena_vacia_verify_ok(tmp_path):
    """Una bitácora vacía (sin entradas ni ancla) es un estado inicial coherente."""
    conn = _migrated_conn(tmp_path / "m.db")
    try:
        result = audit.verify_chain(conn)
        assert result.ok is True
    finally:
        conn.close()


def test_genesis_prev_hmac_vacio(tmp_path):
    """La primera entrada (génesis) tiene prev_hmac == '' y encadena las siguientes."""
    conn = _migrated_conn(tmp_path / "m.db")
    try:
        _append(conn, event_type="BENEFICIARY_CREATED")
        _append(conn, event_type="LIMIT_UPDATED")

        rows = conn.execute(
            "SELECT seq, prev_hmac, entry_hmac FROM audit_log ORDER BY seq ASC"
        ).fetchall()
        assert rows[0]["prev_hmac"] == ""
        # El prev_hmac de la 2ª entrada es el entry_hmac de la 1ª (encadenado).
        assert rows[1]["prev_hmac"] == rows[0]["entry_hmac"]
        assert audit.verify_chain(conn).ok is True
    finally:
        conn.close()


# --- Canonicalización estable / determinista (R6.3, §2.2) ---------------------

def test_canonical_determinista_mismo_input(tmp_path):
    """Mismo evento lógico → mismos bytes canónicos (determinismo)."""
    entry = {
        "event_type": "ACH_SETTLED",
        "outcome": "success",
        "entity_ref": "ACH-9",
        "occurred_at": "2026-11-16T12:00:00Z",
        "payload": {"amount_cents": 5000, "kind": "ach"},
    }
    assert audit._canonical(entry) == audit._canonical(dict(entry))


def test_canonical_independiente_del_orden_de_claves():
    """El orden de las claves (de primer nivel y del payload) NO afecta el material canónico."""
    entry_a = {
        "event_type": "ACH_SETTLED",
        "outcome": "success",
        "entity_ref": "ACH-9",
        "occurred_at": "2026-11-16T12:00:00Z",
        "payload": {"amount_cents": 5000, "kind": "ach", "nested": {"a": 1, "b": 2}},
    }
    # Mismo contenido, claves reordenadas en ambos niveles.
    entry_b = {
        "payload": {"nested": {"b": 2, "a": 1}, "kind": "ach", "amount_cents": 5000},
        "occurred_at": "2026-11-16T12:00:00Z",
        "entity_ref": "ACH-9",
        "outcome": "success",
        "event_type": "ACH_SETTLED",
    }
    assert audit._canonical(entry_a) == audit._canonical(entry_b)


def test_canonical_sin_espacios_y_claves_ordenadas():
    """La serialización usa separadores compactos y ordena las claves alfabéticamente."""
    entry = {
        "event_type": "X",
        "outcome": "success",
        "entity_ref": "r",
        "occurred_at": "t",
        "payload": {"b": 1, "a": 2},
    }
    text = audit._canonical(entry).decode("utf-8")
    assert " " not in text  # separadores (",", ":") → sin espacios
    # Claves de primer nivel ordenadas: entity_ref < event_type < occurred_at < outcome < payload
    assert text.startswith('{"entity_ref":"r","event_type":"X"')
    # payload con claves ordenadas a<b
    assert '"payload":{"a":2,"b":1}' in text


def test_entry_hmac_estable_para_mismo_prev_y_entrada():
    """El HMAC recomputado es idéntico para el mismo prev_hmac y la misma entrada."""
    key = b"clave-de-prueba-determinista"
    entry = {
        "event_type": "E",
        "outcome": "success",
        "entity_ref": "r",
        "occurred_at": "t",
        "payload": {"x": 1},
    }
    h1 = audit._compute_entry_hmac(key, "", entry)
    h2 = audit._compute_entry_hmac(key, "", entry)
    assert h1 == h2
    # Un prev_hmac distinto cambia el resultado (encadenado efectivo).
    assert audit._compute_entry_hmac(key, "abc", entry) != h1


def test_payload_persistido_es_canonico(tmp_path):
    """El payload se persiste como JSON canónico (claves ordenadas, sin espacios)."""
    conn = _migrated_conn(tmp_path / "m.db")
    try:
        _append(conn, event_type="E", payload={"b": 1, "a": 2})
        stored = conn.execute("SELECT payload FROM audit_log WHERE seq = 1").fetchone()["payload"]
        assert stored == '{"a":2,"b":1}'
    finally:
        conn.close()


# --- Ancla de cola coherente (§2.9) ------------------------------------------

def test_ancla_actualizada_tras_appends(tmp_path):
    """El ancla (audit_anchor id=1) refleja el last_seq/last_hmac de la última entrada."""
    conn = _migrated_conn(tmp_path / "m.db")
    try:
        _append(conn, event_type="A")
        _append(conn, event_type="B")
        last = _append(conn, event_type="C")

        anchor = conn.execute(
            "SELECT last_seq, last_hmac FROM audit_anchor WHERE id = 1"
        ).fetchone()
        tail = conn.execute(
            "SELECT seq, entry_hmac FROM audit_log ORDER BY seq DESC LIMIT 1"
        ).fetchone()

        assert anchor["last_seq"] == last == tail["seq"]
        assert anchor["last_hmac"] == tail["entry_hmac"]
    finally:
        conn.close()


def test_ancla_fila_unica_tras_multiples_appends(tmp_path):
    """El UPSERT mantiene una sola fila de ancla (id=1) aunque haya muchos appends."""
    conn = _migrated_conn(tmp_path / "m.db")
    try:
        for i in range(5):
            _append(conn, event_type=f"E{i}")
        n = conn.execute("SELECT COUNT(*) AS n FROM audit_anchor").fetchone()["n"]
        assert n == 1
        assert audit.verify_chain(conn).ok is True
    finally:
        conn.close()


# --- Fail-closed de la clave (R6.3) ------------------------------------------

def test_load_key_fail_closed_sin_clave(monkeypatch):
    """Sin SHIFT_AUDIT_HMAC_KEY, load_key lanza AuditConfigError (fail-closed)."""
    monkeypatch.delenv("SHIFT_AUDIT_HMAC_KEY", raising=False)
    with pytest.raises(audit.AuditConfigError):
        audit.load_key()


def test_load_key_fail_closed_clave_vacia(monkeypatch):
    """Una clave vacía/espacios también falla fail-closed."""
    monkeypatch.setenv("SHIFT_AUDIT_HMAC_KEY", "   ")
    with pytest.raises(audit.AuditConfigError):
        audit.load_key()


def test_load_key_no_filtra_material(monkeypatch):
    """El mensaje de error nunca incluye material de clave (R2.6)."""
    secret = "clave-super-secreta-no-debe-aparecer"
    monkeypatch.setenv("SHIFT_AUDIT_HMAC_KEY", secret)
    # Con clave válida no lanza; pero al borrarla el mensaje no debe contener el valor previo.
    monkeypatch.delenv("SHIFT_AUDIT_HMAC_KEY", raising=False)
    with pytest.raises(audit.AuditConfigError) as exc:
        audit.load_key()
    assert secret not in str(exc.value)


# --- Detección básica de manipulación (prueba de humo; exhaustivo en Tarea 11) ---

def test_verify_detecta_entry_hmac_alterado(tmp_path):
    """Alterar un entry_hmac (vía bypass de triggers) hace fallar verify_chain en ese seq."""
    conn = _migrated_conn(tmp_path / "m.db")
    try:
        _append(conn, event_type="A")
        _append(conn, event_type="B", payload={"k": "v"})
        _append(conn, event_type="C")
        assert audit.verify_chain(conn).ok is True

        # Deshabilitar temporalmente los triggers append-only para simular manipulación
        # directa de la DB (fuera de la ruta de aplicación), como haría un atacante con acceso.
        conn.execute("DROP TRIGGER audit_log_no_update")
        conn.execute(
            "UPDATE audit_log SET entry_hmac = 'deadbeef' WHERE seq = 2"
        )
        conn.commit()

        result = audit.verify_chain(conn)
        assert result.ok is False
        assert result.failed_seq == 2
        assert result.reason is not None
    finally:
        conn.close()
