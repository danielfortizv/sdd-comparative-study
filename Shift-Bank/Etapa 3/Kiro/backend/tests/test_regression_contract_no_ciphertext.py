"""Regresión Etapa 3 (Tarea 17) — contratos de API intactos con cifrado+auditoría activos.

Prueba ADITIVA y SOLO-LECTURA (no modifica código de aplicación). Confirma que, con el cifrado
en reposo (Tarea 7) y la auditoría transaccional (Tareas 12–13) activos, los contratos públicos
heredados (Etapas 1/2) se preservan sin cambios de forma:

- `GET /api/beneficiaries`: cuenta **enmascarada** (`account_masked`, últimos 4) y routing en
  claro; NUNCA el número de cuenta completo.
- `GET /api/transfers`: entradas ACH conservan su forma (type/date/amount/status/beneficiary con
  cuenta enmascarada); internas mantienen `direction {from,to}` con estados en MAYÚSCULAS.
- En NINGUNA de las dos respuestas aparece texto cifrado (`enc:v1:`), material de clave ni
  identificadores internos (p. ej. columnas `_kind`, `customer_id`, `rowid`, `snapshot`).

Fuente del comportamiento esperado: `routers/beneficiaries.py`, `routers/transfers.py`,
`beneficiaries.public_view`.

_Requisitos: R14.1, R14.2, R14.3, R14.4_ · _Diseño: §12, §1.5_ · _AC: AC-01_
"""

import json

_CODE = "123456"
_VALID_BEN = {"name": "ACME SA", "bank": "Banco X",
              "routing_number": "123456789", "account_number": "9876543210"}

# Tokens/campos que jamás deben aparecer en las respuestas públicas.
_CIPHERTEXT_PREFIX = "enc:v1:"
_FULL_ACCOUNT = _VALID_BEN["account_number"]           # 9876543210 (nunca completo en API)
_FORBIDDEN_INTERNAL_KEYS = {
    "beneficiary_snapshot", "snapshot", "customer_id", "rowid", "id_", "from_kind", "to_kind",
    "balance_cents", "amount_cents", "entry_hmac", "prev_hmac",
}


def _seed_mixed_activity(app_client):
    """Crea un beneficiario + un ACH (snapshot cifrado en reposo) + una transferencia interna."""
    # Beneficiario (cuenta/routing se cifran en reposo en la DB).
    bid = app_client.post("/api/beneficiaries", json=_VALID_BEN).json()["id"]
    # ACH ad-hoc bajo umbral → pending con débito y snapshot cifrado persistido.
    ach = app_client.post("/api/ach", json={
        "from": "savings", "amount": "1000.00", "description": "proveedor", "adhoc": _VALID_BEN})
    assert ach.status_code == 201
    # Transferencia interna bajo umbral → COMPLETED (estado MAYÚSCULAS heredado).
    tr = app_client.post("/api/transfers", json={
        "from": "checking", "to": "savings", "amount": "1000.00", "description": "x"})
    assert tr.status_code == 201
    return bid


def _assert_no_ciphertext(blob: str, where: str):
    assert _CIPHERTEXT_PREFIX not in blob, f"texto cifrado filtrado en {where}"
    assert _FULL_ACCOUNT not in blob, f"número de cuenta completo filtrado en {where}"


def test_beneficiaries_sin_ciphertext_cuenta_enmascarada(app_client):
    _seed_mixed_activity(app_client)

    resp = app_client.get("/api/beneficiaries")
    assert resp.status_code == 200
    body = resp.json()
    raw = json.dumps(body)

    # Sin ciphertext ni cuenta completa en el JSON serializado.
    _assert_no_ciphertext(raw, "GET /api/beneficiaries")

    ben = body["beneficiaries"]
    assert len(ben) == 1
    item = ben[0]
    # Forma heredada: cuenta enmascarada (últimos 4) + routing en claro; sin cuenta completa.
    assert item["account_masked"] == "••••3210"
    assert item["routing_number"] == "123456789"
    assert "account_number" not in item
    # Sin claves internas filtradas.
    assert _FORBIDDEN_INTERNAL_KEYS.isdisjoint(item.keys())


def test_transfers_history_sin_ciphertext_forma_heredada(app_client):
    _seed_mixed_activity(app_client)

    resp = app_client.get("/api/transfers")
    assert resp.status_code == 200
    body = resp.json()
    raw = json.dumps(body)

    # Sin ciphertext ni cuenta completa en el JSON serializado del historial.
    _assert_no_ciphertext(raw, "GET /api/transfers")

    items = body["transfers"]
    assert items, "el historial debe contener las entradas sembradas"

    internal = [i for i in items if i["type"] == "internal"]
    ach = [i for i in items if i["type"] == "ach"]
    assert internal and ach, "deben coexistir entradas internas y ACH"

    # Internas: estados en MAYÚSCULAS y `direction {from,to}` con nombres amigables.
    for it in internal:
        assert it["status"] == it["status"].upper()
        assert set(it["direction"].keys()) == {"from", "to"}
        assert _FORBIDDEN_INTERNAL_KEYS.isdisjoint(it.keys())

    # ACH: beneficiario con cuenta enmascarada; sin snapshot/ciphertext/cuenta completa.
    for it in ach:
        masked = it["beneficiary"]["account_masked"]
        assert masked.startswith("••••") and masked.endswith("3210")
        assert _CIPHERTEXT_PREFIX not in json.dumps(it["beneficiary"])
        assert _FORBIDDEN_INTERNAL_KEYS.isdisjoint(it.keys())


def test_db_guarda_ciphertext_pero_api_no(app_client, isolated_db_path):
    """Contraparte: en la DB el snapshot ACH es `enc:v1:...`, pero la API lo descifra+enmascara."""
    import app.db as db

    _seed_mixed_activity(app_client)

    conn = db.get_connection(isolated_db_path)
    try:
        snap = conn.execute(
            "SELECT beneficiary_snapshot FROM transfer WHERE type='ach' "
            "AND beneficiary_snapshot IS NOT NULL LIMIT 1").fetchone()
    finally:
        conn.close()
    assert snap is not None
    # En reposo: token cifrado versionado.
    assert str(snap["beneficiary_snapshot"]).startswith(_CIPHERTEXT_PREFIX)

    # En la API: sin rastro del token.
    assert _CIPHERTEXT_PREFIX not in app_client.get("/api/transfers").text
    assert _CIPHERTEXT_PREFIX not in app_client.get("/api/beneficiaries").text
