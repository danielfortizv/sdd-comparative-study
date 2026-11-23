# Implementation Plan: Shift Bank Etapa 4 (Opción A)

> Plan de implementación nativo de Kiro para la Etapa 4. Cada tarea deriva de un requisito
> aprobado (`requirements.md`, R1–R20), de un componente del diseño (`design.md`, §1–§7) y de las
> decisiones D-01..D-14 y DK-01..DK-05 y la matriz AC4-01..AC4-20. Encabezados canónicos en inglés
> para el validador; contenido en español por coherencia con las Etapas 1–3.

## Overview

## Resumen

Objetivo: plan **dependency-ordered** ejecutable con "Run All Tasks" con mínimo prompting
adicional. Orden macro (milestones):

- **M0 — Baseline y evidencia inicial** (regresión heredada verde + evidencia D1 del NUEVO
  account).
- **M1 — Esquema multidivisa, fixture D-02 y FX exacto** (D-01/D-02/D-03 → R1–R4, R15).
- **M2 — Event Sourcing, CQRS y patrón de comando** (D-05/D-06/D-09 → R6–R8, R13).
- **M3 — Idempotencia y concurrencia optimista** (D-13/D-14 → R9–R10).
- **M4 — Operaciones currency-aware** (D-04/D-07/D-08 → R5, R11–R12): internas, conversiones, ACH,
  recurrentes, límites, MFA.
- **M5 — Frontend multidivisa** (D-10 → R14).
- **M6 — Atomicidad/concurrencia/fallo/recuperación + regresión + cobertura + carga + despliegue**
  (D-11/D-12 → R13, R16, R19).
- **M7 — SonarQube PRE/POST (gates) y evidencia/reporte final** (D-12 → R16).

Separación explícita: las tareas `(auto)` son ejecutables automáticamente; las `(GATE
INVESTIGADOR)` requieren revisión/aprobación externa y **detienen** la ejecución automática. Un
servicio no disponible o evidencia faltante NO cuenta como aprobado: la tarea de verificación
falla.

## Convenciones

- `[ ]` tarea pendiente. `(auto)` ejecutable por el agente; `(GATE INVESTIGADOR)` requiere
  aprobación humana antes de continuar; `(verificación)` es prueba/validación.
- Trazabilidad: `_Requisitos: R.n_` a `requirements.md`; `_Diseño:_` a secciones de `design.md`;
  `_AC:_` a la matriz externa; `_D:_`/`_DK:_` a decisiones.
- **Nunca** se alteran datos ni evidencia de la Etapa 3 ni `SEED-4.md`. Toda prueba/corrida usa
  **DB y volúmenes desechables aislados** (patrón `conftest.py`: parchear `config.DB_PATH` antes
  de importar la app; o DB temporal dedicada para carga/despliegue).
- Capturar **evidencia cruda** (stdout, JSON/CSV, versiones de entorno, comandos exactos) en
  `_experiment_logs/Kiro/` sin sobrescribir artefactos previos (nombres con timestamp).
- Sin dependencias de runtime externas no aprobadas (sin ORM, broker, vendor cloud, API FX,
  event-store externo). `fractions`/`decimal` son stdlib; Locust es **solo dev**.
- Nunca marcar como PASS una validación fallida o no ejecutada.

## Task Dependency Graph

```
M0 ─▶ M1 ─▶ M2 ─▶ M3 ─▶ M4 ─▶ M6 ─▶ M7
                         │      ▲
                         └─ M5 ─┘
```

Definición de olas (wave scheduling) para "Run All Tasks" en `tasks.meta.json`. Las tareas de una
ola dependen de las olas previas; las tareas `gate` detienen la ejecución automática hasta
aprobación del investigador.

### Gates de investigador (detienen "Run All Tasks")

1. **G-SPEC** — Aprobación de los tres Specs antes de implementar (tarea 4).
2. **G-SONAR-PRE** — Revisión del PRE-scan de la Etapa 4 (tras implementar/probar y regresión/
   cobertura), antes de la fase correctiva (tarea 28).
3. **G-SONAR-FINAL** — Aprobación del escaneo final (mismo alcance/cobertura, comparable 1:1 con
   el PRE) (tarea 30).

---

## Tasks

## Tareas

## M0 — Baseline y evidencia inicial

> Depende de: nada. Fija el verde heredado y la evidencia D1 ANTES de cualquier cambio.

- [x] 1. (auto) (verificación) Capturar la regresión heredada verde de partida
  - Ejecutar la suite backend heredada (`python -m pytest -q` desde `backend/`, venv aislado) y
    Vitest + build de producción del frontend; preservar stdout/exit codes con timestamp en
    `_experiment_logs/Kiro/E4/baseline/`.
  - Criterio de aceptación: backend verde (se registra el conteo observado real, p. ej. 372
    passed), Vitest verde, build exit 0. No se afirma ningún número sin observarlo.
  - _Requisitos: R16_ · _Diseño: Testing Strategy_ · _AC: AC4-20_

- [x] 2. (auto) Registrar el baseline de medición D1 del NUEVO account
  - Registrar en `_experiment_logs/Kiro/E4/D1/` el snapshot PRE provisto: NUEVO Kiro Student,
    30.24/1000 usados, 969.76 restantes, 2026-11-18 (America/Bogota). Marcar explícitamente que el
    snapshot 898.98 pertenece a OTRO account (histórico, no baseline actual).
  - Criterio de aceptación: existe el registro D1 del nuevo account; no se mezcla con el histórico;
    no se inventan totales de tokens/créditos/tiempo.
  - _Requisitos: R16_ · _DK: medición_ · _AC: AC4-19_

- [x] 3. (auto) Preparar la captura de evidencia experimental de la Etapa 4
  - Crear la estructura de evidencia `_experiment_logs/Kiro/E4/` (baseline, migracion, eventos,
    concurrencia, carga, despliegue, sonar, reporte) con convención de nombres con timestamp.
  - Criterio de aceptación: estructura creada; no sobrescribe artefactos previos.
  - _Requisitos: R16_ · _AC: AC4-20_

- [x] 4. (GATE INVESTIGADOR) Aprobación de los Specs de la Etapa 4 (requirements/design/tasks)
  - APROBADO por el investigador (2026-11-18) condicionado a que las tareas 1–3 estén completas
    con evidencia real registrada; condición verificada: backend 372 passed, Vitest 3 passed,
    build 41 módulos, D1 del nuevo account registrado, estructura de evidencia creada.
  - Confirmación del investigador de los tres Specs nativos y de las decisiones DK-01..DK-05 antes
    de implementar.
  - Criterio de aceptación: aprobación explícita registrada. Sin aprobación, "Run All Tasks" se
    detiene aquí.
  - _Requisitos: R1–R20_ · _AC: AC4-01..AC4-20_

## M1 — Esquema multidivisa, fixture D-02 y FX exacto

> Depende de: M0. Introduce moneda, identificadores públicos, versión y el motor FX.

- [x] 5. (auto) Migración de esquema aditiva: `account` (currency/public_id/version) + índices
  - Extender `db.migrate` con `ALTER TABLE account ADD COLUMN currency/public_id/version`, índice
    único de `public_id` y unicidad `(customer_id, kind, currency)`; backfill `currency='USD'`;
    todo idempotente/transaccional con rollback total ante fallo. No eliminar nada heredado.
  - Criterio de aceptación: migración idempotente (re-ejecutable), re-run no duplica; rollback
    probado; `test_migration_suite` extendido verde.
  - _Requisitos: R1, R2, R15_ · _Diseño: §1.1, §7_ · _D: D-01, D-02, DK-02, DK-03_ · _AC: AC4-01,
    AC4-02, AC4-14_

- [x] 6. (auto) Fixture experimental de la Etapa 4 (seed D-02) sin tocar la Etapa 3
  - `seed` de la Etapa 4: CHK-1001 USD 2,500.00, SAV-2001 USD 10,000.00, EUR-3001 EUR 0.00,
    GBP-4001 GBP 0.00, con `public_id` inmutables; idempotente; no lee ni modifica datos de la
    Etapa 3. Documentar la discontinuidad experimental (no conversión COP→USD).
  - Criterio de aceptación: las cuatro cuentas existen con saldos/monedas/ids exactos; seed
    idempotente; nota de discontinuidad presente; evidencia de que la Etapa 3 permanece intacta.
  - _Requisitos: R2, R15_ · _Diseño: §7_ · _D: D-02, DK-01_ · _AC: AC4-03, AC4-19_

- [x] 7. (auto) Motor FX exacto (`app/fx.py`) con tasas racionales fijas y `ROUND_HALF_UP`
  - Implementar `fx.convert` (via `fractions.Fraction`, redondeo una sola vez al final) y
    `fx.usd_equivalent_minor` (sin redondear para MFA; redondeado para límites). Tasas fijas en
    `config.py`. Extender `money.py` a multidivisa (2 decimales por moneda). Sin floats, sin
    servicio externo.
  - Criterio de aceptación: `test_fx` verde: identidad `src==dst`, conservación bajo las reglas de
    redondeo, `ROUND_HALF_UP` aplicado una sola vez, determinismo para igual entrada.
  - _Requisitos: R3, R4, R11_ · _Diseño: §2_ · _D: D-03, D-07_ · _AC: AC4-04, AC4-05, AC4-06_

## M2 — Event Sourcing, CQRS y patrón de comando

> Depende de: M1. Almacén de eventos, proyecciones y la envoltura transaccional de comando.

- [x] 8. (auto) Almacén de eventos de dominio (`domain_event`) append-only, separado de auditoría
  - DDL `domain_event` (+ `UNIQUE(aggregate_id, aggregate_ver)`, índices, triggers append-only) en
    `db.migrate`; módulo `app/events.py` con `append_event`/`read_events`. Separado de `audit_log`.
  - Criterio de aceptación: `test_event_store` verde: inserción append-only, rechazo de
    UPDATE/DELETE ordinarios, unicidad de versión por agregado, independencia de `audit_log`.
  - _Requisitos: R6, R7_ · _Diseño: §1.2, §5_ · _D: D-05, D-09_ · _AC: AC4-08, AC4-09_

- [x] 9. (auto) Proyecciones CQRS (`account_projection`) y reconstrucción determinista
  - DDL `account_projection`; `app/projections.py` con `apply_event_to_projection` (síncrono,
    misma transacción) y `rebuild_projections` (determinista desde eventos). Guarda de
    consistencia `projection.version == account.version`.
  - Criterio de aceptación: `test_projection` verde: proyección == suma de eventos; rebuild
    reproduce el mismo estado; inconsistencia → fail-closed.
  - _Requisitos: R8_ · _Diseño: §1.3, §7_ · _D: D-06_ · _AC: AC4-10, AC4-14_

- [x] 10. (auto) Patrón de comando atómico (`app/command.py`): evento+proyección+auditoría+versión
  - `with_command` que, dentro de `financial_transaction`, aplica evento(s), actualiza
    proyección(es), escribe auditoría y hace bump de versión de cuenta, atómicamente (fail-closed
    ante cualquier fallo). (La idempotencia se integra en M3, tarea 11.) Reutiliza
    `txn.financial_transaction` y `audit.append_in_tx`.
  - Criterio de aceptación: `test_command_atomicity` verde: todos los efectos se confirman juntos;
    un fallo inyectado revierte todo; sin estados parciales.
  - _Requisitos: R7, R8, R13_ · _Diseño: §3.1, §4_ · _D: D-09, D-11, DK-03_ · _AC: AC4-09, AC4-12_

## M3 — Idempotencia y concurrencia optimista

> Depende de: M2. Clave de idempotencia y versión esperada, en el orden D-13→D-14.

- [x] 11. (auto) Idempotencia (`idempotency_key`) y versión optimista en el patrón de comando
  - DDL `idempotency_key`; integrar en `with_command`: (1) replay idempotente **antes** de versión
    (DK-04); replay exacto → respuesta original sin efectos; reuse con payload distinto → 409
    `IDEMPOTENCY_CONFLICT`. (2) versión esperada por cuenta; mismatch → 409
    `ACCOUNT_VERSION_CONFLICT`. Header `Idempotency-Key` UUID obligatorio para internas/FX/ACH;
    `Expected-Version` por cuenta.
  - Criterio de aceptación: `test_idempotency` y `test_optimistic_concurrency` verdes: replay sin
    nuevos efectos; payload distinto → 409; versión obsoleta → 409; replay precede a versión;
    registro atómico con el efecto.
  - _Requisitos: R9, R10, R13_ · _Diseño: §1.4, §3.1_ · _D: D-13, D-14, DK-04_ · _AC: AC4-13,
    AC4-15, AC4-16_

## M4 — Operaciones currency-aware

> Depende de: M3. Conversiones, internas misma-moneda, ACH/recurrentes, límites y MFA en USD-eq.

- [x] 12. (auto) Conversión FX (`conversion_service.py` + `routers/conversions.py`)
  - `POST /api/conversions`: valida monedas/cuentas, calcula con `fx`, debita origen/abona destino,
    emite evento **compuesto** (debited+credited, mismo `operation_id`), expone tasa+origen+
    destino+registros; pasa por `with_command` (idempotencia/versión/atomicidad).
  - Criterio de aceptación: `test_conversion` verde: respuesta con tasa/origen/destino; balance
    conservado por reglas de redondeo; moneda no soportada → rechazo sin mover saldos; idempotencia
    y versión aplicadas.
  - _Requisitos: R3, R4, R9, R10_ · _Diseño: §3.2_ · _D: D-03, D-13, D-14_ · _AC: AC4-05, AC4-06,
    AC4-15_

- [x] 13. (auto) Transferencias internas misma-moneda (`service.py` adaptado)
  - Exigir misma moneda; cross-currency → `CROSS_CURRENCY_NOT_ALLOWED` (remite a `/api/conversions`);
    preservar MFA/fondos/estados/expiración; débito/crédito vía `with_command` (eventos+proyección+
    auditoría+idempotencia+versión).
  - Criterio de aceptación: `test_regression_internal_transfers` adaptado verde; cross-currency
    rechazado; misma-moneda completa con evento/proyección/versión correctos.
  - _Requisitos: R5, R9, R10, R13_ · _Diseño: §3.3_ · _D: D-04_ · _AC: AC4-07_

- [x] 14. (auto) Límites y MFA en equivalente USD (`limit_service.py` adaptado)
  - Calcular consumo/límites en equivalente USD (5,000.00 op / 10,000.00 diario, día UTC); MFA si
    equivalente USD **sin redondear** `> 1,000.00`; verificación autoritativa dentro de la
    transacción; orden fondos→límites→MFA.
  - Criterio de aceptación: `test_limits` adaptado verde: límites/MFA en USD-eq para USD/EUR/GBP;
    umbral estricto sin redondear; sin TOCTOU.
  - _Requisitos: R11_ · _Diseño: §3.5_ · _D: D-07_ · _AC: AC4-17_

- [x] 15. (auto) Restricciones de divisa para ACH y recurrentes (`ach_service`/`recurring_service`)
  - ACH solo origen USD; recurrentes internos misma moneda; recurrentes ACH solo USD; preservar
    ciclo ACH (débito pending, settlement sin doble débito, un único reembolso) y ejecución
    recurrente idempotente (único scheduler), ahora emitiendo eventos de dominio.
  - Criterio de aceptación: `test_ach`/`test_recurring*` adaptados verdes: guardias de moneda;
    exactamente-una-vez preservado; eventos sin doble débito/crédito.
  - _Requisitos: R7, R12_ · _Diseño: §3.4_ · _D: D-08, D-09_ · _AC: AC4-11, AC4-18_

## M5 — Frontend multidivisa

> Depende de: M4 (contratos de API currency-aware). Puede ejecutarse junto a M6.

- [x] 16. (auto) Adaptar tipos, cliente API y headers de comando en el frontend
  - `types.ts`: `Account` con `public_id`/`currency`; tipos de conversión; cliente añade
    `Idempotency-Key` (UUID) y `Expected-Version`; manejo de 409 idempotencia/versión. Montos como
    `string`/`BigInt`, nunca `number`.
  - Criterio de aceptación: Vitest verde; build exit 0; sin `number` para dinero; 409 manejado.
  - _Requisitos: R14_ · _Diseño: §6_ · _D: D-03, D-10, D-13, D-14_ · _AC: AC4-04, AC4-19_

- [x] 17. (auto) Dashboard multidivisa y formulario de conversión (UI)
  - `AccountsPanel`: totales separados por moneda; total USD **estimado (solo visualización)**.
    Nuevo `ConversionForm` que muestra tasa/origen/destino. Preservar flujos heredados.
  - Criterio de aceptación: Vitest/build verdes; totales por moneda sin mezclar; USD estimado
    etiquetado; conversión muestra tasa.
  - _Requisitos: R14_ · _Diseño: §6_ · _D: D-10_ · _AC: AC4-19_

## M6 — Atomicidad, concurrencia, fallo/recuperación, regresión, cobertura, carga, despliegue

> Depende de: M4 y M5. Verificación profunda y preservación de capacidades heredadas.

- [x] 18. (auto) (verificación) Atomicidad compuesta y fail-closed end-to-end
  - Probar que evento+proyección+auditoría+idempotencia+versión se confirman/revierten juntos ante
    fallos inyectados en cada punto; sin dobles débitos/créditos ni aplicación duplicada de eventos.
  - Criterio de aceptación: `test_command_atomicity`/`test_audit_atomicity` verdes; inconsistencia
    → `PROJECTION_INCONSISTENT` fail-closed.
  - _Requisitos: R13, R19_ · _Diseño: §3.1, §4_ · _D: D-11_ · _AC: AC4-12_

- [x] 19. (auto) (verificación) Event Sourcing/CQRS: persistencia, replay y rebuild sin doble conteo
  - Probar persistencia de eventos, replay determinista, `rebuild_projections` == estado vivo, y
    migración de fixture/históricas sin doble conteo.
  - Criterio de aceptación: `test_event_store`/`test_projection`/`test_rebuild` verdes; rebuild
    reproduce saldos exactos; sin doble conteo.
  - _Requisitos: R6, R8, R15_ · _Diseño: §1.2, §1.3, §7_ · _D: D-05, D-06_ · _AC: AC4-08, AC4-10,
    AC4-14_

- [x] 20. (auto) (verificación) Concurrencia: idempotencia, versión y multiproceso SQLite
  - Reintentos concurrentes con misma `Idempotency-Key` (un solo efecto); solicitudes con versión
    obsoleta (409); multiproceso lector/escritor con invariantes financieros y cadena de auditoría
    verificable.
  - Criterio de aceptación: `test_concurrency_sqlite` adaptado + `test_idempotency`/
    `test_optimistic_concurrency` verdes; sin corrupción de datos ni de la cadena.
  - _Requisitos: R9, R10, R19_ · _Diseño: §3.1_ · _D: D-13, D-14_ · _AC: AC4-13, AC4-15_

- [x] 21. (auto) (verificación) Fallo y recuperación: retry ACH, reembolso único, recovery tras reinicio
  - Probar fallo+reembolso ACH exactamente-una-vez con eventos; recuperación del scheduler tras
    reinicio vía `next_run_at`/`schedule_execution` (sin estado en memoria).
  - Criterio de aceptación: `test_ach`/`test_scheduler`/`test_recurring_execution` adaptados verdes;
    un único reembolso; sin doble ejecución.
  - _Requisitos: R7, R12, R19_ · _Diseño: §3.4_ · _D: D-08, D-09_ · _AC: AC4-11, AC4-18_

- [x] 22. (auto) (verificación) Regresión completa backend + frontend
  - Ejecutar toda la suite Pytest + Vitest + build de producción; comparar con el baseline M0;
    preservar evidencia cruda. No afirmar verde sin observarlo.
  - Criterio de aceptación: Pytest verde (conteo observado), Vitest verde, build exit 0; evidencia
    con timestamp.
  - _Requisitos: R16_ · _Diseño: Testing Strategy_ · _AC: AC4-20_

- [x] 23. (auto) Generación de cobertura (backend + frontend)
  - Generar cobertura (`pytest --cov` + cobertura de Vitest) e importarla como evidencia para
    SonarQube; preservar reportes.
  - Criterio de aceptación: reportes de cobertura generados y preservados; comandos exactos
    registrados.
  - _Requisitos: R16_ · _AC: AC4-20_

- [x] 24. (auto) (verificación) Carga Locust con invariantes multidivisa
  - Reutilizar el arnés Locust heredado con DB sintética aislada; incluir alguna conversión/op
    multidivisa válida; verificar invariantes financieros post-carga (conservación por moneda,
    cadena de auditoría, consistencia de proyección). Preservar resultados legibles por máquina.
  - Criterio de aceptación: `verify_invariants` post-carga sin violaciones; resultados preservados;
    cualquier violación de invariante → FALLA, con independencia de métricas.
  - _Requisitos: R16, R19_ · _Diseño: Testing Strategy_ · _D: D-12_ · _AC: AC4-20_

- [x] 25. (auto) (verificación) Validación de despliegue local (Compose/Nginx/TLS) — COMPLETA:
  ciclo en vivo verificado — `docker compose build`/`up` (exit 0), backend+nginx healthy, HTTPS
  `GET /api/v2/accounts` 200 con fixture D-02, redirección HTTP→HTTPS 301, reverse-proxy de API,
  conversión multidivisa por HTTPS 200, persistencia tras `restart` (volumen SQLite), auditoría
  `verify` {"ok":true}, y fail-closed con claves vacías (backend no arranca). Stack y volumen
  eliminados (`down -v`), `.env`/`certs` borrados, workspace limpio. Evidencia:
  `_experiment_logs/Kiro/E4/despliegue/`.
  - `docker compose config`/build/up de ambos servicios con healthchecks; smoke HTTPS + redirect +
    proxy /api + una operación representativa (incluida una conversión) sobre TLS; persistencia
    tras reinicio; fail-closed sin claves. Volúmenes desechables aislados. No reclamar despliegue
    verificado sin observarlo.
  - Criterio de aceptación: evidencia de build/up/health/HTTPS/redirect/proxy/persistencia/
    fail-closed; sin afirmaciones no observadas.
  - _Requisitos: R16_ · _Diseño: Architecture_ · _D: D-12_ · _AC: AC4-20_

## M7 — Calidad (SonarQube) y evidencia/reporte final

> Depende de: M6. Escaneos controlados por gates y consolidación de evidencia.

- [x] 26. (auto) Preparar `sonar-project.properties` de la Etapa 4 (proyecto key separado)
  - Configurar un project key separado del de la Etapa 3 (preservar el de la Etapa 3 como
    referencia histórica); incluir rutas de cobertura importada.
  - Criterio de aceptación: configuración lista y versionada; no reutiliza el key de la Etapa 3.
  - _Requisitos: R16_ · _AC: AC4-20_

- [x] 27. (auto) Escaneo SonarQube PRE de la Etapa 4 (tras implementar/probar; antes de corregir)
  - Ejecutar el PRE-scan con la cobertura importada, DESPUÉS de implementar/probar y de la
    regresión/cobertura.
  - Criterio de aceptación: PRE-scan ejecutado con cobertura; resultados preservados. Si el
    servicio no está disponible, la tarea FALLA (no PASS).
  - _Requisitos: R16_ · _D: D-12_ · _AC: AC4-20_

- [x] 28. (GATE INVESTIGADOR) Revisión del PRE-scan antes de la fase correctiva
  - APROBADO por el investigador (2026-11-19): PRE verificado — analysisId
    cd37bcc9-6884-4dd4-a92a-d4e8f374cb62, Quality Gate OK, 162 issues (0 bugs / 1 vuln / 161 code
    smells), cobertura 49.7%, deuda 783 min. Evidencia PRE original preservada en
    `_experiment_logs/Kiro/E4/sonarqube/`. Autoriza T29 (una pasada correctiva acotada).
  - Revisión del investigador del PRE-scan de la Etapa 4 antes de cualquier corrección dirigida.
  - Criterio de aceptación: aprobación registrada; "Run All Tasks" se detiene aquí hasta aprobar.
  - _Requisitos: R16_ · _AC: AC4-20_

- [x] 29. (auto) Correcciones dirigidas por SonarQube (sin cambiar comportamiento aprobado)
  - Resolver hallazgos sin alterar contratos ni invariantes aprobados; re-ejecutar regresión tras
    las correcciones.
  - Criterio de aceptación: hallazgos abordados; regresión verde tras corregir; sin cambio de
    comportamiento aprobado.
  - _Requisitos: R16_ · _AC: AC4-20_

- [x] 30. (GATE INVESTIGADOR) (verificación) Escaneo final de SonarQube (mismo alcance/cobertura)
  - Escaneo final comparable 1:1 con el PRE (mismo alcance y cobertura), aprobado por el
    investigador.
  - Criterio de aceptación: escaneo final ejecutado y aprobado; comparable al PRE. Sin servicio o
    sin evidencia → FALLA, no PASS.
  - _Requisitos: R16_ · _D: D-12_ · _AC: AC4-20_

- [x] 31. (auto) Consolidar la evidencia experimental final y el reporte de la Etapa 4
  - Consolidar evidencia (baseline, migración/discontinuidad, eventos/replay, concurrencia, carga,
    despliegue, sonar PRE/POST, D1 del nuevo account) y un reporte final que documente la
    discontinuidad experimental DK-01 y el uso real disponible. No inventar totales de
    tokens/créditos/tiempo.
  - Criterio de aceptación: reporte final presente con enlaces a evidencia cruda; discontinuidad
    documentada; sin cifras inventadas.
  - _Requisitos: R15, R16_ · _DK: DK-01, medición_ · _AC: AC4-19, AC4-20_
