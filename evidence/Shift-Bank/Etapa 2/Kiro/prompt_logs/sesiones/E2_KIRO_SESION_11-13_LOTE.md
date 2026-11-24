# E2 · Kiro · Sesión de implementación — Lote Tareas 11–13

- **Fecha:** 2026-11-16 · Etapa 2 · Herramienta: Kiro
- **Alcance:** ejecución en lote de las Tareas 11, 12 y 13 (cierre de la Fase B). Autorizado a
  ejecutar solo 11–13; detenerse antes de la Tarea 14 (Fase C).
- **Estado:** T11 COMPLETED · T12 COMPLETED · T13 COMPLETED.

## Ajuste de proceso experimental (registrado, sin modificar históricos)

Hasta la Tarea 10 el investigador autorizó **una tarea por interacción**. A partir de aquí el
investigador cambió a **ejecución por lotes** (varias tareas por interacción), con verificación
por tarea y una sola corrida de la suite completa al final del lote. Se registra este cambio de
protocolo como ajuste experimental. No se reescriben los registros de sesiones previas
(01–10), que mantienen el modelo por tarea.

## Tareas ejecutadas

### Tarea 11 — Siembra idempotente de límites por defecto
- `config.py`: `DEFAULT_PER_TRANSFER_LIMIT_CENTS = 500_000_000`,
  `DEFAULT_DAILY_LIMIT_CENTS = 1_000_000_000` (D01).
- `seed.py`: `seed_limits(conn)` — inserta la fila de `transfer_limit` del cliente mock solo si
  no existe (idempotente; no sobrescribe un límite modificado por el usuario). No altera `seed()`.

### Tarea 12 — Arranque por `lifespan`
- `main.py`: se reemplazó `@app.on_event("startup")` por un context manager `lifespan` y
  `FastAPI(lifespan=lifespan)`. `_initialize_database()` ejecuta el orden
  `init_schema → migrate → seed → seed_limits` (todo idempotente). El **lanzamiento del
  scheduler** queda explícitamente para la **Tarea 32** (puntos de arranque/apagado preparados
  con comentarios, sin implementar). Efecto colateral positivo: desaparecen los warnings de
  deprecación `on_event` (la suite pasó de 101 a 1 warning).

### Tarea 13 — Suite de migración sobre copia de DB de E1
- `tests/test_migration_suite.py` (7 pruebas): migración sobre una **copia real** de la DB
  histórica (`shutil.copy2`, original no tocada, hash verificado antes/después); migración E2E
  desde estado heredado reconstruido; idempotencia en múltiples "arranques"; `seed_limits`
  inserta valores por defecto; `seed_limits` idempotente (no sobrescribe); una sola fila de
  límite; inicialización por `lifespan` sin duplicar (vía `app_client`).

## Archivos creados / modificados

| Acción | Archivo |
|---|---|
| Modificado | `backend/app/config.py` (defaults de límites, D01) |
| Modificado | `backend/app/seed.py` (`seed_limits`) |
| Modificado | `backend/app/main.py` (lifespan) |
| Creado | `backend/tests/test_migration_suite.py` (7 pruebas) |
| Modificado | `.kiro/specs/shift-bank-stage2/tasks.md` (Tareas 11, 12, 13) |
| Creado | `_experiment_logs/Kiro/sesiones/E2_KIRO_SESION_11-13_LOTE.md` |

## Resumen del diff

- `config.py`: +2 constantes de límite (aditivo).
- `seed.py`: + función `seed_limits` (aditivo; `seed()` sin cambios).
- `main.py`: `on_event("startup")` → `lifespan`; misma inicialización + `seed_limits`; sin
  cambiar routers, CORS ni contratos.
- `db.py`: sin cambios en este lote (T7/T8).

## Comandos ejecutados y resultados reales

1. `python -m pytest tests/test_migration_suite.py -v` → **7 passed, 1 warning in 0.88s** (exit 0).
2. `python -m pytest` (suite completa, una vez al final) → **95 passed, 1 warning in 4.92s**
   (exit 0): 51 (Fase A) + 6 (T7) + 12 (T8) + 10 (T9) + 9 (T10) + 7 (lote). **Passed 95 ·
   Failed 0 · Skipped 0.**

## Errores y correcciones

- Ninguno. Las 7 pruebas del lote y las 95 de la suite pasaron en la primera ejecución.

## Verificación de regresión

- Las 88 pruebas previas siguen verdes. Sin aserciones debilitadas.
- Nota: la suite pasó de 101 a **1 warning** por la migración a `lifespan` (desaparecen los
  `DeprecationWarning: on_event`). Es una mejora esperada, no una regresión.

## Integridad de la base de datos histórica

- **Antes y después:** `407B0E132E76900FBF59412C31A2D8047A666F2BE1856BE1FF6B88531C89B4A8` —
  sin cambios. La prueba de copia real verifica además el hash de la original antes/después.
- `shift_bank.db` no existe en `Etapa 2/Kiro/backend`; sin DB temporales residuales.
- `Etapa 1/Kiro` git limpio.

## Métricas

- **Duración de la sesión:** N/D. pytest: 0,88 s (lote) y 4,92 s (suite).
- **Tokens / créditos / interacciones de herramientas:** N/D (no expuestos). No se estiman.

## Alcance / restricciones respetadas

- Solo se ejecutaron las Tareas 11–13. Tareas 14–46 sin iniciar y sin marcar; Tareas 1–10
  preservadas; total de 46 intacto.
- El scheduler (Tarea 32) NO se implementó; el `lifespan` solo deja los puntos preparados.
- No se implementó enforcement de límites, ACH ni recurrentes; no se tocó el frontend, contratos
  de API, requisitos/diseño, la Etapa 1 ni registros previos; sin dependencias nuevas.
- Sin blockers ni contradicciones de diseño.
