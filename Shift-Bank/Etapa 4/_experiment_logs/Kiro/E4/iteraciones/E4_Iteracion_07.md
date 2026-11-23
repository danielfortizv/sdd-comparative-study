# E4 — Iteración 07

## Fecha/hora y fase
- Fecha/hora: 2026-11-19 (America/Bogota).
- Fase/milestone: Cierre de M6 con verificación REAL — carga Locust en vivo (T24) y despliegue
  Docker en vivo (T25), antes del gate T28 (SonarQube PRE).

## Tareas principales completadas y progreso
- Progreso de tareas principales: **26/31** (1–26 completas; 27–31 pendientes; 28 y 30 son gates
  del investigador).
- Reconciliación: T24 y T25 pasan de evidencia supletoria/parcial a **PASS real en vivo**, sin
  borrar la evidencia histórica previa (se añadieron entradas nuevas en `tasks.meta.json`).

## Actividades y decisiones técnicas
- **T24 carga en vivo.** Arnés `loadtest/run_loadtest_stage4.py` (reusa el runner robusto
  heredado) + `locustfile_stage4.py` (mezcla 60/30/10 multidivisa) + aislamiento D-02
  (`isolation.setup_loadtest_db_stage4`, `SHIFT_SEED_MODE=stage4`). Servidor uvicorn vivo sobre DB
  sintética aislada; DB histórica intacta. Contrato exacto 30u/5s/60s.
- **T25 despliegue en vivo.** Certificado autofirmado desechable (vía `cryptography`), `.env`
  desechable; `docker compose build`+`up`; smoke por HTTPS; reinicio; auditoría; fail-closed;
  teardown `down -v` + borrado de `.env`/`certs`.
- Decisión honesta: la verificación de invariantes in-process previa (iteración 06) se reclasifica
  como SUPLETORIA; la aceptación de T24 ahora exige el benchmark en vivo con umbrales reales.

## Archivos creados o modificados
- Creados: `loadtest/locustfile_stage4.py`, `loadtest/run_loadtest_stage4.py`,
  `carga/LOAD-SUMMARY.md`, `despliegue/DEPLOYMENT-VALIDATION.md` (reescrita a PASS en vivo) y
  evidencia cruda en `carga/` y `despliegue/`.
- Modificados: `loadtest/isolation.py` (`seed_synthetic_db_stage4`, `setup_loadtest_db_stage4`),
  `tasks.md`/`tasks.meta.json` (T24/T25 reconciliadas).
- Temporales creados y ELIMINADOS: `certs/` (cert+key), `.env`, volumen `shift_db_data`,
  contenedores. Workspace restaurado a estado limpio.

## Pruebas ejecutadas (reales)
- Carga Locust oficial 30/5/60: **8,409 peticiones, 0 fallos**, exit 0. p95 lecturas 53/61 ms
  (<200), p95 operaciones 73/71 ms (<500), errores inesperados 0% (<1%). Distribución ~60/30/10.
- Invariantes post-carga (corrida con verificación en vivo): `invariants_ok=True`
  (projection_consistency, no_duplicate_versions, internal_conservation_per_currency,
  rebuild_matches) y `audit_chain_ok=True`.
- Despliegue: build/up exit 0; backend+nginx **healthy**; HTTPS 200 con fixture D-02; redirección
  **301**; conversión HTTPS 200 (9/10, 100 USD→90 EUR); persistencia tras `restart` (CHK 2400/v2,
  EUR 90/v2); `audit/verify` **{"ok":true}**; **fail-closed** con claves vacías (ConfigError,
  backend Restarting). `down -v` exit 0; cleanup verificado.

## Errores, reintentos y correcciones
- `openssl` del sistema/Git no operable (config path roto): se generó el certificado con
  `cryptography` (Python). Correcto al primer intento tras el cambio.
- Encoding Windows cp1252: el runner imprime `→`, que rompía stdout redirigido; corregido fijando
  `PYTHONIOENCODING=utf-8`. Smoke de mecánica (5u/3s) verde antes del run oficial.
- PowerShell: varias asignaciones `$env:` en una línea consumían la llamada; se envolvió en
  `& { ... }` para ejecutar de forma fiable.

## Rutas de evidencia
- `_experiment_logs/Kiro/E4/carga/` (LOAD-SUMMARY.md, locust-official-run.txt,
  load-invariants-live.txt, smoke-mechanics.txt) + `loadtest/results_stage4/locust_run_*_stats.csv`.
- `_experiment_logs/Kiro/E4/despliegue/` (DEPLOYMENT-VALIDATION.md, docker-build/up/ps/restart/
  down-final.txt, smoke.txt, persistence.txt, fail-closed.txt, cert-gen.txt).
- Cobertura: `backend/coverage.xml` (94%), `frontend/coverage/lcov.info`.

## Configuración exacta del escáner (para el PRE del investigador)
- Archivo: `Etapa 4/Kiro/sonar-project-stage4.properties`.
- `sonar.projectKey=Shift-Bank---Stage-4---Kiro` (NUNCA la clave de la Etapa 3, que se preserva en
  `sonar-project.properties`).
- `sonar.sources=backend/app,frontend/src`; `sonar.python.coverage.reportPaths=backend/coverage.xml`;
  `sonar.javascript.lcov.reportPaths=frontend/coverage/lcov.info`; `sonar.sourceEncoding=UTF-8`.
- Instancia del investigador: `localhost:9000` (escaneo autenticado, ejecutado por el investigador).

## Interacciones de modelo, llamadas a herramientas, tiempo y créditos
- Modelo: Auto. Métricas exactas de esta iteración: **N/D**. D1 PRE del nuevo account:
  30.24/969.76 (2026-11-18). No se inventan totales.

## Bloqueadores, limitaciones y próxima actividad
- **GATE OBLIGATORIO: T28 (SonarQube PRE).** DETENER antes del escaneo. No se ejecuta SonarQube ni
  corrección dirigida por Sonar antes del PRE; la Etapa 3 no se modifica.
- Pendientes tras el PRE: T27 (ejecución PRE del investigador), T28 gate, T29 correcciones, T30
  gate final, T31 evidencia/reporte.
