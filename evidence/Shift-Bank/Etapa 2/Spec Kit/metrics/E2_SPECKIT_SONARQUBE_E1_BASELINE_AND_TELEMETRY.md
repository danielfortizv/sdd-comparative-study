# Shift Bank - Spec Kit: Reporte de Intento de Medicion SonarQube E1 y Reconciliacion de Telemetria

**Documento ID:** E2_SPECKIT_SONARQUBE_E1_BASELINE_AND_TELEMETRY.md
**Destino:** Shift-Bank/Etapa 2/_experiment_logs/Spec Kit/E2_SPECKIT_SONARQUBE_E1_BASELINE_AND_TELEMETRY.md
**Estudio:** SDD Comparative Study - Brownfield Development (Shift Bank)
**Herramienta SDD:** GitHub Spec Kit v1.0.6 sobre Gemini CLI v0.65.0
**Fecha:** 15 de noviembre de 2026 (UTC) / 14 de noviembre de 2026 (Local)
**Estado:** INFORME DE BLOQUEADOR DE PERMISOS E1 Y AUDITORIA TELEMETRICA SEPARADA

---

## 1. Intento de Analisis Estatico SonarQube para Linea Base Preservada (Etapa 1)

En cumplimiento de las instrucciones recibidas, se intento ejecutar el analisis de SonarQube exclusivamente sobre el codigo fuente preservado de la Etapa 1 (Shift-Bank/Etapa 1/Spec Kit), montado como volumen de solo lectura (:ro) para garantizar la inmutabilidad absoluta de la linea base historica:

### 1.1. Configuracion Exacta del Escaner Ejecutado
- Contenedor Docker: sdd-sonar-scanner:frozen (SonarScanner CLI 8.1.0.6389).
- Servidor SonarQube: Community Build 26.9.0.129388 en http://host.docker.internal:9000.
- Clave de Proyecto: Shift-Bank---Stage-1---Spec-Kit.
- Nombre de Proyecto: Shift Bank - Stage 1 - Spec Kit.
- Version del Proyecto: 1.0.0.
- Alcance de Fuentes: backend/src, frontend/src.
- Alcance de Pruebas: backend/tests.
- Inclusiones de Prueba: backend/tests/**.
- Exclusiones: node_modules, dist, __pycache__, *.db*, .pytest_cache, _experiment_logs, specs, .specify, .gemini, frontend/src/App.test.tsx, frontend/src/setupTests.ts.
- Directorio de Trabajo del Escaner: /tmp/.scannerwork (aislado en contenedor).

### 1.2. Resultado del Procesamiento Local del Escaner
- Archivos Indexados: 11 archivos (5 archivos fuente Python en backend/src, 4 archivos fuente TypeScript en frontend/src, 1 archivo CSS en frontend/src, mas los archivos de pruebas en backend/tests).
- Sensores Ejecutados: Python Sensor, JS/TS/CSS Sensor (creando programa TypeScript 6.0.3 con tsconfig.json), Secrets Sensor, CPD (Copy-Paste Detector).
- Reporte Generado: 446.6 kB (comprimido en 115.8 kB).

### 1.3. Error Exacto de Autenticacion / Permisos Observado al Subir el Analisis
Al finalizar el analisis local e intentar publicar el reporte en el servidor SonarQube, el escaner fallo con el siguiente error exacto:

`	ext
00:32:33.879 ERROR You are not authorized to analyze this project or the project does not exist on SonarQube and you are not authorized to create it. Please contact an administrator.
00:32:33.979 INFO  EXECUTION FAILURE
00:32:33.981 INFO  Total time: 1:08.961s
`

### 1.4. Causa Raiz Verificada
1. La variable de entorno SONAR_TOKEN contiene el token SONAR_TOKEN_SPECKIT2, generado el 2026-11-14T23:58:44Z en SonarQube con tipo PROJECT_ANALYSIS_TOKEN asociado exclusivamente al proyecto Shift-Bank---Stage-2---Spec-Kit.
2. Segun la arquitectura de seguridad de SonarQube Community Build, un PROJECT_ANALYSIS_TOKEN carece de privilegios globales para aprovisionar proyectos nuevos (POST /api/projects/create responde HTTP 403 Forbidden: Insufficient privileges) y tampoco permite cargar analisis sobre claves de proyecto diferentes (HTTP 403 Forbidden).
3. El proyecto Shift-Bank---Stage-1---Spec-Kit no existe en la base de datos de SonarQube (GET /api/components/show responde HTTP 404).
4. El token historico de la Etapa 1 (SONAR_TOKEN_SPECKIT) expiro el 2026-10-30 (isExpired: true).
5. En consecuencia, de acuerdo con la directiva explicita de la consigna, se reporta el fallo de permisos y se detiene la medicion de E1 sin inventar valores ficticios.

---

## 2. Preservacion de Resultados de la Etapa 2 y Comparacion Concisa E1 vs. E2

Los resultados finales autenticados de la Etapa 2 se preservan de forma integra e inalterada en E2_SPECKIT_SONARQUBE_FINAL.md y en las exportaciones JSON asociadas (E2_SPECKIT_SONARQUBE_FINAL.json, E2_SPECKIT_SONARQUBE_MEASURES.json, E2_SPECKIT_SONARQUBE_ISSUES.json, E2_SPECKIT_SONARQUBE_TASK.json).

A continuacion se presenta la comparativa concisa entre el estado de partida (E1) y la implementacion final (E2) en Spec Kit:

| Dimension de Analisis | Etapa 1 (Linea Base Preservada) | Etapa 2 (Implementacion Final Spec Kit) | Variacion / Impacto E2 vs. E1 |
|---|---|---|---|
| **Estado Analisis SonarQube** | BLOQUEADO (HTTP 403/404) | **SUCCESS (Computado en Servidor)** | Analisis E2 autenticado y exportado |
| **Archivos Indexados Escaner** | 11 archivos | **23 archivos** | +12 archivos (+109,1 %) |
| **Archivos Totales de Proyecto** | 59 archivos | **74 archivos** | +15 archivos netos (+25,4 %) |
| **Evolucion de Lineas (Diff LOC)**| 0 (linea base) | **+7.298 anadidas / -273 borradas** | +7.025 lineas de cambio neto |
| **Lineas de Codigo (NCLOC)** | No cargado en servidor | **4.099** | Backend Python y Frontend React/TS |
| **Lineas Totales (lines)** | No cargado en servidor | **5.039** | Incluye comentarios y lineas en blanco |
| **Bugs Tradicionales** | No medible en servidor | **3** (2 en scheduler.py, 1 en App.tsx) | Introducidos en implementacion E2 |
| **Vulnerabilidades** | No medible en servidor | **0** (Rating A 1.0) | Limpio estaticamente |
| **Code Smells** | No medible en servidor | **72** | Deuda tecnica agregada |
| **Deuda Tecnica (sqale_index)**| No medible en servidor | **476 minutos** (7 h 56 min) | Esfuerzo de remediacion estimado |
| **Complejidad Cognitiva** | No medible en servidor | **460** | Comprensibilidad y anidamiento |
| **Complejidad Ciclomatica** | No medible en servidor | **551** | Grafo de flujo de control |
| **Densidad de Duplicacion** | No medible en servidor | **0,0 %** | Cero bloques duplicados |
| **Quality Gate** | No evaluado | **OK** (caycStatus: compliant) | Sin condiciones configuradas |
| **Fiabilidad MQR** | No medible en servidor | **Rating D (4.0)** (18 issues) | Impacto de bugs en scheduler async |
| **Seguridad MQR** | No medible en servidor | **Rating A (1.0)** (0 issues) | Optimo |
| **Mantenibilidad MQR** | No medible en servidor | **Rating A (1.0)** (74 issues) | Esfuerzo de remediacion: 486 min |

---

## 3. Documentacion Separada de Telemetria: Captura /stats vs. Snapshots JSONL

Para evitar el doble conteo de solicitudes, llamadas a herramientas o tokens en la tesis, se documentan y concilian rigurosamente las dos capas de observabilidad registradas durante la Etapa 2 de Spec Kit:

### 3.1. Telemetria Consolidada desde Snapshots JSONL (Nivel Cable API HTTP)
Los archivos JSONL registran cada transaccion HTTP entre el cliente Gemini CLI y la API del modelo de lenguaje:

- **Anomalia de Registro Plano (Descartada):** El log plano contabilizaba 5.213 herramientas y 236.4M tokens debido a la duplicacion de eventos en streaming y la acumulacion de contexto plano en cada turno.
- **Cifras Reales Deduplicadas por Identificador de Evento (Capa API):**
  - **Sesiones:** 2 (Sesion 01: Descubrimiento y especificacion; Sesion 02: Remediacion e implementacion).
  - **Turnos Humanos / Solicitudes:** 25 interacciones humanas.
  - **Solicitudes al Modelo (Model Requests):** **521 turnos API**.
  - **Llamadas a Herramientas Unicas:** **485 llamadas ejecutadas** (520 respuestas registradas incluyendo reintentos, 10 errores de ejecucion).
  - **Tokens de Entrada Reales:** **123.950.969 tokens**.
  - **Tokens Cacheados (Prompt Cache):** **108.868.091 tokens** (tasa de acierto de cache: 87,8 %).
  - **Tokens de Salida:** **335.430 tokens**.
  - **Tiempo de Pared Transcurrido:** **4 h 55 min 34 s**.

### 3.2. Telemetria de Captura de Pantalla Gemini CLI (/stats - Nivel Cliente CLI)
La captura de pantalla final de la interfaz interactiva de Gemini CLI para la sesion principal e272589-bd7f-4c7d-8205-4f821865bbc9 registro los acumuladores internos del proceso cliente:

- **Llamadas a Herramientas:** **486 llamadas** (480 exitosas, 6 fallidas).
- **Duracion Total de la Sesion:** **5 h 34 min 36 s**.
- **Tiempo Activo del Agente:** **4 h 22 min 55 s**.
- **Tiempo en Solicitudes de Modelo (API Time):** **1 h 30 min 24 s**.
- **Tiempo en Ejecucion de Herramientas (Tool Time):** **2 h 52 min 31 s**.
- **Tiempo Inactivo de Usuario / Pausas:** **1 h 11 min 41 s**.

### 3.3. Correccion Metodologica y Distincion de Ambitos (Scopes)
En estricto cumplimiento de la correccion metodologica reportada:
1. **No Equivalencia Directa:** Las **485 llamadas a herramientas deduplicadas de JSONL** cubren las **dos primeras sesiones historicas** de desarrollo (Sesion 01: especificacion y diseno; Sesion 02: implementacion y pruebas). Por el contrario, las **486 llamadas a herramientas de la captura de pantalla (/stats)** corresponden a **una instantanea de sesion posterior** (Sesion e272589-bd7f-4c7d-8205-4f821865bbc9).
2. **Preservacion de Ambas Mediciones:** Ambas cifras son mediciones empiricas validas pero pertenecen a ambitos temporales y ventanas de sesion diferentes:
   - **Ambito JSONL (Historico de 2 sesiones):** 485 herramientas unicas, 521 solicitudes API, 123.95M tokens de entrada, 335.4K tokens de salida, 4 h 55 min 34 s de pared.
   - **Ambito Pantalla /stats (Instantanea de sesion posterior):** 486 herramientas (480 exitosas, 6 fallidas), 5 h 34 min 36 s de duracion de sesion, 4 h 22 min 55 s de agente activo, 1 h 30 min 24 s de tiempo API, 2 h 52 min 31 s de tiempo de herramientas.
3. **Regla Anti-Doble Conteo:** No deben sumarse aritmeticamente las llamadas de ambas fuentes ni asumirse que miden el mismo periodo temporal. Ambas deben reportarse de forma desglosada con sus respectivos alcances y marcas de tiempo.

---

## 4. Estado de Archivos Generados en ../_experiment_logs/Spec Kit/

| Archivo | Descripcion |
|---|---|
| E2_SPECKIT_SONARQUBE_FINAL.md | Informe completo de medicion estatica de la Etapa 2 (preservado). |
| E2_SPECKIT_SONARQUBE_FINAL.json | JSON canonico con medidas, tarea y Quality Gate de la Etapa 2 (preservado). |
| E2_SPECKIT_SONARQUBE_MEASURES.json | Carga de medidas completas de componentes E2 (preservado). |
| E2_SPECKIT_SONARQUBE_ISSUES.json | Inventario de 75 issues detectados en E2 (preservado). |
| E2_SPECKIT_SONARQUBE_TASK.json | Metadata de la tarea del Compute Engine de SonarQube para E2 (preservado). |
| E2_SPECKIT_SONARQUBE_E1_BASELINE_AND_TELEMETRY.md | Documento actual: auditoria del intento E1, comparativa E1-E2 y reconciliacion /stats. |

---
**Fin del Documento.**
