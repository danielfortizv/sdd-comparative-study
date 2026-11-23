"""Regresión Etapa 1 — MFA simulada en transferencias internas (Tarea 4).

Fija el comportamiento HEREDADO del mecanismo MFA: umbral, estado PENDING_MFA sin mover
saldos, confirmación con código correcto/incorrecto, expiración a 5 minutos, re-verificación
de fondos al confirmar e idempotencia. No introduce lockout, códigos alternativos ni reglas
nuevas: verifica el contrato tal como está en la Etapa 1.

Fuente del comportamiento esperado (código heredado real):
- `app/config.py`: `MFA_THRESHOLD = 1000000`, `MFA_CODE = "123456"`, `MFA_TTL_SECONDS = 300`.
- `app/service.py`: `requires_mfa = amount >= MFA_THRESHOLD`; PENDING_MFA con
  `expires_at = now + 5min`, `reference = uuid4().hex`, sin tocar saldos; `_expire_if_needed`
  compara `_now_utc()` con `expires_at`; código incorrecto → sigue PENDING_MFA (sin lockout);
  correcto + fondos insuficientes → FAILED; correcto + fondos → COMPLETED (apply_transfer).
- `app/routers/transfers.py`: `POST /api/transfers` → 201; `POST /api/transfers/{ref}/mfa`;
  mapa HTTP: INVALID_MFA_CODE 401, EXPIRED 409, INSUFFICIENT_FUNDS (confirmar) 409, NOT_FOUND 404.

Control de tiempo determinista: se monkeypatchea `app.service._now_utc` (solo en el entorno de
test) para forzar la expiración sin esperar 5 minutos reales. No se modifica código de producción.

_Requisitos: 15.4_ · _Contrato: HER-03; A13_
"""

from datetime import datetime, timedelta, timezone

import app.db as db
import app.service as service


_CODE = "123456"           # código MFA simulado heredado
_THRESHOLD_STR = "1000000.00"  # umbral exacto (COP 1.000.000)


def _balances_cents(db_path):
    conn = db.get_connection(db_path)
    try:
        rows = conn.execute("SELECT display_name, balance_cents FROM account").fetchall()
    finally:
        conn.close()
    return {r["display_name"]: r["balance_cents"] for r in rows}


def _create_transfer(client, amount, frm="savings", to="checking", desc="mfa"):
    return client.post(
        "/api/transfers",
        json={"from": frm, "to": to, "amount": amount, "description": desc},
    )


# --- A. Umbral de MFA ----------------------------------------------------------

def test_bajo_umbral_no_requiere_mfa(app_client):
    """Monto < 1.000.000 no requiere MFA (COMPLETED directo)."""
    resp = _create_transfer(app_client, "999999.99")
    assert resp.status_code == 201
    assert resp.json()["mfa_required"] is False
    assert resp.json()["status"] == "COMPLETED"


def test_exactamente_umbral_requiere_mfa(app_client):
    """Monto == 1.000.000 requiere MFA (umbral es >=)."""
    resp = _create_transfer(app_client, _THRESHOLD_STR)
    assert resp.status_code == 201
    body = resp.json()
    assert body["mfa_required"] is True
    assert body["status"] == "PENDING_MFA"


def test_sobre_umbral_requiere_mfa(app_client):
    """Monto > 1.000.000 requiere MFA."""
    resp = _create_transfer(app_client, "2000000.00")
    assert resp.status_code == 201
    assert resp.json()["mfa_required"] is True
    assert resp.json()["status"] == "PENDING_MFA"


def test_respuesta_inicial_mfa_schema_heredado(app_client):
    """La respuesta MFA-required contiene reference y expires_at (schema heredado)."""
    body = _create_transfer(app_client, _THRESHOLD_STR).json()
    assert set(body.keys()) == {"status", "mfa_required", "reference", "expires_at"}
    assert isinstance(body["reference"], str) and body["reference"]
    assert isinstance(body["expires_at"], str) and body["expires_at"].endswith("Z")


# --- B. Autorización pendiente -------------------------------------------------

def test_pending_no_debita_ni_acredita(app_client, isolated_db_path):
    """Una transferencia PENDING_MFA no mueve ningún saldo."""
    before = _balances_cents(isolated_db_path)
    _create_transfer(app_client, "2000000.00")
    assert _balances_cents(isolated_db_path) == before


def test_pending_visible_en_historial(app_client):
    """La transferencia pendiente es observable en el historial con estado PENDING_MFA."""
    _create_transfer(app_client, "2000000.00", desc="pend")
    hist = app_client.get("/api/transfers").json()["transfers"]
    pend = [t for t in hist if t["description"] == "pend"]
    assert len(pend) == 1
    assert pend[0]["status"] == "PENDING_MFA"


# --- C. Confirmación MFA exitosa ----------------------------------------------

def test_confirmacion_correcta_completa_y_mueve_saldos(app_client, isolated_db_path):
    """Código correcto → COMPLETED (200), débito+crédito, total preservado, una sola vez."""
    before = _balances_cents(isolated_db_path)
    total_before = sum(before.values())
    ref = _create_transfer(app_client, "2000000.00").json()["reference"]

    resp = app_client.post(f"/api/transfers/{ref}/mfa", json={"code": _CODE})
    assert resp.status_code == 200
    assert resp.json()["status"] == "COMPLETED"

    after = _balances_cents(isolated_db_path)
    # 2.000.000,00 COP = 200.000.000 centavos; Savings→Checking.
    assert after["Savings"] == before["Savings"] - 200_000_000
    assert after["Checking"] == before["Checking"] + 200_000_000
    assert sum(after.values()) == total_before  # total invariante


def test_estado_y_forma_tras_completar(app_client):
    """Tras COMPLETED, el historial conserva forma heredada y estado MAYÚSCULAS."""
    ref = _create_transfer(app_client, "2000000.00", desc="ok").json()["reference"]
    app_client.post(f"/api/transfers/{ref}/mfa", json={"code": _CODE})
    hist = app_client.get("/api/transfers").json()["transfers"]
    t = next(x for x in hist if x["description"] == "ok")
    assert t["status"] == "COMPLETED"
    # Campos heredados + `type` aditivo aprobado (D03/D05, Tarea 25).
    assert {"date", "direction", "amount", "description", "status"}.issubset(t.keys())
    assert set(t.keys()) <= {"date", "direction", "amount", "description", "status", "type"}
    assert t.get("type") == "internal"


# --- D. Confirmación MFA inválida ---------------------------------------------

def test_codigo_incorrecto_rechazado_sin_lockout(app_client, isolated_db_path):
    """Código incorrecto → 401 INVALID_MFA_CODE, sigue PENDING_MFA, permite reintento, sin débito."""
    before = _balances_cents(isolated_db_path)
    ref = _create_transfer(app_client, "2000000.00").json()["reference"]

    # Varios intentos incorrectos: ninguno bloquea (sin lockout) ni mueve saldos.
    for _ in range(3):
        resp = app_client.post(f"/api/transfers/{ref}/mfa", json={"code": "000000"})
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "INVALID_MFA_CODE"
    assert _balances_cents(isolated_db_path) == before

    # Tras los intentos incorrectos, el código correcto AÚN completa (no hubo lockout).
    ok = app_client.post(f"/api/transfers/{ref}/mfa", json={"code": _CODE})
    assert ok.status_code == 200
    assert ok.json()["status"] == "COMPLETED"


def test_referencia_inexistente(app_client):
    """Una referencia desconocida → 404 NOT_FOUND."""
    resp = app_client.post("/api/transfers/noexiste/mfa", json={"code": _CODE})
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


# --- E. Expiración de MFA (control de tiempo determinista) --------------------

def test_expiracion_a_cinco_minutos(app_client, isolated_db_path, monkeypatch):
    """Tras >5 min, confirmar → 409 EXPIRED, sin débito; estado EXPIRED (perezoso)."""
    before = _balances_cents(isolated_db_path)
    ref = _create_transfer(app_client, "2000000.00").json()["reference"]

    # Avanzar el reloj del servicio más allá de la ventana de 5 minutos (determinista).
    real_now = service._now_utc()
    monkeypatch.setattr(
        service, "_now_utc", lambda: real_now + timedelta(seconds=301)
    )
    resp = app_client.post(f"/api/transfers/{ref}/mfa", json={"code": _CODE})
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "EXPIRED"
    # Expiración no mueve saldos.
    assert _balances_cents(isolated_db_path) == before


def test_expirada_no_completa_con_codigo_correcto(app_client, isolated_db_path, monkeypatch):
    """Una transferencia EXPIRED no se completa ni con el código correcto."""
    ref = _create_transfer(app_client, "2000000.00").json()["reference"]
    real_now = service._now_utc()
    monkeypatch.setattr(service, "_now_utc", lambda: real_now + timedelta(seconds=600))
    # Primer intento marca EXPIRED (perezoso) y rechaza.
    r1 = app_client.post(f"/api/transfers/{ref}/mfa", json={"code": _CODE})
    assert r1.status_code == 409 and r1.json()["error"]["code"] == "EXPIRED"
    # Segundo intento (aún con reloj avanzado) sigue rechazando; estado terminal.
    r2 = app_client.post(f"/api/transfers/{ref}/mfa", json={"code": _CODE})
    assert r2.status_code == 409


# --- F. Re-verificación de fondos e idempotencia ------------------------------

def test_fondos_insuficientes_al_confirmar_marca_failed(app_client, isolated_db_path):
    """Si los fondos del origen ya no alcanzan al confirmar → 409 INSUFFICIENT_FUNDS (FAILED)."""
    # PENDING_MFA desde Savings (15M) por 2M.
    ref = _create_transfer(app_client, "2000000.00", frm="savings", to="checking").json()["reference"]

    # Simular que, entre creación y confirmación, el saldo de Savings cae por debajo del monto.
    # Se manipula SOLO la DB aislada del test (no código de producción): poner Savings en 1 centavo.
    conn = db.get_connection(isolated_db_path)
    try:
        conn.execute("UPDATE account SET balance_cents = 1 WHERE kind = 'savings'")
        conn.commit()
    finally:
        conn.close()

    resp = app_client.post(f"/api/transfers/{ref}/mfa", json={"code": _CODE})
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "INSUFFICIENT_FUNDS"
    # El saldo manipulado no cambia por el intento fallido (no se debita).
    assert _balances_cents(isolated_db_path)["Savings"] == 1


def test_confirmacion_repetida_no_debita_dos_veces(app_client, isolated_db_path):
    """Confirmar dos veces no mueve saldos por segunda vez (estado terminal tras COMPLETED)."""
    before = _balances_cents(isolated_db_path)
    ref = _create_transfer(app_client, "2000000.00").json()["reference"]
    # Primera confirmación: COMPLETED.
    r1 = app_client.post(f"/api/transfers/{ref}/mfa", json={"code": _CODE})
    assert r1.status_code == 200
    after_first = _balances_cents(isolated_db_path)
    assert after_first["Savings"] == before["Savings"] - 200_000_000
    assert after_first["Checking"] == before["Checking"] + 200_000_000

    # Segunda confirmación sobre la misma referencia: no debe debitar/acreditar de nuevo.
    r2 = app_client.post(f"/api/transfers/{ref}/mfa", json={"code": _CODE})
    assert r2.status_code != 200  # estado terminal; no vuelve a COMPLETED
    assert _balances_cents(isolated_db_path) == after_first  # saldos sin cambio adicional
