# E2 · Kiro · Sesión de implementación 05 — Tarea 5

- **Fecha:** 2026-11-16
- **Tarea:** 5 — (verificación) Pruebas de regresión: contratos de API e historial
- **Objetivo:** fijar los invariantes del contrato público de la Etapa 1 (formas de respuesta,
  códigos HTTP, estructura de error, formato/orden del historial, no exposición de IDs internos)
  como base de compatibilidad para la Etapa 2, sin duplicar exhaustivamente las tareas 2–4.
- **Estado final:** COMPLETED

## Estado del repositorio

- **Commit:** `ebf1017748928b30a9a5ad68a56b9b532f304e86` (sin commit nuevo).
- **Etapa 1 (`Etapa 1/Kiro`):** git limpio, sin cambios.
- **DB histórica E1 (`shift_bank.db`):** 36 864 bytes, 13/10/2026 2:58:26 p. m. — sin modificar.

## Contratos de API inspeccionados (fuente de los asertos)

- `GET /api/accounts` → `{accounts:[{name,balance}]}`.
- `POST /api/transfers` → **201** en ambos casos: sin MFA `{status:"COMPLETED",
  mfa_required:false}`; con MFA `{status:"PENDING_MFA", mfa_required:true, reference, expires_at}`.
- `POST /api/transfers/{reference}/mfa` → 200 `{status:"COMPLETED"}`; errores con códigos
  mapeados (INVALID_MFA_CODE 401, EXPIRED 409, INSUFFICIENT_FUNDS 409, NOT_FOUND 404).
- `GET /api/transfers` → `{transfers:[{date, direction:{from,to}, amount, description, status}]}`,
  orden `created_at DESC, rowid DESC`; `TransferDirection` serializa `from` (alias de salida);
  2 históricas sembradas con `created_at` en el pasado.
- Errores → `{error:{code,message}}`.

No se modificó código de aplicación; las pruebas verifican el contrato tal cual.

## Archivos creados / modificados

| Acción | Archivo |
|---|---|
| Creado | `Etapa 2/Kiro/backend/tests/test_regression_api_contracts.py` (13 pruebas) |
| Modificado | `Etapa 2/Kiro/.kiro/specs/shift-bank-stage2/tasks.md` (marcada solo la Tarea 5) |

Sin cambios en código de aplicación, requisitos, diseño, Etapa 1 ni registros previos.

## Casos de prueba introducidos (13) y su propósito

**A. Compatibilidad del contrato público:**
- `test_contrato_get_accounts` — forma exacta de `GET /api/accounts`.
- `test_contrato_creacion_sin_mfa` — 201 COMPLETED, reference/expires_at nulos (campos opcionales).
- `test_contrato_creacion_con_mfa` — 201 PENDING_MFA con reference y expires_at (`Z`).
- `test_contrato_confirmacion_mfa` — confirmación correcta → 200 `{status:"COMPLETED"}`.

**B. Historial:**
- `test_historial_estructura_y_campos` — 5 campos exactos, `direction{from,to}`, estados
  MAYÚSCULAS, nombres amigables.
- `test_historial_historicas_y_nueva` — 2 históricas persisten + nueva COMPLETED.
- `test_historial_pending_observable` — PENDING_MFA observable en historial.
- `test_historial_orden_desc_por_fecha` — nueva primero; fechas no crecientes.
- `test_historial_sin_identificadores_internos` — sin id/uuid/reference/kind/requires_mfa/
  expires_at/completed_at.
- `test_historial_montos_decimal_string_2_decimales` — montos decimal-string 2 decimales.

**C. Contratos de error:**
- `test_estructura_de_error_publica` — forma `{error:{code,message}}` con tipos.
- `test_codigos_y_http_de_errores_representativos` — SAME_ACCOUNT/NON_POSITIVE_AMOUNT/
  INVALID_AMOUNT 400, INVALID_MFA_CODE 401, NOT_FOUND 404; sin cambios de saldo tras los rechazos.

**D. Preservación para el historial unificado:**
- `test_internas_no_tienen_campos_ach` — las internas de E1 **no** exponen `type` ni
  `beneficiary` (contrato heredado estricto; base para añadir ACH de forma aditiva sin alterar
  internas).

## Comandos ejecutados y resultados reales

1. `python -m pytest tests/test_regression_api_contracts.py -v` → **13 passed, 29 warnings in
   1.13s** (exit 0).
2. `python -m pytest -q` (suite completa) → **51 passed, 101 warnings in 2.98s** (exit 0):
   4 (T1) + 8 (T2) + 12 (T3) + 14 (T4) + 13 (T5). Tareas 1–4 siguen pasando.

- Passed: **51** · Failed: **0** · Skipped: **0** · Warnings: 101 (deprecation, no bloqueantes).

### Advertencias (no bloqueantes)

- `DeprecationWarning: on_event is deprecated` (patrón heredado de E1; migración en Tarea 12) y
  alias de anyio en `TestClient`.

## Hallazgos de compatibilidad (historial y errores)

- El contrato de internas es estable y estricto: exactamente 5 campos, sin `type`/`beneficiary`.
  Esto confirma que el futuro historial unificado de la Etapa 2 podrá **añadir** entradas ACH y
  un campo `type` de forma aditiva sin alterar la representación de las internas (D03/D05).
- La estructura de error `{error:{code,message}}` y los códigos/HTTP son consistentes; los
  rechazos no producen cambios financieros.

## Evidencia de aislamiento y preservación de la Etapa 1

- `shift_bank.db` no existe en `Etapa 2/Kiro/backend` (solo DB temporales); sin residuos.
- DB histórica de E1 sin cambios (tamaño/fecha idénticos). `Etapa 1/Kiro` git limpio.

## Errores / correcciones

- Ninguno. 13/13 en la primera ejecución; el contrato observado coincide con la Etapa 1. No se
  corrigió comportamiento heredado.

## Métricas

- **Duración:** N/D (no instrumentada); pytest reportó 1,13 s (T5) y 2,98 s (suite).
- **Tokens / créditos / interacciones de herramientas:** N/D (no expuestos). No se estiman.

## Alcance / restricciones respetadas

- Solo se ejecutó la Tarea 5. Tareas 6–46 sin iniciar y sin marcar; Tareas 1–4 preservadas.
- No se introdujeron campos ni estados de ACH en las expectativas heredadas.
- No se implementó ACH/recurrentes/límites; no se cambió lógica de negocio ni contratos de API;
  no se tocó la Etapa 1 ni registros previos; sin dependencias nuevas.
- **No** se reclama que el checkpoint del baseline (Tarea 6) esté completo.
