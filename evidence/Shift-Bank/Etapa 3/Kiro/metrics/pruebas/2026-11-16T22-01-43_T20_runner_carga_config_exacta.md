# Evidencia — Tarea 20 (Kiro, Etapa 3): Runner de carga con configuración exacta

- **Timestamp:** 2026-11-16T22-01-43
- **Tarea:** 20 (auto) — Runner de carga con configuración exacta (`loadtest/run_loadtest.py`)
- **Trazabilidad:** requirements **R9.1** · design.md **§3.1, §3.2** · AC-10
- **Archivos creados:**
  - `Etapa 3/Kiro/loadtest/run_loadtest.py` — runner orquestador.
  - `Etapa 3/Kiro/loadtest/_uvicorn_launcher.py` — bootstrap del subproceso uvicorn (aislamiento
    en el proceso hijo).
- **Archivo tocado (doc):** `Etapa 3/Kiro/loadtest/__init__.py` (nota de estado de la Tarea 20).
- **Preservación:** NO se modificó `SEED-3.md` ni ningún dato de la Etapa 2. NO se optimizó la
  aplicación (ningún cambio de rendimiento; el primer baseline llega en la Tarea 23, con gate en
  la Tarea 24). Solo se añadió tooling de carga bajo `loadtest/`.

## Entorno

| Componente | Versión |
|------------|---------|
| SO | Windows-11-10.0.26300-SP0 (win32) |
| Python (backend `.venv`) | 3.13.2 |
| locust (solo dev) | 2.47.0 |
| uvicorn | 0.32.1 |

Comandos ejecutados desde `Etapa 3/Kiro/` usando `backend\.venv\Scripts\python.exe`.

## Configuración por defecto (contrato exacto, R9.1 / design.md §3.2)

Los defaults del runner codifican el contrato **no negociable**:

| Parámetro | Default | Nota |
|-----------|---------|------|
| usuarios | **30** | `DEFAULT_USERS` |
| spawn-rate | **5 usuarios/segundo** | `DEFAULT_SPAWN_RATE` |
| ramp-up | **6 s** (calculado = users / spawn_rate = 30/5) | propiedad `LoadConfig.ramp_up_seconds` |
| steady-state tras el ramp | **60 s** | `DEFAULT_STEADY_SECONDS` |
| total de corrida de Locust | **66 s** (ramp 6 + steady 60) | propiedad `LoadConfig.total_run_seconds` |

Verificación de defaults (salida cruda):

```
> backend\.venv\Scripts\python.exe -c "import loadtest.run_loadtest as r; c=r.LoadConfig(); print('defaults:', c.users, c.spawn_rate, c.steady_seconds, 'ramp', c.ramp_up_seconds, 'total', c.total_run_seconds)"
import OK
defaults: 30 5 60 ramp 6.0 total 66.0
```

Las duraciones/conteos son **parametrizables** (`--users`, `--spawn-rate`, `--steady-seconds`,
`--port`, `--health-timeout-seconds`) **solo** para permitir un *smoke* de mecánica en entornos
limitados. Si la invocación no respeta el contrato exacto (o si se pasa `--mechanics-smoke`), el
runner marca la corrida como **SMOKE de mecánica** y lo rotula en la salida y en los nombres de
artefactos (`locust_smoke_*`), para que **nunca se confunda con el baseline oficial** (Tarea 23).

## Cómo aísla + lanza uvicorn (R10.1 / §3.1)

1. **Aislamiento ANTES de arrancar la app.** El runner llama a
   `loadtest.isolation.setup_loadtest_db()` (Tarea 18) que: fija `DB_PATH` hacia un archivo
   SQLite sintético desechable en el temp dir, fija las claves de carga `SHIFT_*` por entorno,
   parchea `config.DB_PATH`/`db.DB_PATH` en el proceso padre y siembra la DB de forma
   determinista (saldos/límites amplios). Esto ocurre **antes** de lanzar uvicorn.
2. **Launcher dedicado del subproceso uvicorn** (`_uvicorn_launcher.py`). Hallazgo importante: la
   app heredada resuelve `app.config.DB_PATH` como una **constante calculada**
   (`Path(__file__)…/shift_bank.db`) que **NO lee la variable de entorno `DB_PATH`**. Por tanto,
   un `uvicorn app.main:app` "a secas" usaría la DB **histórica**. Para respetar la restricción
   de **no modificar la app**, el launcher corre en el proceso hijo y replica la técnica del
   arnés (`conftest.py` / `isolation.py`): lee `DB_PATH` del entorno, parchea
   `config.DB_PATH`/`db.DB_PATH` **antes** de importar `app.main`, y arranca uvicorn
   programáticamente. Así el `lifespan` del hijo valida las claves de carga y sirve SIEMPRE la DB
   sintética. El hijo hereda `DB_PATH` + `SHIFT_*` del entorno del runner.
   > Esta fue una corrección real durante la implementación: el primer intento lanzaba uvicorn
   > directamente y la DB histórica resultó modificada (`DB histórica intacta: False`). Tras
   > introducir el launcher, el chequeo pasa a `True` (ver abajo).
3. **Puerto local libre.** Si `--port 0` (default), el runner reserva un puerto efímero libre
   enlazando a `127.0.0.1:0` y lo pasa al launcher por entorno (`SHIFT_LOADTEST_PORT`).

## Cómo espera la salud (bounded, fail-loud)

`_wait_until_healthy` hace *poll* a `GET /api/accounts` hasta recibir 2xx, con **timeout
acotado** (default 30 s, intervalo 0.25 s). Falla ruidosamente (`RunnerError` → salida != 0) si:

- el proceso de uvicorn muere antes de quedar sano (se aborta de inmediato, sin esperar al
  timeout, adjuntando el tail del log), o
- se agota el timeout sin 2xx.

Un servicio inalcanzable **NUNCA** se reporta como corrida válida.

## Cómo delimita la ventana steady de 60 s

El runner ejecuta Locust con `--run-time (ramp + steady)` = **66 s** por defecto. Antes de lanzar
Locust registra:

- `run_started_at` = `time.time()` del arranque de Locust (t0),
- `steady_window_start_at` = `t0 + ramp_up_seconds` (t0 + 6 s),
- `steady_window_end_at` = `steady_window_start_at + steady_seconds` (+ 60 s).

Estos timestamps (epoch) quedan en el `RunResult` y se imprimen, de modo que la **ventana de 60 s
posterior al ramp es identificable**. El split exacto de p50/p95/p99 por ventana lo hará la
Tarea 21 (R9.4) a partir de los CSV de Locust (`--csv`, incluido `stats_history.csv`); el runner
solo deja la ventana marcada.

## Teardown

El bloque `finally` de `run_load_test` siempre: (1) termina Locust (`terminate → wait → kill`),
(2) termina uvicorn igual, (3) cierra los handles de log, (4) elimina la DB sintética desechable
(`isolation.teardown_synthetic_db`, incluidos `-wal/-shm/-journal`) y (5) reverifica que la DB
histórica no fue tocada. La salida de los subprocesos se escribe a **archivos de log** (no a
PIPE) para evitar un *deadlock* de tubería en corridas largas (otra corrección real: el primer
intento con `stdout=PIPE` + `--csv-full-history` colgó Locust por buffer de tubería lleno).

## Robustez / fail-loud (verificado)

El servidor no disponible produce `RunnerError` (traducido a salida != 0 por `main()`):

```
> backend\.venv\Scripts\python.exe -c "... r._wait_until_healthy(cfg, p) contra puerto muerto, timeout 1s ..."
RunnerError raised as expected (fail-loud): El servidor nunca quedó sano en http://127.0.0.1:9/api/accounts dentro
```

## Smoke de MECÁNICA ejecutado (NO es el baseline oficial)

El entorno **sí** puede enlazar puerto local, lanzar subprocesos y correr Locust, así que se
ejecutó un smoke end-to-end real. Para que termine rápido se usó `--steady-seconds 5`
(ramp 6 s + 5 s = 11 s de corrida), con `--mechanics-smoke`. **Esto valida la mecánica del
runner, NO el baseline de 60 s** (el baseline oficial es la Tarea 23, gated por la Tarea 24).

Salida cruda del runner:

```
> backend\.venv\Scripts\python.exe -m loadtest.run_loadtest --mechanics-smoke --steady-seconds 5
[runner] DB sintética: C:\Users\danie\AppData\Local\Temp\shift_bank_loadtest_e672b6b80db34202b91e0061083a6afe.db
[runner] uvicorn → http://127.0.0.1:55686 (sirve la DB sintética aislada)
[runner] esperando salud en http://127.0.0.1:55686/api/accounts (timeout 30s)...
[runner] servidor SANO.
[runner] Locust (SMOKE de mecánica): users=30 spawn-rate=5 ramp-up=6s steady=5s total=11s
[runner] ventana STEADY: inicia en t0+6s (epoch 1794884412.789) y dura 5s (fin epoch 1794884417.789)
[runner] Locust finalizó con exit code 0.
[runner] teardown: DB sintética eliminada (C:\Users\danie\AppData\Local\Temp\shift_bank_loadtest_e672b6b80db34202b91e0061083a6afe.db).
[runner] DB histórica intacta: True
=== run_loadtest: RESULT ===
  base_url:            http://127.0.0.1:55686
  users:               30
  spawn_rate:          5
  ramp_up_seconds:     6.0
  steady_seconds:      5
  total_run_seconds:   11
  steady_window_start: epoch 1794884412.789
  steady_window_end:   epoch 1794884417.789
  locust_exit_code:    0
  csv_prefix:          ...\Kiro\loadtest\results\locust_smoke_20261116T220006
  mechanics_smoke:     True
  NOTA: corrida marcada como SMOKE de mecánica — NO es el baseline oficial (el baseline es la Tarea 23).
EXITCODE=0
```

Observaciones del smoke:

- `servidor SANO` tras el poll de salud; `DB histórica intacta: True`; DB sintética **eliminada**
  en el teardown. Confirmado aparte: el `mtime` de `backend/shift_bank.db` fue idéntico antes y
  después del smoke (`2026-11-16T20:35:21.9043354-05:00`).
- 30 usuarios, spawn-rate 5, ramp 6 s; ventana steady delimitada por timestamps.
- `locust_exit_code: 0` con `--exit-code-on-error 1` ⇒ cero errores inesperados.

### Estadísticas reales de Locust (archivo `locust_smoke_20261116T220006_stats.csv`)

```
Type,Name,Request Count,Failure Count,...,50%,...,95%,...
GET,GET /api/accounts,216,0,...
GET,GET /api/transfers,103,0,...
POST,POST /api/transfers,37,0,...
,Aggregated,356,0,...
```

- **356 peticiones, 0 fallos.** La proporción observada (216 / 103 / 37 ≈ **60/30/10**) refleja la
  mezcla del locustfile (Tarea 19). Cero fallos confirma que las transferencias pasan los
  controles heredados (sin MFA por monto bajo, sin rechazos de límite por los saldos/límites
  amplios sembrados en la Tarea 18) — R10.3.
- `..._failures.csv` quedó vacío (solo cabecera), consistente con 0 fallos.

Artefactos preservados (con timestamp, sin sobrescribir — R9.6), en
`Etapa 3/Kiro/loadtest/results/`:

```
locust_smoke_20261116T220006_stats.csv
locust_smoke_20261116T220006_stats_history.csv
locust_smoke_20261116T220006_failures.csv
locust_smoke_20261116T220006_exceptions.csv
locust_20261116T220005.log      (stdout de Locust)
uvicorn_20261116T220005.log     (stdout del launcher/uvicorn)
```

## Verificación / aceptación

1. **Import limpio del módulo:**
   ```
   > backend\.venv\Scripts\python.exe -c "import loadtest.run_loadtest as r; import loadtest._uvicorn_launcher as l; print('imports OK')"
   imports OK
   ```
2. **Ejecución end-to-end:** el runner completa la corrida y emite estadísticas de Locust
   (356 req / 0 fallos) — caso (a) de la aceptación. El camino de fallo (b) está verificado
   arriba (fail-loud ante servidor no disponible).
3. **Suite backend completa — 344 green (sin regresiones):**
   ```
   > backend\.venv\Scripts\python.exe -m pytest -q   (desde backend/)
   344 passed, 1 warning in 19.07s
   EXITCODE=0
   ```
4. **Defaults = contrato exacto 30 / 5 / 60-steady-after-ramp:** confirmado (sección de defaults).

## Honestidad sobre lo que realmente corrió

- El entorno **sí** soporta la prueba (puerto local, subprocesos, Locust): se ejecutó un smoke
  real de **mecánica** con 5 s de steady (no 60 s) para que terminara rápido. El smoke NO es el
  baseline oficial y está así rotulado en salida, en el `RunResult` y en los nombres de archivo.
- **No se fabricó** ningún baseline. El baseline de 60 s de steady se captura en la Tarea 23.
- Durante la implementación se encontraron y corrigieron dos problemas reales: (1) la app no lee
  `DB_PATH` del entorno → se añadió `_uvicorn_launcher` para parchear la ruta en el hijo (si no,
  la DB histórica se tocaba); (2) `stdout=PIPE` colgaba Locust por buffer lleno → se pasó a logs
  en archivo. Ambos quedaron verificados tras la corrección (`DB histórica intacta: True`,
  corrida finaliza con exit 0).
