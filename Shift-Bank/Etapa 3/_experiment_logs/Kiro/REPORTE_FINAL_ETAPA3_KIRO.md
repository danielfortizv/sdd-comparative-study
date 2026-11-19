# REPORTE FINAL — Etapa 3 Shift Bank (Kiro)

**Tipo:** Consolidación de evidencia (solo lectura). No se ejecutó ningún escaneo nuevo, no se
modificó código de aplicación, no se refactorizó, y no se re-ejecutaron pruebas para este informe.
Cada veredicto se mapea a un artefacto real ya preservado en disco bajo
`Etapa 3/_experiment_logs/Kiro/`. Ninguna cifra es fabricada.

- **Fecha/hora (local):** 2026-11-17 15:40:56
- **Spec:** `Etapa 3/Kiro/.kiro/specs/shift-bank-stage3`
- **Contrato de aceptación externo:** matriz **AC-01 .. AC-16** (requirements.md Parte V)
- **Workspace de la app:** `Etapa 3/Kiro`

---

## 1. Resumen ejecutivo

- **Regresión completa VERDE** (T31/T34): backend **372 passed** (exit 0, cobertura 95%), build de
  frontend **exit 0**, Vitest **3 passed** (exit 0).
- **SonarQube PRE+POST** con mismo alcance y cobertura importada, gated por el investigador: neto
  **41/42 hallazgos corregidos del alcance confirmados FIXED; 1 nuevo S8786** (regex) apareció;
  **−41 code_smells**, **−214 min de deuda**; ratings **A** salvo **MQR reliability C**.
- **Carga (D-E3-03) PASS**: SLOs de lectura/transferencia cumplidos, 0% de errores inesperados,
  invariantes financieros íntegros.
- **Despliegue Docker/HTTPS (T25–T29) PASS**: build real, HTTPS 200 + redirección 301 + proxy de
  API + backend aislado, token `enc:` en la DB del volumen, `verify_chain` ok, fail-closed real,
  persistencia tras reinicio, contenedores no-root.
- **Veredicto AC:** 16/16 con backing real; **AC-15 PASS con 1 limitación documentada**
  (S8786 nuevo + Quality Gate de código-nuevo en ERROR). Ver §3 y §6.

---

## 2. Decisiones aprobadas (honradas y preservadas)

| Decisión | Contenido | Estado |
|---|---|---|
| **D-E3-01** | Cifrado AEAD (AES-GCM) de identificadores bancarios sensibles en reposo (token `enc:v1:kid:…`) + HTTPS/TLS en tránsito; claves externas por entorno; sin fallback a texto plano; fail-closed ante claves ausentes/inválidas | Honrada |
| **D-E3-02** | Cadena de auditoría HMAC append-only, encadenada; verificación vía rutina/endpoint protegido (`X-Admin-Token`); ancla de cola para truncación | Honrada |
| **D-E3-03** | Carga Locust: 30 usuarios, ramp 5/s, 60 s steady, mezcla 60/30/10, DB sintética aislada, distribución real medida | Honrada |
| **D-E3-04** | Topología Docker Compose (backend + Nginx TLS), red interna aislada, secretos por entorno, fail-closed, volumen persistente, un solo scheduler, no-root, verificación solo local | Honrada |

D-E3-01..04 se preservaron en todas las tareas (confirmado en notas T22, T23, T25–T31, T34).

---

## 3. Matriz de aceptación AC-01 .. AC-16 (veredicto + artefacto)

| AC | Caso de aceptación | Veredicto | Artefacto(s) de respaldo |
|----|--------------------|-----------|---------------------------|
| **AC-01** | Regresión de la funcionalidad bancaria heredada | **PASS** | `pruebas/2026-11-17T13-59-44_T31_regresion_completa_cobertura.md` (backend 372 passed, exit 0, cov 95%); `sonarqube/20261117-151451_T34_corrective_pass.md` (372 + 206 dirigida, verde) |
| **AC-02** | Cifrado de campos sensibles, payload cifrado, descifrado autorizado, sin fallback inseguro | **PASS** | `backend/tests/test_encryption_at_rest.py`, `test_crypto.py`, `test_regression_contract_no_ciphertext.py` (verdes en la suite 372); evidencia en volumen: `despliegue/…task29…md` §B (token `enc:v1:test:` en DB, plaintext ausente) |
| **AC-03** | Integridad del cifrado, texto cifrado manipulado, claves ausentes/obsoletas, rechazo seguro | **PASS** | `backend/tests/test_crypto.py`, `test_config_failclosed.py`, `test_encryption_migration.py` (suite 372); `pruebas/20261116-155227_task05_config_failclosed.md` |
| **AC-04** | Cifrado en reposo, migración idempotente, rollback ante corrupción | **PASS** | `backend/tests/test_encryption_migration.py`, `test_migration.py`, `test_migration_suite.py`; `pruebas/2026-11-16T16-12-09_T8_migracion_cifrado_idempotente_transaccional.md`; `pruebas/2026-11-16T16-07-43_T7_cifrado_en_reposo_bordes_io.md` |
| **AC-05** | Cadena de auditoría HMAC válida y verificable | **PASS** | `backend/tests/test_audit_chain.py`, `test_audit_schema.py`, `test_audit_integration.py`, `test_audit_access.py`; `pruebas/20261116-164454_tarea10_audit_chain.md`, `pruebas/2026-11-16T16-33-35_T9_esquema_auditoria_append_only_wal.md` |
| **AC-06** | Detección de manipulación y rechazo de UPDATE/DELETE ordinarios | **PASS** | `backend/tests/test_audit_tamper.py`, `test_audit_schema.py`; `pruebas/2026-11-16T16-57-58_tarea11_test_audit_tamper.md`, `pruebas/2026-11-16T19-42-23_tarea15_auditoria_protegida.md` |
| **AC-07** | Atomicidad financiera; fallo de auditoría/PIN inválido sin estados parciales | **PASS** | `backend/tests/test_audit_atomicity.py`, `test_regression_mfa.py`, `test_regression_internal_transfers.py`; `pruebas/2026-11-16T19-31-07_T14_atomicidad_rechazos_failclosed.md`, `pruebas/20261116-172305_tarea12_auditoria_transaccional.md` |
| **AC-08** | Auditoría durable de fallo/lockout de MFA sin mutaciones no autorizadas | **PASS** | `backend/tests/test_regression_mfa.py`, `test_audit_atomicity.py`, `test_audit_config_events.py`; `pruebas/2026-11-16T17-42-26_T13_auditoria_config_sensible.md` |
| **AC-09** | Concurrencia real multiproceso y lector/escritor sin bloquear lecturas | **PASS** | `backend/tests/test_concurrency_sqlite.py` (5 pruebas, WAL, SQLite 3.45.3); `backend/tests/test_loadtest_invariants.py` (15 pruebas); `pruebas/2026-11-16T19-49-19_T16_concurrencia_sqlite_lector_escritor_multiproceso.md`, `pruebas/2026-11-16T22-40-00_T22_verificacion_invariantes_post_carga.md` (verify_invariants + verify_chain íntegra) |
| **AC-10** | Carga Locust reproducible: 30 usuarios, ramp 5/s, 60 s steady, mezcla 60/30/10, DB aislada | **PASS** | `carga/20261117T111520__T23_verdict.json` (config D-E3-03 exacta; distribución real 60.45/29.97/9.57); `carga/20261117T111520__T23_baseline_nota.md`; CSVs/logs de Locust en `carga/` |
| **AC-11** | SLOs de rendimiento, evidencia exportada, distribución real medida | **PASS** | `carga/20261117T111520__T23_verdict.json` (read p95 37ms<200; transfer p95 46ms<500; unexpected 0%<1%; invariantes ok; exit 0) + artefactos CSV/JSON preservados |
| **AC-12** | Build/arranque de contenedores, HTTPS, healthchecks, redirección, proxy, secretos externos | **PASS** | `despliegue/20261117-125441_task25_backend_dockerfile.md`, `…task26_frontend_nginx.md`, `…task27_docker_compose.md`, `…task27_fix_topologia_red_despliegue.md`, `…task28_smoke_despliegue_rerun.md` (HTTPS 200, redirección 301, proxy API 200, backend aislado interno, healthchecks healthy) |
| **AC-13** | Despliegue persistente seguro, volumen aislado, no-root, supervivencia de cifrado/auditoría al reiniciar | **PASS** | `despliegue/20261117-135500_task29_funcionalidad_failclosed_persistencia.md` (A banca/MFA, B `enc:` en volumen, C `verify_chain` ok + fail-closed auth, D fail-closed ConfigError al quitar clave, E persistencia tras reinicio) |
| **AC-14** | Regresión completa Pytest + Vitest + build frontend, stdout y fallos intermedios preservados | **PASS** | `pruebas/2026-11-17T13-59-44_T31_regresion_completa_cobertura.md` (372 passed; build exit 0; Vitest 3 passed); `pruebas/2026-11-17_135606_tarea30_vitest_minimo_frontend.md` (Vitest mínimo) |
| **AC-15** | Baseline y medición final SonarQube reproducibles, mismo alcance y cobertura importada | **PASS (con 1 limitación)** | `sonarqube/20261117-143156_T32_PRE_EVIDENCE_INDEX_and_SUMMARY.md` (PRE); `sonarqube/20261117-154056_T35_POST_PRE_vs_POST_COMPARISON.md` (POST + comparación). Limitación: 1 nuevo S8786 + Quality Gate de código-nuevo en ERROR (ver §6) |
| **AC-16** | Documentación y métricas verificadas contra JSON/CLI/evidencia cruda | **PASS** | SLOs de carga en `carga/…T23_verdict.json`; escaneos Sonar comparables preservados en `sonarqube/` (PRE+POST raw JSON/logs); este informe traza cada cifra a su archivo |

**Conteo: 16/16 AC con respaldo real. 15 PASS pleno + 1 PASS con limitación documentada (AC-15).**
Ningún AC quedó UNVERIFIED.

---

## 4. Evidencia de regresión y pruebas (resumen de cifras reales)

Fuente: `pruebas/2026-11-17T13-59-44_T31_regresion_completa_cobertura.md` y
`sonarqube/20261117-151451_T34_corrective_pass.md`.

| Verificación | Resultado real | Exit |
|---|---|---|
| Backend Pytest (con cobertura) | **372 passed**, 2 warnings (preexistentes, no fallos), cobertura TOTAL **95%** (line-rate 0.952) | 0 |
| Build frontend (`tsc && vite build`) | 41 módulos, Vite 5.4.21 | 0 |
| Frontend Vitest (`vitest run --coverage`) | **3 passed** (1 archivo), LCOV generado (cobertura global 2.78%, documentada) | 0 |
| Sanity dirigida tras T34 (módulos tocados) | **206 passed**, 1 warning | 0 |
| Invariantes post-carga (`test_loadtest_invariants.py`) | **15 passed** | 0 |
| Concurrencia (`test_concurrency_sqlite.py`) | parte de los 372 (WAL lector/escritor + multiproceso) | 0 |

Las 2 warnings del backend son preexistentes y ajenas a cualquier cambio de Etapa 3:
`DeprecationWarning` de starlette/anyio y `ResourceWarning` de sqlite en un test de fail-closed.

---

## 5. Resultado SonarQube (PRE→POST)

Detalle completo en `sonarqube/20261117-154056_T35_POST_PRE_vs_POST_COMPARISON.md`.

- **Identidad:** PRE analysisId `b330beea-…` (CE `104e3187-…`, SUCCESS); POST analysisId `1f9cb39d-…`
  (CE `e36a0259-…`, SUCCESS); mismo `componentKey Shift-Bank---Stage-3---Kiro` / mismo `componentId
  47a1d7c4-…`. Alcance 1:1 confirmado (exclusiones/inclusiones idénticas, ambas coberturas importadas,
  3 lenguajes / 75 archivos indexados).
- **Deltas:** code_smells **172→131 (−41)**; sqale_index **831→617 min (−214, ~3h34m)**;
  cognitive_complexity 449→440; MQR maintainability effort 811→597; MQR reliability effort 205→20;
  coverage 44.1→44.4%; duplicación 0.0% en ambos.
- **Ratings:** reliability A / security A / security_review A / maintainability A (tradicional);
  MQR maintainability A, security A, **reliability C (3.0)** (se mantiene C). bugs 0, vulnerabilities 0,
  hotspots 0 en ambos.
- **Resolución:** 42 RESOLVED (todos FIXED) = exactamente los 42 objetivos de T34 (S6772×37, S3776×3,
  S1192×1, S8786×1). Reglas de alcance S3776/S1192/S6772 totalmente resueltas (0 sin resolver).
  **S8786 NO neto-resuelto:** el original en `AccountsPanel.tsx:14` quedó FIXED/CLOSED, pero apareció un
  **nuevo** S8786 en `AccountsPanel.tsx:17` (OPEN). Neto = **41/42** confirmados fijos.
- **Quality Gate:** PRE **OK** (primer análisis, sin línea base de código-nuevo); POST **ERROR** en
  condiciones de **código nuevo** (período PREVIOUS_VERSION = el análisis PRE): new_coverage 39.7<80
  (ERROR), new_violations 1>0 (ERROR, = el nuevo S8786), new_duplicated_lines_density 0.0 (OK);
  caycStatus compliant.

---

## 6. Limitaciones conocidas (reportadas sin maquillaje)

1. **Nuevo hallazgo S8786 (regex) en `frontend/src/components/AccountsPanel.tsx:17`** — `status=OPEN`,
   RELIABILITY:MEDIUM, es un `new_violation` del POST. El reemplazo de regex de T34 cerró el S8786
   original (línea 14) pero introdujo uno equivalente (línea 17). No se resolvió; **por instrucción del
   investigador no se ejecutó otra pasada correctiva**. Es la causa de que la MQR reliability siga en C.
2. **Quality Gate de código-nuevo en ERROR (POST)** — `new_coverage 39.7% < 80%` (impulsado por las
   pruebas mínimas de frontend) + `new_violations = 1` (el nuevo S8786). Es higiene de **código nuevo**,
   no una regresión de funcionalidad existente; la calidad global mejoró (−41 smells, −214 min deuda).
3. **Cobertura de frontend intencionalmente mínima** — 3 pruebas de humo (Task 30), cobertura global
   ~2.78%. Es un alcance deliberado documentado, no un defecto; el backend mantiene ~95%.
4. **AC-15** se marca **PASS con limitación** por (1) y (2): el baseline y la medición final son
   reproducibles y de mismo alcance con cobertura importada (lo que exige el AC), pero el resultado POST
   incluye el nuevo S8786 y el gate de código-nuevo en ERROR, que se reportan con honestidad.
5. **Modelo de amenazas de auditoría** (documentado en requirements §Requisito 6/limitaciones): la
   truncación del extremo solo es detectable con ancla externa; no se reclama inmutabilidad absoluta
   frente a un administrador con control total de DB+app+clave HMAC. Implementado y verificado con ancla
   de cola (AC-06 PASS dentro de ese modelo declarado).

---

## 7. Versiones del entorno (verificadas contra evidencia)

| Herramienta | Versión | Fuente |
|---|---|---|
| Python (venv backend) | 3.13.2 | T31 note, T16 note |
| pytest | 8.3.4 | T31 note |
| coverage.py | 7.17.3 | T31 note (line-rate 0.952) |
| pytest-cov | 7.1.0 | T31 note |
| Node.js | v20.17.0 | T31 note (entorno de la regresión) |
| npm | 11.6.3 | T31 note |
| Vitest | 2.1.9 | T31 note |
| Vite | 5.4.21 | T31 note |
| @vitest/coverage-v8 | 2.1.9 (devDependency) | T31 note |
| Locust | 2.47.0 | `carga/…T23_verdict.json` |
| Docker Engine | 29.9.3 | `despliegue/…task29…md` |
| SonarQube | 26.9.0 (Community Build 26.9.0.129388) | scanner.log PRE/POST |
| SonarScanner CLI | 8.1.0.6389 | scanner.log PRE/POST |

> Nota: `_experiment_logs/Kiro/ENTORNO.md` (captura de setup, 2026-11-16) registra Node v24.19.0 /
> npm 11.17.0 a nivel de SO; la regresión autoritativa de cierre (T31) se ejecutó con el Node v20.17.0
> del proyecto frontend. Se citan las versiones de T31 por ser las de las ejecuciones de evidencia.

---

## 8. Integridad experimental

- Sin escaneo nuevo, sin cambios de código de app, sin refactor, sin re-ejecución de pruebas para este
  informe. Toda cifra traza a un archivo preservado.
- Ningún token/secreto ni material de clave se escribió en este documento.
- Evidencia PRE de Sonar intacta (`20261117-143156_T32_PRE_*`).
- Decisiones **D-E3-01..D-E3-04 preservadas**.
- Sin referencias a otras metodologías de spec.

---

## 9. Veredicto de cierre

**Etapa 3 (Kiro): COMPLETA.** Los 16 AC tienen respaldo en evidencia real: **15 PASS pleno** y
**1 PASS con limitación documentada (AC-15)**. T35 y T36 cumplen sus criterios de aceptación:
T35 produjo la verificación POST + comparación PRE/POST desde datos reales preservados; T36 consolida
los 16 AC con rutas de artefacto y resultados reales, incluyendo las limitaciones conocidas sin maquillar.
El único punto abierto (nuevo S8786 + gate de código-nuevo en ERROR) está documentado y fue dejado así
por instrucción del investigador — no bloquea el cierre de la Etapa.
