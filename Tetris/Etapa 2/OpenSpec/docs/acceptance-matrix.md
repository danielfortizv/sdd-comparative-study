# Mapa de aceptación — Etapa 2 OpenSpec

`pass` aquí significa que existe la evidencia indicada; los mecanismos son diferentes y no deben confundirse con veinte controles de API de caja negra. La definición de cada escenario está en `../../shared/acceptance/catalog.md`.

| ID | Estado | Mecanismo | Evidencia principal |
| --- | --- | --- | --- |
| S2-01 | pass | API externa | `acceptance-api.json`, creación e invariantes |
| S2-02 | pass | API externa | `acceptance-api.json`, dos lecturas sin mutación |
| S2-03 | pass | API externa | `acceptance-api.json`, bloqueo sin línea y rotación de vista previa |
| S2-04 | pass | prueba de dominio | `backend-coverage.log`, `test_stage2_scoring_and_progression` |
| S2-05 | pass | prueba de dominio | `backend-coverage.log`, `test_stage2_scoring_and_progression` |
| S2-06 | pass | prueba de dominio | `backend-coverage.log`, `test_stage2_scoring_and_progression` |
| S2-07 | pass, solo regla aislada | prueba de dominio | `backend-coverage.log`, fixture de cuatro filas en `test_stage2_scoring_and_progression` |
| S2-08 | pass | prueba de dominio | `backend-coverage.log`, `test_stage2_level_boundary_uses_pre_lock_score` |
| S2-09 | pass | prueba de dominio | `backend-coverage.log`, `test_stage2_level_and_gravity_speed_progression` |
| S2-10 | pass | API externa | `acceptance-api.json`, primer Hold |
| S2-11 | pass | API externa | `acceptance-api.json`, segundo Hold rechazado y estado intacto |
| S2-12 | pass | API externa | `acceptance-api.json`, Hold restablecido tras bloqueo y cambio sin consumir preview |
| S2-13 | pass | prueba de dominio | `backend-coverage.log`, `test_stage2_hold_mechanics` y estado expuesto sin pieza activa ilegal |
| S2-14 | pass | prueba de dominio | `backend-coverage.log`, `test_stage2_game_over_actions_leave_state_unchanged` |
| S2-15 | pass | API externa | `acceptance-api.json`, nueva sesión con contadores reiniciados |
| S2-16 | pass | API externa y tests backend | `acceptance-api.json`, rutas compatibles y 404 |
| S2-17 | pass | prueba de React + navegador local | `frontend-test-coverage.log`, `screenshots/tetris-stage2-ui.png`, observación de botón y tecla C |
| S2-18 | pass | prueba de React controlada | `frontend-test-coverage.log`, temporizador 500→450 ms y respuestas reordenadas |
| S2-19 | pass | pruebas de regresión backend | `backend-coverage.log`, pruebas Stage 1 de grilla, movimiento, colisión, lock, borrado y game over |
| S2-20 | pass | compilación reproducible | `frontend-build.log` |

Las salidas JSON de SonarQube, la auditoría de tokens y los archivos de prueba se conservan en `docs/`; el informe narrativo está en `RESEARCH_LOG.md`.
