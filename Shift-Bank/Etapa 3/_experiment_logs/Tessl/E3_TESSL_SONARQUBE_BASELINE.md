# Reporte de Línea Base SonarQube — Shift Bank Etapa 3 (Tessl)

**Fecha de medición:** 13 de noviembre de 2026  
**Fase:** Medición de línea base SonarQube (Stage 3 — Tessl SDD)  
**Proyecto:** Shift Bank — Stage 3 — Tessl  
**Project Key:** `Shift-Bank---Stage-3---Tessl`  
**Servidor SonarQube:** `http://localhost:9000`  
**Versión del Servidor SonarQube:** 26.9.0.129388 (Status: UP)  
**Versión de SonarScanner:** 5.1.0 (`sonarqube-scanner` via npx)  
**ID de Tarea Compute Engine:** `fe154f2f-4fc1-4375-9876-c9e4c40aa7f8`  
**ID de Análisis:** `cee9b875-e572-42de-998f-36be6fbeabd6`  
**Estado del Procesamiento:** `SUCCESS`  
**Tiempo de Ejecución:** Scanner: 20.485 s | Compute Engine: 1.801 ms  
**Autenticación:** Variable de entorno `SONAR_TOKEN` configurada y validada en sesión (longitud: 44 caracteres, valor protegido sin divulgar ni persistir)

---

## 1. Alcance del Análisis y Configuración

El análisis se ejecutó estrictamente con la configuración existente en `sonar-project.properties` ubicado en la raíz del proyecto `Shift-Bank/Etapa 3/Tessl`:

```properties
sonar.projectKey=Shift-Bank---Stage-3---Tessl
sonar.projectName=Shift Bank - Stage 3 - Tessl
sonar.projectVersion=3.0.0

sonar.host.url=http://localhost:9000

# Production Source Scope
sonar.sources=backend/app,frontend/src,docker-compose.yml,backend/Dockerfile,frontend/Dockerfile,nginx/nginx.conf

# Test Scope
sonar.tests=backend/tests,frontend/src/__tests__
sonar.test.inclusions=backend/tests/**,frontend/src/__tests__/**

# Exclusions: builds, dependencies, databases, certificates, secrets, experiment logs, benchmark artifacts, and specs
sonar.exclusions=**/__pycache__/**,**/node_modules/**,**/dist/**,frontend/dist/**,**/*.db*,nginx/certs/**,.env*,.pytest_cache/**,backend/tests/load/load_benchmark_report.json,**/_experiment_logs/**,specs/**

# Source Encoding
sonar.sourceEncoding=UTF-8
```

### Estadísticas de Indexación
- **Archivos indexados totales:** 66 archivos.
- **Archivos fuente analizados:** 40 archivos de código fuente de producción.
- **Archivos de pruebas indexados:** 26 archivos de pruebas.
- **Distribución de líneas de código por lenguaje (`ncloc`):**
  - Python: 2.475 líneas (44,9 %)
  - TypeScript: 2.315 líneas (42,0 %)
  - CSS: 693 líneas (12,6 %)
  - Docker: 24 líneas (0,4 %)
  - **Total `ncloc`:** 5.507 líneas

---

## 2. Resultados Cuantitativos — Métricas Estáticas Oficiales

Las siguientes métricas fueron extraídas directamente de la API de SonarQube (`/api/measures/component` y `/api/qualitygates/project_status`) tras procesarse el análisis:

| Métrica | Clave API SonarQube | Valor Observado | Escala / Detalle |
|---|---|---:|---|
| **Quality Gate** | `alert_status` | **OK** | 0 condiciones configuradas (`caycStatus: compliant`) |
| **Líneas totales** | `lines` | **6.630** | Incluye comentarios y líneas en blanco |
| **Líneas de código no comentadas** | `ncloc` | **5.507** | Código de producción analizado |
| **Sentencias** | `statements` | **1.951** | Instrucciones evaluables |
| **Funciones** | `functions` | **233** | Funciones y métodos |
| **Líneas de comentarios** | `comment_lines` | **348** | Densidad de comentarios: 5,9 % |
| **Bugs (API clásica)** | `bugs` | **12** | Calificación: **D** (`reliability_rating: 4.0`) |
| **Vulnerabilidades (API clásica)** | `vulnerabilities` | **2** | Calificación: **B** (`security_rating: 2.0`) |
| **Code Smells (API clásica)** | `code_smells` | **71** | Calificación: **A** (`sqale_rating: 1.0`) |
| **Total Defectos Detectados** | *bugs + vuln + smells* | **85** | Severidad: 22 Critical, 33 Major, 30 Minor |
| **Deuda Técnica** | `sqale_index` | **450 min** | Estimación de remediación: 7,5 horas |
| **Ratio de Deuda Técnica** | `sqale_debt_ratio` | **0,3 %** | Esfuerzo de remediación vs. costo de desarrollo |
| **Complejidad Cognitiva** | `cognitive_complexity` | **585** | Dificultad acumulada de entendimiento de flujo |
| **Complejidad Ciclomática** | `complexity` | **697** | Rutas independientes de ejecución |
| **Duplicación de líneas** | `duplicated_lines_density` | **0,6 %** | 40 líneas duplicadas en 2 bloques (2 archivos) |
| **Security Hotspots** | `security_hotspots` | **0** | Ningún punto caliente de seguridad reportado |
| **Cobertura reportada en SonarQube** | `coverage` | **0,0 %** | Cobertura no importada en la configuración del scanner |

### Clasificación bajo el Modelo MQR (Clean Code)
- **Fiabilidad (Reliability):** 40 incidencias, Rating **D** (4.0).
- **Seguridad (Security):** 2 incidencias, Rating **B** (2.0).
- **Mantenibilidad (Maintainability):** 62 incidencias, Rating **A** (1.0).
- **Security Hotspots:** 0 incidencias.

---

## 3. Detalle Exhaustivo de Incidencias Detectadas (Pre-remediación)

### 3.1. Bugs (12 incidencias — Severidad CRITICAL)
Todas las 12 incidencias de bugs se originan en el servicio de migración de bases de datos bajo la regla `python:S5779`:
- **Regla:** `python:S5779` — *"Don't use assert inside a try-except that catches AssertionError"*.
- **Ubicación:** `backend/app/services/migration_service.py`.
- **Líneas afectadas:** 140, 142, 145, 147, 156, 158, 161, 163, 172, 174, 177, 179.
- **Impacto:** El uso de aserciones dentro de bloques `try-except AssertionError` como mecanismo de flujo puede ser eludido si Python se ejecuta en modo optimizado (`-O`), afectando la verificación estructural de las migraciones.

### 3.2. Vulnerabilidades (2 incidencias — Severidad MINOR)
Las 2 vulnerabilidades detectadas corresponden a la configuración de contenedores Docker bajo la regla `docker:S6471`:
- **Regla:** `docker:S6471` — *"The image runs with 'root' as the default user. Make sure it is safe here"*.
- **Archivos afectados:**
  1. `backend/Dockerfile` (Línea 1): Imagen base `python:3.11-slim` ejecutándose como usuario `root`.
  2. `frontend/Dockerfile` (Línea 14): Imagen base `nginx:alpine` ejecutándose como usuario `root`.
- **Impacto:** Principio de menor privilegio en ejecución de contenedores.

### 3.3. Code Smells (71 incidencias — 10 CRITICAL, 33 MAJOR, 28 MINOR)
Los 10 Code Smells de severidad CRITICAL abarcan:
1. **Complejidad Cognitiva excesiva (`python:S3776` / `typescript:S3776` > 15):**
   - `backend/app/services/audit_service.py` (Línea 51)
   - `backend/app/services/crypto_service.py` (Línea 249)
   - `backend/app/services/migration_service.py` (Línea 19)
   - `backend/app/services/recurring_service.py` (Línea 24)
   - `backend/app/services/transfer_service.py` (Línea 150)
   - `frontend/src/components/TransferModal.tsx` (Línea 94)
2. **Duplicación de cadenas literales (`python:S1192`):**
   - `backend/app/models.py` (Líneas 44, 53, 84)
   - `backend/app/services/migration_service.py` (Línea 45)

**Distribución global de los 71 Code Smells por regla:**
- `typescript:S7773` (14): Type annotations y typing practices en TypeScript.
- `typescript:S6853` (9): Mejores prácticas en React / JSX.
- `python:S8410` (8): Convenciones de estilo y typing en Python.
- `typescript:S6819` (5): Uso de efectos y hooks en React.
- `python:S3776` (5): Complejidad cognitiva en servicios de backend.
- `python:S9073` (5): Manejo de excepciones y tipos.
- `python:S1192` (4): Cadenas literales duplicadas sin constante.
- `typescript:S6772` (3): Manipulación de promesas y estado.
- `typescript:S7758` (2): Parámetros y tipado.
- `typescript:S6660` (2): Optimización de renderizado.
- `python:S9117` (2): Uso de retornos en funciones.
- `python:S8572` (2): Formato de docstrings y tipos.
- `typescript:S3358` (2): Operadores ternarios anidados.
- `python:S5778` (2): Prácticas en tests y excepciones.
- `typescript:S3776` (1): Complejidad cognitiva en componente modal frontend.
- `css:S7924` (1): Propiedades CSS en desuso o sintaxis de fuentes.
- `python:S3457` (1): Formato de strings.
- `python:S1481` (1): Variables no utilizadas.
- `typescript:S1871` (1): Ramas condicionales idénticas.
- `typescript:S5906` (1): Accesibilidad en componentes interactivos.

---

## 4. Evidencia de Cobertura y Distinción Metodológica

En estricto cumplimiento con la directiva de la fase:
> *"Attempt coverage generation with compatible temporary tooling, without modifying application dependency manifests. Clearly distinguish unavailable coverage from measured 0% coverage."*

### 4.1. Cobertura en la API de SonarQube (`coverage = 0.0%`)
El valor `0.0%` reflejado en el dashboard de SonarQube obedece exclusivamente a que el archivo estándar `sonar-project.properties` no contiene parámetros de ingesta de reportes (`sonar.python.coverage.reportPaths` ni `sonar.javascript.lcov.reportPaths`). Por tanto, este número **no representa una ausencia de pruebas**, sino una **cobertura no importada** por diseño de la configuración base.

### 4.2. Medición Real con Herramientas Temporales Compatibles
Sin modificar los manifiestos de dependencias de la aplicación (`backend/requirements.txt` y `frontend/package.json` se preservaron intactos), se ejecutó la suite de pruebas automatizadas con herramientas de cobertura compatibles en el entorno local:

#### A. Backend (Python 3.13.2 / pytest 9.1.1 con pytest-cov 7.1.0)
- **Pruebas ejecutadas:** 79 pruebas en 11 archivos de prueba.
- **Resultado de pruebas:** 79 aprobadas, 0 fallidas (100% éxito en 5,21 s).
- **Sentencias totales analizadas:** 1.589 sentencias.
- **Sentencias no cubiertas:** 122 sentencias.
- **Cobertura real de sentencias medida:** **92 %**.
- **Desglose por módulo:**
  - `backend/app/database.py`: 80% (20 stmts, 4 miss)
  - `backend/app/main.py`: 98% (48 stmts, 1 miss)
  - `backend/app/models.py`: 99% (145 stmts, 2 miss)
  - `backend/app/routers/accounts.py`: 100% (13 stmts, 0 miss)
  - `backend/app/routers/audit.py`: 95% (22 stmts, 1 miss)
  - `backend/app/routers/beneficiaries.py`: 100% (32 stmts, 0 miss)
  - `backend/app/routers/crypto.py`: 100% (13 stmts, 0 miss)
  - `backend/app/routers/limits.py`: 100% (13 stmts, 0 miss)
  - `backend/app/routers/recurring.py`: 100% (27 stmts, 0 miss)
  - `backend/app/routers/transactions.py`: 100% (10 stmts, 0 miss)
  - `backend/app/routers/transfers.py`: 100% (20 stmts, 0 miss)
  - `backend/app/schemas.py`: 98% (265 stmts, 5 miss)
  - `backend/app/services/account_service.py`: 100% (49 stmts, 0 miss)
  - `backend/app/services/audit_service.py`: 88% (165 stmts, 19 miss)
  - `backend/app/services/crypto_service.py`: 74% (172 stmts, 45 miss)
  - `backend/app/services/limit_service.py`: 90% (49 stmts, 5 miss)
  - `backend/app/services/mfa_service.py`: 80% (51 stmts, 10 miss)
  - `backend/app/services/migration_service.py`: 95% (128 stmts, 6 miss)
  - `backend/app/services/recurring_service.py`: 91% (171 stmts, 15 miss)
  - `backend/app/services/scheduler.py`: 93% (28 stmts, 2 miss)
  - `backend/app/services/transfer_service.py`: 95% (148 stmts, 7 miss)

#### B. Frontend (Vitest 1.6.1 con @vitest/coverage-v8@1.6.1 temporal)
- Se utilizó la versión `@vitest/coverage-v8@1.6.1` perfectamente compatible con `vitest@1.6.1`, instalada de forma efímera con `--no-save --no-package-lock` para no alterar `package.json` ni `package-lock.json`.
- **Pruebas ejecutadas:** 39 pruebas en 7 suites de prueba.
- **Resultado de pruebas:** 39 aprobadas, 0 fallidas (100% éxito en 2,05 s).
- **Cobertura real medida:**
  - **Sentencias (`% Stmts`):** **69,13 %**
  - **Ramas (`% Branch`):** **69,29 %**
  - **Funciones (`% Funcs`):** **57,14 %**
  - **Líneas (`% Lines`):** **69,13 %**
- **Desglose por componentes clave:**
  - `src/api/crypto.ts`: 100% Stmts / 100% Lines / 85% Branch
  - `src/components/AccountSummary.tsx`: 96,61% Stmts / 93,75% Branch
  - `src/components/MfaModal.tsx`: 100% Stmts / 69,23% Branch
  - `src/components/TransactionHistory.tsx`: 96,68% Stmts / 87,50% Branch
  - `src/components/TransferLimits.tsx`: 96,13% Stmts / 56,25% Branch
  - `src/components/TransferModal.tsx`: 90,16% Stmts / 68,05% Branch
  - `src/components/RecurringPayments.tsx`: 73,58% Stmts / 60,46% Branch

#### C. Resumen de Calidad de Pruebas
- Total de pruebas automatizadas: **118 pruebas** (79 backend + 39 frontend).
- Tasa de éxito: **100 %**.
- Conclusión: Existe una cobertura sustancial de código (92% backend, 69% frontend), confirmando que el `0.0%` en SonarQube refleja una limitación de ingesta documental del scanner y no una carencia de validación automatizada.

---

## 5. Comparación Longitudinal (Etapa 1 vs. Etapa 2 vs. Etapa 3 Tessl)

| Métrica | Etapa 1 Final | Etapa 2 Inicial | Etapa 3 Línea Base | Variación E3 vs E2 | Variación E3 vs E1 |
|---|---:|---:|---:|---:|---:|
| **LOC SonarQube (`ncloc`)** | 2.182 | 4.230 | **5.507** | +1.277 (+30,2%) | +3.325 (+152,4%) |
| **Líneas totales (`lines`)** | 2.585 | 4.966 | **6.630** | +1.664 (+33,5%) | +4.045 (+156,5%) |
| **Bugs tradicionales** | 0 | 0 | **12** | +12 | +12 |
| **Vulnerabilidades tradicionales** | 0 | 0 | **2** | +2 | +2 |
| **Code Smells tradicionales** | 21 | 51 | **71** | +20 (+39,2%) | +50 (+238,1%) |
| **Total Defectos Detectados** | **21** | **51** | **85** | **+34 (+66,7%)** | **+64 (+304,8%)** |
| **Deuda Técnica (`sqale_index`)** | 82 min | 276 min | **450 min** | +174 min (+63,0%) | +368 min (+448,8%) |
| **Complejidad Cognitiva** | 98 | 329 | **585** | +256 (+77,8%) | +487 (+496,9%) |
| **Complejidad Ciclomática** | — | — | **697** | — | — |
| **Duplicación de líneas** | 0,0 % | 0,8 % | **0,6 %** | -0,2 pp | +0,6 pp |
| **Densidad Code Smells (x 1.000 ncloc)** | 9,62 | 12,06 | **12,89** | +0,83 | +3,27 |
| **Densidad Total Defectos (x 1.000 ncloc)** | 9,62 | 12,06 | **15,43** | +3,37 | +5,81 |
| **Deuda Técnica x KLOC (`min / kloc`)** | 37,58 | 65,25 | **81,71** | +16,46 | +44,13 |

### Análisis Longitudinal:
1. **Crecimiento del código:** La base de código de producción creció de 2.182 ncloc en Etapa 1 a 4.230 en Etapa 2 y a 5.507 en Etapa 3 (+152% respecto a la fase inicial), debido a la incorporación de cifrado cliente-servidor, auditoría HMAC encadenada, infraestructura Nginx HTTPS con TLS, migraciones estructuradas y Docker Compose.
2. **Evolución de Defectos:** La Etapa 3 introduce por primera vez Bugs (12) y Vulnerabilidades (2) detectados estáticamente, todos localizados en los nuevos componentes arquitectónicos de la etapa (`migration_service.py` y `Dockerfile`s).
3. **Densidad de Deuda Técnica:** La deuda técnica por cada 1.000 líneas de código aumentó de 37,58 minutos en Etapa 1 a 65,25 en Etapa 2 y a 81,71 en la línea base de la Etapa 3.

---

## 6. Preservación de la Línea Base Pre-Remediación

En estricta observancia de los mandatos metodológicos para la investigación comparativa de SDD:
- **No se aplicó ninguna corrección de código:** Ninguno de los 12 bugs, 2 vulnerabilidades ni 71 code smells fue intervenido. La línea base permanece en su estado puro pre-remediación para permitir la evaluación objetiva del desempeño de Tessl.
- **Hallazgo H12 (Secretos por defecto en Docker Compose):** Se verificó que `docker-compose.yml` preserva los valores predeterminados para `ENCRYPTION_KEY`, `AUDIT_SECRET_KEY` y `ADMIN_SECRET_KEY` sin modificar.
- **Hallazgo H13 (Certificados TLS de Desarrollo):** Se preservó el script `nginx/generate_certs.py` y la configuración HTTPS autofirmada.
- **Integridad de Base de Datos:** Los archivos persistentes `shift_bank.db`, `shift_bank.db-wal` y `shift_bank.db-shm` permanecieron intactos.
- **Especificaciones y Manifiestos:** Las especificaciones en `specs/` y los manifiestos de dependencias (`backend/requirements.txt`, `frontend/package.json`) permanecen inalterados.

---

## 7. Registro de Ejecución del Scanner

```text
[INFO]  Bootstrapper: Platform: win32 x64
[INFO]  Bootstrapper: Server URL: http://localhost:9000
[INFO]  Bootstrapper: Using SonarScanner for NPM (@sonar/scan)
[INFO]  Bootstrapper: Version: 5.1.0
[INFO]  Bootstrapper: SonarQube server version: 26.9.0
[INFO]  ScannerEngine: Starting SonarScanner Engine...
[INFO]  ScannerEngine: Java 21.0.11 Eclipse Adoptium (64-bit)
[INFO]  ScannerEngine: Server id: 147B411E-AaDu3RAtjbxfUIRaFUSu
[INFO]  ScannerEngine: Project key: Shift-Bank---Stage-3---Tessl
[INFO]  ScannerEngine: Base dir: C:\Users\danie\Documents2\sdd-comparative-study\Shift-Bank\Etapa 3\Tessl
[INFO]  ScannerEngine: 6 languages detected in 66 preprocessed files
[INFO]  ScannerEngine: 66 files indexed
[INFO]  ScannerEngine: Quality profile for css: Sonar way
[INFO]  ScannerEngine: Quality profile for docker: Sonar way
[INFO]  ScannerEngine: Quality profile for json: Sonar way
[INFO]  ScannerEngine: Quality profile for py: Sonar way
[INFO]  ScannerEngine: Quality profile for ts: Sonar way
[INFO]  ScannerEngine: Quality profile for yaml: Sonar way
[INFO]  ScannerEngine: Sensor Python Sensor [python] -> 40 source files analyzed
[INFO]  ScannerEngine: Sensor TextAndSecretsSensor [text] -> 66 source files analyzed
[INFO]  ScannerEngine: Sensor JavaScript/TypeScript/CSS analysis [javascript] -> 21 source files analyzed
[INFO]  ScannerEngine: SCM revision ID 'a3dacf482c9ffa76086dbd01a6711ae6222940db'
[INFO]  ScannerEngine: Analysis report uploaded in 125ms
[INFO]  ScannerEngine: ANALYSIS SUCCESSFUL
[INFO]  ScannerEngine: Dashboard: http://localhost:9000/dashboard?id=Shift-Bank---Stage-3---Tessl
[INFO]  ScannerEngine: Report processing: http://localhost:9000/api/ce/task?id=fe154f2f-4fc1-4375-9876-c9e4c40aa7f8
[INFO]  ScannerEngine: Analysis total time: 20.485 s
[INFO]  ScannerEngine: SonarScanner Engine completed successfully
```
