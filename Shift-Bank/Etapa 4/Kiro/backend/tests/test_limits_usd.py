"""Verificación de límites y MFA en equivalente USD (Etapa 4, Tarea 14; D-07).

Límite por operación USD 5,000.00 y diario USD 10,000.00 (día UTC) en equivalente USD, con
consumo derivado de los eventos de dominio de débito. Umbral de MFA: equivalente USD SIN redondear
estrictamente > USD 1,000.00. Cubre las tres monedas (USD/EUR/GBP).

_Requisitos: R11_ · _Diseño: §2, §3.5_ · _AC: AC4-17_
"""

import app.db as db
from app import command, events, fx, limit_service
from app.clock import ManualClock
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


def _aid(conn, public_id):
    return conn.execute("SELECT id FROM account WHERE public_id = ?", (public_id,)).fetchone()["id"]


def test_check_usd_por_operacion():
    import pytest
    # 5000.00 USD exacto pasa (igualdad permitida); 5000.01 falla.
    class _NoConn:
        def execute(self, *a, **k):
            class _C:
                def fetchall(self_inner):
                    return []
            return _C()
    clk = ManualClock()
    limit_service.check_usd(_NoConn(), 5000_00, clk.now_utc())
    with pytest.raises(limit_service.LimitError) as exc:
        limit_service.check_usd(_NoConn(), 5000_01, clk.now_utc())
    assert exc.value.code == "LIMIT_EXCEEDED_PER_TRANSFER"


def test_consumo_diario_en_usd_equivalente(tmp_path):
    path = _stage4(tmp_path / "l.db")
    conn = db.get_connection(path)
    try:
        chk, sav = _aid(conn, "CHK-1001"), _aid(conn, "SAV-2001")
        clk = ManualClock()
        occurred = clk.now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")
        # Débito de 1000 USD (interno CHK->SAV).
        command.run_command(
            conn,
            effects=[
                command.AccountEffect(chk, events.EVENT_INTERNAL_TRANSFER_DEBITED, -1000_00),
                command.AccountEffect(sav, events.EVENT_INTERNAL_TRANSFER_CREDITED, +1000_00),
            ],
            occurred_at=occurred,
        )
        consumed = limit_service.daily_consumption_usd_minor(conn, clk.now_utc())
        assert consumed == 1000_00  # un débito de 1000 USD cuenta 1000 USD
    finally:
        conn.close()


def test_consumo_eur_convertido_a_usd(tmp_path):
    path = _stage4(tmp_path / "l.db")
    conn = db.get_connection(path)
    try:
        eur = _aid(conn, "EUR-3001")
        # Inyectar fondos EUR y un débito de 90.00 EUR (== 100.00 USD).
        conn.execute("UPDATE account SET balance_cents = 100000 WHERE public_id='EUR-3001'")
        conn.commit()
        clk = ManualClock()
        occurred = clk.now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")
        # Evento de débito EUR directo (sin crédito, para aislar el consumo).
        conn.execute("BEGIN")
        events.append_event_no_commit(
            conn, event_type=events.EVENT_CONVERSION_DEBITED, aggregate_id=eur,
            aggregate_ver=2, operation_id="op", currency="EUR", amount_minor=-90_00,
            payload={}, occurred_at=occurred)
        conn.commit()
        consumed = limit_service.daily_consumption_usd_minor(conn, clk.now_utc())
        assert consumed == 100_00  # 90.00 EUR == 100.00 USD
    finally:
        conn.close()


def test_umbral_mfa_usd_por_moneda():
    # USD: >1000.00 exacto no; 1000.01 sí.
    assert fx.requires_mfa_usd(1000_00, "USD") is False
    assert fx.requires_mfa_usd(1000_01, "USD") is True
    # GBP: 800.00 GBP == 1000.00 USD exacto -> no; 800.01 GBP -> sí.
    assert fx.requires_mfa_usd(800_00, "GBP") is False
    assert fx.requires_mfa_usd(800_01, "GBP") is True
