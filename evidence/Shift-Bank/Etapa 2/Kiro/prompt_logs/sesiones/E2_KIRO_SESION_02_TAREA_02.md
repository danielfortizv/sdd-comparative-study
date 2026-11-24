# E2 · Kiro · Sesión de implementación 02 — Tarea 2

- **Fecha:** 2026-11-16
- **Tarea:** 2 — (verificación) Pruebas de regresión: cuentas y saldos iniciales
- **Objetivo:** fijar el comportamiento heredado de la Etapa 1 para la recuperación de cuentas,
  saldos iniciales y representación monetaria, usando el arnés aislado de la Tarea 1, antes de
  introducir funcionalidad de la Etapa 2.
- **Estado final:** COMPLETED

## Estado del repositorio

- **Commit:** `ebf1017748928b30a9a5ad68a56b9b532f304e86` (sin commit nuevo en esta sesión).
- **Etapa 1 (`Etapa 1/Kiro`):** git limpio, sin cambios (verificado).
- **DB histórica E1 (`shift_bank.db`):** 36 864 bytes, LastWrite 13/10/2026 2:58:26 p. m. —
  sin modificar.

## Inspección del comportamiento heredado (fuente de los asertos)

- `app/routers/accounts.py`: `GET /api/accounts` → `AccountsResponse` con
  `AccountOut(name=display_name, balance=format_cents(balance_cents))`, orden checking→savings.
- `app/schemas.py`: `AccountOut{ name: str, balance: str }` (decimal-string).
- `app/seed.py`: Checking = 5.000.000,00 (500.000.000 centavos); Savings = 15.000.000,00
  (1.500.000.000 centavos); nombres amigables "Checking"/"Savings".
- `app/money.py`: `format_cents` → decimal con 2 decimales.

No se modificó ningún archivo de aplicación; las pruebas verifican el contrato tal como está.

## Archivos creados / modificados

| Acción | Archivo |
|---|---|
| Creado | `Etapa 2/Kiro/backend/tests/test_regression_accounts.py` (8 pruebas) |
| Modificado | `Etapa 2/Kiro/.kiro/specs/shift-bank-stage2/tasks.md` (marcada solo la Tarea 2) |

Sin cambios en código de aplicación, requisitos, diseño ni Etapa 1.

## Casos de prueba introducidos

| Prueba | Verifica |
|---|---|
| `test_get_accounts_responde_200` | `GET /api/accounts` → 200 (recuperación exitosa) |
| `test_estructura_de_respuesta_de_cuentas` | forma `{accounts:[{name,balance}]}`, 2 cuentas, solo `name`+`balance` (str) |
| `test_cuentas_checking_y_savings_presentes` | nombres exactos y orden heredado `["Checking","Savings"]` |
| `test_saldos_iniciales_heredados` | Checking `5000000.00`, Savings `15000000.00` |
| `test_representacion_monetaria_decimal_string_2_decimales` | saldos como cadena decimal con 2 decimales |
| `test_sin_identificadores_internos_en_la_respuesta` | sin `id/uuid/customer_id/account_id/kind` |
| `test_consistencia_entre_api_y_db_aislada` | API ↔ DB aislada: 500.000.000 / 1.500.000.000 centavos |
| `test_lectura_no_altera_saldos` | GET es de solo lectura: saldos invariables tras repetir |

## Dependencias

Ninguna nueva (se reutilizan `pytest`/`httpx` de la Tarea 1).

## Comandos ejecutados y resultados reales

1. `python -m pytest tests/test_regression_accounts.py -v` → **8 passed, 19 warnings in 1.13s**
   (exit 0). Las 8 pruebas listadas arriba PASSED.
2. `python -m pytest -q` (suite completa) → **12 passed, 23 warnings in 0.95s** (exit 0):
   4 del arnés (Tarea 1) + 8 de regresión de cuentas (Tarea 2). Las pruebas de la Tarea 1 siguen
   pasando.

- Passed: **12** · Failed: **0** · Skipped: **0**.

### Advertencias (no bloqueantes)

- `DeprecationWarning: on_event is deprecated` (patrón heredado de E1; migración planificada en
  la Tarea 12) y alias de anyio en `TestClient`. No afectan a la validez de las pruebas.

## Evidencia de aislamiento y preservación de la Etapa 1

- `shift_bank.db` **no** existe en `Etapa 2/Kiro/backend` (las pruebas usaron solo DB temporales).
- Sin DB temporales residuales tras la ejecución (teardown correcto).
- DB histórica de E1 sin cambios (tamaño/fecha idénticos). `Etapa 1/Kiro` git limpio.

## Errores encontrados y correcciones

- Ninguno. Las 8 pruebas pasaron en la primera ejecución. No se detectó inconsistencia del
  baseline heredado: el comportamiento observado coincide con el seed y el contrato de la Etapa 1.

## Criterios de completitud (Tarea 2)

| Criterio | Resultado |
|---|---|
| Recuperación exitosa vía `GET /api/accounts` | ✅ |
| Cuentas Checking y Savings esperadas | ✅ |
| Saldos iniciales correctos (seed real) | ✅ |
| Representación monetaria y estructura de respuesta | ✅ |
| Consistencia API ↔ DB aislada | ✅ |
| Saldos preservados en lecturas | ✅ |
| Pruebas de la Tarea 1 siguen pasando | ✅ (12/12) |

## Métricas

- **Duración:** no instrumentada de forma fiable; pytest reportó 1,13 s (T2) y 0,95 s (suite).
- **Tokens / créditos / interacciones de herramientas:** no disponibles (no expuestos). No se
  estiman.

## Alcance / restricciones respetadas

- Solo se ejecutó la Tarea 2. Tareas 3–46 sin iniciar y sin marcar; Tarea 1 preservada.
- No se implementó ACH, recurrentes ni límites; no se cambió lógica de negocio ni contratos de
  API; no se modificaron requisitos/diseño ni la Etapa 1; no se instalaron dependencias nuevas;
  no se modificaron registros experimentales previos.
