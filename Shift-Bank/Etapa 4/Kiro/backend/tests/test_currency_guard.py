"""Verificación de guardias de divisa ACH/recurrentes (Etapa 4, Tarea 15; D-08, R12).

ACH solo desde USD; recurrente interno misma moneda; recurrente ACH solo USD. Violaciones ->
error de dominio sin mover saldos ni crear schedules.

_Requisitos: R12_ · _Diseño: §3.4_ · _AC: AC4-18_
"""

import pytest

import app.db as db
from app import currency_guard as cg
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


def test_ach_origen_usd_ok(tmp_path):
    path = _stage4(tmp_path / "g.db")
    conn = db.get_connection(path)
    try:
        cg.require_ach_origin_usd(conn, public_id="CHK-1001")  # USD -> ok
    finally:
        conn.close()


def test_ach_origen_no_usd_rechazado(tmp_path):
    path = _stage4(tmp_path / "g.db")
    conn = db.get_connection(path)
    try:
        with pytest.raises(cg.CurrencyGuardError) as exc:
            cg.require_ach_origin_usd(conn, public_id="EUR-3001")
        assert exc.value.code == "ACH_ORIGIN_NOT_USD"
    finally:
        conn.close()


def test_recurrente_interno_misma_moneda(tmp_path):
    path = _stage4(tmp_path / "g.db")
    conn = db.get_connection(path)
    try:
        cg.require_recurring_internal_same_currency(
            conn, from_public_id="CHK-1001", to_public_id="SAV-2001")  # USD/USD ok
        with pytest.raises(cg.CurrencyGuardError) as exc:
            cg.require_recurring_internal_same_currency(
                conn, from_public_id="CHK-1001", to_public_id="EUR-3001")
        assert exc.value.code == "CROSS_CURRENCY_NOT_ALLOWED"
    finally:
        conn.close()


def test_recurrente_ach_solo_usd(tmp_path):
    path = _stage4(tmp_path / "g.db")
    conn = db.get_connection(path)
    try:
        cg.require_recurring_ach_usd(conn, from_public_id="SAV-2001")  # USD ok
        with pytest.raises(cg.CurrencyGuardError) as exc:
            cg.require_recurring_ach_usd(conn, from_public_id="GBP-4001")
        assert exc.value.code == "RECURRING_ACH_NOT_USD"
    finally:
        conn.close()
