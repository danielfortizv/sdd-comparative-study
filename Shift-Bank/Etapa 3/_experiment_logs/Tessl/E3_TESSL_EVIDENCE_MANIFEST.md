# Manifiesto de Evidencias Experimentales — Shift Bank Etapa 3 (Tessl SDD)

**Caso de Estudio:** Shift Bank  
**Etapa:** 3 — Cifrado E2E, Auditoría Inmutable, Pruebas de Carga y Despliegue  
**Herramienta:** Tessl SDD (vía Gemini CLI con plugin Spec-Driven Development)  
**Fecha de Consolidación:** 13 de noviembre de 2026  
**Ubicación Principal de Bitácoras:** Shift-Bank/Etapa 3/_experiment_logs/Tessl/  

---

## 1. Inventario y Clasificación de Evidencias Primarias

| Identificador de Artefacto | Archivo / Ruta Relativa | Fecha / Timestamp | Tipo de Evidencia | Descripción y Propósito |
|---|---|---|---|---|
| **E3-ART-01** | SEED-3 (1).md | 2026-11-13 14:31 | Requerimientos Base | Semilla común de la Etapa 3 compartida entre herramientas (Opción A). |
| **E3-ART-02** | PROMPT_GEMINI_TESSL_ETAPA3_01 (1).md | 2026-11-13 14:31 | Prompt Inicial | Directiva inicial del investigador para la preparación y arranque de la Etapa 3. |
| **E3-ART-03** | E3_TESSL_REGISTRO_00_PREPARACION.md | 2026-11-13 14:31 | Protocolo Interno | Registro de condiciones iniciales, derivas de entorno y comprobaciones de copia. |
| **E3-ART-04** | E3_TESSL_PREPARACION_01.md | 2026-11-13 14:18 | Bitácora de Copia | Verificación inicial de copia brownfield y exclusiones de build/dependencias. |
| **E3-ART-05** | E3_TESSL_BASELINE_SHA256.csv | 2026-11-13 14:14 | Integridad Hashing | Hashes criptográficos SHA-256 de los 66 archivos base heredados de la Etapa 2. |
| **E3-ART-06** | E3_TESSL_BASELINE_METADATA.json | 2026-11-13 14:17 | Metadatos de Copia | Resumen estructurado del inventario y verificación inicial de integridad. |
| **E3-ART-07** | E3_TESSL_REGRESION_BACKEND.txt | 2026-11-13 14:15 | Prueba de Regresión | Registro de 79 pruebas Pytest previas a la medición estática. |
| **E3-ART-08** | E3_TESSL_REGRESION_FRONTEND.txt | 2026-11-13 14:15 | Prueba de Regresión | Registro de 39 pruebas Vitest previas a la medición estática. |
| **E3-ART-09** | ackend/tests/load/load_benchmark_report.json | 2026-11-13 16:49 | Benchmark Carga | Reporte formal generado por Locust: 100 usuarios, p95 12,8 ms, 0,0 % errores. |
| **E3-ART-10** | E3_TESSL_SONARQUBE_BASELINE.md | 2026-11-13 17:38 | Calidad Estática | Reporte oficial de línea base SonarQube original (análisis cee9b875, 85 defectos). |
| **E3-ART-11** | E3_TESSL_SONARQUBE_PRE_REMEDIATION_MEASURES_20261113.json | 2026-11-13 17:45 | Métricas Crudas | Dump JSON de métricas tradicionales y MQR de la línea base pre-remediación. |
| **E3-ART-12** | E3_TESSL_SONARQUBE_PRE_REMEDIATION_ISSUES_20261113.json | 2026-11-13 17:45 | Incidencias Crudas | Dump JSON de las 85 incidencias completas de la línea base pre-remediación. |
| **E3-ART-13** | E3_TESSL_SONARQUBE_COVERAGE_BASELINE.md | 2026-11-13 17:49 | Calidad Estática | Línea base intermedia con cobertura importada (análisis cce34118, 78,0 % cobertura). |
| **E3-ART-14** | E3_TESSL_SONARQUBE_COVERAGE_BASELINE_20261113.json | 2026-11-13 17:48 | Métricas Crudas | Dump JSON de métricas con cobertura sobre código fuente inalterado. |
| **E3-ART-15** | E3_TESSL_SONARQUBE_POST_REMEDIATION.md | 2026-11-13 18:20 | Calidad Estática | Reporte post-remediación inicial (análisis c9aa6430, 0 bugs, 0 vulns, 73 smells). |
| **E3-ART-16** | E3_TESSL_SONARQUBE_POST_REMEDIATION_MEASURES_20261113.json | 2026-11-13 18:19 | Métricas Crudas | Dump JSON de métricas post-remediación de prioridad. |
| **E3-ART-17** | E3_TESSL_SONARQUBE_POST_REMEDIATION_ISSUES_20261113.json | 2026-11-13 18:19 | Incidencias Crudas | Dump JSON de incidencias post-remediación (14 cerradas/fijadas). |
| **E3-ART-18** | E3_TESSL_SONARQUBE_QUALITY_CLOSURE.md | 2026-11-13 18:30 | Calidad Estática | Reporte final de cierre focalizado de calidad (análisis e560df70, 72 smells, 77,9 % cov). |
| **E3-ART-19** | E3_TESSL_SONARQUBE_QUALITY_CLOSURE_MEASURES_20261113.json | 2026-11-13 18:30 | Métricas Crudas | Dump JSON final de métricas post-cierre de calidad. |
| **E3-ART-20** | E3_TESSL_SONARQUBE_QUALITY_CLOSURE_ISSUES_20261113.json | 2026-11-13 18:30 | Incidencias Crudas | Dump JSON final de incidencias (16 cerradas/fijadas, 72 abiertas). |
| **E3-ART-21** | E3_TESSL_REGISTRO_01_INTERACCIONES.md | 2026-11-13 18:31 | Bitácora de Sesión | Registro detallado de las 23 interacciones del ciclo de vida experimental. |
| **E3-ART-22** | E3_TESSL_TRACEABILITY.csv | 2026-11-13 18:35 | Trazabilidad | Matriz que vincula cada requerimiento funcional con spec, código y tests. |
| **E3-ART-23** | E3_TESSL_INFORME_EXPERIMENTAL.md | 2026-11-13 18:40 | Reporte Científico | Informe formal de resultados bajo las cinco dimensiones de estandarización. |
| **E3-ART-24** | docs/STAGE3_TECHNICAL.md | 2026-11-13 18:42 | Manual Técnico | Documentación técnica exhaustiva de arquitectura, contratos, criptografía y despliegue. |
| **E3-ART-25** | E3_TESSL_TEXTO_TESIS_9_4_4.md | 2026-11-13 18:45 | Texto de Tesis | Sección académica consolidada para el cuerpo principal de la tesis (Capítulo 9.4.4). |

---

## 2. Mapa de Integridad y Trazabilidad de Requerimientos

La correspondencia detallada entre las 4 capacidades de la semilla SEED-3.md, las 11 especificaciones SDD en specs/, los módulos de código de producción y las 125 pruebas automatizadas aprobadas se encuentra formalizada en el archivo:
- **Ruta:** Shift-Bank/Etapa 3/_experiment_logs/Tessl/E3_TESSL_TRACEABILITY.csv
- **Requerimientos cubiertos:** 24 requisitos formales de arquitectura, seguridad, carga y despliegue (E3-REQ-01 a E3-REQ-24), todos en estado VERIFIED.

---

## 3. Protocolo de Protección de Credenciales y Secretos

En cumplimiento estricto con los mandatos de seguridad del proyecto:
1. **Credenciales de SonarQube:** La variable SONAR_TOKEN fue utilizada exclusivamente en memoria durante las ejecuciones de SonarScanner y llamadas REST al servidor local; su valor no fue impreso en terminal, ni almacenado en logs, ni persistido en ningún archivo de bitácora.
2. **Secretos Criptográficos de Aplicación:** Los archivos .env reales y certificados privados TLS (
ginx/certs/*.key) están debidamente excluidos por .gitignore. Las plantillas públicas (.env.example y docker-compose.yml) no contienen claves predeterminadas ni contraseñas operativas conocidas.
