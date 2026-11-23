# Reporte de Medición SonarQube Post-Remediación — Shift Bank Etapa 3 (Tessl)

**Fecha de medición:** 13 de noviembre de 2026  
**Fase:** Medición final post-remediación (Stage 3 — Tessl SDD)  
**Proyecto:** Shift Bank — Stage 3 — Tessl  
**Project Key:** `Shift-Bank---Stage-3---Tessl`  
**Servidor SonarQube:** `http://localhost:9000` (Community Build v26.9.0.129388, Status: UP)  
**Versión de SonarScanner:** 5.1.0 (`sonarqube-scanner` via npx)  
**ID de Tarea Compute Engine:** `402541bb-403f-42e9-ba70-d00170ea84b1`  
**ID de Análisis:** `c9aa6430-6ff8-4b47-81e2-474427b91d8e`  
**Estado del Procesamiento:** `SUCCESS`  
**Tiempo de Ejecución:** Scanner: 17.360 s | Compute Engine: 1.716 ms  
**Línea Base de Referencia:** `E3_TESSL_SONARQUBE_COVERAGE_BASELINE_20261113.json` (Análisis `cce34118`)  

---

## 1. Tabla Comparativa General (Antes vs. Después de la Remediación)

| Métrica | Clave API SonarQube | Línea Base (Con Cobertura) | Valor Final Post-Remediación | Diferencia Absoluta | Variación % |
|---|---|---:|---:|---:|---:|
| **Quality Gate** | `alert_status` | **OK** (0 cond.) | **ERROR** (3 cond. CAYC) | Cambio de estado | — |
| **Bugs tradicionales** | `bugs` | **12** | **0** | **-12** | **-100,0 %** |
| **Vulnerabilidades tradicionales** | `vulnerabilities` | **2** | **0** | **-2** | **-100,0 %** |
| **Code Smells tradicionales** | `code_smells` | **71** | **73** | **+2** | **+2,8 %** |
| **Total Defectos Abiertos** | *bugs + vuln + smells* | **85** | **73** | **-12** | **-14,1 %** |
| **Deuda Técnica** | `sqale_index` | 450 min (7,5 h) | **496 min** (8,27 h) | +46 min | +10,2 % |
| **Ratio de Deuda Técnica** | `sqale_debt_ratio` | 0,3 % | 0,3 % | 0,0 pp | 0,0 % |
| **Rating de Fiabilidad** | `reliability_rating` | 4.0 (D) | **1.0 (A)** | -3.0 (Mejora a A) | — |
| **Rating de Seguridad** | `security_rating` | 2.0 (B) | **1.0 (A)** | -1.0 (Mejora a A) | — |
| **Rating de Mantenibilidad** | `sqale_rating` | 1.0 (A) | **1.0 (A)** | 0.0 | — |
| **Complejidad Cognitiva** | `cognitive_complexity` | 585 | **624** | +39 | +6,7 % |
| **Complejidad Ciclomática** | `complexity` | 697 | **712** | +15 | +2,2 % |
| **Líneas de código no comentadas** | `ncloc` | 5.507 | **5.533** | +26 | +0,5 % |
| **Líneas totales** | `lines` | 6.630 | **6.667** | +37 | +0,6 % |
| **Sentencias** | `statements` | 1.951 | **1.973** | +22 | +1,1 % |
| **Funciones** | `functions` | 233 | **234** | +1 | +0,4 % |
| **Líneas de comentarios** | `comment_lines` | 348 | **351** | +3 | +0,9 % |
| **Densidad de comentarios** | `comment_lines_density` | 5,9 % | **6,0 %** | +0,1 pp | +1,7 % |
| **Duplicación de líneas** | `duplicated_lines_density` | 0,6 % | **0,6 %** | 0,0 pp | 0,0 % |
| **Líneas duplicadas** | `duplicated_lines` | 40 | **40** | 0 | 0,0 % |
| **Bloques duplicados** | `duplicated_blocks` | 2 | **2** | 0 | 0,0 % |
| **Archivos duplicados** | `duplicated_files` | 2 | **2** | 0 | 0,0 % |
| **Security Hotspots** | `security_hotspots` | 0 | **0** | 0 | 0,0 % |
| **Cobertura reportada** | `coverage` | **78,0 %** | **77,7 %** | **-0,3 pp** | -0,4 % |
| **Cobertura de líneas** | `line_coverage` | 78,5 % | **78,2 %** | -0,3 pp | -0,4 % |
| **Cobertura de ramas** | `branch_coverage` | 69,3 % | **69,3 %** | 0,0 pp | 0,0 % |

### Métricas Bajo el Modelo MQR (Clean Code)

| Métrica MQR | Clave API SonarQube | Línea Base | Valor Final Post-Remediación | Diferencia |
|---|---|---:|---:|---:|
| **Incidencias de Fiabilidad (Reliability)** | `software_quality_reliability_issues` | 40 | **28** | **-12** (-30,0 %) |
| **Rating de Fiabilidad MQR** | `software_quality_reliability_rating` | 4.0 (D) | **3.0 (C)** | -1.0 (Mejora a C) |
| **Incidencias de Seguridad (Security)** | `software_quality_security_issues` | 2 | **0** | **-2** (-100,0 %) |
| **Rating de Seguridad MQR** | `software_quality_security_rating` | 2.0 (B) | **1.0 (A)** | -1.0 (Mejora a A) |
| **Incidencias de Mantenibilidad (Maintainability)** | `software_quality_maintainability_issues` | 62 | **64** | **+2** (+3,2 %) |
| **Rating de Mantenibilidad MQR** | `software_quality_maintainability_rating` | 1.0 (A) | **1.0 (A)** | 0.0 |
| **Ratio de Deuda de Mantenibilidad** | `software_quality_maintainability_debt_ratio` | 0,3 % | **0,3 %** | 0,0 pp |

---

## 2. Verificación de Hallazgos Prioritarios

### 2.1. Eliminación de los 12 Bugs python:S5779 (100% Resueltos)
- Todas las 12 incidencias de la regla `python:S5779` (*"Don't use assert inside a try-except that catches AssertionError"*) en `backend/app/services/migration_service.py` pasaron al estado **CLOSED** con resolución **FIXED** en SonarQube.
- **Mecanismo:** Se sustituyó el uso de aserciones por comprobaciones condicionales explícitas con la excepción dedicada `MigrationVerificationError(RuntimeError)`.
- **Resultado:** Bugs abiertos en el proyecto: **0**. Rating de Fiabilidad tradicional: **A (1.0)**.

### 2.2. Eliminación de las 2 Vulnerabilidades docker:S6471 (100% Resueltas)
- Ambas incidencias de la regla `docker:S6471` (*"The image runs with 'root' as the default user. Make sure it is safe here"*) pasaron al estado **CLOSED** con resolución **FIXED**:
  - `backend/Dockerfile:1`: Resuelto mediante `USER appuser` (UID 1000).
  - `frontend/Dockerfile:14`: Resuelto mediante `USER nginx`.
- **Resultado:** Vulnerabilidades abiertas en el proyecto: **0**. Rating de Seguridad tradicional: **A (1.0)**.

---

## 3. Desglose y Distinción de Code Smells (73 Totales)

### 3.1. Incidencias Preexistentes no Resueltas (71 Code Smells)
De acuerdo con las instrucciones metodológicas (*"Do not remediate unrelated code smells"*), las 71 incidencias de mantenibilidad de la línea base se mantuvieron inalteradas para no desvirtuar el estudio comparativo.

### 3.2. Incidencias Nuevas Introducidas por la Remediación (2 Code Smells)
El análisis identificó exactamente 2 nuevas incidencias de mantenibilidad surgidas directamente de los cambios de hardening:
1. **`docker:S7031` (Severidad MINOR):**  
   - **Ubicación:** `backend/Dockerfile` (Línea 6).  
   - **Mensaje:** *"Merge this RUN instruction with the consecutive ones."*  
   - **Causa:** La adición de la instrucción `RUN groupadd -r appuser && useradd ...` genera dos comandos `RUN` sucesivos (preparación de usuario e instalación de paquetes).
2. **`python:S8997` (Severidad MAJOR):**  
   - **Ubicación:** `backend/tests/test_deployment_config.py` (Línea 120).  
   - **Mensaje:** *"Use the 'monkeypatch' fixture for temporary modifications instead of manually modifying global state."*  
   - **Causa:** La verificación de reproducibilidad desde clon limpio introduce `sys.path.insert(0, WORKSPACE_ROOT)` de forma condicional para importar el generador de certificados si están ausentes.

---

## 4. Análisis Causal de Métricas Derivadas

### 4.1. Incremento de Complejidad Cognitiva (+39) y Ciclomática (+15)
- **Observación:** La complejidad cognitiva aumentó de 585 a 624 (+39 / +6,7%) y la ciclomática de 697 a 712 (+15 / +2,2%).
- **Explicación técnica:** La sustitución de 12 aserciones lineales de una sola línea por 12 bloques condicionales explícitos (`if not cond: raise MigrationVerificationError(...)`) dentro de los bucles de verificación de beneficiarios, transferencias y cronogramas añade bifurcaciones lógicas formales al árbol sintáctico abstracto (AST). De acuerdo con el algoritmo de cálculo de SonarSource, cada sentencia condicional anidada incrementa la complejidad cognitiva y ciclomática, así como el tiempo estimado de deuda técnica (+46 min). Esto evidencia el trade-off formal entre seguridad en tiempo de ejecución y complejidad estática.

### 4.2. Variación en Cobertura Importada (-0,3 pp)
- **Observación:** La cobertura agregada pasó de 78,0% a 77,7% (-0,3 pp), con cobertura de líneas en 78,2% (-0,3 pp) y ramas en 69,3% (invariante).
- **Explicación técnica:** Los nuevos caminos de excepción (las sentencias `raise MigrationVerificationError`) y la guarda defensiva `validate_admin_key_at_startup()` en `backend/app/main.py` incrementaron el número total de líneas ejecutables evaluadas por `pytest-cov` (de 1.589 a 1.610 sentencias). Dado que las pruebas funcionales verifican el camino exitoso de migración, las ramas de excepción extrema de corrupción representan código ejecutable adicional no cubierto en el denominador, generando una ligera variación porcentual sin reducción de pruebas aprobadas (118/118 aprobadas).

### 4.3. Estado del Quality Gate (ERROR en Nuevo Código)
- **Observación:** El Quality Gate pasó de `OK` a `ERROR`.
- **Evaluación metodológica:** En la línea base inicial, el Quality Gate reportó `OK` porque **no existían condiciones configuradas sobre el código total** (`conditions: []`). Al ejecutarse un escaneo subsecuente con código modificado (período `PREVIOUS_VERSION`), SonarQube activa las condiciones Clean as You Code (CAYC):
  - `new_coverage`: 52,9% (Umbral requerido: >= 80,0%) -> **ERROR**.
  - `new_violations`: 2 incidencias nuevas introducidas -> **ERROR**.
  - `new_duplicated_lines_density`: 0,0% (Umbral: <= 3,0%) -> **OK**.
- **Conclusión:** Se ratifica el principio metodológico de la tesis: un Quality Gate con estado `OK` sin condiciones evaluadas no constituye evidencia de cumplimiento de estándares de calidad, sino una ausencia de reglas de corte configuradas para código legado.

---

## 5. Advertencia Metodológica sobre Integridad de Base de Datos

Durante la fase de verificación previa:
- El archivo temporal SQLite `shift_bank.db-shm` mostró un cambio en su marca de tiempo de última modificación durante la ejecución de las pruebas locales de humo de integración.
- Por tanto, **se registra formalmente que la no-modificación histórica de los archivos de base de datos no puede ser garantizada de forma estrictamente independiente mediante metadatos del sistema de archivos**.
- No obstante, se verificó que el archivo de base de datos principal `shift_bank.db` conservó exactamente su tamaño íntegro de 155.648 bytes y ninguna tabla ni registro de la fase previa fue intervenido.

---

## 6. Conclusión y Cierre de la Medición

La fase de medición final post-remediación para Shift Bank Etapa 3 (Tessl) concluyó con:
1. **0 Bugs** (12 eliminados, fiabilidad calificada en **A**).
2. **0 Vulnerabilidades** (2 eliminadas, seguridad calificada en **A**).
3. **0 Security Hotspots**.
4. **73 Code Smells** (71 preexistentes preservados + 2 identificados en los ajustes de hardening).
5. **77,7 % de Cobertura Global** y **118 pruebas automatizadas aprobadas (100% de éxito)**.
6. Ningún código de producción adicional fue modificado en esta fase de medición.
