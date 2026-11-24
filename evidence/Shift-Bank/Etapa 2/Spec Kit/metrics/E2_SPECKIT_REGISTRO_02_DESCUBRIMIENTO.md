# E2 Spec Kit — Hito 1: Registro de descubrimiento

**Estado:** ABIERTO — no rellenar resultados antes de recibir la respuesta real de Gemini.  
**Fecha de preparación de la plantilla:** 2026-11-14  
**Ruta sugerida:** `Shift-Bank/Etapa 2/_experiment_logs/Spec Kit/E2_SPECKIT_REGISTRO_02_DESCUBRIMIENTO.md`

## Fuentes y procedencia

- Semilla propuesta: `Etapa 2/SEED-2.md` (versión y fecha de aprobación humana: **pendiente**).
- Contrato común propuesto: `Etapa 2/E2_COMMON_FUNCTIONAL_CONTRACT.md` (aprobación: **pendiente**).
- Prompt exacto: `PROMPT_01_READ_ONLY_DISCOVERY.md` (guardar archivo sin reescritura).
- Referencias históricas del investigador: `SHIFT_BANK_E2_CONTRATO_COMUN_Y_REFERENCIA_TESSL.md`, matriz de etapas y guía de métricas.
- Base operativa: `E2_SPECKIT_REGISTRO_01_PREPARACION.md` y manifiestos SHA-256, ya generados en la preparación anterior.

## Línea base heredada (según preparación; pendiente de confirmación por Gemini)

- Copia aislada de E1: 59 archivos durables, 59/59 hashes iguales.
- Pruebas heredadas: backend 12/12; frontend 5/5; frontend build OK.
- Reglas Stage 1: COP, MFA >= 1.000.000 COP, PIN `123456`, TTL 300 s.
- Semilla reproducible del código: checking 5.000.000 COP, savings 15.000.000 COP.
- BD histórica preservada exclusivamente en E1: checking 4.000.000 COP, savings 16.000.000 COP; no copiada.
- Spec Kit v1.0.6; Gemini CLI instalado v0.65.0 frente a protocolo v0.60.0; modelo configurado `gemini-3.5-flash` sin verificación efectiva.
- Node 20.17.0 y advertencia de dependencia frontend que solicita Node >= 22; 12 vulnerabilidades reportadas por npm ci. No se autorizaron cambios de dependencias en preparación.

## Sesión de descubrimiento (rellenar con evidencia real)

| Campo | Resultado / evidencia |
|---|---|
| Fecha/hora real inicio y final | PENDIENTE |
| Comando de arranque usado | PENDIENTE |
| Versión CLI/modelo realmente observados | PENDIENTE |
| Identificador de sesión / JSONL / transcript | PENDIENTE |
| Prompt enviado exactamente | `PROMPT_01_READ_ONLY_DISCOVERY.md` |
| Archivos leídos por Gemini | PENDIENTE |
| Archivos modificados (debe ser ninguno) | PENDIENTE |
| Resumen de inventario y compatibilidad | PENDIENTE |
| Decisiones pendientes detectadas | PENDIENTE |
| Primera pregunta de aclaración | PENDIENTE |
| Respuesta humana, fecha y alcance | PENDIENTE |
| `/stats` y salida final de la sesión | PENDIENTE |
| Incidencias, desvíos y correcciones | PENDIENTE |

## Puntos de control

- [ ] El investigador aprobó la semilla común antes de autorizar cambios a specs.
- [ ] Se conservó la fuente y la versión exacta del contrato enviado.
- [ ] Gemini confirmó el Spec Kit realmente instalado, sin reinicialización.
- [ ] Ningún archivo de código, specs ni constitución fue alterado durante descubrimiento.
- [ ] La desviación de versión/modelo fue registrada sin ocultarla.
- [ ] Se preservó E1 y su base de datos histórica sin mutaciones.
- [ ] La primera pregunta material se resolvió y quedó registrada.
- [ ] Se aprobó explícitamente pasar a `/speckit.specify`.

**No marcar un ítem como cumplido por una promesa del agente; comprobar con transcript, comparación de archivos o comandos ejecutados.**


Shift Bank E2 / Spec Kit — Registro 02: descubrimiento Gemini
- Etapa: 2, Opción A, preespecificación.
- Fecha indicada por la captura: 2026-11-14 (fecha/hora exacta de inicio y cierre de sesión: NO DOCUMENTADA).
- Fuente primaria: sesiones/E2_SPECKIT_GEMINI_HITO01_TRANSCRIPCION_COPIA.txt (copia del texto recibido del investigador; la exportación JSONL o transcript íntegro de Gemini CLI sigue pendiente).
- Prompt: PROMPT_01_READ_ONLY_DISCOVERY.md conservado en paquete Hito 1.
- Estado: descubrimiento entregado; decisiones de negocio y aprobación de especificación pendientes. Este archivo es una síntesis del investigador basada en la captura, no una métrica inventada por el agente.
A. Resultados observados en la salida de Gemini
Campo	Observación	Evidencia de la captura
Integración Spec Kit	1.0.6; 10 comandos .gemini/commands	Inspección de archivos y reporte Gemini
Constitución	v1.2.0, conservada	Reporte Gemini
Feature activo antes de E2	specs/001-shift-bank-stage1, .specify/feature.json	Get-Content .specify/feature.json
Siguiente feature previsto	specs/002-shift-bank-stage2	Propuesta de Gemini; NO CREADO aún según esta captura
Gemini CLI	0.65.0; protocolo inicial 0.60.0	gemini --version
Modelo	variable GEMINI_MODEL=gemini-3.5-flash	listado de entorno; NO prueba de enrutamiento efectivo
Backend	12 pruebas aprobadas, 1 warning	pytest backend/tests/test_api.py -v
Frontend	5 pruebas aprobadas	npm --prefix frontend test -- --run
Build	tsc && vite build exitoso	npm --prefix frontend run build
Archivos durables	59	conteo informado; no consta comparación SHA posterior en esta captura
Moneda y balances de semilla	COP; checking 5.000.000, savings 15.000.000	backend/src/database.py y consulta Stage 2 DB
MFA heredado	>= 1.000.000 COP; código 123456; vencimiento 300 s; reintentos ilimitados durante la vigencia, sin bloqueo	Inspección de API/test; hallazgo reportado por Gemini
SQLite observado en E2	cuentas 5M/15M y tercer registro de transferencia EXPIRED además de 2 seed	Read accounts/transfers from backend/shift_bank.db


B. Brechas de E2 identificadas
- ACH: destinatarios guardados/ad hoc, validación routing/cuenta, estados pending–settled–failed, débito inicial y reintegro idempotente.
- Recurrencia: scheduler automático, frecuencias +1/+7/+30 días, estado active/paused/cancelled, ejecución y fallos.
- Límites: por operación y diario, editable en UI, UTC, evaluación previa a MFA y en cada ejecución programada.
- Frontend: transferencias diferenciadas, beneficiarios, programaciones, estado, validación inmediata de routing y panel de límites.
- Persistencia: extender SQLite sin eliminar ni reescribir datos históricos legítimos.
- Especificaciones: mantener specs/001-shift-bank-stage1, crear feature E2 independiente, sin modificar constitución.
C. Incidencias / precisiones de rigor
1. Alcance de solo lectura incumplido parcialmente: Gemini ejecutó pytest, npm test y npm build, que pueden crear caches, dist y base de prueba. El prompt no los autorizaba en esta etapa. Debe contabilizarse como desviación operativa, aunque los tests pasaron.
2. Se accedió a backend/shift_bank.db de E2: la afirmación de que "the database ... has not been accessed" solo puede referirse a la BD histórica preservada en E1. La copia E2 sí fue consultada y mostró un registro EXPIRED adicional. Es compatible con una base mutada por tests; no se infiere el origen exacto sin más evidencia.
3. Git no estaba íntegramente limpio: git status mostraba archivos E2 no rastreados y cambios en otras carpetas del repositorio. No afirmar que todo el repositorio esté limpio. No atribuir esos cambios al agente de E2 sin evidencia.
4. Integridad de archivos posterior: se requiere cotejar el manifiesto E2_READY_FOR_GEMINI_SHA256.csv del Hito 0 contra el estado actual, excluyendo artefactos generados. La captura NO contiene esa comparación.
5. Modelo sin comprobar: GEMINI_MODEL configurado no identifica de forma concluyente el modelo servido. Exportar /stats/transcript de la sesión; registrar cualquier enrutamiento alternativo.
6. Archivo fuente primario parcial: el .txt suministrado reproduce salida de pantalla (con bloques abreviados). No demuestra exhaustividad de la sesión. Conservar, si se puede, JSONL original y /stats final.
D. Elementos resueltos versus decisiones pendientes
Herencia confirmada y no negociable: COP, MFA desde 1M inclusive, PIN 123456, reto 300 s sin lockout, saldos seed 5M/15M; preservar todas las pruebas E1.

Pendiente de aprobación humana prospectiva: límites iniciales en COP; fixture/BD de arranque; MFA al crear recurrencia sensible; operación automática real del scheduler. Hay propuestas en E2_SPECKIT_DECISIONES_01_PROPUESTAS.md.

Discreción de Spec Kit durante planificación: definición exacta de tablas, endpoints, partición React, mecanismo interno de scheduler, siempre que satisfaga los resultados observables.

Cambios autorizados a la fecha de esta captura: ninguno sobre especificaciones/código de E2. La especificación 002 no se considera creada.
E. Próximo punto de control
Al revisar las cuatro propuestas en E2_SPECKIT_DECISIONES_01_PROPUESTAS.md, el investigador puede enviar PROMPT_02_SPECKIT_SPECIFY.md, cuyo envío constituye aprobación únicamente de esas decisiones y de la escritura de artefactos de especificación. No se autoriza plan técnico ni código; conservar respuesta, hashes y diff generado.

# Shift Bank — Etapa 2: Spec Kit
## Bitácora acumulativa del experimento

**Fecha de inicio:** 14 de noviembre de 2026  
**Última actualización:** 14 de noviembre de 2026  
**Herramienta SDD:** GitHub Spec Kit 1.0.6  
**Agente:** Gemini CLI 0.65.0  
**Modelo configurado:** `gemini-3.5-flash`  
**Caso de estudio:** Sistema bancario simulado  
**Etapa:** 2 — Complejidad funcional y estado  
**Opción:** A  
**Estado:** Especificación generada; aclaración pendiente.

---

## 1. Objetivo y metodología

Evaluar la capacidad de Spec Kit para ampliar la aplicación Shift Bank desarrollada en la Etapa 1, conservando sus funcionalidades, arquitectura y contratos existentes.

Las capacidades nuevas son:

1. Transferencias ACH simuladas a terceros.
2. Pagos recurrentes automáticos.
3. Límites dinámicos por transferencia y acumulados diarios.

Se aplica el flujo SDD nativo de Spec Kit, con especificación previa a las modificaciones de código y validación posterior contra los requisitos.

### 1.1. Reglas experimentales

- Todas las interacciones con Gemini se realizan en inglés.
- Se conserva la implementación de E1 de la propia herramienta, sin utilizar código de Tessl u otras herramientas.
- Los cambios funcionales se autorizan primero mediante especificaciones.
- Se registran los resultados reales, incluidos fallos y desviaciones.
- Las conclusiones del agente requieren contraste con evidencia.
- La documentación narrativa del investigador se mantiene en esta única bitácora.

**Procedencia del contrato:** `SEED-2.md` y `E2_COMMON_FUNCTIONAL_CONTRACT.md` fueron preparados el 14 de noviembre de 2026 para las herramientas restantes. No constituyen evidencia de una semilla común utilizada históricamente por Tessl.

---

## 2. Hito 0 — Preparación del entorno

**Estado:** Completado.

Se preparó una copia independiente de la implementación E1 de Spec Kit:

- Origen: `Shift-Bank/Etapa 1/Spec Kit`
- Destino: `Shift-Bank/Etapa 2/Spec Kit`
- Evidencias: `Shift-Bank/Etapa 2/_experiment_logs/Spec Kit`

### 2.1. Integridad y reproducibilidad

La preparación previa registró:

| Indicador | Resultado |
|---|---|
| Archivos durables E1 | 59 |
| Coincidencias SHA-256 | 59/59 |
| Archivos inesperados o modificados en copia | 0 |
| Pruebas backend | 12 aprobadas |
| Pruebas frontend | 5 aprobadas |
| Build frontend | Correcto |
| Constitución Spec Kit | v1.2.0 |
| Commit de referencia | `130ca53c2854e042f89c8a957182c7925b176d6f` |

Se conservaron los manifiestos SHA-256 originales y los resultados de pruebas.

### 2.2. Estado bancario heredado

La implementación E1 utiliza:

- Moneda: COP.
- Checking: COP 5.000.000,00.
- Savings: COP 15.000.000,00.
- Dos transferencias históricas definidas en la semilla de código.
- Transferencias internas entre cuentas propias.
- Historial de movimientos y saldos.
- MFA simulado desde COP 1.000.000,00 inclusive.
- Código MFA `123456`.
- Vigencia de 300 segundos.
- Reintentos ilimitados durante la vigencia, sin bloqueo.

La base histórica de E1 contiene un estado mutable distinto: Checking COP 4.000.000, Savings COP 16.000.000 y cinco movimientos. Se decidió conservarla sin migrarla y utilizar la semilla reproducible del código para la ejecución E2.

### 2.3. Observaciones del entorno

- Gemini CLI instalado: 0.65.0; versión objetivo del protocolo: 0.60.0.
- Variable `GEMINI_MODEL=gemini-3.5-flash`; el enrutamiento efectivo del modelo no está verificado.
- Node 20.17.0; una dependencia frontend declara requerir Node 22 o superior.
- `npm ci` reportó 12 vulnerabilidades en dependencias.
- No se realizaron actualizaciones correctivas de dependencias durante la preparación.

Las desviaciones de versión se mantienen como observaciones experimentales.

---

## 3. Iteración 01 — Descubrimiento de E1

**Comando:** Prompt de descubrimiento de solo lectura.  
**Estado:** Completado.  
**Evidencia:** Transcripción de Gemini del 14 de noviembre de 2026.

### 3.1. Actividades ejecutadas

Gemini inspeccionó:

- La constitución de Spec Kit.
- La especificación E1.
- Contratos de API.
- Modelos, base de datos y rutas backend.
- Componentes y servicios frontend.
- Pruebas heredadas.
- Configuración e integración de Spec Kit.
- Semilla y contrato de Etapa 2.

Confirmó la disponibilidad de diez comandos nativos de Spec Kit y el directorio activo inicial `specs/001-shift-bank-stage1`.

### 3.2. Resultados

| Componente | Hallazgo |
|---|---|
| ACH | No existe; requiere beneficiarios, transferencias externas y estados |
| Recurrencia | No existe; requiere programaciones y ejecución automática |
| Límites | Solo existe umbral MFA; faltan límites configurables |
| Frontend | Requiere ampliar formularios y controles |
| Persistencia | SQLite; requiere ampliación de datos |
| MFA | Reutilizar comportamiento heredado sin introducir bloqueo |

Gemini volvió a ejecutar las pruebas: 12 backend y 5 frontend aprobadas, además de una compilación frontend correcta.

### 3.3. Incidencias

1. Se ejecutaron pruebas durante una actividad solicitada como descubrimiento de solo lectura. Esto excedió la intención restrictiva del prompt.
2. Un comando de inspección SQLite falló por problemas de interpretación de comillas en PowerShell. Las consultas posteriores funcionaron.
3. La base SQLite generada en E2 mostró un registro `EXPIRED` adicional respecto de la semilla limpia. Este dato de ejecución no se considera parte de la semilla reproducible.
4. El repositorio general contenía modificaciones ajenas al experimento en Tetris, aunque Gemini calificó el directorio de trabajo de Spec Kit como limpio.

No se dispone de una comparación independiente posterior a esta sesión que certifique ausencia absoluta de modificaciones en todos los archivos.

---

## 4. Decisiones aprobadas — D-01 a D-04

Las siguientes decisiones fueron comunicadas y aprobadas mediante el prompt de `/speckit.specify`.

| ID | Decisión |
|---|---|
| D-01 | Límite inicial de COP 5.000.000 por operación y COP 10.000.000 acumulados por día UTC, editables |
| D-02 | Utilizar la semilla reproducible de E1, sin importar la base histórica |
| D-03 | Exigir MFA al crear pagos recurrentes desde COP 1.000.000; no cobrar al crear ni pedir MFA interactivo en ejecución automática |
| D-04 | Ejecutar automáticamente los pagos vencidos mientras el backend/scheduler está funcionando |

Los límites COP son una decisión prospectiva específica de esta ejecución y no se consideran económicamente equivalentes a límites definidos en USD.

---

## 5. Iteración 02 — `/speckit.specify`

**Estado:** Completado según transcripción.  
**Fecha:** 14 de noviembre de 2026.

### 5.1. Objetivo

Crear una especificación E2 independiente, con requisitos verificables para ACH, pagos recurrentes, límites dinámicos y compatibilidad E1.

### 5.2. Artefactos reportados

| Artefacto | Resultado |
|---|---|
| `specs/002-shift-bank-stage2/spec.md` | Creado, 269 líneas |
| `specs/002-shift-bank-stage2/checklists/requirements.md` | Creado, 35 líneas |
| `.specify/feature.json` | Actualizado para activar E2 |

Gemini reportó cuatro historias de usuario, requisitos funcionales, escenarios de aceptación, casos límite y una matriz de trazabilidad con las familias ACH, REC, LIM y HER.

### 5.3. Resultado de calidad declarado por Gemini

El checklist generado reportó:

- Calidad de contenido: PASS.
- Completitud de requisitos: PASS.
- Preparación de la funcionalidad: PASS.
- Marcadores `NEEDS CLARIFICATION`: ninguno.

Estas afirmaciones corresponden al propio agente. La especificación completa todavía no ha sido contrastada independientemente contra todos los requisitos.

### 5.4. Incidencias

**INC-01 — Entrada truncada.** El prompt llegó a Gemini incompleto, terminando en `Do NOT i`, aproximadamente después de 4.000 caracteres útiles. La ejecución continuó. No puede darse por recibida la instrucción final completa.

**INC-02 — Invocación de PowerShell.** El script intentó utilizar `pwsh`, que no estaba disponible. Luego utilizó `powershell -NoProfile -ExecutionPolicy Bypass` y obtuvo correctamente las rutas de la funcionalidad E2.

**INC-03 — Artefacto adicional.** Se generó `checklists/requirements.md`, aunque la autorización del prompt se había limitado a la nueva especificación y los metadatos mínimos. Este archivo pertenece al flujo nativo de Spec Kit, pero se registra como diferencia respecto del alcance literal autorizado.

**INC-04 — Verificación parcial.** La transcripción muestra fragmentos de la especificación y el resumen final, no una lectura independiente íntegra de sus 269 líneas.

### 5.5. Conclusión de la iteración

La funcionalidad E2 fue registrada como nueva característica de Spec Kit sin necesidad de reescribir la especificación histórica de E1. El agente declaró completado el proceso de especificación, pero es necesario revisar ambigüedades e inconsistencias antes de autorizar la planificación.

---

## 6. Ajuste del protocolo de interacción

Después de detectar truncamiento del prompt, se adopta una política conservadora:

- Prompts preferidos: 300–800 caracteres.
- Prompts complejos: hasta aproximadamente 1.200 caracteres.
- Contexto extenso: referenciar archivos existentes.
- Una operación SDD principal por interacción.
- Establecer explícitamente el límite de autorización y la condición de parada.
- Incluir una marca final breve cuando sea útil para detectar truncamiento.

No se afirma que Gemini CLI tenga un límite oficial de 1.200 o 4.096 caracteres. Estos valores son controles operativos del experimento.

---

## 7. Estado de las dimensiones de evaluación

| Dimensión | Estado de evidencia |
|---|---|
| D1 — Esfuerzo y consumo | Sesiones iniciadas; tokens, tiempo y llamadas consolidadas: N/D |
| D2 — Calidad del código | Línea base heredada; SonarQube E2 aún no ejecutado |
| D3 — Especificaciones | Una especificación E2 de 269 líneas reportadas; recuento completo pendiente |
| D4 — Expectativa funcional | Contratos definidos; validación E2 aún no ejecutada |
| D5 — Retroalimentación | Incidencias de descubrimiento y especificación registradas |

`N/D` significa que no hay evidencia suficiente para consignar un valor. Los números de prompts del investigador no se sustituyen por métricas `Msgs` de Gemini CLI.

---

## 8. Siguiente iteración — Aclaración

**Iteración 03:** `/speckit.clarify`  
**Estado:** Pendiente de ejecución.

### Propósito

Revisar la especificación E2 contra la semilla, el contrato común y la constitución; identificar decisiones realmente ambiguas y corregir exclusivamente la especificación mediante el flujo nativo, después de la aprobación humana correspondiente.

Aspectos prioritarios:

- ACH: estados, liquidación e idempotencia de reintegros.
- Pagos recurrentes: primera ejecución, periodicidades, fallos y cancelación terminal.
- Integración MFA: conservación de los contratos E1.
- Límites COP: acumulados diarios y frontera UTC.
- Compatibilidad entre las funcionalidades heredadas y las nuevas.

### Criterios de cierre

La iteración se considera completa cuando Gemini haya expuesto las aclaraciones realizadas, los cambios en la especificación y los asuntos pendientes, sin modificar código ni iniciar planificación o implementación.

**Implementación E2:** No autorizada todavía.

---

## 9. Fuentes de evidencia

- `SEED-2.md`
- `E2_COMMON_FUNCTIONAL_CONTRACT.md`
- Constitución y especificaciones nativas de Spec Kit.
- Manifiestos SHA-256 de preparación.
- Transcripciones originales de descubrimiento y `/speckit.specify`.
- Resultados originales de Pytest, Vitest y Vite.
- Archivos de especificación generados por Gemini.

Las transcripciones y resultados originales se conservan separados de esta interpretación del investigador.

**Último hito completado:** Iteración 02 — Especificación.

**Próximo hito:** Iteración 03 — Aclaración.

# Shift Bank — Etapa 2: Spec Kit
## Bitácora acumulativa del experimento

**Fecha de inicio:** 14 de noviembre de 2026  
**Última actualización:** 14 de noviembre de 2026  
**Herramienta:** GitHub Spec Kit 1.0.6  
**Agente:** Gemini CLI 0.65.0  
**Modelo configurado:** `gemini-3.5-flash`  
**Etapa:** 2 — Complejidad funcional y estado  
**Opción:** A  
**Estado:** Especificación generada; aclaraciones en curso.

---

## 1. Objetivo y metodología

Evaluar la capacidad de Spec Kit para ampliar la aplicación Shift Bank de la Etapa 1 sin introducir regresiones funcionales ni perder trazabilidad entre requisitos, especificaciones, implementación y validación.

Las funcionalidades nuevas son transferencias ACH simuladas a terceros, programación de pagos recurrentes y límites dinámicos.

El experimento sigue el flujo nativo de Spec Kit, con supervisión humana, especificación previa al código y conservación de evidencia.

### Reglas metodológicas

- Todas las interacciones con Gemini se realizan en inglés.
- La implementación parte exclusivamente de la E1 de Spec Kit.
- Los cambios funcionales deben reflejarse en especificaciones aprobadas antes de modificar código.
- Se preservan las decisiones, errores, correcciones y salidas originales.
- No se utilizan implementaciones de Tessl u otras herramientas como plantillas.
- Las métricas se reportan únicamente cuando existe evidencia verificable.

El contrato común de E2 fue elaborado retrospectivamente a partir de la experiencia Tessl. No constituye una semilla históricamente utilizada por todas las herramientas.

---

## 2. Hito 0 — Preparación

**Estado: Completado.**

Se copió la implementación E1 de Spec Kit a un directorio independiente de E2, sin modificar el proyecto original.

| Indicador | Resultado |
|---|---|
| Archivos durables heredados | 59 |
| Integridad SHA-256 | 59/59 coincidencias |
| Pruebas backend | 12/12 |
| Pruebas frontend | 5/5 |
| Build frontend | Exitoso |
| Spec Kit | 1.0.6 |
| Constitución | 1.2.0 |
| Gemini CLI | 0.65.0 |

### Contratos heredados

- Moneda: COP.
- Checking: COP 5.000.000,00.
- Savings: COP 15.000.000,00.
- Dos movimientos históricos definidos por el código.
- Transferencias entre cuentas propias.
- Consulta de saldos e historial.
- MFA desde COP 1.000.000,00 inclusive.
- Código MFA `123456`.
- Expiración después de 300 segundos.
- Intentos ilimitados durante la vigencia, sin bloqueo.

La base de datos histórica de E1 contiene saldos y operaciones adicionales. Se preserva sin migración y se utiliza la semilla reproducible del código para E2.

### Desviaciones de entorno

- Gemini CLI 0.65.0 frente a versión objetivo 0.60.0.
- Variable `GEMINI_MODEL=gemini-3.5-flash`, sin confirmación independiente del modelo efectivo.
- Node 20.17.0 frente a dependencias que declaran requerir Node 22.
- Doce vulnerabilidades reportadas durante instalación de dependencias.

No se autorizaron actualizaciones correctivas durante preparación.

---

## 3. Iteración 01 — Descubrimiento

**Estado: Completado.**

Gemini inspeccionó la constitución, especificaciones E1, contratos de API, frontend, backend, pruebas y configuración de Spec Kit.

### Resultados

Identificó correctamente:

- Ausencia de transferencias ACH y beneficiarios.
- Ausencia de programaciones recurrentes.
- Ausencia de límites dinámicos.
- Necesidad de ampliar persistencia e interfaz.
- Necesidad de reutilizar las reglas MFA existentes.
- Disponibilidad de diez comandos nativos de Spec Kit.

Las verificaciones reportaron 12 pruebas backend y 5 frontend aprobadas, junto con una compilación exitosa.

### Incidencias

**INC-01:** Gemini ejecutó pruebas durante un descubrimiento solicitado como solo lectura.

**INC-02:** Un comando de inspección SQLite falló por problemas de interpretación en PowerShell; las consultas posteriores funcionaron.

**INC-03:** La base temporal E2 contenía un movimiento `EXPIRED` adicional que no pertenece a la semilla reproducible.

**INC-04:** El repositorio general presentaba modificaciones ajenas a Spec Kit, aunque Gemini calificó el directorio de trabajo como limpio.

La sesión terminó con una matriz de compatibilidad y decisiones pendientes.

---

## 4. Decisiones D-01 a D-04

Estas decisiones fueron aprobadas mediante el prompt de especificación.

| ID | Decisión |
|---|---|
| D-01 | Límites iniciales de COP 5.000.000 por transferencia y COP 10.000.000 diarios, editables |
| D-02 | Usar la semilla reproducible E1 sin migrar la base histórica |
| D-03 | Exigir MFA al crear programaciones desde COP 1.000.000; no debitar al crear ni solicitar MFA interactivo en ejecuciones automáticas |
| D-04 | Ejecutar automáticamente programaciones vencidas mientras el scheduler está activo |

Los límites en COP constituyen una decisión experimental prospectiva y no implican equivalencia económica con los límites USD de Tessl.

---

## 5. Iteración 02 — `/speckit.specify`

**Estado: Completado según transcripción.**

### Objetivo

Generar una especificación E2 independiente utilizando los requisitos comunes ACH, REC, LIM y HER, junto con las decisiones D-01 a D-04.

### Artefactos producidos

| Archivo | Resultado |
|---|---|
| `specs/002-shift-bank-stage2/spec.md` | Creado, 269 líneas reportadas |
| `specs/002-shift-bank-stage2/checklists/requirements.md` | Creado, 35 líneas reportadas |
| `.specify/feature.json` | Referencia actualizada a E2 |

La especificación incluyó cuatro historias de usuario:

1. Límites dinámicos.
2. Transferencias ACH y beneficiarios.
3. Pagos recurrentes.
4. Preservación de E1.

Gemini declaró completa la trazabilidad con los identificadores ACH-01..10, REC-01..12, LIM-01..09, HER-01..06 y A01..A21.

El checklist generado marcó todos sus criterios como satisfactorios. Estos resultados son autoevaluaciones del agente, no certificación independiente.

### Incidencias

**INC-05 — Truncamiento de entrada:** el prompt terminó prematuramente en `Do NOT i`. Se ejecutó `/speckit.specify`, pero no todas las restricciones finales fueron recibidas.

**INC-06 — PowerShell:** falló una llamada con `pwsh`; Gemini utilizó posteriormente `powershell` y obtuvo las rutas correspondientes.

**INC-07 — Artefacto adicional:** Gemini generó un checklist de requisitos además de la especificación y los metadatos expresamente autorizados.

**INC-08 — Verificación parcial:** la transcripción no permite comprobar independientemente la totalidad de las 269 líneas de especificación.

### Resultado

La funcionalidad E2 quedó activa en Spec Kit y preparada para aclaraciones, sin implementación funcional reportada.

---

## 6. Iteración 03 — `/speckit.clarify`

**Estado: En curso.**

### 6.1. Objetivo

Identificar ambigüedades materiales de la especificación y resolverlas mediante decisiones explícitas del investigador, conservando el contrato E1.

### 6.2. Primera pregunta — Estado previo al MFA en programaciones recurrentes

Gemini identificó una ambigüedad en REC-03, REC-09 y D-03.

**Problema:** cuando se crea una programación recurrente sensible, no estaba claramente definido si debía persistirse antes de completar MFA, ni cómo debía comportarse al cerrar la ventana de verificación.

Gemini presentó tres alternativas:

- **A:** persistir como `PENDING_MFA`, permitir reanudación y activar únicamente después de MFA.
- **B:** persistir solamente después de MFA correcto.
- **C:** persistir inmediatamente como `ACTIVE`, bloqueando internamente su ejecución hasta autorización.

La herramienta recomendó A por compatibilidad con el ciclo MFA heredado.

### 6.3. Decisión D-05 — Propuesta enviada para aprobación mediante Gemini

**Selección: Opción A.**

El prompt de respuesta establece las siguientes obligaciones:

1. Una solicitud sensible se persiste inicialmente como `PENDING_MFA`.
2. La validación conserva el código `123456`, duración de 300 segundos, reintentos ilimitados y ausencia de bloqueo.
3. Cerrar la ventana MFA permite recuperar la solicitud pendiente durante su vigencia.
4. Solo una verificación satisfactoria transforma la programación en `ACTIVE`.
5. Al expirar el desafío, el estado pasa a `EXPIRED` y queda excluido de ejecución.
6. No se debitan fondos durante la creación o autorización.
7. El scheduler ejecuta únicamente programaciones elegibles en `ACTIVE`.
8. El primer vencimiento conserva las reglas de REC-04.

**Justificación:** la decisión conserva el ciclo MFA de E1 y separa las solicitudes pendientes de autorización de las programaciones efectivamente activas. Evita ejecutar pagos sin confirmación y mantiene la posibilidad de reanudar la verificación.

**Estado de evidencia:** decisión formulada en el prompt de respuesta. Pendiente de confirmar su recepción, incorporación a `spec.md` y los cambios reales que Gemini efectúe.

### 6.4. Límites de autorización

Para esta iteración solo se autoriza modificar la especificación E2 mediante el flujo de aclaración. No están autorizados cambios de código, pruebas, dependencias, constitución ni especificaciones históricas E1.

Gemini debe continuar formulando una pregunta material por vez.

### 6.5. Evidencia pendiente

- Respuesta de Gemini a D-05.
- Secciones de `spec.md` modificadas.
- Nuevas preguntas y decisiones.
- Confirmación de que no hubo cambios fuera del alcance.
- Estado final del comando `/speckit.clarify`.

---

## 7. Política de longitud de prompts

El truncamiento de la iteración 02 motivó un ajuste operativo.

Se priorizará referenciar los archivos de contrato y especificaciones existentes en lugar de repetirlos íntegramente en los mensajes.

Los prompts tendrán extensión suficiente para expresar las decisiones y restricciones esenciales, procurando permanecer por debajo del punto de truncamiento observado.

El límite detectado es empírico de esta interacción; no se presenta como límite oficial de Gemini CLI.

---

## 8. Estado de dimensiones de evaluación

| Dimensión | Evidencia actual |
|---|---|
| D1 — Esfuerzo y consumo | Transcripciones disponibles; consolidación de tokens y tiempo pendiente |
| D2 — Calidad del código | Pruebas heredadas aprobadas; SonarQube E2 pendiente |
| D3 — Especificaciones | Nueva especificación E2, 269 líneas reportadas; ampliaciones pendientes |
| D4 — Expectativa funcional | Contratos definidos; implementación y validación pendientes |
| D5 — Retroalimentación | Ocho incidencias registradas y una decisión de aclaración formulada |

No se asignan valores inventados para métricas todavía no recolectadas.

---

## 9. Fuentes de evidencia

- `SEED-2.md`
- `E2_COMMON_FUNCTIONAL_CONTRACT.md`
- Constitución y especificaciones nativas de Spec Kit.
- Manifiestos SHA-256 de preparación.
- Transcripciones originales de Gemini CLI.
- Salidas Pytest, Vitest y Vite.
- Checklist y especificación E2 generados.
- Respuestas humanas a las aclaraciones.

Los archivos originales se preservan sin sobrescritura. Esta bitácora documenta e interpreta el desarrollo del experimento, pero no sustituye sus evidencias primarias.

---

## 10. Estado actual y siguiente actividad

**Última iteración confirmada:** Iteración 02 — Especificación generada.

**Iteración actual:** 03 — Aclaraciones.

**Decisión pendiente de confirmación en Gemini:** D-05, persistencia `PENDING_MFA` para programaciones sensibles.

**Próxima actividad:** revisar la respuesta de Gemini a D-05 y continuar con las ambigüedades materiales restantes.

**Planificación e implementación:** todavía no autorizadas.

# Shift Bank — Etapa 2: Spec Kit
## Bitácora acumulativa del experimento

**Fecha de inicio:** 14 de noviembre de 2026  
**Última actualización:** 14 de noviembre de 2026  
**Herramienta SDD:** GitHub Spec Kit 1.0.6  
**Agente:** Gemini CLI 0.65.0  
**Modelo configurado:** `gemini-3.5-flash`  
**Caso de estudio:** Shift Bank  
**Etapa:** 2 — Complejidad funcional y estado  
**Opción:** A  
**Estado:** Especificación generada; aclaraciones en curso.

---

## 1. Objetivo y metodología

Evaluar la capacidad de Spec Kit para ampliar la aplicación Shift Bank de la Etapa 1, conservando sus funcionalidades, arquitectura y contratos existentes.

Las capacidades nuevas son:

1. Transferencias ACH simuladas a terceros.
2. Pagos recurrentes automáticos.
3. Límites dinámicos por transferencia y acumulados diarios.

El experimento sigue el flujo SDD nativo de Spec Kit, con especificación previa a las modificaciones de código y validación posterior contra los requisitos.

### 1.1. Reglas experimentales

- Todas las interacciones con Gemini se realizan en inglés.
- La implementación parte exclusivamente de E1 de Spec Kit.
- Los cambios funcionales se autorizan primero mediante especificaciones.
- Se registran resultados reales, incluidos fallos y desviaciones.
- Las conclusiones del agente requieren contraste con evidencia.
- La documentación narrativa del investigador se mantiene en esta única bitácora.

**Procedencia del contrato:** `SEED-2.md` y `E2_COMMON_FUNCTIONAL_CONTRACT.md` fueron preparados el 14 de noviembre de 2026 para las herramientas restantes. No constituyen evidencia de una semilla común utilizada históricamente por Tessl.

---

## 2. Hito 0 — Preparación del entorno

**Estado:** Completado.

Se preparó una copia independiente de la implementación E1 de Spec Kit:

- Origen: `Shift-Bank/Etapa 1/Spec Kit`
- Destino: `Shift-Bank/Etapa 2/Spec Kit`
- Evidencias: `Shift-Bank/Etapa 2/_experiment_logs/Spec Kit`

### 2.1. Integridad y reproducibilidad

| Indicador | Resultado |
|---|---|
| Archivos durables E1 | 59 |
| Coincidencias SHA-256 | 59/59 |
| Archivos inesperados o modificados en copia | 0 |
| Pruebas backend | 12 aprobadas |
| Pruebas frontend | 5 aprobadas |
| Build frontend | Correcto |
| Constitución Spec Kit | v1.2.0 |
| Commit de referencia | `130ca53c2854e042f89c8a957182c7925b176d6f` |

Se conservaron los manifiestos SHA-256 originales y los resultados de pruebas.

### 2.2. Estado bancario heredado

La implementación E1 utiliza:

- Moneda: COP.
- Checking: COP 5.000.000,00.
- Savings: COP 15.000.000,00.
- Dos transferencias históricas definidas en la semilla de código.
- Transferencias internas entre cuentas propias.
- Historial de movimientos y saldos.
- MFA simulado desde COP 1.000.000,00 inclusive.
- Código MFA `123456`.
- Vigencia de 300 segundos.
- Reintentos ilimitados durante la vigencia, sin bloqueo.

La base histórica de E1 contiene un estado mutable distinto: Checking COP 4.000.000, Savings COP 16.000.000 y cinco movimientos. Se decidió conservarla sin migrarla y utilizar la semilla reproducible del código para la ejecución E2.

### 2.3. Observaciones del entorno

- Gemini CLI instalado: 0.65.0; versión objetivo del protocolo: 0.60.0.
- Variable `GEMINI_MODEL=gemini-3.5-flash`; el enrutamiento efectivo del modelo no está verificado.
- Node 20.17.0; una dependencia frontend declara requerir Node 22 o superior.
- `npm ci` reportó 12 vulnerabilidades en dependencias.
- No se realizaron actualizaciones correctivas de dependencias durante la preparación.

Las desviaciones de versión se mantienen como observaciones experimentales.

---

## 3. Iteración 01 — Descubrimiento de E1

**Estado:** Completado.  
**Evidencia:** Transcripción de Gemini del 14 de noviembre de 2026.

### 3.1. Actividades

Gemini inspeccionó la constitución, especificación E1, contratos API, modelos, base de datos, backend, frontend, pruebas y configuración de Spec Kit.

### 3.2. Resultados

| Componente | Hallazgo |
|---|---|
| ACH | No existe; requiere beneficiarios, transferencias externas y estados |
| Recurrencia | No existe; requiere programaciones y ejecución automática |
| Límites | Solo existe umbral MFA; faltan límites configurables |
| Frontend | Requiere ampliar formularios y controles |
| Persistencia | SQLite; requiere ampliación de datos |
| MFA | Reutilizar comportamiento heredado sin introducir bloqueo |

Confirmó diez comandos nativos de Spec Kit, 12 pruebas backend y 5 frontend aprobadas y compilación satisfactoria.

### 3.3. Incidencias

1. Se ejecutaron pruebas durante una actividad solicitada como descubrimiento de solo lectura.
2. Un comando SQLite falló por problemas de comillas en PowerShell; las consultas posteriores funcionaron.
3. La base temporal E2 mostró un registro `EXPIRED` adicional respecto de la semilla limpia.
4. Existían modificaciones Git ajenas a Spec Kit en carpetas de Tetris.

No se dispone de una comparación independiente posterior que certifique ausencia absoluta de modificaciones en todos los archivos.

---

## 4. Decisiones aprobadas — D-01 a D-04

| ID | Decisión |
|---|---|
| D-01 | Límites iniciales de COP 5.000.000 por operación y COP 10.000.000 por día UTC, editables |
| D-02 | Utilizar semilla reproducible E1 sin migrar la base histórica |
| D-03 | MFA al crear pagos recurrentes desde COP 1.000.000; no cobrar al crear ni pedir MFA interactivo en ejecución automática |
| D-04 | Ejecutar automáticamente programaciones vencidas mientras el scheduler funciona |

Los límites COP son una decisión prospectiva específica de esta herramienta, sin asumir equivalencia económica con límites USD de Tessl.

---

## 5. Iteración 02 — `/speckit.specify`

**Estado:** Completado según transcripción.

### 5.1. Objetivo

Crear una especificación E2 independiente con requisitos verificables para ACH, recurrencia, límites y compatibilidad E1.

### 5.2. Artefactos generados

| Artefacto | Resultado |
|---|---|
| `specs/002-shift-bank-stage2/spec.md` | Creado, 269 líneas |
| `specs/002-shift-bank-stage2/checklists/requirements.md` | Creado, 35 líneas |
| `.specify/feature.json` | Actualizado para activar E2 |

Gemini reportó cuatro historias de usuario y una matriz de trazabilidad con las familias ACH, REC, LIM, HER y escenarios A01–A21.

### 5.3. Calidad declarada por Gemini

El checklist generado reportó:

- Calidad de contenido: PASS.
- Completitud: PASS.
- Preparación para planificación: PASS.
- Marcadores de aclaración pendientes: ninguno.

Son autoevaluaciones del agente y requieren revisión independiente.

### 5.4. Incidencias

**INC-05:** El prompt fue truncado, terminando en `Do NOT i`.

**INC-06:** Falló la llamada a `pwsh`; posteriormente funcionó `powershell`.

**INC-07:** Se generó un checklist adicional al conjunto de artefactos expresamente autorizado.

**INC-08:** La transcripción mostró fragmentos de la especificación, no una revisión independiente íntegra de sus 269 líneas.

La funcionalidad E2 quedó activa sin implementación funcional reportada.

---

## 6. Iteración 03 — `/speckit.clarify`

**Estado:** En curso.

### 6.1. Objetivo

Resolver ambigüedades materiales de la especificación mediante decisiones explícitas del investigador, conservando el contrato E1.

### 6.2. Aclaración D-05 — Persistencia de pagos recurrentes pendientes de MFA

**Pregunta:** ¿Cómo debe gestionarse una programación sensible antes de superar MFA?

Gemini propuso tres alternativas:

- A: persistir como `PENDING_MFA`, permitir reanudar y activar tras verificación.
- B: persistir únicamente después de verificar MFA.
- C: persistir inmediatamente como `ACTIVE`, pero bloqueando su ejecución.

**Decisión aprobada:** Opción A.

Se estableció que una programación sensible:

1. Se almacena inicialmente como `PENDING_MFA`.
2. Conserva código `123456`, expiración a 300 segundos y reintentos ilimitados.
3. Puede reanudarse si el usuario cierra el modal de verificación.
4. Solo pasa a `ACTIVE` tras MFA válido.
5. Pasa a `EXPIRED` cuando caduca la autorización.
6. No debita fondos al crearse ni al autorizarse.
7. Solo puede ejecutarse automáticamente cuando esté activa y vencida.

**Justificación:** esta solución conserva la semántica del MFA heredado, ofrece continuidad a la interacción del usuario y evita ejecutar pagos no autorizados.

### 6.3. Resultado observado tras D-05

Gemini aceptó la respuesta y ejecutó una modificación de:

`specs/002-shift-bank-stage2/spec.md`

La herramienta reportó:

- Escritura aceptada.
- 269 líneas anteriores reemplazadas.
- 277 líneas posteriores.
- Incorporación de la aclaración D-05 mediante el flujo nativo.

El incremento neto reportado fue de ocho líneas físicas. La transcripción muestra la operación de escritura, pero no permite verificar independientemente todas las diferencias semánticas.

No se observaron comandos de implementación, planificación o edición de código en la salida proporcionada.

### 6.4. Aclaración D-06 — Liquidación o fallo de transferencias ACH

Después de D-05, Gemini formuló una nueva pregunta:

**¿Qué mecanismo determina si una transferencia ACH pendiente termina en `settled` o `failed`, sin conectividad bancaria real?**

Presentó tres opciones:

- **A:** liquidación automática y fallos provocados por indicadores artificiales o mecanismos de pruebas.
- **B:** liquidación automática normal y fallos simulados exclusivamente mediante un mecanismo de pruebas no público.
- **C:** ambas transiciones requieren activación manual o de pruebas.

Gemini recomendó la opción A.

### 6.5. Decisión D-06 — Propuesta de aprobación

**Selección propuesta:** Opción B.

El prompt preparado establece:

- Las transferencias ACH aceptadas comienzan en `PENDING`.
- El débito inicial se realiza exactamente una vez.
- Un proceso autónomo liquida operaciones normales y registra la fecha de liquidación.
- Los fallos se inducen mediante un mecanismo exclusivo de pruebas.
- No se utilizan nombres bancarios, cuentas ni sufijos especiales como indicadores artificiales de fallo.
- Una operación fallida pasa a `FAILED` y reintegra exactamente una vez el importe debitado.
- Los estados terminales son excluyentes y sus transiciones no producen efectos duplicados.
- Los ACH fallidos y reintegrados no consumen el cupo diario efectivo.
- El mecanismo de simulación no se expone como operación bancaria ordinaria.
- No se requieren redes ACH reales ni capacidades futuras de seguridad.

**Justificación:** la opción B permite probar ambas transiciones sin contaminar las reglas normales de negocio con datos artificiales. Mantiene liquidación autónoma, reproducibilidad experimental y separación entre funcionalidades públicas y mecanismos de prueba.

**Estado:** Decisión formulada en el prompt siguiente; pendiente de comprobar recepción y actualización de especificación por Gemini.

### 6.6. Registro de aclaraciones

| ID | Tema | Decisión | Estado |
|---|---|---|---|
| D-05 | MFA y persistencia de pagos recurrentes | Opción A | Aplicada según transcripción |
| D-06 | Liquidación y fallos ACH | Opción B | Pendiente de respuesta |

---

## 7. Ajuste del protocolo de interacción

Se detectó truncamiento de un prompt de aproximadamente 4.000 caracteres útiles durante `/speckit.specify`.

A partir de esta observación:

- Los prompts deben referenciar archivos existentes en lugar de reproducir contratos íntegros.
- Su longitud se ajusta al propósito de cada interacción.
- Las decisiones de negocio pueden describirse con detalle cuando es necesario.
- Se utiliza un comando SDD principal por intervención.
- Se mantienen límites explícitos de autorización.
- No se presenta un máximo empírico de caracteres como límite oficial de Gemini CLI.

---

## 8. Estado de las dimensiones de evaluación

| Dimensión | Estado |
|---|---|
| D1 — Esfuerzo y consumo | Sesiones iniciadas; tokens, tiempo y llamadas consolidadas: N/D |
| D2 — Calidad del código | Línea base heredada; SonarQube E2 pendiente |
| D3 — Especificaciones | 269 líneas E2 inicialmente; 277 tras D-05, según escritura reportada |
| D4 — Expectativa funcional | Contratos establecidos; implementación E2 pendiente |
| D5 — Retroalimentación | Ocho incidencias registradas; D-05 aplicada y D-06 pendiente |

Los valores ausentes se mantienen como N/D hasta disponer de evidencia verificable.

---

## 9. Fuentes de evidencia

- `SEED-2.md`
- `E2_COMMON_FUNCTIONAL_CONTRACT.md`
- Constitución y especificaciones nativas de Spec Kit.
- Manifiestos SHA-256 de preparación.
- Transcripciones originales de Gemini CLI.
- Resultados originales de Pytest, Vitest y Vite.
- Checklist y especificación E2 generados.
- Respuestas humanas a las aclaraciones.

Las transcripciones y resultados originales se conservan separados de esta interpretación del investigador.

---

## 10. Estado actual

**Última decisión aplicada según transcripción:** D-05.

**Próxima decisión:** D-06, mecanismo de liquidación y fallo ACH.

**Siguiente actividad:** verificar la respuesta de Gemini a D-06 y continuar resolviendo ambigüedades materiales de la especificación.

**Planificación e implementación:** no autorizadas todavía.

# Shift Bank — Etapa 2: Spec Kit
## Bitácora acumulativa del experimento

**Fecha de inicio:** 14 de noviembre de 2026  
**Última actualización:** 14 de noviembre de 2026  
**Herramienta SDD:** GitHub Spec Kit 1.0.6  
**Agente:** Gemini CLI 0.65.0  
**Modelo configurado:** `gemini-3.5-flash`  
**Caso:** Shift Bank — Sistema bancario simulado  
**Etapa:** 2 — Complejidad funcional y estado  
**Opción:** A  
**Estado:** Aclaraciones de especificación en curso.

---

## 1. Objetivo y metodología

Evaluar la capacidad de Spec Kit para ampliar una aplicación bancaria previamente desarrollada, manteniendo la consistencia de requisitos, arquitectura, funcionalidades y estado.

La Etapa 2 incorpora:

1. Transferencias ACH simuladas a terceros.
2. Programación y ejecución automática de pagos recurrentes.
3. Límites dinámicos por operación y acumulados diarios.

### Reglas metodológicas

- Todas las interacciones con Gemini se realizan en inglés.
- Cada herramienta utiliza exclusivamente su propia implementación E1.
- Las modificaciones funcionales deben surgir de especificaciones aprobadas.
- Se conservan los resultados, errores, correcciones y decisiones.
- No se utilizan soluciones de otras herramientas como plantillas.
- Las métricas reportadas deben sustentarse en evidencia real.
- La documentación del investigador se consolida en esta bitácora.

**Procedencia:** `SEED-2.md` y `E2_COMMON_FUNCTIONAL_CONTRACT.md` fueron preparados el 14 de noviembre de 2026 para las ejecuciones restantes. No constituyen evidencia de una semilla históricamente compartida con Tessl.

---

## 2. Hito 0 — Preparación

**Estado:** Completado.

Se preparó una copia independiente de E1:

- Origen: `Shift-Bank/Etapa 1/Spec Kit`
- Destino: `Shift-Bank/Etapa 2/Spec Kit`
- Evidencia: `Shift-Bank/Etapa 2/_experiment_logs/Spec Kit`

### Integridad y entorno

| Indicador | Resultado |
|---|---|
| Archivos durables heredados | 59 |
| Comparación SHA-256 | 59/59 |
| Pruebas backend | 12/12 |
| Pruebas frontend | 5/5 |
| Build frontend | Exitoso |
| Spec Kit | 1.0.6 |
| Constitución | 1.2.0 |
| Gemini CLI | 0.65.0 |
| Commit de referencia | `130ca53c2854e042f89c8a957182c7925b176d6f` |

### Contratos E1

- Moneda: COP.
- Checking: COP 5.000.000.
- Savings: COP 15.000.000.
- Dos transferencias históricas definidas en código.
- Transferencias entre cuentas propias.
- Consulta de saldos e historial.
- MFA para montos >= COP 1.000.000.
- Código MFA: `123456`.
- Vigencia: 300 segundos.
- Reintentos ilimitados durante la vigencia, sin bloqueo.

Se preservó la base histórica de E1, cuyos saldos y movimientos difieren de la semilla reproducible. No se autorizó su migración.

### Desviaciones ambientales

- CLI 0.65.0 frente al objetivo 0.60.0.
- Variable `GEMINI_MODEL=gemini-3.5-flash`, sin verificación del modelo efectivo.
- Node 20.17.0 frente a dependencias que solicitan Node 22.
- Doce vulnerabilidades reportadas durante instalación de dependencias.

No se realizaron actualizaciones correctivas.

---

## 3. Iteración 01 — Descubrimiento

**Estado:** Completado.

Gemini inspeccionó la constitución, especificaciones E1, contratos API, backend, frontend, pruebas y configuración de Spec Kit.

### Resultados

| Dimensión | Resultado |
|---|---|
| ACH | Requiere beneficiarios, transferencias externas y estados |
| Recurrencia | Requiere programaciones y automatización |
| Límites | Requiere máximos configurables y acumulación diaria |
| Frontend | Ampliación de formularios y controles |
| Persistencia | Ampliación de SQLite |
| MFA | Conservación del comportamiento heredado |

Se confirmaron diez comandos nativos de Spec Kit y las pruebas heredadas.

### Incidencias

**INC-01:** Gemini ejecutó pruebas durante descubrimiento solicitado como solo lectura.

**INC-02:** Falló un comando SQLite por problemas de interpretación de comillas en PowerShell.

**INC-03:** La base temporal E2 contenía una transferencia `EXPIRED` adicional frente a la semilla limpia.

**INC-04:** Existían modificaciones Git ajenas a Spec Kit en otras carpetas del repositorio.

La ejecución terminó con una matriz de compatibilidad y preguntas pendientes.

---

## 4. Decisiones iniciales D-01 a D-04

Se aprobaron mediante el prompt de `/speckit.specify`.

| ID | Decisión |
|---|---|
| D-01 | Límites iniciales de COP 5.000.000 por operación y COP 10.000.000 diarios, editables |
| D-02 | Usar la semilla E1 reproducible sin migrar la base histórica |
| D-03 | Exigir MFA al crear programaciones desde COP 1.000.000 y no solicitar MFA interactivo en cada ejecución |
| D-04 | Procesar automáticamente los pagos vencidos mientras el scheduler funciona |

Los límites COP son específicos de esta ejecución; no se consideran equivalentes económicamente a los valores USD de Tessl.

---

## 5. Iteración 02 — `/speckit.specify`

**Estado:** Completado según transcripción.

### Objetivo

Crear una especificación E2 independiente con obligaciones verificables de ACH, recurrencia, límites dinámicos y compatibilidad E1.

### Artefactos

| Archivo | Resultado |
|---|---|
| `specs/002-shift-bank-stage2/spec.md` | 269 líneas iniciales |
| `specs/002-shift-bank-stage2/checklists/requirements.md` | 35 líneas |
| `.specify/feature.json` | Referencia actualizada a E2 |

Gemini reportó cuatro historias de usuario y trazabilidad con ACH-01..10, REC-01..12, LIM-01..09, HER-01..06 y A01..A21.

El checklist generado declaró satisfechos los criterios de calidad, completitud y preparación. Estos resultados constituyen autoevaluación del agente.

### Incidencias

**INC-05:** El prompt original fue truncado, terminando en `Do NOT i`.

**INC-06:** Falló `pwsh`; posteriormente funcionó `powershell`.

**INC-07:** Se generó un checklist adicional al alcance literal autorizado.

**INC-08:** La transcripción no mostró una revisión independiente completa de las 269 líneas.

No se reportaron modificaciones funcionales de código.

---

## 6. Iteración 03 — `/speckit.clarify`

**Estado:** En curso.

### Objetivo

Resolver ambigüedades materiales mediante decisiones aprobadas por el investigador, conservando los requisitos heredados.

### 6.1. Decisión D-05 — MFA en programaciones recurrentes

**Pregunta:** ¿Debe persistirse una programación sensible antes de verificar MFA?

Alternativas presentadas:

- A: persistir `PENDING_MFA` y permitir reanudación.
- B: guardar únicamente después de verificar MFA.
- C: guardar inmediatamente como `ACTIVE` con bloqueo de autorización.

**Decisión aprobada:** A.

Contrato:

- La solicitud sensible comienza en `PENDING_MFA`.
- Mantiene el código `123456`, duración de 300 segundos y reintentos ilimitados.
- Cerrar el modal permite reanudar la verificación.
- MFA exitoso transforma la programación en `ACTIVE`.
- MFA vencido transforma la solicitud en `EXPIRED`.
- No se debitan fondos durante creación o autorización.
- Solo las programaciones `ACTIVE` son elegibles para ejecución automática.

**Justificación:** mantener coherencia con el ciclo MFA de E1 sin ejecutar pagos no autorizados.

**Resultado observado:** Gemini modificó `spec.md`, reportando reemplazo de 269 por 277 líneas.

### 6.2. Decisión D-06 — Liquidación y fallos ACH

**Pregunta:** ¿Cómo determinar si un ACH pendiente termina en `settled` o `failed` en ausencia de una red bancaria real?

Alternativas:

- A: liquidación autónoma con fallos mediante indicadores artificiales o mecanismos de prueba.
- B: liquidación autónoma y fallos simulados exclusivamente mediante un mecanismo de prueba no público.
- C: ambas transiciones por invocación explícita.

**Decisión aprobada:** B.

Contrato:

1. Todo ACH autorizado comienza `PENDING` con débito único.
2. Un proceso autónomo liquida operaciones elegibles.
3. Se registra la fecha de liquidación sin débito adicional.
4. Los fallos se simulan mediante un mecanismo exclusivo de pruebas.
5. No se utilizan nombres, rutas bancarias ni sufijos artificiales como señales de fallo.
6. Un ACH fallido reintegra exactamente una vez el dinero debitado.
7. `SETTLED` y `FAILED` son estados terminales mutuamente excluyentes.
8. El procesamiento repetido no puede producir efectos financieros duplicados.
9. Los ACH fallidos y reintegrados se excluyen del consumo diario.
10. El mecanismo de pruebas no se expone como operación bancaria ordinaria.

**Justificación:** separa las reglas bancarias simuladas de la instrumentación experimental y permite pruebas deterministas.

**Resultado observado:** Gemini aceptó la respuesta y ejecutó una escritura de `spec.md`, reemplazando 277 por 279 líneas.

La transcripción confirma la escritura y posterior continuación del flujo, aunque no proporciona una comparación independiente completa de su contenido.

### 6.3. Decisión D-07 — Reducción de límite diario por debajo del consumo

**Pregunta de Gemini:** ¿Debe permitirse establecer un límite diario menor que el consumo ya registrado durante el día UTC?

Alternativas:

- A: aceptar inmediatamente el nuevo límite y dejar disponible diario en cero.
- B: rechazar reducciones inferiores al consumo registrado.
- C: aceptar la actualización, pero diferir su aplicación al siguiente día UTC.

Gemini recomienda la opción A.

**Selección propuesta en el siguiente prompt:** A.

Contrato preparado:

1. El usuario puede reducir el límite diario por debajo del consumo acumulado.
2. El cambio entra en vigor inmediatamente.
3. Las transacciones históricas no se revierten ni modifican.
4. La disponibilidad se calcula como `max(0, límite_diario - consumo_elegible)`.
5. No se autorizan nuevas transferencias mientras no exista disponibilidad suficiente.
6. Los pagos recurrentes siguen las mismas restricciones cuando se ejecutan.
7. Los ACH fallidos y reintegrados dejan de consumir el cupo diario.
8. Un aumento posterior del límite aplica inmediatamente.
9. El límite configurado persiste después del reinicio diario del consumo.
10. La interfaz muestra límite, consumo y disponibilidad por separado.

**Justificación:** permitir una reducción inmediata ofrece control al usuario sin modificar ni revertir operaciones ya ejecutadas y mantiene una interpretación consistente de los límites.

**Estado:** Decisión formulada en el siguiente prompt. Su recepción y aplicación todavía no están verificadas.

### 6.4. Registro acumulado de aclaraciones

| ID | Tema | Decisión | Evidencia |
|---|---|---|---|
| D-05 | MFA y persistencia recurrente | A | Escritura `spec.md` 269 → 277 |
| D-06 | Liquidación y fallos ACH | B | Escritura `spec.md` 277 → 279 |
| D-07 | Reducción de límites diarios | A propuesta | Pendiente |

---

## 7. Control de prompts

Se detectó truncamiento del prompt de `/speckit.specify`.

La longitud se ajustará de forma empírica según la respuesta observada, procurando aprovechar las especificaciones persistentes y evitar repetir contratos extensos.

No se afirma que Gemini CLI tenga un límite oficial de 4.096 caracteres. La medida corresponde únicamente a una precaución operativa del experimento.

Cada intervención conserva un alcance explícito y requiere autorización para adoptar nuevas decisiones funcionales.

---

## 8. Estado de las dimensiones experimentales

| Dimensión | Estado |
|---|---|
| D1 — Esfuerzo y consumo | Transcripciones disponibles; consolidación pendiente |
| D2 — Calidad del código | Pruebas heredadas aprobadas; SonarQube E2 pendiente |
| D3 — Especificaciones | 269 líneas iniciales, 277 tras D-05 y 279 tras D-06, según escrituras reportadas |
| D4 — Expectativa funcional | Requisitos definidos; implementación E2 pendiente |
| D5 — Retroalimentación | Ocho incidencias registradas; dos decisiones de aclaración aplicadas según transcripción |

No se calculan métricas sin evidencia suficiente.

---

## 9. Evidencias y trazabilidad

Fuentes conservadas:

- `SEED-2.md`
- `E2_COMMON_FUNCTIONAL_CONTRACT.md`
- `.specify/memory/constitution.md`
- `specs/001-shift-bank-stage1/`
- `specs/002-shift-bank-stage2/`
- Manifiestos SHA-256 de preparación.
- Transcripciones originales de Gemini CLI.
- Resultados originales de Pytest, Vitest y Vite.
- Respuestas aprobadas del investigador.

La bitácora documenta los hechos observados y decisiones, pero no sustituye las evidencias originales.

---

## 10. Estado y continuidad

**Última decisión aplicada según transcripción:** D-06.

**Próxima decisión propuesta:** D-07, actualización de límite diario por debajo del consumo acumulado.

**Próximo paso:** confirmar que Gemini registre D-07, verificar sus cambios y continuar las aclaraciones materiales restantes.

**Planificación e implementación:** todavía no autorizadas.

# Shift Bank — Etapa 2: Spec Kit
## Bitácora acumulativa del experimento

**Fecha de inicio:** 14 de noviembre de 2026  
**Última actualización:** 14 de noviembre de 2026  
**Herramienta SDD:** GitHub Spec Kit 1.0.6  
**Agente:** Gemini CLI 0.65.0  
**Modelo configurado:** `gemini-3.5-flash`  
**Caso:** Shift Bank  
**Etapa:** 2 — Complejidad funcional y estado  
**Opción:** A  
**Estado:** Aclaraciones de especificación en curso.

---

## 1. Objetivo y metodología

Evaluar la capacidad de Spec Kit para ampliar una aplicación bancaria desarrollada previamente, manteniendo la consistencia funcional y la trazabilidad entre especificación, implementación y validación.

### Alcance funcional

1. Transferencias ACH simuladas a terceros.
2. Programación y ejecución automática de pagos recurrentes.
3. Límites dinámicos por operación y acumulados diarios.

### Reglas metodológicas

- Todas las interacciones con Gemini se realizan en inglés.
- Cada herramienta utiliza exclusivamente su propia implementación E1.
- Los cambios funcionales deben surgir de especificaciones aprobadas.
- Se conservan resultados, errores, correcciones y decisiones.
- No se utilizan soluciones de otras herramientas como plantillas.
- Las métricas se sustentan en evidencia real.
- La documentación del investigador se consolida en esta bitácora.

**Procedencia:** `SEED-2.md` y `E2_COMMON_FUNCTIONAL_CONTRACT.md` fueron preparados el 14 de noviembre de 2026 para las ejecuciones restantes. No constituyen evidencia de una semilla históricamente compartida con Tessl.

---

## 2. Hito 0 — Preparación

**Estado:** Completado.

Se creó una copia independiente de E1:

- Origen: `Shift-Bank/Etapa 1/Spec Kit`
- Destino: `Shift-Bank/Etapa 2/Spec Kit`
- Evidencia: `Shift-Bank/Etapa 2/_experiment_logs/Spec Kit`

### Integridad y entorno

| Indicador | Resultado |
|---|---|
| Archivos durables heredados | 59 |
| Comparación SHA-256 | 59/59 |
| Pruebas backend | 12/12 |
| Pruebas frontend | 5/5 |
| Build frontend | Exitoso |
| Spec Kit | 1.0.6 |
| Constitución | 1.2.0 |
| Gemini CLI | 0.65.0 |
| Commit de referencia | `130ca53c2854e042f89c8a957182c7925b176d6f` |

### Contratos E1

- Moneda: COP.
- Checking: COP 5.000.000.
- Savings: COP 15.000.000.
- Dos transferencias históricas definidas en código.
- Transferencias entre cuentas propias.
- Consulta de saldos e historial.
- MFA para montos >= COP 1.000.000.
- Código MFA: `123456`.
- Vigencia: 300 segundos.
- Reintentos ilimitados durante la vigencia, sin bloqueo.

Se preservó la base histórica de E1, cuyos saldos y movimientos difieren de la semilla reproducible. No se autorizó su migración.

### Desviaciones ambientales

- Gemini CLI 0.65.0 frente al objetivo 0.60.0.
- Variable `GEMINI_MODEL=gemini-3.5-flash`, sin verificación del modelo efectivo.
- Node 20.17.0 frente a dependencias que solicitan Node 22.
- Doce vulnerabilidades reportadas durante instalación de dependencias.

No se realizaron actualizaciones correctivas.

---

## 3. Iteración 01 — Descubrimiento

**Estado:** Completado.

Gemini inspeccionó la constitución, especificaciones E1, contratos API, backend, frontend, pruebas y configuración de Spec Kit.

### Resultados

| Dimensión | Resultado |
|---|---|
| ACH | Requiere beneficiarios, transferencias externas y estados |
| Recurrencia | Requiere programaciones y automatización |
| Límites | Requiere máximos configurables y acumulación diaria |
| Frontend | Ampliación de formularios y controles |
| Persistencia | Ampliación de SQLite |
| MFA | Conservación del comportamiento heredado |

Se confirmaron diez comandos nativos de Spec Kit y las pruebas heredadas.

### Incidencias

**INC-01:** Gemini ejecutó pruebas durante un descubrimiento solicitado como solo lectura.

**INC-02:** Falló un comando SQLite por interpretación de comillas en PowerShell.

**INC-03:** La base temporal E2 contenía una transferencia `EXPIRED` adicional frente a la semilla limpia.

**INC-04:** Existían modificaciones Git ajenas a Spec Kit en otras carpetas del repositorio.

---

## 4. Decisiones iniciales D-01 a D-04

Aprobadas mediante el prompt de `/speckit.specify`.

| ID | Decisión |
|---|---|
| D-01 | Límites iniciales de COP 5.000.000 por operación y COP 10.000.000 diarios, editables |
| D-02 | Usar la semilla E1 reproducible sin migrar la base histórica |
| D-03 | Exigir MFA al crear programaciones desde COP 1.000.000 y no solicitar MFA interactivo en cada ejecución |
| D-04 | Procesar automáticamente los pagos vencidos mientras el scheduler funciona |

Los límites COP son específicos de esta ejecución y no se consideran económicamente equivalentes a los valores USD de Tessl.

---

## 5. Iteración 02 — `/speckit.specify`

**Estado:** Completado según transcripción.

### Objetivo

Crear una especificación E2 independiente con requisitos verificables para ACH, recurrencia, límites dinámicos y compatibilidad E1.

### Artefactos

| Archivo | Resultado |
|---|---|
| `specs/002-shift-bank-stage2/spec.md` | 269 líneas iniciales |
| `specs/002-shift-bank-stage2/checklists/requirements.md` | 35 líneas |
| `.specify/feature.json` | Referencia actualizada a E2 |

Gemini reportó cuatro historias de usuario y trazabilidad con ACH-01..10, REC-01..12, LIM-01..09, HER-01..06 y A01..A21.

El checklist generado declaró satisfechos los criterios de calidad, completitud y preparación. Estos resultados constituyen autoevaluación del agente.

### Incidencias

**INC-05:** El prompt original fue truncado, terminando en `Do NOT i`.

**INC-06:** Falló `pwsh`; posteriormente funcionó `powershell`.

**INC-07:** Se generó un checklist adicional al alcance literal autorizado.

**INC-08:** La transcripción no mostró una revisión independiente completa de las 269 líneas.

No se reportaron modificaciones funcionales de código.

---

## 6. Iteración 03 — `/speckit.clarify`

**Estado:** En curso.

### 6.1. Objetivo

Resolver ambigüedades materiales mediante decisiones aprobadas por el investigador, conservando los requisitos heredados.

### 6.2. D-05 — MFA en programaciones recurrentes

**Pregunta:** ¿Debe persistirse una programación sensible antes de completar MFA?

Gemini presentó tres opciones:

- A: persistir `PENDING_MFA` y permitir reanudación.
- B: persistir únicamente después de verificar MFA.
- C: persistir inmediatamente como `ACTIVE` con bloqueo de autorización.

**Decisión aprobada:** A.

Se estableció que:

1. La solicitud comienza en `PENDING_MFA`.
2. Conserva código `123456`, vigencia de 300 segundos y reintentos ilimitados.
3. Cerrar el modal permite reanudar la verificación.
4. MFA exitoso transforma la programación en `ACTIVE`.
5. MFA vencido transforma la solicitud en `EXPIRED`.
6. No se debitan fondos durante creación o autorización.
7. Solo las programaciones `ACTIVE` pueden ejecutarse automáticamente.

**Resultado observado:** Gemini modificó `spec.md`, reportando reemplazo de 269 por 277 líneas.

**Justificación:** preservar el comportamiento MFA heredado sin permitir pagos automáticos no autorizados.

### 6.3. D-06 — Liquidación y fallos ACH

**Pregunta:** ¿Cómo determinar si un ACH pendiente termina en `settled` o `failed` sin una red bancaria real?

Opciones:

- A: liquidación autónoma con fallos mediante indicadores artificiales o mecanismos de prueba.
- B: liquidación autónoma y fallos simulados exclusivamente mediante un mecanismo no público.
- C: ambas transiciones por invocación explícita.

**Decisión aprobada:** B.

Contrato:

1. Todo ACH autorizado comienza `PENDING` con débito único.
2. Un proceso autónomo liquida operaciones elegibles.
3. Se registra la fecha de liquidación sin débito adicional.
4. Los fallos se simulan mediante un mecanismo exclusivo de pruebas.
5. No se utilizan nombres, rutas bancarias ni sufijos artificiales para provocar fallos.
6. Un ACH fallido reintegra exactamente una vez el dinero debitado.
7. `SETTLED` y `FAILED` son estados terminales mutuamente excluyentes.
8. El procesamiento repetido no puede producir efectos financieros duplicados.
9. Los ACH fallidos y reintegrados se excluyen del consumo diario.
10. El mecanismo de pruebas no se expone como operación bancaria ordinaria.

**Resultado observado:** Gemini modificó `spec.md`, pasando de 277 a 279 líneas.

**Justificación:** separar las reglas bancarias simuladas de la instrumentación experimental y permitir pruebas deterministas.

### 6.4. D-07 — Reducción del límite diario por debajo del consumo

**Pregunta:** ¿Debe permitirse configurar un límite diario inferior al consumo registrado durante el día UTC?

Opciones:

- A: aceptar inmediatamente la reducción, dejando disponibilidad cero.
- B: rechazar reducciones inferiores al consumo.
- C: aceptar la actualización y diferir su aplicación al día siguiente.

**Decisión aprobada:** A.

Se estableció:

1. El usuario puede reducir el límite diario por debajo del consumo acumulado.
2. La modificación entra en vigor inmediatamente.
3. Las transacciones anteriores no se revierten, eliminan ni modifican.
4. La disponibilidad se calcula como `max(0, límite_diario - consumo_elegible)`.
5. Se rechazan nuevas transferencias que excedan la disponibilidad.
6. Los pagos recurrentes utilizan los límites vigentes al ejecutarse.
7. Los ACH fallidos y reintegrados dejan de consumir cupo diario.
8. Un aumento posterior del límite tiene efecto inmediato.
9. El límite configurado permanece vigente después del cambio de día UTC.
10. La interfaz distingue límite, consumo y disponibilidad.

**Resultado observado:** Gemini aceptó la decisión y realizó una escritura de `spec.md`, reemplazando 279 por 283 líneas.

La transcripción muestra la operación aceptada, aunque no proporciona un diff independiente completo de todas las modificaciones semánticas.

**Justificación:** permitir al cliente disminuir inmediatamente su exposición futura sin modificar operaciones autorizadas previamente.

### 6.5. D-08 — Gestión y eliminación de beneficiarios

**Pregunta de Gemini:** ¿Qué operaciones deben permitirse sobre los beneficiarios guardados y qué ocurre con los movimientos históricos o programaciones recurrentes cuando uno es eliminado?

Opciones:

- A: Crear, listar y eliminar; beneficiarios inmutables y preservación de históricos y programaciones mediante snapshots.
- B: Crear, listar, editar y eliminar; la edición afecta a las programaciones futuras asociadas.
- C: Crear y listar, sin posibilidad de eliminación.

Gemini recomienda la opción A.

**Selección propuesta:** A.

Contrato preparado:

1. Permitir crear, consultar y eliminar beneficiarios.
2. Conservar validación de nombre, banco, routing de nueve dígitos y cuenta de 4–17 dígitos.
3. Los beneficiarios pertenecen exclusivamente al usuario simulado.
4. No permitir editar directamente los datos bancarios de un beneficiario.
5. Los cambios requieren eliminar el registro y crear uno nuevo.
6. La eliminación impide seleccionar ese beneficiario para nuevas operaciones.
7. Las transferencias históricas conservan sus datos originales.
8. Las programaciones recurrentes conservan una copia independiente de los datos del destinatario.
9. La eliminación no cancela ni modifica las programaciones existentes.
10. Las ejecuciones posteriores siguen sujetas a saldos, límites y estados aprobados.
11. La eliminación no altera saldos ni genera operaciones financieras.

**Justificación:** esta alternativa mantiene la integridad del historial financiero, evita cambios retroactivos de destinatario y reduce la complejidad funcional sin impedir administrar beneficiarios.

**Estado:** Decisión formulada en el siguiente prompt; aplicación aún no verificada.

### 6.6. Registro acumulado de aclaraciones

| ID | Tema | Decisión | Evidencia |
|---|---|---|---|
| D-05 | MFA y persistencia recurrente | A | `spec.md` 269 → 277 |
| D-06 | Liquidación y fallos ACH | B | `spec.md` 277 → 279 |
| D-07 | Reducción de límites diarios | A | `spec.md` 279 → 283 |
| D-08 | Gestión de beneficiarios | A propuesta | Pendiente |

---

## 7. Control de prompts

Durante `/speckit.specify` se detectó truncamiento de entrada. Desde entonces se emplean instrucciones que aprovechan archivos persistentes y evitan repetir contratos extensos.

La longitud se ajusta según los resultados empíricos observados, conservando suficiente detalle para registrar las decisiones y sus consecuencias.

No se presenta un límite de caracteres empírico como máximo oficial de Gemini CLI.

Cada intervención mantiene un alcance explícito y exige aprobación humana para nuevas decisiones funcionales.

---

## 8. Dimensiones experimentales

| Dimensión | Estado |
|---|---|
| D1 — Esfuerzo y consumo | Transcripciones disponibles; consolidación de tokens, tiempo e interacciones pendiente |
| D2 — Calidad del código | Pruebas heredadas aprobadas; SonarQube E2 pendiente |
| D3 — Especificaciones | 269 líneas iniciales, 277 tras D-05, 279 tras D-06 y 283 tras D-07, según escrituras reportadas |
| D4 — Expectativa funcional | Contratos definidos; implementación E2 pendiente |
| D5 — Retroalimentación | Ocho incidencias registradas; tres decisiones de aclaración aplicadas según transcripción |

No se calculan métricas ausentes sin evidencia.

---

## 9. Evidencias

Fuentes del experimento:

- `SEED-2.md`.
- `E2_COMMON_FUNCTIONAL_CONTRACT.md`.
- `.specify/memory/constitution.md`.
- `specs/001-shift-bank-stage1/`.
- `specs/002-shift-bank-stage2/`.
- Manifiestos SHA-256 de preparación.
- Transcripciones originales de Gemini CLI.
- Resultados originales de Pytest, Vitest y Vite.
- Checklist y especificación E2 generados.
- Respuestas aprobadas del investigador.

Esta bitácora documenta decisiones y observaciones, pero no sustituye las evidencias originales.

---

## 10. Estado actual

**Última decisión aplicada según transcripción:** D-07.

**Siguiente decisión propuesta:** D-08, gestión y eliminación de beneficiarios.

**Próximo paso:** verificar que Gemini registre D-08 y continuar con las aclaraciones materiales restantes.

**Planificación e implementación:** todavía no autorizadas.

# Shift Bank — Etapa 2: Spec Kit
## Bitácora acumulativa del experimento

**Fecha de inicio:** 14 de noviembre de 2026  
**Última actualización:** 14 de noviembre de 2026  
**Herramienta SDD:** GitHub Spec Kit 1.0.6  
**Agente:** Gemini CLI 0.65.0  
**Modelo configurado:** `gemini-3.5-flash`  
**Caso:** Shift Bank  
**Etapa:** 2 — Complejidad funcional y estado  
**Opción:** A  
**Estado:** Aclaraciones de especificación en curso.

---

## 1. Objetivo y metodología

Evaluar la capacidad de Spec Kit para ampliar una aplicación bancaria desarrollada previamente, conservando su funcionamiento y la trazabilidad entre requisitos, especificaciones, implementación y validación.

### Alcance funcional

1. Transferencias ACH simuladas a terceros.
2. Programación y ejecución automática de pagos recurrentes.
3. Límites dinámicos por operación y acumulados diarios.

### Reglas metodológicas

- Las interacciones con Gemini se realizan en inglés.
- Cada herramienta utiliza exclusivamente su implementación de E1.
- Los cambios funcionales deben derivarse de especificaciones aprobadas.
- Se conservan resultados, errores, correcciones, decisiones y evidencias.
- No se reutilizan soluciones de otras herramientas.
- Las métricas requieren respaldo experimental.
- La documentación interpretativa del investigador se consolida en esta bitácora.

**Procedencia:** `SEED-2.md` y `E2_COMMON_FUNCTIONAL_CONTRACT.md` fueron preparados el 14 de noviembre de 2026 para las ejecuciones restantes. No constituyen evidencia de una semilla utilizada históricamente por Tessl.

---

## 2. Hito 0 — Preparación

**Estado:** Completado.

Se creó una copia independiente de E1:

- Origen: `Shift-Bank/Etapa 1/Spec Kit`
- Destino: `Shift-Bank/Etapa 2/Spec Kit`
- Evidencias: `Shift-Bank/Etapa 2/_experiment_logs/Spec Kit`

### Integridad y entorno

| Indicador | Resultado |
|---|---|
| Archivos durables heredados | 59 |
| Comparación SHA-256 | 59/59 |
| Pruebas backend | 12/12 |
| Pruebas frontend | 5/5 |
| Build frontend | Exitoso |
| Spec Kit | 1.0.6 |
| Constitución | 1.2.0 |
| Gemini CLI | 0.65.0 |
| Commit de referencia | `130ca53c2854e042f89c8a957182c7925b176d6f` |

### Contratos E1

- Moneda: COP.
- Checking: COP 5.000.000.
- Savings: COP 15.000.000.
- Dos movimientos históricos definidos en código.
- Transferencias entre cuentas propias.
- Consulta de saldos e historial.
- MFA para montos mayores o iguales a COP 1.000.000.
- Código MFA: `123456`.
- Vigencia: 300 segundos.
- Reintentos ilimitados durante la vigencia, sin bloqueo.

La base de datos histórica de E1 contiene saldos y movimientos diferentes de la semilla reproducible. Se preserva sin migración.

### Desviaciones ambientales

- Gemini CLI 0.65.0 frente a versión objetivo 0.60.0.
- Variable `GEMINI_MODEL=gemini-3.5-flash`, sin verificación independiente del modelo efectivo.
- Node 20.17.0 frente a dependencias que solicitan Node 22.
- Doce vulnerabilidades reportadas durante la instalación de dependencias.

No se realizaron actualizaciones correctivas durante la preparación.

---

## 3. Iteración 01 — Descubrimiento

**Estado:** Completado.

Gemini inspeccionó constitución, especificaciones E1, contratos API, backend, frontend, pruebas y configuración de Spec Kit.

### Resultados

| Dimensión | Hallazgo |
|---|---|
| ACH | Requiere beneficiarios, transferencias externas y estados |
| Recurrencia | Requiere programaciones y automatización |
| Límites | Requiere máximos configurables y acumulación diaria |
| Frontend | Ampliación de formularios y controles |
| Persistencia | Ampliación de SQLite |
| MFA | Conservación del comportamiento heredado |

Se confirmaron diez comandos nativos de Spec Kit y la ejecución exitosa de las pruebas heredadas.

### Incidencias

**INC-01:** Gemini ejecutó pruebas durante descubrimiento solicitado como solo lectura.

**INC-02:** Falló un comando SQLite por interpretación de comillas en PowerShell.

**INC-03:** La base temporal E2 contenía una transferencia `EXPIRED` adicional respecto de la semilla limpia.

**INC-04:** Existían modificaciones Git ajenas a Spec Kit en otras carpetas del repositorio.

---

## 4. Decisiones iniciales D-01 a D-04

Aprobadas mediante el prompt de `/speckit.specify`.

| ID | Decisión |
|---|---|
| D-01 | Límites iniciales de COP 5.000.000 por operación y COP 10.000.000 diarios, editables |
| D-02 | Usar semilla E1 reproducible sin migrar la base histórica |
| D-03 | MFA al crear programaciones desde COP 1.000.000; no pedir MFA interactivo en ejecuciones automáticas |
| D-04 | Procesar automáticamente los pagos vencidos mientras el scheduler funciona |

Los límites COP son específicos de esta ejecución y no implican equivalencia económica con los límites USD de Tessl.

---

## 5. Iteración 02 — `/speckit.specify`

**Estado:** Completado según transcripción.

### Objetivo

Crear una especificación E2 independiente con requisitos verificables para ACH, recurrencia, límites dinámicos y compatibilidad E1.

### Artefactos

| Archivo | Resultado |
|---|---|
| `specs/002-shift-bank-stage2/spec.md` | 269 líneas iniciales |
| `specs/002-shift-bank-stage2/checklists/requirements.md` | 35 líneas |
| `.specify/feature.json` | Referencia actualizada a E2 |

Gemini reportó cuatro historias de usuario y trazabilidad con ACH-01..10, REC-01..12, LIM-01..09, HER-01..06 y A01..A21.

El checklist declaró satisfechos los criterios de calidad, completitud y preparación. Estos resultados corresponden a la autoevaluación del agente.

### Incidencias

**INC-05:** El prompt original fue truncado, terminando en `Do NOT i`.

**INC-06:** Falló `pwsh`; posteriormente funcionó `powershell`.

**INC-07:** Se generó un checklist adicional al alcance literal autorizado.

**INC-08:** La transcripción no mostró una revisión independiente completa de las 269 líneas.

No se reportaron modificaciones funcionales de código.

---

## 6. Iteración 03 — `/speckit.clarify`

**Estado:** En curso.

### 6.1. Objetivo

Resolver ambigüedades materiales de la especificación mediante decisiones expresas del investigador, conservando los contratos heredados.

### 6.2. D-05 — MFA en programaciones recurrentes

**Pregunta:** ¿Debe persistirse una programación sensible antes de completar MFA?

Opciones:

- A: persistir `PENDING_MFA` y permitir reanudación.
- B: persistir únicamente después de verificar MFA.
- C: persistir inmediatamente como `ACTIVE` con bloqueo.

**Decisión aprobada:** A.

Comportamiento aprobado:

1. La solicitud sensible comienza en `PENDING_MFA`.
2. Conserva código `123456`, vigencia de 300 segundos y reintentos ilimitados.
3. Cerrar el modal permite reanudar la verificación.
4. MFA exitoso transforma la programación en `ACTIVE`.
5. MFA vencido transforma la solicitud en `EXPIRED`.
6. No se debitan fondos durante creación o autorización.
7. Solo las programaciones `ACTIVE` pueden ejecutarse automáticamente.

**Resultado:** Gemini escribió `spec.md`, pasando de 269 a 277 líneas.

**Justificación:** conservar la semántica MFA de E1 y prevenir pagos automáticos no autorizados.

### 6.3. D-06 — Liquidación y fallos ACH

**Pregunta:** ¿Cómo determinar si un ACH pendiente termina en `settled` o `failed` sin una red bancaria real?

Opciones:

- A: liquidación automática con indicadores artificiales o mecanismos de prueba.
- B: liquidación automática y fallos mediante mecanismo exclusivo de pruebas.
- C: ambas transiciones por invocación explícita.

**Decisión aprobada:** B.

Comportamiento:

1. El ACH autorizado comienza en `PENDING` y debita una sola vez.
2. Un proceso autónomo liquida las operaciones elegibles.
3. La liquidación registra su fecha sin nuevo débito.
4. El fallo se simula por un mecanismo de pruebas no público.
5. No se utilizan nombres o sufijos especiales de beneficiarios como indicadores de fallo.
6. Un ACH fallido reintegra exactamente una vez el importe.
7. `SETTLED` y `FAILED` son terminales y mutuamente excluyentes.
8. El reprocesamiento no duplica efectos financieros.
9. Los ACH fallidos y reintegrados no consumen el cupo diario.

**Resultado:** Gemini escribió `spec.md`, pasando de 277 a 279 líneas.

**Justificación:** separar el funcionamiento bancario simulado de los mecanismos de validación experimental.

### 6.4. D-07 — Reducción del límite diario por debajo del consumo

**Pregunta:** ¿Se permite establecer un límite diario inferior al consumo registrado durante el día UTC?

Opciones:

- A: aceptar inmediatamente y dejar disponibilidad cero.
- B: rechazar reducciones inferiores al consumo.
- C: diferir el cambio al siguiente día.

**Decisión aprobada:** A.

Comportamiento:

1. El usuario puede reducir el límite por debajo del consumo registrado.
2. El cambio entra en vigor inmediatamente.
3. Las operaciones históricas no se revierten ni modifican.
4. La disponibilidad es `max(0, límite_diario - consumo_elegible)`.
5. Se rechazan nuevas transferencias que excedan la disponibilidad.
6. Los pagos recurrentes están sujetos a los límites vigentes al ejecutarse.
7. Los ACH fallidos y reintegrados dejan de consumir cupo.
8. Los aumentos posteriores también tienen efecto inmediato.
9. El límite configurado persiste tras el cambio de día UTC.
10. La interfaz separa límite, consumo y disponibilidad.

**Resultado:** Gemini escribió `spec.md`, pasando de 279 a 283 líneas.

**Justificación:** permitir disminuir la exposición futura sin modificar operaciones ya autorizadas.

### 6.5. D-08 — Gestión y eliminación de beneficiarios

**Pregunta:** ¿Qué operaciones se permiten sobre los beneficiarios guardados y qué ocurre con las transacciones y programaciones existentes al eliminarlos?

Opciones:

- A: Crear, listar y eliminar; datos inmutables y preservación de históricos mediante snapshots.
- B: Crear, listar, editar y eliminar; las ediciones afectan programaciones futuras.
- C: Crear y listar, sin eliminación.

**Decisión aprobada:** A.

Comportamiento:

1. Permitir crear, listar y eliminar beneficiarios.
2. Conservar validaciones de nombre, banco, routing de nueve dígitos y cuenta de 4–17 dígitos.
3. Los beneficiarios pertenecen exclusivamente al usuario simulado correspondiente.
4. Los detalles bancarios no pueden editarse directamente.
5. Cambiarlos requiere eliminar y crear otro beneficiario.
6. La eliminación impide seleccionarlo para nuevas operaciones.
7. Las transferencias históricas conservan su información original.
8. Las programaciones recurrentes guardan un snapshot independiente del destinatario.
9. Eliminar un beneficiario no cancela ni redirige programaciones existentes.
10. Las ejecuciones futuras siguen sujetas a estado, saldos y límites.
11. La eliminación no altera balances ni crea movimientos.

**Resultado observado:** Gemini aceptó la respuesta y ejecutó una escritura de `spec.md`, reemplazando 283 por 287 líneas.

La transcripción muestra la operación aceptada y la continuación del flujo con una nueva pregunta. No contiene una comparación independiente íntegra del documento final.

**Justificación:** preservar la integridad histórica y evitar que modificaciones posteriores redirijan pagos recurrentes ya autorizados.

### 6.6. D-09 — Fecha inicial de ejecución de pagos recurrentes

**Pregunta de Gemini:** Cuando el usuario define explícitamente una fecha futura para una programación recurrente, ¿qué formato debe utilizar y a qué hora UTC se ejecuta por primera vez?

Opciones:

- **A:** Fecha calendario `YYYY-MM-DD`; primera ejecución a las `00:00:00 UTC`. Sin fecha explícita, primera ejecución después de un intervalo completo.
- **B:** Fecha y hora completas ISO-8601, permitiendo definir hora y minuto.
- **C:** Fecha `YYYY-MM-DD` combinada con la hora a la que se creó la programación.

Gemini recomienda A.

**Selección propuesta:** A.

Comportamiento preparado:

1. Admitir fechas explícitas en formato `YYYY-MM-DD`.
2. Interpretarlas como `00:00:00 UTC` de la fecha seleccionada.
3. Exigir que el instante de ejecución sea estrictamente futuro respecto de la creación.
4. Si no se proporciona fecha, calcular la primera ejecución como fecha y hora de creación más un intervalo completo.
5. Las frecuencias tienen duraciones exactas: diaria = 24 horas, semanal = 7 días, mensual = 30 días.
6. Las ejecuciones posteriores conservan el horario UTC y avanzan un intervalo desde el vencimiento anterior.
7. Si se exige MFA, la programación permanece `PENDING_MFA` hasta su verificación, sin recalcular la fecha inicial solo por confirmar unos segundos después.
8. Los estados `PENDING_MFA` y `EXPIRED` nunca son ejecutables.
9. Los fallos por fondos o límites se registran y avanzan el vencimiento según REC-10.
10. La interfaz identifica claramente la interpretación UTC.
11. No se introducen nuevas frecuencias ni configuración adicional de zonas horarias.

**Justificación:** una fecha calendario con hora UTC fija produce resultados deterministas y simplifica la comparación entre herramientas. Mantiene los intervalos exactos establecidos por el contrato común.

**Estado:** Decisión formulada en el siguiente prompt. Pendiente de confirmar su aplicación por Gemini.

### 6.7. Registro acumulado de aclaraciones

| ID | Tema | Decisión | Evidencia |
|---|---|---|---|
| D-05 | MFA y persistencia recurrente | A | `spec.md` 269 → 277 |
| D-06 | Liquidación y fallos ACH | B | `spec.md` 277 → 279 |
| D-07 | Reducción de límites diarios | A | `spec.md` 279 → 283 |
| D-08 | Gestión de beneficiarios | A | `spec.md` 283 → 287 |
| D-09 | Fecha inicial y horario UTC | A propuesta | Pendiente |

---

## 7. Control de prompts

Durante `/speckit.specify` se detectó truncamiento de entrada. Desde entonces se emplean instrucciones que referencian los contratos persistentes y evitan repetir documentos extensos.

Se conserva el detalle necesario para aprobar decisiones y sus efectos, sin presentar límites empíricos como máximos oficiales de Gemini CLI.

Cada interacción restringe las modificaciones permitidas y exige autorización humana para nuevas decisiones de negocio.

---

## 8. Dimensiones experimentales

| Dimensión | Estado |
|---|---|
| D1 — Esfuerzo y consumo | Transcripciones disponibles; consolidación de tokens, tiempos e interacciones pendiente |
| D2 — Calidad del código | Pruebas heredadas aprobadas; SonarQube E2 pendiente |
| D3 — Especificaciones | 269 líneas inicialmente; 277 tras D-05, 279 tras D-06, 283 tras D-07 y 287 tras D-08 |
| D4 — Expectativa funcional | Contratos establecidos; implementación E2 pendiente |
| D5 — Retroalimentación | Ocho incidencias registradas; cuatro decisiones de aclaración aplicadas según transcripción |

Las cifras de líneas corresponden a operaciones de escritura reportadas por Gemini; no sustituyen una validación independiente de cobertura.

---

## 9. Evidencias

- `SEED-2.md`.
- `E2_COMMON_FUNCTIONAL_CONTRACT.md`.
- `.specify/memory/constitution.md`.
- `specs/001-shift-bank-stage1/`.
- `specs/002-shift-bank-stage2/`.
- Manifiestos SHA-256 de preparación.
- Transcripciones originales de Gemini CLI.
- Resultados originales de Pytest, Vitest y Vite.
- Checklist y especificación E2 generados.
- Respuestas aprobadas por el investigador.

La bitácora documenta observaciones y decisiones, pero no sustituye las evidencias primarias.

---

## 10. Estado actual

**Última decisión aplicada según transcripción:** D-08.

**Próxima decisión propuesta:** D-09, fechas explícitas de programaciones recurrentes.

**Siguiente paso:** confirmar que Gemini registre D-09 y continuar las aclaraciones materiales pendientes.

**Planificación e implementación:** todavía no autorizadas.

---

## Iteración 03 — Cierre de `/speckit.clarify`

**Fecha:** 14 de noviembre de 2026  
**Estado:** Completada.

### Decisión D-09 — Fechas de ejecución recurrente

Se aprobó la opción A presentada por Gemini:

- Las fechas explícitas utilizan `YYYY-MM-DD` y se interpretan a las `00:00:00 UTC`.
- Solo se admiten fechas cuyo instante de ejecución sea estrictamente futuro.
- Sin fecha explícita, el primer vencimiento ocurre después de un intervalo completo desde la creación.
- Los intervalos son exactos: 24 horas, 7 días y 30 días.
- Las ejecuciones posteriores avanzan desde el vencimiento programado anterior.
- La confirmación MFA no desplaza la fecha inicialmente programada.
- Únicamente las programaciones `ACTIVE` pueden ejecutarse.

**Resultado observado:** Gemini actualizó `spec.md`, pasando de 287 a 290 líneas.

### Resultado final de la aclaración

Gemini declaró completado el proceso después de cinco preguntas consecutivas, correspondientes a D-05, D-06, D-07, D-08 y D-09.

| Indicador | Resultado |
|---|---|
| Preguntas formuladas | 5 |
| Decisiones de aclaración aprobadas | 5 |
| Decisiones totales D-01 a D-09 | 9 |
| Especificación inicial | 269 líneas |
| Especificación final | 290 líneas |
| Checklist | 16/16 aprobados según Gemini |
| Ambigüedades restantes | Ninguna según Gemini |

**Archivos modificados:**
- `specs/002-shift-bank-stage2/spec.md`
- `specs/002-shift-bank-stage2/checklists/requirements.md`

El checklist pasó de 35 a 36 líneas. Gemini reportó la incorporación de las nueve decisiones y la finalización del ciclo de aclaraciones.

No se observaron modificaciones de código ni ejecución de pruebas en esta interacción.

**Evaluación:** El flujo de aclaración concluyó satisfactoriamente según la evidencia de Gemini. Las afirmaciones de cobertura y calidad siguen siendo autoevaluaciones, sujetas a verificación posterior.

---

## Iteración 04 — Planificación técnica

**Comando:** `/speckit.plan`  
**Estado:** Pendiente de ejecución.

**Objetivo:** Transformar la especificación aprobada en un plan técnico implementable, incluyendo persistencia, contratos de API, procesos automáticos, manejo de estados, integración de MFA, frontend y estrategia de pruebas.

**Restricción:** Solo se autoriza generar documentación de planificación nativa de Spec Kit. No se autoriza modificar código.

**Evidencia pendiente:** Archivos generados, decisiones arquitectónicas, posibles bloqueos y reporte de finalización de Gemini.

**Próximo hito:** Revisión del plan antes de generar tareas con `/speckit.tasks`.

---

## Iteración 04 — Planificación técnica con `/speckit.plan`

**Fecha:** 14 de noviembre de 2026  
**Estado:** Completada.

### Objetivo

Transformar la especificación aprobada de E2 y las decisiones D-01 a D-09 en un diseño técnico implementable, sin modificar código.

### Artefactos generados

| Archivo | Contenido |
|---|---|
| `plan.md` | Arquitectura, componentes y estrategia de implementación |
| `research.md` | Decisiones técnicas y alternativas |
| `data-model.md` | Esquema SQLite y máquinas de estados |
| `contracts/api.md` | Contratos REST y mecanismos de prueba |
| `quickstart.md` | Verificación de escenarios A01–A21 |

Todos se crearon en `specs/002-shift-bank-stage2/`.

### Decisiones arquitectónicas

- **Backend:** conservar FastAPI y SQLite, sin incorporar ORM.
- **Procesamiento automático:** tareas `asyncio` asociadas al ciclo de vida de FastAPI, con evaluaciones periódicas.
- **Persistencia:** migraciones incrementales e idempotentes, preservando la estructura y los datos heredados.
- **ACH:** operaciones financieras atómicas, liquidación automática y fallos controlados mediante mecanismos exclusivos de prueba.
- **Límites:** cálculo mediante `Decimal` y agregación de transferencias elegibles del día UTC.
- **Recurrencia:** estados explícitos, MFA heredado, fechas UTC e intervalos exactos de 1, 7 y 30 días.
- **Frontend:** ampliación de React y TypeScript con CSS existente, sin bibliotecas visuales adicionales.
- **Validación:** pruebas heredadas y escenarios A01–A21.

### Observaciones de revisión

El plan es coherente en términos generales con la especificación. Sin embargo, antes de implementar deben comprobarse los siguientes riesgos:

1. Un `asyncio.Lock` protege tareas dentro de un proceso, pero no garantiza exclusión entre varios procesos. El diseño debe mantener el alcance de ejecución previsto y la atomicidad en SQLite.
2. Los endpoints de simulación de fallos deben quedar restringidos al entorno de pruebas.
3. La liquidación automática podría competir con la simulación de fallos; las pruebas necesitan un mecanismo determinista.
4. El cálculo del día UTC debe evitar errores de límites temporales y doble contabilización.
5. Las pruebas de programaciones vencidas deben respetar las reglas de fecha futura aprobadas en D-09.

Estas son observaciones técnicas para la descomposición de tareas, no defectos de implementación demostrados.

### Resultado

Gemini reportó cinco artefactos de planificación generados, ausencia de bloqueos y cumplimiento de la constitución. Declaró preparación completa para `/speckit.tasks`.

No se observaron modificaciones de código en la transcripción.

---

## Iteración 05 — Generación de tareas

**Comando:** `/speckit.tasks`  
**Estado:** Pendiente.

**Objetivo:** Descomponer el plan en tareas verificables, ordenadas por dependencias y vinculadas con los requisitos E2 y escenarios A01–A21.

**Alcance autorizado:** únicamente creación de `tasks.md`. Quedan excluidas las modificaciones de código, pruebas y dependencias.

**Evidencia pendiente:** número de tareas, organización por fases, cobertura de requisitos, riesgos y archivos realmente modificados.

**Siguiente hito:** revisión de tareas y consistencia antes de autorizar la implementación.

---

## Iteración 05 — Generación de tareas con `/speckit.tasks`

**Fecha:** 14 de noviembre de 2026  
**Estado:** Completada.

### Resultado

Gemini generó `specs/002-shift-bank-stage2/tasks.md`, con 52 tareas distribuidas en siete fases.

| Fase | Tareas | Cantidad |
|---|---|---:|
| 1. Preparación | T001–T003 | 3 |
| 2. Fundamentos | T004–T008 | 5 |
| 3. Límites dinámicos | T009–T016 | 8 |
| 4. ACH y beneficiarios | T017–T027 | 11 |
| 5. Pagos recurrentes | T028–T040 | 13 |
| 6. Compatibilidad E1 | T041–T046 | 6 |
| 7. Validación final | T047–T052 | 6 |
| **Total** | **T001–T052** | **52** |

Gemini identificó 18 tareas potencialmente paralelizables y declaró cobertura de los requisitos ACH, REC, LIM, HER y escenarios A01–A21.

### Decisiones y observaciones

- La implementación seguirá el orden de dependencias, comenzando por infraestructura y persistencia.
- Las pruebas se integraron como tareas explícitas.
- Se contemplaron mecanismos de protección contra transacciones duplicadas.
- Se incluyeron pruebas para los límites temporales UTC y ejecución automática.
- El agente declaró que no modificó código ni artefactos anteriores.

**Observación:** La cobertura y el paralelismo son afirmaciones del agente todavía no verificadas independientemente. Se requiere analizar posibles conflictos de tareas sobre archivos compartidos, exposición de endpoints de prueba, compatibilidad real de migraciones y seguridad de ejecución concurrente.

### Cierre

**Artefacto creado:** `tasks.md` (191 líneas reportadas).

**Implementación:** No iniciada.

---

## Iteración 06 — Análisis de consistencia

**Comando:** `/speckit.analyze`  
**Estado:** Pendiente.

**Objetivo:** Verificar la consistencia entre especificación, plan, contratos, modelo de datos, pruebas y las 52 tareas antes de autorizar modificaciones de código.

**Alcance:** Análisis de solo lectura. Cualquier corrección posterior requerirá autorización.

**Próximo paso:** Revisar los hallazgos de Gemini, corregir bloqueos confirmados si existen y decidir si puede iniciarse `/speckit.implement`.

---

## Iteración 06 — Análisis de consistencia con `/speckit.analyze`

**Fecha:** 14 de noviembre de 2026  
**Estado:** Completada — hallazgos pendientes de corrección.

### Resultados

Gemini analizó los artefactos de especificación, planificación y tareas frente al código heredado de E1, utilizando el comando nativo `/speckit.analyze`.

Reportó cobertura completa de los 37 requisitos funcionales, nueve decisiones aprobadas y 21 escenarios de aceptación. Identificó diez hallazgos:

| ID | Severidad | Hallazgo |
|---|---|---|
| F-01 | Crítica | Incompatibilidad entre el esquema SQLite E1 y las transferencias ACH |
| F-02 | Crítica | Consulta de historial E1 excluye movimientos ACH |
| F-03 | Alta | Condición de carrera entre liquidación automática y simulación de fallo |
| F-04 | Alta | Comparación temporal UTC incorrecta cerca de medianoche |
| F-05 | Alta | Riesgo de reembolsos duplicados por operaciones no atómicas |
| F-06 | Alta | Tareas paralelas modifican el mismo archivo de pruebas |
| F-07 | Media | `asyncio.Lock` no protege múltiples procesos |
| F-08 | Media | Falta especificar actualización automática de MFA vencidos |
| F-09 | Media | Validaciones de límites deben anteceder al MFA heredado |
| F-10 | Baja | Riesgo de contaminación entre bases de pruebas |

### Hallazgos principales

**F-01:** La tabla `transfers` heredada exige `destination_account_id NOT NULL`, incompatible con transferencias hacia cuentas externas. La planificación debe incluir una migración segura de la tabla.

**F-02:** El historial utiliza un `INNER JOIN` con cuentas internas y filtra por `COMPLETED`, por lo que no mostraría movimientos ACH pendientes, liquidados o fallidos.

**F-04:** El cálculo diario previsto utiliza un límite temporal superior que puede excluir movimientos con fracciones de segundo. Se requiere una ventana UTC semiabierta.

**F-06:** Ocho tareas marcadas como paralelas modifican `backend/tests/test_stage2.py`, generando posibles conflictos.

### Observación adicional del investigador

El análisis consideró privados los endpoints de prueba porque no aparecen en el frontend. Esa condición no garantiza que sean inaccesibles por HTTP. Se requiere una restricción explícita por entorno o un mecanismo de pruebas interno.

### Evaluación

Gemini emitió una recomendación de **GO condicionado** a seis correcciones técnicas.

Para reducir el riesgo de introducir defectos durante implementación, se decidió incorporar primero los diez hallazgos en los artefactos técnicos. Esto no modifica los requisitos de negocio aprobados.

**Archivos modificados durante el análisis:** ninguno reportado.

---

## Iteración 07 — Corrección documental posterior al análisis

**Estado:** Pendiente de ejecución.

**Objetivo:** Actualizar los artefactos de planificación y tareas para resolver los hallazgos F-01 a F-10 antes de implementar.

**Alcance autorizado:** documentación técnica de E2 exclusivamente. No se autoriza código, pruebas ni modificaciones de la especificación aprobada.

**Evidencia pendiente:** archivos corregidos, estado de cada hallazgo, número actualizado de tareas paralelas y riesgos restantes.

**Siguiente paso:** verificar las correcciones mediante otro análisis de solo lectura antes de autorizar `/speckit.implement`.

---

## Iteración 07 — Correcciones documentales interrumpidas

**Fecha:** 14 de noviembre de 2026  
**Estado:** Parcialmente ejecutada.

### Resultado observado

Gemini comenzó la corrección documental de los diez hallazgos del análisis anterior.

Se registraron modificaciones en:

- `research.md`: incorporación de recomendaciones sobre migraciones, concurrencia, liquidación ACH, límites UTC y protección de mecanismos de prueba.
- `data-model.md`: revisión de la migración SQLite y de las máquinas de estados.

Durante la ejecución aparecieron errores HTTP 400 `INVALID_ARGUMENT`, específicamente relacionados con una discrepancia entre las partes de llamadas y respuestas de funciones.

El proceso no terminó correctamente y no existe confirmación de que los demás artefactos hayan sido corregidos.

### Incidencia INC-09

**Tipo:** Fallo de comunicación con la API durante una operación de múltiples escrituras.

**Impacto:** Corrección documental incompleta, con archivos potencialmente en estados intermedios.

**Acción:** Reiniciar la sesión de Gemini y reanudar desde los archivos actuales, conservando las modificaciones válidas.

**Restricción:** No iniciar la implementación hasta completar y verificar las correcciones.

---

## Iteración 07 — Finalización de las correcciones documentales

**Fecha:** 14 de noviembre de 2026  
**Estado:** Completada según Gemini.

### Resultados

Después de reiniciar Gemini CLI, se reanudaron las correcciones interrumpidas por los errores HTTP 400.

Gemini inspeccionó los documentos existentes y completó los ajustes pendientes.

**Archivos modificados durante la continuación:**

- `data-model.md`: historial unificado mediante `LEFT JOIN`.
- `plan.md`: migración SQLite, concurrencia, límites UTC y protección de endpoints.
- `contracts/api.md`: contratos de historial, validaciones y operaciones de prueba.
- `quickstart.md`: procedimientos actualizados de validación.
- `tasks.md`: dependencias, pruebas separadas y correcciones técnicas.

`research.md` ya había sido modificado durante la ejecución interrumpida.

### Hallazgos corregidos

Gemini declaró resueltos los diez hallazgos F-01 a F-10 a nivel documental. Entre los ajustes principales destacan la migración segura de `transfers`, liquidación ACH después de diez segundos, reembolsos atómicos, ventanas UTC semiabiertas, aislamiento de bases de pruebas y restricción de endpoints administrativos.

Las tareas se conservaron en **52**, distribuidas en siete fases. El agente reportó **17 tareas paralelizables y 35 secuenciales**, frente a las 18 paralelizables inicialmente declaradas.

**Evaluación:** La corrección documental concluyó, pero todavía no se ha demostrado mediante implementación ni pruebas que todos los problemas estén resueltos.

### Registro de métricas de sesión de Gemini CLI

Al cerrar la sesión anterior, Gemini proporcionó estadísticas acumuladas:

| Métrica | Valor |
|---|---:|
| Duración total | 1 h 6 min 2 s |
| Tiempo activo del agente | 26 min 21 s |
| Tiempo de API | 22 min 21 s |
| Tiempo de herramientas | 4 min |
| Llamadas a herramientas | 106 |
| Llamadas exitosas | 103 |
| Llamadas fallidas | 3 |
| Tasa de éxito | 97,2 % |
| Líneas añadidas | 3435 |
| Líneas eliminadas | 1996 |

**Uso de modelos registrado:**

| Modelo | Solicitudes | Tokens entrada | Tokens salida |
|---|---:|---:|---:|
| `gemini-3.8-flash` | 116 | 15.033.790 | 117.188 |
| `gemini-3-flash-preview` | 2 | 30.464 | 204 |
| **Total** | **118** | **15.064.254** | **117.392** |

Las lecturas de caché reportadas fueron 13.980.169 tokens. Estas estadísticas corresponden a la sesión completa, no exclusivamente a una iteración. Tampoco permiten calcular directamente un costo monetario sin información adicional de facturación.

**Observación experimental:** El modelo principal reportado por la sesión fue `gemini-3.8-flash`, diferente del modelo inicialmente configurado como `gemini-3.5-flash`. Esta discrepancia debe conservarse en el registro metodológico.

---

## Iteración 08 — Análisis final de consistencia

**Comando:** `/speckit.analyze`  
**Estado:** Pendiente de ejecución.

**Objetivo:** Verificar las correcciones F-01 a F-10 y comprobar la consistencia de los artefactos técnicos antes de implementar.

**Alcance:** Exclusivamente lectura y análisis.

**Criterio de continuación:** Autorizar `/speckit.implement` únicamente después de revisar los hallazgos críticos y altos que puedan permanecer.

**Evidencia pendiente:** Informe de análisis y decisión GO/NO-GO.

---

## Iteración 08 — Verificación final con `/speckit.analyze`

**Fecha:** 14 de noviembre de 2026  
**Estado:** Completada.

### Resultados

Gemini ejecutó un análisis de solo lectura para verificar las correcciones F-01 a F-10 frente a los artefactos técnicos y el código heredado.

| Indicador | Resultado reportado |
|---|---|
| Hallazgos anteriores revisados | 10 |
| Hallazgos críticos pendientes | 0 |
| Hallazgos altos pendientes | 0 |
| Otros hallazgos pendientes | 0 |
| Tareas de implementación | 52 |
| Tareas paralelizables | 17 |
| Escenarios de aceptación cubiertos | 21/21 |
| Veredicto | **GO** |

El análisis confirmó documentalmente las estrategias de migración SQLite, preservación de E1, precisión monetaria, concurrencia, liquidación ACH, límites UTC, manejo de MFA y aislamiento de pruebas.

### Evaluación

El resultado permite continuar a implementación. No obstante, la verificación fue documental: no se ejecutó código ni se demostró todavía el funcionamiento de las soluciones propuestas.

La cobertura reportada y la ausencia de hallazgos corresponden a la evaluación de Gemini, no a pruebas funcionales independientes.

**Archivos modificados:** Ninguno reportado.

---

## Iteración 09 — Inicio de implementación

**Comando:** `/speckit.implement`  
**Estado:** Pendiente de ejecución.

### Alcance autorizado

Se autorizan exclusivamente las primeras ocho tareas:

- **T001–T003:** preparación, aislamiento de pruebas y modelos TypeScript.
- **T004–T008:** migración SQLite, límites iniciales, modelos Pydantic, protección de concurrencia e infraestructura del scheduler.

La ejecución se divide en fases para facilitar la observación de errores y la verificación de compatibilidad.

**Criterio de avance:** Revisar los archivos modificados, pruebas y bloqueos antes de autorizar T009–T016.

**Implementación funcional ACH, recurrencia y límites:** todavía pendiente.

---

## Iteración 09 — Implementación inicial con `/speckit.implement`

**Fecha:** 14 de noviembre de 2026  
**Estado:** T001–T008 completadas según Gemini; verificación adicional pendiente.

### Resultados

Gemini implementó las fases de preparación e infraestructura de Shift Bank E2.

**Archivos creados:**
- `backend/tests/conftest.py`
- `backend/src/scheduler.py`

**Archivos modificados:**
- `backend/src/database.py`
- `backend/src/models.py`
- `backend/src/main.py`
- `frontend/src/types.ts`
- `specs/002-shift-bank-stage2/tasks.md`

Se incorporaron migraciones SQLite, tablas de E2, límites iniciales, modelos Pydantic, aislamiento de pruebas, tipos TypeScript e infraestructura del scheduler con FastAPI lifespan.

El scheduler todavía contiene funciones de procesamiento pendientes de desarrollar.

### Validaciones observadas

| Validación | Resultado |
|---|---|
| Pruebas backend heredadas | 12/12 aprobadas |
| Pruebas frontend heredadas | 5/5 aprobadas |
| Build frontend | Exitoso |
| Prueba temporal de migración SQLite | Aprobada |
| Funciones de bloqueo del scheduler | Verificadas |
| Protección de endpoints de prueba | Verificación básica aprobada |

Se registraron errores transitorios de comandos PowerShell/Python, posteriormente corregidos. Gemini terminó reportando cero errores.

### Incidencia INC-10 — Modificación de la base de desarrollo

Durante la ejecución, `backend/shift_bank.db` cambió:

- **Tamaño inicial:** 24.576 bytes.
- **Tamaño final:** 53.248 bytes.
- **Última modificación final:** 14:05:47.
- **Contenido final observado:** dos transferencias semilla, una transferencia adicional y configuración de límites.

Aunque Gemini declaró que la base permaneció intacta, las evidencias muestran que fue modificada durante el flujo. No se ha demostrado que el cambio haya sido causado específicamente por Pytest.

**Impacto:** No está completamente verificado el aislamiento entre pruebas, inicialización del backend y base de desarrollo.

---

## Iteración 10 — Auditoría de infraestructura

**Estado:** Pendiente.

**Objetivo:** Investigar la modificación de la base de datos y verificar la seguridad de la infraestructura antes de desarrollar los límites dinámicos.

**Alcance:** Corrección de defectos confirmados en T001–T008, sin iniciar nuevas funcionalidades.

**Próximo paso:** Revisar el resultado y decidir si se autoriza T009–T016.

---

## Iteración 10 — Auditoría y corrección del aislamiento de bases de datos

**Fecha:** 14 de noviembre de 2026  
**Estado:** Completada.

### Causa identificada

Gemini determinó que el cambio de tamaño de `backend/shift_bank.db` de 24.576 a 53.248 bytes fue provocado por una ejecución manual de `database.init_db()` fuera de Pytest.

Al no existir `TEST_DB_PATH`, la función utilizó la ruta predeterminada y aplicó la migración SQLite, creó las nuevas tablas y registró los límites iniciales.

Por tanto, la afirmación anterior de que la base de desarrollo no había sido modificada fue incorrecta. Las pruebas Pytest posteriores sí utilizaron una base aislada.

### Correcciones implementadas

Se modificó `backend/src/database.py` para:

- Detectar automáticamente contextos de prueba y seleccionar una base aislada.
- Resolver dinámicamente la ruta de base de datos.
- Ejecutar la reconstrucción de la tabla `transfers` mediante una transacción con rollback ante errores.
- Mejorar la idempotencia de las migraciones.

### Verificaciones

| Validación | Resultado |
|---|---|
| Backend E1 | 12/12 aprobadas |
| Frontend E1 | 5/5 aprobadas |
| Build frontend | Exitoso |
| Migración SQLite en base temporal | Aprobada |
| Segunda ejecución de migración (idempotencia) | Aprobada |
| Integridad y claves foráneas | Aprobadas |
| Scheduler y protección de endpoints | Verificados |
| Base de desarrollo durante nuevas pruebas | Sin cambios observados |

No se modificó nuevamente la base de desarrollo durante esta auditoría.

**Resultado:** Gemini mantuvo T001–T008 completadas y emitió **GO para Fase 3**.

---

## Iteración 11 — Implementación de límites dinámicos

**Comando:** `/speckit.implement`  
**Estado:** Pendiente.

**Alcance:** T009–T016, correspondientes a la historia de usuario US1.

Se implementarán configuración de límites, cálculo de consumo diario UTC, validación antes de MFA, interfaz React y pruebas automatizadas.

**Avance previo:** 8/52 tareas completadas (15,4 %).

**Próximo hito:** Verificar US1 antes de comenzar ACH y beneficiarios (T017–T027).

---

## Iteración 11 — Implementación de límites dinámicos (US1)

**Fecha:** 14 de noviembre de 2026  
**Comando:** `/speckit.implement`  
**Estado:** Completada según Gemini.

### Resultados

Gemini ejecutó las tareas T009–T016, implementando la primera funcionalidad nueva de E2: configuración y aplicación de límites dinámicos.

**Funcionalidades implementadas:**

- Consulta y actualización de límites mediante `GET /api/limits` y `PUT /api/limits`.
- Límites iniciales de COP 5.000.000 por transferencia y COP 10.000.000 diarios.
- Consumo acumulado mediante `Decimal` y ventanas UTC semiabiertas.
- Reducción inmediata del límite diario, sin disponibilidad negativa.
- Validación de límites antes de MFA y nuevamente al confirmar.
- Interfaz React para consultar y modificar límites.
- Pruebas backend y frontend de la funcionalidad.

### Incidencias durante la implementación

Se observaron tres problemas corregidos durante la ejecución:

1. **Validación HTTP:** Pydantic devolvía 422 donde las pruebas exigían 400. Gemini agregó un manejador global de errores de validación.
2. **Pruebas frontend:** aparecieron coincidencias ambiguas al localizar importes repetidos. Se ajustaron los selectores.
3. **Pruebas backend combinadas:** inicialmente hubo cinco fallos y un error por contaminación entre pruebas y bloqueo SQLite. Gemini ajustó los fixtures y el cierre de conexiones.

### Validación final

| Indicador | Resultado |
|---|---:|
| Pruebas backend E1 | 12/12 |
| Pruebas backend US1 | 9/9 |
| Total backend | 21/21 |
| Pruebas frontend | 7/7 |
| Build frontend | Exitoso |
| Base de desarrollo | Sin cambios observados durante las pruebas finales |

### Observación técnica

La interfaz de actualización utiliza `parseFloat().toFixed(2)`, que puede redondear silenciosamente valores con más de dos decimales. Aunque el backend valida la precisión, conviene corregir este comportamiento para respetar la especificación también desde la interfaz.

**Evaluación:** US1 pasó las pruebas registradas y se completaron las ocho tareas previstas. Los errores intermedios y sus correcciones forman parte de la evidencia experimental.

---

## Iteración 12 — Transferencias ACH y beneficiarios (US2)

**Estado:** Pendiente de ejecución.  
**Alcance:** T017–T027.

**Objetivo:** Implementar beneficiarios persistentes, transferencias ACH simuladas, liquidación autónoma, fallos y reembolsos idempotentes, preservando MFA y límites dinámicos.

**Avance acumulado de implementación:** 16/52 tareas (30,8 %).

**Próximo hito:** Validar US2 antes de comenzar pagos recurrentes (T028–T040).

---

## Iteración 12 — Implementación de ACH y beneficiarios (US2)

**Fecha:** 14 de noviembre de 2026  
**Comando:** `/speckit.implement`  
**Estado:** Completada según Gemini.

### Resultados

Gemini ejecutó las tareas T017–T027, implementando:

- Creación, consulta y eliminación de beneficiarios.
- Validaciones de routing de nueve dígitos y cuentas de 4–17 dígitos.
- Transferencias ACH con destinatarios guardados o nuevos.
- MFA para transferencias desde COP 1.000.000.
- Débito único, estado `PENDING` y liquidación automática a `SETTLED` tras diez segundos de elegibilidad.
- Simulación de fallos con reintegro único y protección contra duplicados.
- Historial de transferencias internas y ACH.
- Interfaz React con formularios, selección de beneficiarios y validaciones.

También se corrigió parcialmente la validación de decimales de la interfaz de límites.

### Incidencias

Durante la implementación se observaron:

1. **Transacción SQLite anidada:** una transferencia ACH con beneficiario guardado produjo `cannot start a transaction within a transaction`. Gemini reorganizó la operación financiera.
2. **Pruebas frontend:** inicialmente fallaron tres pruebas y posteriormente dos por diferencias entre los componentes y sus selectores. Se ajustaron los nombres y las pruebas.
3. **Observación pendiente:** el formulario ACH todavía utilizaba `parseFloat().toFixed(2)`, con riesgo de redondear silenciosamente importes inválidos.

La ejecución terminó con todas las pruebas registradas aprobadas.

### Validación final

| Indicador | Resultado |
|---|---:|
| Pruebas backend E1 | 12/12 |
| Pruebas backend límites | 9/9 |
| Pruebas backend ACH | 11/11 |
| **Total backend** | **32/32** |
| **Pruebas frontend** | **10/10** |
| Build frontend | Exitoso |
| Base de desarrollo | Sin cambios observados |

**Limitación:** la prueba de liquidación ACH registrada utilizó un disparador de pruebas. Aunque el procesamiento autónomo fue implementado, su funcionamiento continuo no queda demostrado únicamente por esa prueba.

### Evaluación

US2 quedó implementada y validada según los resultados registrados por Gemini. Se conservaron las pruebas heredadas y las restricciones funcionales aprobadas.

---

## Iteración 13 — Implementación de pagos recurrentes (US3)

**Comando:** `/speckit.implement`  
**Estado:** Pendiente de ejecución.

**Alcance:** T028–T040.

**Objetivo:** Implementar el ciclo de vida de las programaciones, autorización MFA, ejecución autónoma, manejo de fallos y controles de interfaz.

**Avance acumulado:** 27/52 tareas completadas (51,9 %).

**Próximo hito:** Validar los pagos recurrentes antes de iniciar la fase de compatibilidad E1 (T041–T046).

---

## Iteración 13 — Implementación de pagos recurrentes (US3)

**Fecha:** 14 de noviembre de 2026  
**Comando:** `/speckit.implement`  
**Estado:** Completada según Gemini.

### Resultados

Gemini ejecutó las tareas T028–T040, incorporando la tercera funcionalidad principal de E2.

**Funcionalidades implementadas:**

- Programaciones internas y ACH con frecuencias diaria (+24 h), semanal (+7 días) y mensual (+30 días).
- Fechas explícitas de inicio a las 00:00 UTC y fechas predeterminadas calculadas desde la creación.
- Estados `ACTIVE`, `PENDING_MFA`, `PAUSED`, `CANCELLED` y `EXPIRED`.
- Autorización MFA para programaciones desde COP 1.000.000, con vigencia de 300 segundos.
- Ejecución automática de programaciones activas, validando saldo y límites.
- Registro de ejecuciones exitosas o fallidas y actualización de la siguiente fecha.
- Conservación de destinatarios ACH después de eliminar beneficiarios.
- Interfaz React para crear, consultar, pausar, reanudar, cancelar y autorizar programaciones.

También se reforzó la validación de precisión decimal en los formularios monetarios.

### Incidencias durante la implementación

1. **Expiración MFA:** una prueba esperaba HTTP 410, pero el backend devolvía 400. Se corrigió la respuesta para programaciones expiradas.
2. **Compilación TypeScript:** faltaba importar `RecurringScheduleCreate`. El error se corrigió.
3. **Pruebas frontend:** inicialmente fallaron tres pruebas y posteriormente una, principalmente por selectores y mensajes distintos a los esperados. Gemini ajustó las implementaciones y pruebas.

### Validación final

| Indicador | Resultado |
|---|---:|
| Pruebas backend E1 | 12/12 |
| Pruebas backend límites | 9/9 |
| Pruebas backend ACH | 11/11 |
| Pruebas backend recurrencia | 9/9 |
| **Total backend** | **41/41** |
| **Pruebas frontend** | **12/12** |
| Build frontend | Exitoso |
| Base de desarrollo | Sin cambios observados |

### Observación metodológica

Las pruebas de ejecución recurrente registradas utilizaron principalmente modificaciones controladas de fechas y el endpoint de ejecución de pruebas. La integración con el scheduler autónomo fue implementada, pero todavía se requiere demostrar su funcionamiento real mediante el ciclo de vida de FastAPI, sin disparadores manuales.

Adicionalmente, la ausencia de modificaciones en la base de desarrollo se verificó mediante tamaño y fecha de modificación, no mediante comparación criptográfica del contenido.

**Evaluación:** US3 superó las pruebas registradas. Su integración autónoma completa deberá verificarse durante la validación final.

---

## Iteración 14 — Verificación de compatibilidad E1 (US4)

**Comando:** `/speckit.implement`  
**Estado:** Pendiente.

**Alcance:** T041–T046.

**Objetivo:** Verificar que las funcionalidades E2 preserven los contratos, datos iniciales, transferencias internas, historial y MFA heredados de E1.

**Avance acumulado:** 40/52 tareas completadas (76,9 %).

**Siguiente hito:** Completar la regresión de E1 y después realizar la validación transversal final (T047–T052).

---

## Iteración 14 — Verificación de compatibilidad E1 (US4)

**Fecha:** 14 de noviembre de 2026  
**Comando:** `/speckit.implement`  
**Estado:** Completada según Gemini.

### Resultados

Gemini ejecutó T041–T046, correspondientes a la preservación de las funcionalidades heredadas de E1.

Se creó `backend/tests/test_stage2_regression.py`, con cinco pruebas adicionales para verificar:

- Saldos iniciales, transferencias semilla e historial.
- Compatibilidad de los contratos REST de transferencias internas.
- MFA heredado y validación del código `123456`.
- Historial unificado de transferencias internas, ACH y recurrentes.
- Integridad de saldos al combinar funcionalidades de E1 y E2.

### Incidencia

La primera ejecución de las nuevas pruebas produjo un error `NameError` porque faltaba importar `timedelta`. Gemini corrigió el import y repitió las pruebas exitosamente.

### Validación final

| Indicador | Resultado |
|---|---:|
| Pruebas backend | 46/46 |
| Pruebas frontend | 12/12 |
| Build frontend | Exitoso |
| Base de desarrollo | Tamaño y fecha de modificación sin cambios |

**Archivos modificados:** `backend/tests/test_stage2_regression.py` y `tasks.md`.

**Evaluación:** Gemini declaró completadas las seis tareas y no reportó bloqueos. La verificación final transversal permanece pendiente.

---

## Iteración 15 — Validación final de E2

**Comando:** `/speckit.implement`  
**Estado:** Pendiente.

**Alcance:** T047–T052.

**Objetivo:** Completar las verificaciones funcionales y de integración, comprobar la ejecución autónoma real y cerrar la trazabilidad de los escenarios A01–A21.

**Avance acumulado:** 46/52 tareas (88,5 %).

**Criterio de cierre:** Todas las tareas verificadas y ausencia de defectos críticos o altos pendientes.

---

## Iteración 15 — Verificación final y cierre de implementación E2

**Fecha:** 14 de noviembre de 2026  
**Comando:** `/speckit.implement`  
**Estado:** Completada.

### Resultados

Gemini ejecutó las seis tareas finales, T047–T052, y declaró finalizada la implementación de Shift Bank E2.

Se verificaron los contratos de error HTTP, la precisión monetaria, las pruebas de regresión, el build frontend y la trazabilidad de los 21 escenarios de aceptación.

### Verificación de ejecución autónoma

Se incorporó `test_autonomous_lifespan_scheduler_ach_and_recurring` en `backend/tests/test_stage2_regression.py`.

La prueba inició el ciclo de vida de FastAPI mediante `TestClient(app)` y comprobó que el scheduler:

- Liquidara una transferencia ACH sin invocar manualmente el endpoint de simulación.
- Ejecutara un pago recurrente vencido.
- Actualizara saldos y fechas de ejecución.

Para acelerar la prueba, las fechas de elegibilidad fueron modificadas directamente en una base de datos aislada. Por tanto, se verificó el disparo autónomo, pero no una espera real de diez segundos desde la creación de la transferencia.

### Resultados finales

| Indicador | Resultado |
|---|---:|
| Tareas completadas | 52/52 |
| Pruebas backend | 47/47 |
| Pruebas frontend | 12/12 |
| Build de producción | Exitoso |
| Escenarios A01–A21 | Cobertura declarada por Gemini |
| Veredicto de Gemini | GO |

**Archivos modificados:**

- `backend/tests/test_stage2_regression.py`
- `specs/002-shift-bank-stage2/tasks.md`

### Limitaciones del cierre

Aunque Gemini reportó cero defectos pendientes y declaró la solución lista para producción, esta última afirmación excede la evidencia disponible.

La aplicación sigue siendo un prototipo experimental con autenticación simulada, MFA fijo, SQLite y scheduler de un solo proceso. La verificación tampoco constituye una prueba exhaustiva de concurrencia o carga.

El archivo `backend/shift_bank.db` conservó su tamaño y fecha de modificación durante las últimas verificaciones. No se registró una comparación mediante hashes.

**Conclusión:** La implementación experimental de E2 quedó finalizada según el plan de 52 tareas y las pruebas ejecutadas.

---

## Iteración 16 — Consolidación de evidencias experimentales

**Estado:** Pendiente.

**Objetivo:** Consolidar resultados, métricas operativas, consumo de tokens, incidencias y limitaciones de Spec Kit en E2.

**Restricción:** No modificar la implementación ni comenzar E3.

**Criterio de cierre:** Contar con un informe reproducible que diferencie los resultados observados, las declaraciones del agente y las métricas todavía no disponibles.

---

## Iteración 16 — Consolidación de evidencias de Spec Kit

**Fecha:** 14 de noviembre de 2026  
**Estado:** Completada.

Gemini generó `E2_SPECKIT_FINAL_EVIDENCE.md`, consolidando la implementación, pruebas, trazabilidad y telemetría.

**Resultados registrados:**

- Implementación: 52/52 tareas.
- Pruebas backend: 47 aprobadas.
- Pruebas frontend: 12 aprobadas.
- Build frontend: exitoso.
- Escenarios A01–A21: cobertura declarada por Gemini.
- Veredicto: prototipo experimental validado, sin certificación de producción.

### Telemetría reportada

| Métrica | Total |
|---|---:|
| Sesiones | 2 |
| Interacciones humanas | 25 |
| Solicitudes API | 972 |
| Tokens de entrada | 236.439.047 |
| Tokens cacheados | 208.019.589 |
| Tokens de salida | 600.788 |
| Llamadas a herramientas | 5.213 |
| Tiempo de pared | 4 h 55 min 34 s |
| Costo | N/D |

Los valores proceden del análisis realizado por Gemini y requieren revisión metodológica, especialmente el conteo de llamadas a herramientas.

### Observaciones

Gemini generó dos copias del informe, una dentro del workspace y otra en la carpeta central de experimentos.

El registro reporta cero errores de herramientas, aunque durante la extracción se observaron comandos fallidos y errores de procesamiento. Estas categorías deben distinguirse.

La cobertura automatizada A01–A21 no equivale a una validación manual completa. El informe tampoco acredita por sí solo los cortes SonarQube, el Diff LOC y el inventario final SHA-256.

---

## Iteración 17 — Auditoría de medición experimental

**Estado:** Pendiente.

**Objetivo:** Revisar la integridad de la telemetría e identificar las mediciones faltantes antes de cerrar la comparación experimental.

**Avance de implementación:** 100 %.

---

## Iteración 17 — Auditoría de métricas experimentales

**Estado:** Completada.

Gemini auditó los registros JSONL originales y corrigió el conteo duplicado de tokens y herramientas.

**Telemetría corregida:**

- Sesiones: 2.
- Interacciones humanas: 25.
- Solicitudes al modelo: 521.
- Tokens de entrada: 123.950.969.
- Tokens cacheados: 108.868.091.
- Tokens de salida: 335.430.
- Llamadas únicas a herramientas: 485.
- Errores de herramientas: 10.
- Tiempo transcurrido: 4 h 55 min 34 s.
- Costo: N/D.

Se contabilizaron ocho archivos de especificación con 1.640 líneas.

**Pendientes:** SonarQube, inventario SHA-256, Diff LOC y validación manual A01–A21.

**Archivo generado:** `E2_SPECKIT_PENDIENTES_MEDICION.md`.

---

## Iteración 18 — Mediciones finales

**Estado:** Pendiente.

**Objetivo:** Generar inventarios SHA-256, calcular Diff LOC y obtener métricas de SonarQube comparables con Tessl.

**Avance de implementación:** 100 %.

**Cambio a Etapa 3:** Aplazado hasta completar el cierre experimental de E2.

---

## Iteración 18 — Inventarios SHA-256 y métricas Diff LOC

**Fecha:** 14 de noviembre de 2026  
**Estado:** Completada parcialmente respecto al cierre experimental.

### Resultados

Se generaron los inventarios y las métricas de evolución entre E1 y E2.

- Archivos E1: 59.
- Archivos E2: 74.
- Archivos nuevos: 15.
- Archivos modificados: 10.
- Archivos sin cambios: 49.
- Archivos eliminados: 0.
- Líneas añadidas: 7.298.
- Líneas eliminadas: 273.
- Cambio neto: +7.025 líneas.

Se generaron manifiestos SHA-256, matrices Diff LOC, resúmenes CSV y documentación de especificaciones.

### Bloqueador de SonarQube

Se verificó que el servidor SonarQube y SonarScanner Docker estaban disponibles con las versiones utilizadas en Tessl.

Sin embargo, el análisis no pudo ejecutarse porque el servidor respondió HTTP 401 y no se encontró un token de autenticación configurado.

### Pendientes

1. Ejecutar SonarQube E1 y E2 con autenticación válida.
2. Completar la validación manual de la aplicación y registrar evidencias.

---

## Iteración 19 — Análisis SonarQube

**Estado:** Pendiente de ejecución.

**Objetivo:** Obtener métricas estáticas comparables con Tessl para la línea base E1 y la implementación final E2.

**Avance de implementación:** 100 %.

---

## Iteración 19 — Análisis estático SonarQube E2

**Estado:** Completada parcialmente.

### Resultados

Gemini ejecutó correctamente SonarScanner sobre la implementación final de Spec Kit E2 y exportó las métricas e incidencias mediante la API autenticada de SonarQube.

Se registraron 4.099 NCLOC, 3 bugs, 72 code smells, 476 minutos de deuda técnica, complejidad cognitiva de 460 y fiabilidad MQR D.

El Quality Gate indicó OK, pero no tenía condiciones configuradas, por lo cual no representa una validación independiente de calidad.

### Incidencias

El análisis E1 no pudo realizarse porque el token utilizado tenía permisos exclusivos sobre el proyecto E2. SonarQube rechazó la creación y el análisis del proyecto E1.

Durante la generación del informe también ocurrieron varios errores de sintaxis en comandos Python, corregidos posteriormente.

### Telemetría adicional

La pantalla final de Gemini CLI registró, para la sesión identificada como `fe272589-bd7f-4c7d-8205-4f821865bbc9`:

- 486 llamadas a herramientas, 480 exitosas.
- 5 h 34 min 36 s de duración total.
- 4 h 22 min 55 s de actividad del agente.
- 1 h 30 min 24 s de tiempo API.
- 2 h 52 min 31 s de tiempo de herramientas.

Estas cifras deberán conciliarse con la telemetría JSONL previamente consolidada.

---

## Iteración 20 — SonarQube de línea base E1

**Estado:** Pendiente.

**Objetivo:** Ejecutar el análisis de E1 con permisos adecuados y obtener una comparación estática reproducible E1–E2.

**Avance de implementación:** 100 %.

---

## Iteración 20 — SonarQube E1 y conciliación de telemetría

**Estado:** Bloqueada parcialmente.

### Resultados

Gemini intentó ejecutar SonarScanner sobre la línea base histórica de Spec Kit E1, conservando los archivos mediante un montaje de solo lectura.

El escáner procesó los archivos y generó el paquete de análisis, pero el servidor rechazó su publicación por permisos insuficientes.

Se identificó que:

- El proyecto `Shift-Bank---Stage-1---Spec-Kit` todavía no existía.
- El token activo estaba restringido al proyecto E2.
- El token histórico de Spec Kit E1 había expirado.
- Las métricas SonarQube finales de E2 permanecieron intactas.

### Observación de telemetría

Se documentaron por separado las estadísticas de Gemini CLI y las métricas deduplicadas de JSONL.

No obstante, la comparación entre 485 llamadas JSONL consolidadas y 486 llamadas de la captura no demuestra equivalencia: corresponden a alcances temporales diferentes.

Esta observación deberá corregirse en la consolidación definitiva de métricas.

### Evidencia generada

`E2_SPECKIT_SONARQUBE_E1_BASELINE_AND_TELEMETRY.md`

---

## Iteración 21 — Recuperación del análisis SonarQube E1

**Estado:** Pendiente.

**Objetivo:** Completar el análisis estático de E1 utilizando un proyecto y token autorizados, y generar una comparación reproducible con E2.

**Avance de implementación:** 100 %.

**Pendiente posterior:** Validación manual de la aplicación antes del cierre experimental.

---

## Iteración 21 — Nuevo intento de análisis SonarQube E1

**Estado:** Bloqueada.

Gemini verificó nuevamente la autenticación y los permisos de SonarQube.

La autenticación del token fue válida; sin embargo, el proyecto `Shift-Bank---Stage-1---Spec-Kit` no estaba creado en el servidor y el token activo seguía asociado exclusivamente a E2.

El servidor devolvió HTTP 404 al consultar E1 y HTTP 403 al intentar crear el proyecto mediante la API.

No se obtuvieron métricas estáticas E1. Las mediciones finales E2 permanecieron conservadas.

Gemini también actualizó la documentación de telemetría para distinguir los registros JSONL de la captura posterior de estadísticas de Gemini CLI.

### Próximo paso

Crear manualmente el proyecto E1, generar un token con el alcance correspondiente y repetir el análisis.

**Avance de implementación E2:** 100 %.

---

## Iteración 22 — Ejecución autorizada de SonarQube E1

**Estado:** Pendiente de configuración manual.

**Objetivo:** Obtener las métricas SonarQube de E1 y completar la comparación E1–E2 sin modificar las implementaciones.

## Iteración 22 — Cierre de SonarQube E1–E2

**Estado:** Completada.

Se ejecutó un análisis retrospectivo de E1 mediante el proyecto SonarQube existente para E2. Se exportaron los resultados de la línea base y posteriormente se restauró E2 como último análisis del proyecto.

La restauración confirmó coincidencia completa de las 20 métricas medidas respecto al análisis E2 original.

Los resultados evidenciaron un incremento en volumen de código, deuda técnica, code smells y complejidad cognitiva. La fiabilidad MQR pasó de C en E1 a D en E2.

El análisis retrospectivo, realizado después de la implementación, se documentó explícitamente para garantizar la trazabilidad metodológica.

**Telemetría adicional:** La sesión `99ea3c2c-8122-48d3-9c54-16b3e9aadc02` reportó 190 llamadas a herramientas y una duración de 4 h 23 min 11 s.

**Implementación E2:** 100 %.

---

## Iteración 23 — Validación manual y cierre experimental

**Estado:** Pendiente.

**Objetivo:** Ejecutar los escenarios de aceptación en el navegador, registrar evidencias humanas y consolidar el informe experimental definitivo.

**Condición para pasar a E3:** Documentar el resultado de la validación manual y los escenarios que permanezcan sin verificar.

Shift Bank — Etapa 2 / Spec Kit — Telemetría suplementaria de la última sesión
Clasificación: E2_SPECKIT_TELEMETRIA_SUPLEMENTARIA
Fecha de registro: 2026-11-15 (America/Bogota). La captura no muestra una hora explícita de inicio o finalización.
Fuente primaria: captura de cierre de Gemini CLI image(20261116-001730).png, aportada por el investigador y asociada explícitamente por él a Etapa 2.
Session ID: af5b9190-d850-4910-96b5-daadc705bf1a.
1. Estadísticas de interacción (captura literal)
Métrica	Valor observado
Tool Calls	72
Llamadas exitosas	70
Llamadas fallidas	2
Success Rate	97,2 %
User Agreement	100,0 % (70 reviewed)
Code Changes: additions	+1.244
Code Changes: deletions	−527
Wall Time	2 h 21 min 43 s
Agent Active	13 min 26 s
API Time	10 min 17 s (76,6 % del activo)
Tool Time	3 min 8 s (24,4 % del activo)


2. Model Usage (captura literal)
Modelo / función	Requests	Input tokens	Cache reads	Output tokens
gemini-3.5-flash-lite — utility_summarizer	1	0	0	0
gemini-3.8-flash — main	70	7.581.855	6.931.904	49.487
gemini-3-flash-preview — utility_loop_detector	2	44.851	0	261
Total de la captura	73	7.626.706	6.931.904	49.748


Los cache reads se reportan como dimensión separada; no deben sumarse otra vez a input tokens como si fueran consumo adicional. Las 73 solicitudes de modelo y las 72 llamadas a herramientas son métricas distintas.
3. Reglas de integración al cierre E2
1. Esta es una captura adicional de la sesión indicada, no un recálculo del total acumulado de E2.
2. No sumar este registro a capturas previas sin comprobar si son sesiones únicas o capturas solapadas mediante sessionId y registros nativos JSONL.
3. No inferir costo monetario, fecha de comienzo, duración de trabajo humano ni calidad final a partir de la captura.
4. User Agreement 100 % es una estadística de aprobación/revisión de la herramienta; no demuestra que la implementación no tenga defectos.
5. Code Changes +1244/-527 es un contador de la sesión; no sustituye un git diff de cierre ni prueba qué archivos se modificaron.
6. Los modelos y subfunciones se transcriben tal como aparecen en la captura; no se sustituye el modelo principal con el configurado en el entorno.
7. Conservar la imagen original junto al registro y, si existe, el transcript/JSONL de esa misma sesión como evidencia primaria.
8. No contabilizar estos datos como Etapa 3 y no mezclarlos con actividad de Codex durante el Hito 0 de E3.
4. Ruta sugerida en el repositorio local
Shift-Bank/Etapa 2/_experiment_logs/Spec Kit/E2_SPECKIT_TELEMETRIA_ULTIMA_SESION_20261115.md

La creación de este archivo en ChatGPT no modifica automáticamente el repositorio local de Windows. Copiarlo a la ruta sugerida si se desea incorporarlo allí.