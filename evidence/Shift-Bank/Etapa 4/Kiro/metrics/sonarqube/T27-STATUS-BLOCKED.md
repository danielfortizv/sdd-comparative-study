# T27 — Exportación del PRE-scan de SonarQube — BLOQUEADO (no completado)

Fecha/hora: 2026-11-19 (America/Bogota).

## Estado
- **T27 NO completado.** No se exportaron métricas, Quality Gate, issues, reglas, cobertura,
  configuración ni logs del escáner, porque **falta acceso verificable** a los resultados.

## Qué se verificó (real)
- SonarQube **UP**: `GET http://localhost:9000/api/system/status` → 200,
  `{"version":"26.9.0.129388","status":"UP"}`.
- Lectura del proyecto/Quality Gate **requiere autenticación**:
  `GET /api/components/show?component=Shift-Bank---Stage-4---Kiro` → **401**;
  `GET /api/qualitygates/project_status?projectKey=Shift-Bank---Stage-4---Kiro` → **401**.
- **No hay artefactos locales del escáner**: no se encontró `report-task.txt` ni `.scannerwork`
  bajo `Etapa 4/` (el `report-task.txt` contiene `ceTaskId` y `analysisId`, necesarios para
  verificar la tarea del Compute Engine y resolver el analysis ID).
- No hay `SONAR_TOKEN`/`SONAR_LOGIN` en el entorno de esta sesión.

## Qué se necesita para completar T27 (una de las dos opciones)
1. **Token de SonarQube** (user token o token del proyecto) con permiso de lectura sobre
   `Shift-Bank---Stage-4---Kiro`. Con él se puede:
   - `GET /api/ce/task?id=<ceTaskId>` (o `/api/ce/component?component=...`) → verificar
     `status=SUCCESS` y obtener `analysisId`.
   - `GET /api/qualitygates/project_status?analysisId=<id>` → Quality Gate PRE.
   - `GET /api/measures/component?component=...&metricKeys=...` → métricas/cobertura.
   - `GET /api/issues/search?componentKeys=...&p=N&ps=500` → issues paginados (todas las páginas).
   - `GET /api/rules/show?key=...` → reglas de los issues.
   - `GET /api/settings/values` / `/api/qualitygates/get_by_project` → configuración.
2. **`report-task.txt` del escáner** (y los logs del scanner, p. ej. `.scannerwork/` o el stdout de
   la corrida del investigador). Con `ceTaskId`/`analysisId` + token se exporta todo lo anterior.

## Restricciones respetadas
- No se ejecutó otro escaneo.
- No se modificó código de la aplicación.
- No se inventaron métricas, severidades ni Quality Gate.
- La Etapa 3 no se tocó. El key de la Etapa 4 confirmado: `Shift-Bank---Stage-4---Kiro`
  (`sonar-project-stage4.properties`), nunca el de la Etapa 3.

## Siguiente acción
Proporcionar un token de lectura de SonarQube (o la ruta al `report-task.txt`/logs del escáner).
En cuanto esté disponible, se verifica la tarea del Compute Engine, se resuelve el analysis ID y
se exporta la evidencia cruda PRE a este directorio; solo entonces se marca T27 completo y se
detiene en T28 para la revisión del investigador.
