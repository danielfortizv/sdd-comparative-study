# Cierre académico y experimental — Shift Bank Etapa 3 — OpenSpec

**Fecha de cierre documental:** 17 de noviembre de 2026  
**Proyecto:** `Shift-Bank---Stage-3---OpenSpec`  
**Directorio evaluado:** `Etapa 3/OpenSpec`  
**Cambio OpenSpec:** `stage3-banking-security-load-deployment` (`spec-driven`)  
**Framework:** OpenSpec 1.11.0 · **Agente:** OpenAI Codex CLI

## 1. Resumen ejecutivo

La implementación aprobada de Stage 3 se completó en cuatro bloques: protección y migración de datos bancarios sensibles, auditoría transaccional y atomicidad, carga reproducible con Locust y despliegue local con Docker Compose. El cambio registra 21/21 tareas completas. La evidencia conserva suites de regresión, prueba de concurrencia multiproceso, ejecución Locust, aceptación de despliegue y dos análisis SonarQube distintos. No se repitieron pruebas, escaneos, benchmarks ni despliegues durante este cierre.

La comparación SonarQube muestra 5→0 Bugs, 47→34 Code Smells activos y 52→34 hallazgos tradicionales, con deuda estimada 301→223 minutos. La reconciliación por identificador confirma 19 incidencias iniciales resueltas, 33 persistentes y una incidencia nueva: `python:S1481` por una variable local `rec` sin uso en `backend/banking.py`. Esta nueva incidencia explica que 19 incidencias resueltas produzcan una reducción neta de 18. El Quality Gate fue OK en ambos análisis, aunque el extracto inicial no incluyó condiciones y el final sí expuso tres; por ello se reportan los estados, pero no se presenta la configuración del gate como una comparación plenamente equivalente.

La evidencia respalda el cierre técnico de OpenSpec. El cierre académico queda **calificado** por telemetría D1 no disponible, acceso HTTP 403 a los detalles de Security Hotspots, diferencia observada en las condiciones del Quality Gate y ausencia de la matriz protocolaria que define individualmente AC-15 y AC-16. No se atribuye causalidad experimental más allá de lo que permite la comparación de un proyecto y una sola ronda correctiva.

## 2. Identidad, entorno y mediciones

| Elemento | Evidencia |
|---|---|
| SonarQube inicial | CE task `ea27677b-df48-4d54-9b89-25ac686bce41`, `SUCCESS`; analysis ID `5242ca1c-0d7b-4acc-961a-e538fb54f1f1`; proyecto y clave coinciden |
| SonarQube final | CE task `82f9f447-63ba-462a-8d43-f71582e4f365`, `SUCCESS`; analysis ID `1a39a34f-ee2e-44f5-9a1c-f569e22bf717`; mismo proyecto |
| Instantes CE | Inicial: `2026-11-17T00:40:14+0000`; final: `2026-11-17T19:54:29+0000` |
| SonarQube / scanner | Community Build `26.9.0.129388`; SonarScanner CLI `8.1.0.6389`, imagen congelada `sdd-sonar-scanner:frozen` |
| Herramientas de código/cobertura | Python 3.13; Node 24.19.0; npm 11.17.0; coverage.py 7.17.3; c8 12.0.0 |
| Plataforma de carga | Windows 11 build 10.0.26300; Python 3.13.2; Locust 2.47.0; FastAPI 0.142.2; Uvicorn 0.54.0; SQLite 3.45.3 |
| Identidad del benchmark | `RUN_01_20261116T201253Z`, carga local HTTPS y SQLite sintético aislado |
| Identidad del despliegue | `DEPLOYMENT_20261116T211350Z`, proyecto Compose aislado, aceptación final 50/50 |

Los dos análisis son distintos y pertenecen a la misma clave de proyecto. Las extracciones originales son la fuente autoritativa; sus archivos no se alteraron. Se calcularon hashes para las extracciones, fuentes y entregables en `E3_OPENSPEC_INDICE_EVIDENCIAS_SHA256.json`.

## 3. D1 — Esfuerzo del agente y del investigador

| Métrica | Registro disponible | Lectura metodológica |
|---|---|---|
| Tokens In / Cache / Out | N/D | No se expuso telemetría de sesión verificable |
| Crédito/costo | N/D | No se estimó costo sin uso y tarifa observables |
| Mensajes del agente / llamadas de herramienta | N/D | No existe contador normalizado conservado |
| Duraciones visibles de Codex | Especificación 4:04; Bloque 1 16:58; Bloque 2 18:31; Bloque 3 20:01; Bloque 4 1:08:49 | Suma de esos cinco indicadores: 2:08:23. Es una suma parcial de tiempos mostrados por la interfaz, no tiempo de CPU ni duración total del estudio |
| Hito 7–9, corrección Sonar y cierre | N/D | No se registró una duración visible comparable para todos esos tramos |
| Intervención humana | Aprobaciones D-E3-01..04; aprobación de especificaciones; autorizaciones explícitas para Bloques 1–4 y Hito 8; ejecución investigadora del escaneo final | Se documentan los puntos de autorización, pero no se inventa un total de prompts, turnos ni minutos de intervención |

Las duraciones anteriores provienen de los registros académicos por bloque. No deben sumarse a los tiempos internos del scanner, al tiempo CE ni al tiempo de ejecución del benchmark.

## 4. D2 — Calidad del código y comparación SonarQube

| Métrica | Inicial | Final | Cambio |
|---|---:|---:|---:|
| NCLOC | 1.859 | 1.866 | +7 (+0,38 %) |
| Líneas físicas | 2.219 | 2.226 | +7 (+0,32 %) |
| Bugs | 5 | 0 | −5 (−100 %) |
| Vulnerabilidades | 0 | 0 | Sin cambio |
| Code Smells activos | 47 | 34 | −13 (−27,66 %) |
| Hallazgos tradicionales | 52 | 34 | −18 (−34,62 %) |
| Hallazgos/KLOC | 27,972 | 18,221 | −9,751 (−34,86 %) |
| Deuda técnica estimada | 301 min | 223 min | −78 min (−25,91 %) |
| Complejidad ciclomática | 528 | 528 | Sin cambio |
| Complejidad cognitiva | 464 | 464 | Sin cambio |
| Duplicación | 0,0 % | 0,0 % | Sin cambio |
| Cobertura global | 80,7 % | 80,8 % | +0,1 puntos porcentuales |
| Cobertura de líneas | 80,8 % | 80,9 % | +0,1 puntos porcentuales |
| Líneas por cubrir | 1.163 | 1.170 | +7 |
| Líneas sin cubrir | 223 | 223 | Sin cambio |
| Reliability Rating | C (3,0) | A (1,0) | Mejora de C a A |
| Security Rating | A (1,0) | A (1,0) | Sin cambio |
| Maintainability Rating | A (1,0) | A (1,0) | Sin cambio |

Fórmula aplicada: `Hallazgos = Bugs + Vulnerabilities + Code Smells`; `Hallazgos/KLOC = Hallazgos / (NCLOC / 1.000)`. MQR se mantiene separado de los tipos tradicionales: issues de reliability 5→0, security 0→0 y maintainability 47→34. `software_quality_maintainability_debt` no está disponible y no se imputó.

**Quality Gate:** inicial OK con `conditions: []`; final OK con condiciones satisfechas para `new_coverage` (80 % mínimo, valor 84,1 %), `new_duplicated_lines_density` (máximo 3 %, valor 0,0 %) y `new_violations` (máximo 0, valor 0). El estado OK no prueba ausencia de defectos. La evidencia no permite determinar por qué el conjunto de condiciones expuesto por la API difiere entre extracciones; por tanto, la comparación del gate se limita a sus estados y condiciones observadas.

**Hotspots:** la métrica agregada es 0 en ambos análisis, pero los dos endpoints de detalle devolvieron HTTP 403. No se afirma que los hotspots hayan sido revisados individualmente.

### Alcance y cobertura SonarQube

El hash de `sonarqube/sonar-project.properties` es `c6d52175bc0623c3c5b64fad0dbe705fb9f8e3cbaf3862466bf8e47277f87ee1`, igual al registrado en la configuración inicial. Ambos análisis declaran los mismos 14 archivos productivos: cinco módulos backend y nueve archivos en `frontend/src`. Las exclusiones, `sonar.tests=backend/tests,frontend/tests`, versiones de lenguaje, perfiles `Sonar way` para CSS/JS/Python/TypeScript y rutas de cobertura permanecieron iguales. La configuración de propiedades y los manifiestos SHA-256 de fuentes sustentan la comparación.

Los 20 archivos indexados inicialmente se reconcilian como 14 productivos + 6 de prueba (cinco backend y uno frontend). El análisis final indexó 21: 14 productivos + 7 de prueba. El archivo adicional es `frontend/tests/button-types.test.mjs`, ubicado bajo `frontend/tests`, clasificado como prueba por la misma ruta `sonar.tests`; no aumentó el inventario productivo. El hallazgo `python:S1481` final tiene `scope=MAIN`, independiente de ese archivo adicional.

Los sensores procesaron Cobertura Python y LCOV JavaScript/TypeScript en ambos análisis sin advertencias de importación. La instrumentación se mantuvo en los módulos backend y los tres módulos frontend `.mjs`; los componentes React TSX no tienen cobertura LCOV medida. Para hacer accesible dentro del contenedor la ruta `source` del XML Cobertura final, se normalizó esa ruta absoluta de Windows a `/usr/src/backend`; no se cambió el código ni los conteos cubiertos. El scanner final registró la importación de `backend-coverage-sonar.xml` y LCOV.

## 5. Reconciliación de incidencias

El export inicial contiene 52 incidencias abiertas. El export final contiene 53 registros porque SonarQube conserva los registros resueltos: 19 con estado `CLOSED`/`FIXED`, 33 incidencias iniciales aún abiertas y una nueva incidencia abierta. Así, el total activo de métricas es 34. Los cinco Bugs iniciales están cerrados; de 47 Code Smells iniciales, 14 están cerrados y 33 persisten. El nuevo Code Smell eleva los activos finales a 34.

**Resueltas (19):** cinco `typescript:S9011` por tipo explícito de botón; siete `python:S1192` por literales repetidos; dos `python:S1172` por parámetros ACH sin uso; tres `python:S5713` por clases de excepción redundantes; y dos `python:S8415` por respuestas OpenAPI no documentadas. Las claves completas se incluyen en `E3_OPENSPEC_RECONCILIACION_HALLAZGOS_SONAR.csv`.

**Persistentes (33):** los mismos issue keys, reglas, archivos y mensajes continúan abiertos; seis se desplazaron exactamente cinco líneas en `backend/banking.py` por los cambios previos. No se interpretan como hallazgos nuevos: sus identidades estables no cambiaron. Las seis claves desplazadas son `80d3bea2-3943-4580-8ca7-34d07f713921`, `95595748-ac3f-4b3a-bb16-431c5eda62df`, `b81a44f5-c7eb-4fca-804c-335872d0eac0`, `d5ce429d-45e7-4032-a864-9e3f0eb38f16`, `da59d531-db25-4f5e-84b3-10ccaf61e0a6` y `fceb6e85-c378-4021-8473-baa8e5a10ac8`.

**Nueva (1):** `28eea554-7c34-4d1e-959b-9ee8c19a3805`, `python:S1481`, MINOR, `backend/banking.py:342`: variable local `rec` sin uso. Su ubicación y contenido concuerdan con la eliminación previa del argumento `rec` en `_accept_ach`, aunque el análisis no establece causalidad formal por sí solo. Esta ronda de cierre fue documental y no hizo una segunda corrección.

La reducción neta se explica así: 52 activos iniciales − 19 resueltos + 1 nuevo = 34 activos finales. El desglose de cada clave inicial y final, estado, ubicación y mensaje queda en el CSV de reconciliación.

## 6. D3 — Especificación, implementación y trazabilidad

El cambio OpenSpec conserva `proposal.md`, `design.md`, `tasks.md` y cinco especificaciones de capacidad: `banking-data-protection`, `transaction-audit`, `load-testing`, `local-deployment` y `banking-compatibility`. El conteo físico de esas cinco especificaciones es 18 requisitos y 43 escenarios; `tasks.md` contiene 21 tareas, todas marcadas completas. `openspec.cmd validate --all --strict` registró 6 aprobados, 0 fallidos.

| Capacidad | Evidencia de implementación/pruebas |
|---|---|
| Datos bancarios | `backend/encryption.py`, `database.py`, `test_encryption.py`, `test_banking.py`, `test_api.py`; AES-256-GCM, claves versionadas externas, migración idempotente/rollback y compatibilidad |
| Auditoría transaccional | `backend/audit.py`, `test_audit.py`, `test_banking.py`, `test_api.py`; cadena HMAC, fallos/atomicidad, procesos concurrentes y verificación tras reinicio |
| Load testing | `backend/loadtest/`, `test_loadtest_metrics.py`, `E3_OPENSPEC_LOCUST_RUN_01.json` y CSV originales |
| Despliegue local | `deployment/`, `verify_deployment.py`, `E3_OPENSPEC_DEPLOYMENT_ACCEPTANCE.json` y registros HTTPS/restart |
| Compatibilidad heredada | `test_banking.py`, `test_api.py`, regresión completa y aceptación desplegada AC-01 |

La trazabilidad está disponible por capacidad, tareas y evidencia de suites/escenarios. No se encontró una matriz separada que enlace uno a uno los 18 requisitos y 43 escenarios con cada función y cada prueba; no se presenta una cobertura de requisitos más granular que la documentada. Se preservaron el cambio Stage 2 activo, sus contratos y las especificaciones comunes. No se sincronizó ni archivó el cambio.

## 7. D4 — Matriz AC-01 a AC-16

La evidencia local cita AC-01 y AC-05–14; las autorizaciones y registros del Bloque 1 agrupan AC-02–04. No se encontró en los archivos disponibles una copia íntegra de la matriz protocolaria ni definiciones individuales para AC-15 y AC-16. Los renglones 02–04 reconstruyen los grupos de verificación del contrato de cifrado; 15–16 quedan parciales y no reciben criterios inventados.

| Caso | Criterio operativo usado | Estado | Evidencia y limitación |
|---|---|---|---|
| AC-01 | Regresión bancaria heredada, incluida la operación por API desplegada | PASS | Bloques 2 y 4; suite backend, frontend y aceptación de despliegue |
| AC-02 | Cifrado autenticado, round-trip y detección de ciphertext alterado | PASS | `E3_OPENSPEC_BLOCK1_ENCRYPTION.md`; pruebas de cifrado/descifrado e integridad |
| AC-03 | Claves externas, fallos cerrados y transporte HTTPS sin fallback HTTP | PASS | Bloque 1 y pruebas API; despliegue AC-12 |
| AC-04 | Migración heredada idempotente, rollback y persistencia/reinicio | PASS | Bloque 1: fixtures sintéticos, rollback e idempotencia; reinicio verificado |
| AC-05 | Cadena de auditoría criptográfica válida y verificable tras reinicio | PASS | `E3_OPENSPEC_BLOCK2_AUDIT.md`; cadena multiproceso final consistente |
| AC-06 | Detección de alteración/eliminación/inserción/reordenamiento y append-only | PASS | Bloque 2; garantía limitada según modelo de amenaza aprobado |
| AC-07 | Atomicidad financiera al fallar autorización o persistencia de auditoría | PASS | Bloque 2; inyección de errores, rollback de transferencia/ACH/beneficiario y límites |
| AC-08 | Rechazos y fallos MFA durables sin autorizar la operación ni guardar el código | PASS | Bloque 2; evento de rechazo, estado MFA y balances verificados |
| AC-09 | Concurrencia real de procesos y lector/escritor SQLite | PASS | Cuatro procesos del sistema operativo; dos conexiones WAL; validación después de reinicio |
| AC-10 | Perfil Locust, ventana completa estable y mezcla observada | PASS | RUN_01: 30 usuarios, 5 usuarios/s, 60,003 s estables; mezcla observada 60,443/29,674/9,882 % |
| AC-11 | Umbrales estrictos de latencia y errores | PASS | RUN_01: lecturas combinadas p95 121,835 ms; transferencias p95 437,330 ms; 0/7.397 errores inesperados |
| AC-12 | Compose, HTTPS, redirect, proxy, healthchecks y secretos externos | PASS | Despliegue real, aceptación 50/50; puertos loopback y backend no publicado |
| AC-13 | Persistencia cifrada/auditada, reinicio, usuario no root y scheduler único | PASS | Despliegue AC-13; balances, historial, auditoría, volumen y recuperación recurrente comprobados |
| AC-14 | Regresión completa, build de producción y validación estricta | PASS | Bloque final: 54 backend, 9 frontend, build TypeScript/Vite, validación strict 6/0 |
| AC-15 | Definición individual no disponible en la fuente protocolaria recuperada | PARTIAL | La medición inicial SonarQube existe y está vinculada al CE baseline; faltan criterios AC-15 y el detalle de hotspots devolvió 403 |
| AC-16 | Definición individual no disponible en la fuente protocolaria recuperada | PARTIAL | La medición final y su comparación existen; las condiciones Gate expuestas difieren y hotspots devolvió 403 |

AC-15/16 son parciales por indisponibilidad de su definición, no porque no se haya ejecutado SonarQube. La matriz debe sustituirse o ratificarse por la versión protocolaria autorizada si se requiere conformidad estricta con esos números.

## 8. D5 — Aprobaciones, retroalimentación y desviaciones

- El investigador aprobó las decisiones D-E3-01 a D-E3-04, el baseline de especificación y las autorizaciones separadas para los Bloques 1–4 y la única ronda correctiva Hito 8. El escaneo final y su extracción se realizaron después, según el registro Hito 9.
- La extracción inicial tuvo intentos de API con HTTP 401; se conserva esa evidencia. Posteriormente el investigador obtuvo extracción autenticada: CE, medidas, gate e issues respondieron 200. Los detalles de hotspots respondieron 403 en ambos momentos.
- El primer intento de escaneo final falló por una ruta Windows absoluta en el atributo `source` del XML Cobertura Python dentro de Docker. Se normalizó la ruta del reporte para el mount del contenedor y el siguiente scanner terminó con `EXECUTION SUCCESS`; no se modificó código ni conteos de cobertura.
- El alcance indexado pasó de 20 a 21 por la prueba adicional `frontend/tests/button-types.test.mjs`, clasificada como prueba; el alcance productivo y el hash de propiedades se mantuvieron.
- Las condiciones Gate recuperadas cambiaron de un arreglo vacío en la extracción inicial a tres condiciones satisfechas en la final. No se puede establecer con la evidencia actual si se deben a nueva elegibilidad de métricas de código nuevo o a un cambio externo de configuración; se conserva como desviación de comparabilidad.
- El agente registró iteraciones de comandos y correcciones en los bloques previos; la finalización de cobertura, tests y reportes se conserva. No se repitieron el benchmark RUN_01 ni la aceptación de Docker.
- No se accedió a implementaciones de otras herramientas SDD ni se modificaron Stage 1, Stage 2 o `SEED-3.md` durante este cierre. No se archivó ni sincronizó OpenSpec y no se creó un commit.

## 9. Limitaciones metodológicas

1. No se localizó un documento independiente de protocolo/métrica que contenga la matriz AC completa; `SEED-3.md`, el registro de interacción y `bitacora.md` conservan los requisitos, pero no definen AC-15 y AC-16 individualmente.
2. Los detalles de Security Hotspots no son verificables por HTTP 403; el valor agregado 0 no equivale a revisión humana de hotspots.
3. Quality Gate quedó OK en ambos análisis, pero las condiciones recuperadas no son idénticas. La comparación de Gate es indicativa, no una prueba bajo condición exactamente constante.
4. La modificación del XML Cobertura fue un ajuste de ruta para el contenedor; se conservó instrumentación y configuración, pero el reporte final no es byte a byte igual al reporte inicial.
5. El frontend LCOV cubre únicamente tres archivos `.mjs`; no mide componentes React TSX. El aumento de 0,1 puntos de cobertura debe leerse junto con el aumento de siete líneas por cubrir y 223 líneas descubiertas, sin atribución causal automática.
6. El benchmark es un único RUN_01 en entorno local/sintético; no acredita capacidad de producción ni variabilidad entre repeticiones. CPU y memoria no fueron medidas.
7. Sin telemetría de tokens, costo, tool calls, duración total normalizada o conteo de intervenciones, D1 solo puede informarse parcialmente.
8. Existe una incidencia nueva `S1481` sin corregir al cierre documental; no se autorizó una segunda ronda. Las 33 incidencias iniciales persistentes también quedan como deuda técnica observada.
9. El Quality Gate OK no prueba que el proyecto carezca de defectos. La comparación es antes/después de una intervención, sin grupo de control, y debe redactarse como asociación observada.

## 10. Reproducibilidad y trazabilidad

Las extracciones de SonarQube se conservan en `sonarqube/EXTRACCION_INICIAL_20261117T141345069/` y `sonarqube/EXTRACCION_FINAL_20261117T145759941/`. Los logs originales de scanner son `E3_OPENSPEC_SONAR_SCAN_20261116T193919.log`, `E3_OPENSPEC_SONAR_SCAN_20261117T144816.log` (fallido) y `E3_OPENSPEC_SONAR_SCAN_20261117T145330.log` (exitoso). La configuración congelada es `sonarqube/sonar-project.properties`; no la cambie para reproducir el análisis.

Comandos conservados en evidencia: backend `python -m unittest discover -s tests -v`; frontend `npm.cmd test`; build `npm.cmd run build`; OpenSpec `openspec.cmd validate --all --strict`; Locust original `python backend\loadtest\run_benchmark.py --run-id RUN_01 --steady-seconds 60`; despliegue con `docker compose --project-name shift-bank-e3-openspec-block4 --env-file deployment/.env.local -f deployment/compose.yaml build` y `up -d`. Estos comandos describen ejecuciones registradas; no se ejecutaron durante este cierre.

La reproducción SonarQube usa el scanner congelado y `sonarqube/sonar-project.properties`, con `SONAR_TOKEN` transferido por variable de entorno (nunca como argumento literal). Compare únicamente contra analysis ID `5242ca1c-0d7b-4acc-961a-e538fb54f1f1`, espere el nuevo CE `SUCCESS` y exporte sus métricas/issues. No se incluye ni requiere ningún valor de credencial en el informe.

El índice de evidencia SHA-256 relaciona las fuentes y artefactos clave. El resumen numérico y la matriz AC también se entregan como JSON, y el cruce completo por issue key como CSV.

## 11. Conclusiones y evaluación de cierre

La evidencia disponible confirma la implementación de las capacidades Stage 3 aprobadas, sus regresiones finales y una reducción cuantificada de hallazgos activos y deuda SonarQube. La mejora más clara es reliability: 5 Bugs a 0 y rating C a A. La deuda SonarQube cayó 78 minutos; mantenibilidad permaneció en A y complejidad agregada no cambió. El detalle por issue key muestra que se resolvieron 19 incidencias, persistieron 33 y apareció una incidencia menor nueva. La medición de cobertura aumentó 0,1 puntos, sin disminuir las 223 líneas sin cubrir.

**Evaluación:** el trabajo OpenSpec está completo en su dimensión técnica (21/21 tareas). Este informe y sus artefactos dejan completada la consolidación documental con las limitaciones observadas. Es **apto para cierre académico formal como estudio de caso calificado**, siempre que el cierre mantenga visibles las limitaciones D1, hotspots, condiciones del Quality Gate y definiciones ausentes de AC-15/16. No debe presentarse como satisfacción plenamente demostrada de los 16 criterios canónicos ni como garantía de ausencia de defectos. Si la institución exige una matriz AC-01–AC-16 íntegra y D1 cuantitativo, se requiere recuperar esas definiciones/telemetría antes de declarar un cierre sin reservas.
