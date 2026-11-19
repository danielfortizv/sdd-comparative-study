"""Aceptación T14: MFA en equivalente USD en los endpoints v2 reales (D-07), fixture D-02.

Verifica el flujo real pending/confirmación y el comportamiento de frontera: el umbral es el
equivalente USD SIN redondear estrictamente > USD 1,000.00. 1000.00 USD exacto NO pide MFA y se
aplica; 1000.01 USD pide MFA (PENDING_MFA) sin mover saldo; confirmar con el código correcto
aplica; código incorrecto -> 401 sin mover saldo.

_Requisitos: R11_ · _Diseño: §3.2, §3.5_ · _AC: AC4-17_
"""

import uuid


def _accounts(client):
    return {a["public_id"]: a for a in client.get("/api/v2/accounts").json()["accounts"]}


def _key():
    return {"Idempotency-Key": str(uuid.uuid4())}


def test_frontera_1000_exacto_no_pide_mfa(stage4_app_client):
    c = stage4_app_client
    # 1000.00 USD exacto: equivalente USD sin redondear == 1000.00 -> NO MFA (estricto >).
    r = c.post("/api/v2/transfers", headers=_key(),
               json={"from": "SAV-2001", "to": "CHK-1001", "amount": "1000.00"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "COMPLETED"
    accs = _accounts(c)
    assert accs["SAV-2001"]["balance"] == "9000.00"  # se aplicó


def test_frontera_1000_01_pide_mfa_y_no_mueve_saldo(stage4_app_client):
    c = stage4_app_client
    before = _accounts(c)
    r = c.post("/api/v2/transfers", headers=_key(),
               json={"from": "SAV-2001", "to": "CHK-1001", "amount": "1000.01"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "PENDING_MFA" and body["mfa_required"] is True
    assert "reference" in body
    after = _accounts(c)
    # Sin movimiento de saldo hasta confirmar.
    assert after["SAV-2001"]["balance"] == before["SAV-2001"]["balance"]


def test_confirmacion_mfa_aplica(stage4_app_client):
    c = stage4_app_client
    r = c.post("/api/v2/transfers", headers=_key(),
               json={"from": "SAV-2001", "to": "CHK-1001", "amount": "1500.00"})
    ref = r.json()["reference"]
    # Código correcto -> COMPLETED y saldo movido.
    r2 = c.post(f"/api/v2/mfa/{ref}", json={"code": "123456"})
    assert r2.status_code == 200, r2.text
    assert r2.json()["status"] == "COMPLETED"
    accs = _accounts(c)
    assert accs["SAV-2001"]["balance"] == "8500.00"


def test_confirmacion_codigo_incorrecto_401_sin_mover_saldo(stage4_app_client):
    c = stage4_app_client
    r = c.post("/api/v2/transfers", headers=_key(),
               json={"from": "SAV-2001", "to": "CHK-1001", "amount": "1500.00"})
    ref = r.json()["reference"]
    before = _accounts(c)
    r2 = c.post(f"/api/v2/mfa/{ref}", json={"code": "000000"})
    assert r2.status_code == 401
    assert r2.json()["error"]["code"] == "INVALID_MFA_CODE"
    after = _accounts(c)
    assert after["SAV-2001"]["balance"] == before["SAV-2001"]["balance"]


def test_conversion_alto_valor_pide_mfa(stage4_app_client):
    c = stage4_app_client
    # 1500.00 USD -> EUR: equivalente USD = 1500.00 > 1000 -> MFA.
    r = c.post("/api/conversions", headers=_key(),
               json={"from": "SAV-2001", "to": "EUR-3001", "amount": "1500.00"})
    assert r.status_code == 200
    assert r.json()["status"] == "PENDING_MFA"
    ref = r.json()["reference"]
    r2 = c.post(f"/api/v2/mfa/{ref}", json={"code": "123456"})
    assert r2.status_code == 200
    body = r2.json()
    assert body["status"] == "COMPLETED"
    # 1500 USD * 9/10 = 1350.00 EUR.
    assert body["to"]["amount"] == "1350.00" and body["to"]["currency"] == "EUR"


def test_conversion_gbp_frontera_sin_redondear(stage4_app_client):
    c = stage4_app_client
    # 800.00 GBP == 1000.00 USD exacto -> NO MFA. Pero GBP-4001 tiene saldo 0; usar origen USD.
    # 800.01 USD -> no supera 1000; probamos 1000.00 USD->GBP (==1000 USD) sin MFA.
    r = c.post("/api/conversions", headers=_key(),
               json={"from": "SAV-2001", "to": "GBP-4001", "amount": "1000.00"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "COMPLETED"  # exactamente 1000 USD no pide MFA
