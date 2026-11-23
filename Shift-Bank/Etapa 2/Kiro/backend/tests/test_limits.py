"""Pruebas de límites dinámicos y concurrencia (Etapa 2, Tarea 18).

Cubren: defaults D01, GET/PUT de límites, validación (LIM-09), frontera exacta (A11), consumo
diario acumulado (A12), que un PIN correcto no salta el límite (A14) y que dos operaciones
concurrentes con conexiones SQLite distintas no superan juntas el límite diario (T-8/F8/F9).

Usa fixtures aislados (`app_client`, `isolated_db_path`) y las utilidades de reloj/transacción.

_Requisitos: 13.x, 14.x_ · _Contrato: LIM-01..09; A10, A11, A12, A14_
"""

from datetime import datetime, timezone

import pytest

import app.db as db
import app.limit_service as limit_service
from app.txn import financial_transaction


_CODE = "123456"


def _set_limits(client, per_transfer=None, daily=None):
    payload = {}
    if per_transfer is not None:
        payload["per_transfer"] = per_transfer
    if daily is not None:
        payload["daily"] = daily
    return client.put("/api/limits", json=payload)


def _internal(client, amount, frm="checking", to="savings"):
    return client.post("/api/transfers",
                       json={"from": frm, "to": to, "amount": amount, "description": "x"})


# --- GET / PUT de límites ------------------------------------------------------

def test_defaults_d01(app_client):
    data = app_client.get("/api/limits").json()
    assert data["per_transfer"] == "5000000.00"
    assert data["daily"] == "10000000.00"


def test_get_incluye_consumo_y_disponibilidad(app_client):
    data = app_client.get("/api/limits").json()
    assert set(data.keys()) == {"per_transfer", "daily", "daily_consumed", "daily_remaining"}
    assert data["daily_consumed"] == "0.00"
    assert data["daily_remaining"] == "10000000.00"


def test_put_actualiza_y_aplica(app_client):
    r = _set_limits(app_client, per_transfer="2000000.00", daily="3000000.00")
    assert r.status_code == 200
    assert app_client.get("/api/limits").json()["per_transfer"] == "2000000.00"


def test_put_rechaza_invalidos_sin_modificar(app_client):
    for bad in ("-1.00", "100.123", "abc"):
        r = _set_limits(app_client, per_transfer=bad)
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "INVALID_LIMIT"
    # Los vigentes no cambian.
    assert app_client.get("/api/limits").json()["per_transfer"] == "5000000.00"


# --- Aplicación de límites a internas ------------------------------------------

def test_rechaza_sobre_limite_por_transferencia(app_client):
    _set_limits(app_client, per_transfer="100000.00")
    r = _internal(app_client, "100000.01")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "LIMIT_EXCEEDED_PER_TRANSFER"


def test_frontera_exacta_por_transferencia_permitida(app_client):
    """A11: un monto exactamente igual al límite por transferencia se permite."""
    _set_limits(app_client, per_transfer="100000.00")
    r = _internal(app_client, "100000.00")
    assert r.status_code == 201
    assert r.json()["status"] == "COMPLETED"


def test_consumo_diario_acumulado_a12(app_client):
    """A12 (unidades COP): daily=1000, per_transfer suficiente; 400+300+300 OK, el siguiente falla."""
    _set_limits(app_client, per_transfer="1000.00", daily="1000.00")
    assert _internal(app_client, "400.00").status_code == 201
    assert _internal(app_client, "300.00").status_code == 201
    assert _internal(app_client, "300.00").status_code == 201  # consumo = 1000 exacto (A12 permite)
    # El siguiente (cualquier monto > 0) excede el diario.
    r = _internal(app_client, "10.00")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "LIMIT_EXCEEDED_DAILY"


def test_frontera_exacta_diaria_permitida(app_client):
    """A12: alcanzar exactamente el límite diario disponible se permite."""
    _set_limits(app_client, per_transfer="1000.00", daily="500.00")
    assert _internal(app_client, "500.00").status_code == 201  # exacto
    assert _internal(app_client, "0.01").status_code == 409    # ya no queda disponible


def test_pin_correcto_no_salta_limite_a14(app_client):
    """A14: un PIN correcto no puede completar una transferencia que excede el límite diario.

    Se crea una PENDING_MFA cuando el límite aún lo permite; luego se reduce el límite diario
    por debajo del monto. Al confirmar con el PIN correcto, la verificación de límite (dentro de
    la transacción financiera, antes del débito) rechaza la operación → el PIN no salta el límite.
    """
    # Límites holgados: la creación >= umbral MFA entra en PENDING_MFA.
    _set_limits(app_client, per_transfer="5000000.00", daily="5000000.00")
    r = _internal(app_client, "1500000.00", frm="savings", to="checking")
    assert r.status_code == 201 and r.json()["status"] == "PENDING_MFA"
    ref = r.json()["reference"]

    # Entre la creación y la confirmación, el límite diario baja por debajo del monto pendiente.
    _set_limits(app_client, daily="1000000.00")

    # Confirmar con el PIN correcto debe fallar por límite diario, sin completar ni debitar.
    conf = app_client.post(f"/api/transfers/{ref}/mfa", json={"code": _CODE})
    assert conf.status_code == 409
    assert conf.json()["error"]["code"] == "LIMIT_EXCEEDED_DAILY"
    # El saldo no se movió (la transferencia no se completó).
    bal = app_client.get("/api/accounts").json()["accounts"]
    savings = next(a["balance"] for a in bal if a["name"] == "Savings")
    assert savings == "15000000.00"


# --- Consumo diario: exclusión de estados no consumidos ------------------------

def test_pending_mfa_no_cuenta_para_consumo(app_client, isolated_db_path):
    """Una PENDING_MFA no debe sumar al consumo diario (solo COMPLETED/ACH pending-settled)."""
    _set_limits(app_client, per_transfer="5000000.00", daily="5000000.00")
    # Crear una PENDING_MFA (>= umbral) sin confirmar.
    _internal(app_client, "2000000.00", frm="savings", to="checking")
    conn = db.get_connection(isolated_db_path)
    try:
        consumo = limit_service.daily_consumption_cents(conn, datetime.now(timezone.utc))
    finally:
        conn.close()
    assert consumo == 0  # la pendiente no cuenta


# --- Concurrencia con conexiones distintas (T-8) -------------------------------

def test_concurrencia_no_supera_limite_diario(isolated_db_path):
    """Dos operaciones concurrentes (conexiones distintas) no exceden juntas el límite diario.

    Sincronización determinista (sin sleeps): conn1 abre `financial_transaction` (BEGIN
    IMMEDIATE, toma el write-lock); mientras está abierta, conn2 no puede iniciar su propia
    transacción de escritura (OperationalError), por lo que no puede leer-y-debitar en paralelo.
    Esto demuestra la serialización que previene el doble gasto del límite diario.
    """
    # Preparar DB con esquema, seed y límites; fijar daily pequeño.
    from app.seed import seed, seed_limits
    conn_setup = db.get_connection(isolated_db_path)
    try:
        db.init_schema(conn_setup)
        db.migrate(conn_setup)
        seed(conn_setup)
        seed_limits(conn_setup)
        cust = conn_setup.execute("SELECT id FROM customer LIMIT 1").fetchone()["id"]
        # daily = 100.000 centavos (1.000,00 COP); per_transfer amplio.
        conn_setup.execute(
            "UPDATE transfer_limit SET per_transfer_cents = 100000000, daily_cents = 100000 "
            "WHERE customer_id = ?", (cust,))
        conn_setup.commit()
    finally:
        conn_setup.close()

    import sqlite3
    import app.repository as repository
    from app.clock import iso

    conn1 = db.get_connection(isolated_db_path)
    conn2 = sqlite3.connect(str(isolated_db_path), timeout=0.2)
    conn2.row_factory = sqlite3.Row
    conn2.execute("PRAGMA foreign_keys = ON;")
    now = datetime.now(timezone.utc)
    try:
        # conn1 toma el write-lock y consume el total del diario creando una transferencia
        # COMPLETED (que es lo que cuenta para el consumo diario).
        created = repository.create_transfer(
            conn1, from_kind="savings", to_kind="checking", amount_cents=100000,
            description="c", status="PENDING_MFA", requires_mfa=False,
            created_at=iso(now), expires_at=None, reference=None)
        with financial_transaction(conn1):
            limit_service.check(conn1, 100000, now)  # 100.000 == daily: permitido (frontera)
            repository.apply_transfer_in_tx(
                conn1, transfer_id=created.id, from_kind="savings", to_kind="checking",
                amount_cents=100000, completed_at=iso(now))
            # Mientras conn1 mantiene la transacción, conn2 NO puede iniciar BEGIN IMMEDIATE.
            with pytest.raises(sqlite3.OperationalError):
                conn2.execute("BEGIN IMMEDIATE")
        # Tras el commit de conn1, conn2 ya ve el consumo (100.000) y su check del diario falla.
        with pytest.raises(limit_service.LimitError) as ei:
            with financial_transaction(conn2):
                limit_service.check(conn2, 1, now)  # 1 centavo más excede el diario ya consumido
        assert ei.value.code == "LIMIT_EXCEEDED_DAILY"
    finally:
        conn1.close()
        conn2.close()
