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


## Corrección del transporte de modo — ACP sin prompt (2026-10-21)

Tras confirmar modo Vibe pese al flag Spec en01/02, se implementó run-kiro-acp.py usando el protocolo público oficial. Se verificó configuración antes de inferencia: initialize → session/new → opciones anunciadas mode=spec/model=auto. El preflight sandbox falló con acceso denegado; se conservó y el mismo control fuera de sandbox pasó. Sesión de configuración sess_4687607e-2d7f-4d7d-9273-46f15f2407aa: respuesta y metadata nativa confirman Spec/Auto; **0 solicitudes session/prompt y0 mensajes de usuario**. Los36 archivos del baseline y Etapa1 siguen intactos. Esta preparación se excluye de invocaciones/consumo del experimento. La ruta real de inferencia aún no se ejecutó por el investigador. Fuentes, límites y evidencia: ACP_DRIVER.md y researcher-setup/acp-spec-auto-preflight-verification.json. No se modificó ni detuvo02.



## 02-specify-student — tres artefactos; modo Vibe observado (2026-10-21)

Invocación fresca, sin reanudar01, con la cuenta Student confirmada por el proceso principal. CLI2.33.0, SHA-256 BC711541FC139D5E5FC8E07FC8FA13E9239ED039862F4A9D55C0E344BAC7C3F8; el piloto01 usó2.25.0. Se conserva esa diferencia de runtime por invocación. El update oficial y los probes de autenticación/cuenta son preparación y quedan fuera de los totales de generación. El saldo FREE3.09 de cuenta comunicado por el proceso principal no se asigna entero a01, que carece de resumen final. El inicio Student0.00/1000 es estado de cuenta, no un contador de tokens.

02 comenzó20:11:08.531353Z y cerró20:16:39.551350Z, **331.014 s CLI**, exit0, stopReason=end_turn. Resumen nativo de esta ejecución: **5.897180333001658 créditos**, **326.445 s de agente**, **18 requestIds observados**, sin equivalerlos a intentos/éxitos API. Tokens input/cache/output/thought siguen desconocidos. La semilla recibida completa coincide con el prompt de9744 caracteres tras normalización y conserva5/5 párrafos.

ACP y metadata nativa confirman selección **Auto** y modo **Vibe**; pedir Spec por flag no cambió el modo real. El propio mensaje final declara que escribió tres Markdown nativos sin acreditar un motor automatizado del workflow. Se registra la limitación, sin presentar este intento como workflow Spec efectivo. El transporte ACP de configuración separada ya acredita Spec/Auto antes de prompt y se utilizará por el proceso principal para revisión nativa03; el investigador no envía esa inferencia.

Archivos nuevos en .kiro/specs/tetris-stage2-option-a/: **3 archivos,686 líneas,512 no vacías,52798 caracteres normalizados**,228.67 líneas/archivo. requirements277 líneas/24269 caracteres; design288/19960; tasks121/8569. Las diferencias entre bytes físicos y caracteres Unicode/LF se mantienen explícitas. Los36 archivos heredados y sus originales Etapa1 permanecen idénticos, acreditados en02-baseline-preservation.json; no hay cambios de app/pruebas/dependencias.

Se revisaron **14 mensajes naturales Say**: **0 preguntas bloqueantes** y **1 referencia no bloqueante a confirmación en la revisión**, sobre la colisión al hacer hold-swap. No se mezcla con preguntas dentro de los documentos ni con18 registros Reasoning. La referencia final termina la ejecución y no implica una respuesta del investigador ni una decisión funcional tomada aquí. La revisión de los tres artefactos pertenece al proceso principal.

Archivo por hash actualizado y snapshot specification-02 preservan el estado antes de03. El fin del turno y los archivos escritos no acreditan implementación ni aceptación funcional. La configuración Spec/Auto tampoco prueba ejecución de todas las fases/aprobaciones del workflow: no se manipulan estados privados ni se marcan tareas manualmente por el investigador; los hitos deben quedar respaldados por acciones/artefactos nativos observados.


## Latest control: automatic suspension cancelled by user

The user explicitly cancelled the suspension task and requested continuing Kiro on October21,2026 America/Bogota. Windows task Codex-Quota-Hourly-Suspend-Kevin was stopped and verified Disabled. The durable suspension-disabled.json guard prevents normal monitor execution and power API calls; a real normal invocation returned skip/user_cancelled_suspension/action none. The researcher continuation now contains no power action or Codex quota gate. Do not re-enable suspension without a new explicit instruction. Historical quota observations and the earlier pre-implementation exhaustion checkpoint remain preserved.

After the completed actual Spec/Auto review03 and baseline/input/snapshot checks, invocation04-implement started through official ACP on the authenticated Kiro Student account. It owns its raw RPC/ACP logs and has Spec/Auto verified before the prompt. Application, tests, metrics and final acceptance remain pending verification; starting implementation is not a claim of completion. Recorded at 2026-10-22T00:52:40.886295+00:00.


## Auditoría manual de preguntas de03 — cierre revisado

Se leyeron completos los **19 mensajes naturales Say** del intervalo20:20:02.788416Z–20:26:38.518881Z de03-native-spec-review. Resultado: **0 preguntas bloqueantes y0 referencias de confirmación no bloqueantes**. Las explicaciones sobre herramientas, citas de documentos y planes de validación no se cuentan como preguntas. El resumen final comunica revisiones y cierre, sin pedir aclaración. No se incluyen Reasoning, salidas de herramientas ni fragmentos de documentos como mensajes del agente independientes. Cada ID tiene adjudicación factual y timestamp en question-review.json; se preservaron todos los registros anteriores.

Clasificación manual de la invocación: **preimplementation_spec_revision**. Son correcciones de requisitos/diseño/tareas solicitadas antes de implementar, separadas de correcciones posteriores a implementación. Metadata: fase spec_revision; ACPSpec/Auto verificado antes de prompt; exit0 ystopReason=end_turn. Métricas de03 ya retenidas: **8.02610462437811 créditos**, **395.730s de proceso**, **393.627s de agente**, **23 identificadores requestIds** (sin renombrarlos como intentosAPI). Input completo7555caracteres/5de5párrafos. Esto no acredita04 ni aceptación final. El collector y los reportes se dejan sin regenerar durante04.

## 04 — cierre nativo y revisión independiente completada (registro23 de octubre)

04 terminó con end_turn/exit0: 1796.250 s de proceso y1792.693 s de agente;49.45827078706466 créditos nativos,130 requestIds (identificadores, no intentos API). Se leyeron los105 mensajes naturales Say completos;0 aclaraciones bloqueantes.130 Reasoning excluidos. El diagnóstico no convierte autoinformes en pruebas. La suite terminó en120 instancias backend aprobadas (la parametrización cambió118→120) y38 frontend; estos son resultados del candidato04, no aceptación final. Cobertura frontend89.75% excluía main.tsx, contradiciendo la declaración de cobertura de toda producción; la corrección externa exige incluirlo. La auditoría global retenía7 hallazgos:3 moderados,2 altos,2 críticos. omit=dev0 no acredita la seguridad de Vite como build/dev-server.

Sonar04: tres análisis, fallos6→2 violaciones nuevas y cierreOK con0 nuevas,91.8% cobertura nueva y0% duplicación nueva. CE final161470a8-2dfa-4f58-ac40-0eadf5de5212 SUCCESS, análisis79552604-fb00-45fe-a4f5-b97e083319e2. Global91.7%;7 smells heredados activos,0 bugs/vulnerabilidades/hotspots,0% duplicación, complejidad150/cognitiva97, deuda23min, ncloc772, líneas1235, ratingsA. Los dos intentos fallidos y el aprobado quedan preservados. Son dos ciclos conocidos de remediación Sonar dentro de04, separados de prompts externos; no equivalen a todos los fallos/correcciones posibles del turno. Desviación de procedimiento: el Say b6140ade-6a42-4ea3-95ad-7094fcda0075-say declara que corregirá los hallazgos de estilo directamente sin revisar specs primero. No se acredita spec-first para esa remediación interna. El ajuste de la igualdad de claves del test heredado sí tuvo revisión previa de specs; la aplicación agrega siete campos obligatorios.

Aceptación externa04: tres carreras reales reproducidas y fallidas, no ocultadas por el gateOK. La repetición previa a05 conservó hash estable y LCOV intacto; calidad y fuentes están congeladas en implementation-04 y quality-before-05. Pruebas Stage1 originales:38/39 aprobadas; la única igualdad cerrada de cuatro claves es incompatible con los siete campos obligatorios de Stage2. No se alteró esa evidencia ni se presenta39/39 sin cambios.

## 05 — interrupción recuperada el23 de octubre;06 reintento del mismo objetivo

05 arrancó el21 de octubre, realizó revisión nativa parcial de requisitos y quedó durante la revisión de diseño. Al recuperar el23 no estaban sus procesos ni un cierre nativo/runFinished. Se preservaron prompt, RPC, ACP y sesión identificada. El registro reconstruido conserva ended/duration/exit como desconocidos y usa observation_end_upper_bound_utc únicamente para acotar la lectura del intervalo; no convierte el lapso fuera de línea en tiempo de agente. No hay resumen final de créditos/tokens; el saldo de cuenta no se asigna por diferencia. Las34 fuentes permanecían idénticas al candidato04; las specs sí conservan revisión parcial. Snapshot interrupted-05-recovered:118 archivos por hash.

Se leyeron8 Say de05. Hubo1 confirmación de alcance/workflow, vinculada al user_input toolu_bdrk_01NGHsSKaYGP3mPKAEqgTXvc: preguntó cómo abordar la corrección de varias partes. El cliente seleccionó la opción ofrecida de completar todo usando la autorización previa; no llegó una respuesta humana nueva. Se cuenta una pregunta, sin sumar dos veces Say y pending_interaction. No era una nueva decisión de reglas del juego. Las restantes7 intervenciones no solicitan aclaración.

06-qa-retry comenzó el23 por ACP oficial, sesión sess_285253f9-10ca-44db-a3df-b2418fed1d38. Spec/Auto verificados antes de prompt; mismo CLI2.33.0 y hashes de semilla intactos. Es un segundo intento externo del mismo qa_intent_id kiro-stage2-qa-01, no un segundo objetivo de corrección. Debe finalizar revisión nativa de requisitos/diseño/tareas antes de código, arreglar carreras, auditoría global, cobertura bootstrap y título, conservando gate y pruebas. Su resultado/consumo final permanece pendiente.

## Control de energía reactivado por nueva instrucción23 de octubre

Se reutilizó Codex-Quota-Hourly-Suspend-Kevin: Ready/PT1H, próximo control15:13:16 America/Bogota, sin wake timer ni duplicado. La cancelación anterior se conserva en historial; suspension-disabled.json ahora tiene disabled=false. Pasan37 controles de decisión. Dry-run real:95% Codex cinco horas/99% semanal y932.18 créditos Kiro Student incluidos. Ejecución normal de la tarea a14:13:51 terminó LastTaskResult0; evento19:13:56.285Z mode=monitor/decision=continue/action=none. No se realizó una prueba real de suspensión ni se consumieron restablecimientos. La tarea Windows independiente es el ejecutor; el heartbeat de Codex permanece PAUSED para evitar duplicación. Evidencia: shared/quota-monitor/reactivation-20261023.json y events.jsonl.

## Ajustes de instrumentación investigadora

kiro_research.interval_records admite un límite superior de observación explícito para el caso05 sin inventar ended/duración. La enumeración de manifiestos añade requirements-dev.txt y la de configuraciones reconoce tsconfig.vitest.json si existe; las capturas antiguas no se alteran. Nuevos snapshots incluyen READMEs, LCOV y RPC originales. Son cambios de captura/documentación, no autoría de aplicación/tests/specs. Orquestación, verificación y monitor siguen separados del consumo Kiro del experimento.
