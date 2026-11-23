"""Verificación de proyecciones CQRS y reconstrucción determinista (Etapa 4, Tarea 9; D-06).

Proyección == suma de eventos; rebuild reproduce el mismo estado; verify_consistency detecta
inconsistencia (fail-closed).

_Requisitos: R8_ · _Diseño: §1.3, §7_ · _AC: AC4-10, AC4-14_
"""

import app.db as db
from app import command, events, projections
from app.seed import seed_stage4


def _stage4(path):
    conn = db.get_connection(path)
    try:
        db.init_schema(conn)
        db.migrate(conn)
        seed_stage4(conn)
    finally:
        conn.close()
    return path


def _account_id(conn, public_id):
    return conn.execute("SELECT id FROM account WHERE public_id = ?", (public_id,)).fetchone()["id"]


def test_proyeccion_inicial_coincide_con_eventos(tmp_path):
    path = _stage4(tmp_path / "p.db")
    conn = db.get_connection(path)
    try:
        assert projections.verify_consistency(conn) is True
    finally:
        conn.close()


def test_comando_actualiza_proyeccion_atomicamente(tmp_path):
    path = _stage4(tmp_path / "p.db")
    conn = db.get_connection(path)
    try:
        chk = _account_id(conn, "CHK-1001")
        sav = _account_id(conn, "SAV-2001")
        # Transferencia interna USD 100.00 CHK -> SAV (misma moneda).
        command.run_command(
            conn,
            effects=[
                command.AccountEffect(chk, events.EVENT_INTERNAL_TRANSFER_DEBITED, -100_00),
                command.AccountEffect(sav, events.EVENT_INTERNAL_TRANSFER_CREDITED, +100_00),
            ],
            occurred_at="2026-01-02T00:00:00Z",
        )
        # Proyección refleja el nuevo saldo y versión 2.
        rows = {r["public_id"]: (r["balance_minor"], r["version"]) for r in conn.execute(
            "SELECT public_id, balance_minor, version FROM account_projection").fetchall()}
        assert rows["CHK-1001"] == (2_400_00, 2)
        assert rows["SAV-2001"] == (10_100_00, 2)
        assert projections.verify_consistency(conn) is True
    finally:
        conn.close()


def test_rebuild_reproduce_estado(tmp_path):
    path = _stage4(tmp_path / "p.db")
    conn = db.get_connection(path)
    try:
        chk = _account_id(conn, "CHK-1001")
        sav = _account_id(conn, "SAV-2001")
        command.run_command(
            conn,
            effects=[
                command.AccountEffect(chk, events.EVENT_INTERNAL_TRANSFER_DEBITED, -250_00),
                command.AccountEffect(sav, events.EVENT_INTERNAL_TRANSFER_CREDITED, +250_00),
            ],
            occurred_at="2026-01-03T00:00:00Z",
        )
        before = {r["account_id"]: (r["balance_minor"], r["version"]) for r in conn.execute(
            "SELECT account_id, balance_minor, version FROM account_projection").fetchall()}
        # Reconstruir desde eventos dentro de una transacción.
        conn.execute("BEGIN")
        projections.rebuild_projections(conn)
        conn.commit()
        after = {r["account_id"]: (r["balance_minor"], r["version"]) for r in conn.execute(
            "SELECT account_id, balance_minor, version FROM account_projection").fetchall()}
        assert after == before
        assert projections.verify_consistency(conn) is True
    finally:
        conn.close()


def test_verify_consistency_detecta_inconsistencia(tmp_path):
    path = _stage4(tmp_path / "p.db")
    conn = db.get_connection(path)
    try:
        # Corromper la proyección directamente (sin pasar por eventos) -> inconsistencia.
        conn.execute("UPDATE account_projection SET balance_minor = balance_minor + 1")
        conn.commit()
        assert projections.verify_consistency(conn) is False
    finally:
        conn.close()
