"""Detección de manipulación y endurecimiento de la bitácora (Etapa 3, Tarea 11).

Pruebas NEGATIVAS/de endurecimiento de `app/audit.verify_chain` y de los triggers append-only
(`audit_log_no_update`/`audit_log_no_delete`). Cubren el modelo de amenazas de design.md §2.5,
§2.9 y §10, y los requisitos R6.4, R6.5, R6.6.

Enfoque: para simular a un atacante con acceso DIRECTO a la base de datos (fuera de la ruta de
la aplicación), cada prueba de manipulación primero hace `DROP TRIGGER` del trigger relevante,
luego muta la fila/ancla con SQL crudo, y después invoca `verify_chain` para comprobar que la
detección ocurre en el `seq` correcto. Las pruebas de ENDURECIMIENTO (caso 4) NO sueltan los
triggers: comprueban que un UPDATE/DELETE ordinario es abortado por SQLite.

Esta tarea escribe SOLO pruebas: no modifica el comportamiento de `app/audit.py`. Cada prueba
usa una DB temporal con el esquema migrado (Tarea 9); nunca la DB histórica ni `SEED-3.md`.

_Requisitos: R6.4, R6.5, R6.6_ · _Diseño: §2.5, §2.9, §10_ · _AC: AC-06_

**Validates: Requirements 6.4, 6.5, 6.6**
"""

import sqlite3

import pytest

import app.audit as audit
import app.db as db
from app.seed import seed
from app.txn import financial_transaction


def _migrated_conn(path):
    """Crea una DB temporal con esquema heredado + migración (incluye audit_log/anchor/triggers)."""
    conn = db.get_connection(path)
    db.init_schema(conn)
    seed(conn)
    db.migrate(conn)
    return conn


def _append(conn, *, event_type, outcome="success", entity_ref="ref",
            occurred_at="2026-11-16T00:00:00Z", payload=None):
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


def _seed_chain(conn, n=5):
    """Crea una cadena válida de `n` entradas y confirma que verify_chain la acepta."""
    seqs = []
    for i in range(n):
        seqs.append(
            _append(
                conn,
                event_type=f"EVENT_{i}",
                outcome="success" if i % 2 == 0 else "rejected",
                entity_ref=f"ref-{i}",
                payload={"idx": i, "amount_cents": 100 * (i + 1)},
            )
        )
    assert seqs == list(range(1, n + 1))
    assert audit.verify_chain(conn).ok is True
    return seqs


# ---------------------------------------------------------------------------
# Caso 1 — Manipulación de contenido (payload, entry_hmac, outcome, entity_ref)
# ---------------------------------------------------------------------------
# design.md §2.5 (a): recomputar entry_hmac detecta manipulación de contenido.
# R6.4 (recomputa HMAC y detecta manipulación de contenido), R6.5 (identifica el punto de ruptura).

@pytest.mark.parametrize(
    "column, new_value",
    [
        ("payload", '{"idx":999,"amount_cents":1}'),  # payload mutado (recanonicaliza distinto)
        ("entry_hmac", "deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"),
        ("outcome", "success"),       # era "rejected" en seq=2 (idx impar) → cambia material
        ("entity_ref", "attacker-ref"),
    ],
)
def test_content_tamper_detected_at_correct_seq(tmp_path, column, new_value):
    """Mutar un campo cubierto por el HMAC en una fila intermedia → verify falla en ese seq."""
    conn = _migrated_conn(tmp_path / "m.db")
    try:
        _seed_chain(conn, n=5)
        target_seq = 2  # fila intermedia

        # Simular atacante con acceso directo: soltar el trigger de UPDATE y mutar la fila.
        conn.execute("DROP TRIGGER audit_log_no_update")
        conn.execute(
            f"UPDATE audit_log SET {column} = ? WHERE seq = ?",
            (new_value, target_seq),
        )
        conn.commit()

        result = audit.verify_chain(conn)
        assert result.ok is False, f"verify_chain NO detectó manipulación de {column}"
        assert result.failed_seq == target_seq, (
            f"manipulación de {column}: se esperaba fallo en seq={target_seq}, "
            f"se obtuvo seq={result.failed_seq}"
        )
        assert result.reason is not None
    finally:
        conn.close()


def test_content_tamper_payload_reason_mentions_hmac(tmp_path):
    """La razón del fallo por contenido alude al HMAC recomputado (no a un hueco de seq)."""
    conn = _migrated_conn(tmp_path / "m.db")
    try:
        _seed_chain(conn, n=4)
        conn.execute("DROP TRIGGER audit_log_no_update")
        conn.execute("UPDATE audit_log SET payload = '{\"x\":1}' WHERE seq = 2")
        conn.commit()

        result = audit.verify_chain(conn)
        assert result.ok is False
        assert result.failed_seq == 2
        assert "entry_hmac" in result.reason
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Caso 2 — Reordenamiento / cadena rota (prev_hmac reescrito)
# ---------------------------------------------------------------------------
# design.md §2.5 (b): prev_hmac de cada fila == entry_hmac de la anterior.
# R6.4 (detecta cadenas rotas/reordenadas), R6.5 (punto de ruptura).

def test_broken_chain_prev_hmac_rewritten_detected(tmp_path):
    """Reescribir el prev_hmac de una fila intermedia → verify falla en ese seq (cadena rota)."""
    conn = _migrated_conn(tmp_path / "m.db")
    try:
        _seed_chain(conn, n=5)
        target_seq = 3

        conn.execute("DROP TRIGGER audit_log_no_update")
        conn.execute(
            "UPDATE audit_log SET prev_hmac = ? WHERE seq = ?",
            ("00" * 32, target_seq),
        )
        conn.commit()

        result = audit.verify_chain(conn)
        assert result.ok is False
        assert result.failed_seq == target_seq
        assert "prev_hmac" in result.reason
    finally:
        conn.close()


def test_reorder_swap_prev_hmac_detected(tmp_path):
    """Intercambiar el prev_hmac de dos filas contiguas rompe el encadenado y se detecta."""
    conn = _migrated_conn(tmp_path / "m.db")
    try:
        _seed_chain(conn, n=4)
        rows = conn.execute(
            "SELECT seq, prev_hmac FROM audit_log ORDER BY seq ASC"
        ).fetchall()
        prev_by_seq = {r["seq"]: r["prev_hmac"] for r in rows}

        conn.execute("DROP TRIGGER audit_log_no_update")
        # Intercambiar prev_hmac de seq=2 y seq=3 (ambos quedan descolgados del encadenado real).
        conn.execute("UPDATE audit_log SET prev_hmac = ? WHERE seq = 2", (prev_by_seq[3],))
        conn.execute("UPDATE audit_log SET prev_hmac = ? WHERE seq = 3", (prev_by_seq[2],))
        conn.commit()

        result = audit.verify_chain(conn)
        assert result.ok is False
        # El primer fallo se da en la primera fila cuyo prev_hmac ya no encadena (seq=2).
        assert result.failed_seq == 2
        assert result.reason is not None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Caso 3 — Eliminación intermedia (hueco de seq / contigüidad)
# ---------------------------------------------------------------------------
# design.md §2.5 (c): seq contiguo y creciente detecta eliminación intermedia.
# R6.4 (registros intermedios faltantes), R6.5 (punto de ruptura).

def test_intermediate_deletion_creates_gap_detected(tmp_path):
    """Borrar una fila intermedia deja un hueco de seq → verify falla por contigüidad."""
    conn = _migrated_conn(tmp_path / "m.db")
    try:
        _seed_chain(conn, n=5)
        deleted_seq = 3

        # Simular atacante: soltar el trigger de DELETE y borrar una entrada intermedia.
        conn.execute("DROP TRIGGER audit_log_no_delete")
        conn.execute("DELETE FROM audit_log WHERE seq = ?", (deleted_seq,))
        conn.commit()

        result = audit.verify_chain(conn)
        assert result.ok is False
        # Al recorrer asc, tras seq=2 se espera seq=3 pero aparece seq=4 → fallo señalado en 4.
        assert result.failed_seq == 4
        assert "secuencia no contigua" in result.reason
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Caso 4 — Endurecimiento append-only (SIN soltar triggers)
# ---------------------------------------------------------------------------
# design.md §10 / DT-6: triggers frenan UPDATE/DELETE ordinarios (R6 endurecimiento).

def test_ordinary_update_blocked_by_trigger(tmp_path):
    """Un UPDATE ordinario sobre audit_log es abortado por el trigger append-only."""
    conn = _migrated_conn(tmp_path / "m.db")
    try:
        _seed_chain(conn, n=3)
        with pytest.raises(sqlite3.Error) as exc:
            conn.execute("UPDATE audit_log SET outcome = 'success' WHERE seq = 1")
        assert "append-only" in str(exc.value)
        conn.rollback()
        # La cadena sigue íntegra: el UPDATE no tuvo efecto.
        assert audit.verify_chain(conn).ok is True
    finally:
        conn.close()


def test_ordinary_delete_blocked_by_trigger(tmp_path):
    """Un DELETE ordinario sobre audit_log es abortado por el trigger append-only."""
    conn = _migrated_conn(tmp_path / "m.db")
    try:
        _seed_chain(conn, n=3)
        with pytest.raises(sqlite3.Error) as exc:
            conn.execute("DELETE FROM audit_log WHERE seq = 1")
        assert "append-only" in str(exc.value)
        conn.rollback()
        assert audit.verify_chain(conn).ok is True
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Caso 5 — Truncación de cola detectada por el ancla
# ---------------------------------------------------------------------------
# design.md §2.9: el ancla externa referencia el último seq/hmac; si se borran las últimas
# entradas conservando una cadena consistente, el ancla queda por delante y se detecta.
# R6.6 (truncación del final detectable con ancla externa).

def test_tail_truncation_detected_by_anchor(tmp_path):
    """Borrar la última entrada (cadena restante consistente) pero sin tocar el ancla → detectado."""
    conn = _migrated_conn(tmp_path / "m.db")
    try:
        _seed_chain(conn, n=5)
        anchor_before = conn.execute(
            "SELECT last_seq, last_hmac FROM audit_anchor WHERE id = 1"
        ).fetchone()
        assert anchor_before["last_seq"] == 5

        # Atacante borra la cola (seq=5) pero NO actualiza el ancla. La cadena 1..4 es internamente
        # consistente (cada prev_hmac encadena), de ahí que solo el ancla delate la truncación.
        conn.execute("DROP TRIGGER audit_log_no_delete")
        conn.execute("DELETE FROM audit_log WHERE seq = 5")
        conn.commit()

        result = audit.verify_chain(conn)
        assert result.ok is False, "verify_chain NO detectó la truncación de cola vía ancla"
        assert result.failed_seq == 5  # el ancla referencia el seq truncado
        assert "truncación del final" in result.reason
    finally:
        conn.close()


def test_tail_truncation_multiple_rows_detected_by_anchor(tmp_path):
    """Truncar varias entradas de cola también se detecta mientras el ancla no se reescriba."""
    conn = _migrated_conn(tmp_path / "m.db")
    try:
        _seed_chain(conn, n=6)
        conn.execute("DROP TRIGGER audit_log_no_delete")
        conn.execute("DELETE FROM audit_log WHERE seq IN (5, 6)")
        conn.commit()

        result = audit.verify_chain(conn)
        assert result.ok is False
        assert result.failed_seq == 6  # el ancla sigue apuntando al último seq original
        assert "truncación del final" in result.reason
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Caso 6 — Límite del modelo de amenazas (documentado): truncación + ancla reescrita
# ---------------------------------------------------------------------------
# design.md §2.9 / §10 y R6.6: si el atacante controla TAMBIÉN el ancla (y la clave HMAC),
# puede truncar la cola y reescribir el ancla para que referencie la nueva cola. En ese caso la
# verificación por recomputación + ancla ya NO puede detectar la truncación. Esta prueba asienta
# ese LÍMITE conocido como comportamiento esperado (verify ok), haciendo explícita la frontera en
# vez de reclamar una protección inexistente. NO es un fallo: es la honestidad del modelo.

def test_full_control_truncation_with_anchor_rewrite_is_undetectable_documented_limit(tmp_path):
    """LÍMITE DOCUMENTADO: truncar la cola Y reescribir el ancla a la nueva cola → verify ok.

    Demuestra que, con control total de la DB (incluida la tabla de ancla) y de la clave HMAC, la
    truncación del final vuelve a ser indetectable. Es el límite reconocido en §2.9/§10 y R6.6; no
    se reclama inmutabilidad absoluta frente a un administrador con control total.
    """
    conn = _migrated_conn(tmp_path / "m.db")
    try:
        _seed_chain(conn, n=5)

        # Atacante con control total: borra la cola (seq=5) y reescribe el ancla para que apunte
        # al nuevo último presente (seq=4), dejando un estado globalmente consistente.
        conn.execute("DROP TRIGGER audit_log_no_delete")
        conn.execute("DELETE FROM audit_log WHERE seq = 5")

        new_tail = conn.execute(
            "SELECT seq, entry_hmac FROM audit_log ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        assert new_tail["seq"] == 4
        conn.execute(
            "UPDATE audit_anchor SET last_seq = ?, last_hmac = ? WHERE id = 1",
            (new_tail["seq"], new_tail["entry_hmac"]),
        )
        conn.commit()

        result = audit.verify_chain(conn)
        # Comportamiento ESPERADO y correcto dentro del modelo: la truncación ya no es detectable.
        assert result.ok is True, (
            "El límite documentado cambió: con ancla reescrita la truncación debería ser "
            "indetectable (verify ok). Revisar §2.9/§10 y R6.6."
        )
        assert result.failed_seq is None
        assert result.reason is None
    finally:
        conn.close()
