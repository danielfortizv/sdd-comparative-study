"""Regresión Etapa 1 — Contratos de API, historial y errores públicos (Tarea 5).

Fija los INVARIANTES de contrato observables de la Etapa 1 (formas de respuesta, códigos HTTP,
estructura de error, formato e orden del historial, no exposición de identificadores internos),
como base de compatibilidad para los cambios de la Etapa 2. No duplica exhaustivamente las
tareas 2–4: se centra en los invariantes de contrato más amplios y en la preservación del
contrato de internas de cara al futuro historial unificado con ACH.

Prueba el contrato REAL de la Etapa 1; NO introduce campos ni estados específicos de ACH en las
expectativas heredadas.

Fuente del comportamiento esperado (código heredado real):
- `routers/accounts.py`, `routers/transfers.py`, `schemas.py`, `repository.list_transfers`
  (orden `created_at DESC, rowid DESC`), `seed.py` (2 históricas en el pasado).
- Creación → 201 (COMPLETED y PENDING_MFA). Errores → `{error:{code,message}}`.
- `TransferDirection` serializa el campo como `from` (alias de salida).

_Requisitos: 15.1, 15.5_ · _Contrato: HER-01; A01_
"""

import app.db as db

_CODE = "123456"


def _hist(client):
    return client.get("/api/transfers").json()["transfers"]


# --- A. Compatibilidad del contrato público -----------------------------------

def test_contrato_get_accounts(app_client):
    """`GET /api/accounts` → 200 con `{accounts:[{name,balance}]}` (solo esos campos)."""
    resp = app_client.get("/api/accounts")
    assert resp.status_code == 200
    data = resp.json()
    assert list(data.keys()) == ["accounts"]
    for a in data["accounts"]:
        assert set(a.keys()) == {"name", "balance"}


def test_contrato_creacion_sin_mfa(app_client):
    """Creación < umbral → 201 con `{status:"COMPLETED", mfa_required:false}` (sin reference)."""
    resp = app_client.post(
        "/api/transfers",
        json={"from": "checking", "to": "savings", "amount": "1000.00", "description": "x"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "COMPLETED"
    assert body["mfa_required"] is False
    # reference/expires_at presentes como null (campos del schema), no requeridos para el caso.
    assert body.get("reference") in (None,)
    assert body.get("expires_at") in (None,)


def test_contrato_creacion_con_mfa(app_client):
    """Creación >= umbral → 201 con status PENDING_MFA, mfa_required true, reference y expires_at."""
    resp = app_client.post(
        "/api/transfers",
        json={"from": "savings", "to": "checking", "amount": "1000000.00", "description": "x"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "PENDING_MFA"
    assert body["mfa_required"] is True
    assert isinstance(body["reference"], str) and body["reference"]
    assert isinstance(body["expires_at"], str) and body["expires_at"].endswith("Z")


def test_contrato_confirmacion_mfa(app_client):
    """`POST /api/transfers/{ref}/mfa` correcto → 200 con `{status:"COMPLETED"}`."""
    ref = app_client.post(
        "/api/transfers",
        json={"from": "savings", "to": "checking", "amount": "1000000.00", "description": "x"},
    ).json()["reference"]
    resp = app_client.post(f"/api/transfers/{ref}/mfa", json={"code": _CODE})
    assert resp.status_code == 200
    assert resp.json() == {"status": "COMPLETED"}


# --- B. Historial --------------------------------------------------------------

def test_historial_estructura_y_campos(app_client):
    """Cada entrada interna conserva los campos heredados (más el campo aditivo `type`, D03/D05).

    Actualizado en la Tarea 25: la extensión aditiva añade `type` a cada entrada. Se verifica
    que los campos HEREDADOS de una entrada interna siguen presentes con su forma (no se
    renombran ni eliminan); `type` es un añadido aprobado, no una regresión.
    """
    for t in _hist(app_client):
        # Los 5 campos heredados siguen presentes.
        assert {"date", "direction", "amount", "description", "status"}.issubset(t.keys())
        # El único campo nuevo permitido es `type` (extensión aditiva aprobada).
        assert set(t.keys()) <= {"date", "direction", "amount", "description", "status", "type"}
        assert t["type"] == "internal"
        assert set(t["direction"].keys()) == {"from", "to"}
        assert t["direction"]["from"] in {"Checking", "Savings"}
        assert t["direction"]["to"] in {"Checking", "Savings"}
        assert isinstance(t["amount"], str)
        assert t["status"] == t["status"].upper()  # MAYÚSCULAS heredadas


def test_historial_historicas_y_nueva(app_client):
    """Las 2 históricas persisten y una nueva COMPLETED se añade al historial."""
    inicial = _hist(app_client)
    assert len(inicial) == 2
    app_client.post(
        "/api/transfers",
        json={"from": "checking", "to": "savings", "amount": "5000.00", "description": "nueva"},
    )
    despues = _hist(app_client)
    assert len(despues) == 3
    assert any(t["description"] == "nueva" and t["status"] == "COMPLETED" for t in despues)


def test_historial_pending_observable(app_client):
    """Una transferencia PENDING_MFA es observable en el historial con ese estado."""
    app_client.post(
        "/api/transfers",
        json={"from": "savings", "to": "checking", "amount": "1500000.00",
              "description": "pend"},
    )
    pend = [t for t in _hist(app_client) if t["description"] == "pend"]
    assert len(pend) == 1 and pend[0]["status"] == "PENDING_MFA"


def test_historial_orden_desc_por_fecha(app_client):
    """El historial se ordena por fecha descendente: la nueva aparece primero."""
    app_client.post(
        "/api/transfers",
        json={"from": "checking", "to": "savings", "amount": "7000.00", "description": "reciente"},
    )
    hist = _hist(app_client)
    # La transferencia recién creada (created_at = now) precede a las históricas (en el pasado).
    assert hist[0]["description"] == "reciente"
    # Fechas monótonas no crecientes.
    fechas = [t["date"] for t in hist]
    assert fechas == sorted(fechas, reverse=True)


def test_historial_sin_identificadores_internos(app_client):
    """El historial no expone IDs internos, UUID, references ni `kind`."""
    import json

    app_client.post(
        "/api/transfers",
        json={"from": "savings", "to": "checking", "amount": "1000000.00", "description": "p"},
    )
    raw = json.dumps(_hist(app_client))
    for forbidden in ("\"id\"", "uuid", "reference", "customer_id", "\"kind\"", "requires_mfa",
                      "expires_at", "completed_at"):
        assert forbidden not in raw


def test_historial_montos_decimal_string_2_decimales(app_client):
    """Los montos del historial son cadenas decimales con 2 decimales."""
    for t in _hist(app_client):
        assert "." in t["amount"] and len(t["amount"].split(".")[1]) == 2


# --- C. Contratos de error -----------------------------------------------------

def test_estructura_de_error_publica(app_client):
    """Los errores usan la forma `{error:{code,message}}` con tipos correctos."""
    resp = app_client.post(
        "/api/transfers",
        json={"from": "checking", "to": "checking", "amount": "1.00", "description": ""},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert set(body.keys()) == {"error"}
    assert set(body["error"].keys()) == {"code", "message"}
    assert isinstance(body["error"]["code"], str)
    assert isinstance(body["error"]["message"], str)


def test_codigos_y_http_de_errores_representativos(app_client, isolated_db_path):
    """Códigos y HTTP heredados para casos representativos; sin cambios financieros."""
    conn = db.get_connection(isolated_db_path)
    try:
        before = conn.execute("SELECT kind, balance_cents FROM account").fetchall()
        before_map = {r["kind"]: r["balance_cents"] for r in before}
    finally:
        conn.close()

    casos = [
        ({"from": "checking", "to": "checking", "amount": "1.00"}, 400, "SAME_ACCOUNT"),
        ({"from": "checking", "to": "savings", "amount": "0.00"}, 400, "NON_POSITIVE_AMOUNT"),
        ({"from": "checking", "to": "savings", "amount": "1.001"}, 400, "INVALID_AMOUNT"),
    ]
    for payload, status, code in casos:
        resp = app_client.post("/api/transfers", json={**payload, "description": ""})
        assert resp.status_code == status
        assert resp.json()["error"]["code"] == code

    # MFA con código incorrecto → 401 INVALID_MFA_CODE.
    ref = app_client.post(
        "/api/transfers",
        json={"from": "savings", "to": "checking", "amount": "1000000.00", "description": ""},
    ).json()["reference"]
    bad = app_client.post(f"/api/transfers/{ref}/mfa", json={"code": "000000"})
    assert bad.status_code == 401 and bad.json()["error"]["code"] == "INVALID_MFA_CODE"

    # Referencia inexistente → 404 NOT_FOUND.
    nf = app_client.post("/api/transfers/nope/mfa", json={"code": _CODE})
    assert nf.status_code == 404 and nf.json()["error"]["code"] == "NOT_FOUND"

    # Ninguno de los errores anteriores movió saldos (los rechazos y el PENDING_MFA no debitan).
    conn = db.get_connection(isolated_db_path)
    try:
        after = conn.execute("SELECT kind, balance_cents FROM account").fetchall()
        after_map = {r["kind"]: r["balance_cents"] for r in after}
    finally:
        conn.close()
    assert after_map == before_map


# --- D. Preservación del contrato de internas (base para historial unificado) --

def test_internas_conservan_forma_sin_beneficiario(app_client):
    """Las entradas internas conservan su forma heredada y NO llevan `beneficiary` (solo las ACH).

    Actualizado en la Tarea 25: se admite el campo aditivo `type='internal'` (D03/D05), pero las
    internas siguen SIN `beneficiary` y conservan `direction {from,to}`. Esto preserva el
    contrato heredado de las internas mientras habilita la extensión ACH aditiva.
    """
    app_client.post(
        "/api/transfers",
        json={"from": "checking", "to": "savings", "amount": "2000.00", "description": "i"},
    )
    for t in _hist(app_client):
        assert t.get("type") == "internal"
        assert "beneficiary" not in t          # el beneficiario solo aparece en entradas ACH
        assert "direction" in t                # forma heredada preservada
        assert set(t.keys()) == {"date", "direction", "amount", "description", "status", "type"}
