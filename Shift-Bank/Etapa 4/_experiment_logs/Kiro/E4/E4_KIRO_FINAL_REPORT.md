# Shift Bank — Etapa 4 (Opción A) — Reporte final (Kiro, SDD nativo)

> Documento de consolidación experimental de la Etapa 4 para la cuenta **NUEVA** de Kiro Student.
> Solo evidencia verificable; donde no hay evidencia se indica **N/D**. No mezcla la cuenta nueva
> con la anterior. No se inventan totales de tokens/créditos/tiempo.

## 1. Objetivo, método y reproducibilidad

- **Objetivo.** Evolucionar de forma disruptiva la aplicación Shift Bank heredada (Etapa 3 de Kiro)
  hacia: cuentas **multidivisa** (USD/EUR/GBP), **conversión FX exacta**, **Event Sourcing**,
  **CQRS**, **idempotencia** por `Idempotency-Key` y **concurrencia optimista** por versión de
  cuenta, preservando las salvaguardas bancarias (MFA, límites, ACH, recurrentes, cifrado,
  auditoría) y la capacidad de despliegue. Semilla canónica: `Etapa 4/SEED-4.md`
  (SHA-256 `8d7e32d3…0fd3047`, verificada byte a byte).
- **Método.** SDD nativo de Kiro (Specs `requirements.md` → `design.md` → `tasks.md` +
  `tasks.meta.json`) con gates de investigador. Implementación por capas sobre el baseline
  heredado (FastAPI + `sqlite3` sin ORM; React/TS; Docker Compose/Nginx/TLS). Decisiones comunes
  **D-01..D-14** y de diseño **DK-01..DK-05**.
- **Reproducibilidad.** Backend con venv aislado (Python 3.13.2); frontend Node v20.17.0/npm
  11.6.3; dependencias fijadas. Todas las pruebas usan DB SQLite temporal/aislada. Comandos,
  stdout, exit codes y timestamps preservados en `_experiment_logs/Kiro/E4/` (ver índice de
  evidencia). La Etapa 3 y su evidencia NO se modifican.

## 2. Workflow SDD nativo y Specs finales

- Spec nativo en `Kiro/.kiro/specs/shift-bank-stage4/`:
  - `requirements.md`: 20 requisitos (16 FR + 4 NFR), 81 criterios EARS, glosario D-01..D-14 +
    DK-01..DK-05 + matriz AC4-01..AC4-20.
  - `design.md`: modelo de datos (esquema aditivo), FX exacto, Event Sourcing/CQRS, patrón de
    comando atómico, idempotencia/versión, puertos currency-aware, frontend, migración/fixture.
  - `tasks.md` (31 tareas, 7 milestones, 3 gates) + `tasks.meta.json` (olas + historial de
    ejecución + gates).
- Gates de investigador: **T4** (aprobación de Specs), **T28** (revisión PRE SonarQube), **T30**
  (escaneo final SonarQube). Los tres aprobados.

## 3. Las 31 tareas y su evidencia real de finalización

**31/31 completas.** Resumen (detalle y timestamps en `tasks.meta.json` y en las iteraciones):

- **M0 (1–4):** baseline heredado verde (backend 372, Vitest 3, build 41 módulos), D1 PRE del
  nuevo account registrado, estructura de evidencia, gate T4 aprobado.
- **M1 (5–7):** esquema multidivisa aditivo/idempotente; fixture D-02 (seed_stage4); motor FX
  exacto (`fx.py`, matriz de tasas de la guía).
- **M2 (8–10):** almacén de eventos (`events.py`), proyecciones CQRS + rebuild (`projections.py`),
  patrón de comando atómico (`command.py`).
- **M3 (11):** idempotencia + versión optimista (`idempotency.py`), replay antes de versión (DK-04).
- **M4 (12–15):** conversiones `/api/conversions`, internas misma-moneda `/api/v2/transfers`,
  límites/MFA en equivalente USD, guardias de divisa ACH/recurrentes (integradas en los servicios).
- **M5 (16–17):** frontend multidivisa (`stage4/`): formateo bigint/string, cliente v2 con
  Idempotency-Key/Expected-Version, dashboard por moneda + formulario de conversión (integrados en
  `App.tsx`).
- **M6 (18–25):** verificación de atomicidad/ES-CQRS/concurrencia/fallo; regresión completa;
  cobertura; **carga Locust en vivo**; **despliegue Docker en vivo**.
- **M7 (26–31):** config SonarQube Etapa 4 (key separada), PRE verificado (T27), gate PRE (T28),
  pasada correctiva acotada (T29), escaneo final verificado + gate (T30), consolidación final (T31).

## 4. Requisitos funcionales y trazabilidad D-01..D-14

| Decisión | Implementación | Evidencia |
|---|---|---|
| D-01 moneda fija por cuenta | `account.currency` {USD,EUR,GBP}; sin mezcla | test_schema_stage4, test_conversion_api |
| D-02 fixture CHK/SAV/EUR/GBP | `seed_stage4` (reset controlado, DK-01) | test_fixture_stage4; smoke despliegue |
| D-03 Decimal/bigint, tasas racionales, HALF_UP 1 vez | `fx.py`, `money.py`, `currencyFormat.ts` | test_fx (11), currencyFormat.test |
| D-04 internas misma moneda; FX por /api/conversions | `conversion_service`, router v2 | test_conversion_api (cross-currency 422) |
| D-05 eventos append-only separados de auditoría | `domain_event` + triggers | test_event_store |
| D-06 proyecciones síncronas/atómicas, rebuild determinista | `projections.py` | test_projection |
| D-07 límites USD-eq 5000/10000; MFA USD-eq sin redondear >1000 | `limit_service.check_usd`, `fx.requires_mfa_usd`, flujo MFA v2 | test_limits_usd, test_mfa_v2_api |
| D-08 ACH solo USD; recurrentes internos misma moneda; recurrentes ACH USD | `currency_guard` integrado en servicios | test_currency_integration |
| D-09 eventos compuestos, versión +1 por cuenta; ACH exactamente-una-vez | `command.apply_effects_in_tx` | test_command_atomicity, test_event_store |
| D-10 dashboard por moneda; USD estimado solo visual | `MultiCurrencyDashboard` | currencyFormat.test, build |
| D-11 cifrado AES-GCM, auditoría HMAC, atomicidad compuesta | reutilización `audit`/`crypto` + comando | test_command_atomicity; despliegue audit verify |
| D-12 FastAPI/React/SQLite + Compose/Nginx/TLS | preservados; despliegue en vivo | DEPLOYMENT-VALIDATION.md |
| D-13 Idempotency-Key UUID; replay sin efectos; payload distinto 409 | `idempotency.py` | test_idempotency, test_conversion_api |
| D-14 versión esperada; obsoleta 409; replay antes de versión | `idempotency.py` (DK-04) | test_idempotency |

## 5. Capacidades implementadas (resumen técnico)

- **Multidivisa:** moneda ISO-4217 por cuenta, identificadores públicos inmutables (CHK-1001,
  SAV-2001, EUR-3001, GBP-4001), saldos/historial inequívocos por moneda.
- **FX exacto:** `fractions.Fraction` con la matriz oficial de la guía (USD/EUR=9/10, USD/GBP=8/10,
  cruzadas EUR/GBP=8/9, GBP/EUR=9/8); `ROUND_HALF_UP` una sola vez; sin floats.
- **Event Sourcing:** `domain_event` append-only (triggers anti UPDATE/DELETE), `UNIQUE(aggregate_id,
  aggregate_ver)` anti-duplicado, eventos compuestos por `operation_id`. Separado de `audit_log`.
- **CQRS:** `account_projection` actualizada en la misma transacción; `rebuild_projections`
  determinista; `verify_consistency` fail-closed.
- **Idempotencia + concurrencia optimista:** `idempotency_key` + versión esperada por cuenta; el
  replay idempotente se evalúa ANTES de la versión (DK-04); todo atómico en `BEGIN IMMEDIATE`.
- **MFA/ACH/recurrentes:** MFA v2 con equivalente USD sin redondear estrictamente >1000
  (pending/confirm, sin mover saldo hasta confirmar); ACH solo USD; recurrentes internos misma
  moneda, recurrentes ACH USD; ciclo ACH exactamente-una-vez preservado.

## 6. Reset controlado de la fixture D-02 y discontinuidad monetaria (DK-01)

La Etapa 3 de Kiro sembraba **COP 5.000.000** (checking) y **COP 15.000.000** (savings), sin
columna de moneda. La D-02 exige **USD 2.500,00 / USD 10.000,00 / EUR 0,00 / GBP 0,00**. El
investigador autorizó un **reset controlado de la fixture experimental** de la Etapa 4:

- **NO es** una conversión COP→USD ni una migración que preserve valor; es una **discontinuidad
  experimental declarada**: cambian moneda, identidad de cuenta y valor por decisión de fixture.
- El estado y la evidencia de la Etapa 3 (COP) se **preservan sin modificación**; la Etapa 4 parte
  de una fixture separada (`seed_stage4`), que no lee ni toca la Etapa 3.
- La verificación de migración/rollback es **estructural** (aditiva, idempotente, transaccional,
  rebuild determinista, sin doble conteo), sin afirmar equivalencia de valor COP↔USD.
- **Decisión Path A (dual-fixture):** el arnés de regresión HEREDADO usa la siembra COP
  (`SHIFT_SEED_MODE=legacy`) para preservar el baseline verde (compatibilidad hacia atrás,
  AC4-20); la app por defecto y todas las pruebas de ACEPTACIÓN de la Etapa 4 usan la fixture D-02
  (`SHIFT_SEED_MODE=stage4`, fixture `stage4_app_client`). Implicación: las pruebas legacy NO
  demuestran aceptación de la Etapa 4; la aceptación se demuestra solo con la fixture D-02.

## 7. Resultados finales de pruebas y cobertura

- **Backend Pytest:** **444 passed**, exit 0 (baseline heredado 372 preservado + ~72 pruebas nuevas
  de la Etapa 4). Evidencia: `sonarqube/T29_backend_regression.txt`.
- **Frontend Vitest:** **14 passed** (3 heredadas + 11 Stage 4), exit 0. Build de producción
  (`tsc && vite build`): exit 0, **45 módulos**.
- **Cobertura (regenerada, misma metodología PRE):** backend 94% local (coverage.py);
  medición SonarQube del proyecto **49,6%** (línea 49,6 / rama 50,8) — el denominador SonarQube
  incluye el frontend React heredado sin pruebas unitarias (ver Limitaciones). Artefactos:
  `backend/coverage.xml`, `frontend/coverage/lcov.info`.

## 8. Carga Locust en vivo (contrato exacto)

Servidor FastAPI vivo + fixture D-02 aislada. 30 usuarios, ramp 5/s (6 s), 60 s estable.
**8.409 peticiones, 0 fallos.** Distribución medida ≈ 60/30/10:

| Ruta | Count | p50 | p95 | Máx |
|---|---|---|---|---|
| GET /api/v2/accounts | 5.084 | 10 ms | 53 ms | 341 ms |
| GET /api/transfers | 2.518 | 10 ms | 61 ms | 403 ms |
| POST /api/conversions | 403 | 18 ms | 73 ms | 325 ms |
| POST /api/v2/transfers | 404 | 19 ms | 71 ms | 270 ms |
| Agregado | 8.409 | 13 ms | 59 ms | 403 ms |

Throughput ≈ 128,7 req/s. Umbrales: p95 lectura <200 ms ✔, p95 operación <500 ms ✔, errores
inesperados <1% (0%) ✔. Evidencia: `carga/LOAD-SUMMARY.md`,
`Kiro/loadtest/results_stage4/locust_run_*_stats.csv`.

## 9. Validación de invariantes post-carga (separada)

Corrida con verificación ANTES del teardown (DB viva): `invariants_ok=True` —
`projection_consistency`, `no_duplicate_versions`, `internal_conservation_per_currency`,
`rebuild_matches`; **audit_chain_ok=True**. Evidencia: `carga/load-invariants-live.txt`,
`loadtest/verify_invariants_stage4.py`.

## 10. Despliegue Docker HTTPS (en vivo)

`build`+`up` exit 0; backend+nginx **healthy**. HTTPS `GET /api/v2/accounts` 200 con **fixture
D-02**; redirección HTTP→HTTPS **301**; reverse-proxy de API; **conversión por HTTPS** 200
(9/10, 100 USD→90 EUR). **Persistencia tras `restart`** (CHK 2400/v2, EUR 90/v2 idénticos);
**auditoría** `verify` {"ok":true}; **fail-closed** con claves vacías (ConfigError, backend no
arranca). Teardown `down -v` + borrado de `.env`/`certs`; workspace limpio. Certificado y secretos
DESECHABLES (generados y eliminados). Evidencia: `despliegue/DEPLOYMENT-VALIDATION.md` + logs.

## 11. SonarQube PRE/POST (claves de issue y severidad/impacto)

- Proyecto `Shift-Bank---Stage-4---Kiro` (nunca la key de la Etapa 3). Config PRE==POST
  (byte-idéntica). CE tasks: PRE `c69bea55` SUCCESS / analysisId `cd37bcc9`; POST `171f9bef`
  SUCCESS / analysisId `bb7434e4`. Quality Gate PRE OK, POST OK (new_violations=0).
- **Por clave de issue:** 4 resueltos, 0 introducidos.
  - `1c9b78d4…` typescript:**S2245** (VULNERABILITY) `apiV2.ts:47` → CLOSED/FIXED.
  - `9a8ff686…` typescript:S7767 `apiV2.ts:47` → cerrado por el mismo reescrito seguro.
  - `1dd96ef1…` / `6f57b9f8…` typescript:S6759 en `ConversionForm.tsx:14` /
    `MultiCurrencyDashboard.tsx:12`.
- No modificados (decisión deliberada): python:S9073 (94), S5778 (17), S9083 (13) — 100% en
  archivos de test, 0 en `app/`; evitar el anti-patrón de churn de tests y preservar el baseline y
  la Etapa 3.

## 12. Métricas tradicionales vs MQR (sin mezclar)

- **Tradicional:** bugs 0→0; vulnerabilities **1→0**; code_smells 161→158; violations 162→158;
  deuda (sqale_index) 783→768 min; duplicación 0%→0%; ratings reliability A→A, **security C→A**,
  maintainability A→A.
- **MQR:** impactos — SECURITY/MED **1→0**; RELIABILITY HIGH **1→0** (quedan MED 2 / LOW 3);
  MAINTAINABILITY HIGH 3→2, resto estable. Ratings MQR: maintainability A→A, **reliability D→C**,
  **security C→A**; remediación maintainability 743→728, reliability 60→55 min.
- Ambos modelos se reportan por separado; no se combinan sus escalas.

## 13. Regresiones, reintentos, limitaciones y amenazas metodológicas

- Reintentos reales (sin ocultar): corrección del orden de guardia ACH en recurrentes
  (`INVALID_SOURCE`→`RECURRING_ACH_NOT_USD`); literal SQLite `1000_00`; `Math.random` en el
  fallback de UUID (resuelto en T29); `openssl` del sistema no operable (cert vía `cryptography`);
  encoding cp1252 del runner (`PYTHONIOENCODING=utf-8`); componentes Stage 4 no entraban al bundle
  hasta integrarlos en `App.tsx` (41→45 módulos).
- Limitaciones y amenazas: ver `E4_KIRO_LIMITATIONS.md`.

## 14. Decisión Path A (dual-fixture) e implicaciones

Ver §6. Reversible, sin cambio de contrato de los Specs; mantiene verde la regresión heredada como
baseline preservado y aísla la aceptación de la Etapa 4 en la fixture D-02. Selección explícita y
determinista por `SHIFT_SEED_MODE`.

## 15. Iteraciones y evidencia cruda

- Iteraciones: `iteraciones/E4_Iteracion_01.md` … `E4_Iteracion_11.md`.
- Índice completo de evidencia: `E4_KIRO_EVIDENCE_INDEX.md`.
- Métricas consolidadas: `E4_KIRO_METRICS_SUMMARY.md`. Limitaciones: `E4_KIRO_LIMITATIONS.md`.

## 16. Medición D1 (cuenta NUEVA)

- PRE (provisto por el investigador, 2026-11-18, America/Bogota): **30,24 / 1000 créditos usados**,
  **969,76 restantes**. El snapshot 898,98 pertenece a OTRA cuenta (histórico, no baseline).
- Consumo de la Etapa 4 (deltas de créditos, conteos de interacción/tool-calls/subagentes,
  timestamps de sesión, snapshot POST): **N/D** — no hay export de uso de sesión en el workspace
  (`preparacion/D1/session-exports/` solo contiene `.gitkeep`; no se identificó archivo de uso).
  No se inventan totales. Detalle en `E4_KIRO_METRICS_SUMMARY.md`.

## 17. Veredicto

Etapa 4 (Kiro, SDD nativo): **31/31 tareas completas**. Aceptación funcional verificada sobre la
fixture D-02; regresión heredada preservada; carga y despliegue en vivo **PASS**; SonarQube POST
**Quality Gate OK** con la vulnerabilidad resuelta y mejora de ratings de seguridad y fiabilidad en
MQR, sin introducir issues. Evidencia cruda PRE/POST y de ejecución preservada.
