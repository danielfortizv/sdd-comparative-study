# Reporte de Cierre de Calidad Focalizado SonarQube — Shift Bank Etapa 3 (Tessl)

**Fecha de medición:** 13 de noviembre de 2026  
**Fase:** Cierre de calidad focalizado (Stage 3 — Tessl SDD)  
**Proyecto:** Shift Bank — Stage 3 — Tessl  
**Project Key:** `Shift-Bank---Stage-3---Tessl`  
**Servidor SonarQube:** `http://localhost:9000` (Community Build v26.9.0.129388, Status: UP)  
**Versión de SonarScanner:** 5.1.0 (`sonarqube-scanner` via npx)  
**ID de Tarea Compute Engine:** `0d1878fc-b371-4278-8c77-3f7aebcdb1d2`  
**ID de Análisis:** `e560df70-7dc9-427e-84e3-101ed77cba13`  
**Estado del Procesamiento:** `SUCCESS`  
**Tiempo de Ejecución:** Scanner: 16.870 s | Compute Engine: 1.294 ms  

---

## 1. Evolución Longitudinal de Métricas en la Etapa 3 (Tessl)

| Métrica | Clave SonarQube | 1. Línea Base Original (`cee9b875`) | 2. Línea Base + Cobertura (`cce34118`) | 3. Post-Remediación (`c9aa6430`) | 4. Cierre Focalizado (`e560df70`) | Variación Neta (4 vs 2) |
|---|---|---:|---:|---:|---:|---:|
| **Quality Gate** | `alert_status` | **OK** (0 cond.) | **OK** (0 cond.) | **ERROR** (3 cond.) | **ERROR** (3 cond.) | Cambio régimen CAYC |
| **Bugs tradicionales** | `bugs` | **12** | **12** | **0** | **0** | **-12 (-100%)** |
| **Vulnerabilidades tradicionales** | `vulnerabilities` | **2** | **2** | **0** | **0** | **-2 (-100%)** |
| **Code Smells tradicionales** | `code_smells` | **71** | **71** | **73** | **72** | **+1 (+1,4%)** |
| **Total Defectos Abiertos** | *bugs+vuln+smells* | **85** | **85** | **73** | **72** | **-13 (-15,3%)** |
| **Defectos Cerrados/Fijados** | *closed_fixed* | 0 | 0 | 14 | **16** | **+16** |
| **Deuda Técnica** | `sqale_index` | 450 min | 450 min | 496 min | **491 min** | +41 min (+9,1%) |
| **Ratio Deuda Técnica** | `sqale_debt_ratio` | 0,3 % | 0,3 % | 0,3 % | **0,3 %** | 0,0 pp |
| **Rating Fiabilidad** | `reliability_rating` | 4.0 (D) | 4.0 (D) | **1.0 (A)** | **1.0 (A)** | -3.0 (Mejora a A) |
| **Rating Seguridad** | `security_rating` | 2.0 (B) | 2.0 (B) | **1.0 (A)** | **1.0 (A)** | -1.0 (Mejora a A) |
| **Rating Mantenibilidad** | `sqale_rating` | 1.0 (A) | 1.0 (A) | 1.0 (A) | **1.0 (A)** | 0.0 |
| **Complejidad Cognitiva** | `cognitive_complexity` | 585 | 585 | 624 | **624** | +39 (+6,7%) |
| **Complejidad Ciclomática** | `complexity` | 697 | 697 | 712 | **712** | +15 (+2,2%) |
| **Líneas de código (ncloc)** | `ncloc` | 5.507 | 5.507 | 5.533 | **5.536** | +29 (+0,5%) |
| **Líneas totales** | `lines` | 6.630 | 6.630 | 6.667 | **6.668** | +38 (+0,6%) |
| **Sentencias** | `statements` | 1.951 | 1.951 | 1.973 | **1.973** | +22 (+1,1%) |
| **Funciones** | `functions` | 233 | 233 | 234 | **234** | +1 (+0,4%) |
| **Duplicación líneas** | `duplicated_lines_density` | 0,6 % | 0,6 % | 0,6 % | **0,6 %** | 0,0 pp |
| **Security Hotspots** | `security_hotspots` | 0 | 0 | 0 | **0** | 0 |
| **Cobertura general** | `coverage` | **0,0 %** | **78,0 %** | **77,7 %** | **77,9 %** | **-0,1 pp** |
| **Cobertura de líneas** | `line_coverage` | — | 78,5 % | 78,2 % | **78,4 %** | -0,1 pp |
| **Cobertura de ramas** | `branch_coverage` | — | 69,3 % | 69,3 % | **69,3 %** | 0,0 pp |
| **Cobertura en código nuevo** | `new_coverage` | — | — | 52,9 % | **70,6 %** | **+17,7 pp** |

---

## 2. Correcciones Focalizadas de Mantenibilidad

En cumplimiento de la directiva de corrección focalizada:
1. **`docker:S7031` en `backend/Dockerfile`:**  
   - **Estado:** **CLOSED / FIXED**.  
   - **Solución:** Se unificaron las instrucciones consecutivas `RUN apt-get ...` y `RUN groupadd ... useradd ...` en una única directiva `RUN` encadenada con `&&`, optimizando las capas de la imagen Docker.
2. **`python:S8997` en `backend/tests/test_deployment_config.py`:**  
   - **Estado:** **CLOSED / FIXED**.  
   - **Solución:** Se adaptó la prueba para utilizar el fixture estándar de Pytest `monkeypatch.syspath_prepend(WORKSPACE_ROOT)` en lugar de mutar manualmente `sys.path` global.

---

## 3. Ampliación de Pruebas Automatizadas de Comportamiento Nuevo

Se incorporaron 7 nuevas pruebas automatizadas significativas para cubrir rutas de ejecución introducidas durante el hardening:
1. **Validación de Secretos de Inicio (FastAPI Lifespan y Criptografía):**
   - `test_validate_admin_key_at_startup_enforcement`: Comprueba que el inicio aborte con `RuntimeError` si `ADMIN_SECRET_KEY` está ausente en modo de producción, y proceda cuando está presente.
   - `test_validate_encryption_key_at_startup_enforcement`: Comprueba que el inicio aborte si `ENCRYPTION_KEY` falta o es menor a 32 bytes.
   - `test_validate_audit_key_at_startup_enforcement`: Comprueba que el inicio aborte si `AUDIT_SECRET_KEY` falta o es menor a 16 bytes.
2. **Generación e Idempotencia de Certificados TLS:**
   - `test_generate_development_certificates_fresh_and_idempotent`: Verifica la generación de certificados X.509 RSA-2048 en directorios temporales limpios y comprueba que ejecuciones sucesivas preserven los archivos existentes sin sobreescribir.
3. **Manejo de Errores de Verificación y Rollback en Migración:**
   - `test_migration_verification_detects_unencrypted_routing_and_rolls_back`: Valida que coordenadas de ruta no cifradas activen `MigrationVerificationError` y ejecuten rollback atómico.
   - `test_migration_verification_detects_corrupt_account_length_and_rolls_back`: Valida la detección de longitudes corruptas en cuentas descifradas.
   - `test_migration_verification_detects_unencrypted_transfer_record`: Valida la detección de coordenadas no cifradas en transferencias ACH.

**Estado total de la suite:** **125 pruebas automatizadas (86 backend + 39 frontend), 100% aprobadas.**

---

## 4. Evaluación del Quality Gate y Causas Remanentes de ERROR

El estado final del Quality Gate permanece en **ERROR** bajo las reglas Clean as You Code (CAYC):
- **Causa 1 — Cobertura en código nuevo (`new_coverage`):**  
  - **Resultado actual:** **70,6 %** (frente al umbral requerido de **80,0 %**, déficit de 9,4 pp).  
  - Aunque la cobertura aumentó significativamente (+17,7 pp respecto a 52,9%), ciertas ramas defensivas de excepción extrema en `migration_service.py` (p. ej. validación de cronogramas recurrentes) y rutas de error en `main.py` no son transitadas en pruebas nominales.
- **Causa 2 — Nuevas incidencias (`new_violations`):**  
  - **Resultado actual:** **1 incidencia** (frente al umbral de 0).  
  - Corresponde a `python:S9073` (falta de anotación de tipo en una función auxiliar de prueba en `backend/tests/test_encryption.py:348`).
- **Causa 3 — Duplicación en código nuevo:** **0,0 %** (Cumple umbral <= 3,0 % -> **OK**).

### Principio de Integridad Metodológica:
En estricta observancia de las directivas:
- **No se debilitaron reglas bancarias.**
- **No se excluyeron archivos artificialmente del reporte de cobertura.**
- **No se modificaron los umbrales del Quality Gate** en SonarQube para forzar un estado "OK".
- **No se inició un ciclo de remediación sin restricciones.** Se reportan las causas de forma transparente y objetiva.

---

## 5. Preservación y Advertencias

- Se conservan inalterados todos los reportes previos (`E3_TESSL_SONARQUBE_BASELINE.md`, `E3_TESSL_SONARQUBE_COVERAGE_BASELINE.md`, `E3_TESSL_SONARQUBE_POST_REMEDIATION.md`).
- La advertencia sobre el archivo temporal SQLite `shift_bank.db-shm` se mantiene registrada: la no-modificación histórica no puede ser garantizada de forma estrictamente independiente mediante marcas de tiempo del sistema de archivos, si bien `shift_bank.db` permaneció con 155.648 bytes intactos.
- Las Etapas 1 y 2, volúmenes de Docker y el reporte Locust histórico no fueron modificados.
