"""Pruebas de la verificación de invariantes post-carga (Etapa 3, Tarea 22).

design.md §3.4 · requirements R10.4, R10.5 · AC-09.

Verifican que `loadtest.verify_invariants` detecta de verdad —sin tragarse nada— las
violaciones de los tres invariantes financieros tras una corrida de carga:

1. **Conservación del dinero (R10.4).** El invariante se DERIVA del modelo real: la suma de
   saldos más el dinero ACH debitado-no-reembolsado (`pending`/`settled`) debe igualar el total
   inicial sembrado. Las transferencias internas conservan la suma de saldos (debita+abona); las
   ACH sacan dinero del sistema hasta reembolso.
2. **Ausencia de estados parciales (R10.4).** Ninguna fila `transfer` en un `status` fuera del
   catálogo de reposo heredado, ni incoherente con sus columnas (`completed_at`/`settled_at`/
   `refunded`).
3. **Integridad de la cadena de auditoría (R10.4), incluida el ancla (§2.9).**

Estrategia:
- Se siembra una DB SQLite de ARCHIVO aislada reutilizando los helpers de `loadtest.isolation`
  (Tarea 18): claves de SOLO-carga en el entorno, `DB_PATH` parcheado, saldos/límites amplios.
- Se ejecutan transacciones financieras REALES a través de la capa de servicio heredada
  (`app.service.create_transfer`, `app.ach_service.create_ach/settle_ach/fail_ach`) —nunca SQL
  inventado ni mocks—, cada una atómica con su auditoría encadenada.
- Pruebas POSITIVAS: tras transferencias internas y ACH, la conservación se mantiene (contando
  la salida ACH) y la cadena es íntegra.
- Pruebas NEGATIVAS: se corrompe un saldo (rompe conservación), se manipula una fila de
  auditoría (rompe la cadena) y se deja un estado parcial (ACH `settled` sin `settled_at`,
  interna `COMPLETED` sin `completed_at`, estado desconocido): la verificación DEBE reportar
  `ok=False` con la violación correspondiente.

Aislamiento: la DB vive bajo `tmp_path` (archivo desechable), nunca la DB histórica ni
`SEED-3.md`. No se importa `locust`/gevent (coherente con `report.py`), solo el paquete `app`.

_Requisitos: R10.4, R10.5_ · _Diseño: §3.4_ · _AC: AC-09_
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

# `loadtest` vive en la raíz del proyecto (junto a `backend/`). pytest corre desde `backend/`,
# así que se añade la raíz del proyecto a sys.path para importar `loadtest.*`. Importar
# `loadtest.isolation` además añade `backend/` a sys.path y fija las claves de SOLO-carga.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from loadtest import isolation  # noqa: E402
from loadtest import verify_invariants as vi  # noqa: E402

import app.ach_service as ach_service  # noqa: E402
import app.clock as clock  # noqa: E402
import app.db as db  # noqa: E402
import app.service as service  # noqa: E402

# El total inicial sembrado por isolation.py (checking + savings), en centavos.
_SEEDED_TOTAL_CENTS = (
    isolation.LOADTEST_CHECKING_BALANCE_CENTS + isolation.LOADTEST_SAVINGS_BALANCE_CENTS
)

# Monto interno pequeño (bajo el umbral MFA de 1.000.000 COP): completa directo sin MFA.
_INTERNAL_AMOUNT_RAW = "50000.00"
# Monto ACH pequeño (bajo el umbral MFA): crea `pending` + débito sin MFA.
_ACH_AMOUNT_RAW = "25000.00"
_ACH_AMOUNT_CENTS = 25_000_00

_ADHOC_BENEFICIARY = {
    "name": "External Person",
    "bank": "Other Bank",
    "routing_number": "021000021",
    "account_number": "1234567890",
}


@pytest.fixture()
def loadtest_db(tmp_path) -> Path:
    """DB SQLite de archivo aislada, sembrada con los valores sintéticos de carga (Tarea 18).

    Reutiliza `isolation.setup_loadtest_db` (configura entorno + parcheo DB_PATH + siembra
    determinista). Se fija una ruta bajo `tmp_path` (desechable) para no tocar `/tmp` global ni
    la DB histórica. Teardown elimina la DB y sus auxiliares.
    """
    db_path = tmp_path / "shift_bank_loadtest_invariants.db"
    isolation.setup_loadtest_db(db_path)
    yield db_path
    isolation.teardown_synthetic_db(db_path)


def _run_internal_transfers(db_path: Path, n: int) -> None:
    """Ejecuta `n` transferencias internas pequeñas alternando dirección (vía capa de servicio).

    Alternar checking↔savings conserva la suma de saldos y evita drenar una cuenta. Cada una va
    por `app.service.create_transfer`, que aplica el débito/crédito y la auditoría atómicamente.
    """
    conn = db.get_connection(db_path)
    try:
        direction = [("checking", "savings"), ("savings", "checking")]
        for i in range(n):
            from_kind, to_kind = direction[i % 2]
            result = service.create_transfer(
                conn,
                from_kind=from_kind,
                to_kind=to_kind,
                amount_raw=_INTERNAL_AMOUNT_RAW,
                description=f"loadtest internal {i}",
            )
            assert result.status == "COMPLETED"
    finally:
        conn.close()


def _create_ach_pending(db_path: Path, manual: clock.ManualClock) -> str:
    """Crea una ACH pequeña (sin MFA) → `pending` + débito. Devuelve el id de la transferencia.

    Usa un `ManualClock` inyectado para que la elegibilidad de settlement sea determinista.
    """
    original = clock.system_clock
    clock.system_clock = manual
    conn = db.get_connection(db_path)
    try:
        res = ach_service.create_ach(
            conn,
            amount_raw=_ACH_AMOUNT_RAW,
            description="loadtest ach",
            from_kind="checking",
            adhoc=dict(_ADHOC_BENEFICIARY),
        )
        assert res.status == "pending"
        row = conn.execute(
            "SELECT id FROM transfer WHERE reference = ? AND type = 'ach'", (res.reference,)
        ).fetchone()
        return row["id"]
    finally:
        conn.close()
        clock.system_clock = original


# ===========================================================================
# PRUEBAS POSITIVAS: estado sano ⇒ ok=True, conservación y cadena íntegras
# ===========================================================================
def test_clean_run_internal_transfers_conserves_money(loadtest_db: Path):
    """Transferencias internas: suma de saldos conservada, sin salida ACH, cadena íntegra."""
    _run_internal_transfers(loadtest_db, 12)

    report = vi.verify_invariants(loadtest_db, expected_total_cents=_SEEDED_TOTAL_CENTS)

    assert report.ok, report.violations
    assert report.violations == []
    # Sin ACH, el observado == suma de saldos == total sembrado (internas conservan la suma).
    assert report.ach_outflow_cents == 0
    assert report.observed_total_cents == _SEEDED_TOTAL_CENTS
    assert sum(report.balances_cents.values()) == _SEEDED_TOTAL_CENTS


def test_clean_run_with_ach_outflow_conserves_with_formula(loadtest_db: Path):
    """ACH `pending`: el dinero salió del sistema; conservación se mantiene al CONTAR la salida.

    Verifica que la fórmula derivada (`saldos + salida_ACH`) es la correcta: la suma de saldos
    por sí sola ya NO iguala el inicial (hubo débito ACH), pero `saldos + ach_outflow` sí.
    """
    _run_internal_transfers(loadtest_db, 4)
    manual = clock.ManualClock()
    _create_ach_pending(loadtest_db, manual)

    report = vi.verify_invariants(loadtest_db, expected_total_cents=_SEEDED_TOTAL_CENTS)

    assert report.ok, report.violations
    assert report.ach_outflow_cents == _ACH_AMOUNT_CENTS
    # La suma de saldos SOLA quedó corta por el débito ACH...
    assert sum(report.balances_cents.values()) == _SEEDED_TOTAL_CENTS - _ACH_AMOUNT_CENTS
    # ...pero saldos + salida ACH recupera el total sembrado (conservación real).
    assert report.observed_total_cents == _SEEDED_TOTAL_CENTS


def test_clean_run_ach_settled_still_counts_as_outflow(loadtest_db: Path):
    """ACH liquidada (`settled`) sigue siendo dinero fuera del sistema; conservación intacta."""
    manual = clock.ManualClock()
    transfer_id = _create_ach_pending(loadtest_db, manual)

    # Avanzar el reloj más allá del retardo de settlement y liquidar (lógica real).
    manual.advance(seconds=ach_service.ACH_SETTLEMENT_DELAY_SECONDS + 5)
    conn = db.get_connection(loadtest_db)
    try:
        assert ach_service.settle_ach(conn, transfer_id, now=manual.now_utc()) is True
        assert conn.execute(
            "SELECT status FROM transfer WHERE id = ?", (transfer_id,)
        ).fetchone()["status"] == "settled"
    finally:
        conn.close()

    report = vi.verify_invariants(loadtest_db, expected_total_cents=_SEEDED_TOTAL_CENTS)
    assert report.ok, report.violations
    assert report.ach_outflow_cents == _ACH_AMOUNT_CENTS
    assert report.observed_total_cents == _SEEDED_TOTAL_CENTS


def test_clean_run_ach_failed_refund_returns_money(loadtest_db: Path):
    """ACH fallida con reembolso exactamente-una-vez: el dinero vuelve; sin salida pendiente."""
    manual = clock.ManualClock()
    transfer_id = _create_ach_pending(loadtest_db, manual)

    conn = db.get_connection(loadtest_db)
    try:
        assert ach_service.fail_ach(conn, transfer_id) is True
        assert conn.execute(
            "SELECT status, refunded FROM transfer WHERE id = ?", (transfer_id,)
        ).fetchone()["status"] == "failed"
    finally:
        conn.close()

    report = vi.verify_invariants(loadtest_db, expected_total_cents=_SEEDED_TOTAL_CENTS)
    assert report.ok, report.violations
    # `failed` no es salida (ya reembolsó): el dinero volvió a los saldos.
    assert report.ach_outflow_cents == 0
    assert sum(report.balances_cents.values()) == _SEEDED_TOTAL_CENTS
    assert report.observed_total_cents == _SEEDED_TOTAL_CENTS


def test_assert_ok_does_not_raise_on_clean_run(loadtest_db: Path):
    """`assert_ok()` no lanza cuando todo está sano (API fail-loud para llamadores)."""
    _run_internal_transfers(loadtest_db, 3)
    report = vi.verify_invariants(loadtest_db, expected_total_cents=_SEEDED_TOTAL_CENTS)
    report.assert_ok()  # no debe lanzar


# ===========================================================================
# PRUEBAS NEGATIVAS: cada violación DEBE detectarse (fail-loud, R10.5)
# ===========================================================================
def test_corrupted_balance_breaks_conservation(loadtest_db: Path):
    """Corromper un saldo (crear dinero de la nada) ⇒ violación de conservación detectada."""
    _run_internal_transfers(loadtest_db, 2)

    # Inyectar 1.000,00 COP de la nada en checking (rompe la conservación).
    conn = db.get_connection(loadtest_db)
    try:
        conn.execute(
            "UPDATE account SET balance_cents = balance_cents + ? WHERE kind = 'checking'",
            (100_000,),
        )
        conn.commit()
    finally:
        conn.close()

    report = vi.verify_invariants(loadtest_db, expected_total_cents=_SEEDED_TOTAL_CENTS)

    assert report.ok is False
    kinds = {v.kind for v in report.violations}
    assert "money_conservation" in kinds
    assert report.observed_total_cents == _SEEDED_TOTAL_CENTS + 100_000
    # assert_ok debe lanzar en estado violado.
    with pytest.raises(vi.InvariantError):
        report.assert_ok()


def test_destroyed_money_breaks_conservation(loadtest_db: Path):
    """Destruir dinero (restar de un saldo) ⇒ violación de conservación detectada."""
    conn = db.get_connection(loadtest_db)
    try:
        conn.execute(
            "UPDATE account SET balance_cents = balance_cents - ? WHERE kind = 'savings'",
            (500_000,),
        )
        conn.commit()
    finally:
        conn.close()

    report = vi.verify_invariants(loadtest_db, expected_total_cents=_SEEDED_TOTAL_CENTS)
    assert report.ok is False
    assert any(v.kind == "money_conservation" for v in report.violations)
    assert report.observed_total_cents == _SEEDED_TOTAL_CENTS - 500_000


def test_tampered_audit_row_breaks_chain(loadtest_db: Path):
    """Manipular una fila de `audit_log` ⇒ violación de integridad de cadena detectada.

    La manipulación se hace con SQL directo (un atacante con acceso a la DB); los triggers
    append-only de la app abortan UPDATE/DELETE, así que se eliminan antes para simular la
    manipulación a nivel de archivo (dentro del modelo de amenazas §10).
    """
    _run_internal_transfers(loadtest_db, 3)

    conn = db.get_connection(loadtest_db)
    try:
        # Quitar los triggers append-only para poder simular manipulación a nivel de archivo.
        conn.execute("DROP TRIGGER IF EXISTS audit_log_no_update")
        conn.execute("DROP TRIGGER IF EXISTS audit_log_no_delete")
        # Alterar el payload de la primera entrada SIN recalcular el HMAC (contenido manipulado).
        conn.execute(
            "UPDATE audit_log SET payload = ? WHERE seq = (SELECT MIN(seq) FROM audit_log)",
            ('{"tampered":true}',),
        )
        conn.commit()
    finally:
        conn.close()

    report = vi.verify_invariants(loadtest_db, expected_total_cents=_SEEDED_TOTAL_CENTS)
    assert report.ok is False
    assert any(v.kind == "audit_chain" for v in report.violations)
    assert report.audit_failed_seq is not None


def test_truncated_audit_tail_breaks_chain_via_anchor(loadtest_db: Path):
    """Truncar la cola de auditoría (borrar la última entrada) ⇒ el ANCLA lo detecta (§2.9)."""
    _run_internal_transfers(loadtest_db, 4)

    conn = db.get_connection(loadtest_db)
    try:
        conn.execute("DROP TRIGGER IF EXISTS audit_log_no_update")
        conn.execute("DROP TRIGGER IF EXISTS audit_log_no_delete")
        # Borrar la ÚLTIMA entrada pero dejar el ancla apuntando a ella (truncación del final).
        conn.execute(
            "DELETE FROM audit_log WHERE seq = (SELECT MAX(seq) FROM audit_log)"
        )
        conn.commit()
    finally:
        conn.close()

    report = vi.verify_invariants(loadtest_db, expected_total_cents=_SEEDED_TOTAL_CENTS)
    assert report.ok is False
    assert any(v.kind == "audit_chain" for v in report.violations)


def test_partial_state_ach_settled_without_settled_at(loadtest_db: Path):
    """ACH `settled` sin `settled_at` ⇒ estado parcial detectado."""
    manual = clock.ManualClock()
    transfer_id = _create_ach_pending(loadtest_db, manual)

    conn = db.get_connection(loadtest_db)
    try:
        # Forzar un settled parcial (sin settled_at), evitando la lógica correcta del servicio.
        conn.execute(
            "UPDATE transfer SET status = 'settled', settled_at = NULL WHERE id = ?",
            (transfer_id,),
        )
        conn.commit()
    finally:
        conn.close()

    report = vi.verify_invariants(loadtest_db, expected_total_cents=_SEEDED_TOTAL_CENTS)
    assert report.ok is False
    assert any(v.kind == "partial_state" for v in report.violations)


def test_partial_state_internal_completed_without_completed_at(loadtest_db: Path):
    """Interna `COMPLETED` sin `completed_at` ⇒ estado parcial (movimiento parcial) detectado."""
    _run_internal_transfers(loadtest_db, 2)

    conn = db.get_connection(loadtest_db)
    try:
        conn.execute(
            """UPDATE transfer SET completed_at = NULL
               WHERE type = 'internal' AND status = 'COMPLETED'
               AND rowid = (SELECT rowid FROM transfer
                            WHERE type='internal' AND status='COMPLETED' LIMIT 1)"""
        )
        conn.commit()
    finally:
        conn.close()

    report = vi.verify_invariants(loadtest_db, expected_total_cents=_SEEDED_TOTAL_CENTS)
    assert report.ok is False
    assert any(v.kind == "partial_state" for v in report.violations)


def test_partial_state_unknown_status_detected(loadtest_db: Path):
    """Un `status` fuera del catálogo de reposo ⇒ estado parcial detectado."""
    _run_internal_transfers(loadtest_db, 1)

    conn = db.get_connection(loadtest_db)
    try:
        conn.execute(
            """UPDATE transfer SET status = 'WEIRD_INTERMEDIATE'
               WHERE rowid = (SELECT rowid FROM transfer LIMIT 1)"""
        )
        conn.commit()
    finally:
        conn.close()

    report = vi.verify_invariants(loadtest_db, expected_total_cents=_SEEDED_TOTAL_CENTS)
    assert report.ok is False
    assert any(v.kind == "partial_state" for v in report.violations)


# ===========================================================================
# FAIL-LOUD: DB ausente / ilegible NO es un PASS
# ===========================================================================
def test_missing_db_is_failure_not_pass(tmp_path: Path):
    """Una DB inexistente ⇒ ok=False (precondición), nunca un PASS silencioso (R10.5)."""
    missing = tmp_path / "does_not_exist.db"
    report = vi.verify_invariants(missing, expected_total_cents=_SEEDED_TOTAL_CENTS)
    assert report.ok is False
    assert any(v.kind == "precondition" for v in report.violations)


def test_db_without_schema_is_failure(tmp_path: Path):
    """Un archivo DB sin el esquema esperado ⇒ ok=False (fallo explícito), no un PASS."""
    empty = tmp_path / "empty.db"
    # Crear un archivo SQLite vacío (sin las tablas del backend).
    sqlite3.connect(str(empty)).close()

    report = vi.verify_invariants(empty, expected_total_cents=_SEEDED_TOTAL_CENTS)
    assert report.ok is False
    assert any(v.kind == "precondition" for v in report.violations)


def test_default_expected_total_uses_observed(loadtest_db: Path):
    """Sin `expected_total_cents`, se usa el total actual (apoyo diagnóstico): conservación ok.

    Esta ruta no detecta pérdida/creación por sí sola (lo documenta el módulo); solo confirma que
    el fallback no fabrica un número y deja pasar un estado internamente consistente.
    """
    _run_internal_transfers(loadtest_db, 2)
    report = vi.verify_invariants(loadtest_db)  # sin expected_total_cents
    assert report.ok, report.violations
    assert report.expected_total_cents == report.observed_total_cents
