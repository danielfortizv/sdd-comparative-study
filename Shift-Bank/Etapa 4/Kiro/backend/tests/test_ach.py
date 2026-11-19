"""Pruebas de beneficiarios y transferencias ACH (Etapa 2, Fase D: Tarea 26).

Cubren: validación/propiedad/enmascarado de beneficiarios; validación ACH; MFA; atomicidad
financiera (débito con `pending`, nunca `pending` sin débito); `pending_auth` sin débito;
settlement idempotente; fallo con reembolso exactamente-una-vez; límites; historial unificado
y compatibilidad; retry.

Usa fixtures aislados y las utilidades existentes. Para settlement/fallo deterministas se usa
el reloj inyectable (avanzando el instante de `settle_ach`).

_Requisitos: 1–7_ · _Contrato: ACH-01..10; A03–A09_
"""

from datetime import datetime, timedelta, timezone

import pytest

import app.ach_repository as ach_repo
import app.ach_service as ach_service
import app.db as db


_CODE = "123456"
_VALID_BEN = {"name": "ACME SA", "bank": "Banco X",
              "routing_number": "123456789", "account_number": "9876543210"}


def _savings_cents(path):
    conn = db.get_connection(path)
    try:
        return conn.execute(
            "SELECT balance_cents FROM account WHERE kind='savings'").fetchone()["balance_cents"]
    finally:
        conn.close()


# --- Beneficiarios -------------------------------------------------------------

def test_crear_y_listar_beneficiario_enmascarado(app_client):
    r = app_client.post("/api/beneficiaries", json=_VALID_BEN)
    assert r.status_code == 201
    body = r.json()
    assert body["account_masked"] == "••••3210"
    assert "account_number" not in body            # no se expone completo
    assert body["routing_number"] == "123456789"   # routing no enmascarado (F14)
    lst = app_client.get("/api/beneficiaries").json()["beneficiaries"]
    assert len(lst) == 1 and lst[0]["account_masked"] == "••••3210"


def test_validacion_routing(app_client):
    for bad in ("12345678", "1234567890", "12345678a"):
        r = app_client.post("/api/beneficiaries", json={**_VALID_BEN, "routing_number": bad})
        assert r.status_code == 400 and r.json()["error"]["code"] == "INVALID_ROUTING"
    # 9 dígitos válido.
    assert app_client.post("/api/beneficiaries",
                           json={**_VALID_BEN, "routing_number": "000000000"}).status_code == 201


def test_validacion_cuenta(app_client):
    for bad in ("123", "123456789012345678", "12ab"):
        r = app_client.post("/api/beneficiaries", json={**_VALID_BEN, "account_number": bad})
        assert r.status_code == 400 and r.json()["error"]["code"] == "INVALID_ACCOUNT_NUMBER"
    for ok in ("1234", "12345678901234567"):
        assert app_client.post("/api/beneficiaries",
                               json={**_VALID_BEN, "account_number": ok}).status_code == 201


def test_borrado_logico_beneficiario(app_client):
    bid = app_client.post("/api/beneficiaries", json=_VALID_BEN).json()["id"]
    assert app_client.delete(f"/api/beneficiaries/{bid}").status_code == 200
    assert app_client.get("/api/beneficiaries").json()["beneficiaries"] == []
    # Doble borrado → 404.
    assert app_client.delete(f"/api/beneficiaries/{bid}").status_code == 404


# --- ACH: creación, débito atómico, pending_auth -------------------------------

def test_ach_bajo_umbral_pending_y_debita(app_client, isolated_db_path):
    before = _savings_cents(isolated_db_path)
    r = app_client.post("/api/ach", json={
        "from": "savings", "amount": "250000.00", "description": "proveedor", "adhoc": _VALID_BEN})
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "pending" and body["mfa_required"] is False
    # Débito inmediato (250.000,00 = 25.000.000 centavos).
    assert _savings_cents(isolated_db_path) == before - 25_000_000


def test_ach_sensible_pending_auth_sin_debito(app_client, isolated_db_path):
    before = _savings_cents(isolated_db_path)
    r = app_client.post("/api/ach", json={
        "from": "savings", "amount": "2000000.00", "description": "grande", "adhoc": _VALID_BEN})
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "pending_auth" and body["mfa_required"] is True
    assert body["reference"] and body["expires_at"]
    # SIN débito hasta confirmar MFA.
    assert _savings_cents(isolated_db_path) == before


def test_ach_confirmacion_mfa_activa_y_debita(app_client, isolated_db_path):
    before = _savings_cents(isolated_db_path)
    ref = app_client.post("/api/ach", json={
        "from": "savings", "amount": "2000000.00", "adhoc": _VALID_BEN}).json()["reference"]
    # Código incorrecto: sigue pending_auth, sin débito.
    bad = app_client.post(f"/api/ach/{ref}/mfa", json={"code": "000000"})
    assert bad.status_code == 401 and bad.json()["error"]["code"] == "INVALID_MFA_CODE"
    assert _savings_cents(isolated_db_path) == before
    # Código correcto: pending + débito.
    ok = app_client.post(f"/api/ach/{ref}/mfa", json={"code": _CODE})
    assert ok.status_code == 200 and ok.json()["status"] == "pending"
    assert _savings_cents(isolated_db_path) == before - 200_000_000


def test_ach_rechaza_monto_invalido(app_client):
    for amt, code in [("0.00", "NON_POSITIVE_AMOUNT"), ("-1.00", "NON_POSITIVE_AMOUNT"),
                      ("1.001", "INVALID_AMOUNT")]:
        r = app_client.post("/api/ach", json={"amount": amt, "adhoc": _VALID_BEN})
        assert r.status_code == 400 and r.json()["error"]["code"] == code


def test_ach_beneficiario_guardado(app_client):
    bid = app_client.post("/api/beneficiaries", json=_VALID_BEN).json()["id"]
    r = app_client.post("/api/ach", json={
        "from": "checking", "amount": "1000.00", "beneficiary_id": bid})
    assert r.status_code == 201 and r.json()["status"] == "pending"


def test_ach_guardar_adhoc_en_la_operacion(app_client):
    r = app_client.post("/api/ach", json={
        "from": "checking", "amount": "1000.00", "adhoc": _VALID_BEN, "save_adhoc": True})
    assert r.status_code == 201
    # El beneficiario quedó guardado.
    assert len(app_client.get("/api/beneficiaries").json()["beneficiaries"]) == 1


# --- Settlement e idempotencia (lógica; disparo autónomo = Tarea 32) ----------

def test_settlement_idempotente_sin_redebito(app_client, isolated_db_path):
    ref = app_client.post("/api/ach", json={
        "from": "savings", "amount": "250000.00", "adhoc": _VALID_BEN}).json()["reference"]
    after_debit = _savings_cents(isolated_db_path)

    conn = db.get_connection(isolated_db_path)
    try:
        row = ach_repo.get_ach_by_reference(conn, ref)
        tid = row["id"]
        future = datetime.now(timezone.utc) + timedelta(seconds=ach_service.ACH_SETTLEMENT_DELAY_SECONDS + 1)
        assert ach_service.settle_ach(conn, tid, now=future) is True      # pending → settled
        assert ach_service.settle_ach(conn, tid, now=future) is False     # idempotente
        status = conn.execute("SELECT status FROM transfer WHERE id=?", (tid,)).fetchone()["status"]
    finally:
        conn.close()
    assert status == "settled"
    # Settlement NO vuelve a debitar.
    assert _savings_cents(isolated_db_path) == after_debit


def test_settlement_no_elegible_antes_del_retardo(app_client, isolated_db_path):
    ref = app_client.post("/api/ach", json={
        "from": "savings", "amount": "250000.00", "adhoc": _VALID_BEN}).json()["reference"]
    conn = db.get_connection(isolated_db_path)
    try:
        tid = ach_repo.get_ach_by_reference(conn, ref)["id"]
        now = datetime.now(timezone.utc)  # aún no pasó el retardo
        assert ach_service.settle_ach(conn, tid, now=now) is False
    finally:
        conn.close()


# --- Fallo y reembolso exactamente-una-vez ------------------------------------

def test_fallo_reembolsa_una_sola_vez(app_client, isolated_db_path):
    before = _savings_cents(isolated_db_path)
    ref = app_client.post("/api/ach", json={
        "from": "savings", "amount": "250000.00", "adhoc": _VALID_BEN}).json()["reference"]
    assert _savings_cents(isolated_db_path) == before - 25_000_000  # debitado

    conn = db.get_connection(isolated_db_path)
    try:
        tid = ach_repo.get_ach_by_reference(conn, ref)["id"]
        assert ach_service.fail_ach(conn, tid) is True      # failed + refund
        assert ach_service.fail_ach(conn, tid) is False     # idempotente: no re-reembolsa
        status = conn.execute("SELECT status FROM transfer WHERE id=?", (tid,)).fetchone()["status"]
    finally:
        conn.close()
    assert status == "failed"
    # Reembolso exacto una sola vez → saldo vuelve al inicial.
    assert _savings_cents(isolated_db_path) == before


# --- Límites aplicados a ACH ---------------------------------------------------

def test_ach_respeta_limite_por_transferencia(app_client):
    app_client.put("/api/limits", json={"per_transfer": "100000.00"})
    r = app_client.post("/api/ach", json={
        "from": "savings", "amount": "100000.01", "adhoc": _VALID_BEN})
    assert r.status_code == 409 and r.json()["error"]["code"] == "LIMIT_EXCEEDED_PER_TRANSFER"


# --- Historial unificado y compatibilidad -------------------------------------

def test_historial_unificado_internas_y_ach(app_client):
    # Interna (heredada).
    app_client.post("/api/transfers", json={
        "from": "checking", "to": "savings", "amount": "1000.00", "description": "int"})
    # ACH.
    app_client.post("/api/ach", json={
        "from": "savings", "amount": "250000.00", "description": "ach", "adhoc": _VALID_BEN})
    hist = app_client.get("/api/transfers").json()["transfers"]
    internals = [t for t in hist if t["type"] == "internal"]
    achs = [t for t in hist if t["type"] == "ach"]
    assert len(achs) == 1 and len(internals) >= 1
    # ACH: beneficiario enmascarado, estado minúsculas, sin número completo.
    a = achs[0]
    assert a["status"] == "pending"
    assert a["beneficiary"]["account_masked"] == "••••3210"
    assert "account_number" not in a["beneficiary"]
    # Interna: forma heredada con direction + estado MAYÚSCULAS.
    i = internals[0]
    assert "direction" in i and i["status"] == i["status"].upper()


def test_historial_no_expone_numero_completo(app_client):
    import json as _json
    app_client.post("/api/ach", json={
        "from": "savings", "amount": "250000.00", "adhoc": _VALID_BEN})
    raw = _json.dumps(app_client.get("/api/transfers").json())
    assert "9876543210" not in raw  # número de cuenta completo nunca expuesto
