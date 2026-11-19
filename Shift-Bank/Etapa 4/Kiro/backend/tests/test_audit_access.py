"""Acceso protegido a la verificación de auditoría (Etapa 3, Tarea 15).

Verifica que el endpoint administrativo de verificación de la cadena de auditoría
(`GET/POST /api/audit/verify`, `routers/audit.py`) está correctamente GATEADO por el token
administrativo `SHIFT_ADMIN_TOKEN` y NO es alcanzable anónimamente (design.md §2.5/§2.6,
R8.1/R8.2):

- Con cabecera `X-Admin-Token` válida → 200 y `{"ok": true}` sobre una cadena íntegra y no
  vacía (se siembran transferencias reales vía la API para poblar `audit_log`).
- Sin cabecera → 401; no se filtra ningún resultado de verificación.
- Con token erróneo → 401.
- Con `SHIFT_ADMIN_TOKEN` NO configurado (desactivado vía `monkeypatch`) → denegado
  (fail-closed), NUNCA "allow-all".
- La rutina `audit.verify_chain(conn)` sigue siendo invocable en proceso sin pasar por el gate
  (el endpoint es la ÚNICA nueva superficie pública y está protegida).
- Ningún otro endpoint heredado pasó a exigir el token (una transferencia sin cabecera sigue
  funcionando).

DB temporal aislada por prueba (nunca la DB histórica ni `SEED-3.md`/datos de la Etapa 2).

_Requisitos: R8.1, R8.2_ · _Diseño: §2.5, §2.6_ · _AC: AC-05_
"""

import app.audit as audit
import app.config as config
import app.db as db
from tests.conftest import TEST_ADMIN_TOKEN

_SMALL_TRANSFER = {"from": "checking", "to": "savings", "amount": "1000.00",
                   "description": "seed audit chain"}


def _seed_transfers(app_client, n: int = 2) -> None:
    """Puebla `audit_log` con transferencias internas reales (una entrada de auditoría c/u).

    Usa la API pública de transferencias (sin token admin) para generar eventos
    `INTERNAL_TRANSFER_COMPLETED` encadenados, de modo que la cadena quede NO vacía.
    """
    for _ in range(n):
        resp = app_client.post("/api/transfers", json=_SMALL_TRANSFER)
        assert resp.status_code == 201, resp.text


def _assert_chain_nonempty(isolated_db_path) -> None:
    conn = db.get_connection(isolated_db_path)
    try:
        count = conn.execute("SELECT COUNT(*) AS n FROM audit_log").fetchone()["n"]
        assert count >= 1, "la cadena de auditoría debe ser no vacía tras sembrar transferencias"
    finally:
        conn.close()


def test_valid_token_returns_ok_on_intact_chain(app_client, isolated_db_path):
    """Con `X-Admin-Token` válido y cadena íntegra no vacía → 200 y {"ok": true}."""
    _seed_transfers(app_client, n=2)
    _assert_chain_nonempty(isolated_db_path)

    resp = app_client.get("/api/audit/verify", headers={"X-Admin-Token": TEST_ADMIN_TOKEN})
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"ok": True}


def test_valid_token_post_variant(app_client, isolated_db_path):
    """La variante POST aplica el mismo gate y veredicto que la GET."""
    _seed_transfers(app_client, n=1)

    resp = app_client.post("/api/audit/verify", headers={"X-Admin-Token": TEST_ADMIN_TOKEN})
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"ok": True}


def test_missing_token_denied(app_client, isolated_db_path):
    """Sin cabecera → 401; no se expone ningún resultado de verificación."""
    _seed_transfers(app_client, n=1)

    resp = app_client.get("/api/audit/verify")
    assert resp.status_code == 401, resp.text
    body = resp.json()
    # No se filtra el veredicto de verify_chain.
    assert "ok" not in body
    assert "failed_seq" not in body


def test_wrong_token_denied(app_client, isolated_db_path):
    """Con token erróneo → 401."""
    _seed_transfers(app_client, n=1)

    resp = app_client.get("/api/audit/verify",
                          headers={"X-Admin-Token": "definitely-not-the-token"})
    assert resp.status_code == 401, resp.text
    assert "ok" not in resp.json()


def test_token_not_configured_fails_closed(app_client, isolated_db_path, monkeypatch):
    """Si `SHIFT_ADMIN_TOKEN` no está configurado → denegado (fail-closed), no allow-all.

    Se desactiva la variable de entorno para esta prueba. Incluso enviando una cabecera
    (cualquier valor, o ninguna), el acceso DEBE denegarse: sin token configurado no existe
    credencial válida contra la que autenticar.
    """
    monkeypatch.delenv(config.ENV_ADMIN_TOKEN, raising=False)
    assert config.get_admin_token() is None

    # Sin cabecera → denegado.
    resp_no_header = app_client.get("/api/audit/verify")
    assert resp_no_header.status_code == 401, resp_no_header.text

    # Con una cabecera cualquiera → igualmente denegado (no allow-all).
    resp_any = app_client.get("/api/audit/verify", headers={"X-Admin-Token": "anything"})
    assert resp_any.status_code == 401, resp_any.text

    # Incluso con el valor que era válido cuando SÍ estaba configurado → denegado.
    resp_old = app_client.get("/api/audit/verify",
                              headers={"X-Admin-Token": TEST_ADMIN_TOKEN})
    assert resp_old.status_code == 401, resp_old.text


def test_empty_token_configured_fails_closed(app_client, isolated_db_path, monkeypatch):
    """Si `SHIFT_ADMIN_TOKEN` está presente pero vacío → denegado (fail-closed)."""
    monkeypatch.setenv(config.ENV_ADMIN_TOKEN, "   ")

    resp = app_client.get("/api/audit/verify", headers={"X-Admin-Token": "   "})
    assert resp.status_code == 401, resp.text


def test_verify_chain_callable_in_process(app_client, isolated_db_path):
    """`audit.verify_chain` sigue siendo invocable directamente, sin pasar por el gate HTTP."""
    _seed_transfers(app_client, n=1)

    conn = db.get_connection(isolated_db_path)
    try:
        result = audit.verify_chain(conn)
        assert result.ok is True
    finally:
        conn.close()


def test_other_endpoints_not_gated(app_client, isolated_db_path):
    """Confirma que ningún endpoint heredado empezó a exigir el token admin.

    Una transferencia y el historial deben seguir respondiendo SIN cabecera `X-Admin-Token`.
    Solo el endpoint de verificación de auditoría es la nueva superficie gateada.
    """
    resp_transfer = app_client.post("/api/transfers", json=_SMALL_TRANSFER)
    assert resp_transfer.status_code == 201, resp_transfer.text

    resp_history = app_client.get("/api/transfers")
    assert resp_history.status_code == 200, resp_history.text
