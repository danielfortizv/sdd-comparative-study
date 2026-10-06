# Auditoría de la diferencia BMAD entre Calculadora y Tetris

Fecha: 2026-10-05. Alcance: Tetris Etapa 1, opción A. No se modifican las otras cuatro implementaciones.

## Datos que sí están observados

| Indicador | Calculadora, tabla de la tesis | Tetris, ejecución original |
| --- | ---: | ---: |
| Archivos de especificación | 18 | 4 |
| Líneas de especificación | 1.421 | 402 |
| Tiempo de agente | 4.947 s (82,45 min) | 1.146 s (19,10 min) |
| LOC SonarQube | 911 | 778 |

En Tetris, los 1.146 segundos incluyen la generación inicial de especificación y código (818,843 s) y una corrección posterior de requisitos atómicos (327,195 s). No incluyen instalación, pruebas ni SonarQube. En Calculadora, la tesis informa «Agent Time», pero las trazas originales y el detalle de instalación de esa ejecución no se encuentran en este espacio de trabajo; por tanto, el criterio temporal exacto no se puede auditar aquí.

## Instalación y ruta realmente utilizada

El manifiesto original `Bmad Method/_bmad/_config/manifest.yaml` confirma instalación válida de **BMAD Method 6.12.0**, módulos `core` y `bmm`, e integración `gemini`. Se instalaron 29 habilidades. El comando original fue `bmad-method install --directory . --modules bmm --tools gemini --yes`. No hay evidencia de que faltase el módulo BMAD.

La solicitud original a Gemini invocó `bmad-spec` y después `bmad-build`. Esa es una **ruta corta admitida**, que produce un contrato breve y su implementación. La [guía oficial para elegir el camino de planificación](https://github.com/bmad-code-org/BMAD-METHOD/blob/main/docs/plan/choose-a-planning-path.md) distingue esa ruta de la planificación de un producto greenfield mediante documentos de producto, arquitectura, especificación, historias y sesiones de construcción. La cantidad de archivos depende del camino seguido, además del tamaño del caso; no mide por sí sola si una instalación está «completa».

La explicación más plausible de los cuatro archivos y el menor tiempo de Tetris es que se ejecutó una ruta más corta. **No es una causa demostrada de la diferencia con Calculadora:** tampoco están controlados aquí la versión exacta de BMAD y modelo del compañero, sus prompts, el número de sesiones, los reintentos, la amplitud de criterios ni su regla de conteo de archivos. El hecho de que Calculadora tenga 18 archivos no demuestra que Tetris deba producir exactamente 18.

## Repetición controlada dentro de Tetris

Se creó `Bmad Method Full/` como segunda condición, sin sobrescribir la ejecución original. Usa el mismo SHA-256 de semilla (`2AE084C9C64FC41F65D0E07581CED9E30B6C68891D9F8688A37F34594ECFD1C5`), el mismo alcance, Gemini CLI con Vertex AI y el proyecto GCP autorizado. Se reinstaló BMAD 6.12.0 con módulos `core` y `bmm` e integración Gemini mediante todos los parámetros explícitos. El manifiesto nuevo confirma 29 habilidades y `uv 0.12.20` está disponible.

La secuencia prevista es producto → PRD → arquitectura/UX según necesidad → épicas e historias → implementación → pruebas → SonarQube. Los archivos, tiempos y tokens de esta repetición se contarán por separado. Solo después de comprobar código, pruebas, escaneo y alcance se incorporará una comparación numérica al documento de tesis. Si se presenta la repetición en las tablas principales, el resultado original seguirá identificado como condición de ruta corta, para no convertir un cambio de método en una supuesta corrección de instalación.

El `product brief` se creó en 491,001 s. El PRD se redactó en 519,780 s y contiene 30 identificadores únicos de requisitos, pero Gemini lo devolvió en la salida de la sesión sin escribirlo al disco. Se conservaron los documentos exactamente como los emitió el modelo; `Bmad Method Full/docs/full-prd-materialization.json` registra el origen y los hashes. La revisión detectó atajos A/D/S/R y una promesa de cobertura de 100 % no autorizados por la semilla; se solicitó una corrección nativa antes de la arquitectura y la implementación. Este incidente se incluirá en tiempo de agente e intervención, pues omitirlo subestimaría el esfuerzo real del flujo completo.

La corrección y la arquitectura rápida concluyeron en 333,683 s. El PRD corregido conserva los 30 requisitos y los únicos controles previstos son ArrowLeft, ArrowRight, ArrowDown y el botón de reinicio. La arquitectura tiene 126 líneas físicas. Gemini volvió a devolver cinco archivos completos en la salida en vez de escribirlos; el manifiesto `Bmad Method Full/docs/full-architecture-materialization.json` permite auditar la transcripción exacta y los hashes.

La creación de épicas e historias concluyó en 267,555 s. Su documento nativo `epics.md` tiene 399 líneas y cinco épicas; el plan `sprint-status.yaml` tiene 40 líneas. Los dos se extrajeron literalmente de la salida de Gemini y el manifiesto `docs/full-epics-materialization.json` conserva hashes y verifica la cobertura de los 30 requisitos. La revisión encontró además dos metas de desempeño no solicitadas (100 sesiones/256 MB y latencia p95 menor de 50 ms), por lo que la instrucción de `bmad-build` exigió corregir los artefactos nativos antes de dar el resultado por definitivo.

La primera llamada a `bmad-build` duró 133,575 s y se quedó en un plan que pedía aprobación, a pesar de la autorización de ejecución autónoma. Una reanudación de 12,111 s devolvió una respuesta vacía. La variante instalada `bmad-build-auto` sí escribió la aplicación en una iteración de 834,057 s: FastAPI, React/TypeScript y seis pruebas de backend; la compilación Vite pasó. Una ejecución independiente de esas seis pruebas pasó también. No obstante, la revisión detectó que el agente había conservado las metas de capacidad y latencia como «guías», en vez de eliminarlas de PRD, addendum, épicas y especificación de implementación. Por eso se abrió una iteración nativa de corrección antes de la medición final. Estos reintentos son parte del esfuerzo observado, no se descontaron.

## Resultado verificado de la repetición

La segunda iteración `bmad-build-auto` duró 705,325 s y devolvió siete archivos completos para materialización; el manifiesto `docs/full-build-auto-correction-materialization.json` conserva sus hashes antes y después. Se eliminaron las metas de capacidad/latencia no pedidas, la historia 5.4 quedó limitada a la referencia de controles y se conservaron los 30 requisitos funcionales. La nueva batería pasó **13 pruebas** y alcanzó **98 % de cobertura del backend**; una prueba independiente adicional pasó reglas, colisiones, fijación, borrado de 1 a 4 líneas, fin de partida, cuatro rutas HTTP y reinicio. La compilación del frontend pasó. La primera ejecución de Vite en el aislamiento falló por `EPERM` de `realpath`; la repetición con acceso local terminó bien, por lo que se trata de un bloqueo del entorno de verificación.

| Indicador | Tetris BMAD ruta corta | Tetris BMAD planificación completa | Calculadora, tesis |
| --- | ---: | ---: | ---: |
| Archivos principales de especificación | 4 | 6 | 18 |
| Líneas físicas de especificación | 402 | 1.120 | 1.421 |
| Invocaciones del agente registradas | 2 | 9 | N/D aquí |
| Tiempo acumulado del agente | 1.146,038 s (19,10 min) | 3.299,511 s (54,99 min) | 4.947 s (82,45 min) |
| LOC SonarQube (`ncloc`) | 778 | 669 | 911 |
| Pruebas de backend aprobadas | 7 | 13 | N/D aquí |
| Cobertura global SonarQube | 57,6 % | 63,2 % | N/D aquí |
| Bugs / vulnerabilidades / code smells | 0 / 2 / 8 | 0 / 1 / 13 | N/D aquí |
| Complejidad cognitiva / deuda técnica | 64 / 45 min | 97 / 84 min | N/D aquí |
| Duplicación / quality gate | 0 % / OK | 0 % / OK | N/D aquí |

La repetición registra **17.653.626 tokens de entrada observados**, de los cuales **12.533.513** constan como cacheados, **237.579 tokens de salida**, **342 llamadas a herramientas observadas** y **nueve invocaciones**. Con las tarifas teóricas ya empleadas en la tesis, ese tráfico equivale a **11,6984 USD**; no es una factura de GCP ni acredita el consumo efectivo de los créditos disponibles. Los registros de modelo proceden de 19 transcripciones principales y de subagentes, deduplicadas por identificador de respuesta. Los 3.299,511 s incluyen el intento de arranque fallido (2,424 s), el plan que se detuvo, su reanudación vacía y la corrección posterior; excluyen instalación, materialización, pruebas externas y SonarQube, igual que el tiempo registrado para Tetris corto.

Los seis documentos de la repetición abarcan brief, PRD, addendum, arquitectura, épicas/historias e implementación. Se excluyeron del conteo dos `.memlog.md` y el estado de sprint YAML. El conteo original de cuatro archivos proviene de `_bmad-output/specs`; la tesis no conserva aquí la regla exacta con que Calculadora contó sus 18 archivos. Por tanto, el contraste entre 4, 6 y 18 **no se interpreta como un ensayo controlado de granularidad documental**. La diferencia de líneas y tiempo dentro de Tetris sí muestra el costo de recorrer más fases de BMAD con la misma semilla.

En SonarQube, la ruta completa redujo las vulnerabilidades de dos a una y elevó la cobertura global de 57,6 % a 63,2 %. También aumentó los `code smells` de 8 a 13, la complejidad cognitiva de 64 a 97 y la deuda estimada de 45 a 84 minutos, pese a tener menos LOC. La vulnerabilidad restante (`python:S2245`) advierte del generador pseudoaleatorio usado para seleccionar piezas; debe interpretarse en el contexto del juego. Ningún resultado justifica declarar la ruta completa universalmente superior en calidad. El hallazgo defendible es metodológico: **la instalación original no estaba incompleta; el camino seleccionado y la estructura de artefactos cambian sustancialmente esfuerzo y volumen documental**. Las trazas originales de Calculadora siguen siendo necesarias para atribuirle su duración de forma causal.
