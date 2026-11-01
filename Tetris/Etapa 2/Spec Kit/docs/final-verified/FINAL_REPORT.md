# Tetris — Etapa 2, opción A: informe verificado de Spec Kit

Estado: implementación local y verificaciones finales completas para la evidencia descrita. No se hizo commit ni push. Este informe distingue la salida de la herramienta, las correcciones y la verificación independiente.

Generado en UTC: 2026-10-21T05:42:43.818321+00:00.

## Control y procedencia

Semilla maestra: `63919779DD4104076FBABCB130CE296A160FA840E0B4755A2AA5D90757ADA8EF`. Bloque extraído UTF-8/LF: `60D6728689CD5CDAD7B1A386F95DAD4E34850EB5DE0AAB92E837D630DFD2B55A`. La semilla común no cambió. Las incidencias de entrega iniciales y el acceso contextual posterior se conservan en `input-audit.json`; la entrada efectiva de implementación y correcciones está verificada.

Entorno registrado: Spec Kit 1.0.12, Gemini CLI 0.60.0, Node v25.6.1, npm 11.9.0, Python 3.12.14, SonarQube 26.9.0.129388. Modelo solicitado: `gemini-3.5-flash`. Los modelos auxiliares efectivos aparecen por sesión en la tabla y las estadísticas originales.

Las métricas de uso abarcan Gemini CLI y sus roles auxiliares. Excluyen Codex/orquestación del investigador, agentes de revisión de solo lectura, autoría de helpers, trabajo de Drive/UI y verificaciones externas; no son el costo ni los tokens totales del proyecto. Las fuentes actuales incluyen código heredado y cambios generados por Gemini. Helpers, evidencias y este informe son del investigador. La desviación manual documentada en OpenSpec permanece separada en comparaciones.

## Invocaciones, tokens y correcciones

Entrada significa prompt e incluye la caché; la caché no se suma de nuevo. Salida candidata y pensamiento se cuentan por separado. Intentos API, errores y éxitos corresponden a estadísticas completas; respuestas JSONL son otra medida y pueden omitir roles auxiliares. Los valores desconocidos se conservan.

| Sesión | Entrada | Caché incluida | Salida candidata | Pensamiento |
| --- | ---: | ---: | ---: | ---: |
| 01-specify | 372.306 | 328.077 | 572 | 3.622 |
| 02-specify-retry | 553.753 | 417.153 | 5.986 | 8.755 |
| 03-contract-clarification | 231.106 | 152.515 | 5.847 | 18.651 |
| 04-plan | 1.659.066 | 1.321.138 | 14.548 | 8.060 |
| 05-tasks | 293.607 | 155.479 | 4.874 | 6.352 |
| 06-tasks-full-arguments | 0 | 0 | 0 | 0 |
| 07-tasks-native-expanded | 1.065.684 | 505.891 | 8.216 | 7.163 |
| 08-implement | 16.752.166 | 12.893.781 | 36.959 | 41.527 |
| 09-qa-correction | 10.900.997 | 8.551.042 | 40.048 | 42.080 |
| 10-qa-race-correction | 5.514.887 | 4.925.600 | 23.190 | 26.295 |
| 11-qa-timer-ownership | 607.848 | 257.143 | 2.297 | 16.381 |
| 12-qa-timer-retry | 1.830.444 | 1.091.029 | 10.707 | 14.468 |
| 13-qa-completion-retry | 225.989 | 104.499 | 144 | 630 |
| 14-qa-completion-fresh | 720.193 | 422.234 | 1.936 | 15.806 |
| 15-qa-frontend-completion | 160.759 | 0 | 1.808 | 7.575 |
| 16-qa-final-regressions | 1.560.326 | 1.173.857 | 6.505 | 15.859 |
| 17-qa-sonar-style | 1.540.447 | 1.116.692 | 4.735 | 8.890 |

En 13, el primer registro user es contexto sintético/repetición del CLI y no contiene la semilla. El prompt real íntegro, con hash idéntico al previsto, se registró después y antes de la primera respuesta con tokens. Solo hubo update_topic y 0/0 líneas: no produjo trabajo de aplicación. La desviación del primer registro queda preservada; no se relaja el requisito de semilla completa para las correcciones que producen código. Evidencia: 13-input-replay-verification.json.

| Sesión | Segundos | Intentos API | Errores API | Éxitos API | Respuestas JSONL |
| --- | ---: | ---: | ---: | ---: | ---: |
| 01-specify | no disponible | no disponible | no disponible | no disponible | 14 |
| 02-specify-retry | 314,087 | 23 | 2 | 21 | 21 |
| 03-contract-clarification | no disponible | no disponible | no disponible | no disponible | 11 |
| 04-plan | 671,273 | 52 | 4 | 48 | 46 |
| 05-tasks | 304,671 | 13 | 2 | 11 | 11 |
| 06-tasks-full-arguments | 0,084 | 0 | 0 | 0 | 0 |
| 07-tasks-native-expanded | 545,391 | 41 | 14 | 27 | 27 |
| 08-implement | 2.885,870 | 202 | 54 | 148 | 140 |
| 09-qa-correction | 3.450,181 | 149 | 39 | 110 | 100 |
| 10-qa-race-correction | 455,055 | 60 | 0 | 60 | 58 |
| 11-qa-timer-ownership | 439,318 | no disponible | no disponible | no disponible | 14 |
| 12-qa-timer-retry | 1.513,504 | no disponible | no disponible | no disponible | 21 |
| 13-qa-completion-retry | 16,638 | 2 | 0 | 2 | 2 |
| 14-qa-completion-fresh | 184,895 | 20 | 0 | 20 | 20 |
| 15-qa-frontend-completion | 56,315 | 2 | 0 | 2 | 2 |
| 16-qa-final-regressions | 375,325 | 40 | 3 | 37 | 36 |
| 17-qa-sonar-style | 313,986 | 41 | 3 | 38 | 37 |

| Sesión | Modelo auxiliar | Roles declarados | API intentos/errores/éxitos |
| --- | --- | --- | --- |
| 04-plan | gemini-3-flash-preview | utility_loop_detector | 2/0/2 |
| 08-implement | gemini-3-flash-preview | utility_loop_detector | 8/0/8 |
| 09-qa-correction | gemini-3-flash-preview | utility_loop_detector; utility_tool | 10/0/10 |
| 10-qa-race-correction | gemini-3-flash-preview | utility_loop_detector | 2/0/2 |
| 16-qa-final-regressions | gemini-3-flash-preview | utility_loop_detector | 1/0/1 |
| 17-qa-sonar-style | gemini-3-flash-preview | utility_loop_detector | 1/0/1 |

Acumulado observado: 17 intentos de invocación; 16 con modelo acreditado. Duración conocida 11.526,593 s; sesiones con duración desconocida: 01-specify; 03-contract-clarification. Entrada 43.989.578, caché incluida 33.416.130, candidata 168.372, pensamiento 242.114. API conocida 645/121/524; respuestas JSONL 560. La duración excluye trabajo externo y no imputa sesiones interrumpidas.

Intentos externos de corrección después de implementar: 9 iniciados y 9 cerrados; 7 con exit 0 y 2 fallidos/interrumpidos. Representan 4 intenciones QA distintas; un reintento puede compartir intención. Cerrar una invocación no acredita una corrección completada, y exit 0 no sustituye la aceptación independiente. Los reintentos del lanzador y la aclaración previa son categorías distintas; las acciones/rescaneos internos no son prompts externos nuevos.

| Categoría registrada | Intentos cerrados | Prompts con modelo observado | Etiquetas |
| --- | ---: | ---: | --- |
| initial_specification_attempt | 1 | 1 | 01-specify |
| specification_launcher_retry | 1 | 1 | 02-specify-retry |
| preimplementation_specification_correction | 1 | 1 | 03-contract-clarification |
| native_planning | 1 | 1 | 04-plan |
| native_task_generation | 1 | 1 | 05-tasks |
| task_launcher_retry | 2 | 1 | 06-tasks-full-arguments; 07-tasks-native-expanded |
| initial_implementation | 1 | 1 | 08-implement |
| postimplementation_external_correction | 9 | 9 | 09-qa-correction; 10-qa-race-correction; 11-qa-timer-ownership; 12-qa-timer-retry; 13-qa-completion-retry; 14-qa-completion-fresh; 15-qa-frontend-completion; 16-qa-final-regressions; 17-qa-sonar-style |

| Intención QA | Intentos | Exit 0 | Fallidos/interrumpidos |
| --- | --- | --- | --- |
| QA-1 | 09-qa-correction | 09-qa-correction |  |
| QA-2 | 10-qa-race-correction | 10-qa-race-correction |  |
| QA-3 | 11-qa-timer-ownership; 12-qa-timer-retry; 13-qa-completion-retry; 14-qa-completion-fresh; 15-qa-frontend-completion; 16-qa-final-regressions | 13-qa-completion-retry; 14-qa-completion-fresh; 15-qa-frontend-completion; 16-qa-final-regressions | 11-qa-timer-ownership; 12-qa-timer-retry |
| QA-4 | 17-qa-sonar-style | 17-qa-sonar-style |  |

Fallos terminales observados: 11-qa-timer-ownership: RESOURCE_EXHAUSTED; 12-qa-timer-retry: network_fetch_failed. Se conservan como incidencias de infraestructura, no como correcciones completadas. El total API sigue desconocido donde faltan estadísticas completas; no se suma un fallo terminal aislado como si fuese el agregado de errores de la sesión.

Auditoría de reanudación 12-qa-timer-retry (reintento de 11-qa-timer-ownership): no completed CLI counters; main JSONL interval only. No hubo contadores CLI completos para contrastar; se conservan solo tokens/respuestas JSONL del intervalo y los agregados API son desconocidos. El historial anterior no se sumó de nuevo. Los roles auxiliares conservan el alcance declarado por el CLI cuando existe esa evidencia.

Auditoría de reanudación 13-qa-completion-retry (reintento de 12-qa-timer-retry): main CLI counters match current invocation interval. Se contrastaron los contadores CLI con los tokens y las respuestas JSONL únicas dentro del intervalo. El historial anterior no se sumó de nuevo. single CLI-reported model; unlabeled interval records included only after exact token/count comparison and absence of conflicting model labels

Auditoría de reanudación 15-qa-frontend-completion (reintento de 14-qa-completion-fresh): main CLI counters match current invocation interval. Se contrastaron los contadores CLI con los tokens y las respuestas JSONL únicas dentro del intervalo. El historial anterior no se sumó de nuevo. single CLI-reported model; unlabeled interval records included only after exact token/count comparison and absence of conflicting model labels

Preguntas bloqueantes observadas: 0. El resultado procede de revisar texto emitido, no del modo headless. Se mantienen los límites de las sesiones interrumpidas y la separación de aclaraciones originadas por el investigador (`question-audit.json`).

## Tamaño, densidad y cambios de artefactos

Se cuentan líneas físicas y caracteres Unicode tras quitar BOM y normalizar a LF. Densidad = líneas/archivo. Fuente incluye pruebas y configuración textual; Sonar analiza producción con un alcance diferente. Los deltas netos de caracteres reflejan tamaño de estado, no volumen acumulado de edición.

| Alcance | Archivos | Líneas | Caracteres | Líneas/archivo |
| --- | ---: | ---: | ---: | ---: |
| Código Etapa 1 | 27 | 1.412 | 41.297 | 52,30 |
| Código final Etapa 2 | 29 | 3.972 | 122.186 | 136,97 |
| Specs Etapa 1 | 9 | 1.233 | 62.395 | 137,00 |
| Specs nativas Etapa 2 | 9 | 1.713 | 99.987 | 190,33 |

| Comparación | Archivos cambiados | Líneas añadidas/eliminadas | Líneas netas | Caracteres netos |
| --- | ---: | --- | ---: | ---: |
| Código vs Etapa 1 | 16 | 2.643/83 | 2.560 | 80.889 |
| Specs Etapa 2 vs carpeta vacía | 9 | 1.713/0 | 1.713 | 99.987 |
| Specs heredadas copiadas | 0 | 0/0 | 0 | 0 |
| Código QA vs generación 08 | 9 | 1.975/159 | 1.816 | 58.197 |
| Specs QA vs generación 08 | 2 | 223/0 | 223 | 20.410 |

La generación 08 congelada conserva el autoinforme inicial y su Sonar ERROR (57,1 % global; 44,9 % nuevo); sus declaraciones de LCOV y 96 % frontend no sustituyen los resultados independientes. Las correcciones posteriores y sus verificaciones se presentan con su propio estado. Las fuentes/especificaciones originales de Etapa 1 y su copia nativa se preservan.

## Ejecución independiente y calidad

Una llamada exitosa al wrapper no acredita una prueba aprobada: los resultados siguientes se apoyan en salidas originales y exit code 0, posteriores a los cambios finales.

| Comprobación | Comando registrado | Salida original |
| --- | --- | --- |
| backend-tests-and-coverage | D:\KEVIN\UNIVERSIDAD\Trabajos\Proyecto\Caso 2-Tetris\Etapa 1\_toolchain\venv\Scripts\python.exe -m pytest -q --cov=app --cov-report=term-missing --cov-report=xml:D:\KEVIN\UNIVERSIDAD\Trabajos\Proyecto\Caso 2-Tetris\Etapa 2\Spec Kit\docs\coverage.xml | D:\KEVIN\UNIVERSIDAD\Trabajos\Proyecto\Caso 2-Tetris\Etapa 2\Spec Kit\docs\backend-coverage.log; exit 0 |
| frontend-tests-and-coverage | C:\Program Files\nodejs\npm.cmd run test -- --coverage | D:\KEVIN\UNIVERSIDAD\Trabajos\Proyecto\Caso 2-Tetris\Etapa 2\Spec Kit\docs\frontend-test-coverage.log; exit 0 |
| frontend-production-build | C:\Program Files\nodejs\npm.cmd run build | D:\KEVIN\UNIVERSIDAD\Trabajos\Proyecto\Caso 2-Tetris\Etapa 2\Spec Kit\docs\frontend-build.log; exit 0 |
| frontend-dependency-audit | C:\Program Files\nodejs\npm.cmd audit --json | D:\KEVIN\UNIVERSIDAD\Trabajos\Proyecto\Caso 2-Tetris\Etapa 2\Spec Kit\docs\npm-audit.json; exit 0 |

Backend: 35 pruebas aprobadas; cobertura de sentencias 92%. Frontend: 38 pruebas aprobadas. Cobertura frontend: Statements 80.26%; Branches 70.25%; Functions 97.14%; Lines 84.07%. npm audit reporta cero vulnerabilidades.

SonarQube: gate **OK**, análisis `acca3bf6-e8bc-4c46-8db4-932b8609326c`, tarea `c3a9e639-7e05-4398-b9fd-3004cfdabb9f` con SUCCESS. Se verifican la última tarea, el gate exacto, los hashes actuales XML/LCOV y las condiciones sin cambios: nueva cobertura ≥80 %, duplicación nueva ≤3 % y cero observaciones nuevas.

| Medida Sonar de producción | Línea base | Primer escaneo Etapa 2 | Final |
| --- | ---: | ---: | ---: |
| Quality gate | OK | ERROR | OK |
| Cobertura global (%) | 62.0 | 57.4 | 83.9 |
| Bugs | 0 | 0 | 0 |
| Vulnerabilidades | 2 | 0 | 0 |
| Hotspots | 0 | 0 | 0 |
| Code smells | 7 | 7 | 0 |
| Duplicación (%) | 0.0 | 0.0 | 0.0 |
| Complejidad | 110 | 161 | 194 |
| Complejidad cognitiva | 78 | 103 | 148 |
| ncloc | 748 | 1013 | 1098 |
| Deuda técnica (min) | 35 | 35 | 0 |
| Rating mantenibilidad | 1.0 | 1.0 | 1.0 |
| Rating fiabilidad | 1.0 | 1.0 | 1.0 |
| Rating seguridad | 3.0 | 1.0 | 1.0 |

Cobertura nueva final: 86.6 %. El OK de línea base carecía de un período nuevo comparable y no se interpreta como aceptación final. Los ratings nativos de Sonar se muestran en su escala numérica (1 equivale a A). La cobertura global no equivale a la cobertura aislada backend/frontend. Sonar no mide escalabilidad; no se calcula una puntuación de escalabilidad ni se infiere rendimiento sin una carga ejecutada.

## Aceptación: veinte escenarios y mecanismos

El checker común devuelve siete registros aprobados que cubren ocho IDs distintos; el control suplementario S2-16 añade nueve comprobaciones HTTP sin añadir IDs al catálogo. La siguiente matriz registra evidencia de API, dominio, pruebas de interfaz y navegador por separado. Los fixtures de tres/cuatro filas son dominio aislado; no se presentan como partidas alcanzables ni como pruebas manuales de UI. No se calcula una tasa de gameplay a partir de estos mecanismos combinados.

| ID | Estado | Mecanismo | Evidencia |
| --- | --- | --- | --- |
| S2-01 | pass | external_api_and_production_unit | acceptance-api.json; backend/tests/unit/test_qa_iteration1.py::test_qa04_restart_dirty_cleanup; backend-coverage.log |
| S2-02 | pass | external_api_full_response_equality_and_route_draw_spy | acceptance-api.json; backend/tests/unit/test_qa_iteration1.py; backend-coverage.log |
| S2-03 | pass | external_api_and_real_tick_domain | acceptance-api.json; backend/tests/unit/test_game_engine_us1.py::test_scoring_rules_production; backend/tests/unit/test_qa_iteration1.py::test_qa02_random_draw_counts; backend-coverage.log |
| S2-04 | pass | controlled_reachable_horizontal_I_real_tick | backend/tests/unit/test_game_engine_us1.py::test_scoring_rules_production; backend/tests/integration/test_api_us2.py::test_api_line_clear_integration; backend-coverage.log |
| S2-05 | pass | controlled_reachable_O_piece_real_tick | backend/tests/unit/test_game_engine_us1.py::test_scoring_rules_production; backend-coverage.log |
| S2-06 | pass | isolated_domain_mocked_three_row_result_real_production_scoring | backend/tests/unit/test_game_engine_us1.py::test_scoring_rules_production; acceptance-review-notes.md; backend-coverage.log |
| S2-07 | pass | isolated_domain_mocked_four_row_result_real_production_scoring | backend/tests/unit/test_game_engine_us1.py::test_scoring_rules_production; acceptance-review-notes.md; backend-coverage.log |
| S2-08 | pass | controlled_reachable_9_to_10_and_9_to_11_real_tick | backend/tests/unit/test_game_engine_us1.py::test_level_transitions_and_gravity_floor_production; backend-coverage.log |
| S2-09 | pass | controlled_production_level_9_and_10_floor | backend/tests/unit/test_game_engine_us1.py::test_level_transitions_and_gravity_floor_production; backend-coverage.log |
| S2-10 | pass | external_api_and_exact_random_draw_spy | acceptance-api.json; backend/tests/unit/test_qa_iteration1.py::test_qa02_random_draw_counts; backend-coverage.log |
| S2-11 | pass | external_api_full_equality_and_production_snapshot | acceptance-api.json; backend/tests/unit/test_qa_iteration1.py::test_qa03_immutable_deep_state_snapshots; backend-coverage.log |
| S2-12 | pass | external_api_lock_swap_and_exact_draw_spy | acceptance-api.json; backend/tests/unit/test_qa_iteration1.py::test_qa02_random_draw_counts; backend-coverage.log |
| S2-13 | pass | controlled_blocked_Hold_spawn_production_domain | backend/tests/unit/test_game_engine_us2.py::test_hold_obstructed_spawn; backend-coverage.log |
| S2-14 | pass | production_full_state_snapshots_all_move_tick_Hold_actions | backend/tests/unit/test_qa_iteration1.py::test_qa03_immutable_deep_state_snapshots; backend/tests/unit/test_qa_iteration1.py::test_qa02_random_draw_counts; backend-coverage.log |
| S2-15 | pass | external_api_and_fully_dirty_domain_restart | acceptance-api.json; backend/tests/unit/test_qa_iteration1.py::test_qa04_restart_dirty_cleanup; backend-coverage.log |
| S2-16 | pass | external_HTTP_contract_all_five_success_routes_and_four_missing_ID_routes | acceptance-api.json; acceptance-contract.json; acceptance-provenance.json |
| S2-17 | pass | generated_rendered_geometry_controls_and_actual_browser | frontend/tests/App.test.tsx; frontend/tests/useGame.test.ts; frontend-test-coverage.log; browser-evidence.json |
| S2-18 | pass | deferred_fetch_body_and_owned_timer_fake_clock_plus_actual_browser | frontend/tests/useGame.test.ts; frontend-test-coverage.log; browser-evidence.json; qa16-final-review.md |
| S2-19 | pass | inherited_backend_assertion_preservation_executed_regression_and_actual_browser_controls | qa09-final-review.md; backend-coverage.log; frontend-test-coverage.log; browser-evidence.json |
| S2-20 | pass | independent_production_TypeScript_build_recorded_dependencies | frontend-build.log; verification-commands.json; frontend/package-lock.json |

## Capturas y evidencia reproducible

- Actual local UI after QA4: initial counters, board, next preview and empty Hold. Gravity continued while capturing. — `screenshots/app-final-initial.jpg`; procedencia `actual_ui`. Fuentes originales: .
- Actual local UI after QA4: occupied Hold, next preview, board and disabled Hold control before the next lock. — `screenshots/app-final-hold.jpg`; procedencia `actual_ui`. Fuentes originales: .
- Actual local UI after QA4: naturally reached game-over state and restart modal. — `screenshots/app-final-game-over.jpg`; procedencia `actual_ui`. Fuentes originales: .
- Vista derivada de métricas por invocación y tamaños de artefactos; no es una captura de consola. — `screenshots/metrics-panel.jpg`; procedencia `derived_panel`. Fuentes originales: metrics.json.
- Vista derivada de intentos API, errores, éxitos y respuestas JSONL, con denominadores separados. — `screenshots/requests-panel.jpg`; procedencia `derived_panel`. Fuentes originales: metrics.json.
- Vista derivada de la API autenticada de SonarQube y registros de pruebas; no es la interfaz web de SonarQube. — `screenshots/sonar-panel.jpg`; procedencia `derived_panel`. Fuentes originales: sonar-summary.json; sonar-exact-quality-gate.json; sonar-verification.json; backend-coverage.log; frontend-test-coverage.log.
- Visor derivado de los registros originales de pruebas, compilación y auditoría; no es una consola nativa. — `screenshots/tests-panel.jpg`; procedencia `derived_panel`. Fuentes originales: verification-commands.json; backend-coverage.log; frontend-test-coverage.log; frontend-build.log; npm-audit.json.

No se obtuvo una captura autenticada de la interfaz web de SonarQube: la pantalla solicita iniciar sesión. La evidencia de métricas procede de la API local autenticada y sus registros conservados; los paneles derivados se identifican como tales y no se presentan como consola/interfaz Sonar original.

Los paneles derivados, cuando existen, son visualizaciones de registros y no capturas de la interfaz original de Sonar/CLI. Las observaciones de navegador, hashes del backend/checker y origen del servidor están en `browser-evidence.json` y `acceptance-provenance.json`.

## Corpus y límites del estudio

El corpus final incluye sólo Markdown nativo de la feature, tanto por archivo como unificado, con manifiesto y hashes en `bertopic-corpus/final/`. Excluye JSON/OpenAPI, documentación del investigador, transcritos, templates y código de aplicación. No se ha ajustado un modelo BERTopic ni se atribuyen temas, embeddings o puntajes a esta preparación.

No se estima tiempo humano, costo global, escalabilidad ni actividad oculta. Los transcritos interrumpidos, el uso auxiliar y las diferencias de conservación entre herramientas permanecen documentados. Una afirmación futura sobre otro código requiere repetir las comprobaciones que cambien de alcance.

## Fuentes locales

- `13-input-replay-verification.json`
- `13-qa-completion-retry.stdout.json`
- `acceptance-api.json`
- `acceptance-contract.json`
- `acceptance-matrix.json`
- `acceptance-provenance.json`
- `bertopic-corpus/final/manifest.json`
- `browser-evidence.json`
- `environment.json`
- `generation-08/metrics.json`
- `input-audit.json`
- `metrics.json`
- `npm-audit.json`
- `question-audit.json`
- `sonar-baseline/sonar-summary.json`
- `sonar-exact-quality-gate.json`
- `sonar-exact-task.json`
- `sonar-initial/sonar-summary.json`
- `sonar-open-issues.json`
- `sonar-summary.json`
- `sonar-task.json`
- `sonar-verification.json`
- `verification-commands.json`
- `RESEARCH_LOG.md`, `MEASUREMENT_COMPLETENESS.md`, `qa09-final-review.md` y snapshots de generación/corrección.
