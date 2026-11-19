"""Bootstrap de uvicorn para la prueba de carga (Etapa 3, Tarea 20).

design.md §3.1 · requirements R10.1 · AC-10.

Por qué existe este módulo
--------------------------
La app heredada resuelve `app.config.DB_PATH` como una **constante calculada**
(`Path(__file__)...parent.parent / "shift_bank.db"`) que **NO** lee la variable de entorno
`DB_PATH`. Por tanto, un subproceso de uvicorn arrancado "a secas" (`uvicorn app.main:app`)
usaría la DB **histórica**, no la sintética — violando el aislamiento (R10.1).

El arnés de pruebas resuelve esto parcheando `config.DB_PATH`/`db.DB_PATH` ANTES de importar
`app.main` (ver `backend/tests/conftest.py` e `loadtest/isolation.py`). Este launcher replica
esa técnica **dentro del proceso hijo de uvicorn**: lee `DB_PATH` + claves del entorno
(que el runner padre ya fijó), parchea los módulos de la app y arranca uvicorn
**programáticamente**. Así el `lifespan` del hijo valida las claves de carga y sirve SIEMPRE
la DB sintética aislada, sin tocar la histórica y sin modificar el código de la app.

No siembra la DB: el runner padre ya aisló y sembró el archivo sintético (idempotente); el
hijo solo apunta la app al mismo archivo y sirve tráfico.

Variables de entorno esperadas (fijadas por `run_loadtest`):
  DB_PATH                     ruta del archivo SQLite sintético.
  SHIFT_ENC_KEYS, SHIFT_ENC_ACTIVE_KID, SHIFT_AUDIT_HMAC_KEY, SHIFT_ADMIN_TOKEN
  SHIFT_LOADTEST_HOST         host de enlace (p. ej. 127.0.0.1).
  SHIFT_LOADTEST_PORT         puerto de enlace.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Asegurar que el paquete `app` del backend sea importable (igual que conftest/isolation).
_LAUNCHER_DIR = Path(__file__).resolve().parent
_BACKEND_ROOT = _LAUNCHER_DIR.parent / "backend"
if _BACKEND_ROOT.is_dir() and str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


def _patch_db_path() -> Path:
    """Parchea `config.DB_PATH`/`db.DB_PATH` hacia el `DB_PATH` del entorno (R10.1).

    DEBE ejecutarse ANTES de importar `app.main`: si `main` (y por tanto `app.db`) se
    importara con la ruta por defecto, `get_connection` abriría la DB histórica.
    """
    raw = os.environ.get("DB_PATH")
    if not raw:
        raise SystemExit(
            "[uvicorn-launcher] DB_PATH ausente del entorno: el aislamiento de carga "
            "no está configurado (R10.1)."
        )
    resolved = Path(raw)

    import app.config as config
    import app.db as db

    config.DB_PATH = resolved
    db.DB_PATH = resolved
    return resolved


def main() -> int:
    host = os.environ.get("SHIFT_LOADTEST_HOST", "127.0.0.1")
    port_raw = os.environ.get("SHIFT_LOADTEST_PORT")
    if not port_raw:
        raise SystemExit("[uvicorn-launcher] SHIFT_LOADTEST_PORT ausente del entorno.")
    port = int(port_raw)

    # Parcheo de la ruta ANTES de importar la app (orden crítico, R10.1).
    db_path = _patch_db_path()
    print(f"[uvicorn-launcher] DB sintética parcheada: {db_path}", flush=True)

    # Importar la app ya con la ruta sintética fijada; el `lifespan` valida las claves de carga.
    import uvicorn

    import app.main as main_module

    uvicorn.run(main_module.app, host=host, port=port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
