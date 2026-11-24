# E4 — Iteración 04

## Fecha/hora y fase
- Fecha/hora: 2026-11-18 (America/Bogota).
- Fase/milestone: M4 (operaciones currency-aware: conversiones, internas, límites/MFA USD, guardias
  ACH/recurrentes).

## Tareas principales completadas y progreso
- Progreso de tareas principales: **15/31**.
- Completadas en esta iteración: Tareas 12, 13, 14, 15.

## Actividades y decisiones técnicas
- T12 (`conversion_service.py` + `routers/conversions.py`): `POST /api/conversions` convierte vía
  `fx` (tasa racional exacta, `ROUND_HALF_UP` una vez), emite evento COMPUESTO (debited+credited,
  mismo `operation_id`, D-09) y pasa por el patrón idempotente (idempotencia + versión optimista +
  atomicidad). Expone tasa, origen, destino y `event_ids` (D-03, R4). Nuevo `GET /api/v2/accounts`
  con `public_id`/moneda/saldo/versión (D-01/D-02/D-10).
- T13: `POST /api/v2/transfers` transferencia interna SOLO misma moneda; cross-currency -> 422
  `CROSS_CURRENCY_NOT_ALLOWED` remitiendo a `/api/conversions` (D-04).
- T14 (`limit_service`): `check_usd` y `daily_consumption_usd_minor` en equivalente USD (límite op
  5000.00, diario 10000.00, día UTC), consumo derivado de eventos de dominio de débito;
  `fx.requires_mfa_usd` con umbral estricto `>1000.00` sin redondear (D-07). Verificación dentro de
  la transacción (LIM-07).
- T15 (`currency_guard.py`): ACH solo desde USD; recurrente interno misma moneda; recurrente ACH
  solo USD (D-08, R12). Guardias en el borde, sin reescribir la lógica financiera heredada (DK-05);
  ciclo ACH exactamente-una-vez y scheduler único preservados.
- Integración en endpoints reales (condición del investigador): la aceptación de la Etapa 4 se
  prueba por HTTP con la fixture D-02 (`stage4_app_client`); endpoints v2 para no romper el
  contrato heredado (Path A). Headers de comando: `Idempotency-Key` (UUID, obligatorio) y
  `Expected-Version` (JSON por `public_id`, opcional).

## Archivos creados o modificados
- Creados: `backend/app/conversion_service.py`, `backend/app/routers/conversions.py`,
  `backend/app/currency_guard.py`, `backend/tests/test_conversion_api.py`,
  `backend/tests/test_limits_usd.py`, `backend/tests/test_currency_guard.py`.
- Modificados: `backend/app/limit_service.py` (funciones USD), `backend/app/main.py` (registro del
  router de conversiones).
- Specs: `tasks.md` y `tasks.meta.json` (12–15 completas).

## Pruebas ejecutadas (reales)
- `test_conversion_api.py`: **10 passed**, exit 0 (sobre fixture D-02 por HTTP).
- `test_limits_usd.py`: **4 passed**, exit 0.
- `test_currency_guard.py`: **4 passed**, exit 0.
- Regresión completa del backend tras M4: **428 passed, 1 warning**, exit 0.

## Errores, reintentos y correcciones
- Observado y corregido: `test_limits_usd.py` usaba el literal Python `1000_00` dentro de SQL, que
  SQLite rechaza (`unrecognized token`). Corregido a `100000`; prueba verde tras el reintento.

## Rutas de evidencia
- Código/pruebas bajo `Kiro/backend/app/` y `Kiro/backend/tests/`.
- Specs: `Kiro/.kiro/specs/shift-bank-stage4/`.

## Interacciones de modelo, llamadas a herramientas, tiempo y créditos
- Modelo: Auto. Métricas exactas de esta iteración: **N/D** (no disponibles directamente). D1 PRE
  del nuevo account: 30.24/969.76 (2026-11-18). No se inventan totales.

## Bloqueadores, limitaciones y próxima actividad
- Bloqueadores: ninguno técnico. Gates obligatorios pendientes: T28 (SonarQube PRE), T30 (POST).
- Limitación: los endpoints v2 de la Etapa 4 (conversiones/transferencias) aplican límites y
  guardias; el flujo MFA interactivo multidivisa completo (estado PENDING + confirmación) sobre v2
  se consolidará si la verificación de M6 lo exige; el umbral MFA USD ya está implementado y
  probado a nivel de dominio (`fx.requires_mfa_usd`).
- Próxima actividad: M5 — Tarea 16 (tipos/cliente/headers frontend), Tarea 17 (dashboard
  multidivisa + formulario de conversión), con Vitest y build.
