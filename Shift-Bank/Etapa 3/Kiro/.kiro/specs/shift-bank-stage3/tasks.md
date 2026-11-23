# Implementation Plan: Shift Bank Etapa 3 (Opción A)

> Plan de implementación nativo de Kiro para la Etapa 3. Cada tarea deriva de un requisito
> aprobado (`requirements.md`, R1–R19), de un componente del diseño (`design.md`, §1–§12, gates
> G0–G9) y de las decisiones D-E3-01..D-E3-04 y la matriz AC-01..AC-16. Encabezados canónicos en
> inglés para el validador; contenido en español por coherencia con las Etapas 1 y 2.

## Overview

## Resumen

Objetivo: plan **dependency-ordered** ejecutable con "Run all Tasks" con mínimo prompting
adicional. Orden macro (milestones):

- **M0 — Baseline y evidencia inicial** (regresión heredada + SonarQube baseline con cobertura).
- **M1 — Cifrado, claves y migración** (D-E3-01 → R1–R3).
- **M2 — Auditoría transaccional, integridad y concurrencia** (D-E3-02 → R5–R8, R17).
- **M3 — Carga Locust, benchmark e invariantes** (D-E3-03 → R9, R10).
- **M4 — Docker Compose, HTTPS, persistencia y smoke** (D-E3-04 → R4, R11–R13).
- **M5 — Regresión final y evidencia experimental** (R14, R19; incluye corrección SonarQube).

Separación explícita: las tareas `(auto)` son ejecutables automáticamente; las `(GATE
INVESTIGADOR)` requieren revisión/aprobación externa y **detienen** la ejecución automática. Un
servicio no disponible o evidencia faltante NO cuenta como aprobado: la tarea de verificación
falla.

## Convenciones

- `[ ]` tarea pendiente. `(auto)` ejecutable por el agente; `(GATE INVESTIGADOR)` requiere
  aprobación humana antes de continuar; `(verificación)` es prueba/validación.
- Trazabilidad: `_Requisitos: R.n_` a criterios de `requirements.md`; `_Diseño:_` a secciones/
  gates de `design.md`; `_AC:_` a la matriz externa.
- **Nunca** se alteran datos históricos de la Etapa 2 ni `SEED-3.md`. Todas las pruebas y
  corridas usan **DB y volúmenes desechables aislados** (patrón `conftest.py`: parchear
  `config.DB_PATH` antes de importar la app; o DB temporal dedicada para carga/despliegue).
- Capturar **evidencia cruda** (stdout, JSON/CSV, versiones de entorno, comandos exactos) en
  `_experiment_logs/Kiro/` sin sobrescribir artefactos previos (nombres con timestamp).
- Sin dependencias de runtime innecesarias: `cryptography` es runtime; `locust` y
  (opcional) Vitest son **solo de pruebas/dev**.

## Task Dependency Graph

```
M0 (baseline) ─▶ M1 (cifrado) ─▶ M2 (auditoría) ─▶ M3 (carga) ─▶ M5 (evidencia final)
                      │                │               │
                      └────────────────┴───────────────┴────────▶ M4 (despliegue) ─▶ M5
```

Definición de olas (wave scheduling) para "Run all Tasks". Las tareas de una ola dependen de las
olas previas; las tareas marcadas `gate` detienen la ejecución automática hasta aprobación.

```json
{
  "waves": [
    { "wave": 0, "milestone": "M0", "tasks": [1, 2, 3, 4], "depends_on": [] },
    { "wave": 1, "milestone": "M1", "tasks": [5, 6], "depends_on": [0] },
    { "wave": 2, "milestone": "M1", "tasks": [7], "depends_on": [1] },
    { "wave": 3, "milestone": "M1", "tasks": [8], "depends_on": [2] },
    { "wave": 4, "milestone": "M2", "tasks": [9, 10, 11], "depends_on": [3] },
    { "wave": 5, "milestone": "M2", "tasks": [12, 13], "depends_on": [4] },
    { "wave": 6, "milestone": "M2", "tasks": [14, 15, 16, 17], "depends_on": [5] },
    { "wave": 7, "milestone": "M3", "tasks": [18, 19, 20, 21, 22, 23], "depends_on": [6] },
    { "wave": 8, "milestone": "M3", "tasks": [24], "gate": true, "depends_on": [7] },
    { "wave": 9, "milestone": "M4", "tasks": [25, 26, 27, 28, 29], "depends_on": [6] },
    { "wave": 10, "milestone": "M5", "tasks": [30, 31], "depends_on": [8, 9] },
    { "wave": 11, "milestone": "M5", "tasks": [32], "depends_on": [10] },
    { "wave": 12, "milestone": "M5", "tasks": [33], "gate": true, "depends_on": [11] },
    { "wave": 13, "milestone": "M5", "tasks": [34], "depends_on": [12] },
    { "wave": 14, "milestone": "M5", "tasks": [35], "gate": true, "depends_on": [13] },
    { "wave": 15, "milestone": "M5", "tasks": [36], "depends_on": [14] }
  ],
  "gates": {
    "24": "G-LOAD",
    "33": "G-SONAR-PRE autorizacion fase correctiva",
    "35": "G-SONAR-FINAL"
  }
}
```

- **M0** precede a todo (fija el verde heredado y prepara cobertura/escáner; el PRE-scan de la Etapa 3 NO va aquí).
- **M1** (claves→cifrado→migración) precede a **M2** (la auditoría usa la misma clave externa y
  el mismo límite transaccional, y audita operaciones ya cifradas).
- **M2** precede a **M3** (la corrección bajo concurrencia se mide sobre auditoría+cifrado
  estables; "no optimizar antes del primer baseline de carga").
- **M4** (despliegue) depende de **M2** (app cifrada+auditada funcional) y puede ir en paralelo a
  **M3**, pero ambos preceden a **M5**.
- **M5** cierra: regresión completa → **PRE-scan de SonarQube** (T32) → gate de revisión (T33) → corrección acotada (T34) → escaneo final (T35) → evidencia.

### Gates de investigador (detienen "Run all Tasks")

1. **G-LOAD** — Revisión del **primer baseline de carga válido** antes de cualquier optimización
   (tarea 24).
2. **G-SONAR-PRE** — Revisión del **PRE-scan de la Etapa 3** (T32), ejecutado DESPUÉS de
   implementar/probar las capacidades y la regresión/cobertura, con cobertura importada, antes de
   la fase correctiva (gate en la tarea 33).
3. **G-SONAR-FINAL** — Aprobación del **escaneo final** de SonarQube (mismo alcance/cobertura,
   comparable 1:1 con el PRE) (gate en la tarea 35).

---

## Tasks

## Tareas

## M0 — Baseline y evidencia inicial (gate G0)

> Depende de: nada. Fija el verde heredado y el baseline de calidad ANTES de cualquier cambio.

- [x] 1. (auto) (verificación) Capturar la regresión heredada verde de partida
  - Ejecutar la suite backend heredada completa (`python -m pytest -q` desde `backend/`, venv) y
    el build de frontend (`npm run build`), preservando **stdout** y conteos.
  - Verificación: suite backend 100% PASS y build exit 0; registrar versiones (Python, Node, npm)
    y comandos exactos. Si algo falla, DETENER (no es baseline válido).
  - _Requisitos: R14, R19.1, R19.2_ · _Diseño: §8 G0_ · _AC: AC-01, AC-14_

- [x] 2. (auto) Preparar la captura de evidencia experimental de la Etapa 3
  - Crear la estructura `_experiment_logs/Kiro/` para sesiones/pruebas/sonarqube/carga/despliegue
    (sin sobrescribir evidencia previa; nombres con timestamp).
  - Verificación: estructura creada; documento de entorno (SO, versiones) generado.
  - _Requisitos: R19.4_ · _Diseño: §9_ · _AC: AC-16_

- [x] 3. (auto) Añadir `cryptography` (runtime) y `locust` (solo dev) con versiones fijadas
  - Añadir `cryptography` a `requirements.txt`; `locust` a `requirements-dev.txt`. No introducir
    otras dependencias de runtime.
  - Verificación: instalación en entorno limpio; `requirements*.txt` con versiones pinneadas; la
    app arranca igual que antes.
  - _Requisitos: R18.1, R18.2_ · _Diseño: §Módulos afectados_ · _AC: AC-02, AC-10_

- [x] 4. (auto) (verificación) Preflight de baseline heredado y preparación de cobertura
  - Verificación automática del baseline heredado (Hito 0 YA aprobado; **no** requiere nueva
    aprobación del investigador): confirmar que la regresión heredada está verde (reusa T1),
    preparar la **cobertura** para escaneos posteriores — backend **XML** (cobertura de Pytest) y
    frontend **LCOV** — y registrar la configuración exacta del escáner que usará el PRE-scan de
    la Etapa 3 (clave de proyecto, fuentes, rutas de cobertura). NO ejecuta SonarQube aquí: el
    PRE-scan de la Etapa 3 ocurre en M5 (T32), tras implementar y probar las capacidades.
  - Verificación: baseline heredado verde confirmado; generadores de cobertura (XML/LCOV)
    disponibles; archivo de configuración del escáner presente. Evidencia faltante NO es PASS.
  - _Requisitos: R19.1, R19.3_ · _Diseño: §9, §8 G0_ · _AC: AC-14, AC-15_

## M1 — Cifrado, claves y migración (gates G1–G3)

> Depende de: M0. Implementa D-E3-01 (R1–R4). Claves → `crypto` → cifrado en repo → migración.

- [x] 5. (auto) Configuración externa de claves con validación fail-closed (`config.py`, `main.py`)
  - Leer `SHIFT_ENC_KEYS`, `SHIFT_ENC_ACTIVE_KID`, `SHIFT_AUDIT_HMAC_KEY`, `SHIFT_ADMIN_TOKEN`
    de entorno; sin valores por defecto inseguros. Validar en `lifespan` (startup): si falta/ es
    inválida una clave requerida, **abortar el arranque**.
  - Verificación: arranque OK con claves válidas; arranque **falla** sin ellas (negativo). El
    material de clave nunca se registra en logs/errores.
  - _Requisitos: R2.1, R2.2, R2.6, R15.3_ · _Diseño: §1.4_ · _AC: AC-02, AC-03_

- [x] 6. (auto) Implementar `app/crypto.py` (AEAD AES-256-GCM, formato versionado)
  - `load_keys`, `encrypt`, `decrypt`, `is_encrypted`; formato `enc:v1:<kid>:<nonce>:<ct||tag>`
    con `kid` como AAD; nonce de 96 bits por operación; errores `CryptoConfigError`/
    `DecryptionError`.
  - Verificación (`test_crypto.py`): round-trip; nonce único; tag manipulado → `DecryptionError`;
    kid desconocido → error; clave ausente/ inválida → `CryptoConfigError`; **sin** fallback a
    texto plano.
  - _Requisitos: R1.4, R2.3, R2.4, R2.5, R18.2_ · _Diseño: §1.1–§1.3_ · _AC: AC-02, AC-03_

- [x] 7. (auto) Cifrado en reposo en el repositorio (bordes de E/S)
  - Cifrar al escribir y descifrar al leer: `ach_repository.create_beneficiary` (cuenta/routing),
    `list_beneficiaries`/`get_beneficiary`, `create_ach_no_commit`/`get_ach_by_reference`
    (`beneficiary_snapshot`), `repository.create_schedule` (`beneficiary_snapshot`), lectura de
    snapshot en `routers/transfers.py` y en la ejecución recurrente ACH.
  - Comportamiento: la API sigue devolviendo cuenta **enmascarada** y routing como hoy; la capa
    de servicio recibe claro; en SQLite solo hay tokens `enc:`.
  - Verificación (`test_encryption_at_rest.py`): tras crear beneficiario/ACH/schedule, las
    columnas en la DB empiezan por `enc:`; respuestas de API sin cambios de forma; regresión
    heredada verde sobre datos cifrados.
  - _Requisitos: R1.1, R1.2, R1.3, R1.5, R1.6, R14_ · _Diseño: §1.5_ · _AC: AC-01, AC-02, AC-04_

- [x] 8. (auto) Migración de cifrado idempotente y transaccional (`db.migrate_encryption`)
  - Cifrar en su lugar los registros sensibles existentes (`beneficiary`, `transfer`/
    `recurring_schedule` snapshots); idempotente (omite ya cifrados vía `is_encrypted`);
    transaccional con **ROLLBACK total** ante fallo/corrupción; invocada tras `db.migrate` en el
    arranque.
  - Verificación (`test_encryption_migration.py`): 2ª corrida no recifra; **rollback** ante valor
    corrupto (negativo); al terminar no queda claro; datos heredados intactos.
  - _Requisitos: R3.1, R3.2, R3.3, R3.4_ · _Diseño: §1.6, §8 G3_ · _AC: AC-04_

## M2 — Auditoría transaccional, integridad y concurrencia (gates G4–G6)

> Depende de: M1 (clave externa + límite transaccional + datos cifrados). Implementa D-E3-02.

- [x] 9. (auto) Esquema de auditoría y protección append-only (`db.migrate`)
  - DDL idempotente de `audit_log` (`seq` AUTOINCREMENT, `event_type`, `outcome`, `entity_ref`,
    `occurred_at`, `payload`, `prev_hmac`, `entry_hmac`), `audit_anchor` (fila única), y
    **triggers** que abortan UPDATE/DELETE sobre `audit_log`; fijar `PRAGMA journal_mode=WAL`.
  - Verificación: tablas/triggers presentes; UPDATE/DELETE sobre `audit_log` abortan; WAL activo.
  - _Requisitos: R6.1, R6.2_ · _Diseño: §2.1, §2.4, §5.1_ · _AC: AC-06_

- [x] 10. (auto) Implementar `app/audit.py` (serialización canónica + cadena HMAC + ancla)
  - `_canonical` (JSON `sort_keys`, separadores fijos, UTF-8); `append_in_tx(conn, event)` que
    lee la cola, calcula `entry_hmac = HMAC-SHA256(key, prev_hmac || canonical)` y **no** hace
    commit (usa la transacción del llamador); actualizar `audit_anchor` en la misma transacción;
    `verify_chain(conn)` con `hmac.compare_digest`.
  - Verificación (`test_audit_chain.py`): cadena válida; `verify_chain` íntegra; serialización
    estable/determinista; ancla coherente con la cola.
  - _Requisitos: R5.4, R6.3, R6.4_ · _Diseño: §2.2, §2.3, §2.9_ · _AC: AC-05_

- [x] 11. (auto) (verificación) Detección de manipulación y endurecimiento (`test_audit_tamper.py`)
  - Negativos: alterar `payload`/ orden/ eliminar una entrada intermedia → `verify_chain` falla
    en el `seq` correcto; UPDATE/DELETE abortados por trigger; truncación de cola detectada por
    el ancla (dentro del modelo de amenazas).
  - Verificación: todos los negativos detectados; documentar el límite de truncación sin ancla.
  - _Requisitos: R6.4, R6.5, R6.6_ · _Diseño: §2.5, §2.9, §10_ · _AC: AC-06_

- [x] 12. (auto) Integración transaccional de auditoría en operaciones financieras
  - Emitir eventos dentro del **mismo** `financial_transaction`: `service.create_transfer`/
    `confirm_mfa`, `ach_service` (crear/autorizar/settlement/fallo+reembolso),
    `recurring_service` (ejecución/fallo de ocurrencia). Catálogo de eventos de §5.2.
  - Verificación: cada cambio financiero exitoso produce exactamente una entrada encadenada;
    historial/estados heredados sin cambios.
  - _Requisitos: R5.1, R7.1, R7.5_ · _Diseño: §2.3, §2.7, §5.2_ · _AC: AC-05, AC-07_

- [x] 13. (auto) Auditoría de eventos de configuración sensible
  - Auditar alta/baja de beneficiario, `limit_service.update`, y ciclo de vida de schedule
    (pausar/reanudar/cancelar) en la misma transacción que su cambio.
  - Verificación: cada acción genera su entrada; lecturas no generan auditoría.
  - _Requisitos: R5.2, R5.5_ · _Diseño: §2.7, §5.2_ · _AC: AC-05_

- [x] 14. (auto) (verificación) Atomicidad, rechazos y fail-closed (`test_audit_atomicity.py`)
  - Positivo: éxito financiero confirma dinero+auditoría juntos. Negativos: fallo simulado de
    persistencia de auditoría → ROLLBACK (sin saldos/transferencias/beneficiarios parciales);
    **PIN inválido** → sin débito pero intento auditado; rechazos (fondos/límite) auditados sin
    mutación financiera.
  - Verificación: todos los casos cumplen; invariantes financieros preservados.
  - _Requisitos: R5.3, R7.2, R7.3, R7.4_ · _Diseño: §2.7_ · _AC: AC-07, AC-08_

- [x] 15. (auto) Verificación de auditoría protegida (`routers/audit.py`)
  - Endpoint/operación administrativa de `verify_chain` protegida por `SHIFT_ADMIN_TOKEN` (no
    anónima pública). Negativo: sin token → no autorizado.
  - Verificación (`test_audit_access.py`): con token → verifica; sin token → rechazado; no expone
    datos sensibles.
  - _Requisitos: R8.1, R8.2_ · _Diseño: §2.5, §2.6_ · _AC: AC-05_

- [x] 16. (auto) (verificación) Concurrencia real SQLite lector/escritor y multiproceso
  - `test_concurrency_sqlite.py`: dos conexiones (escritor que transfiere, lector de saldos/
    historial) en WAL sin bloquear lecturas innecesariamente; cadena verificable; complementario
    con **dos procesos** independientes sobre el mismo archivo.
  - Verificación: sin corrupción; `seq` sin huecos; cadena íntegra; lecturas no bloqueadas.
  - _Requisitos: R8.3, R8.4, R17.1, R17.2_ · _Diseño: §2.8, §6_ · _AC: AC-09_

- [x] 17. (auto) (verificación) Regresión heredada sobre cifrado+auditoría
  - Ejecutar toda la suite E1/E2 heredada con cifrado y auditoría activos; confirmar cero
    regresiones de forma/estado/invariantes.
  - Verificación: 100% PASS; contratos de API intactos.
  - _Requisitos: R14.1, R14.2, R14.3, R14.4_ · _Diseño: §12_ · _AC: AC-01_

## M3 — Carga Locust, benchmark e invariantes (gate G7)

> Depende de: M2 (correctitud estable antes de medir). Implementa D-E3-03 (R9, R10). NO optimizar
> la aplicación antes de capturar el primer baseline válido.

- [x] 18. (auto) Aislamiento de DB sintética para carga (`loadtest/isolation.py`)
  - Configurar `DB_PATH` hacia una DB SQLite **sintética aislada** y fijar claves de prueba por
    entorno **antes de importar la app**; siembra determinista con **semillas fijas** y saldos
    amplios para 60 s de transferencias pequeñas.
  - Verificación: la app de carga nunca toca datos históricos; reproducible entre corridas.
  - _Requisitos: R10.1, R10.2_ · _Diseño: §3.1_ · _AC: AC-10_

- [x] 19. (auto) Locustfile con la mezcla y controles preservados (`loadtest/locustfile.py`)
  - Tareas con pesos **60% GET saldos / 30% GET historial / 10% POST transferencia interna**
    pequeña y válida; sin eludir MFA/saldo/límites; montos bajo umbral.
  - Verificación: las transferencias pasan los controles heredados; no se disparan MFA ni
    rechazos de límite por diseño.
  - _Requisitos: R9.2, R10.3_ · _Diseño: §3.2_ · _AC: AC-10_

- [x] 20. (auto) Runner de carga con configuración exacta (`loadtest/run_loadtest.py`)
  - Ejecutar Locust headless: **30 usuarios**, **ramp-up 5/s**, **60 s de steady-state tras el
    ramp-up**; separar la ventana steady en el reporte.
  - Verificación: parámetros exactos aplicados; corrida completa sin caídas del arnés.
  - _Requisitos: R9.1_ · _Diseño: §3.2_ · _AC: AC-10_

- [x] 21. (auto) Reporte de métricas con distribución real medida
  - Reportar p50/p95/p99 por tipo, throughput, conteos, **rechazos de negocio esperados** vs
    **errores inesperados**, entorno y parámetros; medir la **distribución real de peticiones**
    HTTP observada (no solo los pesos de Locust). Salida JSON legible por máquina.
  - Verificación: el JSON contiene todas las métricas; distribución real incluida.
  - _Requisitos: R9.3, R9.4_ · _Diseño: §3.3_ · _AC: AC-11_

- [x] 22. (auto) (verificación) Verificación de invariantes post-carga (`loadtest/verify_invariants.py`)
  - Tras la corrida: conservación del dinero, ausencia de estados parciales, `verify_chain`
    íntegra (incluida el ancla). Cualquier violación → corrida **fallida** independientemente del
    rendimiento.
  - Verificación: invariantes OK y cadena íntegra; en caso contrario, FALLA explícita.
  - _Requisitos: R10.4, R10.5_ · _Diseño: §3.4_ · _AC: AC-09_

- [x] 23. (auto) (verificación) Evaluar SLOs y preservar el primer baseline de carga
  - Comprobar umbrales **estrictos**: p95 lectura < 200 ms, p95 transferencia < 500 ms, errores
    inesperados < 1%. Preservar los artefactos crudos (CSV de Locust + JSON del runner) con
    timestamp, **sin sobrescribir**.
  - Verificación: veredicto PASS/FAIL por umbral registrado; artefactos preservados. Un servicio
    caído o sin métricas NO es PASS.
  - _Requisitos: R9.5, R9.6, R16.1_ · _Diseño: §3.3, §8 G7_ · _AC: AC-11, AC-16_

- [x] 24. (GATE INVESTIGADOR) Revisión del primer baseline de carga (antes de optimizar)
  - El investigador revisa el baseline (métricas + invariantes + distribución real). Marca
    **G-LOAD**. Prohibido optimizar la aplicación antes de esta revisión (R9.7).
  - Gate: no iniciar optimizaciones de rendimiento hasta aprobación.
  - _Requisitos: R9.7_ · _Diseño: §3.3, §8 G7_ · _AC: AC-11_

## M4 — Docker Compose, HTTPS, persistencia y smoke (gate G8)

> Depende de: M2 (app cifrada+auditada funcional). Puede ir en paralelo a M3. Implementa D-E3-04
> (R4, R11–R13). Solo verificación local; sin hosting externo/K8s/CI-CD.

- [x] 25. (auto) Dockerfile del backend (no root) y config de arranque
  - Imagen Python slim; instalar `requirements.txt` (incluye `cryptography`); usuario **no root**;
    `DB_PATH` apuntando al punto de montaje del volumen; healthcheck de salud.
  - Verificación: build OK; el contenedor arranca como no root; healthcheck disponible.
  - _Requisitos: R11.4, R12.4_ · _Diseño: §4.1_ · _AC: AC-12, AC-13_

- [x] 26. (auto) Build del frontend y servicio Nginx (TLS + proxy + redirect)
  - Build multistage de Vite → assets estáticos servidos por **Nginx**; Nginx termina **HTTPS**
    (certs montados), redirige HTTP→HTTPS y hace **reverse-proxy** de `/api` al backend por la
    red interna; el frontend usa origen **relativo** para la API (sin cambiar su lógica).
  - Verificación: assets servidos por HTTPS; `/api` proxied; HTTP redirige a HTTPS.
  - _Requisitos: R4.1, R4.2, R4.3, R4.4, R11.1, R11.2_ · _Diseño: §1.7, §4.1, §4.2_ · _AC: AC-12_

- [x] 27. (auto) `docker-compose.yml` con red interna, volumen, secretos y un solo scheduler
  - Dos servicios (backend, nginx) en **red interna** aislada; backend sin puerto al host; nginx
    expone 443/80. `.env` **no versionado** inyectado; `.env.example` versionado sin secretos.
    **Una sola réplica** del backend (exactamente un scheduler). Volumen Docker persistente para
    `DB_PATH`. `.dockerignore`/`.gitignore` excluyen `*.db`, `.env`, certs.
  - Verificación: `docker compose config` válido; sin secretos/DB horneados; una réplica backend.
  - _Requisitos: R11.3, R11.5, R12.1, R12.3, R12.5, R17.3_ · _Diseño: §4.1, §4.3_ · _AC: AC-12, AC-13_

- [x] 28. (auto) (verificación) Smoke de despliegue: build/up/health/HTTPS/redirect/proxy
  - `docker compose config`, build y `up` con **healthchecks saludables**; smoke de HTTPS,
    redirección HTTP→HTTPS, proxy de rutas de API y una llamada representativa sobre TLS. Usar
    **volúmenes desechables aislados**.
  - Verificación: todos los checks PASS; un servicio no disponible NO cuenta como PASS.
  - _Requisitos: R13.1, R13.2_ · _Diseño: §4.4_ · _AC: AC-12_

- [x] 29. (auto) (verificación) Funcionalidad, fail-closed y persistencia tras reinicio
  - Sobre el stack desplegado: operación bancaria + MFA + creación de beneficiario (comprobando
    token `enc:` en la DB del volumen) + `verify_chain` de auditoría. Negativo: quitar una clave
    → arranque **fail-closed**. Reiniciar el stack → datos cifrados y cadena **sobreviven**.
  - Verificación: banca/MFA/cifrado/auditoría OK; fail-closed demostrado; persistencia tras
    reinicio confirmada; volúmenes desechables.
  - _Requisitos: R12.2, R13.3, R13.4, R13.5, R13.6_ · _Diseño: §4.3, §4.4_ · _AC: AC-12, AC-13_

## M5 — Regresión final y evidencia experimental (gates G9, G-SONAR-FINAL)

> Depende de: M3 y M4. Cierra la etapa con regresión completa, corrección SonarQube (tras gate)
> y evidencia final. Implementa R14, R19.

- [x] 30. (auto) Configurar un Vitest mínimo solo-dev si el frontend carece de pruebas
  - El frontend heredado solo tiene `build` (`tsc && vite build`), sin runner de pruebas. Añadir
    un **Vitest mínimo** como dependencia **solo de dev** con una o dos pruebas de humo (p. ej.
    render del cliente de API/tipos), sin dependencias de runtime nuevas y sin alterar la app.
  - Verificación: `vitest run` PASS y `npm run build` sigue verde. Si el equipo decide no
    añadir Vitest, documentar la ausencia explícitamente (no fabricar resultados).
  - _Requisitos: R19.2_ · _Diseño: §7_ · _AC: AC-14_

- [x] 31. (auto) (verificación) Regresión completa Pytest + build (+ Vitest) con evidencia
  - Ejecutar toda la suite backend (Pytest), el build de frontend y Vitest (si está), preservando
    **stdout** y los **fallos intermedios**; registrar comandos y versiones exactas.
  - Verificación: backend 100% PASS, build exit 0, Vitest PASS (o ausencia documentada). Evidencia
    cruda preservada.
  - _Requisitos: R19.1, R19.2, R14_ · _Diseño: §7, §8 G9_ · _AC: AC-01, AC-14_

- [x] 32. (auto) Escaneo SonarQube PRE-remediación de la Etapa 3 (después de implementar/probar; antes de corregir)
  - Ejecutar el escaneo SonarQube PRE-remediación **tras** implementar y probar todas las
    capacidades de la Etapa 3 (M1–M4) y **tras** la regresión/cobertura completa (T31), y
    **antes** de cualquier corrección dirigida por Sonar (protocolo experimental común). Importar
    cobertura backend **XML** y frontend **LCOV**; usar la configuración exacta del escáner
    registrada en T4 (misma clave de proyecto/alcance que el escaneo final de T35).
  - Preservar como evidencia cruda, sin sobrescribir: resultados PRE, identificadores de
    análisis, lista de issues, Quality Gate y la configuración exacta del escáner, además de los
    informes de cobertura XML/LCOV usados.
  - Verificación: PRE-scan completado con cobertura importada; artefactos crudos preservados en
    `_experiment_logs/Kiro/sonarqube/`. Un escáner no disponible o evidencia faltante NO es PASS.
  - _Requisitos: R19.3, R19.4_ · _Diseño: §9, §8 G9_ · _AC: AC-15, AC-16_

- [x] 33. (GATE INVESTIGADOR) Revisión del PRE-scan de la Etapa 3 antes de la fase correctiva
  - El investigador revisa el escaneo PRE-remediación de la Etapa 3 (T32) con cobertura importada
    (XML/LCOV), issues y Quality Gate, y autoriza la fase correctiva. Marca **G-SONAR-PRE**. Sin
    esta aprobación NO se inician correcciones dirigidas por Sonar.
  - Gate: detiene la ejecución automática hasta aprobación.
  - _Requisitos: R19.3_ · _Diseño: §9_ · _AC: AC-15_

- [x] 34. (auto) Correcciones dirigidas por SonarQube (sin cambiar comportamiento aprobado)
  - Aplicar correcciones de calidad/seguridad señaladas por el baseline, preservando contratos,
    invariantes y funcionalidad; re-ejecutar la regresión tras cada corrección.
  - Verificación: regresión sigue verde; sin cambios de comportamiento observable.
  - _Requisitos: R14, R18_ · _Diseño: §8 G9_ · _AC: AC-01, AC-15_

- [x] 35. (GATE INVESTIGADOR) (verificación) Escaneo final de SonarQube (mismo alcance/cobertura)
  - El investigador ejecuta el escaneo **final** con **idéntico alcance** y **cobertura
    importada**, comparable 1:1 con el baseline; se preservan JSON/CLI crudos. Marca
    **G-SONAR-FINAL**.
  - Gate: cierre de calidad requiere esta aprobación; evidencia no disponible NO es PASS.
  - _Requisitos: R19.3, R19.4_ · _Diseño: §9_ · _AC: AC-15, AC-16_

- [x] 36. (auto) Consolidar la evidencia experimental final
  - Consolidar en `_experiment_logs/Kiro/` resultados reales (regresión, carga, despliegue,
    SonarQube PRE/final), comandos exactos, versiones de entorno y veredictos por AC
    (AC-01..AC-16), sin fabricar ni sobrescribir. Verificar además que las métricas documentadas
    coinciden 1:1 con los artefactos crudos (JSON/CSV de Locust, salidas de smoke de despliegue,
    JSON/CLI de SonarQube PRE y final).
  - Verificación: índice de evidencia completo y trazable AC↔artefacto; coincidencia 1:1
    documentación↔evidencia cruda; datos históricos de la Etapa 2 y `SEED-3.md` intactos.
  - _Requisitos: R19.4_ · _Diseño: §9_ · _AC: AC-14, AC-15, AC-16_

---

## Notes

## Notas

### Cobertura requisito → tarea

| Req. | Tareas | Req. | Tareas |
|------|--------|------|--------|
| R1 | 6, 7, 8 | R11 | 25, 26, 27 |
| R2 | 5, 6 | R12 | 25, 27, 29 |
| R3 | 8 | R13 | 28, 29 |
| R4 | 26 | R14 | 1, 7, 17, 31, 34 |
| R5 | 10, 12, 13, 14 | R15 | 5, 6 |
| R6 | 9, 10, 11 | R16 | 23 |
| R7 | 12, 14 | R17 | 16, 27 |
| R8 | 10, 15, 16 | R18 | 3, 6, 30 |
| R9 | 19, 20, 21, 23, 24 | R19 | 1, 2, 4, 31, 32, 33, 35, 36 |
| R10 | 18, 19, 22 | — | — |

### Cobertura AC → tarea

| AC | Tareas | AC | Tareas |
|----|--------|----|--------|
| AC-01 | 1, 7, 17, 31, 34 | AC-09 | 16, 22 |
| AC-02 | 3, 5, 6, 7 | AC-10 | 18, 19, 20 |
| AC-03 | 5, 6 | AC-11 | 21, 23, 24 |
| AC-04 | 7, 8 | AC-12 | 26, 27, 28, 29 |
| AC-05 | 10, 12, 13, 15 | AC-13 | 25, 27, 29 |
| AC-06 | 9, 11 | AC-14 | 30, 31, 36 |
| AC-07 | 12, 14 | AC-15 | 4, 32, 33, 34, 35 |
| AC-08 | 14 | AC-16 | 2, 23, 32, 35, 36 |

Todos los R1..R19 y AC-01..AC-16 tienen al menos una tarea asociada.

### Gates y automatización

- Tareas `(auto)` ejecutables con "Run all Tasks": 1–23, 25–32, 34, 36 (incluye T4, ahora
  preflight automático, y T32, el PRE-scan de la Etapa 3).
- Gates de investigador que DETIENEN la ejecución automática: **24** (revisión del primer
  baseline de carga), **33** (autorizar la fase correctiva tras revisar el PRE-scan de la Etapa
  3), **35** (escaneo final). "Run all Tasks" debe pausar en cada gate y esperar aprobación.
- Regla transversal: un servicio no disponible o evidencia faltante **nunca** es PASS; la tarea
  de verificación falla y detiene el avance.

### Preservación y seguridad

- No se altera ningún dato histórico de la Etapa 2 ni `SEED-3.md`.
- DB y volúmenes **desechables y aislados** en todas las pruebas/corridas/despliegues de prueba.
- Sin dependencias de runtime innecesarias (`cryptography` runtime; `locust`/Vitest solo dev).

