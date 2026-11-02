# Protocolo de medición de Kiro — Etapa 2

Documento investigador. No es una especificación de generación ni modifica aplicación, pruebas o artefactos nativos. Su esquema se obtuvo del CLI instalado y de la evidencia real de Kiro de la Etapa 1.

## Runtime y flujo observado

CLI local: **kiro-cli-chat 2.25.0**. `kiro-cli-provenance.json` conserva ruta y SHA-256 del ejecutable. La ayuda confirma `chat --v3 --mode spec --no-interactive --trust-all-tools --output-format stream-json INPUT`. El stdout usa eventos ACP JSONL `runStarted`, `sessionUpdate`, `runFinished`. Se guardará un stream por invocación y el stderr por separado.

El flag solicitado, la configuración de la sesión y el modo emitido son observables distintos. En la evidencia histórica se pidió `--mode spec`, pero `session.json` registró `modelId=auto` y varios mensajes `agentMode=vibe`. Se preserva esta diferencia sin afirmar un modelo de backend o modo efectivo no acreditado. Los requisitos, diseño y tareas nativos se verifican por sus archivos y por el orden real de escritura. No se usa material de otra herramienta para generar Kiro.

## Contrato del launcher

Cada intento conserva `<label>.prompt.txt` (texto exacto), `.started.json` antes del proceso, `.stdout.jsonl`, `.stderr.txt` y `.run.json` al cerrar. Metadata mínima: `label`, `started`, `ended`, `duration_seconds`, `exit_code`; se recomienda registrar argv, ejecutable/version/hash, resume solicitado/ID y modelo solicitado. El estado del proceso y la ejecución efectiva se informan por separado. `runStarted` solo no acredita una llamada al modelo. Una respuesta de agente o resumen de uso acredita actividad observada, sin establecer cuántas peticiones API ocurrieron.

Las invocaciones abiertas figuran aparte y no entran a los totales cerrados. Una invocación cerrada con exit0 no acredita implementación completa. Categorías, intención QA, reintento y cierre funcional se registran explícitamente en `run-classifications.json` por etiqueta. Los fallos de autenticación, red o cuota no se borran ni se convierten en correcciones completadas.

## Créditos, tokens, peticiones y tiempos

- Kiro conserva `usage_summary` nativo y snapshots ACP `session_info_update._meta.kiro` de tipo `turn_completion`. `promptTurnSummaries[].unit=credit` identifica créditos Kiro; `usage` es la cantidad observada. No se convierte a tokens, dólares ni créditos de Gemini.
- Se usa el último resumen nativo por sesión/`executionId` dentro del intervalo. ACP es fallback si falta el resumen nativo, nunca otra cantidad que se suma a la misma. Una divergencia de los streams deja el agregado sin acreditar.
- `elapsedTime` se interpreta en milisegundos: el histórico540609 coincide con inicio/fin nativos separados por540.609s. Ese tiempo de turno se distingue de546.238s de proceso CLI y del tiempo total de una sesión reanudada. Cada duración desconocida permanece desconocida.
- `requestIds` se conserva como conjunto de identificadores observados. Su cardinalidad **no** se llama intentos API, respuestas exitosas o errores. No hay contadores verificables de esas tres clases en el esquema observado.
- Tokens de entrada, caché, salida y razonamiento quedan `null` mientras no exista un contador facturado acreditado. Los `breakdown.*.tokens` y `contextUsage.usagePercentage` describen ocupación/composición contextual y **no** se suman como consumo. Los ceros `gemini_tokens` de las métricas antiguas de Kiro son instrumentación inaplicable, no uso real cero.
- `agent_message_chunk` son fragmentos; `runFinished.finalText` agrega texto ya emitido. No se cuentan ambos como respuestas nuevas. Native `assistant/operationType=Say` permite contar mensajes de texto natural; `Reasoning` se separa y nunca entra en el recuento de preguntas. Ninguno equivale por definición a una respuesta API.
- Modelos auxiliares no tienen atribución separada en el esquema observado. Se informa esa limitación; la selección `auto` no revela el modelo resuelto.

## Semilla y evidencia de entrada

La semilla común es `Etapa 2/shared/seed.md`. El auditor conserva SHA-256 de todos sus bytes y otro del bloque citado, extraído, recortado, con LF y UTF-8 sin BOM. La semilla de instrucciones es independiente del PRNG del juego heredado (`DEFAULT_SEED=20260929`).

`audit-kiro-inputs.py` contrasta el prompt previsto contra un `payload.type=user` realmente guardado en `messages.jsonl`, dentro del intervalo de esa invocación y en su `sessionId`. Conserva hash y caracteres **raw** del texto decodificado y otros normalizados CRLF→LF. También registra párrafos completos y lecturas de semilla por herramientas, por separado. La copia del prompt en disco o una mención del agente no acredita entrega. Antes de implementar debe verificarse la semilla completa recibida. Si falta la evidencia, el estado es no acreditado; no se inventa un cero ni una entrega.

## Archivos, densidad y deltas

Baseline propio verificado:23 archivos fuente/1207 líneas/33641 caracteres;3 artefactos nativos/608 líneas/28780 caracteres. `baseline-copy-manifest.json` acredita los36 archivos copiados y la preservación de la Etapa1. Los nombres nativos heredados se distinguen de los nuevos bajo `.kiro/specs/`; el nuevo feature debe conservar `requirements.md`, `design.md`, `tasks.md`.

Fuente incluye extensiones `.py/.ts/.tsx/.js/.jsx/.css/.html` bajo backend/frontend y se desglosa en producción, pruebas y configuración/soporte. Manifiestos de dependencias y configuración JSON/INI se cuentan aparte; la configuración TS puede solaparse con fuente, sin sumarse dos veces. Se excluyen dependencias, cachés, builds, docs y Git. Texto UTF-8 sin BOM, LF universal; líneas con `splitlines`, caracteres Unicode decodificados y densidad=líneas/archivos. SHA-256 usa bytes originales.

Los deltas comparan estados retenidos con `SequenceMatcher` para líneas añadidas/eliminadas y diferencia **neta** de caracteres. No se presenta el delta neto como volumen acumulado de edición. Las correcciones externas posteriores a implementación se separan de reintentos de la misma intención y de remediaciones internas/escaneos; estas últimas requieren prueba concreta.

## Archivo, deduplicación y snapshots

`archive-kiro-transcripts.py` copia streams y únicamente las sesiones nativas identificadas en ellos, sin barrer otras conversaciones ni credenciales. Se permiten IDs adicionales exactos con `--session-id`. Las copias son inmutables por hash y tienen un manifiesto. Los streams se comparan como secuencias: se toma el prefijo coherente más largo; no se borran chunks repetidos legítimos. Divergencias quedan explícitas. Native se deduplica por sesión+ID+timestamp porque Kiro reutiliza algunos IDs de interacción en timestamps distintos.

El collector/auditor leen original y archivo; no suman snapshots. `snapshot-kiro.py --label <nombre>` valida hashes contra métricas, rechaza sobrescritura y congela fuente/especificaciones/manifiestos/configuración/evidencia disponible. Rechaza invocaciones abiertas salvo `--allow-pending`, que preserva un estado parcial sin aceptación final. No sigue secretos ni modifica el almacén nativo. Transcripts privados pueden contener cadenas incidentales: las publicaciones deben revisarlas y no difundir códigos de acceso.

## Preguntas y calidad

`audit-kiro-questions.py` inventaría mensajes naturales Say e interacciones diferentes de aprobación automática. El regex produce candidatos, no un contador definitivo. `question-review.json` adjudica cada mensaje con ID, `is_blocking_clarification` y motivo. Hasta revisar todos los mensajes de una invocación, su total es desconocido. Se excluyen razonamiento, salidas citadas de herramientas, preguntas dentro de specs y prompts investigadores externos.

Éxito de wrapper/ACP no prueba que pytest, npm, scanner o comandos hayan salido bien. Se preservan sus logs y códigos de salida como prueba. Calidad exige análisis Sonar exacto, taskSUCCESS, versión/código correspondiente, gate evaluado y datos de cobertura actuales. La complejidad y mantenibilidad pueden medirse; no se inventa una puntuación de escalabilidad sin prueba de carga. El baseline y su primer gateOK sin condiciones evaluadas no son aceptación final.

Los créditos/tokens del experimento corresponden a Kiro. Orquestación Codex, revisiones de investigadores, escritura de helpers y trabajo documental quedan fuera y se declaran para la comparación entre herramientas.

## Orden de captura tras cada cierre

1. Archivar streams y sesiones identificadas.
2. Ejecutar collector, auditor de entradas y auditor de preguntas; adjudicar texto natural cuando exista.
3. Congelar snapshot etiquetado antes de la siguiente corrección.
4. Añadir al log hallazgos, fallos, cambios de entorno y verificación independiente. No declarar final mientras haya una invocación o control pendiente.
