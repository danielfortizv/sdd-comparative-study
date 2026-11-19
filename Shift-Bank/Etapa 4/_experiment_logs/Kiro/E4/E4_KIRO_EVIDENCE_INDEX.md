# Etapa 4 — Kiro — Índice de evidencia

Raíz: `Etapa 4/_experiment_logs/Kiro/E4/`. Todas las rutas son relativas a esa raíz salvo nota.
Las copias crudas se preservan sin modificación; los documentos de consolidación referencian estas
fuentes.

## Documentos de consolidación (T31)
- `E4_KIRO_FINAL_REPORT.md` — reporte final completo.
- `E4_KIRO_METRICS_SUMMARY.md` — métricas consolidadas (tradicional y MQR separadas; D1).
- `E4_KIRO_EVIDENCE_INDEX.md` — este índice.
- `E4_KIRO_LIMITATIONS.md` — limitaciones y amenazas metodológicas.

## Specs nativos (fuera de _experiment_logs)
- `Kiro/.kiro/specs/shift-bank-stage4/requirements.md` (20 req, 81 EARS).
- `Kiro/.kiro/specs/shift-bank-stage4/design.md`.
- `Kiro/.kiro/specs/shift-bank-stage4/tasks.md` (31 tareas; 31/31 [x]).
- `Kiro/.kiro/specs/shift-bank-stage4/tasks.meta.json` (olas + historial de ejecución + gates).

## Iteraciones (bitácora académica en español)
- `iteraciones/E4_Iteracion_01.md` … `E4_Iteracion_11.md` (01 M0/M1; 02 M2; 03 M3; 04 M4; 05 M5;
  06 M6 verificación+Sonar config; 07 carga+despliegue en vivo; 08 PRE verificado; 09 T28/T29;
  10 POST; 11 cierre T30/T31).

## M0 — baseline y entorno (`baseline/`)
- `BASELINE-SUMMARY.md`; `backend-pytest-baseline.txt` (372 passed);
  `frontend-vitest-baseline.txt` (3 passed); `frontend-build-baseline.txt` (41 módulos);
  `environment-versions-20261118-232453.txt`; `pip-install.log`; `frontend-npm-install.log`.
- Regresión acumulada: `backend-regression-coverage.txt`, `backend-regression-preT28.txt`.
- Frontend Stage 4: `frontend-vitest-stage4*.txt`, `frontend-build-stage4*.txt`,
  `frontend-coverage.txt`.

## D1 — medición de créditos (`D1/`)
- `D1-credit-snapshot-stage4.md` — snapshot PRE del NUEVO account (30,24/969,76, 2026-11-18).
  Deltas de consumo/uso de sesión: N/D (ver Limitaciones y Metrics Summary §7).

## Carga en vivo (`carga/`)
- `LOAD-SUMMARY.md` (veredicto + tabla de métricas); `locust-official-run.txt` (30/5/60, exit 0);
  `smoke-mechanics.txt` (smoke 5/3); `load-invariants-live.txt` (invariantes post-carga + audit).
- CSV crudos de Locust (fuera de _experiment_logs): `Kiro/loadtest/results_stage4/locust_run_*`
  (`_stats.csv`, `_failures.csv`, `_stats_history.csv`) y `uvicorn_*.log`.

## Despliegue Docker (`despliegue/`)
- `DEPLOYMENT-VALIDATION.md` (veredicto PASS en vivo); `docker-build.txt`; `docker-up.txt`;
  `docker-ps.txt`; `smoke.txt` (HTTPS 200/redirect 301/conversión 200); `persistence.txt`
  (restart); `docker-restart.txt`; `fail-closed.txt` (ConfigError); `docker-up-failclosed.txt`;
  `docker-down-fc.txt`; `docker-down-final.txt` (down -v); `cert-gen.txt`; `compose-config.txt`,
  `compose-config-ok.txt` (validación de config).

## SonarQube (`sonarqube/`)
- **PRE** (`20261119-004700_T27_PRE_*`): `ce_task.json` (SUCCESS, analysisId cd37bcc9),
  `quality_gate.json` (OK), `measures.json`, `issues_unresolved_p1.json` (162),
  `issues_resolved_p1.json` (0), `rules_metadata.json`, `backend_coverage.xml`,
  `frontend_lcov.info`, `original_coverage.xml`, `properties.txt`, `scanner.log`,
  `export_summary.json`.
- **POST** (`20261119-011552_T30_POST_*`): `ce_task.json` (SUCCESS, analysisId bb7434e4),
  `quality_gate.json` (OK), `measures.json`, `issues_unresolved_p1.json` (158),
  `issues_resolved_p1.json` (4), `rules_metadata.json`, `backend_coverage.xml`,
  `frontend_lcov.info`, `original_coverage.xml`, `properties.txt`, `scanner.log`,
  `scanner_exit_code.txt` (0).
- **T29** (pasada correctiva): `T29_CORRECTIVE_RECORD.md`, `T29_vitest.txt`, `T29_build.txt`,
  `T29_backend_regression.txt`, `T29_backend_coverage.txt`, `T29_frontend_coverage.txt`.
- Histórico: `T27-STATUS-BLOCKED.md` (bloqueo transitorio previo a disponer de la evidencia PRE).

## Artefactos de cobertura (fuera de _experiment_logs)
- `Kiro/backend/coverage.xml` (Cobertura XML, regenerado T29, misma metodología).
- `Kiro/frontend/coverage/lcov.info` (v8 lcov, regenerado T29).
- Copias PRE/POST de ambos preservadas en `sonarqube/*_backend_coverage.xml` /
  `*_frontend_lcov.info` / `*_original_coverage.xml`.

## Verificación de integridad de evidencia
- Config del escáner PRE==POST: `*_PRE_properties.txt` byte-idéntico a `*_POST_properties.txt`.
- Issues por clave: 4 resueltos (keys 1c9b78d4 S2245, 9a8ff686 S7767, 1dd96ef1/6f57b9f8 S6759),
  0 introducidos (comparación de `key` PRE vs POST).
- `original_coverage.xml` difiere PRE vs POST SOLO por el cambio de código (ncloc 6249→6261);
  metodología/alcance idénticos.

## Incidente NO relacionado con el escáner (registrado)
- En la exportación POST, el paso de PowerShell que escribía `*_POST_export_summary.json` **falló**
  (por eso ese archivo no existe, a diferencia del PRE). **El escaneo SÍ tuvo éxito**: `scanner.log`
  POST muestra `ANALYSIS SUCCESSFUL` y `EXECUTION SUCCESS`, `scanner_exit_code.txt` = 0, y el
  `ce_task.json` POST reporta `status=SUCCESS`. Es un fallo del script de exportación de resumen,
  no del análisis ni de los datos exportados (ce_task, quality_gate, measures, issues, coverage y
  log POST están completos y verificados).
