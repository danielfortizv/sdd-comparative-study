# Shift Bank — Stage 2 — Spec Kit: Reporte Final de Analisis Estatico SonarQube

**Documento ID:** E2_SPECKIT_SONARQUBE_FINAL.md  
**Destino de Evidencia:** Shift-Bank/Etapa 2/_experiment_logs/Spec Kit/E2_SPECKIT_SONARQUBE_FINAL.md  
**Estudio:** SDD Comparative Study — Brownfield Development (Shift Bank Stage 2)  
**Herramienta SDD:** GitHub Spec Kit v1.0.6 sobre Gemini CLI v0.65.0  
**Fecha de Analisis:** 15 de noviembre de 2026 (UTC) / 14 de noviembre de 2026 (Local)  
**Servidor SonarQube:** Community Build 26.9.0.129388 (Docker container sonarqube:latest / sdd-sonarqube:frozen)  
**Escaner:** SonarScanner CLI 8.1.0.6389 (Docker image sdd-sonar-scanner:frozen)  
**Estado de Ejecucion:** SUCCESS (Analisis completado y reportes exportados)

---

## 1. Identificacion del Analisis

| Parametro | Valor de Ejecucion |
|---|---|
| **Proyecto** | Shift Bank - Stage 2 - Spec Kit |
| **Project Key** | Shift-Bank---Stage-2---Spec-Kit |
| **Project Name** | Shift Bank - Stage 2 - Spec Kit |
| **Project Version** | 2.0-final |
| **Task ID (Compute Engine)** | 40bec5a0-b886-4ec6-8b79-4e7b2b29bf6a |
| **Analysis ID** | 378408ec-2411-488e-9ec5-566818186883 |
| **Estado Compute Engine** | SUCCESS |
| **Submitter Login** | dmin (autenticado mediante token de analisis de proyecto) |
| **Submitted At** | 2026-11-15T00:19:05+0000 |
| **Executed At** | 2026-11-15T00:19:07+0000 |
| **Compute Engine Execution Time** | 2.138 ms |
| **Scanner Execution Time** | 1 min 11.957 s (Fase de analisis: 1 min 02.311 s) |

---

## 2. Resultados Cuantitativos Principales

| Metrica | Clave SonarQube | Valor Medido | Observaciones |
|---|---|---:|---|
| **Lineas de Codigo No Comentadas** | 
cloc | **4.099** | Backend Python y Frontend React/TypeScript |
| **Lineas Totales** | lines | **5.039** | Incluye comentarios y lineas en blanco indexadas |
| **Bugs (API Tradicional)** | ugs | **3** | 2 en scheduler.py, 1 en App.tsx |
| **Vulnerabilidades (API Tradicional)** | ulnerabilities | **0** | Cero vulnerabilidades estaticas detectadas |
| **Code Smells (API Tradicional)** | code_smells | **72** | Deuda tecnica agregada |
| **Deuda Tecnica** | sqale_index | **476 min** | 7 h 56 min de esfuerzo estimado de remediacion |
| **Complejidad Ciclomatica** | complexity | **551** | Control flow graph aggregate |
| **Complejidad Cognitiva** | cognitive_complexity | **460** | Comprensibilidad y anidamiento |
| **Densidad de Duplicacion** | duplicated_lines_density | **0,0 %** | Cero bloques duplicados detectados |
| **Cobertura de Pruebas** | coverage | **0,0 %** | Cobertura no importada al escaner en esta ejecucion |
| **Quality Gate** | lert_status | **OK** | Sin condiciones configuradas por defecto (conditions: []) |

---

## 3. Clasificacion Visual MQR (Software Quality)

SonarQube 26.9.0 utiliza la taxonomia de Clean Code / Software Quality (MQR):

| Dimension de Calidad | Issues MQR | Rating MQR | Esfuerzo de Remediacion |
|---|---:|:---:|---:|
| **Seguridad (Security)** | **0** | **A (1.0)** | 0 min |
| **Fiabilidad (Reliability)** | **18** | **D (4.0)** | 270 min |
| **Mantenibilidad (Maintainability)** | **74** | **A (1.0)** | 486 min |
| **Security Hotspots** | **0** | **A** | — |

*Nota:* Los 18 issues de fiabilidad MQR abarcan los 3 bugs tradicionales mas reglas adicionales de fiabilidad (p. ej., control de excepciones no relanzadas y tipado). El rating D de fiabilidad refleja la presencia de bugs con severidad mayor en la ruta del scheduler.

---

## 4. Detalle de Defectos Detectados (Bugs y Top Code Smells)

### 4.1. Inventario de Bugs (3 detectados)

1. **python:S7497 (Severidad: MAJOR)** — ackend/src/scheduler.py (Linea 102):  
   *Mensaje:* Ensure that the asyncio.CancelledError exception is re-raised after your cleanup code.  
   *Causa:* En el bloque de captura de cancelacion del scheduler autonomo, CancelledError es interceptado para finalizar el bucle pero no se relanza explicitamente, lo que SonarQube categoriza como riesgo de contencion en el ciclo de vida de tareas asyncio.
2. **python:S7497 (Severidad: MAJOR)** — ackend/src/scheduler.py (Linea 117):  
   *Mensaje:* Ensure that the asyncio.CancelledError exception is re-raised after your cleanup code.  
   *Causa:* Mismo patron de captura en el sub-bucle de ejecucion periodica de pagos recurrentes.
3. **	ypescript:S1082 (Severidad: MINOR)** — rontend/src/App.tsx (Linea 815):  
   *Mensaje:* Visible, non-interactive elements with click handlers must have at least one keyboard listener.  
   *Causa:* Elemento UI interactivo (modal / pestana) con manejador onClick carece de listener de teclado accesible (onKeyDown / onKeyUp).

### 4.2. Distribucion de Defectos por Componente (Total: 75)

- rontend/src/App.tsx: **25** incidencias (1 bug, 24 code smells — accesibilidad, operadores ternarios anidados 	ypescript:S3358, tipado explicito 	ypescript:S7773).
- ackend/src/api.py: **18** incidencias (cadenas literales duplicadas python:S1192, complejidad de rutas).
- ackend/src/services.py: **8** incidencias (complejidad cognitiva en calculo de limites diarios y transacciones ACH).
- ackend/src/scheduler.py: **5** incidencias (2 bugs python:S7497, 3 code smells).
- ackend/tests/test_ach.py: **4** incidencias (code smells de estilo en aserciones de prueba).
- ackend/tests/test_stage2_regression.py: **3** incidencias.
- ackend/src/database.py: **2** incidencias.
- ackend/src/models.py: **2** incidencias.
- ackend/tests/test_api.py: **2** incidencias.
- ackend/tests/test_limits.py: **2** incidencias.
- ackend/tests/test_recurring.py: **2** incidencias.
- ackend/tests/conftest.py: **1** incidencia.
- rontend/src/services.ts: **1** incidencia.

---

## 5. Comparativa Experimental: Spec Kit vs. Tessl (Etapa 2)

A titulo informativo para la tesis comparativa, se contrastan los resultados de SonarQube sobre la misma especificacion funcional de la Etapa 2:

| Dimension de Calidad Estatica | Tessl (Etapa 2 Inicial) | Tessl (Etapa 2 Final) | Spec Kit (Etapa 2 Final) | Variacion Spec Kit vs. Tessl Final |
|---|---:|---:|---:|---|
| **NCLOC** | 4.230 | 4.267 | **4.099** | -168 LOC (-3,9 %) |
| **Lineas Totales (lines)** | 4.966 | 5.004 | **5.039** | +35 lineas (+0,7 %) |
| **Bugs Tradicionales** | 0 | 0 | **3** | +3 bugs |
| **Vulnerabilidades** | 0 | 0 | **0** | Identico (0) |
| **Code Smells Tradicionales** | 51 | 51 | **72** | +21 smells (+41,2 %) |
| **Deuda Tecnica** | 276 min | 276 min | **476 min** | +200 min (+72,5 %) |
| **Complejidad Cognitiva** | 329 | 337 | **460** | +123 (+36,5 %) |
| **Densidad de Duplicacion** | 0,8 % | 0,8 % | **0,0 %** | -0,8 pp (Mejor) |
| **Reliability Rating Tradicional**| A | A | **C (3.0)** | Menor fiabilidad estatica |
| **Security Rating** | A | A | **A (1.0)** | Identico (A) |
| **Maintainability Rating** | A | A | **A (1.0)** | Identico (A) |
| **Issues Fiabilidad MQR** | 26 | 26 | **18** | -8 issues MQR |
| **Rating Fiabilidad MQR** | C (3.0) | C (3.0) | **D (4.0)** | Impacto de bugs en scheduler |
| **Cobertura Importada** | 0,0 % | 0,0 % | **0,0 %** | Identico (no importada) |

---

## 6. Configuracion del Analisis (Identica Metodologia)

El analisis se ejecuto dentro del contenedor Docker sdd-sonar-scanner:frozen con montaje de volumen de solo lectura (:ro) para garantizar la inmutabilidad de los archivos del repositorio:

- Project Key: Shift-Bank---Stage-2---Spec-Kit
- Project Name: Shift Bank - Stage 2 - Spec Kit
- Project Version: 2.0-final
- Sources: backend/src, frontend/src
- Tests: backend/tests
- Exclusions: node_modules, dist, __pycache__, *.db*, .pytest_cache, _experiment_logs, specs, .specify, .gemini, frontend/src/App.test.tsx, frontend/src/setupTests.ts
- Working Directory: /tmp/.scannerwork
- Encoding: UTF-8

### Advertencias Observadas:
1. SCM provider autodetection failed: Normal al ejecutar dentro del contenedor Docker sin montaje del directorio .git raiz del monorepo.
2. Your code is analyzed as compatible with all Python 3 versions by default: Advertencia identica a la reportada en los analisis de Tessl.

---

## 7. Reporte de Bloqueadores Remanentes

### 7.1. Bloqueador de Analisis sobre la Linea Base Preservada de la Etapa 1
- **Requisito del usuario:** Analizar tanto la linea base preservada de la Etapa 1 como la implementacion final de la Etapa 2 con claves separadas y sin sobreescribir proyectos existentes.
- **Resultado del Intento de Ejecucion:**
  Al invocar SonarScanner sobre Shift-Bank/Etapa 1/Spec Kit con -Dsonar.projectKey=Shift-Bank---Stage-1---Spec-Kit (o shift-bank-stage1-speckit), el escaner falla con:
  ERROR You are not authorized to analyze this project or the project does not exist on SonarQube and you are not authorized to create it. Please contact an administrator.
- **Causa Raiz Verificada:**
  1. La variable de entorno SONAR_TOKEN contiene el token SONAR_TOKEN_SPECKIT2, creado el 2026-11-14T23:58:44Z en SonarQube con ambito type: PROJECT_ANALYSIS_TOKEN asignado exclusivamente al proyecto Shift-Bank---Stage-2---Spec-Kit.
  2. En el modelo de permisos de SonarQube Community Build, un PROJECT_ANALYSIS_TOKEN esta estrictamente restringido a su proyecto de asignacion. No tiene permisos globales para crear proyectos nuevos (POST /api/projects/create retorna HTTP 403 Forbidden: Insufficient privileges) ni para subir analisis a claves de proyecto distintas (HTTP 403 Forbidden).
  3. El proyecto independiente Shift-Bank---Stage-1---Spec-Kit no existe en la base de datos de SonarQube (GET /api/components/show?component=Shift-Bank---Stage-1---Spec-Kit retorna HTTP 404).
  4. El token historico de la Etapa 1 (SONAR_TOKEN_SPECKIT) expiro el 2026-10-30 (isExpired: true).
- **Accion Requerida para el Investigador:**
  Para completar la medicion de la linea base E1:
  - Crear manualmente en la interfaz web de SonarQube el proyecto Shift-Bank---Stage-1---Spec-Kit.
  - Generar un Project Analysis Token especifico para dicho proyecto (o un User Token con permisos globales).
  - Ejecutar el comando del escaner apuntando a Shift-Bank/Etapa 1/Spec Kit.
- **Integridad Experimental:** En cumplimiento de la regla de no inventar mediciones ni alterar bases de datos historicas, se documenta el bloqueador de permisos de forma transparente y reproducible.

---

## 8. Inventario de Archivos de Evidencia Generados

Todos los reportes fueron guardados UNICAMENTE bajo ../_experiment_logs/Spec Kit/:

| Ruta de Archivo | Naturaleza del Artefacto |
|---|---|
| ../_experiment_logs/Spec Kit/E2_SPECKIT_SONARQUBE_FINAL.md | Informe narrativo y analitico consolidado (este documento). |
| ../_experiment_logs/Spec Kit/E2_SPECKIT_SONARQUBE_FINAL.json | Exportacion JSON canonica compatible con el formato de Tessl (E2_TESSL_SONARQUBE_FINAL.json), incluyendo tarea, metricas y Quality Gate. |
| ../_experiment_logs/Spec Kit/E2_SPECKIT_SONARQUBE_MEASURES.json | Carga completa de metricas de componentes desde api/measures/component. |
| ../_experiment_logs/Spec Kit/E2_SPECKIT_SONARQUBE_ISSUES.json | Inventario completo de los 75 issues detectados desde api/issues/search. |
| ../_experiment_logs/Spec Kit/E2_SPECKIT_SONARQUBE_TASK.json | Registro de ejecucion del Compute Engine desde api/ce/task. |

---
**Fin del Reporte de Analisis Estatico SonarQube — Shift Bank Stage 2 Spec Kit.**
