# E4 — Iteración 09

## Fecha/hora y fase
- Fecha/hora: 2026-11-19 (America/Bogota).
- Fase/milestone: T28 (aprobación del PRE por el investigador) + T29 (pasada correctiva acotada).
  Gate T30 (escaneo final) a continuación — lo ejecuta el investigador.

## Tareas principales completadas y progreso
- Progreso de tareas principales: **29/31** (1–29 completas; 30 gate PENDIENTE; 31 pendiente).

## Actividades y decisiones técnicas
- **T28 aprobado** por el investigador (PRE analysisId cd37bcc9, QG OK, 162 issues, 49.7% cob.,
  783 min). Evidencia PRE original preservada sin cambios.
- **T29 — pasada correctiva ACOTADA** (inspección de reglas/código ANTES de cambiar):
  - `typescript:S2245` (ÚNICA vulnerabilidad, producción, `apiV2.ts`): `newIdempotencyKey()`
    reescrito a `crypto.randomUUID()` / `crypto.getRandomValues()` (CSPRNG, UUID v4 RFC 4122) con
    **fallo seguro** si no hay aleatoriedad segura; se elimina `Math.random()`. Formato UUID e
    idempotencia preservados. RESUELTO.
  - `typescript:S6759` ("props read-only"): aplicado `Readonly<Props>` SOLO en los 2 componentes
    propios de la Etapa 4 (`MultiCurrencyDashboard`, `ConversionForm`). Los 8 componentes
    HEREDADOS no se tocan (preservación Etapa 3; fuera de alcance). PARCIAL acotado.
  - `python:S9073`/`S5778`/`S9083` (124 findings): **NO modificados por decisión**. Verificado que
    el 100% están en `backend/tests/` (0 en `app/`); reescribir aserciones/decoradores de tests en
    masa es el anti-patrón prohibido y arriesga el baseline de regresión + archivos heredados.
- No se tocaron exclusiones, supresiones, condiciones del Quality Gate, alcance ni cobertura.
  Ningún archivo de `backend/app/` ni de la Etapa 3 cambiado.

## Archivos creados o modificados
- Modificados: `frontend/src/stage4/apiV2.ts`, `frontend/src/stage4/MultiCurrencyDashboard.tsx`,
  `frontend/src/stage4/ConversionForm.tsx`.
- Creados (evidencia): `sonarqube/T29_CORRECTIVE_RECORD.md`, `sonarqube/T29_vitest.txt`,
  `T29_build.txt`, `T29_backend_regression.txt`, `T29_backend_coverage.txt`,
  `T29_frontend_coverage.txt`.
- Regenerados: `backend/coverage.xml`, `frontend/coverage/lcov.info` (misma metodología PRE).
- Specs: `tasks.md`/`tasks.meta.json` (28 aprobado, 29 completo).

## Pruebas ejecutadas (reales)
- Frontend Vitest: **14 passed**, exit 0.
- Build producción (`tsc && vite build`): exit 0, **45 modules**.
- Regresión backend completa: **444 passed**, exit 0.
- Cobertura regenerada: backend 444 passed + `coverage.xml`; frontend 14 passed + `lcov.info`.

## Errores, reintentos y correcciones
- Sin regresiones ni reintentos: todas las suites verdes a la primera tras los fixes.
- `rules_metadata.json` no exponía descripciones en el campo esperado; las descripciones se
  obtuvieron de los `message` distintos por regla en los issues exportados (fuente equivalente).

## Rutas de evidencia
- `_experiment_logs/Kiro/E4/sonarqube/T29_CORRECTIVE_RECORD.md` (registro detallado: issues,
  archivos/líneas, reglas, resueltos/no resueltos, decisiones, limitaciones).
- Logs de pruebas T29 en el mismo directorio. Cobertura en `backend/coverage.xml` +
  `frontend/coverage/lcov.info`.

## Resultado esperado en POST (honesto)
- Vulnerabilidades 1 → 0 (S2245 resuelta). S6759 10 → 8 (2 resueltos en Stage 4).
- python:S9073/S5778/S9083 permanecen (test-only, decisión deliberada). El conteo total NO baja a
  ~0; es intencional y no refleja peor calidad del producto.
- Comparable 1:1 con el PRE: misma key, config, alcance y metodología de cobertura.

## Interacciones de modelo, llamadas a herramientas, tiempo y créditos
- Modelo: Auto. Métricas exactas de esta iteración: **N/D**. D1 PRE del nuevo account:
  30.24/969.76 (2026-11-18). No se inventan totales.

## Bloqueadores, limitaciones y próxima actividad
- **DETENER antes de T30.** No se ejecuta el escaneo POST; lo corre el investigador con la MISMA
  configuración del escáner que el PRE.
- Próxima actividad (tras POST + aprobación T30): T31 (consolidación de evidencia y reporte final).
