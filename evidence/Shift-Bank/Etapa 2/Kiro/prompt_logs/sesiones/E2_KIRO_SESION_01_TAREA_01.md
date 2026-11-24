# E2 · Kiro · Sesión de implementación 01 — Tarea 1

- **Fecha:** 2026-11-16
- **Tarea:** 1 — Preparar el arnés de pruebas del backend con base de datos aislada
- **Objetivo:** establecer un arnés de pruebas de backend ejecutable y aislado **antes** de
  implementar cualquier funcionalidad de la Etapa 2.
- **Estado final:** COMPLETED

## Estado del repositorio

- **Commit al inicio:** `ebf1017748928b30a9a5ad68a56b9b532f304e86` (rama `ShiftBank`).
- **Al finalizar:** mismos commits; cambios sin confirmar (no se hizo commit en esta sesión).
- **Etapa 1 (`Etapa 1/Kiro`):** git limpio, sin cambios (verificado antes y después).
- **DB histórica `Etapa 1/Kiro/backend/shift_bank.db`:** 36 864 bytes, LastWrite 13/10/2026
  2:58:26 p. m. — **sin modificar** (idéntica antes y después).

## Inspección del acceso a datos heredado

- `app/db.py`: `get_connection(db_path=None)` usa `config.DB_PATH` por defecto; `init_schema`
  crea el esquema. Conexión `sqlite3` con `check_same_thread=False` y `PRAGMA foreign_keys=ON`.
- `app/config.py`: `DB_PATH` apunta a `backend/shift_bank.db`.
- `app/main.py`: evento `@app.on_event("startup")` ejecuta `init_schema` + `seed` (idempotente).
- Routers: usan `get_connection()` sin argumento vía `Depends(_conn)`.
- **Conclusión:** el aislamiento se logra parcheando `config.DB_PATH` y `db.DB_PATH` hacia una
  DB temporal en el fixture, **sin modificar código de aplicación**. (No fue necesario ningún
  override de código de producción.)

## Archivos creados / modificados

| Acción | Archivo |
|---|---|
| Creado | `Etapa 2/Kiro/backend/requirements-dev.txt` (pytest, httpx; separados del runtime) |
| Creado | `Etapa 2/Kiro/backend/pytest.ini` (config mínima) |
| Creado | `Etapa 2/Kiro/backend/tests/conftest.py` (fixtures `isolated_db_path`, `app_client`) |
| Creado | `Etapa 2/Kiro/backend/tests/test_harness.py` (4 pruebas del arnés) |
| Modificado | `Etapa 2/Kiro/backend/.gitignore` (+`.pytest_cache/`, `shift_bank_test_*.db*`) |
| Modificado | `Etapa 2/Kiro/.kiro/specs/shift-bank-stage2/tasks.md` (marcada solo la Tarea 1) |

No se modificó ningún archivo de código de aplicación (`app/`), ni specs de requisitos/diseño,
ni la Etapa 1.

## Dependencias instaladas (solo desarrollo)

Instaladas en el venv de la copia de E2 (`backend/.venv`), vía `requirements-dev.txt`:
`pytest==8.3.4`, `httpx==0.28.1` (+ transitivas: pluggy, iniconfig, packaging, colorama,
certifi, httpcore). **No** se tocó `requirements.txt` de runtime (fastapi/uvicorn/pydantic).

## Estrategia de base de datos aislada

- Fixture `isolated_db_path`: crea una ruta de DB temporal única por prueba bajo el `tmp_path`
  de pytest (`shift_bank_test_<uuid>.db`) y parchea `app.config.DB_PATH` + `app.db.DB_PATH` con
  `monkeypatch`. Teardown elimina el archivo y sus auxiliares (`-wal/-shm/-journal`).
- Fixture `app_client`: recarga `app.main` y crea un `TestClient` como context manager para
  disparar el `startup` (init_schema + seed) contra la DB temporal; expone la app heredada sin
  modificarla.
- Resultado: cada prueba usa una DB nueva y vacía; ninguna toca `shift_bank.db` histórica ni un
  baseline persistente; no queda estado tras la sesión.

## Comandos ejecutados y resultados reales

1. `pip install -r requirements-dev.txt` → `Successfully installed … pytest-8.3.4 httpx-0.28.1`
   (exit 0).
2. `python -m pytest -v` → **4 passed, 7 warnings in 0.73s** (exit 0):
   - `test_entorno_importa_la_app_heredada` PASSED
   - `test_db_de_prueba_esta_aislada_y_es_temporal` PASSED
   - `test_la_app_crea_su_db_en_la_ruta_aislada` PASSED
   - `test_rutas_de_db_distintas_entre_pruebas` PASSED

### Advertencias (no bloqueantes)

- `DeprecationWarning: on_event is deprecated, use lifespan` — proviene del patrón heredado de
  E1 (`@app.on_event("startup")`); la migración a `lifespan` está planificada en la Tarea 12.
- `DeprecationWarning: anyio.abc.BlockingPortal alias` — interno del `TestClient` de Starlette;
  ajeno a nuestro código.

Ninguna advertencia afecta a la validez del arnés.

## Verificación del aislamiento (post-ejecución)

- Sin DB temporales residuales (`shift_bank_test_*.db`) en el backend: **vacío**.
- `shift_bank.db` **no** existe en `Etapa 2/Kiro/backend` (los tests no la crearon): confirmado.
- DB histórica de E1 sin cambios; `Etapa 1/Kiro` git limpio.

## Errores encontrados y correcciones

- Ninguno. Las 4 pruebas pasaron en la primera ejecución.

## Criterios de completitud (Tarea 1)

| Criterio | Resultado |
|---|---|
| El entorno de pruebas inicializa | ✅ (test 1) |
| La DB de prueba aislada se crea y se dispone | ✅ (fixtures + test 2/3; sin residuos) |
| Las pruebas acceden a la app heredada sin la DB histórica | ✅ (test 3) |
| Verificación mínima ejecutada y registrada | ✅ (pytest 4/4) |
| Sin tocar DB histórica ni baseline persistente | ✅ (verificado) |

**No** se ejecutó la suite de regresión de la Etapa 1 (corresponde a las tareas 2–5); estas
pruebas validan únicamente el arnés.

## Métricas

- **Duración:** no disponible de forma fiable (no instrumentada); la ejecución de pytest reportó
  0,73 s.
- **Tokens / créditos:** no disponibles (no expuestos al agente). No se estiman.
- **Interacciones de herramientas:** no contabilizadas de forma estandarizada en esta sesión; no
  se fabrican valores.

## Alcance / restricciones respetadas

- Solo se ejecutó la Tarea 1. Tareas 2–46 sin iniciar y sin marcar.
- No se implementó ACH, recurrentes ni límites; no se cambió lógica de negocio de E1; no se
  modificaron requisitos ni diseño; no se tocó la Etapa 1.
