# Shift Bank - Spec Kit: Comparativa Cuantitativa SonarQube Etapa 1 vs. Etapa 2

**Documento ID:** E2_SPECKIT_SONARQUBE_COMPARATIVA_E1_E2.md
**Destino de Evidencia:** Shift-Bank/Etapa 2/_experiment_logs/Spec Kit/E2_SPECKIT_SONARQUBE_COMPARATIVA_E1_E2.md
**Estudio:** SDD Comparative Study - Brownfield Development (Shift Bank)
**Herramienta SDD:** GitHub Spec Kit v1.0.6 sobre Gemini CLI v0.65.0
**Fecha de Analisis:** 15 de noviembre de 2026 (UTC) / 14 de noviembre de 2026 (Local)
**Servidor SonarQube:** Community Build 26.9.0.129388 (Docker container sonarqube:latest / sdd-sonarqube:frozen)
**Escaner:** SonarScanner CLI 8.1.0.6389 (Docker image sdd-sonar-scanner:frozen)
**Clave de Proyecto Unificada:** Shift-Bank---Stage-2---Spec-Kit (Token: SONAR_TOKEN_SPECKIT2)
**Divulgacion Metodologica:** La medicion de la Etapa 1 se realizo de forma retrospectiva sobre el codigo fuente historico inmutable preservado en Shift-Bank/Etapa 1/Spec Kit (montado como volumen de solo lectura :ro), utilizando el mismo proyecto de SonarQube bajo la version 1.0-retrospective-baseline. Posteriormente, la implementacion final de la Etapa 2 (Shift-Bank/Etapa 2/Spec Kit) fue re-analizada y restaurada como la version mas reciente (2.0-final), verificando paridad al 100 % con la medicion original.

---

## 1. Identificacion de Tareas y Analisis en SonarQube

| Parametro | Etapa 1 (Linea Base Retrospectiva) | Etapa 2 (Medicion Original) | Etapa 2 (Restauracion Mas Reciente) |
|---|---|---|---|
| **Version** | 1.0-retrospective-baseline | 2.0-final | 2.0-final-restored |
| **Compute Engine Task ID** | 8c8ef226-43ff-4cab-98dc-e0bbdcf9c129 | 40bec5a0-b886-4ec6-8b79-4e7b2b29bf6a | 5ad31410-9b38-47e9-bcdb-6cf0d5332e09 |
| **Analysis ID** | 17dc6fe7-c974-480e-81a2-a6d688a0f79e | 378408ec-2411-488e-9ec5-566818186883 | 70930530-469e-4125-8001-5bded4603c0d |
| **Submitted At** | 2026-11-15T03:30:44+0000 | 2026-11-15T00:19:05+0000 | 2026-11-15T04:03:21+0000 |
| **Executed At** | 2026-11-15T03:30:47+0000 | 2026-11-15T00:19:07+0000 | 2026-11-15T04:03:24+0000 |
| **Tiempo Compute Engine** | 1355 ms | 2138 ms | 1715 ms |
| **Tiempo Escaner CLI** | 1 min 12.329 s | 1 min 11.957 s | 1 min 19.853 s |
| **Estado Compute Engine** | SUCCESS | SUCCESS | SUCCESS |
| **Archivos Indexados** | 11 archivos | 23 archivos | 23 archivos |

---

## 2. Tabla Comparativa de Metricas: Etapa 1 vs. Etapa 2 (Spec Kit)

| Metrica SonarQube | Clave | Etapa 1 (Linea Base) | Etapa 2 (Final Restaurado) | Delta Absoluto | Variacion Relativa |
|---|---|---:|---:|---:|---:|
| **Lineas de Codigo (NCLOC)** | ncloc | **1215** | **4099** | +2884 | +237.4 % |
| **Lineas Totales** | lines | **1495** | **5039** | +3544 | +237.1 % |
| **Bugs Tradicionales** | bugs | **1** | **3** | +2 | +200.0 % |
| **Vulnerabilidades** | vulnerabilities | **0** | **0** | 0 | 0.0 % |
| **Code Smells** | code_smells | **25** | **72** | +47 | +188.0 % |
| **Deuda Tecnica (min)** | sqale_index | **114** | **476** | +362 | +317.5 % |
| **Complejidad Cognitiva** | cognitive_complexity | **108** | **460** | +352 | +325.9 % |
| **Complejidad Ciclomatica** | complexity | **142** | **551** | +409 | +288.0 % |
| **Densidad de Duplicacion (%)** | duplicated_lines_density | **0.0** | **0.0** | 0 | 0.0 % |
| **Cobertura Importada (%)** | coverage | **0.0** | **0.0** | 0 | 0.0 % |
| **Rating Fiabilidad Tradicional** | reliability_rating | **2.0** | **3.0** | +1 | +50.0 % |
| **Rating Seguridad Tradicional** | security_rating | **1.0** | **1.0** | 0 | 0.0 % |
| **Rating Mantenibilidad** | sqale_rating | **1.0** | **1.0** | 0 | 0.0 % |
| **Issues Fiabilidad MQR** | software_quality_reliability_issues | **6** | **18** | +12 | +200.0 % |
| **Rating Fiabilidad MQR** | software_quality_reliability_rating | **3.0** | **4.0** | +1 | +33.3 % |
| **Issues Seguridad MQR** | software_quality_security_issues | **0** | **0** | 0 | 0.0 % |
| **Rating Seguridad MQR** | software_quality_security_rating | **1.0** | **1.0** | 0 | 0.0 % |
| **Issues Mantenibilidad MQR** | software_quality_maintainability_issues | **25** | **74** | +49 | +196.0 % |
| **Rating Mantenibilidad MQR** | software_quality_maintainability_rating | **1.0** | **1.0** | 0 | 0.0 % |
| **Esfuerzo Remediacion MQR (min)** | software_quality_maintainability_remediation_effort | **114** | **486** | +372 | +326.3 % |

---

## 3. Analisis Cualitativo de Defectos (Bugs)

### 3.1. Defecto en Linea Base Etapa 1 (1 bug)
- **`typescript:S1082` (Severidad: MINOR)** - `frontend/src/App.tsx` (Linea 338):
  Visible, non-interactive elements with click handlers must have at least one keyboard listener.
  Elemento clickeable en pestanas de interfaz de usuario de Stage 1 sin soporte para navegacion por teclado.

### 3.2. Defectos en Implementacion Final Etapa 2 (3 bugs)
1. **`python:S7497` (Severidad: MAJOR)** - `backend/src/scheduler.py` (Linea 102):
   Ensure that the asyncio.CancelledError exception is re-raised after your cleanup code.
2. **`python:S7497` (Severidad: MAJOR)** - `backend/src/scheduler.py` (Linea 117):
   Ensure that the asyncio.CancelledError exception is re-raised after your cleanup code.
3. **`typescript:S1082` (Severidad: MINOR)** - `frontend/src/App.tsx` (Linea 815):
   Visible, non-interactive elements with click handlers must have at least one keyboard listener.

---

## 4. Correccion y Reconciliacion de Telemetria (Ambitos Separados)

Se documenta formalmente la correccion metodologica sobre las mediciones de telemetria:

1. **No Equivalencia Directa:** Las **485 llamadas a herramientas deduplicadas de JSONL** cubren las **dos sesiones historicas** iniciales de desarrollo (Sesion 01: descubrimiento y especificacion; Sesion 02: implementacion y pruebas). Por el contrario, las **486 llamadas a herramientas de la captura de pantalla (/stats)** corresponden a **una instantanea de sesion posterior** (Sesion `fe272589-bd7f-4c7d-8205-4f821865bbc9).
2. **Preservacion de Ambas Mediciones con sus Respectivos Ambitos:**
   - **Ambito JSONL (Historico de 2 sesiones):** 485 herramientas unicas, 521 solicitudes al modelo, 123.950.969 tokens de entrada reales, 108.868.091 tokens cacheados (87,8 % acierto), 335.430 tokens de salida, 4 h 55 min 34 s de pared.
   - **Ambito Pantalla /stats (Instantanea de sesion posterior):** 486 llamadas a herramientas (480 exitosas, 6 fallidas), 5 h 34 min 36 s de duracion de sesion, 4 h 22 min 55 s de agente activo, 1 h 30 min 24 s de tiempo API, 2 h 52 min 31 s de tiempo de herramientas, 1 h 11 min 41 s de tiempo inactivo.
3. **Regla Metodologica Anti-Doble Conteo:** Ambas fuentes constituyen evidencias validas e independientes de fases distintas de observacion. En ningun caso deben sumarse aritmeticamente.

---

## 5. Inventario de Evidencias SonarQube Generadas

| Archivo de Evidencia | Descripcion |
|---|---|
| E1_SPECKIT_SONARQUBE_BASELINE.json | Dataset consolidado de la linea base retrospectiva E1 (tarea, medidas, Quality Gate). |
| E1_SPECKIT_SONARQUBE_MEASURES.json | Carga completa de medidas de componentes de la linea base E1. |
| E1_SPECKIT_SONARQUBE_ISSUES.json | Total de incidencias registradas durante el escaneo de E1. |
| E1_SPECKIT_SONARQUBE_ISSUES_OPEN.json | Inventario de las 26 incidencias activas/abiertas de la linea base E1. |
| E1_SPECKIT_SONARQUBE_TASK.json | Registro de ejecucion del Compute Engine para E1 (Task ID: 8c8ef226-43ff-4cab-98dc-e0bbdcf9c129). |
| E2_SPECKIT_SONARQUBE_BACKUP_INITIAL_FINAL.json | Copia de respaldo de la medicion inicial E2 antes del re-escaneo E1. |
| E2_SPECKIT_SONARQUBE_RESTORATION.json | Dataset consolidado de la restauracion final de E2 como version mas reciente. |
| E2_SPECKIT_SONARQUBE_RESTORATION_MEASURES.json | Carga de medidas de la restauracion E2 (100 % identicas a la medicion original). |
| E2_SPECKIT_SONARQUBE_RESTORATION_ISSUES.json | Inventario de las 75 incidencias abiertas restauradas de E2. |
| E2_SPECKIT_SONARQUBE_RESTORATION_TASK.json | Registro de Compute Engine de la restauracion E2 (Task ID: 5ad31410-9b38-47e9-bcdb-6cf0d5332e09). |
| E2_SPECKIT_SONARQUBE_FINAL.md | Informe narrativo canonico de la Etapa 2 (preservado). |
| E2_SPECKIT_SONARQUBE_FINAL.json | Dataset canonico de la Etapa 2 (preservado). |
| E2_SPECKIT_SONARQUBE_COMPARATIVA_E1_E2.md | Informe comparativo consolidado E1 vs. E2 (este documento). |

---
**Fin del Informe Comparativo.**
