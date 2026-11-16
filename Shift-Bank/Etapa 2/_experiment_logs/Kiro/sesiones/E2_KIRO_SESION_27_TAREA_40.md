# E2 · Kiro · Sesión de implementación 27 — Tarea 40

- **Fecha:** 2026-11-16
- **Tarea:** 40 — (verificación) Ejecutar la suite de regresión de la Etapa 1
- **Fase:** G — Verificación final y evidencia experimental
- **Objetivo:** Re-ejecutar las pruebas de la Fase A (cuentas, internas, MFA, contratos/
  historial y arnés) sobre la aplicación **ya extendida** con las Fases B–F, y confirmar **cero
  regresiones** en el comportamiento heredado de la Etapa 1.
- **Alcance autorizado:** solo Tarea 40. Tarea única de verificación/evidencia; **sin modificar
  código de producción**.
- **Estado final:** COMPLETED — regresión verde, 0 regresiones.
- **Requisitos:** 15.1–15.8 · **Contrato:** HER-01..06; A01, A02, A20.

## Naturaleza de la tarea

Tarea puramente de **verificación**: no crea ni modifica código de aplicación ni pruebas. Se
limita a ejecutar las pruebas de la Fase A existentes contra la aplicación extendida y registrar
los resultados **reales** de pytest. Las pruebas de la Fase A ya habían sido escritas (Tareas
1–5) y adaptadas de forma aditiva para el campo `type` del historial unificado (Tarea 25, D03/
D05); aquí solo se re-ejecutan como evidencia de no-regresión al final de la Etapa 2.

## Archivos de prueba de la Fase A ejecutados

| Archivo | Cobertura heredada | Pruebas |
|---|---|---:|
| `tests/test_regression_accounts.py` | Cuentas y saldos iniciales (HER-01; A01) | 8 |
| `tests/test_regression_internal_transfers.py` | Transferencias internas (HER-02; A02) | 12 |
| `tests/test_regression_mfa.py` | MFA heredada (HER-03; A13) | 14 |
| `tests/test_regression_api_contracts.py` | Contratos de API e historial (HER-01, HER-05; A01) | 13 |
| `tests/test_harness.py` | Arnés / aislamiento de DB temporal (15.8) | 4 |
| **Total Fase A** | | **51** |

## Comandos ejecutados y resultados reales

Ejecutado desde `Etapa 2/Kiro/backend` con el intérprete del entorno virtual
(`.venv\Scripts\python.exe`, Python 3.13.2, pytest 8.3.4).

1. **Suite de la Fase A (regresión Etapa 1), verboso:**
   `python -m pytest tests/test_regression_accounts.py tests/test_regression_internal_transfers.py tests/test_regression_mfa.py tests/test_regression_api_contracts.py tests/test_harness.py -v`
   → **51 passed, 1 warning in 3.60s** (exit 0).
   - 51/51 PASS, 0 FAIL, 0 SKIP.

2. **Suite completa (confirmación de no-regresión global):**
   `python -m pytest -q`
   → **220 passed, 1 warning in 13.91s** (exit 0).
   - 220/220 PASS, 0 FAIL, 0 SKIP. Incluye las 51 de la Fase A más las pruebas de las Fases
     B–E (esquema/migración, límites, ACH, recurrentes, scheduler, etc.).

### Desglose por dominio de regresión (Fase A — todos PASS)

- **Cuentas (8/8):** 200 OK; estructura `{accounts:[{name,balance}]}`; Checking y Savings
  presentes; saldos iniciales heredados (5.000.000,00 / 15.000.000,00); decimal-string 2
  decimales; **sin IDs internos**; consistencia API↔DB aislada; lectura no altera saldos.
- **Internas (12/12):** éxito sin MFA → `COMPLETED`; débito/crédito atómicos con total
  preservado; API refleja nuevos saldos; 2 históricas al inicio + nueva registrada; estructura
  y estados del historial heredados; rechazos (misma cuenta, monto ≤ 0, >2 decimales, fondos
  insuficientes) sin movimiento parcial; representación en centavos / decimal-string.
- **MFA (14/14):** umbral (bajo / exacto / sobre); schema inicial heredado; `PENDING_MFA` no
  mueve saldos y es visible en historial; confirmación correcta completa y mueve saldos; forma
  tras completar; código incorrecto rechazado sin lockout; referencia inexistente; expiración a
  5 min → `EXPIRED`; expirada no completa con código correcto; fondos insuficientes al confirmar
  → `FAILED`; confirmación repetida no debita dos veces.
- **Contratos e historial (13/13):** formas de `GET /api/accounts`, `POST /api/transfers`,
  `/mfa` y `GET /api/transfers`; creación sin/con MFA; confirmación MFA; estructura y campos del
  historial (incluido el aditivo `type`); históricas + nueva; `PENDING_MFA` observable; orden
  DESC por fecha; sin identificadores internos; montos decimal-string 2 decimales; estructura de
  error pública `{error:{code,message}}`; códigos/HTTP representativos; internas conservan su
  forma sin campos de beneficiario.
- **Arnés (4/4):** importa la app heredada; DB de prueba aislada y temporal; la app crea su DB
  en la ruta aislada; rutas de DB distintas entre pruebas.

### Advertencias (no bloqueantes)

- 1 `DeprecationWarning` de `anyio.abc.BlockingPortal` (alias en `starlette.testclient`),
  dependiente de la librería, no del código de la aplicación. No afecta los resultados.

## Resultado de regresión

**CERO regresiones.** Las 51 pruebas de la Fase A pasan sobre la aplicación extendida; el único
cambio observable respecto a la Etapa 1 es el campo **aditivo** `type` del historial unificado,
aprobado en D03/D05 e incorporado en la Tarea 25 sin alterar los valores heredados (nombres
amigables en `direction {from,to}`, estados internos en MAYÚSCULAS, saldos y contratos de
error). La suite completa (220) también está verde, por lo que no hay regresiones ni dentro ni
fuera del dominio heredado.

## Errores y correcciones

- Ninguno. 51/51 (Fase A) y 220/220 (suite completa) en la primera ejecución. No se corrigió
  comportamiento ni se tocó ninguna prueba.

## Evidencia de preservación de la Etapa 1

- **DB histórica de E1 (`Etapa 1/Kiro/backend/shift_bank.db`):** SHA-256
  `407B0E132E76900FBF59412C31A2D8047A666F2BE1856BE1FF6B88531C89B4A8`, 36.864 bytes — **idéntica**
  al hash registrado en la sesión de la Fase D; sin cambios.
- **`shift_bank.db` en `Etapa 2/Kiro/backend`:** no existe (0 archivos `*.db`); las pruebas usan
  DB SQLite temporales aisladas; sin residuos.
- **`git status`:** `Etapa 1/Kiro` no aparece en el diff (sin cambios). Los archivos modificados/
  nuevos listados corresponden a tareas de implementación previas (1–39); esta sesión **no**
  modificó código de producción.

## No modificación de código de producción

Esta sesión solo ejecutó pytest (lectura) y escribió este registro de evidencia más la marca de
la Tarea 40 en `tasks.md`. No se editó `app/`, ni las pruebas, ni el frontend.

## Métricas

- **Duración:** N/D (no instrumentada). pytest reportó 3,60 s (Fase A) y 13,91 s (suite
  completa).
- **Resultados:** Fase A 51/51 PASS · suite completa 220/220 PASS · 0 FAIL · 0 SKIP.
- **Tokens / créditos / interacciones de herramientas:** N/D (no expuestos). No se estiman.

## Alcance / restricciones respetadas

- Solo se ejecutó la Tarea 40. La Tarea 41 (suite de aceptación A01–A19) y 42–46 quedan sin
  iniciar; las Tareas 1–39 se preservan intactas; total de 46 tareas intacto.
- No se modificó código de aplicación, pruebas, requisitos, diseño, la Etapa 1 ni registros
  previos. Sin dependencias nuevas.
