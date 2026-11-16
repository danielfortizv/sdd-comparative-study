# Informe de Cierre Experimental — Shift Bank, Etapa 2, Spec Kit

**Corte de observación:** 15 de noviembre de 2026.  
**Caso de estudio:** Aplicación bancaria *Shift Bank*.  
**Etapa:** 2 — Complejidad funcional y estado.  
**Variante:** GitHub Spec Kit v1.0.6 sobre Gemini CLI v0.65.0 (Modelo base: `gemini-3.8-flash`).  
**Condición experimental:** Extensión *brownfield* de la Etapa 1.  
**Opción seleccionada:** Opción A (Transferencias ACH interbancarias simuladas a terceros, pagos recurrentes programados y límites dinámicos).  
**Documento ID:** `01_INFORME_CIERRE_E2_SPECKIT.md`  
**Destino de Evidencia:** `Shift-Bank/Etapa 2/_experiment_logs/Spec Kit/01_INFORME_CIERRE_E2_SPECKIT.md`  
**Estado Final del Experimento:** **FINALIZADO Y CERRADO (Veredicto: `GO`)**  

---

## 1. Resumen Ejecutivo

El experimento de la Etapa 2 para Shift Bank bajo la metodología **GitHub Spec Kit** extendió exitosamente la base de código *brownfield* heredada de la Etapa 1 (preservada con 59 archivos durables y hashes SHA-256 intactos). La nueva funcionalidad incorporó tres capacidades avanzadas del dominio bancario:
1. **Límites Dinámicos de Transferencia:** Configuración en tiempo de ejecución de topes por operación (por defecto COP 5.000.000,00) y acumulados diarios UTC (COP 10.000.000,00), con cálculo en tiempo real de consumo y disponibilidad remanente (`max(0, daily_limit - consumption)`).
2. **Transferencias ACH Interbancarias y Gestión de Beneficiarios:** Soporte para beneficiarios guardados (CRUD con inmutabilidad de datos bancarios) y transferencias ad-hoc; validación en tiempo real de número de ruta (exactamente 9 dígitos) y cuenta (4 a 17 dígitos); débito inmediato en cuenta de origen y ciclo de liquidación autónomo (`PENDING` -> `SETTLED`).
3. **Pagos Recurrentes Programados:** Ciclo de vida completo (`PENDING_MFA`, `ACTIVE`, `PAUSED`, `CANCELLED`, `EXPIRED`) con frecuencias diaria (+24h), semanal (+7d) y mensual (estrictamente +30 días), validación de fechas de inicio estrictamente futuras a las 00:00:00 UTC, y ejecución automática mediante *scheduler* asíncrono en segundo plano acoplado al ciclo de vida de FastAPI.

### Resultados Globales de Verificación:
- **Pruebas Automatizadas:** **47/47 pruebas backend (`pytest`)**, **12/12 pruebas frontend (`vitest`)** y **compilación de producción limpia (`vite build`, 0 errores)**.
- **Validación Manual de Aceptación:** El **15 de noviembre de 2026**, el investigador realizó una revisión interactiva directa de la aplicación en el navegador (`http://localhost:5173`) sobre la base de datos aislada (`backend/manual_test_shift_bank.db`), reportando que **toda la funcionalidad evaluada opera correctamente**. Conforme a los estándares de integridad metodológica, no se fabricaron capturas de pantalla individuales ni registros pormenorizados paso a paso que no fueron recolectados de manera separada.
- **Evolución del Código:** 74 archivos durables finales (49 intactos de E1, 10 modificados, 15 nuevos, 0 eliminados). Cómputo Diff LOC: **+7.298 líneas añadidas**, **-273 líneas eliminadas** (cambio neto de **+7.025 LOC**).
- **Análisis Estático SonarQube:** 4.099 NCLOC (5.039 líneas totales), 0 vulnerabilidades (Rating A), 3 defectos/bugs (Rating C) y 72 *code smells* (Rating A de mantenibilidad), con 476 minutos de deuda técnica estimada.

---

## 2. Dimensión 1 — Esfuerzo, Telemetría y Consumo de Tokens

### 2.1. Corrección y Reconciliación de Telemetría a Nivel de Sesión (Registros JSONL Originales)
Las mediciones de esfuerzo provienen de los registros JSONL persistentes del cliente Gemini CLI ubicados en `.gemini/tmp/spec-kit-1/chats/`:
- **Sesión 01:** `session-2026-11-14T17-18-f52d4c11.jsonl` (ID: `f52d4c11-3f33-4667-8b68-f76b443d510d`).
  - *Ventana temporal:* 2026-11-14T17:18:20.286Z a 2026-11-14T18:22:56.126Z.
  - *Duración de pared:* **1 h 04 min 36 s (3.876 s)**.
  - *Alcance:* Descubrimiento brownfield, especificación formal (`spec.md`), aclaraciones con el usuario, contratos API y desglose de tareas (`tasks.md`).
- **Sesión 02:** `session-2026-11-14T18-24-fe272589.jsonl` (ID: `fe272589-bd7f-4c7d-8205-4f821865bbc9`).
  - *Ventana temporal:* 2026-11-14T18:24:30.998Z a 2026-11-14T22:15:29.467Z (último registro en archivo: 23:52:56Z).
  - *Duración de pared:* **3 h 50 min 58 s (13.858 s)**.
  - *Alcance:* Remediaciones arquitectónicas preliminares (F-01..F-10), implementación de User Stories 1 a 3 (T001–T052), pruebas automatizadas y pulido de UI.

### 2.2. Totales Consolidados Verificados (Nivel Cable API HTTP - JSONL Deduplicado)
Se preservan íntegramente los totales consolidados auditados en la capa API:

| Métrica Estandarizada | Sesión 01 (Specs/Plan) | Sesión 02 (Impl/Tests) | Total Consolidado E2 Preservado |
|---|---:|---:|---:|
| **Tokens de Entrada Totales (`Tok In`)** | 26.444.222 | 97.506.747 | **123.950.969** |
| **Tokens en Caché (`Tok Cache`)** | 24.492.157 | 84.375.934 | **108.868.091** (87,83 % acierto) |
| **Tokens de Entrada sin Caché (Derivado)** | 1.952.065 | 13.130.813 | **15.082.878** |
| **Tokens de Salida (`Tok Out`)** | 128.450 | 206.980 | **335.430** |
| **Solicitudes al Modelo (`Requests`)** | 198 | 323 | **521 solicitudes API** |
| **Llamadas a Herramientas Únicas (`Tool Calls`)** | 184 | 301 | **485 herramientas únicas** |
| **Interacciones de Usuario (Prompts)** | 15 mensajes | 10 mensajes | **25 interacciones humanas** |
| **Tiempo de Pared (`Wall Clock`)** | 1 h 04 min 36 s | 3 h 50 min 58 s | **4 h 55 min 34 s (17.734 s)** |
| **Costo Financiero ($ USD)** | N/D | N/D | **N/D (Sin tarifa de facturación observada)** |

### 2.3. Explicación de la Discrepancia con la Captura de Pantalla `/stats`
- La captura de pantalla `/stats` corresponde a la **Sesión 02 (`fe272589-bd7f-4c7d-8205-4f821865bbc9`)** al finalizar la fase interactiva de implementación.
- Muestra los contadores acumuladores en memoria del cliente interactivo Gemini CLI:
  - **Llamadas a herramientas:** 486 (480 exitosas, 6 fallidas / 98,8 % éxito).
  - **Duración total de sesión:** 5 h 34 min 36 s (20.076 s).
  - **Tiempo activo del agente:** 4 h 22 min 55 s (15.775 s).
  - **Tiempo API:** 1 h 30 min 24 s (5.424 s).
  - **Tiempo de ejecución de herramientas:** 2 h 52 min 31 s (10.351 s).
  - **Tiempo de espera / inactividad del usuario:** 1 h 11 min 41 s (4.301 s).
- **Causa de la discrepancia:** Las 486 llamadas de `/stats` reflejan el acumulador de la sesión interactiva del cliente CLI (incluyendo reintentos de streaming y sondeos de procesos), mientras que las 485 llamadas únicas de JSONL corresponden a las transacciones HTTP deduplicadas a nivel de cable a lo largo de las dos sesiones de desarrollo.
- **Regla metodológica anti-doble conteo:** Ambas métricas provienen de capas de instrumentación distintas (cable API vs. cliente CLI) y no deben sumarse aritméticamente.

---

## 3. Dimensión 2 — Calidad del Código y Análisis SonarQube

Las mediciones oficiales de SonarQube Community Build 26.9.0 se preservan íntegramente, manteniendo los **3 defectos (bugs)** detectados sin alterar la implementación:

| Métrica SonarQube | Etapa 1 (Línea Base Retrospectiva) | Etapa 2 (Final Restaurado) | Delta Absoluto | Variación (%) |
|---|---|---|---|---|
| **Líneas de Código (NCLOC)** | 1.215 | **4.099** | +2.884 | +237,4 % |
| **Líneas Totales (`lines`)** | 1.495 | **5.039** | +3.544 | +237,1 % |
| **Bugs Tradicionales** | 1 (`typescript:S1082`) | **3** (2 `python:S7497`, 1 `typescript:S1082`) | +2 | +200,0 % |
| **Vulnerabilidades de Seguridad** | 0 | **0** | 0 | 0,0 % |
| **Security Rating** | 1.0 (A) | **1.0 (A)** | 0 | 0,0 % |
| **Code Smells** | 25 | **72** | +47 | +188,0 % |
| **Maintainability Rating** | 1.0 (A) | **1.0 (A)** | 0 | 0,0 % |
| **Deuda Técnica (min)** | 114 | **476** (7 h 56 min) | +362 | +317,5 % |
| **Complejidad Cognitiva** | 108 | **460** | +352 | +325,9 % |
| **Complejidad Ciclomática** | 142 | **551** | +409 | +288,0 % |
| **Densidad de Duplicación (%)** | 0,0 % | **0,0 %** | 0,0 % | 0,0 % |
| **Cobertura Importada (%)** | 0,0 % | **0,0 %** | 0,0 % | 0,0 % |
| **Issues Fiabilidad MQR** | 6 | **18** | +12 | +200,0 % |
| **Rating Fiabilidad MQR** | 3.0 (C) | **4.0 (D)** | +1 | +33,3 % |

### Detalle de los 3 Defectos Detectados en Etapa 2:
1. **`python:S7497` (Severidad: Major)** — `backend/src/scheduler.py` (Línea 102):  
   *Mensaje:* Ensure that the asyncio.CancelledError exception is re-raised after your cleanup code.
2. **`python:S7497` (Severidad: Major)** — `backend/src/scheduler.py` (Línea 117):  
   *Mensaje:* Ensure that the asyncio.CancelledError exception is re-raised after your cleanup code.
3. **`typescript:S1082` (Severidad: Minor)** — `frontend/src/App.tsx` (Línea 815):  
   *Mensaje:* Visible, non-interactive elements with click handlers must have at least one keyboard listener.

---

## 4. Dimensión 3 — Evolución de Archivos y Diff LOC

- **Archivos durables finales:** **74** (49 intactos de E1, 10 modificados, 15 nuevos, 0 eliminados).
- **Líneas añadidas (+):** **7.298**
- **Líneas eliminadas (-):** **273**
- **Cambio neto:** **+7.025 LOC**

### Desglose por grupo funcional:
| Grupo Funcional | Archivos Modificados / Nuevos | Líneas Añadidas (+) | Líneas Eliminadas (-) | Cambio Neto |
|---|---|---:|---:|---:|
| **Especificación Stage 2** | 8 nuevos | +1.640 | -0 | +1.640 |
| **Código Backend Producción** | 4 modif., 2 nuevos | +1.935 | -177 | +1.758 |
| **Pruebas Backend** | 5 nuevos | +1.421 | -0 | +1.421 |
| **Código Frontend Producción** | 4 modif. | +1.875 | -91 | +1.784 |
| **Pruebas Frontend** | 1 modif. | +426 | -4 | +422 |
| **Configuración / Metadata** | 1 modif. (`feature.json`) | +1 | -1 | 0 |
| **TOTALES CONSOLIDADOS** | **25 archivos con diff** | **+7.298** | **-273** | **+7.025** |

---

## 5. Dimensión 4 — Verificación y Aceptación Funcional (A01 – A21)

La matriz de aceptación funcional de 21 escenarios cuenta con doble validación:
1. **Cobertura Automatizada (100 %):** 47 pruebas en `backend/tests/` (`test_api.py`, `test_limits.py`, `test_ach.py`, `test_recurring.py`, `test_stage2_regression.py`), 12 pruebas en `frontend/src/App.test.tsx` y compilación TypeScript/Vite exitosa.
2. **Revisión Manual en Navegador (15/11/2026):** El investigador confirmó interactivamente en la interfaz web (`http://localhost:5173`) el correcto comportamiento de cuentas, límites dinámicos, validación en tiempo real de números de ruta, transferencias ACH, pagos recurrentes y flujo de autenticación multifactorial (MFA).
3. **Detalle Escenario por Escenario:** Documentado íntegramente en `E2_SPECKIT_MANUAL_VALIDATION.md`.

---

## 6. Inventario Completo de Archivos de Evidencia Generados

Todos los artefactos de evidencia se encuentran organizados y verificados bajo `Shift-Bank/Etapa 2/_experiment_logs/Spec Kit/`:

| Archivo de Evidencia | Tamaño (Bytes) | Descripción |
|---|---:|---|
| `01_INFORME_CIERRE_E2_SPECKIT.md` | ~11.000 | Informe consolidado de cierre experimental de la Etapa 2. |
| `E2_SPECKIT_MANUAL_VALIDATION.md` | ~27.500 | Reporte de validación de aceptación manual y matriz de escenarios A01–A21. |
| `E2_SPECKIT_FINAL_EVIDENCE.md` | 23.701 | Registro integral de arquitectura, decisiones D-01..D-09 y remediaciones F-01..F-10. |
| `E2_SPECKIT_DIFF_LOC.md` | 9.146 | Registro metodológico y cálculo formal de Diff LOC y evolución de archivos. |
| `E2_SPECKIT_DIFF_BASELINE_FINAL.csv` | 15.096 | Matriz comparativa archivo por archivo con hashes SHA-256 y cambios de líneas. |
| `E2_SPECKIT_DIFF_RESUMEN.csv` | 413 | Resumen cuantitativo de archivos por categoría y estado de cambio. |
| `E2_SPECKIT_ESPECIFICACIONES_FINAL.csv` | 216 | Inventario de artefactos de especificación generados por Spec Kit. |
| `E2_SPECKIT_FINAL_MANIFEST_SHA256.csv` | 7.806 | Manifiesto de integridad criptográfica SHA-256 de los 74 archivos durables. |
| `E2_SPECKIT_SONARQUBE_COMPARATIVA_E1_E2.md` | 8.448 | Análisis comparativo SonarQube entre la línea base E1 y la entrega final E2. |
| `E2_SPECKIT_SONARQUBE_FINAL.md` | 11.450 | Reporte detallado del escaneo SonarQube para la Etapa 2. |
| `E2_SPECKIT_SONARQUBE_FINAL.json` | 3.352 | Carga JSON del análisis final de componentes en SonarQube. |
| `E2_SPECKIT_SONARQUBE_MEASURES.json` | 2.392 | Métricas cuantitativas del proyecto en SonarQube. |
| `E2_SPECKIT_SONARQUBE_ISSUES.json` | 202.540 | Total de incidencias reportadas en el escaneo de la Etapa 2. |
| `E2_SPECKIT_SONARQUBE_TASK.json` | 1.091 | Registro de ejecución del Compute Engine de SonarQube (Task ID original). |
| `E2_SPECKIT_SONARQUBE_RESTORATION.json` | 4.116 | Registro de restauración de E2 como versión más reciente en SonarQube. |
| `E2_SPECKIT_SONARQUBE_RESTORATION_MEASURES.json`| 2.392 | Carga de métricas restauradas en SonarQube (100 % paridad). |
| `E2_SPECKIT_SONARQUBE_RESTORATION_ISSUES.json` | 202.540 | Incidencias restauradas en SonarQube. |
| `E2_SPECKIT_SONARQUBE_RESTORATION_TASK.json` | 1.091 | Tarea Compute Engine de restauración (`5ad31410-9b38-47e9-bcdb-6cf0d5332e09`). |
| `E2_SPECKIT_SONARQUBE_BACKUP_INITIAL_FINAL.json` | 3.352 | Copia de respaldo previa al escaneo de la línea base retrospectiva. |
| `E1_SPECKIT_SONARQUBE_BASELINE.json` | 4.079 | Dataset del análisis retrospectivo E1 sobre código fuente preservado. |
| `E1_SPECKIT_SONARQUBE_MEASURES.json` | 2.391 | Medidas de componentes de la línea base E1. |
| `E1_SPECKIT_SONARQUBE_ISSUES.json` | 204.825 | Total de incidencias del análisis retrospectivo E1. |
| `E1_SPECKIT_SONARQUBE_ISSUES_OPEN.json` | 44.929 | Incidencias abiertas de la línea base E1 (26 abiertas). |
| `E1_SPECKIT_SONARQUBE_TASK.json` | 1.091 | Registro Compute Engine de E1 (`8c8ef226-43ff-4cab-98dc-e0bbdcf9c129`). |
| `E2_SPECKIT_SONARQUBE_E1_BASELINE_AND_TELEMETRY.md` | 10.516 | Auditoría de permisos de aprovisionamiento de proyectos en SonarQube. |
| `E2_SPECKIT_PENDIENTES_MEDICION.md` | 17.606 | Registro de control de trazabilidad y pendientes metodológicos resueltos. |
| `E2_SPECKIT_REGISTRO_01_PREPARACION.md` | 9.479 | Registro de verificación previa y copia de línea base inicial. |
| `E2_SPECKIT_REGISTRO_02_DESCUBRIMIENTO.md` | 133.683 | Bitácora completa de descubrimiento y especificación de Spec Kit. |
| `E2_SPECKIT_GEMINI_HANDOFF.md` | 11.864 | Protocolo de traspaso y directivas operativas de la herramienta. |
| `PROMPT_01_READ_ONLY_DISCOVERY.md` | 3.537 | Prompt inicial de investigación de solo lectura. |

---

## 7. Limitaciones Metodológicas y Declaraciones de Integridad

1. **Aislamiento de Bases de Datos:** La base de datos original de la Etapa 1 y la base de datos preservada de la Etapa 2 (`backend/shift_bank.db`) permanecen intactas e inmutables. Las pruebas manuales se efectuaron sobre una base aislada (`backend/manual_test_shift_bank.db`).
2. **Endpoints de Simulación Restringidos:** En el entorno manual, los endpoints de falla forzada (`/api/test/*`) se mantuvieron estrictamente deshabilitados (`ENABLE_TEST_ENDPOINTS=false`, retornando 404). El comportamiento de fallos e idempotencia de reembolsos queda respaldado por las pruebas automatizadas del suite.
3. **Limitación de Monoproceso para Concurrencia Asíncrona (F-07):** El planificador de pagos en segundo plano opera mediante tareas asíncronas en memoria acopladas al ciclo de vida de FastAPI (`asyncio.create_task`). Requiere ejecutarse con `--workers 1` para prevenir contenciones de bloqueo en SQLite.
4. **No Existencia de Registro Granular por Escenario:** El reporte manual documenta la confirmación general satisfactoria informada por el investigador el 15/11/2026. No se declaran capturas de pantalla individuales ni trazas temporales detalladas por escenario que no fueron recolectadas de manera separada.
5. **Costo Financiero:** No se reporta costo financiero en dólares debido a la ausencia de tarifas de facturación comercial observadas en el entorno experimental.
6. **Medición Retrospectiva de SonarQube E1:** Debido a que el token de la Etapa 2 carecía de permisos globales para aprovisionar proyectos nuevos (`POST /api/projects/create` 403), el análisis de la línea base E1 se ejecutó retrospectivamente sobre el mismo proyecto bajo la versión `1.0-retrospective-baseline`, restaurando con posterioridad la versión final E2 (`2.0-final-restored`) con paridad exacta al 100 %.
