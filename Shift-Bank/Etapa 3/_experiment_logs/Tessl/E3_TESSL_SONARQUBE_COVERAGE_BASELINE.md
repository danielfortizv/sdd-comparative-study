# Reporte de Línea Base SonarQube con Cobertura Importada — Shift Bank Etapa 3 (Tessl)

**Fecha de medición:** 13 de noviembre de 2026  
**Fase:** Línea base pre-remediación con importación de cobertura (Stage 3 — Tessl SDD)  
**Proyecto:** Shift Bank — Stage 3 — Tessl  
**Project Key:** `Shift-Bank---Stage-3---Tessl`  
**Servidor SonarQube:** `http://localhost:9000` (Community Build v26.9.0.129388)  
**Versión de SonarScanner:** 5.1.0 (`sonarqube-scanner` via npx)  
**ID de Tarea Compute Engine:** `7533ad8b-5b2d-4bf8-bdac-c877bd2ac697`  
**ID de Análisis:** `cce34118-14b2-48e4-a2f6-7a678977bacc`  
**Estado del Procesamiento:** `SUCCESS`  
**Tiempo de Ejecución:** Scanner: 16.030 s | Compute Engine: 1.318 ms  

---

## 1. Propósito Metodológico

Este reporte registra la **línea base previa a cualquier remediación de código**, habilitando la importación de los reportes de cobertura generados por las herramientas de prueba automatizadas compatibles:
- `backend/coverage.xml` (generado con `pytest-cov 7.1.0`)
- `frontend/coverage/lcov.info` (generado con `@vitest/coverage-v8 1.6.1`)

**Importante:** El código fuente de producción no ha sido modificado en esta fase. Este escaneo permite **desacoplar analíticamente la mejora de ingestión de cobertura de las posteriores mejoras de calidad de código y corrección de defectos**.

---

## 2. Comparación: Línea Base Sin Cobertura vs. Con Cobertura Importada (Código Inalterado)

| Métrica | Clave API SonarQube | Línea Base Original (`cee9b875`) | Línea Base + Cobertura (`cce34118`) | Variación |
|---|---|---:|---:|---:|
| **Quality Gate** | `alert_status` | **OK** | **OK** | Sin cambio |
| **Líneas de código no comentadas** | `ncloc` | 5.507 | 5.507 | 0 |
| **Líneas totales** | `lines` | 6.630 | 6.630 | 0 |
| **Sentencias** | `statements` | 1.951 | 1.951 | 0 |
| **Funciones** | `functions` | 233 | 233 | 0 |
| **Bugs (API clásica)** | `bugs` | 12 | 12 | 0 |
| **Vulnerabilidades (API clásica)** | `vulnerabilities` | 2 | 2 | 0 |
| **Code Smells (API clásica)** | `code_smells | 71 | 71 | 0 |
| **Total Defectos** | — | 85 | 85 | 0 |
| **Deuda Técnica** | `sqale_index` | 450 min | 450 min | 0 |
| **Ratio de Deuda Técnica** | `sqale_debt_ratio` | 0,3 % | 0,3 % | 0 |
| **Complejidad Cognitiva** | `cognitive_complexity` | 585 | 585 | 0 |
| **Complejidad Ciclomática** | `complexity` | 697 | 697 | 0 |
| **Duplicación de líneas** | `duplicated_lines_density` | 0,6 % | 0,6 % | 0 |
| **Security Hotspots** | `security_hotspots` | 0 | 0 | 0 |
| **Cobertura reportada (`coverage`)** | `coverage` | **0,0 %** | **78,0 %** | **+78,0 pp** |
| **Cobertura de líneas (`line_coverage`)** | `line_coverage` | — | **78,5 %** | — |
| **Cobertura de ramas (`branch_coverage`)** | `branch_coverage` | — | **69,3 %** | — |

---

## 3. Conclusión de la Fase de Congelamiento de Línea Base

1. **Invarianza del Código:** Las métricas de defectos (12 bugs, 2 vulnerabilidades, 71 code smells), deuda técnica (450 min), complejidad cognitiva (585) y duplicación (0,6%) son exactamente idénticas entre ambos análisis, certificando que el código no fue alterado.
2. **Impacto de la Ingestión de Cobertura:** La importación de los reportes existentes de `pytest-cov` y `vitest-coverage-v8` eleva la cobertura agregada calculada por SonarQube de 0,0% a **78,0%** (78,5% líneas, 69,3% ramas).
3. **Preservación:** El documento `E3_TESSL_SONARQUBE_BASELINE.md` original se conserva inalterado como la referencia oficial de inicio de la etapa de medición.
