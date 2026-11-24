# E4 — Iteración 08

## Fecha/hora y fase
- Fecha/hora: 2026-11-19 (America/Bogota).
- Fase/milestone: T27 — verificación/exportación de la evidencia del PRE-scan de SonarQube
  (ejecutado por el investigador). Gate T28 a continuación.

## Tareas principales completadas y progreso
- Progreso de tareas principales: **27/31** (1–27 completas; 28 gate PENDIENTE; 29–31 pendientes).

## Actividades y decisiones técnicas
- Se verificó la evidencia PRE exportada en `_experiment_logs/Kiro/E4/sonarqube/` (12 archivos
  JSON/XML/log con timestamp `20261119-004700`).
- **CE task verificada:** `ce_task.json` → id `c69bea55-1738-4d87-a4ca-26e169a4934d`,
  `status=SUCCESS`, `analysisId=cd37bcc9-6884-4dd4-a92a-d4e8f374cb62`, `executionTimeMs=4071`,
  1 warning (autodetección SCM, no bloqueante).
- **Quality Gate:** `quality_gate.json` → `status=OK`, sin condiciones, `caycStatus=compliant`.
- **Cobertura importada (confirmada en `scanner.log`):** Cobertura Python parseó
  `/usr/src/backend/coverage.xml`; JS/TS Coverage analizó `/usr/src/frontend/coverage/lcov.info`.
  coverage=49.7% (line 49.7%, branch 51.7%, uncovered_lines 2227, lines_to_cover 4427).
- **Issues paginados íntegros:** `issues_unresolved_p1.json` → paging.total=162, array=162
  (pageSize 500, una sola página); `issues_resolved_p1.json` → total=0. El metric `violations`=162
  concuerda.
- No se buscaron credenciales, no se ejecutó otro escaneo, no se modificó código de la aplicación,
  no se inició T29. La Etapa 3 no se tocó.

## Hallazgos PRE (reales)

### Métricas tradicionales
- violations=162; bugs=0; vulnerabilities=1; code_smells=161; security_hotspots=0.
- Ratings: reliability_rating=1.0 (A), security_rating=3.0 (C), sqale_rating=1.0 (A).
- sqale_index=783 min; sqale_debt_ratio=0.4%; duplicated_lines_density=0.0%.

### Métricas MQR (Multi-Quality Rating, SonarQube 26.x)
- Impactos por issue: MAINTAINABILITY HIGH=3 / MEDIUM=122 / LOW=33 / INFO=1;
  RELIABILITY HIGH=1 / MEDIUM=2 / LOW=3; SECURITY MEDIUM=1.
- MQR ratings: software_quality_maintainability_rating=1.0 (A);
  software_quality_reliability_rating=4.0 (D); software_quality_security_rating=3.0 (C).
- Esfuerzo de remediación MQR: maintainability=743 min, reliability=60 min.
- Nota: en el modelo tradicional reliability_rating=A (bugs=0), pero en MQR la fiabilidad baja a D
  por impactos de fiabilidad en issues clasificados como CODE_SMELL en el modelo tradicional. Esta
  es la diferencia esperada entre ambos modelos; se reportan ambos sin mezclarlos.

### Severidad tradicional de los 162 issues
- CRITICAL=2, MAJOR=126, MINOR=33, INFO=1. Tipos: CODE_SMELL=161, VULNERABILITY=1.

### Reglas principales (top)
- python:S9073 (94), python:S5778 (17), python:S9083 (13), typescript:S6759 (10),
  python:S8410 (5), typescript:S3358 (4), python:S5713 (3), typescript:S6772 (3),
  typescript:S8786 (2), python:S3776 (2), typescript:S7767 (1), typescript:S6819 (1).
- Única VULNERABILITY: `typescript:S2245` en `frontend/src/stage4/apiV2.ts:47` — uso de
  `Math.random()` (fallback de `newIdempotencyKey`). MQR SECURITY/MEDIUM.

## Pruebas ejecutadas (reales)
- Verificación de evidencia (lectura/parseo JSON), sin escaneo ni cambios de código.
- SonarQube server UP (v26.9.0) confirmado en iteraciones previas; esta iteración trabaja sobre la
  evidencia exportada local.

## Errores, reintentos y correcciones
- Ninguno. La iteración previa (07/BLOCKED) quedó desbloqueada al disponer de la evidencia local.

## Rutas de evidencia
- `_experiment_logs/Kiro/E4/sonarqube/20261119-004700_T27_PRE_*` (ce_task, quality_gate, measures,
  issues_unresolved_p1, issues_resolved_p1, rules_metadata, backend_coverage.xml,
  frontend_lcov.info, original_coverage.xml, properties.txt, scanner.log, export_summary.json).

## Recomendación — una pasada correctiva ACOTADA (para T29, tras aprobación del investigador)
Objetivo: reducir violations preservando el comportamiento aprobado, sin cambiar contratos ni
invariantes, re-ejecutando la regresión tras cada cambio. Alcance sugerido (acotado):
1. Resolver la única VULNERABILITY `typescript:S2245` (`apiV2.ts:47`): usar `crypto.randomUUID()`
   sin fallback a `Math.random()` (o `crypto.getRandomValues`), eliminando el PRNG inseguro.
2. Atacar las reglas de mayor volumen con arreglos mecánicos y seguros: `python:S9073` (94),
   `python:S5778` (17), `python:S9083` (13), `typescript:S6759` (10) — cambios locales de estilo/
   tipos que no alteran la lógica.
3. NO perseguir cobertura en esta pasada (el Quality Gate ya es OK; subir cobertura es mayor y
   arriesgado); dejarlo fuera del alcance acotado.
Límite: una sola pasada, sin tocar la Etapa 3, sin cambios de contrato; T30 (escaneo final) debe
ser comparable 1:1 con el PRE (misma config/cobertura/clave).

## Interacciones de modelo, llamadas a herramientas, tiempo y créditos
- Modelo: Auto. Métricas exactas de esta iteración: **N/D**. D1 PRE del nuevo account:
  30.24/969.76 (2026-11-18). No se inventan totales.

## Bloqueadores, limitaciones y próxima actividad
- **GATE T28 (revisión del investigador del PRE):** DETENER. No se inicia T29 hasta aprobación.
- Próxima actividad (tras aprobación): T29 pasada correctiva acotada → T30 (gate escaneo final) →
  T31 (evidencia/reporte final).
