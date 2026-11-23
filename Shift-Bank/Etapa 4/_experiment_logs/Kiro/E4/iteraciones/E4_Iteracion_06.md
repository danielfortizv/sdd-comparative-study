# E4 — Iteración 06

## Fecha/hora y fase
- Fecha/hora: 2026-11-18/19 (America/Bogota).
- Fase/milestone: Reapertura T14/T15 (integración real) + M6 (verificación, regresión, cobertura,
  carga-invariantes, despliegue) + T26 (config SonarQube Etapa 4).

## Tareas principales completadas y progreso
- Progreso de tareas principales: **26/31** (completas: 1–24, 26; **25 PARCIAL**; 27–31 pendientes,
  con 28 y 30 como gates del investigador).

## Actividades y decisiones técnicas
- **T14 REABIERTA (contrato incompleto).** Antes solo existía el predicado `fx.requires_mfa_usd`;
  los endpoints v2 NO exigían MFA. Se implementó el flujo real: tabla `v2_pending_mfa`, respuesta
  `PENDING_MFA` sin mover saldo cuando el equivalente USD SIN redondear > 1000, y endpoint
  `POST /api/v2/mfa/{reference}` que confirma con el código heredado y aplica vía el comando
  idempotente. 6 pruebas de integración por HTTP (frontera 1000.00 vs 1000.01; confirmación;
  código incorrecto 401; conversión alto valor).
- **T15 REABIERTA (contrato incompleto).** Antes las guardias de `currency_guard.py` no se
  invocaban. Se integraron en `ach_service.create_ach` (ACH solo USD) y
  `recurring_service.create_schedule` (interno misma moneda; ACH solo USD, evaluado ANTES de la
  restricción heredada `_INTERNAL_KINDS`). 6 pruebas de integración sobre la fixture D-02.
- M6 verificación (T18–T21): lote de 48 pruebas (atomicidad, event store, proyección/rebuild,
  idempotencia, concurrencia Etapa 4 + heredada SQLite, ACH, scheduler) verde.
- T22 regresión completa: backend 444, Vitest 14, build 45 módulos. T23 cobertura: backend 94%
  (coverage.xml), frontend lcov.info (7.24% global — componentes React heredados sin pruebas
  unitarias, número honesto). T24 carga-invariantes: `verify_invariants_stage4.py` + lote de 40
  operaciones; invariantes multidivisa verdes (consistencia de proyección, sin versiones
  duplicadas, conservación por moneda, rebuild determinista). El benchmark Locust completo
  (servidor vivo, 30 usuarios, 60s) es el arnés heredado, NO ejecutado este segmento (no PASS).
- T25 despliegue PARCIAL: `docker compose config` exit 0 (2 servicios + healthcheck + red +
  volumen; `.env` desechable creado y eliminado). Ciclo build/up/smoke/HTTPS/persistencia/
  fail-closed NO ejecutado; NO marcado PASS.
- T26 SonarQube Etapa 4: `sonar-project-stage4.properties` con
  `sonar.projectKey=Shift-Bank---Stage-4---Kiro` (NUNCA la clave de la Etapa 3, que se preserva);
  rutas de cobertura backend/frontend presentes.

## Archivos creados o modificados
- Modificados: `backend/app/db.py` (tabla `v2_pending_mfa`),
  `backend/app/conversion_service.py` (MFA pending/confirm), `backend/app/routers/conversions.py`
  (gating MFA + endpoint confirm), `backend/app/ach_service.py` (guardia ACH USD),
  `backend/app/recurring_service.py` (guardias de divisa).
- Creados: `backend/tests/test_mfa_v2_api.py`, `backend/tests/test_currency_integration.py`,
  `backend/tests/test_stage4_concurrency.py`, `backend/tests/test_stage4_load_invariants.py`,
  `loadtest/verify_invariants_stage4.py`, `sonar-project-stage4.properties`,
  `_experiment_logs/Kiro/E4/despliegue/DEPLOYMENT-VALIDATION.md`.
- Specs: `tasks.md`, `tasks.meta.json` actualizados.

## Pruebas ejecutadas (reales)
- T14 MFA integración: **6 passed**, exit 0. T15 guardias integración: **6 passed** (tras corregir
  orden de guardia ACH), exit 0. M6 lote verificación: **48 passed**, exit 0.
- Regresión backend completa: **444 passed, 1 warning**, exit 0; cobertura **94%**.
- Frontend: Vitest **14 passed**, build **45 modules** exit 0; cobertura lcov generada.
- Carga-invariantes Etapa 4: **1 passed** (lote 40 ops), exit 0.
- `docker compose config`: exit **0** (con `.env` desechable eliminado).

## Errores, reintentos y correcciones
- T15: primera corrida de `test_currency_integration` falló (`INVALID_SOURCE` en vez de
  `RECURRING_ACH_NOT_USD`): la restricción heredada `_INTERNAL_KINDS` rechazaba el origen EUR antes
  de la guardia de divisa. Corrección: evaluar la guardia ACH-USD ANTES de `_INTERNAL_KINDS`; 6/6
  verdes tras el reintento.
- `docker compose config`: el compose declara `env_file: .env`; se validó con un `.env` desechable
  de claves de prueba, eliminado inmediatamente (patrón aislado).

## Rutas de evidencia
- `_experiment_logs/Kiro/E4/baseline/` (backend-regression-coverage.txt, frontend-coverage.txt,
  backend-regression-preT28.txt, vitest/build stage4).
- `_experiment_logs/Kiro/E4/despliegue/` (compose-config-ok.txt, DEPLOYMENT-VALIDATION.md).
- `backend/coverage.xml`, `frontend/coverage/lcov.info`, `sonar-project-stage4.properties`.

## Interacciones de modelo, llamadas a herramientas, tiempo y créditos
- Modelo: Auto. Métricas exactas de esta iteración: **N/D**. D1 PRE del nuevo account:
  30.24/969.76 (2026-11-18). No se inventan totales.

## Bloqueadores, limitaciones y próxima actividad
- **GATE OBLIGATORIO alcanzado: T28 (SonarQube PRE).** El escaneo PRE lo ejecuta el investigador,
  autenticado, contra `localhost:9000`, con `sonar.projectKey=Shift-Bank---Stage-4---Kiro` y las
  coberturas ya generadas. No se ejecuta escaneo ni corrección dirigida por Sonar antes del PRE.
- Pendientes: T25 completar despliegue end-to-end (bajo autorización); T27 PRE-scan (ejecución del
  investigador), T28 gate, T29 correcciones, T30 gate final, T31 evidencia/reporte.
- Próxima actividad: **DETENER** para el PRE-scan de SonarQube controlado por el investigador (T28).
