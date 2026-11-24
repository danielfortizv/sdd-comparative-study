# E2 · Kiro · Sesión de implementación 03 — Tarea 3

- **Fecha:** 2026-11-16
- **Tarea:** 3 — (verificación) Pruebas de regresión: transferencias internas
- **Objetivo y alcance:** fijar el comportamiento heredado de las transferencias internas
  (ruta **sin MFA**, montos < umbral 1.000.000), su registro en historial y sus validaciones,
  usando el arnés aislado. La regresión exhaustiva de MFA corresponde a la Tarea 4 y **no** se
  ejecutó aquí.
- **Estado final:** COMPLETED

## Estado del repositorio

- **Commit:** `ebf1017748928b30a9a5ad68a56b9b532f304e86` (sin commit nuevo).
- **Etapa 1 (`Etapa 1/Kiro`):** git limpio, sin cambios.
- **DB histórica E1 (`shift_bank.db`):** 36 864 bytes, 13/10/2026 2:58:26 p. m. — sin modificar.

## Comportamiento heredado observado (fuente de los asertos)

- `POST /api/transfers` → **201** `{status, mfa_required, reference?, expires_at?}`; sin MFA:
  `{status:"COMPLETED", mfa_required:false}`.
- Errores `{error:{code,message}}`: `SAME_ACCOUNT` 400, `NON_POSITIVE_AMOUNT` 400,
  `INVALID_AMOUNT` 400, `INSUFFICIENT_FUNDS` 400 (al crear).
- `GET /api/transfers` → `{transfers:[{date, direction:{from,to}, amount, description,
  status}]}`, orden `created_at DESC`; estados internos en MAYÚSCULAS; 2 históricas sembradas
  (500.000 S→C, 100.000 C→S) que no afectan los saldos iniciales.
- `apply_transfer` mueve ambos saldos atómicamente; request con alias `from`; montos
  decimal-string; saldos en centavos enteros.

No se modificó ningún archivo de aplicación; las pruebas verifican el contrato tal cual.

## Archivos creados / modificados

| Acción | Archivo |
|---|---|
| Creado | `Etapa 2/Kiro/backend/tests/test_regression_internal_transfers.py` (12 pruebas) |
| Modificado | `Etapa 2/Kiro/.kiro/specs/shift-bank-stage2/tasks.md` (marcada solo la Tarea 3) |

Sin cambios en código de aplicación, requisitos, diseño, Etapa 1 ni registros previos.

## Casos de prueba introducidos (12)

**1. Transferencias exitosas (sin MFA):**
- `test_transferencia_interna_exitosa_sin_mfa` — < umbral → 201 COMPLETED, `mfa_required=false`.
- `test_debito_y_credito_correctos_y_total_preservado` — débito origen, crédito destino, total
  conservado (centavos).
- `test_api_refleja_los_nuevos_saldos` — `GET /api/accounts` refleja los saldos actualizados.

**2. Historial:**
- `test_historial_tiene_dos_historicas_al_inicio` — 2 históricas COMPLETED al arrancar.
- `test_nueva_transferencia_se_registra_y_preserva_historicas` — nueva añadida (3 total), sin
  borrar históricas.
- `test_estructura_e_estados_del_historial_heredados` — forma heredada + estados MAYÚSCULAS +
  nombres amigables + monto decimal-string.

**3. Validación:**
- `test_rechaza_misma_cuenta` — `SAME_ACCOUNT` 400, sin mover saldos.
- `test_rechaza_monto_no_positivo` — `NON_POSITIVE_AMOUNT` 400 (0 y negativo), sin mover saldos.
- `test_rechaza_decimales_no_soportados` — `INVALID_AMOUNT` 400 (>2 decimales), sin mover saldos.
- `test_rechaza_fondos_insuficientes` — `INSUFFICIENT_FUNDS` 400 en ruta sin MFA, sin mover
  saldos (se drena Checking con operaciones válidas < umbral hasta dejar < umbral y luego se
  intenta exceder el remanente).

**4. Consistencia financiera:**
- `test_rechazo_no_causa_movimiento_parcial` — varios inválidos no mueven saldos.
- `test_representacion_centavos_y_decimal_string` — saldos enteros en DB; decimal-string 2
  decimales en API (0,01 COP exacto).

## Comandos ejecutados y resultados reales

1. `python -m pytest tests/test_regression_internal_transfers.py -v` → **12 passed, 27 warnings
   in 1.24s** (exit 0).
2. `python -m pytest -q` (suite completa) → **24 passed, 47 warnings in 1.94s** (exit 0):
   4 (arnés, T1) + 8 (cuentas, T2) + 12 (internas, T3). Tareas 1 y 2 siguen pasando.

- Passed: **24** · Failed: **0** · Skipped: **0** · Warnings: 47 (deprecation, no bloqueantes).

### Advertencias (no bloqueantes)

- `DeprecationWarning: on_event is deprecated` (patrón heredado de E1; migración en Tarea 12) y
  alias de anyio en `TestClient`. No afectan a la validez de las pruebas.

## Evidencia de atomicidad y consistencia financiera verificada

- Débito+crédito aplicados juntos; total de ambas cuentas conservado tras transferencia interna.
- Ningún request inválido (misma cuenta, monto ≤ 0, >2 decimales, fondos insuficientes) produce
  movimiento parcial: saldos idénticos antes/después (verificado en centavos contra la DB
  aislada).
- Representación: centavos enteros en persistencia; decimal-string de 2 decimales en la API.

## Evidencia de aislamiento y preservación de la Etapa 1

- `shift_bank.db` no existe en `Etapa 2/Kiro/backend` (solo DB temporales); sin residuos tras la
  ejecución.
- DB histórica de E1 sin cambios (tamaño/fecha idénticos). `Etapa 1/Kiro` git limpio.

## Inconsistencias del baseline / correcciones

- Ninguna. Las 12 pruebas pasaron en la primera ejecución; el comportamiento observado coincide
  con el contrato heredado. No se corrigió comportamiento de la Etapa 1.

## Criterios de completitud (Tarea 3)

Transferencia exitosa sin MFA, débito/crédito/total, historial (nueva + históricas + forma +
estados MAYÚSCULAS), validaciones (misma cuenta, no positivo, decimales, fondos), consistencia
financiera y representación monetaria: **todos verificados**. Tareas 1 y 2 siguen pasando.
Cobertura de MFA/Etapa 2 **no** reclamada (fuera de alcance).

## Métricas

- **Duración:** no instrumentada; pytest reportó 1,24 s (T3) y 1,94 s (suite).
- **Tokens / créditos / interacciones de herramientas:** no disponibles (no expuestos). No se
  estiman.

## Alcance / restricciones respetadas

- Solo se ejecutó la Tarea 3. Tareas 4–46 sin iniciar y sin marcar; Tareas 1 y 2 preservadas.
- No se implementó ACH, recurrentes ni límites; no se cambió lógica de negocio ni el contrato de
  la API; no se modificaron requisitos/diseño ni la Etapa 1; sin dependencias nuevas; registros
  experimentales previos intactos. No se ejecutó la ruta MFA (Tarea 4).
