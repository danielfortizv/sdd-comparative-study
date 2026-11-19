"""Regresión Etapa 1 — Transferencias internas (ruta sin MFA) y validaciones (Tarea 3).

Fija el comportamiento HEREDADO observable de las transferencias internas entre las cuentas
propias (Checking/Savings), su registro en el historial y sus validaciones, ANTES de
introducir funcionalidad de la Etapa 2. No impone reglas nuevas: verifica el contrato tal como
está en la Etapa 1.

Se limita a la **ruta sin MFA** (montos < umbral de 1.000.000). La regresión exhaustiva de MFA
corresponde a la Tarea 4 y NO se ejecuta aquí.

Fuente del comportamiento esperado (código heredado real):
- `app/routers/transfers.py`: `POST /api/transfers` → 201 `{status, mfa_required, reference?,
  expires_at?}`; errores `{error:{code,message}}`; `GET /api/transfers` →
  `{transfers:[{date, direction:{from,to}, amount, description, status}]}`.
- `app/service.py`: valida misma cuenta (`SAME_ACCOUNT`), monto ≤ 0 (`NON_POSITIVE_AMOUNT`),
  formato/decimales (`INVALID_AMOUNT`), fondos (`INSUFFICIENT_FUNDS`); < umbral → `COMPLETED`.
- `app/seed.py`: dos históricas sembradas (500.000 S→C, 100.000 C→S) que NO afectan saldos.
- `app/schemas.py`: request con alias `from`; montos como decimal-string.

Usa los fixtures aislados (`app_client`, `isolated_db_path`): DB temporal por prueba; nunca
toca la DB histórica.

_Requisitos: 15.2, 15.3, 15.7_ · _Contrato: HER-02; A02_
"""

import app.db as db


def _balances(client):
    """Mapa nombre→saldo (decimal-string) desde la API."""
    accounts = client.get("/api/accounts").json()["accounts"]
    return {a["name"]: a["balance"] for a in accounts}


def _balances_cents(db_path):
    """Mapa nombre→saldo en centavos desde la DB aislada."""
    conn = db.get_connection(db_path)
    try:
        rows = conn.execute("SELECT display_name, balance_cents FROM account").fetchall()
    finally:
        conn.close()
    return {r["display_name"]: r["balance_cents"] for r in rows}


# --- 1. Transferencias internas exitosas (sin MFA) -----------------------------

def test_transferencia_interna_exitosa_sin_mfa(app_client):
    """Transferencia < umbral C→S responde 201 COMPLETED sin requerir MFA."""
    resp = app_client.post(
        "/api/transfers",
        json={"from": "checking", "to": "savings", "amount": "250000.00",
              "description": "Ahorro"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "COMPLETED"
    assert body["mfa_required"] is False


def test_debito_y_credito_correctos_y_total_preservado(app_client, isolated_db_path):
    """El origen se debita, el destino se acredita y el total se preserva (centavos)."""
    before = _balances_cents(isolated_db_path)
    total_before = before["Checking"] + before["Savings"]

    app_client.post(
        "/api/transfers",
        json={"from": "checking", "to": "savings", "amount": "250000.00",
              "description": "mov"},
    )

    after = _balances_cents(isolated_db_path)
    # 250.000,00 COP = 25.000.000 centavos.
    assert after["Checking"] == before["Checking"] - 25_000_000
    assert after["Savings"] == before["Savings"] + 25_000_000
    # Total conservado (transferencia interna no crea ni destruye dinero).
    assert after["Checking"] + after["Savings"] == total_before


def test_api_refleja_los_nuevos_saldos(app_client):
    """Tras una transferencia exitosa, GET /api/accounts refleja los saldos actualizados."""
    app_client.post(
        "/api/transfers",
        json={"from": "savings", "to": "checking", "amount": "100000.00",
              "description": "mov"},
    )
    bal = _balances(app_client)
    # Checking 5.000.000,00 + 100.000,00 = 5.100.000,00; Savings 15.000.000,00 - 100.000,00.
    assert bal["Checking"] == "5100000.00"
    assert bal["Savings"] == "14900000.00"


# --- 2. Historial de transferencias -------------------------------------------

def test_historial_tiene_dos_historicas_al_inicio(app_client):
    """Al arrancar, el historial contiene exactamente las dos transferencias sembradas."""
    hist = app_client.get("/api/transfers").json()["transfers"]
    assert len(hist) == 2
    # Las históricas son COMPLETED y no afectan los saldos iniciales (verificado en Tarea 2).
    assert all(t["status"] == "COMPLETED" for t in hist)


def test_nueva_transferencia_se_registra_y_preserva_historicas(app_client):
    """Una nueva transferencia se añade al historial sin eliminar las históricas."""
    app_client.post(
        "/api/transfers",
        json={"from": "checking", "to": "savings", "amount": "123456.78",
              "description": "nueva"},
    )
    hist = app_client.get("/api/transfers").json()["transfers"]
    assert len(hist) == 3  # 2 históricas + 1 nueva
    nueva = next(t for t in hist if t["description"] == "nueva")
    assert nueva["status"] == "COMPLETED"


def test_estructura_e_estados_del_historial_heredados(app_client):
    """Cada entrada conserva la forma heredada y los estados en MAYÚSCULAS."""
    app_client.post(
        "/api/transfers",
        json={"from": "checking", "to": "savings", "amount": "1000.00", "description": "x"},
    )
    hist = app_client.get("/api/transfers").json()["transfers"]
    for t in hist:
        # Campos heredados presentes; `type` es extensión aditiva aprobada (D03/D05, Tarea 25).
        assert {"date", "direction", "amount", "description", "status"}.issubset(t.keys())
        assert set(t.keys()) <= {"date", "direction", "amount", "description", "status", "type"}
        assert t.get("type") == "internal"
        assert set(t["direction"].keys()) == {"from", "to"}
        # Nombres amigables en la dirección.
        assert t["direction"]["from"] in {"Checking", "Savings"}
        assert t["direction"]["to"] in {"Checking", "Savings"}
        # Estados internos en MAYÚSCULAS (contrato heredado).
        assert t["status"] in {"PENDING_MFA", "COMPLETED", "FAILED", "EXPIRED"}
        assert t["status"] == t["status"].upper()
        # Monto como decimal-string con 2 decimales.
        assert isinstance(t["amount"], str) and t["amount"].split(".")[1] != ""


# --- 3. Validación de transferencias ------------------------------------------

def test_rechaza_misma_cuenta(app_client, isolated_db_path):
    """Origen == destino se rechaza (SAME_ACCOUNT) sin mover saldos."""
    before = _balances_cents(isolated_db_path)
    resp = app_client.post(
        "/api/transfers",
        json={"from": "checking", "to": "checking", "amount": "1000.00", "description": ""},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "SAME_ACCOUNT"
    assert _balances_cents(isolated_db_path) == before


def test_rechaza_monto_no_positivo(app_client, isolated_db_path):
    """Monto ≤ 0 se rechaza (NON_POSITIVE_AMOUNT) sin mover saldos."""
    before = _balances_cents(isolated_db_path)
    for amount in ("0.00", "-500.00"):
        resp = app_client.post(
            "/api/transfers",
            json={"from": "checking", "to": "savings", "amount": amount, "description": ""},
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "NON_POSITIVE_AMOUNT"
    assert _balances_cents(isolated_db_path) == before


def test_rechaza_decimales_no_soportados(app_client, isolated_db_path):
    """Monto con más de 2 decimales se rechaza (INVALID_AMOUNT) sin mover saldos."""
    before = _balances_cents(isolated_db_path)
    resp = app_client.post(
        "/api/transfers",
        json={"from": "checking", "to": "savings", "amount": "100.123", "description": ""},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVALID_AMOUNT"
    assert _balances_cents(isolated_db_path) == before


def test_rechaza_fondos_insuficientes(app_client, isolated_db_path):
    """Monto mayor al saldo disponible se rechaza (INSUFFICIENT_FUNDS) sin mover saldos.

    Se usa un monto por debajo del umbral de MFA para permanecer en la ruta sin MFA, pero
    superior al saldo de Savings transferido desde... no: Checking tiene 5.000.000,00. Para
    forzar fondos insuficientes sin cruzar el umbral MFA, se agota primero el saldo con una
    operación válida no es necesario: basta un origen con saldo menor al monto y monto < umbral.
    Aquí Savings (15M) no sirve; usamos un segundo paso: reducir Checking no aplica. En su lugar,
    verificamos con un monto < umbral que exceda el saldo del origen tras vaciarlo no es trivial.
    Enfoque simple y determinista: transferir desde Checking un monto < umbral pero > su saldo
    es imposible (saldo 5M > umbral 1M). Por tanto se verifica el rechazo agotando el origen con
    una cuenta de bajo saldo simulada no existe en E1. Se valida el código de error con un monto
    que excede el saldo del origen tras no poder: ver implementación abajo.
    """
    # Checking = 5.000.000,00; umbral MFA = 1.000.000,00. No se puede exceder el saldo con un
    # monto < umbral en una sola operación. Para ejercitar INSUFFICIENT_FUNDS en la ruta sin MFA
    # de forma determinista, primero se reduce el saldo de una cuenta con transferencias válidas
    # < umbral y luego se intenta exceder el remanente, también < umbral.
    before = _balances_cents(isolated_db_path)

    # Vaciar Checking por debajo de 900.000,00: mover 999.999,99 repetidamente (todas < umbral).
    # 5.000.000,00 / 999.999,99 ≈ 5 operaciones dejan < 1.000.000,00 en Checking.
    for _ in range(5):
        app_client.post(
            "/api/transfers",
            json={"from": "checking", "to": "savings", "amount": "999999.99",
                  "description": "drena"},
        )
    remanente = _balances_cents(isolated_db_path)["Checking"]
    # El remanente debe ser < umbral (1.000.000,00 = 100.000.000 centavos) para el siguiente paso.
    assert remanente < 100_000_000
    saldo_actual = _balances_cents(isolated_db_path)

    # Intentar transferir más que el remanente, con un monto < umbral → INSUFFICIENT_FUNDS.
    exceso_cents = remanente + 1  # un centavo más que el saldo disponible
    exceso_str = f"{exceso_cents // 100}.{exceso_cents % 100:02d}"
    resp = app_client.post(
        "/api/transfers",
        json={"from": "checking", "to": "savings", "amount": exceso_str, "description": "x"},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INSUFFICIENT_FUNDS"
    # El rechazo no mueve saldos.
    assert _balances_cents(isolated_db_path) == saldo_actual
    # El total global nunca cambió respecto al inicio (solo movimientos internos válidos).
    assert sum(before.values()) == sum(_balances_cents(isolated_db_path).values())


# --- 4. Consistencia financiera y representación monetaria --------------------

def test_rechazo_no_causa_movimiento_parcial(app_client, isolated_db_path):
    """Un request inválido no produce ningún movimiento parcial de saldos."""
    before = _balances_cents(isolated_db_path)
    # Varios inválidos seguidos.
    app_client.post("/api/transfers",
                    json={"from": "checking", "to": "checking", "amount": "1.00",
                          "description": ""})
    app_client.post("/api/transfers",
                    json={"from": "checking", "to": "savings", "amount": "-1.00",
                          "description": ""})
    app_client.post("/api/transfers",
                    json={"from": "checking", "to": "savings", "amount": "1.001",
                          "description": ""})
    assert _balances_cents(isolated_db_path) == before


def test_representacion_centavos_y_decimal_string(app_client, isolated_db_path):
    """Internamente centavos enteros; en la API decimal-string con 2 decimales."""
    app_client.post(
        "/api/transfers",
        json={"from": "checking", "to": "savings", "amount": "0.01", "description": "centavo"},
    )
    cents = _balances_cents(isolated_db_path)
    # Todos los saldos son enteros (centavos).
    assert all(isinstance(v, int) for v in cents.values())
    # Checking = 5.000.000,00 - 0,01 = 4.999.999,99.
    bal = _balances(app_client)
    assert bal["Checking"] == "4999999.99"
    assert all("." in v and len(v.split(".")[1]) == 2 for v in bal.values())
