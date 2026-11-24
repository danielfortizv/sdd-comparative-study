# T18 — Aislamiento de DB sintética para carga (`loadtest/isolation.py`)

- **Fecha:** 2026-11-16T20:03:53-05:00
- **Tarea:** 18 (M3, wave 7) — _Aislamiento de DB sintética para carga_
- **Spec:** `.kiro/specs/shift-bank-stage3`
- **Requisitos:** R10.1 (aislamiento ANTES de importar la app), R10.2 (siembra determinista, semilla fija)
- **Diseño:** §3.1 (arquitectura y aislamiento de carga)
- **AC:** AC-10
- **Entorno:** Windows, Python 3.13.2, venv `backend/.venv`
- **Alcance explícito:** NO se ejecuta SonarQube ni la prueba de carga real (eso es T20–T23). NO se
  modifica `SEED-3.md` ni datos históricos de la Etapa 2.

## 1. Entregable

Paquete nuevo **tooling de pruebas/carga** (no runtime):

```
Etapa 3/Kiro/loadtest/
  __init__.py       # documentación del paquete de carga
  isolation.py      # aislamiento + siembra determinista + teardown + sanity check
```

`locust` ya es dependencia solo-dev (T3, `backend/requirements-dev.txt`). `loadtest/` vive en la
raíz del proyecto Kiro, junto a `backend/`; `isolation.py` añade `backend/` a `sys.path` ANTES de
importar `app.*` (mismo patrón que `backend/tests/conftest.py`).

## 2. API del módulo (`loadtest.isolation`)

| Símbolo | Tipo | Propósito |
|---|---|---|
| `set_test_keys_env()` | función | Fija claves de SOLO-CARGA en el entorno ANTES de importar la app (R10.1). |
| `make_synthetic_db_path() -> Path` | función | Ruta única de DB sintética **desechable** en el temp dir del SO. |
| `configure_isolation(db_path=None) -> Path` | función | **Núcleo R10.1:** fija `os.environ["DB_PATH"]` + claves, luego importa SOLO `app.config`/`app.db` y parchea su `DB_PATH`. NO importa `app.main` (la app no se arranca aquí). Devuelve la ruta resuelta. |
| `seed_synthetic_db(db_path)` | función | `random.seed(FIJA)` + secuencia de arranque `init_schema → migrate → migrate_encryption → seed → seed_limits` + ajuste determinista de saldos/límites amplios. |
| `_apply_loadtest_values(conn)` | función | UPDATE de saldos (ambas cuentas) y UPSERT de límites a los valores sintéticos amplios. |
| `teardown_synthetic_db(db_path)` | función | Elimina la DB desechable y auxiliares `-wal/-shm/-journal`. |
| `setup_loadtest_db(db_path=None) -> Path` | función | Conveniencia: `configure_isolation()` + `seed_synthetic_db()`. Usada por el runner (T20) y la sanity. |
| `_read_balances` / `_read_limits` | función | Lectura directa para la verificación de sanity. |
| `_main()` / `python -m loadtest.isolation` | CLI | Sanity ejecutable: aísla, siembra, verifica, importa la app y confirma DB histórica intacta. |

### Constantes (deterministas, SOLO carga)

| Constante | Valor | Nota |
|---|---|---|
| `LOADTEST_RANDOM_SEED` | `20240917` | Semilla fija (`random.seed`) → reproducibilidad (R10.2). |
| `LOADTEST_ENC_KID` | `"test"` | Consistente con `conftest.py`. |
| `LOADTEST_ENC_KEY_B64` | `c2hpZnQtYmFuay1zdGFnZTMtdGVzdC1rZXktMzJieXQ=` | base64 de 32 bytes (AES-256), idéntico al arnés. |
| `LOADTEST_ENC_KEYS` | `test:c2hpZnQt…` | `SHIFT_ENC_KEYS`. |
| `LOADTEST_AUDIT_HMAC_KEY` | `shift-bank-stage3-loadtest-audit-hmac-key` | `SHIFT_AUDIT_HMAC_KEY`. |
| `LOADTEST_ADMIN_TOKEN` | `shift-bank-stage3-loadtest-admin-token` | `SHIFT_ADMIN_TOKEN`. |

Las claves son material de **SOLO carga/pruebas**, claramente etiquetado; NO se hornean en el código
de la app ni en `requirements*.txt`. El fail-closed de producción permanece intacto (la app sigue
exigiendo claves por entorno).

## 3. Valores sintéticos sembrados (deterministas, R10.2)

| Campo | Centavos | COP | Motivo |
|---|---|---|---|
| Saldo Checking | `1_000_000_000_000` | 10.000.000.000,00 | Amplio para 60 s de transferencias pequeñas sin agotar fondos. |
| Saldo Savings | `1_000_000_000_000` | 10.000.000.000,00 | Idem. |
| Límite por transferencia | `100_000_000_000` | 1.000.000.000,00 | Muy por encima del monto pequeño de carga; no se dispara. |
| Límite diario acumulado | `100_000_000_000_000` | 1.000.000.000.000,00 | Muy por encima del consumo posible en 60 s; no se dispara. |

Con estos valores, las transferencias de carga (monto pequeño, **por debajo** del umbral MFA de
1.000.000 COP) pasan TODOS los controles heredados (fondos + límites + sin MFA) y se completan como
operaciones bancarias **válidas**, no como rechazos (R10.3; la mezcla exacta la define T19).

## 4. Mecanismo de aislamiento ANTES de importar la app (R10.1)

`configure_isolation` establece el orden crítico:

1. Elegir/crear la ruta de DB sintética desechable (temp dir).
2. `os.environ["DB_PATH"] = <ruta>` + `set_test_keys_env()` (claves de carga).
3. Importar **solo** `app.config` y `app.db` y parchear su `DB_PATH` (igual que `conftest.py`).
   NO se importa `app.main`: la app no se arranca en este paso, así que ninguna conexión se abre
   contra la DB histórica antes de que el aislamiento esté en vigor.

El runner (T20) arrancará uvicorn sobre esta DB; aquí solo se proveen los bloques de construcción y
se verifica que la app **importa limpiamente** contra la DB sintética.

> Si el aislamiento no pudiera establecerse antes de importar la app, la tarea sería FAIL. No es el
> caso: el sanity check confirma el orden correcto y que la DB histórica no se toca.

## 5. Salida real — `python -m loadtest.isolation`

Comando (desde `Etapa 3/Kiro/`):

```
backend\.venv\Scripts\python.exe -m loadtest.isolation
```

Salida (exit 0):

```
=== loadtest.isolation sanity check ===
Resolved DB_PATH (synthetic, disposable): C:\Users\danie\AppData\Local\Temp\shift_bank_loadtest_18bcef373f72489c972a991f691aed96.db
DB file exists: True
Points at historic DB? False
--- seeded balances (cents) ---
  checking  :    1,000,000,000,000  (COP 10,000,000,000.00)
  savings   :    1,000,000,000,000  (COP 10,000,000,000.00)
--- seeded limits (cents) ---
  daily_cents         :  100,000,000,000,000  (COP 1,000,000,000,000.00)
  per_transfer_cents  :      100,000,000,000  (COP 1,000,000,000.00)
--- app import ---
  import app.main: OK (claves de carga válidas; DB sintética parcheada)
--- historic DB ---
  historic DB untouched: True
=== RESULT: PASS ===
Teardown: removed synthetic DB C:\Users\danie\AppData\Local\Temp\shift_bank_loadtest_18bcef373f72489c972a991f691aed96.db (+ -wal/-shm/-journal)
```

Verificaciones automáticas dentro de la sanity (todas PASS):
- DB sintética != DB histórica (`backend/shift_bank.db`).
- Saldos y límites sembrados == valores sintéticos documentados.
- `import app.main` OK contra la DB sintética (claves válidas en el entorno).
- DB histórica intacta (misma existencia + mismo mtime antes/después).
- Teardown elimina el archivo desechable + auxiliares.

## 6. Regresión backend (sin impacto; añade solo tooling)

Comando (desde `Etapa 3/Kiro/backend/`):

```
.venv\Scripts\python.exe -m pytest -q
```

Resultado:

```
344 passed, 1 warning in 18.56s
```

(1 warning preexistente: DeprecationWarning de Starlette/anyio, no relacionado con T18.) La cuenta
se mantiene en **344** → el tooling de carga no afecta la suite.

## 7. Veredicto

**PASS.** `loadtest/isolation.py` configura una DB SQLite sintética aislada con saldos/límites
amplios documentados, fija las claves de cifrado/auditoría ANTES de importar la app (R10.1), siembra
de forma determinista con semilla fija (R10.2), expone teardown de la DB desechable y NO toca la DB
histórica ni `SEED-3.md`. Regresión backend verde (344 passed).
