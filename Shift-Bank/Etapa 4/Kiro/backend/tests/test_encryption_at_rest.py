"""Cifrado en reposo en los bordes de E/S del repositorio (Etapa 3, Tarea 7).

Verifica el comportamiento de D-E3-01 / design.md §1.5: los identificadores bancarios sensibles
se almacenan en SQLite SOLO como tokens `enc:v1:...`, mientras la capa de servicio y las
respuestas de la API siguen viendo/retornando texto en claro (luego enmascarado) sin cambio de
contrato.

Afirmaciones clave (R1.1, R1.2, R1.3, R1.5, R1.6, R14):

1. **En reposo cifrado.** Tras crear beneficiario + ACH (guardada vía `save_adhoc` y ad hoc) +
   schedule recurrente ACH, las columnas crudas de la DB empiezan por `enc:`:
   `beneficiary.account_number`, `beneficiary.routing_number`,
   `transfer.beneficiary_snapshot`, `recurring_schedule.beneficiary_snapshot`.
2. **Sin texto plano en reposo.** Ningún valor en claro de cuenta/routing aparece en esas
   columnas (se comprueba que los dígitos sensibles NO estén presentes crudos).
3. **Contrato de API intacto.** Las respuestas siguen devolviendo la cuenta **enmascarada**
   (últimos 4) y el routing visible; el historial ACH conserva su forma exacta.

Usa el fixture `app_client` + `isolated_db_path` (DB temporal aislada; nunca toca datos
históricos ni `SEED-3.md`). El material de clave SOLO-PRUEBAS lo provee `conftest.py`.
"""

import sqlite3

import app.db as db


_VALID_BEN = {"name": "ACME SA", "bank": "Banco X",
              "routing_number": "123456789", "account_number": "9876543210"}

# Monto no sensible (< umbral) para evitar MFA en la ACH y en el schedule.
_SMALL_ACH = "250000.00"
_SMALL_REC = "50000"

_ENC_PREFIX = "enc:v1:"


def _raw_rows(path, query):
    """Lee filas CRUDAS de la DB sin pasar por los bordes de descifrado del repositorio."""
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(query).fetchall()
    finally:
        conn.close()


def test_beneficiario_cifrado_en_reposo_pero_enmascarado_en_api(app_client, isolated_db_path):
    # --- API: crear beneficiario; respuesta enmascarada sin cambio de contrato ---
    r = app_client.post("/api/beneficiaries", json=_VALID_BEN)
    assert r.status_code == 201
    body = r.json()
    assert body["account_masked"] == "••••3210"          # últimos 4 (D05)
    assert body["routing_number"] == "123456789"          # routing visible (F14)
    assert "account_number" not in body                   # nunca cuenta completa
    # El listado también enmascara igual que hoy (decrypt-on-read → public_view).
    lst = app_client.get("/api/beneficiaries").json()["beneficiaries"]
    assert len(lst) == 1 and lst[0]["account_masked"] == "••••3210"
    assert lst[0]["routing_number"] == "123456789"

    # --- En reposo: columnas sensibles son tokens enc:, sin claro ---
    rows = _raw_rows(isolated_db_path,
                     "SELECT routing_number, account_number FROM beneficiary")
    assert len(rows) == 1
    routing_raw, account_raw = rows[0]["routing_number"], rows[0]["account_number"]
    assert routing_raw.startswith(_ENC_PREFIX)
    assert account_raw.startswith(_ENC_PREFIX)
    # Ningún identificador en claro embebido en el token.
    assert _VALID_BEN["account_number"] not in account_raw
    assert _VALID_BEN["routing_number"] not in routing_raw
    # Ni siquiera ciphertext/kid revela material sensible: no debe contener los dígitos crudos.
    for token in (routing_raw, account_raw):
        assert "9876543210" not in token and "123456789" not in token


def test_ach_snapshot_cifrado_en_reposo_pero_historial_enmascarado(app_client, isolated_db_path):
    # --- API: crear ACH ad hoc guardándola como beneficiario ---
    created = app_client.post("/api/ach", json={
        "from": "savings", "amount": _SMALL_ACH, "description": "proveedor",
        "adhoc": _VALID_BEN, "save_adhoc": True})
    assert created.status_code == 201
    assert created.json()["status"] == "pending"

    # --- En reposo: snapshot de la fila transfer (ACH) es un token enc: ---
    rows = _raw_rows(isolated_db_path,
                     "SELECT beneficiary_snapshot FROM transfer WHERE type='ach'")
    assert len(rows) == 1
    snap_raw = rows[0]["beneficiary_snapshot"]
    assert snap_raw.startswith(_ENC_PREFIX)
    # El JSON en claro con la cuenta/routing NO está presente crudo en la columna.
    assert "9876543210" not in snap_raw and "123456789" not in snap_raw
    assert "account_number" not in snap_raw

    # El beneficiario guardado (save_adhoc) también quedó cifrado en reposo.
    ben_rows = _raw_rows(isolated_db_path,
                         "SELECT routing_number, account_number FROM beneficiary")
    assert len(ben_rows) == 1
    assert ben_rows[0]["routing_number"].startswith(_ENC_PREFIX)
    assert ben_rows[0]["account_number"].startswith(_ENC_PREFIX)

    # --- API: el historial descifra-al-leer y enmascara igual que hoy ---
    hist = app_client.get("/api/transfers").json()["transfers"]
    ach_items = [h for h in hist if h["type"] == "ach"]
    assert len(ach_items) == 1
    item = ach_items[0]
    assert item["beneficiary"]["account_masked"] == "••••3210"
    assert item["beneficiary"]["name"] == "ACME SA"
    assert item["beneficiary"]["bank"] == "Banco X"
    # El historial nunca expone la cuenta completa ni el token cifrado.
    assert "9876543210" not in str(item)
    assert _ENC_PREFIX not in str(item)


def test_schedule_snapshot_cifrado_en_reposo(app_client, isolated_db_path):
    # --- API: crear schedule recurrente ACH (no sensible → sin MFA) ---
    r = app_client.post("/api/recurring", json={
        "type": "ach", "amount": _SMALL_REC, "frequency": "monthly",
        "from": "checking", "adhoc": _VALID_BEN})
    assert r.status_code == 201
    assert r.json()["type"] == "ach"

    # --- En reposo: snapshot del schedule es un token enc: ---
    rows = _raw_rows(isolated_db_path,
                     "SELECT beneficiary_snapshot FROM recurring_schedule")
    assert len(rows) == 1
    snap_raw = rows[0]["beneficiary_snapshot"]
    assert snap_raw is not None and snap_raw.startswith(_ENC_PREFIX)
    assert "9876543210" not in snap_raw and "123456789" not in snap_raw

    # --- La lista de schedules sigue funcionando (decrypt-on-read) ---
    items = app_client.get("/api/recurring").json()["recurring"]
    assert len(items) == 1 and items[0]["type"] == "ach"


def test_sin_claro_en_ninguna_columna_sensible(app_client, isolated_db_path):
    """Barrido defensivo: tras un flujo completo, ninguna columna sensible contiene claro."""
    app_client.post("/api/beneficiaries", json=_VALID_BEN)
    app_client.post("/api/ach", json={
        "from": "savings", "amount": _SMALL_ACH, "adhoc": _VALID_BEN, "save_adhoc": True})
    app_client.post("/api/recurring", json={
        "type": "ach", "amount": _SMALL_REC, "frequency": "monthly",
        "from": "checking", "adhoc": _VALID_BEN})

    sensitive = ("9876543210", "123456789")

    for query in (
        "SELECT routing_number AS v FROM beneficiary",
        "SELECT account_number AS v FROM beneficiary",
        "SELECT beneficiary_snapshot AS v FROM transfer WHERE type='ach'",
        "SELECT beneficiary_snapshot AS v FROM recurring_schedule",
    ):
        for row in _raw_rows(isolated_db_path, query):
            value = row["v"]
            if value is None:
                continue
            assert value.startswith(_ENC_PREFIX), f"columna sin cifrar: {query!r} -> {value!r}"
            for digits in sensitive:
                assert digits not in value, f"claro filtrado en {query!r}"
