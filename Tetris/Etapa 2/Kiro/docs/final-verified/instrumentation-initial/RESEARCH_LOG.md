# Registro de investigación — Kiro, Etapa 2

## Inicio e instrumentación — 2026-10-21

Trabajo investigador separado de la aplicación. Tessl/BMAD se pausan por créditos Google y se continúa con Kiro por indicación del usuario. No se realizó una consulta a Gemini/Google, llamada de generación Kiro, cambio manual de aplicación/pruebas/specs, commit o push en esta preparación de métricas. No se modificó Drive.

### Baseline propio

Se utiliza exclusivamente la salida original de Kiro de Etapa1:36 archivos copiados con hashes verificados,23 archivos fuente/1207 líneas/33641 caracteres y3 especificaciones nativas/608 líneas/28780 caracteres. La Etapa1 se conserva. Los nuevos artefactos deben escribirse en un feature aparte bajo `.kiro/specs/`, antes del código.

`BASELINE.md` y JSON asociados registran la preparación independiente de entorno:39 pruebas backend pasadas con un warning heredado; build frontend exit0; frontend sin framework ni test script heredado, por lo tanto no se declara un pase de pruebas frontend. npm audit inicial:3 vulnerabilidades (1moderada,2altas). La instrumentación de cobertura se documenta por separado en la misma línea temporal y conserva el manifiesto de dependencias original. Las cifras Sonar y sus condiciones deben leerse de la evidencia exacta del análisis; un baseline no constituye aprobación de Etapa2.

### Runtime y evidencia real

CLI observado: **kiro-cli-chat 2.25.0**. Versión, ruta y SHA-256 quedan en `kiro-cli-provenance.json`. El esquema ACP real se contrastó con su historial propio de Etapa1 y su sesión nativa:8.92421986699834 créditos,540.609s de turno frente546.238s de proceso,35identificadores de peticiones y26mensajes Say separados de35registros Reasoning. Estos son **datos históricos de validación del parser**, no consumo de Etapa2.

`kiro-schema-validation.json` registra la comprobación:903eventos ACP y487chunks se conservan al leer un stream original, su duplicado completo y una copia de prefijo; no se duplican créditos. La primera comprobación de copia temporal falló por permisos del Temp de sandbox; se repitió en scratch dentro del workspace y pasó. No ejecutó código de aplicación ni un modelo.

El comando de lectura `chat --v3 --list-sessions --format json` inició inesperadamente el flujo automático de login desde el sandbox. Se canceló el único proceso investigador con Ctrl+C; no se observó llamada al modelo ni login completado. Se abandona ese probe y se usan archivos locales de sesiones identificadas. La autenticación y cualquier generación real quedan a cargo del proceso principal.

### Definiciones y limitaciones adoptadas

- Créditos nativos se contabilizan por resumen de ejecución; input/cache/output/thought y APIattempts/errors/success permanecen desconocidos si el esquema no los expone.
- El desglose de tokens del contexto no es consumo acumulado. `requestIds` no se renombra como peticiones exitosas ni intentos API.
- Se distinguen tiempo CLI, tiempo de turno, sesiones reanudadas, prompts investigadores, mensajes recibidos y fragmentos emitidos. Exit0 no acredita corrección completa.
- La semilla común se verifica por hash de archivo/bloque y contra el mensaje de usuario realmente recibido. Su hash no se confunde con el PRNG del juego. Antes de implementar se requiere acreditar la entrada completa.
- Los datos auxiliares de modelos no están atribuidos; `modelId=auto` no acredita un modelo resuelto. El flag de modo solicitado no se presenta como prueba del modo efectivo.
- Preguntas: se revisará texto natural Say, excluyendo Reasoning y herramientas. No se infiere cero por ejecución no interactiva. Los totales se mantienen desconocidos hasta adjudicación explícita.
- Métricas de uso corresponden al experimento Kiro; orquestación Codex, revisiones, helpers y documentación quedan fuera y se declararán en la comparación.

Los helpers viven en `Etapa2/shared`: `kiro_research.py`, `collect-kiro-metrics.py`, `archive-kiro-transcripts.py`, `audit-kiro-inputs.py`, `audit-kiro-questions.py`, `snapshot-kiro.py`. El protocolo detallado es `MEASUREMENT_PROTOCOL.md`.

### Estado de este checkpoint

**Preparación, sin invocación generadora de Etapa2 registrada en el momento de crear el checkpoint.** Fuente idéntica al baseline;0artefactos nativos nuevos. Se han generado métricas/auditorías vacías de invocaciones, con contadores no observables desconocidos. Los ceros de totales conocidos con0invocaciones no representan una medición de uso de un modelo. Implementación, aceptación completa, comparación final, documentación de resultados y publicación siguen pendientes.
