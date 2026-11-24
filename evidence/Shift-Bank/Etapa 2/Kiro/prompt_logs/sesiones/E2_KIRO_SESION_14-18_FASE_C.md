# E2 · Kiro · Sesión de implementación — Lote Fase C (Tareas 14–18)

- **Fecha:** 2026-11-16 · Etapa 2 · Herramienta: Kiro
- **Alcance:** Fase C — límites de transacción dinámicos (Tareas 14–18). Autorizado a ejecutar
  solo 14–18; detenerse antes de la Tarea 19.
- **Estado:** T14 ✅ · T15 ✅ · T16 ✅ · T17 ✅ · T18 ✅ — COMPLETED.

## Resumen de implementación

- **T14** `limit_service.py`: `get_limits` (defaults D01 si no hay fila), `update_limits`
  (valida con `money.parse_amount`; rechaza negativos/>2 decimales/no decimal; upsert; no
  modifica ante entrada inválida).
- **T15** consumo diario + verificación (alto riesgo → subtareas 15.1/15.2):
  `daily_consumption_cents(conn, now)` agrega sobre `transfer` en ventana de día UTC
  (`clock.utc_day_bounds`), contando internas `COMPLETED` + ACH `pending`/`settled` y excluyendo
  el resto; `check(conn, amount, now)` rechaza `> per_transfer` (LIM-03) o `consumo+amount >
  daily` (LIM-04), permite igualdad exacta (LIM-05).
- **T16** integración en internas (alto riesgo → subtareas 16.1–16.4):
  - `repository.apply_transfer_in_tx` (débito+crédito+estado **sin** gestionar la transacción);
    `apply_transfer` heredado **intacto** (lo delega para preservar su contrato).
  - `service.create_transfer` (camino COMPLETED): pre-chequeo de feedback + revalidación
    autoritativa de límites y débito dentro de una sola `financial_transaction` (F8/F9); si el
    límite falla → `FAILED` sin débito.
  - `service.confirm_mfa`: verificación de límites antes del débito, en la misma transacción
    (LIM-07/A14: un PIN correcto no salta el límite); si falla → `FAILED` sin débito.
  - `routers/transfers.py`: `LIMIT_EXCEEDED_PER_TRANSFER`/`LIMIT_EXCEEDED_DAILY` → HTTP 409.
- **T17** `routers/limits.py`: `GET /api/limits` (valores + `daily_consumed`/`daily_remaining`),
  `PUT /api/limits` (valida, `INVALID_LIMIT`); registrado en `main.py`.
- **T18** pruebas (incluye concurrencia T-8).

## Atomicidad (F8/F9) y orden (LIM-07)

La verificación autoritativa de límites + consumo diario + débito ocurren dentro de la **misma**
`financial_transaction` (`BEGIN IMMEDIATE`), tanto en la creación interna COMPLETED como en la
confirmación de MFA. El pre-chequeo previo solo da feedback temprano y se **revalida** dentro de
la transacción (evita TOCTOU). Orden: fondos → límites → (si aplica) MFA.

## Archivos creados / modificados

| Acción | Archivo |
|---|---|
| Creado | `backend/app/limit_service.py` |
| Creado | `backend/app/routers/limits.py` |
| Modificado | `backend/app/repository.py` (+`apply_transfer_in_tx`; `apply_transfer` lo delega) |
| Modificado | `backend/app/service.py` (integración de límites en create/confirm) |
| Modificado | `backend/app/routers/transfers.py` (mapa de errores de límite) |
| Modificado | `backend/app/main.py` (registro del router de límites) |
| Creado | `backend/tests/test_limits.py` (11 pruebas) |
| Modificado | `.kiro/specs/shift-bank-stage2/tasks.md` (Tareas 14–18 + subtareas 15/16) |
| Creado | `_experiment_logs/Kiro/sesiones/E2_KIRO_SESION_14-18_FASE_C.md` |

## Pruebas añadidas (11) y resultados

defaults D01; GET con consumo/disponibilidad; PUT actualiza/aplica; PUT rechaza inválidos sin
modificar; rechazo sobre límite por transferencia; frontera exacta por transferencia (A11);
consumo diario 400+300+300 OK y el siguiente excede (A12); frontera exacta diaria; PIN correcto
no salta el límite diario (A14); PENDING_MFA no cuenta para el consumo; **concurrencia con
conexiones SQLite distintas** (T-8): `BEGIN IMMEDIATE` de conn1 bloquea a conn2, y tras el commit
el `check` de conn2 falla por diario — sin sleeps, sincronización determinista.

- `python -m pytest tests/test_limits.py` → **11 passed, 1 warning** (exit 0).

## Errores y correcciones

- **1 fallo durante la implementación:** `test_pin_correcto_no_salta_limite_a14` asumía que un
  monto > límite diario llegaría a PENDING_MFA, pero el **pre-chequeo** de límite lo rechaza
  antes (comportamiento correcto). **Corrección del test** (no del código): crear la PENDING_MFA
  con límite holgado y **reducir el límite** entre creación y confirmación; así el PIN correcto
  falla por límite en la confirmación. No se debilitó ninguna aserción de regresión; se corrigió
  una suposición errónea del propio test nuevo.

## Checkpoint de regresión intermedio (T-7)

- Suite completa: `python -m pytest` → **106 passed, 0 failed, 0 skipped, 1 warning in 6.66s**
  (exit 0): 51 (Fase A) + 6 (T7) + 12 (T8) + 10 (T9) + 9 (T10) + 7 (lote B) + 11 (Fase C).
- Las 51 pruebas de regresión de la Fase A siguen **verdes** tras integrar límites en las
  internas: los defaults (5M/transfer, 10M/día) son holgados frente a los montos de las pruebas
  heredadas, por lo que no alteran su comportamiento observable.

## Integridad de la base de datos histórica

- SHA-256 `407B0E132E76900FBF59412C31A2D8047A666F2BE1856BE1FF6B88531C89B4A8` — sin cambios.
- `shift_bank.db` no existe en `Etapa 2/Kiro/backend`; sin DB temporales residuales; `Etapa 1/
  Kiro` git limpio.

## Conflictos con tests existentes

- Ninguno. Ningún test de baseline fue debilitado ni eliminado. La extensión de límites es
  aditiva sobre el camino interno; el contrato de API de internas no cambió (las respuestas y
  estados siguen igual). El campo `type` sigue sin exponerse en el historial (ajuste previsto en
  la Tarea 25).

## Métricas

- **Duración de la sesión:** N/D. pytest: 1,60 s (Fase C) y 6,66 s (suite).
- **Tokens / créditos / interacciones de herramientas:** N/D (no expuestos). No se estiman.

## Alcance / restricciones respetadas

- Solo Tareas 14–18. Tareas 19–46 sin iniciar; Tareas 1–13 preservadas; total de 46 intacto.
- No se implementó ACH, recurrentes ni scheduler. `apply_transfer` heredado no se alteró. No se
  tocó el frontend, la Etapa 1 ni registros previos; sin dependencias nuevas. Sin blockers.
