# T17 (auto)(verificación) — Regresión heredada sobre cifrado + auditoría

- **Fecha/hora:** 2026-11-16T19:53:41-05:00
- **Tarea:** 17 — Regresión heredada sobre cifrado+auditoría (M2)
- **Requisitos:** R14.1, R14.2, R14.3, R14.4 · **Diseño:** §12, §1.5 · **AC:** AC-01
- **Veredicto global:** ✅ **PASS** — cero regresiones de forma/estado/invariantes con cifrado
  en reposo (T7) y auditoría transaccional (T12–T13) activos.

## Entorno

| Componente | Versión |
|------------|---------|
| SO | Windows (win32) |
| Python | 3.13.2 (`backend/.venv`) |
| pytest | 8.3.4 |
| plugins | anyio-4.16.0, locust-2.47.0, cov-7.1.0 |

- **Directorio backend:** `Etapa 3/Kiro/backend`
- **Aislamiento:** `conftest.py` parchea `DB_PATH` a una DB SQLite temporal por prueba y fija
  claves de cifrado/auditoría SOLO-PRUEBAS antes de arrancar la app. Ninguna prueba toca la DB
  histórica de la Etapa 2 ni `SEED-3.md`. Sin cambios en código de producción.

## Paso 1 — Suites heredadas E1/E2 (ejecución explícita)

**Comando exacto:**

```
python -m pytest tests/test_regression_accounts.py tests/test_regression_internal_transfers.py \
  tests/test_regression_mfa.py tests/test_regression_api_contracts.py tests/test_ach.py \
  tests/test_recurring.py tests/test_recurring_api.py tests/test_recurring_execution.py \
  tests/test_recurring_verification.py tests/test_limits.py tests/test_scheduler.py \
  tests/test_migration.py tests/test_migration_suite.py tests/test_schema_stage2.py \
  tests/test_txn.py tests/test_clock.py tests/test_harness.py -v
```

**Resultado:** `220 passed, 1 warning in 13.32s` — **exit 0**. 100% PASS.

Conteo por archivo heredado (todos PASS, 0 fallos/skips):

| Archivo | Tests |
|---------|-------|
| test_regression_accounts.py | 8 |
| test_regression_internal_transfers.py | 12 |
| test_regression_mfa.py | 14 |
| test_regression_api_contracts.py | 14 |
| test_ach.py | 17 |
| test_recurring.py | 40 |
| test_recurring_api.py | 14 |
| test_recurring_execution.py | 18 |
| test_recurring_verification.py | 21 |
| test_limits.py | 11 |
| test_scheduler.py | 8 |
| test_migration.py | 6 |
| test_migration_suite.py | 7 |
| test_schema_stage2.py | 12 |
| test_txn.py | 9 |
| test_clock.py | 10 |
| test_harness.py | 4 |
| **Total** | **220** |

> La única advertencia es un `DeprecationWarning` de `starlette.testclient` (alias de anyio),
> no relacionado con cifrado/auditoría y preexistente en la cadena de dependencias.

## Paso 2 — Suite completa

**Comando exacto:** `python -m pytest -q`

- **Antes del test aditivo de contrato:** `341 passed, 1 warning in 19.10s` — exit 0.
- **Después del test aditivo de contrato (paso 3):** `344 passed, 1 warning in 19.11s` — exit 0.

Suite completa **verde** (incluye las nuevas capacidades de Etapa 3: crypto, cifrado en reposo,
migración de cifrado, esquema/cadena/manipulación/atomicidad/acceso de auditoría y concurrencia
SQLite).

## Paso 3 — Preservación de contratos con cifrado + auditoría activos

Test **aditivo y SOLO-LECTURA** creado (no modifica código de aplicación):
`tests/test_regression_contract_no_ciphertext.py` (3 tests, todos PASS).

**Comando:** `python -m pytest tests/test_regression_contract_no_ciphertext.py -v`
**Resultado:** `3 passed, 1 warning in 0.74s` — exit 0.

Comprobaciones realizadas tras sembrar beneficiario + ACH (snapshot cifrado) + transferencia
interna:

1. **`GET /api/beneficiaries`**
   - Cuenta **enmascarada** (`account_masked = "••••3210"`), routing en claro
     (`"123456789"`), sin `account_number` completo.
   - El JSON serializado **no contiene** el prefijo de texto cifrado `enc:v1:` ni el número de
     cuenta completo (`9876543210`).
   - Sin claves internas filtradas (`beneficiary_snapshot`, `customer_id`, `rowid`, etc.).

2. **`GET /api/transfers`** (historial unificado)
   - Entradas **ACH** conservan su forma: `type/date/amount/status/beneficiary` con cuenta
     enmascarada (`••••3210`); sin snapshot ni ciphertext.
   - Entradas **internas** mantienen `direction {from,to}` y estados en **MAYÚSCULAS**
     (p. ej. `COMPLETED`).
   - El JSON serializado **no contiene** `enc:v1:` ni la cuenta completa; sin ids internos.

3. **Contraparte en reposo vs API**
   - En la DB aislada, el `beneficiary_snapshot` de la entrada ACH **empieza por `enc:v1:`**
     (cifrado en reposo confirmado).
   - En las respuestas `GET /api/transfers` y `GET /api/beneficiaries` **no aparece** ningún
     token `enc:v1:` (descifrado + enmascarado en el borde de E/S, sin cambio de forma).

## Trazabilidad R14 → evidencia

| Criterio | Evidencia |
|----------|-----------|
| R14.1 — APIs/contratos heredados sin cambio de forma | Paso 1 (220 PASS) + Paso 3 (contratos de cuentas, historial, transferencias, MFA, ACH, recurrentes, límites intactos) |
| R14.2 — Invariantes financieros (conservación, atomicidad, exactamente-una-vez) | Paso 1: `test_txn`, `test_recurring_execution`, `test_ach` (settlement idempotente, reembolso una vez), `test_migration*` PASS |
| R14.3 — Sin exposición de ids internos + enmascarado de cuentas | Paso 3: sin `enc:v1:`, sin cuenta completa, sin claves internas; `account_masked` preservado |
| R14.4 — Cifrado/auditoría añadidos de forma aditiva | Suite completa verde (341→344) sin eliminar ni alterar endpoints/estados/formatos existentes |

## Conclusión

Verificación pura, sin tocar producción ni datos históricos. Nada regresó: las suites heredadas
E1/E2 pasan al 100% (220/220), la suite completa queda verde (344/344) y los contratos públicos
se mantienen intactos con cifrado en reposo y auditoría transaccional activos (sin ciphertext ni
ids internos en las respuestas, enmascarado preservado).
