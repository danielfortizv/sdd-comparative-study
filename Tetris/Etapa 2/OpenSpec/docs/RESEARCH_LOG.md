# Tetris — Etapa 2, opción A: bitácora OpenSpec

Fecha local de cierre: 19 de octubre de 2026 (America/Bogotá). Todo quedó en `Caso 2-Tetris/Etapa 2/OpenSpec`; no se hizo commit ni push.

## Control experimental y procedencia

- Semilla común en inglés: `../../shared/seed.md`; SHA-256 `63919779DD4104076FBABCB130CE296A160FA840E0B4755A2AA5D90757ADA8EF`. El bloque común se anexó literalmente a los intentos iniciales o nuevos 01, 02 y 06–10 (siete invocaciones); 03–05 fueron aclaraciones de contexto sin repetirlo literalmente. La semilla maestra no cambió entre herramientas. Versiones fijadas: Gemini CLI 0.60.0, modelo Gemini 3.5 Flash en Vertex y OpenSpec 1.13.2.
- Las diez entradas enviadas están en `docs/*.prompt.txt`, sus metadatos en `docs/*.run.json`, las salidas en `docs/*.stdout.json` y los errores en `docs/*.stderr.txt`. `docs/token-audit.json` conserva el conteo recuperado de los transcritos JSONL para los intentos 02 y 05.
- Los intentos 01, 02, 05, 06 y 08 no escribieron código de aplicación. 03 creó los artefactos nativos; 04 corrigió el plan; 07 implementó el backend; 09 el frontend; 10 hizo la principal remediación SonarQube.
- **Intervención del investigador:** tras el intento 10 se sustituyeron dos literales repetidos en `backend/main.py` para cerrar las dos observaciones S1192 restantes. Se agregaron dos pruebas backend de control, dos archivos de pruebas frontend y configuración de Vitest/LCOV para validar la implementación. Estas modificaciones se consignan por separado de la salida atribuida a Gemini; la corrección manual de `main.py` no siguió estrictamente la regla del documento maestro de realizar todo cambio de código mediante una aclaración a la herramienta. No se debe atribuir este último ajuste a OpenSpec/Gemini en comparaciones entre herramientas. El cambio nativo ya incluía la tarea 6.2 de centralizar texto repetido, y la tarea 6.5 de cobertura se añadió antes de crear las pruebas frontend.
- El escaneo inicial corresponde al código producido por las invocaciones de la herramienta antes de la remediación. El escaneo intermedio (`docs/sonar-after-first-fix/`) corresponde a la remediación 10. El escaneo final incorpora las pruebas y el pequeño ajuste manual, por lo que se presenta como **resultado verificado con QA**, separado del resultado bruto.

## Medición de artefactos

Se cuentan archivos `.py`, `.ts`, `.tsx`, `.js`, `.jsx`, `.css` y `.html` bajo backend/frontend, incluidas pruebas. Se excluyen dependencias, compilados, cobertura generada, cachés, lockfiles y documentación. Fuente reproducible: `../../shared/collect-openspec-metrics.py` y `docs/metrics.json`.

| Alcance | Archivos | Líneas | Caracteres | Líneas/archivo |
| --- | ---: | ---: | ---: | ---: |
| Código base de Etapa 1 | 13 | 1.366 | 39.957 | 105,08 |
| Código final de Etapa 2, con pruebas de QA | 15 | 2.238 | 69.725 | 149,20 |
| Especificaciones nativas Etapa 1 | 4 | 442 | 23.969 | 110,50 |
| Especificaciones nativas Etapa 2 | 4 | 262 | 20.582 | 65,50 |

La comparación de código identifica 12 archivos distintos modificados o nuevos, 916 líneas añadidas y 44 eliminadas. Las especificaciones de Etapa 2 contienen 15 declaraciones de requisitos: 14 nuevas y una modificación al reinicio existente. Son conteos textuales; la métrica `ncloc` de SonarQube usa otro alcance y definición.

## Invocaciones de Gemini CLI

Los tokens de caché son parte de la entrada y no se suman nuevamente. El tiempo es la duración instrumentada de cada invocación, no el tiempo total de trabajo humano, de pruebas o de espera. 01 carece de estadísticas: no se imputan valores.

| Invocación | Duración s | Entrada | Caché | Salida | Solicitudes | Resultado |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 01-propose | no medido | no disponible | no disponible | no disponible | no disponible | interrupción de red aislada |
| 02-propose-retry | 622,436 | 1.586.942 | 1.262.951 | 15.910 | 66 | propuesta textual, sin archivos |
| 03-materialize-proposal | 137,359 | 2.141.393 | 1.591.392 | 6.694 | 23 | artefactos nativos creados |
| 04-correct-plan | 48,902 | 1.273.520 | 1.075.890 | 2.723 | 10 | aclaración del plan |
| 05-apply | 444,118 | 2.623.509 | 2.252.478 | 4.391 | 24 | interrumpido sin código |
| 06-apply-fresh | 782,457 | 2.011.596 | 1.407.507 | 56.094 | 66 | Plan Mode, sin código |
| 07-direct-apply | 167,938 | 382.138 | 197.261 | 6.667 | 14 | backend y pruebas |
| 08-complete-frontend | 12,868 | 127.382 | 8.020 | 134 | 2 | respuesta vacía |
| 09-frontend-fresh | 237,026 | 541.005 | 253.683 | 8.066 | 18 | frontend |
| 10-sonar-remediation | 409,430 | 2.994.533 | 2.495.552 | 8.443 | 60 | remediación principal |
| **Total observado** | **2.862,534** | **13.682.018** | **10.544.734** | **109.122** | **283** | 9 sesiones medibles de 10 |

Hay una aclaración correctiva del plan (04), una remediación de calidad después de implementar (10) y un ajuste manual final de QA; se distinguen de los reintentos por infraestructura o modo de ejecución. El comando slash `/opsx:apply` activó Plan Mode y negó escrituras en el intento 06; las invocaciones directas con la semilla y los artefactos OpenSpec permitieron la implementación.

## Verificación funcional y calidad

| Comprobación | Resultado | Evidencia |
| --- | --- | --- |
| Validación estricta OpenSpec | cambio válido | `docs/openspec-validation.log` |
| Pruebas backend | 20 aprobadas, 1 advertencia de dependencia | `docs/backend-coverage.log` |
| Cobertura backend de módulos de aplicación | 94 % | `docs/backend-coverage.log`, `docs/coverage.xml` |
| Pruebas frontend | 5 aprobadas | `docs/frontend-test-coverage.log` |
| Cobertura de líneas frontend | 92,96 % | `docs/frontend-test-coverage.log`, `frontend/coverage/lcov.info` |
| Controles externos de API | 7/7 aprobados; cubren ocho IDs del catálogo | `docs/acceptance-api.json` |
| Compilación y lint frontend | aprobados | `docs/frontend-build.log`, `docs/frontend-lint.log` |
| Auditoría npm tras actualizar dependencia vulnerable | 0 vulnerabilidades reportadas | `docs/frontend-npm-audit.json` y lockfile |
| SonarQube final | quality gate OK, cobertura total 90,3 %, cobertura de código nuevo 83,0 %, 0 bugs, 0 vulnerabilidades, 0 hotspots, 0 code smells, 0 % duplicación | `docs/sonar-summary.json`, `docs/sonar-quality-gate.json`, `docs/sonar-scan.log` |

SonarQube inicial: cobertura 61,8 %, 23 code smells, 5 vulnerabilidades, 0 bugs, 0 % duplicación, complejidad 141 y 1.290 `ncloc`. Final: cobertura 90,3 %, 0 code smells, 0 vulnerabilidades, 0 bugs, 0 % duplicación, complejidad 138 y 1.327 `ncloc`. El quality gate inicial también marcaba OK porque su período de código nuevo estaba vacío; el estado final sí satisface cobertura nueva ≥80 %, duplicación nueva ≤3 % y cero observaciones nuevas. Los dos escaneos finales usan el mismo alcance de fuentes que el inicial; las pruebas añadidas se excluyen del código de producción analizado.

La advertencia backend proviene de la dependencia Starlette TestClient (`httpx` deprecado); no es una falla de pruebas. El escaneo intermedio dejó una puerta ERROR por cobertura nueva 42,4 % y dos olores; se conserva para mostrar la secuencia completa. No se infiere un puntaje de escalabilidad de SonarQube.

## Catálogo de aceptación de 20 escenarios

El catálogo común está en `../../shared/acceptance/catalog.md`. La evidencia se distingue por mecanismo; no se afirma que los 20 escenarios se hayan ejecutado como pruebas negras de API. Los siete controles API cubren S2-01, 02, 03, 10, 11, 12, 15 y 16. Las pruebas controladas backend cubren S2-04, 05, 06, 07, 08, 09, 13, 14 y la regresión S2-19. Las pruebas de React cubren S2-17 y 18; el navegador local confirmó además el panel, Hold por botón y tecla C, el indicador LOCKED y el reinicio. S2-20 se verificó con el build. El caso S2-07 de cuatro filas es un control de regla de dominio; no se presenta como partida normal sin rotación. Mapa detallado: `docs/acceptance-matrix.md`.

## Capturas y límites

- `docs/screenshots/tetris-stage2-ui.png`: interfaz en Chrome local a 1440 × 1000.
- `docs/screenshots/metrics-panel.png`: panel local reproducible desde `docs/metrics.json` y salidas originales.
- `docs/screenshots/sonar-panel-final.png`: panel local reproducible desde la API de SonarQube y registros de pruebas; **no es una captura de la interfaz de SonarQube**.
- El primer intento de capturar la interfaz SonarQube mostró la pantalla de login; no se usó como evidencia de métricas. Se prefirieron respuestas JSON de la API autenticada y paneles con procedencia indicada.
- Al cierre original de OpenSpec, las otras cuatro herramientas de Etapa 2 seguían pendientes. Spec Kit comenzó el 20 de octubre de 2026 y conserva su propia bitácora; las restantes celdas comparativas todavía están pendientes.

## Auditoría de definiciones de medición — 20 de octubre de 2026

Durante Spec Kit se detectó que el agregado anterior de 283 solicitudes mezclaba intentos API con respuestas JSONL y se retiró como total comparable. La evidencia completa disponible acredita 127 intentos API, 3 errores y 124 éxitos en 03/04/07/08/09/10; los totales API de 01/02/05/06 son desconocidos. Por separado existen 229 respuestas documentadas: 139 retenidas actualmente (06=66, 09=18, 10=55) y 90 históricas (02=66, 05=24). Las dos solicitudes auxiliares exitosas de 10 están en el JSON CLI y no en el JSONL principal. No se suman estas categorías.

El colector de investigación fue corregido; el script y las métricas previas permanecen en `docs/measurement-before-definition-fix/`. `docs/measurement-definition-verification.json` acredita que no cambiaron código, pruebas, specs, duración conocida ni tokens observados: 13.682.018 entrada, 10.544.734 cacheados incluidos y 109.122 salida candidata. La cobertura de evidencia de uso es parcial y no equivale a una factura completa.

El archivo maestro de semilla permaneció idéntico. Los `.prompt.txt` prueban el archivo de entrada previsto, pero no bastan para demostrar la entrega efectiva completa en todos los mensajes: faltan entradas originales de varias sesiones, y las entradas retenidas de 06/09/10 no contienen el bloque completo. Esto limita la comparación estricta de entrega; no demuestra ausencia de contexto posterior ni modifica los resultados funcionales medidos. Los transcritos todavía disponibles se copiaron a `docs/transcripts-archive/` con manifiesto SHA-256 para preservar su contenido.



