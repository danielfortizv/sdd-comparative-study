"""Regresión Etapa 1 — Cuentas y saldos iniciales (Etapa 2, Tarea 2).

Fija el comportamiento HEREDADO y observable de la Etapa 1 para la recuperación de cuentas,
ANTES de introducir cualquier funcionalidad de la Etapa 2. No rediseña ni normaliza el
contrato existente: verifica el comportamiento tal como está.

Fuente del comportamiento esperado (código heredado real):
- `app/seed.py`: Checking = 5.000.000,00 COP; Savings = 15.000.000,00 COP (fijados en centavos).
- `app/routers/accounts.py`: `GET /api/accounts` → `{ "accounts": [{name, balance}] }`,
  orden checking→savings, sin identificadores internos.
- `app/schemas.py`: `AccountOut{ name: str, balance: str }` (balance como decimal-string).

Usa los fixtures aislados de la Tarea 1 (`app_client`, `isolated_db_path`): cada prueba corre
sobre una DB SQLite temporal; nunca toca la DB histórica.

_Requisitos: 15.1, 15.3, 15.5_ · _Contrato: HER-01; A01_
"""

import app.db as db


# Saldos iniciales esperados (decimal-string), derivados del seed heredado.
_EXPECTED_CHECKING_BALANCE = "5000000.00"
_EXPECTED_SAVINGS_BALANCE = "15000000.00"


def test_get_accounts_responde_200(app_client):
    """GET /api/accounts responde 200 OK (recuperación exitosa)."""
    resp = app_client.get("/api/accounts")
    assert resp.status_code == 200


def test_estructura_de_respuesta_de_cuentas(app_client):
    """La respuesta tiene la forma heredada: { accounts: [ { name, balance } ] }."""
    data = app_client.get("/api/accounts").json()
    assert isinstance(data, dict)
    assert set(data.keys()) == {"accounts"}
    accounts = data["accounts"]
    assert isinstance(accounts, list)
    assert len(accounts) == 2
    for acc in accounts:
        # Solo nombre amigable y saldo; sin identificadores internos.
        assert set(acc.keys()) == {"name", "balance"}
        assert isinstance(acc["name"], str)
        assert isinstance(acc["balance"], str)  # decimal-string, nunca número


def test_cuentas_checking_y_savings_presentes(app_client):
    """Existen exactamente las cuentas Checking y Savings con nombres amigables."""
    accounts = app_client.get("/api/accounts").json()["accounts"]
    names = [a["name"] for a in accounts]
    assert names == ["Checking", "Savings"]  # orden heredado checking→savings


def test_saldos_iniciales_heredados(app_client):
    """Los saldos iniciales son los sembrados: Checking 5.000.000,00; Savings 15.000.000,00."""
    accounts = app_client.get("/api/accounts").json()["accounts"]
    balances = {a["name"]: a["balance"] for a in accounts}
    assert balances["Checking"] == _EXPECTED_CHECKING_BALANCE
    assert balances["Savings"] == _EXPECTED_SAVINGS_BALANCE


def test_representacion_monetaria_decimal_string_2_decimales(app_client):
    """Los saldos se transportan como cadena decimal con exactamente 2 decimales."""
    accounts = app_client.get("/api/accounts").json()["accounts"]
    for a in accounts:
        bal = a["balance"]
        assert isinstance(bal, str)
        # Dos decimales exactos (decimal-string canónico).
        assert "." in bal and len(bal.split(".")[1]) == 2


def test_sin_identificadores_internos_en_la_respuesta(app_client):
    """La respuesta no expone IDs, UUID ni números de cuenta internos."""
    import json

    raw = json.dumps(app_client.get("/api/accounts").json())
    for forbidden in ("id", "uuid", "customer_id", "account_id", "kind"):
        assert forbidden not in raw.lower()


def test_consistencia_entre_api_y_db_aislada(app_client, isolated_db_path):
    """El saldo de la API coincide con el persistido en la DB aislada (centavos)."""
    accounts = app_client.get("/api/accounts").json()["accounts"]
    api_balances = {a["name"]: a["balance"] for a in accounts}

    conn = db.get_connection(isolated_db_path)
    try:
        rows = conn.execute(
            "SELECT display_name, balance_cents FROM account"
        ).fetchall()
    finally:
        conn.close()
    db_balances = {r["display_name"]: r["balance_cents"] for r in rows}

    # 5.000.000,00 COP = 500.000.000 centavos; 15.000.000,00 = 1.500.000.000 centavos.
    assert db_balances["Checking"] == 500_000_000
    assert db_balances["Savings"] == 1_500_000_000
    # La API refleja exactamente esos centavos como decimal-string.
    assert api_balances["Checking"] == _EXPECTED_CHECKING_BALANCE
    assert api_balances["Savings"] == _EXPECTED_SAVINGS_BALANCE


def test_lectura_no_altera_saldos(app_client, isolated_db_path):
    """Consultar cuentas es de solo lectura: repetir GET no cambia los saldos."""
    first = app_client.get("/api/accounts").json()["accounts"]

    conn = db.get_connection(isolated_db_path)
    try:
        before = conn.execute(
            "SELECT display_name, balance_cents FROM account ORDER BY display_name"
        ).fetchall()
        before_map = {r["display_name"]: r["balance_cents"] for r in before}
    finally:
        conn.close()

    # Varias lecturas adicionales.
    for _ in range(3):
        app_client.get("/api/accounts")

    conn = db.get_connection(isolated_db_path)
    try:
        after = conn.execute(
            "SELECT display_name, balance_cents FROM account ORDER BY display_name"
        ).fetchall()
        after_map = {r["display_name"]: r["balance_cents"] for r in after}
    finally:
        conn.close()

    assert before_map == after_map
    # Y la API sigue devolviendo lo mismo.
    second = app_client.get("/api/accounts").json()["accounts"]
    assert first == second
