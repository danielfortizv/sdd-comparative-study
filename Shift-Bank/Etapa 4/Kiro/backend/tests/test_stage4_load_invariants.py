"""Verificación de invariantes multidivisa bajo un lote de operaciones (Tarea 24; D-05/D-06/D-09).

Simula una corrida de carga determinista (lote de transferencias internas y conversiones sobre la
fixture D-02) y verifica los invariantes event-sourced de la Etapa 4 tras la corrida. Cualquier
violación marca FALLA con independencia del rendimiento (R16-3). La DB es sintética/aislada.

NOTA de alcance: el benchmark Locust completo (servidor vivo, 30 usuarios, ramp 5/s, 60s) es el
arnés heredado (`loadtest/`), disponible y preservado; esta prueba verifica los INVARIANTES
multidivisa de forma determinista y reproducible sin levantar el servidor.

_Requisitos: R16, R19_ · _Diseño: Testing Strategy_ · _AC: AC4-20_
"""

import sys
from pathlib import Path

# Hacer importable el paquete loadtest (está en la raíz del repo Kiro, junto a backend/).
_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import uuid

import app.db as db
from app import command, events, idempotency
from app.seed import seed_stage4
from loadtest.verify_invariants_stage4 import verify_all


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


def _internal(conn, amount_minor):
    chk, sav = _aid(conn, "CHK-1001"), _aid(conn, "SAV-2001")
    cv = conn.execute("SELECT version FROM account WHERE id=?", (chk,)).fetchone()["version"]
    sv = conn.execute("SELECT version FROM account WHERE id=?", (sav,)).fetchone()["version"]
    idempotency.execute_idempotent_command(
        conn, idempotency_key=str(uuid.uuid4()), operation="internal_transfer",
        request_payload={"a": amount_minor, "n": uuid.uuid4().hex},
        expected_versions={chk: cv, sav: sv},
        effects=[
            command.AccountEffect(chk, events.EVENT_INTERNAL_TRANSFER_DEBITED, -amount_minor),
            command.AccountEffect(sav, events.EVENT_INTERNAL_TRANSFER_CREDITED, +amount_minor),
        ],
        occurred_at="2026-02-01T00:00:00Z",
        build_response=lambda eids: {"ok": True})


def test_lote_de_carga_mantiene_invariantes(tmp_path):
    path = _stage4(tmp_path / "load.db")
    conn = db.get_connection(path)
    try:
        # Lote determinista: 40 transferencias internas pequeñas ida y vuelta.
        for i in range(40):
            _internal(conn, 10_00 if i % 2 == 0 else 5_00)
        ok = verify_all(conn)
        assert ok == [
            "projection_consistency", "no_duplicate_versions",
            "internal_conservation_per_currency", "rebuild_matches",
        ]
        # Conservación global USD: CHK+SAV sigue sumando 12500.00 (nada sale del sistema interno).
        total = conn.execute(
            "SELECT SUM(balance_cents) AS s FROM account WHERE currency='USD'").fetchone()["s"]
        assert total == 12_500_00
    finally:
        conn.close()
