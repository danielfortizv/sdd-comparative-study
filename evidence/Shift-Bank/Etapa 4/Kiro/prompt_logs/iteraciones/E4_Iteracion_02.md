# E4 — Iteración 02

## Fecha/hora y fase
- Fecha/hora: 2026-11-18 (America/Bogota).
- Fase/milestone: M2 (Event Sourcing, CQRS y patrón de comando atómico).

## Tareas principales completadas y progreso
- Progreso de tareas principales: **10/31**.
- Completadas en esta iteración: Tareas 8, 9, 10.
- Nota: los conteos de pruebas son SUB-pruebas, no tareas principales.

## Actividades y decisiones técnicas
- T8 (`app/events.py`): almacén de eventos de dominio append-only sobre `domain_event`, separado
  de `audit_log` (D-05). Helpers sin commit para componerse en la transacción del comando;
  `current_version`, `read_events`, `read_operation` (evento compuesto por `operation_id`, D-09).
- T9 (`app/projections.py`): proyección CQRS síncrona (`apply_event_to_projection_no_commit`),
  reconstrucción determinista (`rebuild_projections`) desde los eventos, y `verify_consistency`
  (fail-closed) que compara saldo/versión proyectados contra la suma de eventos y `account.version`
  (D-06).
- T10 (`app/command.py`): patrón de comando atómico que, dentro de una sola
  `txn.financial_transaction`, aplica efecto(s) por cuenta (evento + proyección + `balance_cents`
  + bump de versión +1 por cuenta) y, opcionalmente, la auditoría, de forma atómica (D-09, D-11,
  DK-03). La idempotencia/versión esperada se integran en T11.
- Condiciones del investigador respetadas: la aceptación de la Etapa 4 se prueba con la fixture
  D-02 (`stage4_app_client` / `seed_stage4`); las pruebas heredadas (legacy) solo verifican
  compatibilidad hacia atrás; la app por defecto inicializa datos de la Etapa 4; selección de
  fixture explícita y determinista (`SHIFT_SEED_MODE`).

## Archivos creados o modificados
- Creados: `backend/app/events.py`, `backend/app/projections.py`, `backend/app/command.py`,
  `backend/tests/test_event_store.py`, `backend/tests/test_projection.py`,
  `backend/tests/test_command_atomicity.py`.
- Specs: `tasks.md` y `tasks.meta.json` (8–10 completas).

## Pruebas ejecutadas (reales)
- `test_event_store.py`: **4 passed**, exit 0.
- `test_projection.py`: **4 passed**, exit 0.
- `test_command_atomicity.py`: **3 passed**, exit 0.
- Regresión completa del backend tras M2: **405 passed, 1 warning**, exit 0.

## Errores, reintentos y correcciones
- Sin fallos en esta iteración; los tests pasaron en la primera ejecución tras escribir los
  módulos. La prueba de fallo inyectado confirma el rollback total (fail-closed) del comando.

## Rutas de evidencia
- Código/pruebas bajo `Kiro/backend/app/` y `Kiro/backend/tests/`.
- Specs: `Kiro/.kiro/specs/shift-bank-stage4/`.
- Regresión acumulada verificada localmente (405 passed).

## Interacciones de modelo, llamadas a herramientas, tiempo y créditos
- Modelo: Auto. Interacciones/tool-calls/tiempo/créditos exactos de esta iteración: **N/D** (no
  disponibles directamente en esta interfaz). D1 PRE del nuevo account: 30.24/969.76 (2026-11-18).
  No se inventan totales.

## Bloqueadores, limitaciones y próxima actividad
- Bloqueadores: ninguno técnico. Gates obligatorios pendientes: T28 (SonarQube PRE), T30
  (SonarQube POST) — requieren servidor y autorización; sin servicio FALLAN, no PASS.
- Próxima actividad: M3 — Tarea 11 (idempotencia `idempotency_key` + versión optimista esperada en
  el patrón de comando; replay ANTES que versión, DK-04/D-13/D-14).
