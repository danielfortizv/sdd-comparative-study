"""Aceptación de la Etapa 4 sobre la fixture D-02 (T12/T13/T14): conversiones, internas
misma-moneda, idempotencia/versión por HTTP y límites en equivalente USD.

Usa `stage4_app_client` (fixture D-02 real), según la condición del investigador: la aceptación de
la Etapa 4 se prueba con la fixture multidivisa, no con la heredada.

_Requisitos: R3, R4, R5, R9, R10, R11_ · _Diseño: §3.2, §3.3, §3.5_ · _AC: AC4-05, AC4-06, AC4-07,
AC4-13, AC4-15, AC4-17_
"""

import uuid


def _accounts(client):
    r = client.get("/api/v2/accounts")
    assert r.status_code == 200
    return {a["public_id"]: a for a in r.json()["accounts"]}


def test_listado_v2_multidivisa(stage4_app_client):
    accs = _accounts(stage4_app_client)
    assert set(accs) == {"CHK-1001", "SAV-2001", "EUR-3001", "GBP-4001"}
    assert accs["CHK-1001"]["currency"] == "USD"
    assert accs["CHK-1001"]["balance"] == "2500.00"
    assert accs["EUR-3001"]["currency"] == "EUR"


def test_conversion_usd_a_eur(stage4_app_client):
    c = stage4_app_client
    r = c.post("/api/conversions",
               headers={"Idempotency-Key": str(uuid.uuid4())},
               json={"from": "CHK-1001", "to": "EUR-3001", "amount": "100.00"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["rate"] == "9/10"
    assert body["from"]["amount"] == "100.00" and body["from"]["currency"] == "USD"
    assert body["to"]["amount"] == "90.00" and body["to"]["currency"] == "EUR"
    accs = _accounts(c)
    assert accs["CHK-1001"]["balance"] == "2400.00"
    assert accs["EUR-3001"]["balance"] == "90.00"


def test_transferencia_interna_misma_moneda(stage4_app_client):
    c = stage4_app_client
    r = c.post("/api/v2/transfers",
               headers={"Idempotency-Key": str(uuid.uuid4())},
               json={"from": "CHK-1001", "to": "SAV-2001", "amount": "500.00"})
    assert r.status_code == 200, r.text
    accs = _accounts(c)
    assert accs["CHK-1001"]["balance"] == "2000.00"
    assert accs["SAV-2001"]["balance"] == "10500.00"


def test_transferencia_interna_cross_currency_rechazada(stage4_app_client):
    c = stage4_app_client
    r = c.post("/api/v2/transfers",
               headers={"Idempotency-Key": str(uuid.uuid4())},
               json={"from": "CHK-1001", "to": "EUR-3001", "amount": "10.00"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "CROSS_CURRENCY_NOT_ALLOWED"


def test_idempotencia_replay_por_http(stage4_app_client):
    c = stage4_app_client
    key = str(uuid.uuid4())
    payload = {"from": "CHK-1001", "to": "SAV-2001", "amount": "100.00"}
    r1 = c.post("/api/v2/transfers", headers={"Idempotency-Key": key}, json=payload)
    r2 = c.post("/api/v2/transfers", headers={"Idempotency-Key": key}, json=payload)
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json() == r2.json()  # misma respuesta
    accs = _accounts(c)
    assert accs["CHK-1001"]["balance"] == "2400.00"  # un solo débito


def test_idempotencia_payload_distinto_409(stage4_app_client):
    c = stage4_app_client
    key = str(uuid.uuid4())
    c.post("/api/v2/transfers", headers={"Idempotency-Key": key},
           json={"from": "CHK-1001", "to": "SAV-2001", "amount": "100.00"})
    r = c.post("/api/v2/transfers", headers={"Idempotency-Key": key},
               json={"from": "CHK-1001", "to": "SAV-2001", "amount": "200.00"})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"


def test_idempotency_key_requerida(stage4_app_client):
    c = stage4_app_client
    r = c.post("/api/v2/transfers",
               json={"from": "CHK-1001", "to": "SAV-2001", "amount": "100.00"})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"


def test_version_conflict_409(stage4_app_client):
    c = stage4_app_client
    # Esperar versión 0 (incorrecta; la inicial es 1) -> conflicto.
    r = c.post("/api/v2/transfers",
               headers={"Idempotency-Key": str(uuid.uuid4()),
                        "Expected-Version": '{"CHK-1001": 0, "SAV-2001": 0}'},
               json={"from": "CHK-1001", "to": "SAV-2001", "amount": "100.00"})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "ACCOUNT_VERSION_CONFLICT"


def test_limite_por_operacion_usd(stage4_app_client):
    c = stage4_app_client
    # SAV-2001 tiene 10000 USD; 6000 USD supera el límite por operación (5000 USD).
    r = c.post("/api/v2/transfers",
               headers={"Idempotency-Key": str(uuid.uuid4())},
               json={"from": "SAV-2001", "to": "CHK-1001", "amount": "6000.00"})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "LIMIT_EXCEEDED_PER_TRANSFER"


def test_fondos_insuficientes(stage4_app_client):
    c = stage4_app_client
    r = c.post("/api/v2/transfers",
               headers={"Idempotency-Key": str(uuid.uuid4())},
               json={"from": "EUR-3001", "to": "EUR-3001", "amount": "10.00"})
    # misma cuenta -> 400 SAME_ACCOUNT (se valida antes que fondos)
    assert r.status_code == 400
