"""Cobertura negativa de la configuración de claves fail-closed (Etapa 3, Tarea 5).

Verifica que la validación de arranque (`config.validate_startup_config`, invocada por
`main.lifespan`) FALLA CERRADA cuando falta o es inválida una clave requerida de cifrado
o de auditoría (R2.1, R2.2, R2.6, R15.3; diseño §1.4). También verifica que:
- con el material de clave de PRUEBAS válido, la validación pasa;
- el material de clave NUNCA aparece en el mensaje de error (R2.6).

No se debilita el fail-closed de producción: estas pruebas construyen entornos sin/ con
claves inválidas de forma aislada (monkeypatch) y restauran al salir.
"""

import pytest

import app.config as config

# Material de clave de PRUEBAS (coincide con el del arnés en conftest).
_VALID_KID = "test"
_VALID_KEY_B64 = "c2hpZnQtYmFuay1zdGFnZTMtdGVzdC1rZXktMzJieXQ="  # 32 bytes
_VALID_ENC_KEYS = f"{_VALID_KID}:{_VALID_KEY_B64}"
_VALID_HMAC = "shift-bank-stage3-test-audit-hmac-key"

# Valor "secreto" de prueba que NO debe aparecer nunca en los mensajes de error.
_SECRET_MARKER = "SUPERSECRETKEYMATERIAL"


def _set_all(monkeypatch, *, enc_keys=None, active_kid=None, hmac_key=None):
    """Fija (o borra, con None) las tres variables de entorno requeridas."""
    for name, value in (
        (config.ENV_ENC_KEYS, enc_keys),
        (config.ENV_ENC_ACTIVE_KID, active_kid),
        (config.ENV_AUDIT_HMAC_KEY, hmac_key),
    ):
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)


def test_valida_con_claves_de_prueba_correctas(monkeypatch):
    """Caso positivo: con claves válidas la validación no lanza."""
    _set_all(monkeypatch, enc_keys=_VALID_ENC_KEYS, active_kid=_VALID_KID, hmac_key=_VALID_HMAC)
    # No debe lanzar.
    config.validate_startup_config()


def test_falla_sin_enc_keys(monkeypatch):
    """Ausencia de `SHIFT_ENC_KEYS` → fail-closed (ConfigError)."""
    _set_all(monkeypatch, enc_keys=None, active_kid=_VALID_KID, hmac_key=_VALID_HMAC)
    with pytest.raises(config.ConfigError):
        config.validate_startup_config()


def test_falla_sin_active_kid(monkeypatch):
    """Ausencia de `SHIFT_ENC_ACTIVE_KID` → fail-closed."""
    _set_all(monkeypatch, enc_keys=_VALID_ENC_KEYS, active_kid=None, hmac_key=_VALID_HMAC)
    with pytest.raises(config.ConfigError):
        config.validate_startup_config()


def test_falla_active_kid_desconocido(monkeypatch):
    """`SHIFT_ENC_ACTIVE_KID` que no está en el mapa de claves → fail-closed."""
    _set_all(monkeypatch, enc_keys=_VALID_ENC_KEYS, active_kid="otro", hmac_key=_VALID_HMAC)
    with pytest.raises(config.ConfigError):
        config.validate_startup_config()


def test_falla_base64_invalido(monkeypatch):
    """`SHIFT_ENC_KEYS` con base64 inválido → fail-closed."""
    _set_all(
        monkeypatch,
        enc_keys=f"{_VALID_KID}:no-es-base64-valido!!!",
        active_kid=_VALID_KID,
        hmac_key=_VALID_HMAC,
    )
    with pytest.raises(config.ConfigError):
        config.validate_startup_config()


def test_falla_longitud_de_clave_incorrecta(monkeypatch):
    """Clave base64 válida pero de longitud != 32 bytes → fail-closed."""
    import base64

    short_key = base64.b64encode(b"too-short-key").decode()  # 13 bytes
    _set_all(
        monkeypatch,
        enc_keys=f"{_VALID_KID}:{short_key}",
        active_kid=_VALID_KID,
        hmac_key=_VALID_HMAC,
    )
    with pytest.raises(config.ConfigError):
        config.validate_startup_config()


def test_falla_sin_hmac_key(monkeypatch):
    """Ausencia de `SHIFT_AUDIT_HMAC_KEY` → fail-closed."""
    _set_all(monkeypatch, enc_keys=_VALID_ENC_KEYS, active_kid=_VALID_KID, hmac_key=None)
    with pytest.raises(config.ConfigError):
        config.validate_startup_config()


def test_falla_hmac_vacio(monkeypatch):
    """`SHIFT_AUDIT_HMAC_KEY` vacío/espacios → fail-closed."""
    _set_all(monkeypatch, enc_keys=_VALID_ENC_KEYS, active_kid=_VALID_KID, hmac_key="   ")
    with pytest.raises(config.ConfigError):
        config.validate_startup_config()


def test_error_no_expone_material_de_clave(monkeypatch):
    """El mensaje de error NUNCA incluye material de clave (R2.6, R15.2).

    Inyectamos una clave con base64 inválido que contiene un marcador secreto y
    comprobamos que el marcador no aparece en el texto de la excepción.
    """
    _set_all(
        monkeypatch,
        enc_keys=f"{_VALID_KID}:{_SECRET_MARKER}!!!",
        active_kid=_VALID_KID,
        hmac_key=_VALID_HMAC,
    )
    with pytest.raises(config.ConfigError) as excinfo:
        config.validate_startup_config()
    assert _SECRET_MARKER not in str(excinfo.value)


def test_lifespan_falla_cerrado_sin_claves(monkeypatch, tmp_path):
    """Integración: el arranque de la app (`lifespan`) ABORTA sin claves (fail-closed).

    Construye el `TestClient` (que dispara `lifespan`) con las variables de entorno
    borradas; debe propagar `ConfigError` en lugar de servir tráfico. La DB se aísla a
    un archivo temporal para no tocar datos históricos.
    """
    import importlib
    import uuid

    from fastapi.testclient import TestClient

    import app.config as cfg
    import app.db as db

    db_path = tmp_path / f"shift_bank_failclosed_{uuid.uuid4().hex}.db"
    monkeypatch.setattr(cfg, "DB_PATH", db_path, raising=True)
    monkeypatch.setattr(db, "DB_PATH", db_path, raising=True)

    # Quitar todas las claves requeridas del entorno.
    _set_all(monkeypatch, enc_keys=None, active_kid=None, hmac_key=None)

    import app.main as main
    importlib.reload(main)

    with pytest.raises(cfg.ConfigError):
        with TestClient(main.app):
            pass
