# E4 — Iteración 05

## Fecha/hora y fase
- Fecha/hora: 2026-11-18 (America/Bogota).
- Fase/milestone: M5 (frontend multidivisa).

## Tareas principales completadas y progreso
- Progreso de tareas principales: **17/31**.
- Completadas en esta iteración: Tareas 16, 17.

## Actividades y decisiones técnicas
- T16: `stage4/currencyFormat.ts` — aritmética en `bigint`/unidades menores y cadenas decimales
  (nunca `number`, D-03); símbolos por moneda; estimación USD por tasas racionales fijas con
  `bigint` + HALF_UP una sola vez; agrupación de totales SEPARADA por moneda (D-10).
  `stage4/apiV2.ts` — cliente v2 (`/api/v2/accounts`, `/api/conversions`, `/api/v2/transfers`) con
  `Idempotency-Key` UUID automático y `Expected-Version` opcional; errores -> `ApiV2Error`
  con `status` (409 de idempotencia/versión manejables en UI).
- T17: `MultiCurrencyDashboard` (totales por moneda + total USD estimado etiquetado "solo
  visualización") y `ConversionForm` (muestra tasa/origen/destino). Integrados en `App.tsx` como
  nueva sección "Multidivisa" (carga v2 tolerante a fallo, sin romper la experiencia heredada).
- Decisión: integración aditiva (Path A) — la app heredada y sus 3 pruebas Vitest se preservan;
  la UI de la Etapa 4 se añade sin alterar los componentes heredados. El build pasó de 41 a 45
  módulos transformados, confirmando que los nuevos componentes entran al bundle.

## Archivos creados o modificados
- Creados: `frontend/src/stage4/currencyFormat.ts`, `frontend/src/stage4/apiV2.ts`,
  `frontend/src/stage4/MultiCurrencyDashboard.tsx`, `frontend/src/stage4/ConversionForm.tsx`,
  `frontend/src/stage4/currencyFormat.test.ts`, `frontend/src/stage4/apiV2.test.ts`.
- Modificados: `frontend/src/App.tsx` (sección "Multidivisa", estado/carga v2).
- Specs: `tasks.md` y `tasks.meta.json` (16–17 completas).

## Pruebas ejecutadas (reales)
- Vitest: **14 passed (3 archivos)**, exit 0 (3 heredadas + 11 nuevas: currencyFormat + apiV2).
- Build de producción (`tsc && vite build`): exit 0, **45 modules transformed** (antes 41),
  type-check de todo `src/` incluido los nuevos `.tsx`.
- Backend sin cambios en esta iteración (última regresión completa verde: 428 passed).

## Errores, reintentos y correcciones
- Observación intermedia: antes de integrar en `App.tsx`, el build seguía en 41 módulos (los
  componentes nuevos no entraban al bundle por tree-shaking). Corrección: cablear el dashboard y el
  formulario en `App.tsx`; build subió a 45 módulos. Sin errores de compilación.

## Rutas de evidencia
- `_experiment_logs/Kiro/E4/baseline/frontend-vitest-stage4-final.txt`,
  `frontend-build-stage4-final.txt`.
- Código bajo `Kiro/frontend/src/stage4/` y `Kiro/frontend/src/App.tsx`.

## Interacciones de modelo, llamadas a herramientas, tiempo y créditos
- Modelo: Auto. Métricas exactas de esta iteración: **N/D**. D1 PRE del nuevo account:
  30.24/969.76 (2026-11-18). No se inventan totales.

## Bloqueadores, limitaciones y próxima actividad
- Bloqueadores: ninguno técnico. Gates obligatorios pendientes: T28 (SonarQube PRE), T30 (POST).
- Próxima actividad: M6 — Tareas 18–25 (verificación de atomicidad/ES-CQRS/concurrencia/fallo;
  regresión completa; cobertura; carga Locust; despliegue). Se usarán pruebas dirigidas y la
  regresión completa + cobertura en los puntos de verificación.
