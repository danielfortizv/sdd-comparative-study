# E4 — Iteración 03

## Fecha/hora y fase
- Fecha/hora: 2026-11-18 (America/Bogota).
- Fase/milestone: M3 (Idempotencia y concurrencia optimista).

## Tareas principales completadas y progreso
- Progreso de tareas principales: **11/31**.
- Completadas en esta iteración: Tarea 11.

## Actividades y decisiones técnicas
- T11 (`app/idempotency.py`): integra sobre el patrón de comando dos controles en el orden de
  DK-04.
  - `Idempotency-Key` UUID obligatorio (`require_uuid_key`); `request_hash` canónico (SHA-256 del
    payload normalizado) para distinguir replay exacto de reuse con payload distinto.
  - **Replay idempotente ANTES que versión (DK-04):** replay exacto devuelve la respuesta original
    sin nuevos efectos; reuse con payload distinto -> 409 `IDEMPOTENCY_CONFLICT`.
  - Versión optimista por cuenta: mismatch -> 409 `ACCOUNT_VERSION_CONFLICT`.
  - Registro de idempotencia insertado en la MISMA `financial_transaction` que aplica los efectos
    (D-11, D-13-4): no hay efecto sin registro ni registro sin efecto. Re-chequeo dentro de la
    transacción para carreras con la misma clave.

## Archivos creados o modificados
- Creados: `backend/app/idempotency.py`, `backend/tests/test_idempotency.py`.
- Specs: `tasks.md` y `tasks.meta.json` (11 completa).

## Pruebas ejecutadas (reales)
- `test_idempotency.py`: **5 passed**, exit 0 (uuid key; replay exacto sin nuevos efectos; payload
  distinto -> 409; versión obsoleta -> 409 sin efectos; replay precede a versión).
- Regresión completa del backend tras M3: **410 passed, 1 warning**, exit 0.

## Errores, reintentos y correcciones
- Sin fallos; pasaron en la primera ejecución.

## Rutas de evidencia
- `Kiro/backend/app/idempotency.py`, `Kiro/backend/tests/test_idempotency.py`.
- Specs: `Kiro/.kiro/specs/shift-bank-stage4/`.

## Interacciones de modelo, llamadas a herramientas, tiempo y créditos
- Modelo: Auto. Métricas exactas de esta iteración: **N/D** (no disponibles directamente). D1 PRE
  del nuevo account: 30.24/969.76 (2026-11-18). No se inventan totales.

## Bloqueadores, limitaciones y próxima actividad
- Bloqueadores: ninguno técnico. Gates obligatorios pendientes: T28 (SonarQube PRE), T30 (POST).
- Próxima actividad: M4 — Tarea 12 (conversión FX `/api/conversions` vía patrón idempotente),
  Tarea 13 (internas misma-moneda), Tarea 14 (límites/MFA en equivalente USD), Tarea 15 (guardias
  de divisa ACH/recurrentes). Estas tareas también migran las pruebas heredadas al modelo
  multidivisa (condición del investigador: aceptación con fixture D-02).
