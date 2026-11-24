### E4-SK-01 — Inspección inicial y preparación de Gate A
**Fecha:** 16 de noviembre de 2026
**Estado:** Prompt preparado; ejecución pendiente.

**Objetivo:** Verificar la línea base de Spec Kit E4 y preparar la decisión humana sobre incompatibilidades monetarias y contractuales antes de generar especificaciones.

**Acciones ejecutadas:**
- Revisión investigadora de SEED-4 y del paquete preparatorio.
- Identificación del conflicto COP/USD y de aprobaciones pendientes.
- Elaboración del primer prompt de inspección de solo lectura para Codex.
- Sin ejecución de Codex ni modificación del proyecto durante este hito.

**Resultados verificables:**
- Preparación previa: 105/105 archivos reportados como verificados por SHA-256; comprobación independiente por Codex pendiente.
- Especificaciones funcionales E4 nuevas: ninguna acreditada.
- Pruebas E4: no ejecutadas en este hito.
- Gate A: pendiente.

**Problemas y correcciones:**
- Divergencia documentada entre saldos/umbrales COP de E3 y la referencia USD de D-02/D-07.
- Aprobación completa de D-01–D-14 no acreditada.
- Procedencia de la semilla original pendiente de cotejo.
- Correcciones aplicadas: ninguna.

**Evidencias:**
- Paquete SHIFT_BANK_E4_SPECKIT_PREPARACION.
- Documentos de preparación de GitHub Copilot.
- Prompt E4-SK-01.
- Salida de Codex: pendiente.

**Implicaciones D1–D5:**
- D1: consumo, tiempo, mensajes y herramientas Codex E4: N/D hasta ejecución.
- D2: línea base histórica disponible; calidad E4 no medida.
- D3: sin especificaciones E4 nuevas.
- D4: requisitos REQ-01–REQ-06 todavía no verificados.
- D5: bloqueos identificados para revisión humana; sin correcciones implementadas.

**Decisión humana:** Gate A no aprobado. Se solicita inspección independiente antes de resolver las reglas contractuales.

**Próximo paso:** Ejecutar E4-SK-01, revisar evidencia y decidir la reconciliación COP/USD y aprobación D-01–D-14.

### E4-SK-01 — Auditoría inicial de línea base y Gate A
**Fecha:** 16 de noviembre de 2026
**Estado:** Inspección finalizada. Gate A pendiente.

**Objetivo:** Comprobar la integridad de la copia E4 de Spec Kit, identificar las diferencias entre el legado E3 y SEED-4 y preparar decisiones humanas antes de especificar.

**Acciones ejecutadas:**
- Inspección de repositorio, código, especificaciones y evidencias preparatorias.
- Verificación independiente de 105 hashes SHA-256.
- Comparación de contratos monetarios, límites, MFA, ACH, seguridad y arquitectura.
- Revisión de D-01–D-14 y su estado de aprobación.
- Inspección de configuración Spec Kit y versión de Codex.
- Comparación adicional del SEED-4 preparado contra el Anexo A de la guía de replicación por el supervisor.

**Resultados verificables:**
- 105/105 archivos coincidentes; 1.279.387 bytes.
- E3 heredada usa cuentas COP 5.000.000 y COP 15.000.000.
- Conflictos reales con D-02, D-07 y tratamiento de COP en D-01/D-08.
- Spec Kit 1.0.6; Codex CLI 0.168.0.
- Proyecto configurado inicialmente con integración Gemini.
- SEED-4 coincide exactamente con el anexo de la guía salvo el salto de línea final.
- Ninguna prueba E4 ejecutada y ninguna modificación funcional realizada.

**Problemas y correcciones:**
- Incompatibilidad contractual COP/USD: sin resolver.
- Aprobaciones originales D-01–D-14: no acreditadas.
- Configuración Codex/Spec Kit: pendiente de adecuación.
- Algunos comandos de inspección fallaron por rutas ausentes y política PowerShell; la verificación SHA-256 sí se completó.
- Correcciones funcionales: ninguna.

**Evidencias:**
- Salida completa de Codex E4-SK-01.
- BASELINE_FILES_SHA256.tsv.
- PREPARACION_E4_SPECKIT.md.
- D01_D14_PENDING_REVIEW.md.
- SEED-4.md y Anexo A de la guía de replicación.
- Referencias de código y contratos E3 señaladas por Codex.

**Implicaciones D1–D5:**
- D1: Codex reportó 4 min 29 s de trabajo; tokens, costo, llamadas totales y modelo efectivo N/D.
- D2: línea base inspeccionada; métricas de calidad E4 todavía N/D.
- D3: cero especificaciones E4 nuevas; métricas formales pendientes.
- D4: REQ-01–REQ-06 no verificados en E4; conflictos de compatibilidad documentados.
- D5: discrepancias contractuales y bloqueo de integración identificados; aprobación humana requerida, sin retrabajo funcional.

**Decisión humana:** Mantener Gate A bloqueado. La alternativa 3 de preservación del legado COP fue recomendada, pero no aprobada. Se autoriza continuar únicamente con la preparación técnica no funcional de la integración Codex.

**Próximo paso:** E4-SK-02 — adecuación y validación de integración nativa Codex, seguida de revisión humana de Gate A.

### E4-SK-02 — Integración nativa de Codex con Spec Kit

**Fecha:** 16 de noviembre de 2026
**Estado:** Completado. Gate A pendiente.

**Objetivo:** Habilitar OpenAI Codex como agente de desarrollo dentro del flujo nativo de GitHub Spec Kit, preservando las especificaciones, código y evidencias heredadas.

**Acciones ejecutadas:**
- Inspección del estado de integración mediante el CLI de Spec Kit.
- Instalación nativa con `specify integration install codex`.
- Activación mediante `specify integration use codex`.
- Validación de manifiestos y archivos administrados.
- Comparación del árbol de E4 con el manifiesto de 105 archivos de E4-SK-01.
- Generación del registro `INTEGRATION_CODEX_SETUP.md`.

**Resultados verificables:**
- Spec Kit CLI 1.0.6 y Codex CLI 0.168.0.
- Codex instalado como integración predeterminada; Gemini conservado.
- Diez habilidades Spec Kit disponibles en `.agents/skills/`.
- 11 archivos añadidos, 9 modificados y 0 eliminados.
- 96/105 archivos originales conservan su hash; los otros 9 corresponden a configuración nativa.
- Validación de integración OK, sin archivos administrados modificados o faltantes.
- Código, pruebas, constitución y specs E1–E3 sin modificaciones.
- Ninguna prueba funcional o despliegue ejecutado.

**Problemas y correcciones:**
- Errores de acceso a red durante consulta del catálogo; instalación local exitosa.
- Escritura de evidencia fuera de la raíz permitida: requirió una autorización humana puntual.
- Modelo efectivo: N/D.
- No hubo correcciones funcionales.

**Evidencias:**
- Transcript de Codex E4-SK-02.
- `INTEGRATION_CODEX_SETUP.md`.
- Manifiestos nativos Gemini y Codex.
- Comparación SHA-256 de la línea base.

**Implicaciones D1–D5:**
- D1: duración reportada por Codex de 4 min 20 s; tokens, costo y llamadas totales N/D.
- D2: sin modificaciones de código bancario; 9 cambios en archivos de integración registrados por separado.
- D3: ninguna especificación funcional E4 nueva.
- D4: requisitos funcionales E4 todavía no verificados; pruebas no ejecutadas.
- D5: una aprobación humana puntual para escribir evidencia; Gate A todavía pendiente.

**Decisión humana:** Se autorizó la preparación técnica de Codex, no la modificación de contratos ni la implementación.

**Próximo paso:** Obtener aprobación explícita de Gate A y comenzar E4-SK-03 mediante el flujo nativo de especificación.

### E4-SK-03 — Intento 1: bloqueo de Gate A

**Fecha:** 16 de noviembre de 2026
**Estado:** Detenido sin modificaciones.

**Objetivo:** Iniciar las especificaciones mediante el flujo
nativo de GitHub Spec Kit.

**Acciones ejecutadas:**
- Codex comprobó las precondiciones de Gate A.
- Detectó ausencia de autorización humana explícita.
- Detuvo la ejecución antes de generar artefactos.

**Resultados verificables:**
- Duración reportada: 5 segundos.
- Especificaciones creadas: 0.
- Archivos modificados: 0.
- Pruebas ejecutadas: 0.

**Problemas y correcciones:**
- Bloqueo administrativo: Gate A sin aprobación registrada.
- Correcciones realizadas: ninguna.

**Evidencia:** Salida de Codex E4-SK-03, intento 1.

**Implicaciones D1–D5:**
- D1: 5 s reportados; tokens y costos N/D.
- D2: ningún cambio en código.
- D3: ninguna especificación nueva.
- D4: sin verificación funcional.
- D5: una intervención de aprobación pendiente.

**Decisión humana:** Pendiente.

**Próximo paso:** Obtener aprobación explícita y reanudar
E4-SK-03 sin repetir las inspecciones completadas.

### E4-SK-03 — Consolidación del contrato y ejecución

**Fecha:** 16 de noviembre de 2026
**Estado:** Prompt consolidado; ejecución pendiente.

**Objetivo:** Completar las especificaciones y planificación
de la Etapa 4 mediante GitHub Spec Kit.

**Acciones:**
- Revisión de SEED-4 y guía de replicación.
- Reutilización de las decisiones documentadas D-01–D-14.
- Definición prospectiva de compatibilidad COP/USD.
- Consolidación del proceso SDD en un único hito.
- Eliminación de aprobaciones rutinarias redundantes.

**Decisión humana:**
El investigador delegó la resolución de decisiones
técnicas documentadas al supervisor para evitar
iteraciones innecesarias.

**Decisión técnica del supervisor:**
Preservar el legado COP y agregar USD/EUR/GBP,
con excepciones documentadas a D-01, D-02,
D-07 y D-08.

**D1:** Dos intentos previos de E4-SK-03 bloqueados;
consumo exacto N/D.
**D2:** Sin modificaciones funcionales.
**D3:** Especificaciones nuevas pendientes.
**D4:** REQ-01–REQ-06 pendientes de implementación.
**D5:** Dos intervenciones innecesarias identificadas;
proceso corregido para reducir retrabajo.

**Próximo paso:** Ejecutar el E4-SK-03 consolidado y
evaluar la documentación producida para Gate B.


### E4-SK-03 — Especificación y planificación de la Etapa 4

**Fecha:** 16 de noviembre de 2026  
**Estado:** Completado; revisión Gate B pendiente.

**Objetivo:** Generar los artefactos nativos de GitHub Spec Kit necesarios para migrar Shift Bank hacia multimoneda, conversión de divisas, Event Sourcing y CQRS.

**Acciones ejecutadas:**

- Creación de especificación funcional, plan técnico, contratos API/eventos, modelo de datos, investigación y plan de validación.
- Elaboración de 68 tareas de implementación y verificación.
- Incorporación de compatibilidad COP y documentación de excepciones a D-01, D-02, D-07 y D-08.
- Revisión estática de trazabilidad y corrección de inconsistencias documentales.
- Verificación de integridad de la línea base y del estado de la integración Codex.

**Resultados verificables:**

| Indicador | Resultado |
|---|---|
| Archivos nuevos de especificación/planificación | 10 |
| Requisitos funcionales | 27 |
| Criterios de aceptación | 45 |
| Tareas planificadas | 68 |
| REQ cubiertos según Codex | 6/6 |
| Decisiones cubiertas según Codex | 14/14 |
| Checklist independiente | 24 ítems pendientes |
| Pruebas funcionales ejecutadas | Ninguna |
| Duración reportada de Codex | 30 min 25 s |

**Problemas y correcciones:**

Se identificó una falta de trazabilidad para FR-011 y tres tareas sin referencia explícita durante una revisión intermedia. Codex realizó ajustes posteriores, pero la salida no acredita la verificación final de cobertura completa.

La ejecución inicial de scripts PowerShell fue bloqueada por la política del sistema. Se resolvió utilizando una invocación con `ExecutionPolicy Bypass` a nivel de proceso.

No se modificó código de aplicación ni se ejecutaron pruebas funcionales.

**Evidencias:**

- Directorio `specs/004-shift-bank-stage4-multicurrency-eventsourcing-cqrs/`.
- Registro `E4_SPECKIT_DELEGATED_CONTRACT_AND_SPECIFICATION.md`.
- Transcript de Codex E4-SK-03.
- Validaciones de prerrequisitos y manifiestos Spec Kit.

**Implicaciones para las dimensiones:**

- **D1:** duración reportada de 30 min 25 s. Tokens, costo, llamadas totales y modelo efectivo: N/D.
- **D2:** sin cambios en código productivo. Calidad estática E4 pendiente.
- **D3:** diez archivos nuevos de especificación/planificación, 27 requisitos funcionales identificados.
- **D4:** 45 criterios de aceptación definidos; cumplimiento funcional todavía NOT VERIFIED.
- **D5:** adaptación prospectiva COP/USD documentada bajo delegación del investigador; correcciones de trazabilidad realizadas por el agente.

**Decisión de supervisión:** aceptar E4-SK-03 como generación documental completada y solicitar una única revisión final acotada antes de Gate B. La implementación todavía no está autorizada.

**Próximo paso:** E4-SK-04, revisión contractual final y preparación de Gate B.

### E4-SK-04 — Auditoría contractual final y preparación de Gate B

**Fecha:** 16 de noviembre de 2026  
**Estado:** Completado — PASS WITH LIMITATIONS.

**Objetivo:** Comprobar la consistencia de las especificaciones, contratos, criterios de aceptación y tareas de la Etapa 4 antes de autorizar la implementación.

**Acciones ejecutadas:**

- Verificación de trazabilidad entre requisitos, criterios de aceptación y tareas.
- Revisión por Codex de los 24 puntos del checklist contractual.
- Corrección de referencias incompletas de aceptación.
- Incorporación explícita de prevención de doble ejecución en pagos recurrentes concurrentes.
- Corrección de metadatos de la rama/directorio de funcionalidad.
- Validación de los prerrequisitos nativos de GitHub Spec Kit.

**Resultados verificables:**

| Métrica | Resultado |
|---|---|
| Requisitos funcionales con tareas de implementación | 27/27 |
| Requisitos funcionales con tareas de verificación | 27/27 |
| Criterios de aceptación trazados | 45/45 |
| Tareas verificadas documentalmente | 68/68 |
| Requisitos generales | 6/6 |
| Decisiones D-01–D-14 | 14/14 |
| Checklist evaluado por Codex | 24/24 PASS |
| Archivos documentales corregidos | 5 |
| Duración reportada | 46 min 48 s |

**Problemas y correcciones:**

Se corrigieron referencias desactualizadas que terminaban en AC-42, cobertura incompleta de FR-011, referencias faltantes en tareas iniciales y ausencia de un criterio explícito de concurrencia para pagos recurrentes.

No se modificó código productivo ni se ejecutaron pruebas funcionales.

**Evidencias:**

- Transcript de E4-SK-04.
- `E4_SPECKIT_FINAL_CONTRACT_AUDIT.md`.
- `spec.md`, `plan.md`, `tasks.md`.
- Contratos `api.md` y `events.md`.
- Resultado de `check-prerequisites.ps1` y validación de integración.

**Implicaciones D1–D5:**

- **D1:** 46 min 48 s reportados por Codex. Tokens, costo, llamadas y modelo efectivo: N/D.
- **D2:** sin cambios productivos; calidad estática E4 todavía no medida.
- **D3:** trazabilidad documental completa según comprobaciones del agente. Especificación funcional principal reportada con 247 líneas.
- **D4:** criterios definidos, pero cumplimiento funcional E4 todavía NOT VERIFIED.
- **D5:** correcciones documentales realizadas; aprobación de implementación pendiente.

**Decisión del supervisor:** aceptar el paquete documental sin solicitar nuevas rondas de auditoría. Recomendar Gate B para iniciar la implementación.

**Decisión humana Gate B:** pendiente de registro explícito.

**Próximo paso:** tras la aprobación, ejecutar E4-SK-05 para implementar el núcleo financiero, la migración multimoneda y la conversión de divisas.

### E4-SK-05 — Intento inicial y resolución del bloqueo de Gate B

**Fecha:** 16 de noviembre de 2026  
**Estado:** Intento inicial detenido; autorización preparada.

**Objetivo:** Iniciar la implementación de Shift Bank E4 mediante el flujo nativo de GitHub Spec Kit.

**Acciones ejecutadas:**

- Codex inspeccionó el registro de decisiones y los checklists.
- Confirmó que Gate B todavía no estaba aprobado.
- Identificó 24 verificaciones contractuales sin marcar.
- Detuvo la implementación sin modificar archivos.

**Resultados verificables:**

| Indicador | Resultado |
|---|---|
| Checklist de requisitos | 16/16 |
| Checklist contractual | 24 pendientes de aceptación |
| Archivos modificados | 0 |
| Pruebas ejecutadas | 0 |
| Tareas implementadas | 0 |
| Duración reportada | 23 segundos |

**Problemas y correcciones:**

Se identificó una deficiencia en la coordinación entre el supervisor y Codex: el prompt exigía una autorización explícita que todavía no había sido entregada.

Se preparó un único mensaje que permite al investigador autorizar Gate B, aceptar los 24 puntos basándose en la auditoría documentada y comenzar la implementación sin más revisiones preparatorias.

**Evidencia:** Transcript del intento inicial E4-SK-05.

**Implicaciones D1–D5:**

- **D1:** 23 segundos reportados; tokens y costos N/D.
- **D2:** sin modificaciones del código.
- **D3:** especificaciones existentes sin cambios.
- **D4:** sin pruebas funcionales ejecutadas.
- **D5:** bloqueo administrativo adicional identificado; corrección del procedimiento de autorización propuesta.

**Decisión humana:** pendiente de que el investigador envíe la autorización explícita.

**Próximo paso:** registrar Gate B y ejecutar el primer bloque funcional de implementación.

### E4-SK-05 — Implementación del núcleo financiero y migración multimoneda

**Fecha:** 16 de noviembre de 2026  
**Estado:** Completado — primera implementación funcional.

**Objetivo:** Implementar el núcleo de persistencia financiera, migración multimoneda, conversiones FX, Event Sourcing y CQRS, preservando los contratos bancarios heredados.

**Acciones ejecutadas:**

- Registro de aprobación explícita de Gate B y aceptación de los 24 criterios contractuales.
- Implementación de tablas de eventos, idempotencia, versiones y proyecciones SQLite.
- Migración incremental y preservación de cuentas COP.
- Aprovisionamiento de las cuatro cuentas de referencia D-02.
- Implementación de operaciones monetarias exactas y conversiones USD/EUR/GBP.
- Integración de transferencias, límites y MFA con idempotencia y control de versiones.
- Desarrollo de pruebas focalizadas de migración, eventos, aritmética, API, atomicidad, seguridad y concurrencia.
- Ejecución de regresiones heredadas y corrección de incompatibilidades documentadas.

**Resultados verificables:**

| Indicador | Resultado |
|---|---|
| Tareas completadas | 39/68 |
| Tareas pendientes | 29 |
| Última ejecución seleccionada de pytest | 83 aprobadas |
| Advertencias | 1 |
| Duración de la última suite | 15,19 segundos |
| Duración reportada del hito Codex | 56 min 30 s |
| Despliegue | No ejecutado |
| Benchmark Locust | No ejecutado |
| SonarQube E4 | No ejecutado |

**Problemas y correcciones:**

Durante la implementación se identificaron y corrigieron errores en fixtures, migración, expectativas de contratos HTTP, reproducción de proyecciones y pruebas heredadas.

Se registraron fallos intermedios antes de aplicar las correcciones.

La ejecución utilizó bases SQLite desechables. No se acreditó ninguna migración sobre datos históricos o productivos.

**Evidencias:**

- `E4_SPECKIT_GATE_B_APPROVAL_2026-11-16.md`
- `E4-SK-05-IMPLEMENTATION-RUN.md`
- `E4_SPECKIT_IMPLEMENTATION_MILESTONE_2026-11-16.md`
- `tasks.md`
- Directorio `implementation-evidence/`
- Transcript completo E4-SK-05.

**Implicaciones D1–D5:**

- **D1:** 56 min 30 s reportados. Tokens, costo, modelo efectivo y llamadas totales N/D.
- **D2:** cambios en backend y pruebas; métricas estáticas y LOC final pendientes.
- **D3:** especificaciones actualizadas principalmente en estado de autorización y seguimiento; medición documental final pendiente.
- **D4:** 83 pruebas seleccionadas aprobadas; faltan frontend, ACH/recurrentes y aceptación integral.
- **D5:** múltiples fallos y correcciones documentados; modificaciones a pruebas heredadas que requieren contraste con contratos reales.

**Decisión de supervisión:** aceptar E4-SK-05 como primer hito de implementación completado y continuar directamente con el resto de las funcionalidades.

**Próximo paso:** E4-SK-06 — integrar ACH/recurrentes, completar frontend y ejecutar regresión funcional conjunta.

### E4-SK-06 — Integración funcional completa de Shift Bank E4

**Fecha:** 16 de noviembre de 2026  
**Estado:** Completado — pendiente de validación operacional final.

**Objetivo:** Terminar las funcionalidades restantes de la Etapa 4, integrando operaciones ACH y recurrentes con Event Sourcing/CQRS y completando la interfaz multimoneda.

**Acciones ejecutadas:**

- Adaptación de ACH para COP heredado y USD, con rechazo de EUR/GBP.
- Integración de eventos, proyecciones, auditoría e idempotencia en ACH y operaciones recurrentes.
- Implementación de mecanismos de ejecución única para pagos recurrentes concurrentes.
- Incorporación de aritmética monetaria exacta con BigInt en frontend.
- Actualización de formularios y consultas para cuentas, transferencias, conversiones, MFA, ACH y recurrencia.
- Incorporación de versiones de cuentas y claves de idempotencia en las solicitudes.
- Ejecución de regresiones completas de backend y frontend.
- Corrección de errores de integración, pruebas y contratos.

**Resultados observados:**

| Indicador | Resultado |
|---|---|
| Tareas completadas acumuladas | 60/68 |
| Tareas pendientes | T061–T068 |
| Backend pytest | 138 PASS |
| Advertencias backend | 1 |
| Frontend Vitest | 20 PASS |
| Archivos de pruebas frontend | 4 |
| Compilación TypeScript y build | PASS |
| Pruebas ACH/recurrentes focalizadas | 10 PASS |
| Duración de la última suite backend | 29,81 segundos |
| Duración reportada del hito Codex | 57 min 53 s |
| Docker/Locust/SonarQube | No ejecutados |

**Problemas y correcciones:**

La primera ejecución completa de backend detectó 11 fallos, posteriormente corregidos. Entre los problemas identificados estuvieron el aislamiento de fixtures, diferencias en contratos HTTP heredados, formatos de fechas UTC y validaciones obligatorias de versiones.

La ejecución inicial de Vitest encontró problemas en los mocks y aserciones correspondientes a los nuevos parámetros de idempotencia y versiones; se corrigieron y la suite final aprobó.

Se añadió verificación con solicitudes HTTP cifradas que omiten el adaptador de compatibilidad del entorno de pruebas.

Se documentaron fallos intermedios y se eliminaron únicamente los archivos temporales de prueba generados dentro de E4.

**Evidencias:**

- `specs/004-shift-bank-stage4-multicurrency-eventsourcing-cqrs/tasks.md`
- `implementation-evidence/E4-SK-06-IMPLEMENTATION-RUN.md`
- `implementation-evidence/E4-SK-06-BASELINE-FAILURES.md`
- Transcript completo de E4-SK-06.

**Dimensiones experimentales:**

- **D1 — Esfuerzo:** 57 min 53 s reportados por Codex; tokens, costo, modelo efectivo y llamadas totales N/D.
- **D2 — Calidad de código:** funcionalidades backend/frontend implementadas; métricas estáticas E4 pendientes.
- **D3 — Formalización:** especificaciones existentes utilizadas como base de implementación; mediciones consolidadas pendientes.
- **D4 — Calidad funcional:** 138 pruebas backend y 20 frontend aprobadas; build exitoso. Pendientes pruebas de despliegue y rendimiento.
- **D5 — Intervención humana:** implementación bajo Gate B previamente aprobado; correcciones técnicas realizadas por Codex dentro del alcance autorizado.

**Decisión del supervisor:** aceptar E4-SK-06 como implementación funcional completada, sin abrir nuevos hitos de desarrollo.

**Próximo paso:** E4-SK-07 — verificación de despliegue, rendimiento, calidad estática y consolidación de las métricas D1–D5.

### E4-SK-07 — Validación operacional y evaluación experimental

**Fecha:** 16 de noviembre de 2026  
**Estado:** Finalizado con limitaciones; T068 pendiente de cierre humano.

**Objetivo:** Verificar el funcionamiento integral de Shift Bank E4 y obtener resultados de despliegue, rendimiento, calidad estática y métricas experimentales.

**Acciones ejecutadas:**

- Corrección de una expectativa FX incorrecta: USD 100 → EUR 90, según la tasa 9/10.
- Ejecución de regresiones backend/frontend y compilación de producción.
- Despliegue aislado mediante Docker Compose, Nginx y HTTPS.
- Verificación de transacciones cifradas, idempotencia, persistencia, replay y auditoría.
- Ejecución de pruebas Locust con 30 usuarios.
- Análisis estático mediante una instancia aislada de SonarQube.
- Consolidación inicial de evidencias y resultados D1–D5.

**Resultados observados:**

| Métrica | Resultado |
|---|---|
| Tareas completadas | 67/68 |
| Backend | 138 PASS |
| Frontend | 20 PASS |
| TypeScript y build | PASS |
| Docker/Nginx/TLS | PASS |
| Locust — lecturas p95 | 99 ms |
| Locust — transferencias p95 | 5.278 ms |
| Errores inesperados | 0% |
| SonarQube Quality Gate | OK |
| Bugs / vulnerabilidades / smells | 4 / 0 / 93 |
| Deuda técnica | 959 minutos |
| Cobertura importada a Sonar | No disponible |
| Duración reportada del hito | 38 min 58 s |

**Limitaciones:**

1. El rendimiento de transferencias incumplió el objetivo p95 inferior a 500 ms en la carga ejecutada.
2. El perfil medido fue 60% balances, 30% transferencias y 10% historial, diferente del AC-45 aprobado: 60% balances, 30% historial y 10% transferencias.
3. Los cuatro bugs de SonarQube no cuentan con un dictamen individual documentado.
4. La cobertura de SonarQube no se acreditó porque no se importó un reporte de cobertura.
5. El modelo efectivo, tokens, costo y total de llamadas del agente permanecen N/D.

**Evidencias:**

- `acceptance/E4-SK-07-FINAL-VALIDATION.md`
- `acceptance/E4-SK-07-acceptance-matrix.md`
- `acceptance/E4-SK-07-review-package.md`
- `implementation-evidence/E4-SK-07-locust-metrics.json`
- `implementation-evidence/E4-SK-07-sonarqube-metrics.json`
- `implementation-evidence/E4-SK-07-deployment-smoke.json`

**Dimensiones experimentales:**

- **D1:** duración reportada de 38 min 58 s; telemetría de tokens/costo N/D.
- **D2:** Quality Gate OK con 4 bugs, 93 code smells y 959 minutos de deuda; cobertura no medida adecuadamente.
- **D3:** documentación Spec Kit consolidada; métricas completas pendientes de informe final.
- **D4:** regresiones y despliegue aprobados; rendimiento de transferencias fallido en el perfil ejecutado; AC-45 no verificado con su distribución original.
- **D5:** correcciones técnicas, fallos y reintentos documentados, incluyendo la discrepancia del protocolo de carga.

**Decisión de supervisión:** no iniciar nuevas rondas de desarrollo. Realizar una única medición con el perfil AC-45 correcto, si es seguro, y cerrar con las limitaciones observadas.

**Próximo paso:** E4-SK-08 — cierre experimental definitivo y reporte final para la tesis.

### E4-SK-08 — Cierre definitivo del experimento Spec Kit

**Fecha:** 16 de noviembre de 2026  
**Estado:** CLOSED WITH DOCUMENTED LIMITATIONS.

**Objetivo:** Completar la última tarea de revisión, ejecutar el benchmark AC-45 con el perfil aprobado y consolidar las evidencias de las dimensiones D1–D5.

**Acciones ejecutadas:**

- Corrección del perfil Locust para utilizar 60% consultas de balances, 30% consultas de historial y 10% transferencias.
- Ejecución de una única prueba con 30 usuarios, incorporación de 5 usuarios/s y duración sostenida de 60 segundos.
- Consolidación de métricas funcionales, estáticas y documentales.
- Registro de aceptación final con limitaciones.
- Cierre de T068 y actualización de `tasks.md` a 68/68.
- Elaboración de `CIERRE_ETAPA4_SPECKIT.md`.

**Resultados:**

| Indicador | Resultado |
|---|---|
| Tareas cerradas | 68/68 |
| Criterios de aceptación | 44 PASS, 1 FAIL |
| Backend | 138 PASS |
| Frontend | 20 PASS |
| Despliegue aislado | PASS |
| AC-45 — Lecturas p95 | 172,57 ms — PASS |
| AC-45 — Transferencias p95 | 2.803,02 ms — FAIL |
| Errores inesperados | 0% |
| SonarQube Quality Gate | OK |
| Bugs | 4 |
| Code smells | 93 |
| Deuda técnica | 959 minutos |
| Duración reportada de E4-SK-08 | 11 min 31 s |

**Limitaciones experimentales:**

- El criterio AC-45 no se cumplió por latencia de transferencias.
- Persisten cuatro bugs reportados por SonarQube.
- No se importó un informe de cobertura; la cobertura real permanece N/D.
- El modelo efectivo, los tokens y el costo no pudieron recuperarse.
- Los archivos E4 todavía deben respaldarse mediante control de versiones.
- No se acreditó la invocación explícita de todas las habilidades nativas de Spec Kit.

**Evidencia principal:**

`Etapa 4/_experiment_logs/Spec Kit/acceptance/CIERRE_ETAPA4_SPECKIT.md`

**Decisión final:** cerrar la Etapa 4 de Spec Kit con limitaciones documentadas, conservar los resultados fallidos y utilizarlos sin modificaciones en el estudio comparativo.

**Estado final:** experimento completado; pendiente únicamente el respaldo del repositorio y la integración de resultados en el informe de tesis.

