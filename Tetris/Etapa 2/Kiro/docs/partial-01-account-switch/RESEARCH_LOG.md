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


## 01-specify — interrupción por cambio de cuenta (2026-10-21)

La invocación real comenzó **19:58:47.728069Z** y el launcher registró su cierre **20:01:08.660147Z**, duración de proceso **140.931 s**, exit **4294967295**. El proceso principal detuvo exclusivamente su PID 3188 después de que el usuario informara una cuenta equivocada y un plan de créditos mejor. Clasificación: initial_specification, estado **interrupted_for_account_switch**. No es una especificación ni corrección terminada. El cambio/autenticación de cuenta sigue a cargo del proceso principal; este checkpoint no inicia login ni otro modelo.

Se archivaron el stream ACP y session.json/messages.jsonl de sess_bfb2da1c-8ba1-4be0-a8c5-bdbf919798f5, tres copias por hash. No hay runFinished, usage_summary ni resumen turn_completion de cierre. Por tanto **créditos finales, tiempo de agente, tokens e intentos/errores/éxitos API permanecen desconocidos**. La referencia de cuenta FREE 2.63/50 comunicada por el proceso principal no se atribuye como coste de esta invocación: puede describir consumo/cuota de cuenta. El tiempo de proceso 140.931 s sí está acreditado por el launcher.

La entrada nativa recibida a **19:58:52.032Z**, ID e2a3278e-ae5c-4aa0-be6e-de2889a61538, conserva **9744 caracteres**, los **5/5 párrafos** y la semilla completa. SHA-256 del archivo de prompt en bytes con CRLF: 13ECF3745FCEBDA4C986D17DF2A9A6C31727935F7D736A1D4E395CA22F12581A. SHA-256 del texto recibido con LF: F64F0298C83E4E7D0271CD672371E4E36AB3BCC2D03913E72B66FC99EC40E516. El contenido previsto y recibido coincide tras normalizar CRLF→LF; se preservan ambos hashes y tamaños sin confundir archivo y mensaje.

La revisión de **6 mensajes naturales Say** encuentra **0 preguntas de aclaración bloqueantes observadas** en el tramo retenido; los **36 registros Reasoning** se excluyen. No hay interacciones pendientes diferentes de aprobación automática. question-review.json conserva adjudicación por ID. Este cero describe únicamente el intervalo interrumpido, no una ejecución futura/completa.

01-baseline-preservation.json verifica **36/36 archivos copiados** y sus contrapartes originales de Etapa 1 idénticos en bytes. Fuente/pruebas/manifiestos/specs heredadas no cambiaron. Aunque el agente anunció que escribiría los artefactos, **no hay archivos nativos nuevos de Etapa 2 en disco** en este checkpoint. El anuncio no se presenta como escritura realizada. Se congela partial-01-account-switch antes de un nuevo intento.
