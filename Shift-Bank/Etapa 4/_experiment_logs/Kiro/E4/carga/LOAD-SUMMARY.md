# Stage 4 — Carga en vivo (Tarea 24) — evidencia real

## Comando exacto
```
PYTHONIOENCODING=utf-8 SHIFT_LOAD_USERS=30 SHIFT_LOAD_SPAWN=5 SHIFT_LOAD_STEADY=60 \
  backend/.venv/Scripts/python.exe -m loadtest.run_loadtest_stage4
```
Arnés: `loadtest/run_loadtest_stage4.py` (reusa el runner robusto heredado) + locustfile
multidivisa `loadtest/locustfile_stage4.py` + aislamiento D-02 `isolation.setup_loadtest_db_stage4`.
Servidor FastAPI vivo (uvicorn) sobre DB SQLite sintética aislada; claves de SOLO carga; la DB
histórica queda intacta (verificado por el runner).

## Configuración (contrato exacto)
- 30 usuarios concurrentes · ramp 5 usuarios/s (6 s) · 60 s de estado estable tras el ramp.
- `mechanics_smoke: False` (corrida oficial, no smoke). Locust exit code **0**.

## Métricas reales (CSV Locust `_stats.csv`)
Total de peticiones: **8,409**, **0 fallos** (Failures/s = 0 en todas las rutas).

| Ruta | Count | % | p50 (ms) | p95 (ms) | Máx (ms) |
|---|---|---|---|---|---|
| GET /api/v2/accounts | 5,084 | 60.5% | 10 | 53 | 341 |
| GET /api/transfers | 2,518 | 29.9% | 10 | 61 | 403 |
| POST /api/conversions | 403 | 4.8% | 18 | 73 | 325 |
| POST /api/v2/transfers | 404 | 4.8% | 19 | 71 | 270 |
| Aggregated | 8,409 | 100% | 13 | 59 | 403 |

Throughput agregado ≈ **128.7 req/s**. Distribución real medida ≈ 60/30/10 (lecturas/historial/
operaciones; las operaciones se reparten ~mitad conversión, ~mitad interna).

## Umbrales de aceptación (Etapa 3, aplicados a Etapa 4)
- p95 lectura **< 200 ms**: accounts 53 ms, history 61 ms → **CUMPLE**.
- p95 operación **< 500 ms**: conversiones 73 ms, transferencias 71 ms → **CUMPLE**.
- Errores inesperados **< 1%**: 0 / 8,409 = **0%** → **CUMPLE**.
- 409 esperados (idempotencia/versión): 0 (claves únicas, versiones vigentes). Sin errores de
  transporte/5xx.

## Invariantes post-carga (corrida con verificación)
Ejecutada una corrida con verificación ANTES del teardown (DB aún presente):
`invariants_ok=True` — `projection_consistency`, `no_duplicate_versions`,
`internal_conservation_per_currency`, `rebuild_matches`; **audit_chain_ok=True**.
(Verificador: `loadtest/verify_invariants_stage4.py` + `audit.verify_chain`.)

## Veredicto
Carga en vivo Etapa 4: **PASS** — todos los umbrales cumplidos y cero violaciones de invariantes
financieros/de eventos/proyección/auditoría. Evidencia cruda:
`loadtest/results_stage4/locust_run_*_stats.csv` (+ failures), `carga/locust-official-run.txt`,
`carga/load-invariants-live.txt`, `carga/smoke-mechanics.txt`.
```
NOTA: la `internal_conservation_per_currency` cubre transferencias internas (suma 0 por moneda);
las conversiones cruzan monedas por diseño (débito USD + crédito EUR, no suman 0 entre monedas),
lo cual es correcto y no viola conservación (cada evento conserva dentro de su operación compuesta).
```
