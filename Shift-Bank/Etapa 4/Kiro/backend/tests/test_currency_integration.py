"""Aceptación T15: las restricciones de divisa se APLICAN en los servicios reales ACH y recurrente
(D-08), sobre la fixture D-02. No basta con las pruebas unitarias de currency_guard.

ACH solo desde USD; recurrente interno misma moneda; recurrente ACH solo USD. Las cuentas D-02
usan `kind`: checking/savings = USD; eur = EUR; gbp = GBP.

_Requisitos: R12_ · _Diseño: §3.4_ · _AC: AC4-18_
"""

import pytest

import app.db as db
from app import ach_service, recurring_service
from app.clock import ManualClock
from app.seed import seed_stage4, seed_limits


def _stage4(path):
    conn = db.get_connection(path)
    try:
        db.init_schema(conn)
        db.migrate(conn)
        seed_stage4(conn)
        seed_limits(conn)
    finally:
        conn.close()
    return path


def _adhoc():
    return {"name": "Payee", "bank": "Bank", "routing_number": "123456789",
            "account_number": "1234567890"}


def test_ach_desde_usd_ok(tmp_path):
    path = _stage4(tmp_path / "ci.db")
    conn = db.get_connection(path)
    try:
        # checking (USD) -> ACH permitido (monto bajo, sin MFA).
        res = ach_service.create_ach(
            conn, amount_raw="10.00", description="x", from_kind="checking",
            adhoc=_adhoc())
        assert res.status in ("pending", "pending_auth")
    finally:
        conn.close()


def test_ach_desde_no_usd_rechazado(tmp_path):
    path = _stage4(tmp_path / "ci.db")
    conn = db.get_connection(path)
    try:
        # `eur` (EUR) -> ACH debe rechazarse por la guardia de divisa real del servicio.
        with pytest.raises(ach_service.AchError) as exc:
            ach_service.create_ach(
                conn, amount_raw="10.00", description="x", from_kind="eur",
                adhoc=_adhoc())
        assert exc.value.code == "ACH_ORIGIN_NOT_USD"
    finally:
        conn.close()


def test_recurrente_interno_misma_moneda_ok(tmp_path):
    path = _stage4(tmp_path / "ci.db")
    conn = db.get_connection(path)
    try:
        clk = ManualClock()
        res = recurring_service.create_schedule(
            conn, type="internal", amount_raw="10.00", frequency="daily",
            from_kind="checking", to_kind="savings", now=clk.now_utc())
        assert res.status == "active"
    finally:
        conn.close()


def test_recurrente_interno_cross_currency_rechazado(tmp_path):
    path = _stage4(tmp_path / "ci.db")
    conn = db.get_connection(path)
    try:
        clk = ManualClock()
        # checking (USD) -> eur (EUR): cross-currency, rechazado por el servicio real.
        with pytest.raises(recurring_service.RecurringError) as exc:
            recurring_service.create_schedule(
                conn, type="internal", amount_raw="10.00", frequency="daily",
                from_kind="checking", to_kind="eur", now=clk.now_utc())
        assert exc.value.code in ("CROSS_CURRENCY_NOT_ALLOWED", "INVALID_DESTINATION")
    finally:
        conn.close()


def test_recurrente_ach_desde_no_usd_rechazado(tmp_path):
    path = _stage4(tmp_path / "ci.db")
    conn = db.get_connection(path)
    try:
        clk = ManualClock()
        with pytest.raises(recurring_service.RecurringError) as exc:
            recurring_service.create_schedule(
                conn, type="ach", amount_raw="10.00", frequency="daily",
                from_kind="eur", adhoc=_adhoc(), now=clk.now_utc())
        assert exc.value.code == "RECURRING_ACH_NOT_USD"
    finally:
        conn.close()


def test_recurrente_ach_desde_usd_ok(tmp_path):
    path = _stage4(tmp_path / "ci.db")
    conn = db.get_connection(path)
    try:
        clk = ManualClock()
        res = recurring_service.create_schedule(
            conn, type="ach", amount_raw="10.00", frequency="daily",
            from_kind="checking", adhoc=_adhoc(), now=clk.now_utc())
        assert res.status == "active"
    finally:
        conn.close()
