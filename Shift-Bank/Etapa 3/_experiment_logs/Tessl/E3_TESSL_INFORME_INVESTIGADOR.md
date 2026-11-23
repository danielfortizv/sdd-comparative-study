# Informe experimental — Shift Bank, Etapa 3, Tessl

**Fecha:** 13 de noviembre de 2026  
**Caso de estudio:** Shift Bank — sistema bancario simulado  
**Etapa:** E3 — Seguridad, pruebas de carga y despliegue  
**Herramienta SDD:** Tessl  
**Agente de implementación:** Gemini CLI  
**Responsable del análisis:** Investigador del proyecto de grado

## 1. Objetivo y alcance

La tercera etapa consistió en evolucionar el sistema bancario desarrollado en las dos etapas anteriores, manteniendo el backend FastAPI, el frontend React/TypeScript y las funcionalidades bancarias heredadas.

La semilla común `SEED-3.md` estableció cuatro capacidades: cifrado de datos bancarios sensibles, registros de auditoría inmutables, pruebas de carga y despliegue de la aplicación.

Se utilizó Tessl para estructurar las especificaciones y Gemini CLI como agente encargado de implementar, corregir y verificar el código. La revisión de requisitos, aprobación de cambios y evaluación de resultados estuvo dirigida por el investigador.

## 2. D1 — Esfuerzo y consumo

Las métricas de esta dimensión deben extraerse de los registros originales de las sesiones Gemini CLI.

| Métrica | E3 Tessl | Observación |
|---|---:|---|
| Tok In | N/D | Agregación de sesiones E3 pendiente de verificar |
| Tok Cache | N/D | No duplicar entradas cacheadas |
| Tok Out | N/D | Agregación pendiente |
| Costo ($) | N/D | Requiere tarifas y desglose verificados |
| Msgs | N/D | No equivale al número de entradas de bitácora |
| Tool Calls | N/D | Total exclusivo de E3 pendiente |
| Tiempo (s) | N/D | Se debe definir si corresponde a tiempo activo o tiempo de reloj |

Se dispone de capturas parciales de estadísticas Gemini CLI, pero su atribución a cada etapa debe comprobarse mediante el directorio y la exportación original de la sesión.

Las 23 interacciones formales documentadas en la bitácora son unidades de seguimiento del investigador y no deben confundirse con el indicador `Msgs` de la herramienta.

## 3. D2 — Calidad del código generado

### 3.1. Evolución de SonarQube dentro de E3

| Métrica | Línea base con cobertura | Cierre final |
|---|---:|---:|
| LOC (`ncloc`) | 5.507 | 5.536 |
| Hallazgos | 85 | 72 |
| Hal/KLOC | 15,43 | 13,01 |
| Cob (%) | 78,0 % | 77,9 % |
| Bugs | 12 | 0 |
| Vulns | 2 | 0 |
| Smells | 71 | 72 |
| Deuda (m) | 450 | 491 |
| Comp. Cog. | 585 | 624 |
| Dupl. (%) | 0,6 % | 0,6 % |
| Rating | B / D / A | A / A / A |

*Orden de Rating: seguridad / fiabilidad / mantenibilidad, utilizando las métricas clásicas.*

Las intervenciones correctivas permitieron eliminar doce bugs asociados al uso de `assert` en el servicio de migración y dos vulnerabilidades identificadas por SonarQube en la ejecución privilegiada de los contenedores.

Sin embargo, la reducción de defectos de fiabilidad y seguridad estuvo acompañada de un incremento de la complejidad cognitiva y de la deuda técnica. El número de code smells pasó de 71 a 72.

### 3.2. Cobertura y Quality Gate

La ejecución final registró una cobertura global de 77,9 %, cobertura de líneas de 78,4 % y cobertura de ramas de 69,3 %.

La cobertura del código nuevo alcanzó 70,6 %, por debajo del umbral exigido del 80 %. Además, persistió una incidencia nueva de mantenibilidad en un archivo de pruebas.

Por estas razones, el Quality Gate final presentó estado **ERROR**.

El Quality Gate inicial mostró `OK` sin condiciones configuradas. Por tanto, los estados inicial y final no representan evaluaciones equivalentes y deben interpretarse con sus respectivos criterios.

### 3.3. Pruebas automatizadas

| Indicador | Resultado |
|---|---:|
| Pruebas backend | 86 aprobadas |
| Pruebas frontend | 39 aprobadas |
| Total | 125 aprobadas |
| Pruebas fallidas al cierre | 0 |
| Compilación frontend | Exitosa |

La aprobación de estas pruebas demuestra que los casos automatizados ejecutados tuvieron resultados satisfactorios. No implica ausencia de defectos ni cobertura total de todos los escenarios posibles.

### 3.4. Comparación respecto a E2

Tomando como referencia el cierre reportado para Tessl en la Etapa 2:

| Métrica | E2 final | E3 final |
|---|---:|---:|
| LOC | 4.267 | 5.536 |
| Hallazgos | 51 | 72 |
| Hal/KLOC | 11,95 | 13,01 |
| Deuda (m) | 276 | 491 |
| Comp. Cog. | 337 | 624 |
| Dupl. (%) | 0,8 % | 0,6 % |

El crecimiento de código fue aproximadamente del 29,7 %. Los hallazgos aumentaron un 41,2 %, aunque E3 terminó sin bugs ni vulnerabilidades bajo la clasificación clásica.

La comparación debe interpretarse considerando que la Etapa 3 incorpora nuevas capacidades de seguridad, auditoría y despliegue. No debe atribuirse todo incremento de complejidad a una menor calidad de Tessl.

Los valores `LOC Nu.`, `LOC Mod.` y `LOC Del.` quedan pendientes de una comparación reproducible entre los estados finales de E2 y E3; las cifras de cambios de una sesión Gemini no sustituyen ese análisis.

## 4. D3 — Especificaciones

| Métrica | Resultado E3 |
|---|---:|
| Archs .md | 11 |
| Lín. Spec | 1.093 |
| Densidad | 99,36 líneas/archivo |
| Ratio C/E | 5,06 |
| # Req | N/D — conteo estandarizado pendiente |
| Req/CLOD | N/D — depende del conteo anterior |

El inventario documental reporta además 65.380 bytes, 323 viñetas clasificadas automáticamente como cláusulas de requisitos y 248 referencias `[@test]`.

Estas cifras no deben equipararse automáticamente con el número de requisitos atómicos verificados. Durante el desarrollo también se reportaron 219 requisitos mediante otro procedimiento y se construyó una matriz con 24 agrupaciones de requisitos.

La discrepancia evidencia la necesidad de aplicar una sola regla de conteo antes de calcular las métricas definitivas `# Req` y `Req/CLOD`.

## 5. D4 — Expectativa funcional

| ID Req. | Aspecto Mín. | Estado | Reflexión |
|---|---|---|---|
| REQ-01 | Cifrado de datos bancarios sensibles | Cumplió dentro del contrato aprobado | Se implementó cifrado híbrido cliente-servidor y cifrado en reposo; el backend puede descifrar los campos necesarios para procesar operaciones |
| REQ-02 | Auditoría de transacciones | Cumplió dentro del modelo definido | Se incorporó encadenamiento criptográfico, control de integridad y protección contra modificaciones mediante SQLite |
| REQ-03 | Pruebas de carga | Cumplió | Se ejecutó un benchmark Locust en entorno sintético aislado |
| REQ-04 | Despliegue | Cumplió | Se verificó Docker Compose con FastAPI, Nginx, HTTPS y persistencia |

La evaluación no supone integración bancaria real ni certificación de seguridad productiva.

### Pruebas de carga

La ejecución reportada utilizó 30 usuarios virtuales, incremento de 5 usuarios por segundo y una ventana de medición estable de 60 segundos.

Se configuró una distribución de operaciones del 60 % en consultas de saldo, 30 % en historial y 10 % en transferencias internas.

Los resultados medidos fueron:

| Métrica | Resultado |
|---|---:|
| Solicitudes totales | 1.792 |
| Lecturas agregadas | 1.597 (89,1 %) |
| Transferencias internas | 195 (10,9 %) |
| Throughput | 29,9 solicitudes/s |
| p95 lecturas | 11 ms |
| p95 transferencias | 12 ms |
| Errores inesperados | 0 % |
| Rechazos de negocio | 0 |

El reporte disponible no permite afirmar los porcentajes individuales realmente observados para saldo e historial. La relación 60/30/10 representa la configuración del escenario.

Los resultados corresponden a una prueba local controlada y no son extrapolables directamente a producción.

### Despliegue

Se ejecutaron nueve pruebas de humo HTTPS, incluyendo consultas bancarias, cifrado, transferencias con MFA, verificación de auditoría y persistencia después de reiniciar contenedores.

El despliegue utilizó una base independiente del archivo SQLite histórico y posteriormente se reforzó la configuración para utilizar usuarios sin privilegios root y exigir secretos explícitos.

No se dispone de evidencia de un pipeline CI/CD completo. Por tanto, el resultado se clasifica como despliegue contenerizado y validación operacional, no como automatización integral de integración y entrega continua.

## 6. D5 — Retroalimentación humana

Se identificaron inconvenientes relevantes durante la generación, integración y verificación del sistema:

| Nº | Inconveniente | Relevancia | Explicación |
|---|---|---|---|
| 1 | Envío de datos en texto plano ante fallo criptográfico | Alto | Se solicitó eliminar el comportamiento de respaldo inseguro |
| 2 | Inicio del backend tras migración fallida | Alto | Se exigió detener el arranque y comprobar rollback |
| 3 | Persistencia insegura de auditoría | Alto | Se solicitaron garantías transaccionales y propagación de fallos |
| 4 | Bloqueo SQLite global | Alto | Se solicitó separar lecturas y escrituras y comprobar concurrencia multiproceso |
| 5 | Persistencia parcial con MFA incorrecto | Alto | Se identificó y corrigió un caso ACH que podía guardar beneficiarios |
| 6 | Aislamiento de bases de prueba | Alto | Se exigió usar bases desechables y preservar los datos anteriores |
| 7 | Secretos predeterminados y ejecución root | Alto | Se solicitó reforzar la seguridad de Docker Compose |
| 8 | Hallazgos SonarQube posteriores | Medio | Se realizaron correcciones limitadas y se conservó el Quality Gate final fallido |
| 9 | Documentación con métricas de carga inconsistentes | Alto | Se detectaron cifras de 100 usuarios y distribución 70/20/10 que no corresponden al benchmark de E3 |

Las observaciones agrupan problemas identificados en distintas interacciones. Su número no equivale al número total de intervenciones humanas, que debe obtenerse del registro completo.

El investigador no editó manualmente la lógica de aplicación como mecanismo de remediación; las correcciones se solicitaron al agente mediante instrucciones revisadas y aprobadas.

## 7. Limitaciones y conclusiones

La Etapa 3 con Tessl produjo una implementación funcional de las cuatro capacidades acordadas, con 125 pruebas automatizadas aprobadas y resultados de rendimiento favorables en un entorno local controlado.

La evaluación estática mostró una mejora en fiabilidad y seguridad, pero también mayor complejidad cognitiva, más deuda técnica y un Quality Gate final fallido.

Persisten limitaciones metodológicas relacionadas con la atribución de sesiones Gemini CLI, el conteo uniforme de requisitos, las diferencias entre mediciones de etapas y la falta de evidencia de un pipeline CI/CD.

Adicionalmente, se observó una modificación de marca de tiempo en un archivo auxiliar `shift_bank.db-shm`. Esto limita la posibilidad de afirmar una ausencia histórica absoluta de actividad sobre la base de datos, aunque no constituye por sí mismo evidencia de pérdida de datos.

La conclusión principal es que un proceso SDD permitió estructurar y evolucionar un sistema existente, pero su ejecución requirió supervisión humana activa para detectar incumplimientos y defectos no identificados por las pruebas iniciales.

---

**Naturaleza del documento:** análisis interno elaborado por el investigador a partir de evidencia técnica. No constituye una exportación empírica original de Gemini CLI ni sustituye los archivos JSONL, reportes de pruebas o mediciones SonarQube.