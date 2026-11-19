"""Verificación de la fixture experimental de la Etapa 4 (Tarea 6; D-02, DK-01, D-05).

Comprueba que el arranque con `SHIFT_SEED_MODE=stage4` siembra exactamente las cuatro cuentas
D-02 con sus identificadores públicos, monedas y saldos; que cada cuenta tiene un evento
`ACCOUNT_OPENED` y una proyección coherente (version==1, balance==saldo inicial) sin doble
conteo; y que la siembra es idempotente. No lee ni modifica datos de la Etapa 3 (discontinuidad
experimental declarada, no conversión COP->USD).

_Requisitos: R2, R6, R8, R15_ · _Diseño: §7_ · _AC: AC4-03, AC4-08, AC4-14, AC4-19_
"""

import app.db as db
from app.seed import seed_stage4


_EXPECTED = {
    "CHK-1001": ("checking", "USD", 2_500_00),
    "SAV-2001": ("savings", "USD", 10_000_00),
    "EUR-3001": ("eur", "EUR", 0),
    "GBP-4001": ("gbp", "GBP", 0),
}


def test_cuentas_d02_sembradas(stage4_app_client, isolated_db_path):
    conn = db.get_connection(isolated_db_path)
    try:
        rows = conn.execute(
            "SELECT public_id, kind, currency, balance_cents, version FROM account"
        ).fetchall()
    finally:
        conn.close()
    got = {r["public_id"]: (r["kind"], r["currency"], r["balance_cents"]) for r in rows}
    assert got == _EXPECTED
    assert all(r["version"] == 1 for r in rows)


def test_eventos_account_opened_por_cuenta(stage4_app_client, isolated_db_path):
    conn = db.get_connection(isolated_db_path)
    try:
        events = conn.execute(
            "SELECT event_type, currency, amount_minor FROM domain_event WHERE event_type='ACCOUNT_OPENED'"
        ).fetchall()
    finally:
        conn.close()
    assert len(events) == 4
    totals = sorted(e["amount_minor"] for e in events)
    assert totals == [0, 0, 2_500_00, 10_000_00]


def test_proyeccion_coherente_sin_doble_conteo(stage4_app_client, isolated_db_path):
    conn = db.get_connection(isolated_db_path)
    try:
        rows = conn.execute(
            """SELECT a.public_id, a.balance_cents AS acc_bal, p.balance_minor AS proj_bal,
                      a.version AS acc_ver, p.version AS proj_ver
               FROM account a JOIN account_projection p ON p.account_id = a.id"""
        ).fetchall()
    finally:
        conn.close()
    assert len(rows) == 4
    for r in rows:
        # Proyección == saldo de cuenta == evento ACCOUNT_OPENED (sin doble conteo).
        assert r["proj_bal"] == r["acc_bal"]
        assert r["proj_ver"] == r["acc_ver"] == 1


def test_seed_stage4_idempotente(stage4_app_client, isolated_db_path):
    conn = db.get_connection(isolated_db_path)
    try:
        before = conn.execute("SELECT COUNT(*) AS n FROM account").fetchone()["n"]
        seed_stage4(conn)  # segunda ejecución
        after = conn.execute("SELECT COUNT(*) AS n FROM account").fetchone()["n"]
        events = conn.execute("SELECT COUNT(*) AS n FROM domain_event").fetchone()["n"]
    finally:
        conn.close()
    assert before == after == 4
    assert events == 4  # no se duplican eventos ACCOUNT_OPENED
