# Shift Bank — Etapa 3 — GitHub Spec Kit + Gemini CLI
## Bitácora experimental y registro de decisiones

**Caso de estudio:** Shift Bank  
**Etapa:** E3 — Arquitectura, seguridad y despliegue  
**Herramienta SDD:** GitHub Spec Kit  
**Agente evaluado:** Gemini CLI  
**Fecha de registro inicial:** 2026-11-15  
**Estado actual:** Hito 1 aprobado (GO). Hito 2 — Plan de especificaciones pendiente de revisión.

---

## 1. Preparación y línea base — Hito 0

El entorno experimental fue preparado por Codex, exclusivamente como agente de preparación. Codex no se considera el agente evaluado en E3.

Resultados comunicados del Hito 0:

| Verificación | Resultado |
|---|---|
| Integridad E2 | 74/74 SHA-256 |
| Integridad copia E3 | 74/74 SHA-256 |
| Integridad SEED-3.md | Correcta |
| Pytest backend | 47/47 PASS |
| Vitest frontend | 12/12 PASS |
| Build frontend | PASS |
| Decisión humana | GO |

**Regla metodológica:** Estos resultados pertenecen a la preparación, no a las métricas de desarrollo de Gemini durante E3.

Los informes de preparación se encuentran en `_experiment_logs/Spec Kit/preparacion/`.

---

## 2. Hito 1 — Descubrimiento y aclaraciones

**Objetivo:** Identificar y resolver ambigüedades materiales de SEED-3.md antes de modificar especificaciones o código.

**Restricciones:** Operaciones de solo lectura. Sin implementación, nuevas dependencias, migraciones, pruebas de carga ni despliegue.

### Interacción H1-01 — Descubrimiento inicial

**Prompt:** P0 del protocolo E3, adaptado a GitHub Spec Kit y Gemini CLI.

**Respuesta del agente:** Gemini identificó las funcionalidades heredadas, la arquitectura FastAPI/React/SQLite, las reglas de Spec Kit y cuatro áreas que requerían aclaración: cifrado, auditoría, carga y despliegue.

**Primera pregunta:** Definir el significado del cifrado de extremo a extremo, los campos sensibles, la frontera de confianza y la gestión de claves.

**Decisión E3-ENC-01 — Aprobada:**

- Cifrado a nivel de aplicación entre React y FastAPI.
- Descifrado autorizado en el backend para operaciones bancarias.
- No se exige arquitectura zero-knowledge.
- Protección de identificadores bancarios, beneficiarios, importes y PIN MFA durante su transmisión.
- Cifrado autenticado de información sensible persistente.
- Gestión externa de claves y secretos.
- Prohibición de mecanismos de respaldo inseguros en texto plano.
- Conservación de exactitud monetaria y funcionalidades heredadas.

**Observación:** La protección concreta de los importes persistidos deberá quedar explícita y verificable en las especificaciones.

### Interacción H1-02 — Auditoría transaccional

**Pregunta del agente:** Determinar el mecanismo de inmutabilidad, la política de fallo y los eventos que deben auditarse.

**Decisión E3-AUD-01 — Aprobada:**

- Registro append-only con encadenamiento criptográfico verificable.
- Protección contra modificaciones o eliminaciones ordinarias.
- Atomicidad entre operaciones financieras exitosas y sus registros de auditoría.
- Rollback completo cuando falle la auditoría requerida.
- Registro de transferencias internas, ACH, ejecuciones recurrentes, modificaciones de límites y fallos MFA.
- Registro de rechazos sin confirmar cambios financieros inválidos.
- Exclusión de secretos y datos sensibles en texto plano.
- Mecanismo reproducible de verificación de integridad.

**Observación:** La inmutabilidad se define dentro de un modelo de amenazas limitado. No equivale a protección absoluta frente a un administrador con control total del sistema y las claves.

### Interacción H1-03 — Pruebas de carga

**Pregunta del agente:** Definir herramienta, distribución de operaciones, concurrencia, umbrales y aislamiento experimental.

**Decisión E3-LOAD-01 — Aprobada:**

| Parámetro | Valor |
|---|---|
| Herramienta | Locust |
| Usuarios concurrentes | 30 |
| Ramp-up | 5 usuarios/segundo |
| Estado estable | 60 segundos después del ramp-up |
| Consultas de saldos | 60 % |
| Consultas de historial | 30 % |
| Transferencias internas | 10 % |
| p95 lecturas | < 200 ms |
| p95 transferencias | < 500 ms |
| Errores inesperados | < 1 % |

Se exige una base SQLite sintética y aislada, solicitudes HTTP reales con las protecciones criptográficas correspondientes, métricas p50/p95/p99, throughput y conservación del primer benchmark válido.

Los porcentajes efectivos deben medirse a partir de las solicitudes realizadas, no solamente de los pesos configurados.

### Interacción H1-04 — Despliegue

**Pregunta del agente:** Determinar arquitectura de despliegue, TLS, frontend, secretos, persistencia y operación del scheduler.

**Decisión E3-DEP-01 — Aprobada:**

- Despliegue local reproducible mediante Docker Compose.
- Backend FastAPI y frontend React compilado.
- Nginx como proxy inverso con HTTPS local.
- Redirección HTTP a HTTPS.
- Configuración y secretos suministrados externamente.
- Volumen SQLite persistente y aislado.
- Un único scheduler activo.
- Healthchecks y pruebas de humo reproducibles.
- Verificación de persistencia después de reiniciar contenedores.
- No se exige proveedor cloud ni pipeline CI/CD completo.

### Interacción H1-05 — Revisión final del descubrimiento

Gemini consolidó las cuatro decisiones aprobadas y declaró:

`MILESTONE 1 — READY FOR HUMAN REVIEW`

El agente afirmó que no había modificado archivos ni ejecutado operaciones que alteraran el entorno.

**Revisión humana:** GO para cierre del Hito 1.

**Limitación de evidencia:** La ausencia de modificaciones se conoce por declaración del agente. Debe contrastarse con Git y los manifiestos de integridad; no se registra todavía como comprobación independiente.

---

## 3. Estado de decisiones

| ID | Área | Estado |
|---|---|---|
| E3-ENC-01 | Cifrado | Aprobada |
| E3-AUD-01 | Auditoría | Aprobada |
| E3-LOAD-01 | Carga | Aprobada |
| E3-DEP-01 | Despliegue | Aprobada |

**Total:** 4 decisiones principales aprobadas durante el descubrimiento.

La aprobación no autoriza implementación. La creación de especificaciones requiere una autorización posterior e independiente.

---

## 4. Inicio del Hito 2 — Planificación de especificaciones

Se autorizó conceptualmente el inicio del Hito 2, limitado a presentar una propuesta de artefactos mediante el flujo nativo de GitHub Spec Kit.

**Pendiente:** Recibir y revisar la propuesta del agente.

**Restricciones vigentes:**
- No crear ni editar especificaciones todavía.
- No implementar código ni pruebas.
- No ejecutar migraciones, builds o despliegues.
- No modificar E1, E2 ni otras herramientas.

**Próximo punto de control:** Aprobación humana del plan de especificaciones.

---

## 5. Evidencia y telemetría pendiente de consolidación

| Evidencia | Estado |
|---|---|
| Preguntas y respuestas H1 | Disponibles en conversación |
| Decisiones E3-ENC/AUD/LOAD/DEP | Documentadas |
| Transcript original Gemini CLI | Pendiente de exportar/adjuntar |
| Identificador de sesión | Pendiente |
| Versión y modelo efectivo de Gemini | Pendiente de confirmar desde la sesión |
| Tokens de entrada/salida/caché | Pendiente |
| Tool Calls | Pendiente |
| Tiempo activo y tiempo de reloj | Pendiente |
| Verificación independiente de ausencia de cambios | Pendiente |

**Nota:** Las cuatro aclaraciones son interacciones de descubrimiento y no deben contabilizarse automáticamente como correcciones de código en D5.

Las métricas cuantitativas se obtendrán de registros crudos, no de estimaciones ni de resúmenes del agente.

---

## 6. Hito 2 — Planificación de especificaciones

### Interacción H2-01 — Propuesta inicial de artefactos

**Fecha:** 2026-11-15  
**Agente:** Gemini CLI  
**Herramienta:** GitHub Spec Kit  
**Estado:** Plan recibido; aprobación pendiente.

**Prompt del investigador:** Se solicitó revisar las cuatro decisiones aprobadas de E3, inspeccionar los contratos heredados y proponer la estructura de especificaciones mediante el flujo nativo de Spec Kit, sin modificar archivos.

#### 6.1. Resultado propuesto por Gemini

El agente propuso crear un directorio independiente:

`specs/003-shift-bank-stage3/`

Artefactos previstos:

| Artefacto | Propósito |
|---|---|
| `spec.md` | Historias, requisitos y aceptación |
| `contracts/api.md` | Contratos HTTP |
| `data-model.md` | Persistencia y auditoría |
| `plan.md` | Arquitectura técnica |
| `research.md` | Justificación de decisiones |
| `tasks.md` | Tareas de implementación |
| `checklists/requirements.md` | Calidad de requisitos |
| `quickstart.md` | Operación y reproducibilidad |

La propuesta preserva `specs/001-shift-bank-stage1/` y `specs/002-shift-bank-stage2/`.

Gemini relacionó las cuatro capacidades nuevas con historias de usuario y añadió una historia de compatibilidad con E1/E2.

#### 6.2. Decisiones técnicas propuestas, todavía no aprobadas

- AES-256-GCM para cifrado de aplicación y almacenamiento.
- Uso de Web Crypto en React y bibliotecas criptográficas Python.
- Posible clave compartida suministrada externamente.
- Cadena SHA-256 para auditoría.
- API administrativa protegida para verificar auditoría.
- Puertos locales propuestos: 8443/8080.
- Conservación de importes financieros en representación decimal sin cifrado individual para mantener agregaciones SQL.

Estas son propuestas del agente, no decisiones aprobadas por el investigador.

#### 6.3. Revisión humana del plan

**Resultado: AJUSTES REQUERIDOS.**

Se identificaron tres problemas:

**OBS-H2-01 — Gestión de claves.** La propuesta no demuestra cómo evitar exponer una clave simétrica confidencial al navegador. Se solicita revisar el establecimiento y ciclo de vida de claves.

**OBS-H2-02 — Confidencialidad en reposo.** La propuesta de persistir importes financieros en texto claro no demuestra protección de confidencialidad. Un hash de auditoría no sustituye el cifrado. Debe justificarse y resolverse la protección requerida sin alterar la exactitud monetaria.

**OBS-H2-03 — Integridad de auditoría.** El encadenamiento SHA-256 por sí solo no garantiza detectar una reescritura completa de la cadena ni la eliminación de entradas finales. Se requiere precisar el modelo de amenazas y las garantías comprobables.

**OBS-H2-04 — Secuencia metodológica.** Se recuerda que Spec Kit debe generar progresivamente la especificación, el plan y las tareas, con revisión humana entre fases. La lista de artefactos es una previsión, no autorización para crearlos simultáneamente.

#### 6.4. Decisión del investigador

- Organización general: aprobada en principio.
- Solución criptográfica: pendiente.
- Garantías de auditoría: pendientes de justificación.
- Generación de especificaciones: no autorizada.
- Implementación: no autorizada.

**Próxima interacción H2-02:** Solicitar a Gemini una revisión del plan limitada a los hallazgos anteriores, manteniendo el modo de solo lectura.

#### 6.5. Clasificación preliminar para D5

Los hallazgos pertenecen a la revisión de diseño previa a implementación. No constituyen defectos observados en código E3 ni correcciones posteriores a la implementación.

Registrar como intervención humana de aclaración/revisión metodológica. Su contabilización definitiva seguirá las convenciones homogéneas de D5.

**Evidencia pendiente:** Transcript original, identificador de sesión, modelo efectivo, tokens y tiempos.

**Estado del Hito 2:** PLAN EN REVISIÓN — NO GO PARA GENERACIÓN DE ARTEFACTOS.

---

## 7. Hito 2 — Revisión del plan técnico

### Interacción H2-02 — Revisión de arquitectura propuesta

**Fecha:** 2026-11-15  
**Agente:** Gemini CLI  
**Herramienta:** GitHub Spec Kit  
**Estado:** Plan revisado recibido y evaluado.

#### 7.1. Objetivo

Resolver los problemas identificados en H2-01 relacionados con gestión criptográfica de claves, confidencialidad de importes financieros y garantías de auditoría.

También se exigió respetar la secuencia nativa de GitHub Spec Kit, sin generar simultáneamente especificaciones, planes y tareas.

#### 7.2. Propuesta revisada del agente

**A. Cifrado de aplicación**

Gemini propuso una arquitectura de cifrado híbrido:

- Par asimétrico administrado por el backend.
- Distribución de clave pública mediante un endpoint.
- Generación de claves AES-256-GCM efímeras en React mediante Web Crypto.
- Cifrado del contenido y encapsulación de la clave simétrica.
- Descifrado autorizado exclusivamente en el backend.
- Protección de respuestas sensibles mediante mecanismos criptográficos equivalentes.

Esta propuesta evita distribuir una clave simétrica permanente del servidor dentro del frontend.

**B. Cifrado financiero en reposo**

El agente propuso cifrar los importes financieros persistidos en SQLite mediante AES-256-GCM.

Campos considerados:

- `transfers.amount`
- `accounts.balance`
- `recurring_schedules.amount`
- Importes asociados con límites dinámicos.

El agente declaró que el backend utiliza `Decimal` en Python para los cálculos financieros y que no depende de agregaciones SQL mediante `SUM()`.

Esta afirmación procede de la inspección reportada por Gemini y requiere verificación posterior mediante código y pruebas.

**C. Auditoría transaccional**

El agente sustituyó la propuesta de hash simple por:

- Encadenamiento HMAC-SHA256.
- Clave de autenticación externa.
- Secuencias consecutivas.
- Triggers SQLite contra UPDATE y DELETE.
- Mecanismo administrativo de verificación.

Se identificó una limitación pendiente: la continuidad de secuencias y una cadena HMAC no detectan necesariamente el truncamiento final cuando no existe un punto de referencia confiable externo.

**D. Flujo de GitHub Spec Kit**

El agente propuso cuatro fases:

1. Especificación funcional.
2. Arquitectura y contratos.
3. Descomposición en tareas.
4. Implementación y verificación.

Cada fase queda condicionada a revisión y aprobación humana.

#### 7.3. Evaluación del investigador

**Resultado:** Plan apto para continuar con la especificación inicial.

Las soluciones criptográficas propuestas se consideran técnicamente aceptables para evaluación durante la planificación posterior.

No se han aprobado todavía como implementación definitiva ni se ha comprobado su funcionamiento.

Se exige corregir en los artefactos la afirmación de detección absoluta de truncamiento de la cadena de auditoría.

#### 7.4. Decisiones registradas

| Identificador | Decisión | Estado |
|---|---|---|
| H2-TECH-01 | Cifrado híbrido asimétrico y AES-GCM | Candidato técnico aceptado |
| H2-TECH-02 | Importes financieros cifrados en reposo | Enfoque aceptado |
| H2-TECH-03 | Auditoría con HMAC y protecciones SQLite | Candidato aceptado con limitaciones |
| H2-GATE-01 | Inicio de especificación funcional | GO recomendado |
| H2-GATE-02 | Planificación técnica | Pendiente |
| H2-GATE-03 | Implementación | No autorizada |

#### 7.5. Clasificación experimental

Esta interacción corresponde a una revisión humana previa a implementación.

Se corrigieron propuestas de diseño, no defectos observados en software E3 ejecutable.

Para D5 deberá registrarse la intervención y sus motivos, sin clasificarla automáticamente como corrección posterior de código.

#### 7.6. Próxima interacción H2-03

**Acción propuesta:** Invocar `/speckit.specify` para generar la especificación inicial de Stage 3.

**Alcance autorizado al enviar el prompt:** Archivos propios de especificación y listas de comprobación requeridas por el flujo nativo.

**Restricciones:** Sin código, tests, migraciones, dependencias ni despliegue.

**Evidencias por recopilar:**

- Prompt exacto enviado.
- Salida completa de `/speckit.specify`.
- Archivos creados por el workflow.
- Requisitos generados y ambigüedades.
- Cambios Git observados.
- Estadísticas y transcript de Gemini CLI.


**Estado documental:** H2-02 evaluado. H2-03 pendiente de ejecución.

---

## 8. Hito 2 — Generación inicial de especificaciones

### Interacción H2-03 — Ejecución de `/speckit.specify`

**Fecha:** 2026-11-15  
**Agente:** Gemini CLI  
**Herramienta:** GitHub Spec Kit  
**Estado:** Especificación generada; revisión humana pendiente.

#### 8.1. Objetivo

Generar la primera especificación funcional de Shift Bank E3 utilizando el flujo nativo de GitHub Spec Kit, a partir de:

- La semilla común inmutable `SEED-3.md`.
- Los contratos heredados de E1/E2.
- Las decisiones E3-ENC-01, E3-AUD-01, E3-LOAD-01 y E3-DEP-01.
- La Constitución Spec Kit v1.2.0.

La autorización se limitó a la especificación inicial y sus artefactos de calidad asociados.

#### 8.2. Artefactos generados

Gemini reportó la creación de:

| Archivo | Función |
|---|---|
| `.specify/feature.json` | Metadatos de la funcionalidad activa |
| `specs/003-shift-bank-stage3/spec.md` | Especificación funcional E3 |
| `specs/003-shift-bank-stage3/checklists/requirements.md` | Checklist de calidad de requisitos |

Los archivos `plan.md`, `research.md`, `data-model.md`, `tasks.md` y los contratos API permanecieron sin generar, según el reporte.

El archivo `feature.json` debe registrarse como artefacto auxiliar del framework, no como especificación Markdown para la dimensión D3.

#### 8.3. Métricas preliminares reportadas

| Métrica | Valor |
|---|---:|
| Historias de usuario | 5 |
| Escenarios de aceptación | 33 |
| Requisitos funcionales | 32 |
| Criterios de éxito | 10 |
| Casos límite | 10 |
| Criterios del checklist | 16 |
| Ambigüedades declaradas | 0 |
| Modificaciones inesperadas declaradas | 0 |

Distribución reportada de requisitos:

- FR-001–FR-008: cifrado y gestión de claves.
- FR-009–FR-012: persistencia y exactitud financiera.
- FR-013–FR-021: auditoría transaccional.
- FR-022–FR-026: pruebas de carga.
- FR-027–FR-032: despliegue y verificación operacional.

**Procedencia:** cifras declaradas por Gemini. No verificadas todavía mediante lectura directa de los artefactos.

#### 8.4. Decisiones incorporadas según Gemini

El agente afirmó haber incorporado:

1. Cifrado de aplicación entre React y FastAPI.
2. Cifrado autenticado de importes financieros persistidos.
3. Conservación de operaciones exactas con `Decimal`.
4. Registro de auditoría encadenado y verificable.
5. Reconocimiento de las limitaciones de detección de truncamiento.
6. Pruebas Locust con parámetros comunes.
7. Despliegue Docker Compose mediante HTTPS.
8. Preservación de funcionalidades heredadas.

Estas afirmaciones requieren contrastarse contra el contenido real de `spec.md`.

#### 8.5. Evaluación humana preliminar

**Resultado: PENDIENTE DE REVISIÓN DOCUMENTAL.**

La ejecución parece respetar la separación entre especificación e implementación.

Sin embargo, no se autoriza todavía la siguiente fase porque el investigador no ha revisado directamente los requisitos, escenarios ni checklist.

Se establece como condición de aprobación:

- Verificar cobertura de los requisitos aprobados.
- Evaluar verificabilidad y consistencia interna.
- Identificar posibles requisitos no autorizados.
- Comprobar compatibilidad con E1/E2.
- Revisar límites reales de integridad y cifrado.
- Comprobar que el checklist no sustituya la revisión humana.
- Verificar el alcance real de los cambios en el repositorio.

#### 8.6. Evidencia y telemetría

**Disponible:** Resumen del agente sobre generación de artefactos.

**Pendiente:** Archivos completos, diff Git, transcript original, versión/modelo efectivo, estadísticas de tokens, llamadas a herramientas y tiempo de ejecución.

No se asignan valores de D1–D3 con base únicamente en el resumen.

#### 8.7. Próximo punto de control

**Interacción siguiente:** H2-04 — Auditoría humana de la especificación.

**Estado:** NO GO para planificación técnica hasta completar la revisión.

**Restricciones:** Sin implementación, modificación de código, pruebas, migraciones ni despliegue.

---

---

## 9. Hito 2 — Auditoría humana de la primera especificación

### Interacción H2-04 — Revisión de `spec.md` y `requirements.md`

**Fecha:** 2026-11-15  
**Agente evaluado:** Gemini CLI  
**Herramienta SDD:** GitHub Spec Kit  
**Estado:** Revisión completada; correcciones documentales pendientes.

### 9.1. Evidencia recibida

Se recibieron y examinaron directamente los archivos generados por Gemini:

- `specs/003-shift-bank-stage3/spec.md`
- `specs/003-shift-bank-stage3/checklists/requirements.md`

La evaluación se realizó sobre el contenido de los archivos y no únicamente sobre el resumen proporcionado por el agente.

### 9.2. Métricas documentales verificadas

| Métrica | Resultado |
|---|---:|
| Requisitos funcionales | 32 |
| Historias de usuario | 5 |
| Escenarios de aceptación | 34 |
| Criterios de éxito | 10 |
| Casos límite | 10 |
| Criterios del checklist | 16 |
| Checklist marcado por Gemini | 16/16 |
| Líneas físicas de `spec.md` | 226 |
| Líneas físicas de `requirements.md` | 37 |

**Discrepancia encontrada:** Gemini reportó 33 escenarios, mientras que el archivo contiene 34.

La distribución verificada es: cifrado 7, auditoría 8, carga 6, despliegue 7 y compatibilidad 6.

Los conteos de líneas corresponden a los archivos adjuntos y no constituyen todavía el inventario final de especificaciones D3.

### 9.3. Integridad de los archivos examinados

Hashes SHA-256 de las copias adjuntas:

`spec.md`:

`59498c32b98e03bc17fd254879d71b86328c315404cb262cbaa57d40d0b3fa73`

`requirements.md`:

`b0c8e439f1cc2c61264114ade2e292ee9aebf1d81d65df8051ac427c99bee198`

Estos hashes identifican las copias examinadas. No sustituyen una verificación independiente de los archivos locales de Windows.

### 9.4. Hallazgos de revisión

| ID | Descripción | Clasificación |
|---|---|---|
| H2-04-01 | Falta contrato explícito de migración segura E2 → E3 | Especificación incompleta |
| H2-04-02 | Falta prueba explícita de autorización del verificador de auditoría | Seguridad / verificabilidad |
| H2-04-03 | Afirmaciones excesivas sobre inmutabilidad, no repudio y cumplimiento regulatorio | Precisión técnica |
| H2-04-04 | Ambigüedad entre distribución configurada y observada de carga | Medición |
| H2-04-05 | Estados heredados no completamente contrastados con E2 | Compatibilidad |
| H2-04-06 | Frontera de cifrado de respuestas insuficientemente explicitada | Alcance de requisitos |
| H2-04-07 | Checklist autoaprobado sin justificar algunas excepciones técnicas | Calidad documental |
| H2-04-08 | Conteo de escenarios reportado incorrectamente | Exactitud de métricas |

### 9.5. Evaluación del investigador

**Resultado: NO GO para planificación técnica.**

Se considera que la especificación tiene una estructura adecuada, pero debe corregirse antes de convertirse en el contrato aprobado para implementación.

No se ha observado código E3 defectuoso ni se han ejecutado pruebas funcionales de E3 durante esta revisión.

Los hallazgos corresponden exclusivamente a la calidad y precisión de los artefactos de especificación.

### 9.6. Decisión de intervención

Se autoriza una revisión documental limitada a:

- `spec.md`
- `checklists/requirements.md`

Se deben preservar los requisitos correctos, los identificadores cuando sea posible y todas las decisiones previamente aprobadas.

La siguiente revisión comprobará que las correcciones no introduzcan requisitos nuevos sin justificación.

### 9.7. Implicaciones para las métricas

**D1 — Esfuerzo y consumo:** Pendiente de extracción desde transcript y estadísticas de Gemini.

**D2 — Calidad de código:** No aplica todavía a la revisión de especificaciones; la medición E3 se realizará en los hitos correspondientes.

**D3 — Especificaciones:** Se verificaron conteos preliminares de archivos y requisitos. Se deberá conservar la versión inicial y la versión corregida para analizar evolución documental.

**D4 — Expectativa funcional:** Se verificó preliminarmente la correspondencia de las cuatro capacidades principales con los requisitos. El cumplimiento funcional de la aplicación no ha sido evaluado.

**D5 — Retroalimentación:** Se registraron ocho hallazgos de revisión agrupados en una intervención humana. Su contabilización definitiva deberá distinguir hallazgos, mensajes del investigador y correcciones efectuadas por el agente.

No se debe confundir una intervención con ocho prompts ni con ocho correcciones de código.

### 9.8. Próximo punto de control

**Interacción:** H2-05 — Corrección de la especificación.

**Autorizado:** Modificar únicamente los dos documentos de especificación indicados.

**No autorizado:** Código, tests, dependencias, migraciones, planificación técnica o despliegue.

**Estado:** MILESTONE 2 — CORRECCIONES DOCUMENTALES PENDIENTES.

---

---

## 10. Hito 2 — Corrección de la especificación funcional

### Interacción H2-05 — Respuesta a la auditoría humana

**Fecha del registro recibido:** 2026-11-16 (según nombre del transcript; hora efectiva por verificar)  
**Agente evaluado:** Gemini CLI  
**Herramienta SDD:** GitHub Spec Kit  
**Estado:** Correcciones ejecutadas; validación documental pendiente.

### 10.1. Objetivo

Corregir los ocho hallazgos identificados durante la auditoría humana H2-04, preservando las decisiones funcionales aprobadas y evitando cualquier modificación de código o implementación.

El investigador autorizó exclusivamente la modificación de:

- `specs/003-shift-bank-stage3/spec.md`
- `specs/003-shift-bank-stage3/checklists/requirements.md`

### 10.2. Operaciones observadas

El transcript registra operaciones de lectura y escritura sobre los dos documentos autorizados.

Gemini reportó las siguientes modificaciones:

| Archivo | Operación registrada |
|---|---|
| `spec.md` | WriteFile aceptado (+234 / -226) |
| `checklists/requirements.md` | WriteFile aceptado (+43 / -37) |

Estas cifras corresponden a la operación reportada por la herramienta y no deben interpretarse automáticamente como líneas nuevas o modificadas definitivas para D3.

### 10.3. Correcciones declaradas por Gemini

| Hallazgo | Corrección reportada |
|---|---|
| H2-04-01 | Incorporación de migración segura, atómica e idempotente de E2 a E3 |
| H2-04-02 | Protección administrativa del verificador de auditoría |
| H2-04-03 | Eliminación de afirmaciones excesivas sobre no repudio y cumplimiento regulatorio |
| H2-04-04 | Separación entre mezcla configurada y observada de carga; clasificación de errores |
| H2-04-05 | Revisión de estados de transferencias y programaciones heredadas |
| H2-04-06 | Delimitación del cifrado de aplicación y protección HTTPS de respuestas |
| H2-04-07 | Justificación de restricciones tecnológicas en el checklist |
| H2-04-08 | Corrección del conteo de requisitos y escenarios |

La aplicación efectiva de estas correcciones se encuentra pendiente de comprobación independiente.

### 10.4. Métricas documentales reportadas

| Métrica | Inicial | Corregida |
|---|---:|---:|
| Requisitos funcionales | 32 | 35 |
| Escenarios de aceptación | 34 | 38 |
| Historias de usuario | 5 | 5 |
| Criterios de éxito | 10 | 10 |
| Casos límite | 10 | 11 |

Distribución final reportada:

- Cifrado y gestión de claves: 8 requisitos.
- Persistencia y migración: 5 requisitos.
- Auditoría: 10 requisitos.
- Pruebas de carga: 6 requisitos.
- Despliegue: 6 requisitos.

**Total reportado:** 35 requisitos funcionales.

### 10.5. Limitaciones de verificación

Durante la ejecución se observaron comandos de conteo bloqueados por restricciones del entorno.

Las búsquedas alternativas no encontraron coincidencias, por lo que el transcript no proporciona una comprobación independiente satisfactoria de los conteos finales.

La salida de `git status --short` fue `?? ./`, insuficiente para establecer mediante Git que solo se modificaron los dos documentos permitidos.

Gemini declaró que no modificó archivos ajenos al alcance autorizado, pero dicha afirmación permanece pendiente de comprobación independiente.

### 10.6. Evaluación preliminar del investigador

**Resultado: PENDIENTE DE VERIFICACIÓN.**

La intervención parece haber atendido las observaciones principales de H2-04.

No obstante, se requiere comparar los archivos iniciales y corregidos antes de aprobar el contrato funcional.

No se autorizan nuevas modificaciones ni el inicio de planificación técnica hasta completar esa revisión.

### 10.7. Implicaciones experimentales

**D1:** La interacción forma parte del consumo de Gemini en E3. Tokens, tiempo y llamadas a herramientas se extraerán de los registros originales.

**D2:** No se realizó evaluación estática del código E3.

**D3:** Se registra una nueva revisión de dos documentos de especificación, con variaciones de volumen pendientes de medición directa.

**D4:** Las correcciones buscan mejorar la cobertura y verificabilidad de los requisitos, pero no demuestran cumplimiento funcional del software.

**D5:** Se registra una intervención correctiva humana relativa a ocho hallazgos documentales. No equivale a ocho prompts independientes ni a ocho correcciones de código.

### 10.8. Próximo punto de control

**Actividad:** Verificación independiente de las especificaciones corregidas.

**Archivos requeridos:**

- `spec.md` corregido.
- `requirements.md` corregido.

**Decisión de aprobación:** Pendiente.

**Estado:** HITO 2 — ESPECIFICACIÓN REVISADA, AÚN NO APROBADA.

---

---

## 11. Hito 2 — Validación independiente de la especificación corregida

### Interacción H2-06 — Revisión documental final

**Fecha:** 2026-11-15  
**Herramienta:** GitHub Spec Kit  
**Agente evaluado:** Gemini CLI  
**Responsable de revisión:** Investigador, asistido por ChatGPT  
**Resultado:** GO para planificación técnica.

### 11.1. Evidencia examinada

Se compararon las versiones originales y corregidas de:

- `specs/003-shift-bank-stage3/spec.md`
- `specs/003-shift-bank-stage3/checklists/requirements.md`

Se verificaron mediante lectura directa, conteo programático y comparación de contenido.

### 11.2. Métricas verificadas

| Indicador | Inicial | Corregido |
|---|---:|---:|
| Requisitos funcionales | 32 | 35 |
| Escenarios de aceptación | 34 | 38 |
| Historias de usuario | 5 | 5 |
| Criterios de éxito | 10 | 10 |
| Casos límite | 10 | 11 |
| Líneas de especificación | 226 | 234 |
| Líneas de checklist | 37 | 43 |

Los 35 identificadores FR son continuos, sin duplicados ni saltos.

Los conteos anteriores se refieren exclusivamente a estos dos documentos, no a la totalidad futura de especificaciones D3.

### 11.3. Comparación documental

Para `spec.md` se observaron:

- 174 líneas conservadas sin modificación.
- 4 líneas insertadas sin reemplazar contenido anterior.
- 52 líneas anteriores sustituidas por 56 líneas nuevas.
- Variación neta: +8 líneas físicas.

Para `requirements.md`:

- 33 líneas conservadas.
- 4 líneas sustituidas por 10 líneas.
- Variación neta: +6 líneas físicas.

Estas cifras proceden de una comparación de contenido entre ambas versiones, independiente de los contadores de operaciones `WriteFile` de Gemini.

### 11.4. Identificación criptográfica de las versiones

SHA-256 de las copias corregidas examinadas:

`spec.md`:

`abb586f37aa9ab1f718e8ebd009792c3f871664f44ca61765addce`

`requirements.md`:

`dd3413bef02c14eeaedca1303bf26bac30cbd495ea92eba363105d306e5db173`

Los hashes permiten identificar las copias revisadas y compararlas posteriormente con los artefactos locales.

### 11.5. Resultado de la auditoría

Los ocho hallazgos de H2-04 se consideran resueltos documentalmente o suficientemente aclarados para continuar.

Se verificó la incorporación de:

- Migración cifrada, idempotente y con rollback.
- Protección administrativa del verificador de auditoría.
- Limitación explícita de las garantías criptográficas.
- Separación de distribución configurada y medida en Locust.
- Clasificación de errores inesperados.
- Correcciones en el modelo documental de estados.
- Frontera de cifrado entre cliente, backend y HTTPS.
- Reconciliación de los conteos de requisitos y escenarios.

La verificación no constituye evidencia de implementación funcional.

### 11.6. Observaciones no bloqueantes

**OBS-H2-06-A:** La planificación debe considerar también la migración de los límites dinámicos financieros, en cumplimiento de FR-010 y FR-013.

**OBS-H2-06-B:** El checklist debe precisar la procedencia de SQLite como parte de la arquitectura heredada y del protocolo E3, no como requisito textual explícito de SEED-3.md.

**OBS-H2-06-C:** Las afirmaciones sobre estados heredados deberán trazarse contra los contratos originales de E2 durante la planificación.

Estas observaciones no requieren una nueva ronda de especificación funcional.

### 11.7. Decisión humana

**GO — Especificación funcional E3 aprobada para planificación.**

Se autoriza la generación de artefactos técnicos mediante el flujo nativo de GitHub Spec Kit.

No se autoriza todavía implementación, generación de tareas ejecutables, migración de bases de datos, instalación de dependencias ni despliegue.

### 11.8. Implicaciones para D1–D5

**D1:** La revisión y sus prompts deben atribuirse a las sesiones correspondientes. No se dispone todavía de telemetría completa validada.

**D2:** No se ha iniciado la medición de calidad del código E3.

**D3:** Se verificó una evolución de 32 a 35 requisitos y de 226 a 234 líneas físicas en `spec.md`, conservando las versiones inicial y corregida.

**D4:** La especificación cubre las cuatro capacidades principales, pero el cumplimiento funcional continúa sin evaluar.

**D5:** La intervención documental H2-05 queda registrada como una ronda correctiva de especificación, originada por ocho hallazgos de revisión. No se contabiliza como ocho correcciones de código ni como ocho mensajes independientes.

### 11.9. Próxima interacción

**H2-07 — Planificación técnica mediante `/speckit.plan`.**

Se autoriza únicamente la producción de artefactos técnicos y una corrección editorial del checklist.

**Estado:** HITO 2 — ESPECIFICACIÓN FUNCIONAL APROBADA; PLAN TÉCNICO PENDIENTE.

---

---

## 12. Hito 2 — Generación y revisión del plan técnico

### Interacción H2-07 — Ejecución de `/speckit.plan`

**Fecha de evidencia:** 2026-11-16  
**Herramienta SDD:** GitHub Spec Kit  
**Agente:** Gemini CLI  
**Estado:** Plan técnico generado; ajustes solicitados.

### 12.1. Objetivo

Generar los artefactos técnicos de Shift Bank E3 a partir de los 35 requisitos funcionales y 38 escenarios de aceptación aprobados.

Se autorizó exclusivamente la planificación documental mediante el flujo nativo de GitHub Spec Kit.

### 12.2. Evidencia recibida

Se recibieron dos archivos de transcript:

- `Pasted text(20261116-011200).txt`
- `Pasted text(20261116-011208).txt`

Ambos archivos contienen exactamente los mismos 74.715 bytes y comparten el SHA-256:

`e27f752a1378b26a37d72ba7d93dd6eb4079c0d89547365ca4212f3f646fde80`

**Regla de atribución:** Se consideran dos copias de una misma evidencia, no dos ejecuciones independientes. No deben duplicarse las métricas D1 ni D5.

### 12.3. Artefactos reportados

| Archivo | Resultado |
|---|---|
| `research.md` | Creado |
| `plan.md` | Creado |
| `data-model.md` | Creado |
| `contracts/api.md` | Creado |
| `quickstart.md` | Creado |
| `checklists/requirements.md` | Corrección editorial autorizada |

El transcript registra cinco operaciones `WriteFile` y una edición del checklist, además de lecturas de documentos y llamadas al shell.

No se observa autorización ni ejecución de implementación.

### 12.4. Arquitectura propuesta

**Cifrado:** RSA-OAEP + AES-256-GCM para solicitudes del navegador, con claves efímeras y descifrado autorizado en FastAPI.

**Persistencia:** AES-256-GCM por campo sensible, con representación monetaria exacta mediante `Decimal`.

**Migración:** Conversión de información heredada de E2 utilizando transacciones SQLite.

**Auditoría:** Registros append-only, HMAC-SHA256, protección mediante triggers y verificación administrativa.

**Carga:** Locust con 30 usuarios, 5 usuarios/segundo y distribución objetivo de 60/30/10.

**Despliegue:** Docker Compose, Nginx, HTTPS local, persistencia SQLite y scheduler único.

Estas decisiones son propuestas de diseño documentadas; todavía no han sido implementadas ni verificadas experimentalmente.

### 12.5. Hallazgos de revisión humana

| ID | Hallazgo | Severidad |
|---|---|---|
| H2-07-01 | Secretos predeterminados reutilizables en quickstart | Alta |
| H2-07-02 | Benchmark de 60 s totales en lugar de 60 s estables | Alta |
| H2-07-03 | Detección incompleta de migración y campos omitidos | Alta |
| H2-07-04 | Garantía no demostrada de secuencias contiguas | Media-alta |
| H2-07-05 | Afirmaciones de rendimiento no sustentadas por mediciones E3 | Media |

### 12.6. Evaluación metodológica

Gemini completó la generación de los documentos previstos y reportó ausencia de riesgos técnicos.

La revisión humana identificó cinco problemas que no fueron reconocidos como pendientes en el informe del agente.

Esto demuestra la necesidad de verificar las decisiones técnicas antes de transformar el plan en tareas ejecutables.

**Resultado: NO GO para generación de tareas.**

Se autoriza únicamente una corrección focalizada de los documentos de planificación E3.

### 12.7. Implicaciones para D1–D5

**D1:** La ejecución de `/speckit.plan` pertenece al esfuerzo de Gemini en E3. Las dos copias idénticas del transcript no representan sesiones distintas.

**D2:** No se han calculado medidas SonarQube ni evaluaciones de código E3.

**D3:** Se reportan cinco artefactos técnicos nuevos. Sus líneas y contenido definitivo deberán medirse sobre los archivos finales, sin confundir operaciones de escritura con líneas netas.

**D4:** No se ha demostrado todavía el funcionamiento de las capacidades propuestas.

**D5:** Se registra una revisión humana con cinco hallazgos técnicos. La intervención correctiva se contabilizará según la metodología común y no como cinco prompts independientes.

### 12.8. Próxima interacción

**H2-08:** Corrección focalizada del plan técnico.

**Autorizado:** Edición documental de artefactos técnicos E3.

**No autorizado:** Generación de tareas, implementación, instalación de dependencias, migraciones, carga o despliegue.

**Estado:** HITO 2 — PLAN TÉCNICO EN REVISIÓN.

---

---

## 13. Hito 2 — Corrección del plan técnico

### Interacción H2-08 — Resolución de cinco hallazgos

**Fecha:** 2026-11-16  
**Agente:** Gemini CLI  
**Herramienta:** GitHub Spec Kit  
**Estado:** GO para generación de tareas.

### 13.1. Evidencia

Transcript: `Pasted text(20261116-011929).txt`.

Se registraron cuatro archivos modificados:

- `quickstart.md`
- `data-model.md`
- `research.md`
- `plan.md`

Gemini reportó que no modificó código, pruebas, bases de datos, especificaciones funcionales aprobadas ni documentos históricos.

### 13.2. Correcciones realizadas

| Hallazgo | Resultado documentado |
|---|---|
| H2-07-01 — Secretos inseguros | Valores literales reemplazados por placeholders y procedimientos de generación aleatoria |
| H2-07-02 — Locust | Duración propuesta corregida a 66 s: 6 s nominales de ramp-up y 60 s estables |
| H2-07-03 — Migración | Verificación de múltiples campos, estados mixtos, valores nulos y ciphertext corrupto |
| H2-07-04 — Auditoría | Secuencias explícitas bajo transacción `BEGIN IMMEDIATE` y checkpoints externos |
| H2-07-05 — Evidencia | Retiro de afirmaciones de rendimiento no medido y ampliación de matriz de compatibilidad |

### 13.3. Observación metodológica

**OBS-H2-08-A:** Una duración fija de 66 segundos no garantiza por sí sola 60 segundos efectivos a plena concurrencia si el ramp-up tarda más de lo previsto.

La generación de tareas deberá exigir detectar el momento real en que se alcanzan los 30 usuarios y evaluar un intervalo estable completo de 60 segundos.

No se modifican los parámetros comunes del experimento.

### 13.4. Evaluación

La documentación de planificación presenta correcciones pertinentes respecto a los cinco hallazgos.

**Decisión:** GO para descomposición en tareas mediante `/speckit.tasks`, con la observación de temporización incorporada al siguiente prompt.

La aceptación es documental y no demuestra todavía que la arquitectura haya sido implementada o que los requisitos funcionales se cumplan.

### 13.5. Implicaciones D1–D5

- **D1:** Registrar esta interacción en la sesión correspondiente de Gemini.
- **D2:** Sin mediciones de calidad E3 todavía.
- **D3:** Cuatro artefactos técnicos revisados; registrar versiones y diferencias.
- **D4:** Cumplimiento de implementación aún no evaluado.
- **D5:** Una intervención correctiva humana que agrupó cinco hallazgos técnicos; no equivalen a cinco prompts independientes.

### 13.6. Próxima interacción

**H2-09:** Generación de `tasks.md` mediante GitHub Spec Kit.

**Permitido:** Descomposición documental de tareas.

**Prohibido:** Implementación y ejecución de pruebas.

**Estado:** HITO 2 — PLAN TÉCNICO APROBADO; TAREAS PENDIENTES.

---

---

## 14. Hito 2 — Generación de tareas y autorización de implementación

### Interacción H2-09 — Ejecución de `/speckit.tasks`

**Fecha de evidencia:** 2026-11-16  
**Agente:** Gemini CLI  
**Herramienta SDD:** GitHub Spec Kit  
**Resultado:** GO para iniciar implementación controlada.

### 14.1. Evidencia

Transcript recibido: `Pasted text(20261116-012307).txt`.

El agente ejecutó el flujo de descomposición de tareas de GitHub Spec Kit y generó:

`specs/003-shift-bank-stage3/tasks.md`

La operación `WriteFile` fue aceptada y reportó 193 líneas añadidas.

No se observó ejecución de `/speckit.implement` durante esta interacción.

### 14.2. Métricas reportadas

| Indicador | Resultado |
|---|---:|
| Tareas generadas | 38 |
| Identificadores | T001–T038 |
| Fases de desarrollo | 8 |
| Requisitos funcionales cubiertos | 35/35, según Gemini |
| Escenarios de aceptación cubiertos | 38/38, según Gemini |
| Historias de usuario | 5 |

Distribución:

| Fase | Tareas | Cantidad |
|---|---|---:|
| Setup | T001–T004 | 4 |
| Fundamentos | T005–T009 | 5 |
| US1 — Cifrado y persistencia | T010–T017 | 8 |
| US2 — Auditoría | T018–T023 | 6 |
| US3 — Locust | T024–T026 | 3 |
| US4 — Docker/HTTPS | T027–T032 | 6 |
| US5 — Compatibilidad | T033–T035 | 3 |
| Verificación final | T036–T038 | 3 |

### 14.3. Revisión metodológica

La estructura de tareas separa infraestructura, implementación, pruebas y verificaciones finales.

Se incorporaron tareas relacionadas con:

- Cifrado híbrido y persistencia autenticada.
- Migración segura de datos heredados.
- Auditoría transaccional y detección de manipulación.
- Pruebas de carga con medición de estado estable.
- Despliegue HTTPS.
- Regresiones heredadas.

Gemini reportó cobertura completa y ausencia de contradicciones. Estas afirmaciones serán contrastadas durante la ejecución mediante resultados observados.

### 14.4. Decisión humana

**GO — Descomposición de tareas aceptada para iniciar Hito 3.**

La implementación se autoriza de manera incremental y limitada a T001–T017.

Se exige preservar evidencia de pruebas, fallos, correcciones y modificaciones de archivos.

No se autoriza ejecutar todavía los hitos de auditoría completa, carga, despliegue ni evaluación final.

### 14.5. Estado de métricas

**D1:** Pendiente de consolidar tiempos, tokens y llamadas a herramientas de Gemini.

**D2:** Sin nueva evaluación estática del código E3.

**D3:** Se añade `tasks.md` al inventario de artefactos de especificación y planificación.

**D4:** No existe todavía evidencia de cumplimiento funcional de la implementación E3.

**D5:** Esta interacción corresponde a generación de tareas, no a una corrección de código. No se registran nuevos hallazgos correctivos humanos.

### 14.6. Siguiente interacción

**H3-01:** Implementación de infraestructura fundamental, cifrado y persistencia (T001–T017).

**Estado:** HITO 2 APROBADO — HITO 3 AUTORIZADO.

---

---

## 15. Hito 3 — Primera implementación de cifrado y persistencia

### Interacción H3-01 — Ejecución inicial de `/speckit.implement`

**Fecha local:** 2026-11-15  
**Agente:** Gemini CLI  
**Herramienta:** GitHub Spec Kit  
**Evidencia:** `Pasted text(20261116-014411).txt`  
**Resultado:** NO GO — Regresiones pendientes.

### 15.1. Alcance autorizado

Implementación limitada a las tareas T001–T017:

- Preparación y configuración del entorno.
- Infraestructura criptográfica.
- Cifrado híbrido React–FastAPI.
- Cifrado autenticado de información persistida.
- Migración segura de registros heredados.
- Pruebas funcionales de la primera historia de usuario.

Las tareas T018–T038 permanecieron fuera del alcance autorizado.

### 15.2. Línea base previa a modificaciones

| Verificación | Resultado observado |
|---|---|
| Backend pytest | 47/47 PASS |
| Frontend Vitest | 12/12 PASS |
| Frontend build | PASS |

Se observaron advertencias de permisos en `.pytest_cache`, sin impedir la ejecución inicial de las pruebas.

### 15.3. Implementación reportada

El agente introdujo componentes de cifrado RSA-OAEP y AES-256-GCM, persistencia cifrada, migración de SQLite y adaptación de solicitudes HTTP sensibles.

Archivos principales creados o modificados:

- `backend/requirements.txt`
- `backend/src/crypto.py`
- `backend/src/database.py`
- `backend/src/models.py`
- `backend/src/services.py`
- `backend/src/api.py`
- `backend/tests/conftest.py`
- `backend/tests/test_crypto.py`
- `backend/tests/test_migration.py`
- `frontend/src/crypto.ts`
- `frontend/src/crypto.test.ts`
- `frontend/src/types.ts`
- `frontend/src/services.ts`
- `specs/003-shift-bank-stage3/tasks.md`

Gemini marcó T001–T017 como completadas.

### 15.4. Resultados de verificación posteriores

| Prueba | Resultado |
|---|---:|
| Backend criptografía y migración | 16/16 PASS |
| Frontend Vitest | 13/13 PASS |
| Frontend build | PASS |
| Backend completo | 26 PASS / 37 FAIL |
| Total backend ejecutado | 63 pruebas |

Los resultados corresponden al transcript de ejecución de Gemini.

### 15.5. Incidencias y correcciones observadas

**INC-H3-01-A — Endpoint de clave pública no disponible.**

La prueba de `GET /api/crypto/public-key` recibió inicialmente HTTP 404. Después se incorporó el endpoint y las pruebas específicas pasaron.

**INC-H3-01-B — Error de compilación TypeScript.**

El uso de `global.fetch` en `crypto.test.ts` produjo el error `TS2304`. Gemini sustituyó la referencia por `globalThis.fetch`, obteniendo posteriormente un build exitoso.

**INC-H3-01-C — Diferencia de respuesta HTTP.**

Una prueba esperaba HTTP 422 para solicitudes en texto claro, mientras que el manejador de validaciones existente respondió HTTP 400. La aserción se ajustó para aceptar ambos códigos, conforme al requisito aprobado.

### 15.6. Hallazgo crítico de regresión

La ejecución completa de pytest produjo 37 pruebas fallidas.

Gemini atribuyó estas fallas a solicitudes heredadas en texto claro, incompatibles con los nuevos sobres criptográficos obligatorios.

Esta interpretación constituye un diagnóstico del agente y no una clasificación independiente de todas las fallas.

No se introdujo deliberadamente un mecanismo de aceptación de texto claro, según el reporte.

**Resultado de aceptación:** La implementación todavía no satisface el criterio de preservación de las pruebas heredadas.

### 15.7. Decisión humana

**NO GO para Hito 4.**

Se autoriza una iteración correctiva H3-02 destinada a recuperar la compatibilidad de pruebas sin debilitar el contrato criptográfico.

La adaptación de pruebas deberá limitarse al transporte cifrado y conservar las comprobaciones originales de comportamiento bancario.

No se autoriza omitir pruebas, introducir fallback en texto claro ni modificar requisitos aprobados.

### 15.8. Impacto en métricas experimentales

**D1 — Esfuerzo:** Registrar las ejecuciones, reintentos y uso de herramientas. No se han consolidado tokens ni duración total de sesión.

**D2 — Calidad de código:** La implementación existe

---

## 16. Hito 3 — Corrección de regresiones y recuperación funcional

### Interacción H3-02 — Corrección de compatibilidad E1/E2

**Fecha local:** 2026-11-15  
**Agente:** Gemini CLI  
**Herramienta SDD:** GitHub Spec Kit  
**Evidencia:** `Pasted text(20261116-015240).txt`  
**Resultado:** GO condicionado a comprobación de fidelidad del entorno de pruebas.

### 16.1. Objetivo

Resolver los 37 fallos encontrados durante la primera implementación del cifrado E3, conservando los requisitos de seguridad y los comportamientos funcionales heredados.

### 16.2. Clasificación de fallos

Gemini identificó dos causas principales:

| Categoría | Fallos | Descripción |
|---|---:|---|
| Incompatibilidad de transporte HTTP | 32 | Las pruebas heredadas enviaban JSON sin cifrar |
| Consultas SQL sobre datos cifrados | 5 | Las pruebas esperaban importes en texto claro |
| **Total** | **37** | |

### 16.3. Correcciones implementadas

**Archivo `backend/tests/conftest.py`**

Se añadió un adaptador de transporte exclusivo del entorno de pruebas que transforma solicitudes heredadas en sobres criptográficos válidos.

Se incorporó un mecanismo para enviar solicitudes deliberadamente sin cifrar durante pruebas negativas de seguridad.

También se creó un adaptador de conexiones SQLite para presentar valores descifrados a ciertas aserciones heredadas.

**Archivo `backend/tests/test_crypto.py`**

Se modificó la prueba negativa de solicitudes sin cifrar para evitar su transformación automática por el adaptador de pruebas.

**Archivo `backend/src/models.py`**

Se incorporó compatibilidad entre los nombres `code` y `mfa_code` para la confirmación MFA.

### 16.4. Resultados observados

| Verificación | Antes H3-02 | Después H3-02 |
|---|---:|---:|
| Backend completo | 26 PASS / 37 FAIL | 63 PASS / 0 FAIL |
| Frontend Vitest | 13 PASS | 13 PASS |
| Frontend build | PASS | PASS |

La ejecución final de pytest reportó **63 pruebas exitosas** y dos advertencias relacionadas con el entorno de pruebas.

Se recuperó la ejecución satisfactoria de las 47 pruebas backend heredadas, junto con las 16 pruebas E3 existentes.

### 16.5. Observación de calidad

**OBS-H3-02-A — Adaptadores de pruebas**

El adaptador global de transporte y el descifrado transparente de consultas SQLite pueden facilitar la reutilización de pruebas heredadas, pero también pueden ocultar diferencias entre el comportamiento real de producción y el entorno de pruebas.

Por tanto, la aprobación requiere conservar verificaciones independientes mediante:

- Solicitudes HTTP sin modificación automática.
- Consultas directas a SQLite sin adaptadores.
- Pruebas negativas de rechazo de texto claro.
- Validación estricta de credenciales MFA.

La recuperación de las pruebas heredadas no constituye por sí sola prueba exhaustiva de seguridad.

### 16.6. Decisión humana

**GO — Autorizar Hito 4 con validación previa obligatoria.**

El resultado de H3-02 es suficiente para avanzar a la implementación de la auditoría, siempre que se compruebe primero la fidelidad del entorno de pruebas.

El siguiente alcance autorizado comprende exclusivamente T018–T023.

No se autorizan todavía pruebas de carga, despliegue ni evaluación estática final.

### 16.7. Implicaciones para D1–D5

**D1:** Registrar las ejecuciones y correcciones efectuadas durante H3-02. El consumo de tokens y tiempo permanece pendiente de consolidación.

**D2:** No se dispone todavía de resultados finales de calidad estática de E3.

**D3:** No se modificaron las especificaciones funcionales aprobadas, según el registro. Se mantuvieron T001–T017 marcadas como completadas.

**D4:** La tasa observada de aprobación de la suite backend pasó de 26/63 a 63/63. La validación del transporte cifrado y del almacenamiento real requiere comprobaciones independientes adicionales.

**D5:** Se documenta una iteración correctiva humana, dos categorías de fallos y modificaciones en tres archivos. Los 37 fallos no representan necesariamente 37 defectos distintos.

### 16.8. Próxima interacción

**H4-01:** Verificación de adaptadores de pruebas e implementación de auditoría transaccional.

**Tareas autorizadas:** T018–T023, más correcciones estrictamente necesarias derivadas de la comprobación preliminar.

**Condición de cierre:** Auditoría funcional, verificable y atómica, con pruebas heredadas y nuevas exitosas.

**Estado:** HITO 3 ACEPTADO CON OBSERVACIÓN — HITO 4 AUTORIZADO.

---

---

## 17. Hito 4 — Implementación de auditoría transaccional

### Interacción H4-01 — Implementación de T018–T023

**Fecha local:** 2026-11-15  
**Agente:** Gemini CLI  
**Herramienta SDD:** GitHub Spec Kit  
**Evidencia:** `Pasted text(20261116-021020).txt`  
**Resultado:** Implementación ejecutada; validación focalizada pendiente.

### 17.1. Objetivo

Implementar el registro de auditoría criptográficamente encadenado, garantizando trazabilidad de operaciones financieras, atomicidad transaccional, rechazo seguro ante fallos de auditoría y verificación administrativa.

El alcance autorizado comprendió exclusivamente las tareas T018–T023, con correcciones limitadas de seguridad heredadas del Hito 3.

### 17.2. Verificaciones preliminares

Gemini incorporó dos pruebas criptográficas adicionales:

- Verificación del cifrado persistido mediante conexión SQLite directa.
- Validación de códigos MFA vacíos y contradictorios entre `code` y `mfa_code`.

Se modificó `MFACodeConfirm` para rechazar credenciales inconsistentes.

**Resultado observado:** 65/65 pruebas backend exitosas antes de incorporar las pruebas de auditoría.

### 17.3. Implementación realizada

Archivos principales creados o modificados:

| Archivo | Modificación |
|---|---|
| `backend/tests/test_audit.py` | Creación de 10 pruebas de auditoría |
| `backend/src/services.py` | Cadena HMAC, eventos de auditoría e integración transaccional |
| `backend/src/api.py` | Auditoría de transferencias y endpoints administrativos |
| `backend/src/database.py` | Configuración SQLite WAL y timeout |
| `backend/src/models.py` | Validación adicional de MFA |
| `backend/tests/test_crypto.py` | Dos pruebas de seguridad adicionales |
| `specs/003-shift-bank-stage3/tasks.md` | T018–T023 marcadas como completadas |

### 17.4. Evolución de resultados

| Ejecución | PASS | FAIL |
|---|---:|---:|
| Verificación preliminar backend | 65 | 0 |
| Primera ejecución de auditoría | 1 | 9 |
| Segunda ejecución de auditoría | 6 | 4 |
| Ejecución final de auditoría | 10 | 0 |
| Suite backend final | 75 | 0 |
| Suite frontend final | 13 | 0 |

**Compilación frontend:** PASS.

### 17.5. Incidencias observadas

**INC-H4-01-A — Bloqueos SQLite.**

La primera ejecución de las pruebas de auditoría presentó errores `database is locked`. Gemini incorporó configuración WAL y mayor tiempo de espera en las conexiones.

**INC-H4-01-B — Contaminación del registro de auditoría.**

Una prueba insertó un registro artificial con identificador `999999`, provocando discontinuidad de secuencias y fallos de integridad en pruebas posteriores.

Gemini reestructuró las pruebas y obtuvo posteriormente resultados satisfactorios.

**INC-H4-01-C — Simulación de fallo de auditoría.**

La prueba inicial de rollback esperaba HTTP 500, pero recibió HTTP 200, indicando que la inyección del fallo no interrumpía efectivamente la operación evaluada.

El archivo de pruebas se modificó posteriormente. La versión final reportó cumplimiento, pero es necesario verificar que la simulación alcance el camino de ejecución real.

### 17.6. Resultados declarados por Gemini

El agente reportó haber implementado:

- Registros append-only mediante HMAC-SHA256.
- Secuencias contiguas de auditoría.
- Escritura atómica de operaciones financieras y eventos.
- Registro separado de operaciones rechazadas.
- Protección mediante triggers SQLite.
- Verificación administrativa autorizada.
- Detección de modificaciones y truncamientos con checkpoint externo.
- Pruebas de concurrencia.
- Protección contra exposición de secretos.

Los resultados finales de las pruebas están respaldados por las salidas de ejecución del transcript. La cobertura exhaustiva de todos los requisitos todavía requiere validación focalizada.

### 17.7. Observaciones de revisión

**OBS-H4-01-A — Cifrado fail-closed.**

En evidencia de implementación anterior se observó un helper `encrypt_val()` que retornaba el valor original ante una excepción criptográfica.

Debe comprobarse que ninguna ruta actual conserve ese comportamiento, especialmente durante escrituras financieras.

**OBS-H4-01-B — Fidelidad de las pruebas.**

Las sucesivas reescrituras de `test_audit.py` resolvieron los fallos reportados, pero es necesario confirmar que no se hayan eliminado verificaciones relevantes.

**OBS-H4-01-C — Cobertura transaccional.**

La aprobación requiere comprobar que cada operación financiera pertinente produzca su evento de auditoría dentro de los límites transaccionales establecidos.

**OBS-H4-01-D — Checkpoints externos.**

La prueba de truncamiento debe distinguir entre conservar temporalmente un checkpoint durante una prueba y disponer de un mecanismo operacional para mantener un checkpoint confiable fuera de la base evaluada.

### 17.8. Decisión humana

**GO para H4-02: verificación focalizada y corrección de seguridad.**

No se autoriza todavía iniciar las pruebas de carga.

La aprobación del Hito 4 queda condicionada a validar el comportamiento fail-closed, la integridad de las pruebas y la cobertura efectiva de auditoría.

### 17.9. Implicaciones D1–D5

**D1 — Esfuerzo:** Registrar la secuencia de ejecuciones y correcciones de Gemini. Tokens y duración total pendientes de consolidación.

**D2 — Calidad:** Todavía no se ha ejecutado la evaluación estática definitiva.

**D3 — Artefactos:** Actualización de `tasks.md`; las especificaciones aprobadas permanecen sin modificar según el reporte.

**D4 — Funcionalidad:** El backend alcanzó 75/75 pruebas exitosas; frontend 13/13 y compilación exitosa. La evaluación de requisitos adicionales continúa pendiente.

**D5 — Correcciones:** Se observaron varias iteraciones internas del agente para resolver fallos de concurrencia, pruebas y validación. No deben contabilizarse los nueve fallos iniciales como nueve defectos distintos sin clasificación causal.

### 17.10. Próxima interacción

**H4-02:** Auditoría final de seguridad y validez de pruebas.

**Permitido:** Verificación y correcciones focalizadas de Hitos 3 y 4.

**No permitido:** Locust, Docker, SonarQube o evaluación final.

**Estado:** HITO 4 IMPLEMENTADO — APROBACIÓN PENDIENTE.

---

---

## 18. Hito 4 — Verificación correctiva de seguridad

### Interacción H4-02 — Cifrado fail-closed y revisión de auditoría

**Fecha local de ejecución:** 2026-11-15  
**Agente:** Gemini CLI  
**Herramienta SDD:** GitHub Spec Kit  
**Evidencia:** `Pasted text(20261116-021641).txt`  
**Resultado:** GO para Hito 5.

### 18.1. Objetivo

Verificar las garantías de seguridad de los Hitos 3 y 4, especialmente el comportamiento fail-closed del cifrado, la integridad de las pruebas de auditoría y la preservación de los requisitos bancarios heredados.

### 18.2. Hallazgo y corrección principal

Se confirmó que `backend/src/services.py` contenía una implementación de `encrypt_val()` que capturaba excepciones criptográficas y devolvía el valor original sin cifrar.

Este comportamiento representaba un defecto de seguridad: bajo fallos de cifrado, podía permitirse la persistencia de información en texto claro.

**Corrección observada:** Gemini eliminó el bloque de captura y el retorno de texto claro, permitiendo que las excepciones se propaguen.

Se añadieron pruebas de fallo de cifrado y rechazo de ciphertext corrupto.

### 18.3. Archivos modificados observados

| Archivo | Cambios |
|---|---|
| `backend/src/services.py` | Eliminación del fallback a texto claro |
| `backend/tests/test_crypto.py` | Dos nuevas pruebas negativas de seguridad |

El informe de Gemini también describe verificaciones de aislamiento y cobertura de `test_audit.py`. No se observa una nueva operación de escritura de dicho archivo en esta interacción; esas afirmaciones deben distinguirse de las modificaciones directamente evidenciadas.

### 18.4. Incidencia durante las pruebas

**INC-H4-02-A — Inyección incorrecta de fallo.**

La primera ejecución de la nueva prueba falló porque intentó aplicar un monkeypatch sobre un atributo inexistente en el módulo `api`.

Gemini corrigió la inyección para utilizar las funciones realmente importadas en los módulos afectados.

Después de la corrección, las pruebas criptográficas finalizaron satisfactoriamente.

### 18.5. Resultados observados

| Verificación | Resultado |
|---|---:|
| Pruebas criptográficas | 17 PASS |
| Pruebas de auditoría | 10 PASS |
| Suite backend completa | 77 PASS / 0 FAIL |
| Frontend Vitest | 13 PASS / 0 FAIL |
| Compilación frontend | PASS |

Persistieron dos advertencias relacionadas con permisos de `.pytest_cache`, sin impedir el resultado final de pytest.

### 18.6. Garantías evaluadas

**Cifrado en reposo:** Se observó la eliminación del mecanismo que devolvía texto claro ante errores de cifrado.

**Rollback financiero:** La nueva prueba inyectó un fallo criptográfico y verificó que el balance almacenado no cambiara.

**Persistencia:** La prueba inspeccionó directamente SQLite para comprobar que los balances y montos de transferencias existentes permanecieran cifrados.

**Auditoría:** Las 10 pruebas existentes finalizaron correctamente.

**Truncamiento:** Gemini reportó correctamente que la detección de eliminación de registros finales depende de un checkpoint externo confiable. La existencia de un mecanismo operacional persistente para custodiar esos checkpoints no quedó demostrada mediante una prueba nueva en esta interacción.

### 18.7. Limitaciones registradas

**OBS-H4-02-A:** La evidencia directa de la nueva prueba de persistencia se concentra en balances y montos de transferencias. La cobertura de todos los campos sensibles fue declarada por Gemini, pero no constituye una comprobación independiente completa.

**OBS-H4-02-B:** El transcript no demuestra una nueva ampliación de pruebas de manipulación, reordenamiento o eliminación de registros de auditoría en bases aisladas durante H4-02.

Estas limitaciones se conservan para la evaluación final y no se presentan como garantías verificadas exhaustivamente.

### 18.8. Decisión humana

**GO — Hito 4 aprobado para continuar.**

La eliminación del fallback inseguro y las pruebas de regresión exitosas permiten iniciar la siguiente capacidad funcional.

Se autoriza exclusivamente el Hito 5, correspondiente a T024–T026.

No se autoriza todavía despliegue Docker, ejecución de tareas posteriores ni evaluación final.

### 18.9. Implicaciones D1–D5

**D1 — Esfuerzo:** Registrar la interacción correctiva, las operaciones de edición y los reintentos. Tokens y tiempo total pendientes de consolidación.

**D2 — Calidad de código:** Se corrigió un defecto de seguridad identificado durante revisión. La evaluación estática final continúa pendiente.

**D3 — Especificaciones:** No se observaron modificaciones a las especificaciones funcionales aprobadas.

**D4 — Cumplimiento funcional:** 77/77 pruebas backend, 13/13 pruebas frontend y compilación exitosa. Estos resultados demuestran el estado de las suites ejecutadas, no una certificación exhaustiva de seguridad.

**D5 — Retroalimentación:** Una intervención correctiva humana H4-02; un defecto de fallback criptográfico corregido y una incidencia adicional durante la instrumentación de pruebas. Deben distinguirse intervenciones, defectos y reintentos internos del agente.

### 18.10. Próxima interacción

**H5-01:** Implementación y ejecución de pruebas de carga reproducibles con Locust.

**Tareas autorizadas:** T024–T026.

**Parámetros obligatorios:** 30 usuarios, 5 usuarios/s de ramp-up, 60 segundos efectivos de estado estable, distribución objetivo 60/30/10 y medición sobre endpoints HTTPS reales con cifrado de aplicación.

**Estado:** HITO 4 APROBADO — HITO 5 AUTORIZADO.

---

---

## 19. Registro de telemetría de Gemini CLI

### Interacción D1-01 — Cierre de sesión experimental

**Fuente:** Captura `image(20261116-022142).png`  
**Agente:** Gemini CLI  
**Herramienta SDD:** GitHub Spec Kit  
**Session ID:** `803a73df-1582-49fd-bc2b-126223295031`

### 19.1. Uso de herramientas

| Indicador | Valor |
|---|---:|
| Llamadas a herramientas | 207 |
| Exitosas | 205 |
| Fallidas | 2 |
| Tasa de éxito | 99,0% |
| Aprobaciones revisadas | 205 |
| Acuerdo del usuario | 100,0% |
| Líneas añadidas | 9.542 |
| Líneas eliminadas | 5.768 |
| Cambio neto reportable | +3.774 líneas |

Los cambios corresponden a la sesión completa y no representan exclusivamente código funcional nuevo.

### 19.2. Tiempo de ejecución

| Indicador | Duración |
|---|---|
| Tiempo total (Wall Time) | 1 h 57 min 33 s |
| Agente activo | 1 h 00 min 55 s |
| Tiempo de API | 46 min 58 s |
| Tiempo de herramientas | 13 min 56 s |
| Proporción API / herramientas | 77,1% / 22,9% |

El tiempo de API y el tiempo de herramientas son componentes del tiempo activo, no duraciones adicionales al tiempo total.

### 19.3. Consumo de modelos

| Modelo | Solicitudes | Input tokens | Cache reads | Output tokens |
|---|---:|---:|---:|---:|
| gemini-3.8-flash | 221 | 49.301.006 | 46.515.753 | 176.679 |
| gemini-3-flash-preview | 3 | 83.043 | 0 | 441 |
| **Total** | **224** | **49.384.049** | **46.515.753** | **177.120** |

Las lecturas de caché se registran como métrica independiente. No deben sumarse nuevamente a los tokens de entrada para calcular consumo total sin conocer la convención exacta del proveedor.

### 19.4. Alcance y atribución experimental

Esta captura corresponde a una sesión acumulativa que incluyó varias interacciones de especificación, planificación, implementación y corrección.

Por tanto:

- Los 207 llamados a herramientas no corresponden exclusivamente al Hito 4.
- El tiempo total de 1 h 57 min 33 s no debe atribuirse a una sola tarea.
- Los 224 requests son solicitudes a modelos, distintas de las llamadas a herramientas.
- Los valores de tokens deben conservarse separados por modelo y tipo de uso.
- No se debe sumar nuevamente esta sesión cuando se documenten sus interacciones individuales.

### 19.5. Impacto en D1–D5

**D1 — Esfuerzo:** Se dispone de telemetría de sesión directamente respaldada por la captura: duración, solicitudes, tokens, caché y llamadas a herramientas.

**D2 — Calidad de código:** La captura no proporciona métricas de calidad estática.

**D3 — Especificaciones:** Las líneas añadidas y eliminadas incluyen modificaciones de distintos tipos de archivos; no representan por sí solas volumen documental SDD.

**D4 — Cumplimiento:** La telemetría no demuestra cumplimiento funcional.

**D5 — Intervenciones:** Las 205 aprobaciones revisadas y las 207 llamadas a herramientas no equivalen al número de correcciones humanas. Estas se contabilizan mediante la bitácora de interacciones y hallazgos.

### 19.6. Continuidad

El identificador de sesión permite reanudar el contexto mediante:

`gemini --resume "803a73df-1582-49fd-bc2b-126223295031"`

**Estado:** TELEMETRÍA D1 REGISTRADA — HITO 5 PENDIENTE.

---

---

## 20. Hito 5 — Implementación y ejecución de pruebas de carga

### Interacción H5-01 — Benchmark Locust y corrección de concurrencia

**Fecha local:** 2026-11-15  
**Agente:** Gemini CLI  
**Herramienta SDD:** GitHub Spec Kit  
**Evidencia:** `Pasted text(20261116-025754).txt`  
**Estado:** Implementación completada; verificación final pendiente.

### 20.1. Objetivo

Implementar T024–T026: preparación de datos sintéticos, ejecución de Locust sobre HTTPS con cifrado de aplicación y preservación de resultados experimentales.

### 20.2. Artefactos

**Archivos nuevos:**

- `scripts/seed_load_db.py`
- `scripts/run_load_test.py`
- `backend/tests/locustfile.py`
- `backend/tests/test_load_seed.py`
- Reportes JSON, Markdown, HTML y CSV de Locust.

**Archivos modificados:**

- `backend/tests/conftest.py`
- `backend/src/api.py`
- `specs/003-shift-bank-stage3/tasks.md`

Se marcaron T024–T026 como completadas.

### 20.3. Preparación experimental

Se instaló Locust 2.47.0 y se preparó una base SQLite sintética aislada con seis cuentas y un saldo inicial agregado de COP 600.000.000,00.

La distribución configurada fue 60% consultas de balances, 30% consultas de historial y 10% transferencias internas cifradas.

El escenario empleó 30 usuarios virtuales y una tasa de incorporación de 5 usuarios por segundo.

### 20.4. Primer benchmark — Evidencia original preservada

| Indicador | Resultado |
|---|---:|
| Ramp-up | 5,03 s |
| Estado estable reportado | 60,00 s |
| Solicitudes | 7.394 |
| Throughput | 123,23 RPS |
| Lecturas p95 | 122,65 ms |
| Transferencias p95 | 270,38 ms |
| Errores inesperados | 0% |
| Integridad de auditoría | PASS — 755 registros |
| Conservación de fondos | FAIL |

**Defecto identificado:** El saldo agregado terminó en COP 600.000.800,00, una diferencia positiva de COP 800,00 respecto al valor inicial.

Gemini atribuyó la anomalía a una condición de carrera durante actualizaciones concurrentes de balances: se realizaban lecturas antes de adquirir el bloqueo de escritura SQLite.

El primer reporte se conservó como evidencia original, sin sobrescribirlo.

### 20.5. Corrección de concurrencia

Gemini modificó `backend/src/api.py` para utilizar `BEGIN IMMEDIATE` y volver a consultar los saldos dentro de la transacción antes de realizar las actualizaciones.

Durante la corrección aparecieron regresiones en los límites dinámicos y en el orden de validación de fondos insuficientes.

La secuencia observada incluyó:

- Cuatro fallos en pruebas de límites.
- Posteriormente, un fallo de regresión relacionado con fondos insuficientes.
- Correcciones adicionales hasta recuperar las 79 pruebas backend.

### 20.6. Segundo benchmark — Ejecución corregida

| Indicador | Resultado |
|---|---:|
| Ramp-up | 5,03 s |
| Estado estable reportado | 60,00 s |
| Solicitudes | 7.270 |
| Throughput | 121,17 RPS |
| Balance / historial / transferencias | 59,78% / 29,78% / 10,37% |
| Lecturas p50 / p95 / p99 | 17,20 / 118,79 / 212,18 ms |
| Transferencias p50 / p95 / p99 | 95,20 / 279,24 / 380,00 ms |
| Errores inesperados | 0% |
| Conservación de fondos | PASS |
| Auditoría | PASS — 781 registros |

Se cumplieron los tres umbrales de rendimiento reportados.

El saldo agregado final coincidió exactamente con los COP 600.000.000,00 iniciales.

**Reporte:** `benchmark_run_20261116_025418.json` y su correspondiente archivo Markdown.

### 20.7. Verificación de regresiones

| Prueba | Resultado |
|---|---:|
| Backend pytest | 79/79 PASS |
| Frontend Vitest | 13/13 PASS |
| Compilación frontend | PASS |

### 20.8. Observaciones de revisión

**OBS-H5-01-A — HTTPS:** El escenario Locust desactiva la verificación del certificado TLS mediante `self.client.verify = False`. Debe corregirse para confiar explícitamente en el certificado local.

**OBS-H5-01-B — Concurrencia:** El evento `spawning_complete` acredita la finalización del ramp-up, pero la evidencia presentada no demuestra por sí sola que 30 usuarios permanezcan activos durante todo el intervalo.

**OBS-H5-01-C — Clasificación:** En el segundo reporte, las cantidades 4.346 + 2.165 + 754 suman 7.265 solicitudes, frente a 7.270 reportadas. Deben identificarse las cinco solicitudes restantes.

**OBS-H5-01-D — Baseline:** La condición de elegibilidad del primer benchmark debe comprobar la ejecución realmente observada, no únicamente los parámetros solicitados.

**OBS-H5-01-E — Atomicidad:** La corrección de saldos concurrentes debe conservar la validez de los límites dinámicos dentro de las transacciones.

### 20.9. Decisión humana

**GO para H5-02 — Corrección focalizada de reproducibilidad y seguridad.**

Los resultados de rendimiento son favorables, pero no se aprueba todavía el Hito 5 de forma definitiva.

Se autoriza exclusivamente corregir los hallazgos documentados, preservar los reportes originales y ejecutar las verificaciones necesarias.

### 20.10. Implicaciones experimentales D1–D5

**D1 — Esfuerzo:** Se registran instalación de dependencias, exploración de herramientas, ejecuciones de benchmark y varias correcciones. Los tiempos y tokens de esta interacción deben extraerse de la telemetría correspondiente, sin duplicar la sesión anterior.

**D2 — Calidad:** Se corrigió una condición de carrera que afectaba la conservación monetaria. La evaluación estática permanece pendiente.

**D3 — Artefactos:** Se generaron scripts de carga y reportes; se actualizó `tasks.md`. No se reportan cambios a las especificaciones funcionales aprobadas.

**D4 — Cumplimiento:** El primer benchmark no conservó los fondos; el segundo sí. Ambos resultados deben mantenerse separados, sin sustituir retrospectivamente el resultado original.

**D5 — Correcciones:** Se documenta una intervención humana H5-02, una condición de carrera financiera identificada y las regresiones surgidas durante su reparación. Las ejecuciones internas del agente se distinguen de las intervenciones humanas.

### 20.11. Siguiente interacción

**H5-02:** Corrección final de TLS, medición de concurrencia, clasificación de solicitudes y criterios de validez del benchmark.

**Tareas autorizadas:** T024–T026 y correcciones directamente vinculadas al defecto de concurrencia.

**Estado:** HITO 5 EN VALIDACIÓN — HITO 6 BLOQUEADO.

---

---

## 21. Hito 5 — Validación final de reproducibilidad y concurrencia

### Interacción H5-02 — Corrección final del benchmark

**Fecha local:** 2026-11-15  
**Agente:** Gemini CLI  
**Herramienta SDD:** GitHub Spec Kit  
**Evidencia:** `Pasted text(20261116-030904).txt`  
**Resultado:** GO para Hito 6.

### 21.1. Objetivo

Corregir las observaciones de H5-01 relacionadas con verificación TLS, concurrencia sostenida, elegibilidad del benchmark, reconciliación de solicitudes y límites financieros bajo concurrencia.

### 21.2. Correcciones implementadas

| Hallazgo | Corrección |
|---|---|
| H5-01-A — TLS | Sustitución de `verify=False` por validación del certificado local |
| H5-01-B — Concurrencia | Muestreo de usuarios activos a 1 Hz durante la fase estable |
| H5-01-C — Solicitudes | Separación de tráfico bancario y solicitudes de inicialización |
| H5-01-D — Baseline | Criterios de elegibilidad basados en concurrencia, duración y métricas observadas |
| H5-01-E — Atomicidad | Revalidación de límites financieros dentro de `BEGIN IMMEDIATE` |

Se crearon dos pruebas de concurrencia para verificar conservación monetaria y cumplimiento de límites dinámicos.

### 21.3. Incidencias durante la corrección

La primera versión de las pruebas de concurrencia presentó errores de configuración.

Posteriormente, la prueba de límites falló porque asumía un consumo diario inicial de cero, mientras que la base de pruebas contenía transferencias previas.

Gemini corrigió la prueba considerando el consumo inicial existente y obtuvo finalmente ambas pruebas exitosas.

### 21.4. Tercer benchmark — Ejecución validada

**Artefacto:** `locust/reports/benchmark_run_20261116_030600.json`

| Indicador | Resultado |
|---|---:|
| Usuarios concurrentes | 30 |
| Ramp-up | 5,05 s |
| Estado estable | 60,00 s |
| Muestras de concurrencia | 60 |
| Usuarios mínimos/máximos observados | 30 / 30 |
| Solicitudes totales | 7.081 |
| Operaciones bancarias | 7.076 |
| Solicitudes de inicialización | 5 |
| Throughput | 118,02 RPS |
| Balance / historial / transferencias | 59,72% / 30,09% / 10,19% |
| Lecturas p50 / p95 / p99 | 18,17 / 138,84 / 238,01 ms |
| Transferencias p50 / p95 / p99 | 128,19 / 357,77 / 483,95 ms |
| Errores inesperados | 0,000% |
| Conservación de fondos | PASS |
| Integridad de auditoría | PASS — 757 registros |

Los tres umbrales de rendimiento fueron satisfechos.

La concurrencia fue corroborada mediante 60 muestras periódicas. Esta comprobación no equivale a observación continua sin intervalos, pero proporciona evidencia adicional respecto a la ejecución anterior.

### 21.5. Reconciliación de solicitudes

En la segunda ejecución se identificó que las cinco solicitudes no clasificadas como operaciones bancarias correspondían a consultas de clave pública realizadas durante la inicialización de usuarios.

En la tercera ejecución:

- 4.226 consultas de balances.
- 2.129 consultas de historial.
- 721 transferencias cifradas.
- 5 solicitudes de inicialización criptográfica.

**Total: 7.081 solicitudes.**

No quedaron solicitudes sin clasificar en el reporte.

### 21.6. Preservación de evidencia

Se reporta la conservación de los tres benchmarks:

| Ejecución | Resultado financiero | Evidencia |
|---|---|---|
| Intento 1 | FAIL — diferencia de +800 COP | `initial_benchmark_report` y archivo con fecha |
| Intento 2 | PASS | `benchmark_run_20261116_025418` |
| Intento 3 | PASS | `benchmark_run_20261116_030600` |

El primer resultado permanece registrado como evidencia de la condición de carrera identificada durante el experimento.

### 21.7. Verificación de regresiones

| Componente | Resultado |
|---|---|
| Backend pytest | 81/81 PASS |
| Frontend Vitest | 13/13 PASS |
| Compilación frontend | PASS |
| Nuevas pruebas de concurrencia | 2/2 PASS |

### 21.8. Decisión humana

**GO — Hito 5 aprobado.**

Se acepta la tercera ejecución como benchmark corregido y validado según los indicadores reportados.

La primera ejecución se conserva como evidencia del comportamiento inicial, sin sustituirla retrospectivamente.

Se autoriza continuar con el despliegue local Docker de T027–T032.

### 21.9. Implicaciones para D1–D5

**D1 — Esfuerzo:** Registrar ejecución adicional de benchmark, correcciones y reintentos. Evitar duplicar telemetría entre sesiones.

**D2 — Calidad:** Se reforzó la protección frente a condiciones de carrera y se añadieron pruebas. Análisis estático pendiente.

**D3 — Especificaciones:** Sin modificaciones reportadas a requisitos funcionales aprobados.

**D4 — Cumplimiento:** Los tres umbrales de carga fueron satisfechos en la tercera ejecución, junto con conservación monetaria y verificación de auditoría.

**D5 — Correcciones:** Una intervención humana H5-02, que agrupó cinco observaciones de revisión, y correcciones internas adicionales durante las pruebas.

### 21.10. Próxima interacción

**H6-01:** Implementación y verificación del despliegue local mediante Docker Compose.

**Tareas autorizadas:** T027–T032.

**Pendiente:** Compatibilidad final, calidad estática y consolidación experimental.

**Estado:** HITO 5 APROBADO — HITO 6 AUTORIZADO.


---

## 22. Hito 6 — Despliegue local mediante Docker Compose

### Interacción H6-01 — Implementación de T027–T032

**Fecha local:** 2026-11-15  
**Agente:** Gemini CLI  
**Herramienta SDD:** GitHub Spec Kit  
**Evidencia:** `Pasted text(20261116-032158).txt`  
**Resultado:** NO GO para Hito 7; corrección de seguridad requerida.

### 22.1. Objetivo

Implementar el despliegue local de Shift Bank E3 mediante Docker Compose, incluyendo Nginx, HTTPS, frontend React compilado, backend FastAPI, persistencia SQLite, gestión externa de secretos y scheduler único.

### 22.2. Tareas ejecutadas

| Tarea | Implementación | Estado reportado |
|---|---|---|
| T027 | Nginx HTTPS y proxy inverso | Completada |
| T028 | Dockerfiles backend/frontend | Completada |
| T029 | Docker Compose y persistencia | Completada |
| T030 | Endpoint `/api/health` | Completada |
| T031 | Scheduler de instancia única | Completada |
| T032 | Pruebas de despliegue | Completada |

**Tareas acumuladas:** 32/38.

### 22.3. Artefactos generados

- `deployment/nginx.conf`
- `deployment/Dockerfile.backend`
- `deployment/Dockerfile.frontend`
- `deployment/docker-compose.yml`
- `deployment/.env.example`
- `deployment/docker.env`
- `deployment/smoke_test.py`
- `backend/tests/test_health_scheduler.py`

Archivos modificados:

- `backend/src/api.py`
- `backend/src/scheduler.py`
- `specs/003-shift-bank-stage3/tasks.md`

### 22.4. Arquitectura desplegada

Se construyeron dos imágenes:

**Backend:** Python 3.13-slim, usuario no privilegiado y un único worker Uvicorn.

**Frontend:** compilación React mediante Node 20 y distribución estática con Nginx.

**Red:** Docker Compose con backend interno y Nginx expuesto en puertos locales 8080 (HTTP) y 8443 (HTTPS).

**Persistencia:** volumen denominado `shift_bank_data`.

Se observó la construcción exitosa de ambas imágenes y el arranque saludable de los dos contenedores.

### 22.5. Pruebas de despliegue

| Verificación | Resultado |
|---|---|
| Redirección HTTP → HTTPS | PASS |
| React servido por HTTPS | PASS |
| Endpoint de salud | PASS |
| Consulta de cuentas | PASS |
| Transferencia cifrada | PASS |
| Desafío y confirmación MFA | PASS |
| Verificación autorizada de auditoría | PASS |
| Rechazo de verificación no autorizada | PASS |
| Persistencia tras reinicio del backend | PASS |

**Resultado:** 9/9 verificaciones exitosas.

La prueba de persistencia confirmó conservación de saldos y cadena de auditoría tras reiniciar el contenedor backend.

### 22.6. Regresiones

| Verificación | Resultado |
|---|---|
| Backend pytest | 84/84 PASS |
| Frontend Vitest | 13/13 PASS |
| Compilación frontend | PASS |
| Nuevas pruebas health/scheduler | 3/3 PASS |

Se registró inicialmente un fallo en una prueba asíncrona del scheduler. Gemini corrigió la estructura del test y obtuvo resultados satisfactorios.

### 22.7. Hallazgos de revisión humana

**H6-01-01 — Secretos criptográficos reutilizables (severidad alta).**

Gemini introdujo valores literales conocidos para claves de almacenamiento, firma de auditoría y autorización administrativa en archivos de configuración.

También añadió valores predeterminados mediante interpolación de variables en Docker Compose.

Este comportamiento contradice el contrato de aprovisionamiento externo de secretos y puede permitir que el despliegue opere con credenciales conocidas.

Los valores concretos no se reproducen en esta bitácora.

**H6-01-02 — Prueba fail-closed insuficientemente aislada.**

La verificación de ausencia de secretos produjo HTTP 503, pero simultáneamente se observaron errores de acceso a la base de datos y de localización de la clave privada.

Por tanto, el resultado no demuestra de manera independiente el rechazo de cada secreto obligatorio.

**H6-01-03 — Aislamiento de persistencia.**

El smoke test confirmó persistencia después de reiniciar el backend. No quedó demostrada una recreación completa con volumen de prueba desechable y claves externas válidas.

El volumen persistente existente debe conservarse.

**H6-01-04 — Alcance del scheduler.**

La protección implementada utiliza una variable global del proceso. Es válida como mecanismo de control local bajo la configuración de un solo worker, pero no constituye una garantía distribuida frente a múltiples réplicas.

El despliegue deberá mantener explícitamente una sola instancia ejecutora y verificar que los reinicios no dupliquen pagos programados.

### 22.8. Decisión humana

**NO GO para Hito 7.**

Aunque las pruebas funcionales y el despliegue fueron exitosos, la configuración actual de secretos presenta un defecto de seguridad que debe resolverse.

Se autoriza una única iteración correctiva H6-02, limitada a la seguridad del despliegue, la verificación fail-closed y la persistencia.

No se autoriza ejecutar T033–T038 hasta completar esta validación.

### 22.9. Implicaciones experimentales D1–D5

**D1 — Esfuerzo:** Registrar construcción Docker, despliegue, ejecución de pruebas y correcciones del agente. Tokens y tiempos específicos pendientes de consolidación.

**D2 — Calidad:** Las pruebas automatizadas pasan, pero existe un hallazgo crítico de configuración de seguridad. El análisis estático final continúa pendiente.

**D3 — Artefactos:** Se incorporaron ocho archivos de despliegue/pruebas y se modificaron tres archivos existentes, según el transcript.

**D4 — Cumplimiento:** Se verificaron nueve escenarios de despliegue y 84 pruebas backend exitosas. El requisito de secretos externos no puede considerarse cumplido todavía.

**D5 — Retroalimentación:** Se registra una intervención humana correctiva asociada a cuatro hallazgos. No deben confundirse los hallazgos, las llamadas a herramientas y las correcciones internas del agente.

### 22.10. Próxima interacción

**H6-02:** Corrección de secretos y verificación final de seguridad del despliegue.

**Permitido:** Ajustes focalizados de T027–T032.

**Prohibido:** T033–T038, análisis SonarQube y modificaciones de etapas históricas.

**Estado:** HITO 6 IMPLEMENTADO — APROBACIÓN BLOQUEADA POR SEGURIDAD.

---



---

## 23. Hito 6 — Corrección de seguridad del despliegue

### Interacción H6-02 — Secretos externos y validación fail-closed

**Fecha local:** 2026-11-15  
**Agente:** Gemini CLI  
**Herramienta SDD:** GitHub Spec Kit  
**Evidencia:** `Pasted text(20261116-033846).txt`  
**Resultado:** Correcciones implementadas; aprobación final pendiente.

### 23.1. Objetivo

Resolver los cuatro hallazgos de H6-01 sobre credenciales reutilizables, verificaciones fail-closed, persistencia y ejecución única del scheduler.

### 23.2. Modificaciones realizadas

| Archivo | Modificación |
|---|---|
| `.gitignore` | Exclusión de secretos y claves privadas |
| `scripts/generate_deployment_secrets.py` | Generación aleatoria de credenciales |
| `deployment/.env.example` | Sustitución de secretos conocidos por placeholders |
| `deployment/docker.env` | Aprovisionamiento de nuevas claves |
| `deployment/docker-compose.yml` | Eliminación de fallbacks criptográficos y aislamiento de volumen |
| `deployment/smoke_test.py` | Eliminación de credencial administrativa predeterminada |
| `backend/src/api.py` | Comprobaciones adicionales de configuración criptográfica |
| `backend/tests/test_fail_closed_secrets.py` | Cuatro pruebas negativas nuevas |
| `backend/tests/test_health_scheduler.py` | Prueba de no duplicación de ejecuciones programadas |

### 23.3. Correcciones de seguridad

Se eliminaron los valores criptográficos predeterminados conocidos de Docker Compose y del smoke test.

Gemini implementó un generador que produce claves aleatorias y las almacena en `deployment/docker.env`, excluido de Git.

Se verificó el rechazo de operaciones cuando falta individualmente:

- `BANK_STORAGE_KEY`.
- `AUDIT_SIGNING_KEY`.
- `AUDIT_ADMIN_KEY`.
- `BANK_PRIVATE_KEY_PATH`.

**Resultado final:** 4/4 pruebas fail-closed exitosas.

### 23.4. Incidencias durante la ejecución

**INC-H6-02-A — Pruebas fail-closed iniciales.**

La primera ejecución produjo dos fallos. Gemini corrigió la respuesta ante ausencia de clave administrativa y añadió la comprobación de carga de clave privada en el endpoint de salud.

**INC-H6-02-B — Claves incompatibles con volumen anterior.**

Después de generar nuevas claves, el contenedor no pudo consultar correctamente la base SQLite previamente cifrada.

Gemini intentó cambiar el volumen mediante una variable de Compose, pero la inspección del contenedor mostró que seguía montado el volumen anterior.

Finalmente configuró un volumen aislado `shift_bank_h6_data` y recreó los contenedores.

El volumen original `shift_bank_data` permaneció presente según el listado de volúmenes.

**INC-H6-02-C — Prueba del scheduler.**

La nueva prueba de pagos recurrentes falló inicialmente por ausencia de `transfer_type` y posteriormente por problemas con la fecha de ejecución.

Tras corregir la preparación del escenario, las cuatro pruebas del módulo finalizaron satisfactoriamente.

### 23.5. Resultados finales

| Verificación | Resultado |
|---|---|
| Backend pytest | 89/89 PASS |
| Frontend Vitest | 13/13 PASS |
| Frontend build | PASS |
| Pruebas fail-closed | 4/4 PASS |
| Pruebas health/scheduler | 4/4 PASS |
| Smoke tests Docker | 9/9 PASS |
| Persistencia tras reinicio | PASS |
| Integridad de auditoría | PASS |

El despliegue funcionó con el nuevo volumen aislado y las nuevas claves.

### 23.6. Nuevo hallazgo de revisión

**H6-02-01 — Regeneración destructiva de claves (severidad alta).**

El generador utiliza escritura con modo `w` sobre `deployment/docker.env`, sobrescribiendo su contenido sin comprobar si existen claves previamente aprovisionadas.

El transcript registra dos ejecuciones del generador durante H6-02.

Esta operación puede reemplazar las claves necesarias para descifrar información persistida.

La conservación física de un volumen SQLite no garantiza su recuperabilidad criptográfica si se pierde el material de clave correspondiente.

No se dispone de evidencia de respaldo seguro y verificado de todas las claves anteriores.

**Corrección requerida:** Generación exclusivamente para archivos inexistentes, rechazo de sobrescritura accidental y documentación de continuidad de claves.

### 23.7. Decisión humana

**NO GO para Hito 7.**

Las correcciones de H6-02 resolvieron los problemas principales de credenciales reutilizables y las pruebas funcionales finalizaron exitosamente.

Sin embargo, el riesgo de sobrescritura de claves debe corregirse antes de aprobar definitivamente el despliegue.

Se autoriza una iteración focalizada H6-03, sin regenerar claves ni modificar volúmenes persistentes.

### 23.8. Implicaciones experimentales D1–D5

**D1 — Esfuerzo:** Registrar comandos Docker, regeneraciones de configuración, correcciones y pruebas. Telemetría específica pendiente.

**D2 — Calidad:** Se resolvieron problemas de configuración y se detectó un nuevo defecto potencial de continuidad criptográfica.

**D3 — Artefactos:** Se generaron archivos de seguridad y pruebas, sin cambios reportados en especificaciones funcionales aprobadas.

**D4 — Cumplimiento:** 89 pruebas backend, 13 frontend y nueve verificaciones Docker exitosas. La continuidad de claves requiere una comprobación adicional.

**D5 — Correcciones:** Una intervención humana H6-02 con cuatro hallazgos previos; se registra el nuevo hallazgo H6-02-01 y las incidencias internas observadas, sin confundirlas con intervenciones humanas independientes.

### 23.9. Próxima interacción

**H6-03:** Protección de continuidad criptográfica y verificación final del despliegue.

**Alcance autorizado:** Correcciones focalizadas T027–T032.

**Estado:** HITO 6 EN VERIFICACIÓN FINAL — HITO 7 BLOQUEADO.

---

---

## 24. Hito 6 — Verificación de continuidad criptográfica

### Interacción H6-03 — Protección de claves y cierre del despliegue

**Fecha local:** 2026-11-15  
**Agente:** Gemini CLI  
**Herramienta SDD:** GitHub Spec Kit  
**Evidencia:** `Pasted text(20261116-035029).txt`  
**SHA-256 del transcript:** `57c24072d8046e89308c97ea91406988ffe48e9e5ec7069dbed32f9293386dda`  
**Resultado:** GO para Hito 7.

### 24.1. Objetivo

Resolver el hallazgo H6-02-01, relacionado con la regeneración accidental de secretos criptográficos, y comprobar la continuidad de información cifrada durante reinicios y recreaciones de contenedores.

### 24.2. Modificaciones realizadas

| Archivo | Modificación |
|---|---|
| `scripts/generate_deployment_secrets.py` | Protección create-only, documentación de recuperación y permisos específicos por sistema operativo |
| `backend/tests/test_secret_generator.py` | Dos nuevas pruebas de generación y protección de secretos |

No se observaron modificaciones a las especificaciones funcionales aprobadas.

### 24.3. Corrección de seguridad

El generador de secretos fue modificado para rechazar, de forma predeterminada, la sobrescritura de `deployment/docker.env`.

La ejecución del comando sin argumentos confirmó el rechazo de sobrescritura y la conservación del archivo existente.

Se añadió una opción explícita `--force`, que permite reemplazar secretos de manera intencional. Su utilización sobre una base persistente sigue representando un riesgo operativo y no constituye un procedimiento aprobado de rotación criptográfica.

### 24.4. Permisos y recuperación

Gemini implementó controles diferenciados:

- **Windows:** configuración de permisos mediante `icacls`.
- **Linux/POSIX:** permisos de archivo `0600`.

La comprobación ejecutada en Windows devolvió `Success: True`.

Este resultado confirma la ejecución satisfactoria del comando, pero no representa una auditoría independiente exhaustiva de todas las entradas ACL existentes.

Se documentaron instrucciones para respaldar y restaurar las credenciales, las claves asimétricas y los certificados TLS.

No se observó la ejecución de una restauración real desde un respaldo externo.

### 24.5. Verificación de continuidad

Se ejecutaron las siguientes operaciones:

1. Intento de generación de secretos sobre un archivo existente.
2. Comprobación de permisos mediante `icacls`.
3. Reinicio del contenedor backend.
4. Recreación de los contenedores mediante Docker Compose.
5. Ejecución de pruebas funcionales de despliegue.

Las operaciones conservaron la configuración criptográfica existente.

El despliegue continuó funcionando con su almacenamiento persistente, sin regenerar las claves durante esta interacción.

### 24.6. Resultados de pruebas

| Verificación | Resultado |
|---|---|
| Generación create-only y permisos | 2/2 PASS |
| Backend pytest completo | 91/91 PASS |
| Frontend Vitest | 13/13 PASS |
| Compilación frontend | PASS |
| Smoke tests Docker | 9/9 PASS |
| Persistencia tras reinicio | PASS |
| Recreación de contenedores | PASS |
| Transferencia cifrada y MFA | PASS |
| Integridad de auditoría | PASS |

La prueba Docker reportó conservación exacta de COP 20.000.000,00 entre las dos cuentas evaluadas.

La verificación administrativa confirmó ocho registros de auditoría encadenados correctamente.

### 24.7. Preservación de evidencia

El transcript muestra la presencia de los siguientes reportes:

- `initial_benchmark_report.md`
- `benchmark_run_20261116_024200.md`
- `benchmark_run_20261116_025418.md`
- `benchmark_run_20261116_030600.md`

Corresponden a tres ejecuciones de benchmark, puesto que el primer reporte también se conserva como copia inicial identificada.

No se observó su sobrescritura durante H6-03.

### 24.8. Riesgos residuales

**OBS-H6-03-A:** La protección create-only evita sobrescrituras accidentales en condiciones normales; la opción `--force` sigue permitiendo reemplazar claves deliberadamente.

**OBS-H6-03-B:** La responsabilidad de conservar respaldos externos seguros permanece fuera de la automatización implementada.

**OBS-H6-03-C:** La protección del scheduler corresponde a un despliegue local de instancia única; no demuestra exclusión distribuida entre múltiples nodos.

Estas limitaciones no bloquean los requisitos definidos para el despliegue local E3.

### 24.9. Decisión humana

**GO — Hito 6 aprobado.**

Se considera resuelto el hallazgo de sobrescritura accidental de claves.

La evidencia de reinicio, recreación, pruebas funcionales y regresiones permite continuar con la verificación de compatibilidad heredada.

Se autoriza exclusivamente la ejecución de T033–T035.

### 24.10. Implicaciones experimentales D1–D5

**D1 — Esfuerzo:** Registrar la interacción H6-03, las llamadas a herramientas y los comandos Docker. Los tiempos y tokens específicos siguen pendientes de consolidación.

**D2 — Calidad:** Se incorporó una protección adicional para evitar pérdida accidental de claves. La evaluación estática final continúa pendiente.

**D3 — Artefactos:** Un archivo de utilidades modificado y un archivo de pruebas nuevo, según las operaciones registradas.

**D4 — Cumplimiento:** 91 pruebas backend, 13 frontend, compilación y nueve pruebas de despliegue exitosas. La continuidad criptográfica fue comprobada mediante reinicio y recreación con claves existentes.

**D5 — Retroalimentación:** Una intervención correctiva humana H6-03 para resolver un hallazgo de seguridad. Se diferencia de las operaciones internas del agente y de las dos pruebas añadidas.

### 24.11. Próxima interacción

**H7-01:** Verificación de compatibilidad funcional heredada de E1/E2.

**Tareas autorizadas:** T033–T035.

**Pendientes posteriores:** T036–T038, evaluación de calidad y consolidación experimental.

**Estado:** HITO 6 APROBADO — HITO 7 AUTORIZADO.

---

---

## 25. Hito 7 — Verificación de compatibilidad funcional heredada

### Interacción H7-01 — Ejecución de T033–T035

**Fecha local:** 2026-11-15  
**Agente:** Gemini CLI  
**Herramienta SDD:** GitHub Spec Kit  
**Evidencia:** `Pasted text(20261116-035814).txt`  
**Resultado:** Verificación funcional exitosa, con corrección de cobertura pendiente.

### 25.1. Objetivo

Verificar que las capacidades bancarias heredadas de E1/E2 continúan funcionando después de incorporar cifrado de aplicación, persistencia cifrada, auditoría transaccional y despliegue Docker.

### 25.2. Tareas ejecutadas

| Tarea | Actividad | Estado reportado |
|---|---|---|
| T033 | Ejecutar 47 pruebas backend heredadas | Completada |
| T034 | Verificar frontend y compilación | Completada |
| T035 | Ejecutar pruebas de integración entre funcionalidades heredadas y seguridad E3 | Completada |

Gemini marcó las tres tareas como completadas en `tasks.md`.

**Total acumulado:** 35/38 tareas marcadas.

### 25.3. Archivos creados o modificados

**Creado:**

- `backend/tests/test_inherited_compatibility.py`

**Modificado:**

- `specs/003-shift-bank-stage3/tasks.md`

No se observaron modificaciones de pruebas heredadas durante esta interacción.

### 25.4. Verificación del comportamiento heredado

La ejecución independiente de los cinco módulos de pruebas originales produjo:

**47/47 pruebas backend exitosas.**

Las capacidades cubiertas incluyen:

- Cuentas y balances iniciales.
- Transferencias internas.
- Historial de movimientos.
- MFA para operaciones sensibles.
- Límites dinámicos.
- Beneficiarios y transferencias ACH.
- Pagos recurrentes.
- Conservación de fondos.

Adicionalmente, Gemini implementó seis pruebas de integración entre funcionalidades heredadas y los mecanismos de seguridad E3.

### 25.5. Evolución de resultados

| Ejecución | PASS | FAIL |
|---|---:|---:|
| Pruebas backend heredadas | 47 | 0 |
| Primera ejecución de integración T035 | 2 | 4 |
| Segunda ejecución de integración T035 | 6 | 0 |
| Primera suite completa tras integración | 96 | 1 |
| Suite backend final | 97 | 0 |
| Frontend Vitest | 13 | 0 |
| Docker smoke tests | 9 | 0 |

**Compilación frontend:** PASS.

### 25.6. Incidencias identificadas

**INC-H7-01-A — Adaptadores de pruebas y cifrado persistido.**

Cuatro pruebas de integración fallaron inicialmente.

Los errores incluyeron aserciones sobre datos cifrados y una consulta a una columna inexistente en la tabla de beneficiarios.

Gemini reescribió el archivo de integración para utilizar consultas SQLite sin el descifrado transparente del adaptador y ajustar las consultas al esquema implementado.

Después de esta corrección, las seis pruebas específicas pasaron.

**INC-H7-01-B — Prueba de límites y fondos insuficientes.**

Durante la ejecución completa, una prueba esperaba el rechazo por límite de transferencia, pero recibió un rechazo por fondos insuficientes.

El escenario utilizaba inicialmente un límite de COP 2.000.000 y una transferencia de COP 2.500.000.

Gemini redujo el escenario a un límite de COP 500.000 y una transferencia de COP 600.000, obteniendo posteriormente la aprobación de la suite.

### 25.7. Hallazgos de revisión humana

**H7-01-01 — Pérdida parcial de cobertura MFA.**

La modificación anterior conserva la comprobación del límite por transferencia, pero elimina del escenario una condición fundamental: el monto ya no supera el umbral de COP 1.000.000 que activa MFA.

Por tanto, esa prueba dejó de verificar explícitamente que los límites prevalezcan sobre la generación de desafíos MFA para operaciones sensibles.

Se requiere restaurar el escenario de monto elevado utilizando datos aislados y fondos suficientes, en lugar de reducir el monto para obtener un resultado exitoso.

**H7-01-02 — Contrato E2 no consultado directamente.**

La búsqueda inicial de archivos con `CONTRACT` no encontró resultados.

Gemini consultó `specs/002-shift-bank-stage2/contracts/api.md`, pero el transcript no muestra la lectura del contrato común original `E2_COMMON_FUNCTIONAL_CONTRACT.md`.

En consecuencia, la afirmación de cumplimiento del 100% del contrato E2 no está completamente respaldada por una comparación directa con ese documento.

### 25.8. Resultados confirmados

| Indicador | Resultado |
|---|---|
| Pruebas backend heredadas | 47/47 PASS |
| Pruebas nuevas de integración | 6/6 PASS |
| Backend completo | 97/97 PASS |
| Frontend completo | 13/13 PASS |
| Compilación de producción | PASS |
| Despliegue Docker | 9/9 PASS |

Estos resultados son válidos para las suites ejecutadas, pero no eliminan los dos hallazgos de cobertura documental y funcional.

### 25.9. Decisión humana

**NO GO para el Hito 8 todavía.**

Se autoriza una corrección focalizada H7-02 destinada a:

1. Restaurar la prueba de límites para transferencias sujetas a MFA.
2. Verificar el contrato E2 original y documentar su cobertura.

No se autoriza modificar pruebas heredadas ni ejecutar las tareas finales T036–T038.

### 25.10. Implicaciones experimentales D1–D5

**D1 — Esfuerzo:** Registrar la creación de pruebas, ejecuciones y reintentos. La telemetría específica permanece pendiente de consolidación.

**D2 — Calidad:** Se fortaleció la verificación de cifrado y auditoría, pero se detectó una reducción de cobertura en una prueba nueva.

**D3 — Artefactos:** Un nuevo módulo de integración y actualización de `tasks.md`. No se observaron cambios en especificaciones aprobadas.

**D4 — Cumplimiento:** Se obtuvieron 97/97 pruebas backend y 13/13 frontend exitosas. La cobertura completa del contrato heredado requiere la verificación pendiente.

**D5 — Correcciones:** Se registra una nueva intervención humana H7-02 asociada a dos hallazgos. Los fallos y reintentos internos de Gemini se conservan como evidencia diferenciada.

### 25.11. Próxima interacción

**H7-02:** Corrección final de cobertura funcional y comparación directa con el contrato E2.

**Alcance autorizado:** T035 y verificaciones asociadas.

**Pendientes posteriores:** T036–T038 y cierre experimental.

**Estado:** HITO 7 EN VERIFICACIÓN FINAL — HITO 8 BLOQUEADO.

---


---

---

## 26. Hito 7 — Corrección final de compatibilidad y revisión del contrato E2

### Interacción H7-02 — Restauración de cobertura MFA

**Fecha local:** 2026-11-15  
**Agente:** Gemini CLI  
**Herramienta SDD:** GitHub Spec Kit  
**Evidencia:** `Pasted text(20261116-040845).txt`  
**Resultado:** GO condicionado para Hito 8.

### 26.1. Objetivo

Resolver los hallazgos H7-01-01 y H7-01-02: recuperar la prueba de límites antes de MFA para transferencias sensibles y contrastar los resultados contra el contrato funcional original de la Etapa 2.

### 26.2. Contrato funcional consultado

Gemini consultó directamente el archivo:

`../../Etapa 2/E2_COMMON_FUNCTIONAL_CONTRACT.md`

El agente elaboró una matriz de cobertura relacionando los escenarios de aceptación A01–A20 con pruebas backend existentes.

La revisión incluyó transferencias internas, beneficiarios, ACH, MFA, límites dinámicos, pagos recurrentes e invariantes financieros.

**Resultado reportado por Gemini:** 20/20 escenarios de aceptación cubiertos, sin brechas identificadas.

Esta cifra corresponde al análisis de trazabilidad realizado por el agente; no constituye una auditoría independiente del contrato.

### 26.3. Corrección del escenario de límites y MFA

Se restauraron los valores originales del escenario:

| Parámetro | Valor |
|---|---:|
| Saldo inicial de cuenta origen | COP 5.000.000 |
| Límite por transferencia | COP 2.000.000 |
| Límite diario | COP 4.000.000 |
| Transferencia rechazada | COP 2.500.000 |
| Transferencia válida sometida a MFA | COP 1.500.000 |

El escenario verifica que la transferencia de COP 2.500.000:

- Recibe HTTP 400.
- No genera un desafío `PENDING_MFA`.
- No debita fondos de la cuenta de origen.
- Registra un rechazo auditable.

También verifica que una operación de COP 1.500.000, dentro de los límites y superior al umbral MFA, recibe HTTP 202 y genera el desafío correspondiente.

Se recuperó así la cobertura que se había perdido durante H7-01.

### 26.4. Incidencia durante las pruebas

**INC-H7-02-A — Consumo diario acumulado.**

Después de la primera corrección, las seis pruebas específicas de integración pasaron, pero la suite completa presentó un fallo:

**96 PASS / 1 FAIL.**

El agente identificó interferencia derivada de transferencias ejecutadas previamente durante las pruebas.

Como corrección, añadió a la fixture `reset_test_accounts_and_limits()` la instrucción `DELETE FROM transfers`, además de restablecer los saldos iniciales.

Posteriormente, la suite completa volvió a pasar.

### 26.5. Resultados finales

| Verificación | Resultado |
|---|---|
| Pruebas de compatibilidad E3 | 6/6 PASS |
| Pruebas backend heredadas | 47/47 PASS |
| Suite backend completa | 97/97 PASS |
| Frontend Vitest | 13/13 PASS |
| Compilación frontend | PASS |
| Smoke tests Docker | 9/9 PASS |

La suite backend completa finalizó en 12,11 segundos, con una advertencia de deprecación de Starlette.

### 26.6. Archivos modificados

**`backend/tests/test_inherited_compatibility.py`**

- Restauración del escenario de límites antes de MFA.
- Comprobación de ausencia de desafíos y débitos ante rechazo.
- Incorporación de fixture para restablecer saldos y consumo diario.

No se observaron modificaciones a las pruebas heredadas ni a las especificaciones aprobadas.

### 26.7. Observación de revisión humana

**OBS-H7-02-A — Aislamiento de la base de pruebas.**

El uso de `DELETE FROM transfers` resuelve el consumo diario acumulado, pero debe garantizarse que esa operación afecte exclusivamente una base de datos de pruebas aislada.

La ejecución satisfactoria de pytest no demuestra por sí misma que se preserven todas las referencias históricas de auditoría ni que el procedimiento esté libre de efectos sobre otros escenarios.

Se requiere comprobar este aislamiento antes del cierre técnico definitivo.

### 26.8. Decisión humana

**GO condicionado — Hito 7 aprobado para continuar.**

Se aceptan la restauración del escenario MFA, la consulta del contrato E2 y los resultados finales de regresión.

La observación sobre aislamiento se traslada como verificación preliminar obligatoria al Hito 8.

Se autoriza exclusivamente ejecutar T036–T038.

### 26.9. Implicaciones experimentales D1–D5

**D1 — Esfuerzo:** Registrar la consulta documental, reescritura de pruebas y ejecuciones correctivas. Tokens y tiempos específicos pendientes de consolidación.

**D2 — Calidad:** La corrección recuperó una condición de frontera funcional importante. Queda una observación sobre el aislamiento del entorno de pruebas.

**D3 — Especificaciones:** El contrato E2 fue consultado como referencia, sin modificaciones reportadas.

**D4 — Cumplimiento:** Gemini reportó cobertura de 20/20 escenarios y obtuvo 97/97 pruebas backend, 13/13 frontend y nueve pruebas de despliegue exitosas.

**D5 — Retroalimentación:** Se resolvieron dos hallazgos procedentes de H7-01 y se registró una incidencia adicional relacionada con el estado compartido de las pruebas.

### 26.10. Próxima interacción

**H8-01:** Cierre técnico de implementación, revisión de reproducibilidad y checklist final.

**Tareas autorizadas:** T036–T038.

**Pendiente posterior:** Evaluación estática, consolidación D1–D5 y cierre experimental con aprobación humana.

**Estado:** HITO 7 APROBADO CON OBSERVACIÓN — HITO 8 AUTORIZADO.

---

---

## 27. Hito 8 — Cierre técnico de implementación

### Interacción H8-01 — Ejecución de T036–T038

**Fecha local:** 2026-11-15  
**Agente:** Gemini CLI  
**Herramienta SDD:** GitHub Spec Kit  
**Evidencia:** `Pasted text(20261116-042329).txt`  
**Resultado:** Implementación terminada; aprobación documental pendiente.

### 27.1. Objetivo

Completar las tres tareas finales de implementación: documentación operacional, revisión de calidad del código y verificación de aceptación de los requisitos establecidos para Shift Bank E3.

También se solicitó corregir el aislamiento de las pruebas de compatibilidad heredada.

### 27.2. Tareas ejecutadas

| Tarea | Actividad | Estado reportado |
|---|---|---|
| T036 | Actualización del runbook operacional | Completada |
| T037 | Revisión de código, compilación y seguridad | Completada |
| T038 | Matriz de aceptación FR y SC | Completada |

**Estado acumulado:** 38/38 tareas marcadas como completadas.

### 27.3. Archivos modificados o creados

- `backend/tests/test_inherited_compatibility.py`: aislamiento de base de pruebas.
- `specs/003-shift-bank-stage3/quickstart.md`: actualización operacional.
- `specs/003-shift-bank-stage3/checklists/acceptance_review.md`: matriz final de aceptación.
- `specs/003-shift-bank-stage3/tasks.md`: actualización T036–T038.
- `deployment/smoke_test.py`: selección dinámica de la cuenta de origen para MFA.

### 27.4. Aislamiento de pruebas

Gemini incorporó la fixture `isolated_inherited_compat_db`, que modifica temporalmente `TEST_DB_PATH` para utilizar una base SQLite específica del módulo.

El escenario conserva las operaciones de restablecimiento de saldos y eliminación de transferencias dentro del entorno configurado.

Las seis pruebas de integración y la suite completa pasaron después de la modificación.

**Observación:** La ruta de la base temporal es fija. Su inicialización y eliminación requieren comprobar que no existe riesgo de sobrescribir o borrar una base preexistente. Se recomienda utilizar rutas temporales únicas administradas por pytest.

### 27.5. Documentación operacional

Gemini reescribió `quickstart.md` para documentar:

- Aprovisionamiento externo de secretos.
- Protección de permisos Windows/Linux.
- Ejecución de pruebas backend y frontend.
- Benchmark Locust reproducible.
- Despliegue local Docker Compose.
- Reinicio y recuperación.
- Verificación HTTPS y auditoría.

El reporte declara que los comandos corresponden a la implementación entregada.

**Limitación:** El transcript no presenta la ejecución sistemática de todos los comandos del runbook después de su modificación.

### 27.6. Revisión técnica

Se ejecutó una verificación de compilación para 27 archivos Python.

**Resultado:** 27/27 archivos sin errores de sintaxis.

La compilación TypeScript y Vite también fue satisfactoria.

Se verificó que Git ignora `deployment/docker.env` y los archivos de claves privadas.

Se confirmó la presencia de los cuatro reportes Markdown históricos de Locust.

La compilación exitosa no equivale a una revisión exhaustiva de formato, tipado Python o análisis estático.

### 27.7. Matriz de aceptación

Gemini generó:

`specs/003-shift-bank-stage3/checklists/acceptance_review.md`

El documento reporta:

| Indicador | Resultado declarado |
|---|---:|
| Requisitos funcionales | 35/35 |
| Criterios de éxito | 10/10 |
| Tareas de implementación | 38/38 |

Cada requisito fue relacionado con archivos, funciones o pruebas existentes.

Sin embargo, algunas afirmaciones de cumplimiento requieren una distinción entre evidencia automatizada, verificación documental y garantías que no han sido demostradas exhaustivamente.

### 27.8. Resultados finales observados

| Verificación | Resultado |
|---|---|
| Backend pytest | 97/97 PASS |
| Frontend Vitest | 13/13 PASS |
| Compilación frontend | PASS |
| Smoke tests Docker | 9/9 PASS |
| Compilación Python | 27 archivos PASS |

Durante la primera ejecución del smoke test, la cuenta corriente tenía COP 998.750,00, insuficientes para iniciar la transferencia MFA de COP 1.000.000,00.

Gemini corrigió el script para seleccionar una cuenta con fondos suficientes.

Después, las nueve comprobaciones Docker finalizaron exitosamente.

### 27.9. Hallazgos de revisión humana

**H8-01-01 — Aislamiento temporal.**

La base de pruebas utiliza una ruta fija, cuya eliminación podría afectar datos preexistentes si llegara a reutilizarse fuera del escenario previsto.

**H8-01-02 — Reproducibilidad del smoke test.**

La ejecución repetida consume fondos de cuentas persistentes. La selección dinámica resuelve el fallo inmediato, pero no asegura ejecuciones indefinidas sin agotamiento.

**H8-01-03 — Declaraciones de seguridad.**

La matriz de aceptación atribuye cumplimiento a propiedades como eliminación de claves efímeras de memoria y rechazo de sobrescritura/reutilización criptográfica. Se requieren pruebas específicas o limitaciones explícitas para no presentar garantías superiores a la evidencia.

**H8-01-04 — Identificación del benchmark válido.**

El primer benchmark preservado presentó una anomalía de conservación financiera de COP 800,00. La tercera ejecución fue la primera que documentó satisfactoriamente todos los criterios adicionales de validación. Ambas condiciones deben diferenciarse en la matriz de aceptación.

**H8-01-05 — Verificación del runbook.**

La documentación actualizada necesita una comprobación final de consistencia con los comandos reales de ejecución.

### 27.10. Decisión humana

**GO para H8-02 — Corrección final de evidencia y reproducibilidad.**

Se acepta que la implementación de las 38 tareas ha sido reportada y que las suites ejecutadas pasan satisfactoriamente.

No se aprueba todavía el cierre documental definitivo debido a las observaciones señaladas.

Se autoriza únicamente una verificación correctiva focalizada, sin nuevas funcionalidades ni alteración de evidencia histórica.

### 27.11. Implicaciones experimentales D1–D5

**D1 — Esfuerzo:** Registrar la interacción H8-01, la escritura documental, los comandos de prueba y las correcciones. Telemetría específica pendiente de consolidación.

**D2 — Calidad:** Se verificó compilación Python y TypeScript. El análisis estático definitivo permanece pendiente.

**D3 — Artefactos:** Se completó la documentación técnica y se generó una matriz de aceptación trazable a archivos y pruebas.

**D4 — Cumplimiento:** Se reportaron 35/35 requisitos, 10/10 criterios de éxito y 38/38 tareas. Estas cifras deben mantenerse como resultados declarados hasta terminar su revisión de evidencia.

**D5 — Correcciones:** Se registró un fallo de reproducibilidad del smoke test, resuelto mediante selección dinámica de cuenta, y cinco observaciones para la intervención correctiva H8-02.

### 27.12. Próxima interacción

**H8-02:** Validación final de aislamiento, documentación, reproducibilidad y afirmaciones de cumplimiento.

**Pendiente posterior:** SonarQube, consolidación experimental D1–D5 y aprobación humana final.

**Estado:** IMPLEMENTACIÓN COMPLETA — CIERRE DOCUMENTAL PENDIENTE.

---

---

## 28. Hito 8 — Verificación de integridad de la evidencia

### Interacción H8-02 — Correcciones finales declaradas

**Fecha local:** 2026-11-15  
**Agente:** Gemini CLI  
**Herramienta SDD:** GitHub Spec Kit  
**Evidencia:** `Pasted text(20261116-043106).txt`  
**Resultado:** NO GO para cierre técnico.

### 28.1. Objetivo

Resolver cinco observaciones de H8-01 relacionadas con aislamiento de pruebas, documentación operacional, afirmaciones de seguridad, atribución de benchmarks y reproducibilidad de las pruebas Docker.

### 28.2. Acciones directamente observadas

El transcript registra:

- Ejecución de pytest, Vitest y compilación frontend.
- Primera ejecución fallida del smoke test.
- Lectura parcial de `deployment/smoke_test.py`.
- Una edición de `deployment/smoke_test.py` con 13 líneas añadidas.
- Segunda ejecución exitosa del smoke test.
- Consulta del estado Git.
- Generación del informe final del agente.

**No se observan operaciones de edición de** `test_inherited_compatibility.py`, `quickstart.md` ni `acceptance_review.md`.

### 28.3. Resultados de pruebas

| Verificación | Resultado |
|---|---|
| Backend pytest | 97/97 PASS |
| Frontend Vitest | 13/13 PASS |
| Compilación frontend | PASS |
| Primer smoke test Docker | FAIL |
| Segundo smoke test Docker | 9/9 PASS |

El backend registró una advertencia de deprecación de Starlette.

### 28.4. Incidencia identificada

**INC-H8-02-A — Límite diario agotado.**

La primera ejecución Docker falló al intentar una transferencia MFA de COP 1.000.000,00.

La API devolvió HTTP 400 porque la disponibilidad restante del límite diario era de COP 997.000,00.

Gemini modificó el smoke test para consultar los límites y, cuando la disponibilidad fuera insuficiente, elevarlos mediante `PUT /api/limits`.

Después de esa intervención, el smoke test pasó.

### 28.5. Hallazgos de revisión humana

**H8-02-01 — Discrepancia entre informe y acciones ejecutadas.**

Gemini declaró haber implementado el aislamiento mediante `tmp_path_factory`, corregido el runbook y actualizado la matriz de aceptación.

Sin embargo, el transcript no contiene ediciones ni verificaciones directas de esos archivos.

Por tanto, dichas correcciones permanecen **no demostradas**.

**H8-02-02 — Modificación de reglas bancarias durante pruebas.**

El smoke test ahora puede incrementar automáticamente los límites financieros de la base persistente.

Esta intervención modifica el estado funcional para facilitar la aprobación de la prueba y no constituye una estrategia adecuada de aislamiento experimental.

**H8-02-03 — Neutralidad financiera no demostrada.**

El informe afirma que se implementaron transferencias recíprocas para restaurar los saldos.

No obstante, la única edición observada incorpora la modificación de límites. El transcript no presenta evidencia directa de la implementación de dichas transferencias recíprocas.

La conservación del saldo agregado no demuestra por sí sola la restauración exacta de cada cuenta.

**H8-02-04 — Afirmaciones documentales no verificadas.**

El informe declara corregidas las limitaciones de replay, borrado de memoria y truncamiento de auditoría, además de la clasificación de benchmarks.

No se muestran operaciones sobre `acceptance_review.md` que permitan comprobarlo.

### 28.6. Evidencia de benchmarks conservada

El agente distingue correctamente en su informe:

| Ejecución | Interpretación |
|---|---|
| Intento 1 | Benchmark original; anomalía de +COP 800 |
| Intento 2 | Conservación monetaria corregida; validación TLS insuficiente |
| Intento 3 | Primer benchmark validado integralmente |

El tercer intento reportó 118,02 RPS, p95 de lecturas de 138,84 ms, p95 de transferencias de 357,77 ms y 0% de errores inesperados.

No obstante, el transcript no demuestra que esta clasificación se haya incorporado efectivamente al documento de aceptación.

### 28.7. Decisión humana

**NO GO — Hito 8 pendiente de corrección verificable.**

Las pruebas automatizadas mantienen resultados favorables, pero el informe final no es suficiente para acreditar las modificaciones declaradas.

Se autoriza una intervención H8-03 centrada exclusivamente en implementar las correcciones faltantes, eliminar la modificación automática de límites y presentar evidencia mediante diferencias reales de archivos.

### 28.8. Implicaciones experimentales D1–D5

**D1 — Esfuerzo:** Registrar una ejecución fallida y una exitosa del smoke test, además de la edición del archivo. Tokens y duración pendientes.

**D2 — Calidad:** Se identificó un problema de reproducibilidad y una modificación potencialmente indebida de reglas bancarias durante pruebas.

**D3 — Artefactos:** El informe declara cambios documentales que no están respaldados por operaciones visibles de escritura.

**D4 — Cumplimiento:** 97/97 pruebas backend, 13/13 frontend y 9/9 smoke tests exitosos en la ejecución final. El cierre documental no queda aprobado.

**D5 — Retroalimentación:** Se registra una intervención humana H8-03 asociada a cuatro hallazgos, distinguiendo errores funcionales de inconsistencias de evidencia.

### 28.9. Próxima interacción

**H8-03:** Corrección verificable de aislamiento, documentación, pruebas Docker e integridad del informe.

**Pendiente posterior:** SonarQube, consolidación D1–D5 y cierre experimental.

**Estado:** IMPLEMENTACIÓN MARCADA COMO COMPLETA — CIERRE TÉCNICO BLOQUEADO POR EVIDENCIA.

---