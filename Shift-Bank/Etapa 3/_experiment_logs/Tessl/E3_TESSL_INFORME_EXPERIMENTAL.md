# Informe experimental de cierre — Shift Bank, Etapa 3, Tessl SDD

**Fecha de corte:** 13/11/2026  
**Caso de estudio:** Aplicación bancaria Shift Bank  
**Etapa:** 3 — Arquitectura, seguridad, pruebas de carga y despliegue  
**Herramienta SDD:** Tessl (mediante Gemini CLI con plugin Spec-Driven Development)  
**Condición experimental:** Extensión brownfield de la Etapa 2  
**Opción de extensión:** A (Cifrado E2E, auditoría inmutable, pruebas de carga, despliegue en contenedores)  

---

## 1. Resumen Ejecutivo

La Etapa 3 de Shift Bank completó la evolución de la aplicación bancaria desde la base funcional consolidada en la Etapa 2, incorporando cuatro capacidades críticas de nivel empresarial: (1) cifrado híbrido extremo a extremo (RSA-OAEP en cliente y AES-256-GCM en tránsito y reposo con migración atómica); (2) libro mayor de auditoría criptográfica inmutable encadenado por HMAC-SHA256 con garantías transaccionales fail-closed y triggers de base de datos; (3) suite de pruebas de carga automatizadas mediante Locust con base de datos SQLite aislada y validación formal de SLA (p95 < 200 ms, tasa de error < 1,0 %); y (4) arquitectura de despliegue contenerizado en Docker Compose con reverse proxy Nginx HTTPS (TLSv1.2/1.3), usuarios de ejecución no-root y validación estricta de secretos de entorno sin valores por defecto.

El ciclo de desarrollo y remediación ejecutado bajo el flujo Tessl SDD cerró con **125 pruebas automatizadas aprobadas (86 backend, 39 frontend)**, compilación de producción TypeScript/Vite exitosa con cero errores, y validación en vivo de despliegue mediante 9 pruebas de humo integradas sobre HTTPS en contenedores Docker. Se consolidaron **11 especificaciones (.spec.md) con 1.093 líneas físicas y 323 cláusulas de requerimiento**.

La evaluación estática en SonarQube Community Build v26.9.0 analizó 5.536 líneas de código de producción (ncloc) y 6.668 líneas totales. Tras la remediación guiada, **se eliminaron el 100 % de los bugs (12/12) y de las vulnerabilidades (2/2)**, alcanzando calificación **A** en fiabilidad y **A** en seguridad. El proyecto cerró con 72 code smells abiertos (deuda técnica de 491 minutos y complejidad cognitiva de 624). La cobertura de código importada alcanzó el **77,9 % global** (78,4 % en líneas y 69,3 % en ramas), elevándose la cobertura sobre código nuevo al **70,6 %**. El Quality Gate final reportó **ERROR** debido a los umbrales Clean as You Code (CAYC) para código nuevo (cobertura requerida >= 80,0 % e incidencias nuevas <= 0), ratificando la advertencia metodológica de que el estado OK de la línea base inicial respondía a una aprobación incondicionada por ausencia de reglas configuradas y no a un cumplimiento pleno de calidad.

---

## 2. Contexto Experimental y Entorno de Ejecución

- **Línea base heredada:** Proyecto copiado desde la Etapa 2, verificando integridad de archivos base mediante inventario SHA-256. Se preservó la compatibilidad completa con los módulos de Cuentas, Transferencias internas, Movimientos, MFA, ACH/Terceros, Pagos Recurrentes y Límites dinámicos.
- **Entorno operativo:** Windows 11 Enterprise (amd64), PowerShell 5.1, Python 3.13.2, Node.js 24.19.0, npm 11.17.0, Gemini CLI con modelo principal Gemini 3 Flash / 3.8 Flash, Tessl CLI 0.118.1 con tile 	essl-labs/spec-driven-development@2.0.1.
- **Servidor SonarQube:** Community Build v26.9.0.129388 (Status: UP) con SonarScanner 5.1.0 vía 
px.
- **Integridad y límites:** Durante todo el experimento se preservaron intactas las Etapas 1 y 2, los volúmenes de Docker preexistentes, las bases de datos SQLite históricas y el informe original de Locust.

---

## 3. Dimensión 1 — Esfuerzo y Consumo

La telemetría agregada de la sesión se resume bajo la taxonomía de la guía de estandarización. Los valores que no fueron exportados de forma independiente por el CLI en esta sesión se registran formalmente como no disponibles (N/D), evitando imputar ceros artificiales.

| Indicador Estandarizado | Unidad | Valor Observado Etapa 3 |
|---|---|---:|
| Interacciones documentadas | # | **23** |
| Prompts humanos de control / hitos | # | **10** |
| Solicitudes de modelo (Turns) | # | **N/D** |
| Tok In (incluye caché) | Tokens | **N/D** |
| Tok Cache | Tokens | **N/D** |
| Tok In sin caché (derivado) | Tokens | **N/D** |
| Tok Out | Tokens | **N/D** |
| Tool Calls totales | # | **N/D** |
| Llamadas a herramientas exitosas | # | **N/D** |
| Llamadas a herramientas fallidas | # | **N/D** |
| Tiempo activo del agente | Segundos | **N/D** |
| Tiempo de pared (Wall clock) | Segundos | **N/D** |
| Costo financiero atribuible | USD | **N/D** |

*Nota metodológica:* El registro detallado de interacciones en E3_TESSL_REGISTRO_01_INTERACCIONES.md documenta las 23 fases de diálogo, diagnósticos, ejecuciones y verificaciones de la etapa.

---

## 4. Dimensión 2 — Calidad del Código Generado (SonarQube y Pruebas)

### 4.1. Evolución Longitudinal SonarQube en la Etapa 3

Se mantuvieron cuatro mediciones formales registradas de forma independiente para aislar el impacto de la ingesta de cobertura respecto a la remediación de código:

| Métrica | Clave SonarQube | 1. Línea Base Original (cee9b875) | 2. Línea Base + Cobertura (cce34118) | 3. Post-Remediación (c9aa6430) | 4. Cierre Focalizado (e560df70) | Variación Neta (4 vs 2) |
|---|---|---:|---:|---:|---:|---:|
| **Quality Gate** | lert_status | **OK** (0 cond.) | **OK** (0 cond.) | **ERROR** (3 cond.) | **ERROR** (3 cond.) | CAYC diferencial activo |
| **Bugs tradicionales** | ugs | **12** | **12** | **0** | **0** | **-12 (-100,0 %)** |
| **Vulnerabilidades** | ulnerabilities | **2** | **2** | **0** | **0** | **-2 (-100,0 %)** |
| **Code Smells** | code_smells | **71** | **71** | **73** | **72** | **+1 (+1,4 %)** |
| **Total Defectos Abiertos** | *bugs+vuln+smells* | **85** | **85** | **73** | **72** | **-13 (-15,3 %)** |
| **Defectos Resueltos (Closed/Fixed)** | *closed_fixed* | 0 | 0 | 14 | **16** | **+16** |
| **Deuda Técnica** | sqale_index | 450 min | 450 min | 496 min | **491 min** | +41 min (+9,1 %) |
| **Ratio de Deuda Técnica** | sqale_debt_ratio | 0,3 % | 0,3 % | 0,3 % | **0,3 %** | 0,0 pp |
| **Rating Fiabilidad** | 
eliability_rating | 4.0 (D) | 4.0 (D) | **1.0 (A)** | **1.0 (A)** | -3.0 (Mejora a A) |
| **Rating Seguridad** | security_rating | 2.0 (B) | 2.0 (B) | **1.0 (A)** | **1.0 (A)** | -1.0 (Mejora a A) |
| **Rating Mantenibilidad** | sqale_rating | 1.0 (A) | 1.0 (A) | 1.0 (A) | **1.0 (A)** | 0.0 |
| **Complejidad Cognitiva** | cognitive_complexity | 585 | 585 | 624 | **624** | +39 (+6,7 %) |
| **Complejidad Ciclomática** | complexity | 697 | 697 | 712 | **712** | +15 (+2,2 %) |
| **LOC no comentadas (
cloc)** | 
cloc | 5.507 | 5.507 | 5.533 | **5.536** | +29 (+0,5 %) |
| **Líneas totales (lines)** | lines | 6.630 | 6.630 | 6.667 | **6.668** | +38 (+0,6 %) |
| **Sentencias (statements)** | statements | 1.951 | 1.951 | 1.973 | **1.973** | +22 (+1,1 %) |
| **Funciones (unctions)** | unctions | 233 | 233 | 234 | **234** | +1 (+0,4 %) |
| **Densidad Comentarios** | comment_lines_density | 5,9 % | 5,9 % | 6,0 % | **5,9 %** | 0,0 pp |
| **Duplicación líneas** | duplicated_lines_density | 0,6 % | 0,6 % | 0,6 % | **0,6 %** | 0,0 pp |
| **Security Hotspots** | security_hotspots | 0 | 0 | 0 | **0** | 0 |
| **Cobertura general** | coverage | **0,0 %** | **78,0 %** | **77,7 %** | **77,9 %** | **-0,1 pp** |
| **Cobertura de líneas** | line_coverage | — | 78,5 % | 78,2 % | **78,4 %** | -0,1 pp |
| **Cobertura de ramas** | ranch_coverage | — | 69,3 % | 69,3 % | **69,3 %** | 0,0 pp |
| **Cobertura en código nuevo** | 
ew_coverage | — | — | 52,9 % | **70,6 %** | **+17,7 pp** |

### 4.2. Métricas MQR (Clean Code)
- **Fiabilidad MQR:** 28 incidencias, Rating C (3.0), frente a 40 incidencias y Rating D inicial (-12 incidencias de fiabilidad eliminadas).
- **Seguridad MQR:** 0 incidencias, Rating A (1.0), frente a 2 incidencias y Rating B inicial (-2 vulnerabilidades eliminadas).
- **Mantenibilidad MQR:** 64 incidencias, Rating A (1.0).

### 4.3. Verificación de Pruebas Automatizadas y Compilación
- **Pruebas de Backend (Pytest):** 86 pruebas ejecutadas, **86 aprobadas (100 % de éxito)**.
- **Pruebas de Frontend (Vitest):** 7 suites, 39 pruebas ejecutadas, **39 aprobadas (100 % de éxito)**.
- **Total Pruebas Automatizadas:** **125 pruebas aprobadas**.
- **Compilación de Producción:** Vite + TypeScript compiló con **0 errores de tipo**.
- **Pruebas de Carga (Locust):** 100 usuarios concurrentes, 1.280 peticiones, p95 12,8 ms (< 200 ms SLA), 0,0 % errores (< 1,0 % SLA).
- **Pruebas de Despliegue en Vivo:** 9/9 pruebas de humo en contenedores Nginx/FastAPI HTTPS aprobadas.

---

## 5. Dimensión 3 — Especificaciones

Se consolidaron **11 especificaciones .spec.md**, distribuidas entre 7 especificaciones funcionales heredadas y evolucionadas de Etapas 1 y 2, y 4 nuevas especificaciones de arquitectura empresarial para la Etapa 3:

| Especificación (.spec.md) | Origen | Líneas Físicas | Bytes | Requerimientos | Etiquetas [@test] |
|---|---|---:|---:|---:|---:|
| ccounts.spec.md | E1 (Inalterado) | 53 | 2.285 | 13 | 9 |
| 	ransfers.spec.md | E1/E2 (Evolucionado) | 92 | 4.714 | 24 | 23 |
| 	ransactions.spec.md | E1 (Inalterado) | 53 | 2.414 | 13 | 9 |
| mfa.spec.md | E1 (Evolucionado) | 78 | 3.972 | 23 | 25 |
| ch_transfers.spec.md | E2 (Evolucionado E3) | 157 | 8.463 | 44 | 41 |
| 
ecurring_payments.spec.md | E2 (Evolucionado E3) | 140 | 8.298 | 40 | 35 |
| 	ransfer_limits.spec.md | E2 (Inalterado) | 71 | 3.791 | 20 | 16 |
| encryption.spec.md | E3 (Nuevo) | 137 | 10.269 | 44 | 27 |
| udit_log.spec.md | E3 (Nuevo) | 117 | 9.049 | 38 | 29 |
| load_testing.spec.md | E3 (Nuevo) | 83 | 6.260 | 26 | 17 |
| deployment.spec.md | E3 (Nuevo) | 112 | 5.865 | 38 | 17 |
| **Total** | | **1.093** | **65.380** | **323** | **248** |

### Métricas Estandarizadas de Especificación:
- **Total Archivos Spec:** 11 archivos (+4 vs. E2).
- **Líneas de Especificación:** 1.093 líneas (+518 líneas, +90,1 % vs. E2).
- **Densidad de Especificación:** 99,36 líneas / archivo (vs. 82,14 en E2).
- **Ratio Código / Especificación (C/E):** 5.536 ncloc / 1.093 líneas spec = **5,06** (vs. 7,42 en E2 y 9,05 en E1).
- **Cláusulas de Requerimiento:** 323 cláusulas.
- **Densidad Requerimientos por Spec:** 29,36 req / spec.
- **Req / CLOD (Requerimientos por 100 líneas spec):** (323 / 1.093) * 100 = **29,55**.
- **Distribución de líneas spec (ordenada):** [53, 53, 71, 78, 83, 92, 112, 117, 137, 140, 157].
  - Mínimo: 53 | Q1: 74,5 | Mediana: 92 | Q3: 127 | Máximo: 157.

---

## 6. Dimensión 4 — Requisitos Funcionales y Cumplimiento

Las cuatro capacidades solicitadas en la semilla común SEED-3.md fueron formalizadas e implementadas con verificación exhaustiva:

1. **Cifrado extremo a extremo de datos bancarios sensibles:**  
   - *Especificación:* specs/encryption.spec.md.  
   - *Implementación:* Cifrado híbrido cliente-servidor mediante RSA-OAEP (SHA-256) y AES-256-GCM en rontend/src/api/crypto.ts y ackend/app/services/crypto_service.py. Cifrado en reposo con prefijo enc:v1:. Migración idempotente y atómica en migration_service.py.  
   - *Evidencia:* 15 pruebas en 	est_encryption.py y 4 pruebas en crypto.test.ts. 100% aprobadas.
2. **Registros inmutables de auditoría:**  
   - *Especificación:* specs/audit_log.spec.md.  
   - *Implementación:* Tabla udit_log encadenada criptográficamente con HMAC-SHA256 desde bloque Génesis (udit_service.py). Triggers SQLite de prevención de UPDATE/DELETE. Endpoint protegido GET /api/audit/verify con cabecera X-Admin-Key. Garantía transaccional fail-closed.  
   - *Evidencia:* 17 pruebas automatizadas en 	est_audit_log.py. 100% aprobadas.
3. **Pruebas de carga del sistema:**  
   - *Especificación:* specs/load_testing.spec.md.  
   - *Implementación:* Carga distribuida con Locust (locustfile.py) simulando 100 usuarios en proporción 70/20/10 sobre base SQLite aislada (	est_load.db).  
   - *Evidencia:* Reporte formal en load_benchmark_report.json verificado por 	est_load_performance.py. SLA cumplido con holgura (p95 12,8 ms << 200 ms, error 0,0 % << 1,0 %).
4. **Despliegue de la aplicación:**  
   - *Especificación:* specs/deployment.spec.md.  
   - *Implementación:* docker-compose.yml, ackend/Dockerfile (usuario no-root ppuser, UID 1000), rontend/Dockerfile (usuario no-root 
ginx), 
ginx/nginx.conf (reverse proxy TLS en puerto 8443, redirección HTTP en 8080), script generate_certs.py. Secretos obligatorios sin valores por defecto.  
   - *Evidencia:* 9 pruebas en 	est_deployment_config.py y 9 pruebas en vivo HTTPS en 	est_live_deployment_smoke.py. 100% aprobadas.

---

## 7. Dimensión 5 — Retroalimentación Humana y Hallazgos Remanentes

### 7.1. Intervenciones Humanas y Bloqueadores Resueltos
1. **Desbloqueo de Credencial SonarQube (Interacción 19-20):**  
   El análisis inicial fue rechazado con HTTP 401 por ausencia de token en la sesión. El operador configuró SONAR_TOKEN, permitiendo reanudar la medición sin exponer credenciales.
2. **Remediación de Prioridad (Interacción 20):**  
   El operador autorizó la resolución de los 12 bugs críticos python:S5779 en migration_service.py, la eliminación de secretos por defecto en Docker Compose (H12), el paso a usuarios no-root en contenedores (H11/docker:S6471) y la reproducibilidad TLS en clones limpios (H13).
3. **Cierre Focalizado (Interacción 22):**  
   Se corrigieron las 2 incidencias introducidas por el hardening (docker:S7031 y python:S8997), ambas verificadas como CLOSED / FIXED.

### 7.2. Hallazgos Remanentes y Calidad Estática
- **72 Code Smells Abiertos:** 71 corresponden a código heredado o preexistente de etapas previas (TypeScript typing, convenciones React, docstrings Python y complejidad cognitiva preexistente), deliberadamente no modificados para preservar el aislamiento experimental.
- **1 Violación Nueva:** python:S9073 en ackend/tests/test_encryption.py:348 (anotación de tipo en función auxiliar de prueba).
- **Quality Gate en ERROR:** La cobertura sobre código nuevo alcanzó 70,6 % frente al umbral del 80,0 %. No se aplicaron exclusiones artificiales ni se modificaron umbrales del Quality Gate.

---

## 8. Advertencia Metodológica sobre Base de Datos

Se ratifica la observación metodológica registrada: el archivo temporal SQLite shift_bank.db-shm mostró una actualización de timestamp durante las pruebas de integración locales previas. Por consiguiente, la no-modificación histórica de los archivos de base de datos no puede ser garantizada de forma estrictamente independiente mediante metadatos del sistema de archivos. La base de datos principal shift_bank.db conservó exactamente sus 155.648 bytes intactos.

---

## 9. Conclusiones

Shift Bank Stage 3 (Tessl SDD) concluyó exitosamente su ciclo experimental, demostrando la capacidad del enfoque basado en especificaciones para orquestar requisitos avanzados de ciberseguridad, infraestructura y auditoría. La combinación de 125 pruebas automatizadas al 100% de éxito, 0 bugs, 0 vulnerabilidades y 77,9% de cobertura consolida una base ejecutable de alta fiabilidad, documentando de forma transparente las limitaciones y el estado diferencial del Quality Gate.
