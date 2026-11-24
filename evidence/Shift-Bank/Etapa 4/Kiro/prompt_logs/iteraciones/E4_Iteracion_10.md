# E4 — Iteración 10

## Fecha/hora y fase
- Fecha/hora: 2026-11-19 (America/Bogota).
- Fase/milestone: T30 — revisión de resultados del escaneo POST de SonarQube (ejecutado por el
  investigador). DETENER para aprobación del investigador del gate T30 antes de T31.

## Tareas principales completadas y progreso
- Progreso de tareas principales: **29/31** (1–29 completas; 30 gate PENDIENTE de aprobación; 31
  pendiente). No se marca T30 completo (es gate del investigador).

## Verificación del POST (real)
- CE task POST: id `171f9bef-d49d-4c15-a51b-4d74cae94056`, **status=SUCCESS**,
  analysisId `bb7434e4-29e5-424e-8799-8f2c8b1cc936`, executedAt 2026-11-19T06:17:39Z,
  executionTimeMs 2366, 1 warning no bloqueante (SCM autodetect). Scanner exit code **0**.
- Quality Gate POST: **OK** (condiciones de New Code: new_violations 0 ≤ 0, new_coverage 10.5
  informativo, new_duplicated 0.0; `caycStatus=compliant`).
- Configuración idéntica PRE↔POST: `properties.txt` **byte-idénticos** (misma key
  `Shift-Bank---Stage-4---Kiro`, mismas fuentes/alcance/exclusiones/rutas de cobertura).
- Paginación POST: unresolved total 158 == array 158; resolved total 4 == array 4.

## Comparación PRE vs POST

### Quality Gate
- PRE: OK (sin condiciones evaluadas; análisis inicial). POST: OK (New Code: new_violations=0).

### Tradicional (bugs / vulnerabilities / code smells)
| Métrica | PRE | POST | Δ |
|---|---|---|---|
| bugs | 0 | 0 | 0 |
| vulnerabilities | **1** | **0** | **-1** |
| code_smells | 161 | 158 | -3 |
| violations (total) | 162 | 158 | -4 |
| security_hotspots | 0 | 0 | 0 |

### Severidad tradicional de los issues abiertos
- PRE: CRITICAL 2, MAJOR 126, MINOR 33, INFO 1.
- POST: CRITICAL 2, MAJOR 124, MINOR 31, INFO 1.

### MQR — impactos y ratings
- Impactos abiertos:
  * PRE: MAINTAINABILITY HIGH 3 / MED 122 / LOW 33 / INFO 1; RELIABILITY HIGH 1 / MED 2 / LOW 3;
    **SECURITY MED 1**.
  * POST: MAINTAINABILITY HIGH 2 / MED 122 / LOW 31 / INFO 1; RELIABILITY MED 2 / LOW 3;
    **SECURITY: ninguno**.
- Ratings MQR:
  * security_rating (MQR): PRE 3.0 (C) → POST **1.0 (A)**.
  * reliability_rating (MQR): PRE 4.0 (D) → POST **3.0 (C)** (se eliminó el impacto RELIABILITY/HIGH).
  * maintainability_rating (MQR): 1.0 (A) → 1.0 (A).
- Ratings tradicionales: security PRE C (3.0) → POST **A (1.0)**; reliability A→A; sqale A→A.

### Deuda técnica
- sqale_index (deuda): PRE 783 min → POST **768 min** (-15). sqale_debt_ratio 0.4% → 0.4%.
- MQR remediation: maintainability 743→728 min; reliability 60→55 min.

### Cobertura y duplicación
- coverage: PRE 49.7% → POST 49.6% (line 49.6, branch 50.8). Variación mínima por el cambio de
  código (ncloc 6249→6261, lines_to_cover 4427→4437). Metodología/alcance IDÉNTICOS (mismo
  `--cov=app` Cobertura XML + Vitest v8 lcov, mismas exclusiones). No se infló cobertura.
- duplicated_lines_density: 0.0% → 0.0% (sin cambios).

### Issues: resueltos / introducidos / restantes
- **Resueltos (4):** `typescript:S2245` (CLOSED, resolution=FIXED, `apiV2.ts`), 2× `typescript:S6759`
  (componentes Stage 4), 1× `typescript:S7767` (bonus: el reescrito con `getRandomValues` también
  lo cerró).
- **Introducidos:** 0 (new_violations=0).
- **Restantes:** 158 (todos CODE_SMELL; 0 bugs, 0 vulnerabilidades).

## ¿typescript:S2245 realmente resuelto?
- **SÍ, verificado.** En POST unresolved: 0 ocurrencias de S2245. En POST resolved: S2245 con
  `status=CLOSED`, `resolution=FIXED` en `frontend/src/stage4/apiV2.ts`. Métrica
  `vulnerabilities` 1→0 y `security_rating` C→A lo confirman de forma independiente.

## Coherencia con lo esperado en T29
- Coincide con la predicción honesta: vuln 1→0; S6759 10→8 (2 resueltos); las reglas test-only
  (python:S9073/S5778/S9083) permanecen por decisión deliberada. El total baja de 162 a 158 (−4),
  no a ~0 — resultado honesto, no manipulado.

## Errores / reintentos / limitaciones
- Ninguno. Esta iteración es de lectura/verificación de evidencia; no se modificó código ni se
  re-ejecutó SonarQube. Evidencia PRE y POST preservada sin cambios.

## Rutas de evidencia
- POST: `_experiment_logs/Kiro/E4/sonarqube/20261119-011552_T30_POST_*` (ce_task, quality_gate,
  measures, issues_unresolved_p1, issues_resolved_p1, rules_metadata, backend_coverage.xml,
  frontend_lcov.info, original_coverage.xml, properties.txt, scanner.log, scanner_exit_code.txt).
- PRE: `..._20261119-004700_T27_PRE_*` (preservado).

## Interacciones de modelo, llamadas a herramientas, tiempo y créditos
- Modelo: Auto. Métricas exactas de esta iteración: **N/D**. D1 PRE del nuevo account:
  30.24/969.76 (2026-11-18). No se inventan totales.

## Bloqueadores, limitaciones y próxima actividad
- **DETENER para aprobación del investigador del gate T30.** No se marca T30 completo hasta la
  aprobación.
- Próxima actividad (tras aprobación de T30): T31 — consolidación de la evidencia experimental y
  reporte final de la Etapa 4.
