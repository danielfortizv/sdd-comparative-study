"""Pruebas de los endpoints de pagos recurrentes (Etapa 2, Fase E, Tarea 33).

Cubren el router `routers/recurring.py` a nivel HTTP (vía `TestClient`):

- `GET /api/recurring`: lista los schedules del cliente con su estado y su **próxima fecha de
  vencimiento** (Req. 12.1); refleja los cambios de estado tras las acciones de ciclo de vida.
- `POST /api/recurring`: crea un schedule interno y uno ACH; exige MFA en montos sensibles y
  rechaza la creación sin autorización; mapea validaciones a 400 y MFA a 401 (Req. 8.x, REC-09).
- `POST /api/recurring/{id}/pause|resume|cancel`: transiciones de ciclo de vida y su mapeo HTTP
  (transición ilegal → 409, schedule inexistente → 404) (Req. 9, 12.2).

Se usa el cliente de la app (`app_client`) atado a una DB aislada por el fixture compartido.

_Requisitos: 12.1, 12.2_ · _Contrato: REC-12_
"""

import pytest

_CODE = "123456"
_VALID_BEN = {"name": "ACME SA", "bank": "Banco X",
              "routing_number": "123456789", "account_number": "9876543210"}

# Monto no sensible (< umbral de 1.000.000) y sensible (>= umbral).
_SMALL = "50000"
_SENSITIVE = "1000000"


def _create_internal(client, **overrides):
    body = {"type": "internal", "amount": _SMALL, "frequency": "weekly",
            "from": "checking", "to": "savings"}
    body.update(overrides)
    return client.post("/api/recurring", json=body)


# --- GET /api/recurring --------------------------------------------------------

def test_lista_vacia_inicialmente(app_client):
    r = app_client.get("/api/recurring")
    assert r.status_code == 200
    assert r.json() == {"recurring": []}


def test_crear_y_listar_estado_y_proxima_fecha(app_client):
    """REC-12 / Req. 12.1: la lista expone estado + próxima fecha de vencimiento."""
    created = _create_internal(app_client)
    assert created.status_code == 201
    sid = created.json()["id"]

    items = app_client.get("/api/recurring").json()["recurring"]
    assert len(items) == 1
    item = items[0]
    assert item["id"] == sid
    assert item["type"] == "internal"
    assert item["status"] == "active"              # estado inicial (REC-03)
    assert item["frequency"] == "weekly"
    assert item["next_run_at"]                      # próxima fecha presente (ISO-8601)
    assert "T" in item["next_run_at"] and item["next_run_at"].endswith("Z")


# --- POST /api/recurring: creación ---------------------------------------------

def test_crear_interno_201(app_client):
    r = _create_internal(app_client)
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "active"
    assert body["type"] == "internal"
    assert body["requires_mfa"] is False
    assert body["authorized"] is True


def test_crear_ach_con_adhoc_201(app_client):
    r = app_client.post("/api/recurring", json={
        "type": "ach", "amount": _SMALL, "frequency": "monthly",
        "from": "checking", "adhoc": _VALID_BEN})
    assert r.status_code == 201
    assert r.json()["type"] == "ach"


def test_crear_sensible_sin_mfa_rechazado_401(app_client):
    """REC-09 / Req. 8.6: monto sensible sin MFA → 401 y NO se persiste."""
    r = _create_internal(app_client, amount=_SENSITIVE)
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "MFA_REQUIRED"
    # No se persiste un schedule sensible no autorizado.
    assert app_client.get("/api/recurring").json()["recurring"] == []


def test_crear_sensible_mfa_incorrecta_401(app_client):
    r = _create_internal(app_client, amount=_SENSITIVE, mfa_code="000000")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "INVALID_MFA_CODE"


def test_crear_sensible_con_mfa_201(app_client):
    r = _create_internal(app_client, amount=_SENSITIVE, mfa_code=_CODE)
    assert r.status_code == 201
    body = r.json()
    assert body["requires_mfa"] is True
    assert body["authorized"] is True


def test_crear_frecuencia_invalida_400(app_client):
    r = _create_internal(app_client, frequency="hourly")
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_FREQUENCY"


def test_crear_destino_igual_origen_400(app_client):
    r = _create_internal(app_client, to="checking")
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_DESTINATION"


# --- Ciclo de vida: pause / resume / cancel (Req. 9, 12.2) ---------------------

def test_pause_resume_actualiza_estado(app_client):
    sid = _create_internal(app_client).json()["id"]

    r = app_client.post(f"/api/recurring/{sid}/pause")
    assert r.status_code == 200 and r.json()["status"] == "paused"
    assert app_client.get("/api/recurring").json()["recurring"][0]["status"] == "paused"

    r = app_client.post(f"/api/recurring/{sid}/resume")
    assert r.status_code == 200 and r.json()["status"] == "active"
    assert app_client.get("/api/recurring").json()["recurring"][0]["status"] == "active"


def test_cancel_terminal(app_client):
    sid = _create_internal(app_client).json()["id"]
    r = app_client.post(f"/api/recurring/{sid}/cancel")
    assert r.status_code == 200 and r.json()["status"] == "cancelled"
    # Cancelar de nuevo es una transición ilegal → 409.
    r2 = app_client.post(f"/api/recurring/{sid}/cancel")
    assert r2.status_code == 409
    assert r2.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


def test_pause_cancelled_transicion_ilegal_409(app_client):
    sid = _create_internal(app_client).json()["id"]
    app_client.post(f"/api/recurring/{sid}/cancel")
    r = app_client.post(f"/api/recurring/{sid}/pause")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


def test_resume_activo_transicion_ilegal_409(app_client):
    sid = _create_internal(app_client).json()["id"]
    r = app_client.post(f"/api/recurring/{sid}/resume")  # ya está active
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


def test_accion_sobre_schedule_inexistente_404(app_client):
    for action in ("pause", "resume", "cancel"):
        r = app_client.post(f"/api/recurring/does-not-exist/{action}")
        assert r.status_code == 404
        assert r.json()["error"]["code"] == "NOT_FOUND"
