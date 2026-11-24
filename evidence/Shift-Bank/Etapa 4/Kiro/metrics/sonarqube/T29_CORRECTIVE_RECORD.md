# T29 — Pasada correctiva acotada (dirigida por SonarQube PRE) — registro detallado

Fecha/hora: 2026-11-19 (America/Bogota). Base: PRE analysisId
`cd37bcc9-6884-4dd4-a92a-d4e8f374cb62`, 162 issues (0 bugs / 1 vuln / 161 code smells), QG OK.

## Principio aplicado
Correcciones **seguras y preservadoras del comportamiento** sobre código RELEVANTE de producción.
NO se modifican tests en masa solo para bajar conteos (anti-patrón prohibido), NO se tocan
exclusiones, supresiones, condiciones del Quality Gate, alcance ni cobertura artificial, y NO se
modifica la Etapa 3.

## Issues ABORDADOS

### 1. typescript:S2245 — VULNERABILITY (prioridad) — RESUELTO
- Archivo/línea PRE: `frontend/src/stage4/apiV2.ts:47`.
- Regla: "Make sure that using this pseudorandom number generator is safe here."
- Causa: el fallback de `newIdempotencyKey()` usaba `Math.random()` para un identificador sensible
  de idempotencia.
- Fix: reescrito `newIdempotencyKey()` para preferir `crypto.randomUUID()`; si no existe, componer
  un UUID v4 con `crypto.getRandomValues()` (CSPRNG, versión/variante RFC 4122); si no hay
  aleatoriedad segura, **fallar de forma segura (throw)** — NUNCA `Math.random()`.
- Contrato preservado: formato UUID v4 (validado por `apiV2.test.ts` contra la regex v4) e
  idempotencia (la clave sigue siendo única por operación). Vitest 14/14 verde.

### 2. typescript:S6759 — "Mark the props of the component as read-only" — PARCIAL (acotado)
- Resueltos SOLO en los 2 componentes propios de la Etapa 4 (cambio idiomático `Readonly<Props>`,
  sin alterar comportamiento):
  * `frontend/src/stage4/MultiCurrencyDashboard.tsx:12` → firma `({ accounts }: Readonly<Props>)`.
  * `frontend/src/stage4/ConversionForm.tsx:14` → firma `({ accounts, onDone }: Readonly<Props>)`.
- NO modificados (decisión): los 8 componentes HEREDADOS (AccountsPanel, AchTransferForm,
  BeneficiariesPanel, HistoryList, LimitsPanel, MfaDialog, RecurringPanel, TransferForm). Razón:
  modificar código heredado de Etapas 1–3 por conteos de estilo está fuera del alcance de la
  Etapa 4 y arriesga sus contratos. Preservación de la Etapa 3 (instrucción explícita).

## Issues NO abordados (decisión deliberada y justificada)

### python:S9073 (94), python:S5778 (17), python:S9083 (13) — NO modificados
- Verificado con la evidencia PRE: **100% de estos 124 findings están en `backend/tests/`**
  (0 en `backend/app/`). Reglas de estilo de pruebas: "split composite assertion", "one throwing
  invocation per exception test", "remove empty decorator parentheses".
- Decisión: NO reescribir 124 aserciones/decoradores de tests. Justificación: (a) no afectan el
  comportamiento ni la calidad del código de producción de la app; (b) reescribir el cuerpo de la
  suite de regresión (incluida la heredada) para bajar conteos es exactamente el anti-patrón
  prohibido ("do not blindly modify code to eliminate issue counts") y arriesga el baseline verde
  de 444 pruebas; (c) la mayoría viven en archivos de test HEREDADOS (preservación Etapa 3).
- Resultado esperado en POST: estos conteos permanecerán; es un resultado honesto, no una
  regresión de calidad del producto.

## Archivos modificados (resumen)
- `frontend/src/stage4/apiV2.ts` (`newIdempotencyKey` seguro, S2245).
- `frontend/src/stage4/MultiCurrencyDashboard.tsx` (`Readonly<Props>`, S6759).
- `frontend/src/stage4/ConversionForm.tsx` (`Readonly<Props>`, S6759).
- NINGÚN archivo de `backend/app/` cambiado (no era necesario; la única vuln estaba en frontend).
- NINGÚN archivo de test ni de la Etapa 3 cambiado.

## Pruebas reales tras los fixes
- Frontend Vitest: **14 passed**, exit 0 (`T29_vitest.txt`).
- Build de producción (`tsc && vite build`): exit 0, **45 modules** (`T29_build.txt`).
- Regresión backend completa: **444 passed**, exit 0 (`T29_backend_regression.txt`).
- Cobertura regenerada con la MISMA metodología/alcance del PRE:
  * backend `pytest --cov=app --cov-report=xml:coverage.xml` → 444 passed (`T29_backend_coverage.txt`),
    `backend/coverage.xml` presente.
  * frontend `vitest run --coverage` (v8 → lcov) → 14 passed (`T29_frontend_coverage.txt`),
    `frontend/coverage/lcov.info` presente.

## Regresiones / reintentos / limitaciones
- Sin regresiones: todas las suites verdes a la primera tras los cambios.
- Limitación: el conteo total de issues en POST no bajará a cerca de 0; la reducción esperada es la
  vulnerabilidad (1→0) y 2 de 10 findings S6759. Es intencional y honesto (se priorizó seguridad y
  se evitó el churn de tests). El investigador puede autorizar una pasada mayor sobre tests si lo
  desea, pero queda FUERA de esta pasada acotada.

## Comparabilidad para T30 (POST)
- La config del escáner no cambia: `sonar-project-stage4.properties`, key
  `Shift-Bank---Stage-4---Kiro`, mismas rutas de cobertura y mismo alcance. El investigador ejecuta
  el POST con la MISMA configuración que el PRE. No se tocaron exclusiones/QG/cobertura.
