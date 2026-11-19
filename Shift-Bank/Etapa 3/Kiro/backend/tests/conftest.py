"""Fixtures compartidos del arnés de pruebas del backend (Etapa 2, Tarea 1).

Objetivo: aislar cada prueba en una base de datos SQLite temporal propia, de modo que
NINGUNA prueba lea ni escriba la base de datos histórica de la Etapa 1 (`shift_bank.db`)
ni ningún baseline experimental persistente.

Estrategia de aislamiento (sin modificar código de aplicación):
- La aplicación heredada resuelve la ruta de la DB desde `app.config.DB_PATH`, que
  `app.db.get_connection()` usa por defecto. El fixture parchea esa ruta hacia un archivo
  temporal único por prueba ANTES de importar/crear la app, de modo que el ciclo de arranque
  (init_schema + seed) y todas las conexiones por request apunten a la DB temporal.
- Cada prueba recibe una DB nueva y vacía; al finalizar se elimina junto con sus posibles
  archivos auxiliares de SQLite (-wal/-shm/-journal). No queda estado persistente.

Este módulo NO contiene pruebas de regresión de la Etapa 1 (esas corresponden a las tareas
2–5); solo provee la infraestructura de aislamiento y un cliente de la app heredada.
"""

import importlib
import os
import sys
import tempfile
import uuid
from pathlib import Path

import pytest

# Asegurar que el paquete `app` del backend sea importable al ejecutar pytest desde `backend/`.
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

# --- Etapa 3 (Tarea 5): material de clave SOLO-PRUEBAS -----------------------
#
# Desde la Etapa 3, el arranque de la app (`lifespan`) valida fail-closed las claves
# externas de cifrado/auditoría (`SHIFT_ENC_KEYS`, `SHIFT_ENC_ACTIVE_KID`,
# `SHIFT_AUDIT_HMAC_KEY`). El arnés heredado arranca la app vía `TestClient`, lo que
# dispara `lifespan`; por eso DEBEMOS proveer claves válidas antes de importar/arrancar
# la app, igual que ya se parchea `DB_PATH` antes de importar.
#
# IMPORTANTE: estas son claves de PRUEBA deterministas y claramente etiquetadas. NO se
# hornean en el código de la app ni en `requirements*.txt`; viven solo en el arnés. No
# debilitan el fail-closed de producción (la app sigue exigiendo claves por entorno).
#
# `TEST_ENC_KEY_B64` = base64 de 32 bytes b"shift-bank-stage3-test-key-32byt" (AES-256).
TEST_ENC_KID = "test"
TEST_ENC_KEY_B64 = "c2hpZnQtYmFuay1zdGFnZTMtdGVzdC1rZXktMzJieXQ="
TEST_ENC_KEYS = f"{TEST_ENC_KID}:{TEST_ENC_KEY_B64}"
TEST_AUDIT_HMAC_KEY = "shift-bank-stage3-test-audit-hmac-key"
TEST_ADMIN_TOKEN = "shift-bank-stage3-test-admin-token"


def _set_test_key_env() -> None:
    """Fija el material de clave SOLO-PRUEBAS en el entorno del proceso de pytest.

    Se ejecuta al importar `conftest.py` (antes de cualquier arranque de app) para que la
    validación fail-closed del `lifespan` encuentre claves válidas. `setdefault` respeta
    cualquier valor que el entorno ya traiga (p. ej. CI con claves propias).
    """
    os.environ.setdefault("SHIFT_ENC_KEYS", TEST_ENC_KEYS)
    os.environ.setdefault("SHIFT_ENC_ACTIVE_KID", TEST_ENC_KID)
    os.environ.setdefault("SHIFT_AUDIT_HMAC_KEY", TEST_AUDIT_HMAC_KEY)
    os.environ.setdefault("SHIFT_ADMIN_TOKEN", TEST_ADMIN_TOKEN)


_set_test_key_env()


@pytest.fixture(autouse=True)
def _ensure_test_keys():
    """Autouse: garantiza las claves de prueba presentes en cada test.

    Un test negativo puede borrar/alterar las variables de entorno para probar el
    fail-closed; este fixture las restaura antes de cada prueba para no contaminar al
    resto de la suite. Es un seguro adicional sobre `_set_test_key_env`.
    """
    _set_test_key_env()
    yield


def _remove_db_files(db_path: Path) -> None:
    """Elimina el archivo de DB y sus auxiliares de SQLite si existen."""
    for suffix in ("", "-wal", "-shm", "-journal"):
        p = Path(str(db_path) + suffix)
        if p.exists():
            p.unlink()


@pytest.fixture()
def isolated_db_path(tmp_path, monkeypatch):
    """Ruta a una base de datos SQLite temporal, aislada y única por prueba.

    Parchea `app.config.DB_PATH` y `app.db.DB_PATH` para que toda la aplicación use esta ruta,
    nunca la base de datos histórica. Devuelve la ruta (la DB aún no existe hasta que algo la
    crea, p. ej. el arranque de la app o una conexión).
    """
    # `tmp_path` de pytest ya es un directorio temporal único por prueba; añadimos un nombre
    # único para evitar colisiones y dejar claro el propósito.
    db_path = tmp_path / f"shift_bank_test_{uuid.uuid4().hex}.db"

    # Importar los módulos y parchear la ruta en ambos (config la define; db la importa).
    import app.config as config
    import app.db as db

    monkeypatch.setattr(config, "DB_PATH", db_path, raising=True)
    monkeypatch.setattr(db, "DB_PATH", db_path, raising=True)

    yield db_path

    # Teardown explícito (además del propio tmp_path de pytest): no dejar estado persistente.
    _remove_db_files(db_path)


@pytest.fixture()
def app_client(isolated_db_path):
    """Cliente de pruebas de la aplicación FastAPI heredada, atado a la DB aislada.

    Usa `TestClient` como context manager para disparar los eventos de ciclo de vida
    (startup: init_schema + seed) contra la base de datos temporal. La app heredada no se
    modifica; solo se consume con la ruta de DB ya parcheada por `isolated_db_path`.
    """
    from fastapi.testclient import TestClient

    # Importar la app después del parcheo de la ruta. Recargar por si un test previo la importó.
    import app.main as main
    importlib.reload(main)

    with TestClient(main.app) as client:
        yield client
