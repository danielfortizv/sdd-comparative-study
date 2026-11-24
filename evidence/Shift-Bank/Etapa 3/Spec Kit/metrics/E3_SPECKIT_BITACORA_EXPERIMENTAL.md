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

---

## 29. Hito 8 — Migración de agente y continuación de la verificación

### Interacción H8-C01 — Transición de Gemini CLI a Codex

**Fecha local:** 2026-11-16  
**Herramienta SDD:** GitHub Spec Kit  
**Agente anterior:** Gemini CLI  
**Agente actual:** Codex  
**Motivo de transición:** Interrupción del entorno Gemini CLI por deshabilitación de facturación de Google Cloud.  
**Estado:** Verificación incompleta; aprobación pendiente.

### 29.1. Objetivo

Reanudar el trabajo correctivo H8-03 sin reiniciar el experimento, regenerar artefactos previamente completados ni modificar las etapas históricas.

La transición constituye un cambio de agente de implementación, no un cambio de herramienta SDD.

### 29.2. Inspección inicial

Codex identificó:

- Proyecto estructurado mediante GitHub Spec Kit.
- Las 38 tareas marcadas como completadas.
- Existencia de evidencia de los tres benchmarks Locust.
- Documentación de aceptación y operación previamente generada.
- Archivos no rastreados en el repositorio, preservados sin modificación.

El agente indicó que no encontró el archivo `.tessl/RULES.md` en la ubicación esperada.

### 29.3. Modificaciones realizadas

**Archivo:** `deployment/smoke_test.py`

Codex reportó dos ediciones:

1. Incorporación de capturas de saldos iniciales y cálculo del saldo agregado.
2. Incorporación de verificaciones posteriores a las transferencias recíprocas, incluida la selección de cuenta para MFA según el saldo actualizado.

El objetivo es comprobar la conservación monetaria sin restablecer artificialmente los saldos de la base persistente.

No se reportaron modificaciones a especificaciones, contratos históricos ni benchmarks.

### 29.4. Observaciones de la revisión

**OBS-H8-C01-A — Verificación no ejecutada.**

Codex no ejecutó las suites backend, frontend, compilación ni pruebas Docker después de sus modificaciones.

Por tanto, no existen nuevos resultados PASS atribuibles a esta interacción.

**OBS-H8-C01-B — Aislamiento de pruebas.**

El agente identificó una fixture que utiliza `backend/tests/test_shift_bank.db` y elimina archivos durante la preparación y limpieza.

Debe comprobarse el alcance real de esta fixture y su interacción con la base temporal del módulo de compatibilidad antes de ejecutar pytest.

**OBS-H8-C01-C — Configuración de límites.**

Codex afirmó que el smoke test inspeccionado no contiene incrementos automáticos de límites.

Esta afirmación debe contrastarse con el código actual, dado que en H8-02 se registró una edición que introducía esa operación.

**OBS-H8-C01-D — Efectos secundarios de Docker.**

Las pruebas de despliegue pueden reiniciar el backend y generar movimientos y registros de auditoría persistentes.

Las transferencias recíprocas pueden restaurar saldos, pero no eliminan esos efectos secundarios.

Por ello, deben ejecutarse sobre almacenamiento experimental aislado.

**OBS-H8-C01-E — Registro de transición.**

Codex reconoció que todavía no ha registrado formalmente el cambio de agente en la bitácora experimental.

### 29.5. Resultados de esta interacción

| Verificación | Resultado |
|---|---|
| Inspección de repositorio | Parcialmente completada |
| Corrección del smoke test | Editada; pendiente de prueba |
| Backend pytest | No ejecutado |
| Frontend Vitest | No ejecutado |
| Compilación frontend | No ejecutada |
| Docker smoke tests | No ejecutados |
| Registro de transición | Pendiente |

Los resultados históricos de 97 pruebas backend, 13 frontend y nueve verificaciones Docker pertenecen a ejecuciones anteriores y no deben presentarse como nuevas mediciones de Codex.

### 29.6. Implicaciones experimentales D1–D5

**D1 — Esfuerzo:** La interacción de Codex debe contabilizarse separadamente de las sesiones Gemini. No se dispone todavía de telemetría consolidada de tiempo o tokens.

**D2 — Calidad:** Se introdujeron nuevas comprobaciones de conservación de balances, aún sin validación automatizada.

**D3 — Especificaciones:** Se preservó GitHub Spec Kit; no se reportaron cambios en los requisitos aprobados.

**D4 — Cumplimiento:** No se actualiza el estado de aceptación debido a la ausencia de nuevas ejecuciones de verificación.

**D5 — Intervenciones:** Se registra una transición de agente por indisponibilidad del entorno anterior y una nueva intervención de revisión humana. No debe atribuirse a Gemini el trabajo ejecutado por Codex.

### 29.7. Decisión humana

**GO para H8-04 — Verificación pendiente y cierre correctivo.**

Se autoriza comprobar el aislamiento de pruebas, validar los cambios existentes y ejecutar las verificaciones no destructivas.

Las pruebas Docker deberán utilizar un entorno desechable, independiente de los volúmenes persistentes históricos.

No se autoriza iniciar la evaluación experimental final.

### 29.8. Próxima interacción

**H8-04:** Verificación completa, corrección de discrepancias reales y registro definitivo de la transición.

**Estado:** IMPLEMENTACIÓN COMPLETA — VALIDACIÓN DE CODEX PENDIENTE.

---

---

## 30. Hito 8 — Identificación de riesgos de aislamiento experimental

### Interacción H8-04 — Inspección preventiva de bases de datos

**Fecha local:** 2026-11-16  
**Agente:** Codex  
**Herramienta SDD:** GitHub Spec Kit  
**Evidencia:** Transcripción de ejecución H8-04 proporcionada por el investigador.  
**Resultado:** Verificación bloqueada preventivamente.

### 30.1. Objetivo

Completar las verificaciones pendientes de H8-03 sin comprometer bases de datos persistentes, claves criptográficas ni evidencia histórica.

### 30.2. Inspección realizada

Codex examinó la configuración de pruebas, las referencias a `TEST_DB_PATH`, el despliegue Docker y los cambios previos en `deployment/smoke_test.py`.

Identificó que la fixture general de pytest utiliza la ruta fija:

`backend/tests/test_shift_bank.db`

La configuración elimina este archivo al iniciar y finalizar la sesión de pruebas.

El agente también identificó que la configuración de Docker Compose define nombres de contenedores, puertos, red y volumen persistente, por lo que no es seguro asumir aislamiento al ejecutar el despliegue habitual.

### 30.3. Hallazgos

**H8-04-01 — Eliminación potencial de bases preexistentes.**

La utilización de una ruta fija para el almacenamiento de pruebas representa un riesgo cuando el archivo ya existe y contiene información que debe preservarse.

Se requiere reemplazarla por una ruta temporal única, con limpieza restringida exclusivamente a los archivos creados por esa ejecución.

**H8-04-02 — Aislamiento Docker insuficiente.**

La configuración normal de Docker Compose no demuestra independencia respecto al despliegue persistente existente.

Se deben separar contenedores, puertos, redes, volúmenes y credenciales antes de permitir nuevas pruebas destructivas o con efectos persistentes.

**H8-04-03 — Correcciones anteriores conservadas.**

Codex confirmó la presencia de verificaciones de conservación monetaria y transferencias recíprocas en el smoke test.

También informó que no encontró incrementos automáticos de límites en la versión inspeccionada.

Estas observaciones todavía requieren validación mediante ejecución segura.

**H8-04-04 — Documentación experimental.**

Los documentos operacionales y de aceptación contienen información sobre limitaciones de seguridad y benchmarks históricos, pero conservan afirmaciones que deberán contrastarse con los resultados de la siguiente verificación.

El cambio de agente Gemini CLI → Codex continúa pendiente de registro en el repositorio.

### 30.4. Ejecuciones y modificaciones

| Actividad | Resultado |
|---|---|
| Inspección de configuración SQLite | Realizada |
| Inspección de aislamiento Docker | Realizada |
| Inspección de smoke test | Realizada |
| Modificaciones de código | Ninguna |
| Backend pytest | No ejecutado |
| Frontend Vitest | No ejecutado |
| Compilación frontend | No ejecutada |
| Docker smoke tests | No ejecutados |

No se registraron nuevos resultados de rendimiento ni cumplimiento funcional durante esta interacción.

### 30.5. Interpretación experimental

La suspensión preventiva de pruebas constituye una decisión de seguridad del nuevo agente ante un riesgo identificado en la infraestructura de verificación.

Este resultado no debe clasificarse como fallo funcional de Shift Bank ni como una ejecución exitosa de las pruebas.

Tampoco implica que se hayan perdido datos: el riesgo fue identificado antes de ejecutar las operaciones potencialmente destructivas.

### 30.6. Implicaciones para D1–D5

**D1 — Esfuerzo:** Se registra tiempo dedicado a inspección y diagnóstico, sin ejecución de suites.

**D2 — Calidad:** Se identificó un riesgo relacionado con el ciclo de vida de archivos temporales.

**D3 — Especificaciones:** No se reportaron cambios a los requisitos aprobados.

**D4 — Cumplimiento:** Se mantiene el último estado verificado; la nueva ejecución completa continúa pendiente.

**D5 — Retroalimentación:** Se registra una intervención correctiva humana H8-05 para autorizar el aislamiento seguro y retomar las pruebas.

### 30.7. Decisión humana

**GO para H8-05 — Corrección segura del entorno de pruebas.**

Se autoriza modificar exclusivamente la infraestructura de pruebas necesaria para utilizar recursos temporales únicos y verificar la implementación existente.

Las pruebas Docker permanecerán bloqueadas mientras no se demuestre aislamiento completo.

### 30.8. Próxima interacción

**H8-05:** Corrección del aislamiento pytest, ejecución de regresiones y revisión final de evidencia.

**Pendientes posteriores:** Aprobación del Hito 8, evaluación estática y consolidación experimental.

**Estado:** IMPLEMENTACIÓN COMPLETA — VERIFICACIÓN BLOQUEADA HASTA CORREGIR AISLAMIENTO.

---

---

## 31. Hito 8 — Corrección del aislamiento de pruebas y bloqueo de pytest

### Interacción H8-05 — Aislamiento temporal y error de permisos

**Fecha local:** 2026-11-16  
**Agente:** Codex  
**Herramienta SDD:** GitHub Spec Kit  
**Evidencia:** Transcripción H8-05 proporcionada por el investigador.  
**Resultado:** Corrección parcial implementada; verificación bloqueada.

### 31.1. Objetivo

Eliminar la dependencia de rutas fijas para bases de datos y certificados de prueba, evitando operaciones de limpieza sobre archivos preexistentes.

### 31.2. Modificaciones realizadas

**Archivo modificado:** `backend/tests/conftest.py`

Codex reemplazó la configuración de la base de pruebas mediante una ruta fija por un mecanismo que utiliza directorios temporales administrados por pytest.

También trasladó la generación de claves de prueba al contexto de la fixture de sesión y eliminó la generación prematura durante la importación del módulo.

No se reportaron modificaciones a bases de datos persistentes, certificados originales, volúmenes Docker ni benchmarks históricos.

### 31.3. Incidencias observadas

**INC-H8-05-A — Ruta incorrecta de ejecución.**

La primera invocación utilizó una ubicación incorrecta para `pytest.exe`, por lo que las pruebas no se ejecutaron.

**INC-H8-05-B — Inicialización prematura de claves.**

La siguiente ejecución presentó un error durante la recolección de pruebas, relacionado con la generación de claves antes de crear los directorios temporales.

Codex eliminó la llamada prematura.

**INC-H8-05-C — Permisos del directorio temporal.**

La ejecución posterior alcanzó la preparación de fixtures, pero pytest no pudo crear su directorio temporal predeterminado bajo `%TEMP%/pytest-of-danie`.

Se registraron **97 errores de configuración**.

Estos errores impiden evaluar las aserciones funcionales y no deben interpretarse como 97 regresiones bancarias.

### 31.4. Resultados de verificación

| Verificación | Resultado |
|---|---|
| Modificación de aislamiento pytest | Implementada; pendiente de validación |
| Recolección inicial de pruebas | ERROR |
| Ejecución backend posterior | 97 errores de setup |
| Frontend Vitest | No ejecutado |
| Compilación frontend | No ejecutada |
| Docker smoke tests | No ejecutados |
| Registro de transición | Pendiente |

No existen nuevas cifras de pruebas exitosas atribuibles a H8-05.

### 31.5. Revisión de seguridad

El agente mantuvo bloqueada la ejecución Docker debido a que la configuración existente utiliza recursos persistentes compartidos.

La próxima interacción debe solucionar el problema de permisos mediante un directorio temporal nuevo, sin cambiar permisos globales del sistema ni eliminar directorios existentes.

### 31.6. Implicaciones experimentales D1–D5

**D1 — Esfuerzo:** Se registran tres intentos de ejecución, modificaciones de fixtures y diagnóstico de permisos. La telemetría específica de Codex permanece pendiente.

**D2 — Calidad:** Se mejoró el diseño de aislamiento de pruebas, pero su funcionamiento completo todavía no está demostrado.

**D3 — Especificaciones:** No se observaron modificaciones a los requisitos aprobados.

**D4 — Cumplimiento:** No se actualizan los indicadores de cumplimiento funcional por ausencia de ejecuciones válidas.

**D5 — Retroalimentación:** Se registra la intervención correctiva H8-06, derivada del bloqueo ambiental identificado durante H8-05.

### 31.7. Decisión humana

**GO para H8-06 — Recuperación del entorno de pruebas.**

Se autoriza configurar un directorio temporal exclusivo, verificar la inicialización de fixtures y completar las pruebas no destructivas pendientes.

Las pruebas Docker continúan bloqueadas hasta demostrar un aislamiento independiente.

### 31.8. Próxima interacción

**H8-06:** Resolver permisos de pytest, ejecutar regresiones backend/frontend y registrar evidencia real.

**Estado:** IMPLEMENTACIÓN COMPLETA — VALIDACIÓN FINAL BLOQUEADA POR ENTORNO DE PRUEBAS.

---

---

## 32. Hito 8 — Recuperación del entorno de pruebas con Codex

### Interacción H8-06 — Resolución de errores temporales y nuevas restricciones

**Fecha local:** 2026-11-16  
**Agente:** Codex  
**Herramienta SDD:** GitHub Spec Kit  
**Evidencia:** Transcripción H8-06 proporcionada por el investigador.  
**Resultado:** Recuperación parcial del entorno; verificación incompleta.

### 32.1. Objetivo

Resolver el bloqueo de permisos de pytest identificado en H8-05, completar las pruebas automatizadas y registrar formalmente la continuidad del experimento después del cambio de agente.

### 32.2. Acciones realizadas

Codex configuró un directorio temporal local y único mediante un identificador GUID, comprobando que no existiera antes de utilizarlo como argumento `--basetemp`.

Se corrigió adicionalmente la inicialización de claves de prueba en `backend/tests/conftest.py`, asegurando que el directorio de certificados temporales estuviera disponible antes de generar el material criptográfico.

No se reportaron modificaciones deliberadas a bases de datos persistentes, secretos de despliegue ni resultados históricos.

### 32.3. Resultados backend

| Ejecución | Resultado |
|---|---|
| Primer intento con directorio local | 97 errores de preparación |
| Segundo intento después de corregir fixtures | 96 PASS / 1 FAIL |
| Tiempo de segunda ejecución | 15,53 segundos |

El único fallo restante corresponde a:

`test_secret_generator.py::test_create_only_refusal_when_file_exists`

La prueba falló porque las restricciones de permisos aplicadas al archivo temporal generado en Windows impidieron que el propio proceso de pruebas pudiera volver a leerlo.

El agente conservó las aserciones y evitó relajar las restricciones de seguridad.

### 32.4. Bloqueos adicionales

**INC-H8-06-A — Permisos de archivos Windows.**

El generador aplica controles ACL destinados a proteger secretos. Es necesario verificar que dichos controles permiten el acceso del propietario legítimo sin ampliar permisos innecesariamente.

**INC-H8-06-B — Ejecución frontend.**

La invocación inicial de npm mediante PowerShell fue bloqueada por la política de ejecución.

La alternativa `npm.cmd` evitó ese primer obstáculo, pero Vitest tampoco inició correctamente porque esbuild intentó acceder a un directorio fuera del espacio autorizado del agente.

**INC-H8-06-C — Registro experimental.**

Codex identificó el directorio de bitácoras, pero no pudo escribir el registro porque estaba fuera de su raíz autorizada.

**INC-H8-06-D — Docker.**

Las pruebas de despliegue permanecieron bloqueadas debido a la falta de aislamiento independiente de los recursos persistentes.

### 32.5. Estado de los artefactos

**Archivo modificado:** `backend/tests/conftest.py`.

Se reportó la creación de dos directorios temporales `.pytest-h8-06-*`, conservados sin eliminarlos.

No se reportaron modificaciones a los benchmarks, especificaciones históricas ni claves de producción.

### 32.6. Evaluación de la interacción

El problema original de `%TEMP%` quedó superado, permitiendo ejecutar los 97 casos de prueba.

Sin embargo, **no puede afirmarse que la suite backend haya pasado completamente**, debido al fallo de permisos del generador de secretos.

Las pruebas frontend, la compilación y las verificaciones Docker continúan pendientes.

### 32.7. Implicaciones experimentales D1–D5

**D1 — Esfuerzo:** Se registran dos intentos de pytest, diagnóstico de permisos Windows y ejecución fallida de herramientas frontend. La telemetría de Codex se mantiene separada de Gemini.

**D2 — Calidad:** Se mejoró la configuración temporal de pruebas. Permanece un problema en la aplicación de permisos ACL.

**D3 — Especificaciones:** No se reportan modificaciones a contratos funcionales aprobados.

**D4 — Cumplimiento:** 96 pruebas backend exitosas y una fallida. No se actualiza el cumplimiento final hasta concluir las verificaciones.

**D5 — Retroalimentación:** Se registra una nueva intervención correctiva humana H8-07 motivada por restricciones de entorno y permisos, no por una regresión funcional bancaria demostrada.

### 32.8. Decisión humana

**GO para H8-07 — Corrección de permisos y verificación final.**

Se autoriza corregir el problema ACL, completar las pruebas backend/frontend y registrar la transición de agente mediante acceso limitado o un fragmento preparado para incorporación manual.

Docker continúa bloqueado hasta demostrar aislamiento completo.

### 32.9. Próxima interacción

**H8-07:** Corrección de permisos Windows, ejecución de regresiones y finalización del registro experimental.

**Estado:** IMPLEMENTACIÓN COMPLETA — CIERRE EXPERIMENTAL TODAVÍA PENDIENTE.

---


## 33. H8-07 — Codex final environment verification (2026-11-16)

**Agent transition:** Gemini CLI was replaced by Codex after the Google Cloud billing interruption. This section records Codex work only; prior Gemini implementation, benchmark runs, and measurements remain attributed to Gemini and are not reattributed here.

- Corrected `backend/tests/conftest.py` to use a unique pytest-managed database and test-certificate directory under a fresh project-local `--basetemp`. Existing fixed-path databases/certificates are no longer removed or overwritten by the session fixture.
- Corrected `scripts/generate_deployment_secrets.py` Windows ACL identity selection. The managed process executes as `ZORRO\CodexSandboxOffline` while `%USERNAME%` named `danie`; using the latter after removing inheritance made the creating process unable to read its own temporary test file. The helper now grants read/write only to the actual `whoami` identity.
- Backend command: `.venv\Scripts\pytest.exe --basetemp <fresh non-existing project-local .pytest-h8-07-* path> -q` — **97 passed, 0 failed**, one Starlette/httpx deprecation warning; 13.29 s.
- Frontend command: `npm.cmd --prefix frontend test -- --run` — **13 passed** across 2 test files.
- Production build: `npm.cmd --prefix frontend run build` — **PASS**, TypeScript and Vite build completed (33 modules).
- Docker smoke tests: **BLOCKED / NOT RUN**. Existing Compose resource names and persistent deployment prevent an independently confirmed isolated run; no containers, volumes, or deployment secrets were touched.
- No Locust benchmark was run. Historical Gemini benchmark attempts and reports remain unchanged and retain their existing attribution.
- Human review remains required; this entry does not claim approval or alter historical evidence.

## 34. H8-08 — Isolated Docker verification (2026-11-16)

**Agent attribution:** Codex performed this inspection. No Gemini implementation or measurement is claimed in this section.

- Inspected `deployment/docker-compose.yml` and `deployment/smoke_test.py`. Compose uses fixed container names (`shift_bank_backend`, `shift_bank_nginx`), host ports 8080/8443, network `shift_bank_network`, named volume `shift_bank_smoke_data`, the existing `deployment/docker.env`, and mounts `backend/certs` read-only for backend and Nginx.
- Smoke test has nine numbered checks, but Test 9 restarts backend through the fixed `deployment/docker-compose.yml`; Test 1 expects the redirect target to contain port 8443. Therefore an isolated overlay would also require configurable smoke-test restart compose path and redirect port (or isolated test launcher adaptation), plus unique host ports, containers, network, volume, disposable database, generated TLS certificates, and temporary cryptographic secrets.
- Docker CLI is installed (`Docker 29.9.3`, Compose `v5.7.0`), but `docker version` reports permission denied connecting to `npipe:////./pipe/docker_engine`; Docker daemon access is unavailable. Resolved Compose configuration and resource overlap could not be independently checked against a live daemon.
- **Docker smoke tests: BLOCKED / NOT RUN.** No Docker resources or production secrets/certificates were touched. No financial-limit change, database reset, or benchmark execution occurred.
- No Docker result or measurement is attributed to Gemini. Human review remains required.


---

## 33. Hito 8 — Recuperación completa de pruebas automatizadas

### Interacción H8-07 — Corrección de permisos y validación no Docker

**Fecha local:** 2026-11-16  
**Agente:** Codex  
**Herramienta SDD:** GitHub Spec Kit  
**Evidencia:** Transcripción H8-07 proporcionada por el investigador.  
**Resultado:** GO para H8-08.

### 33.1. Objetivo

Resolver los problemas de permisos identificados en H8-06, recuperar las verificaciones backend/frontend y registrar la continuidad experimental tras la transición de Gemini CLI a Codex.

### 33.2. Corrección de permisos Windows

Codex identificó que el fallo de `test_create_only_refusal_when_file_exists` se debía a una diferencia entre el usuario indicado por la variable de entorno `USERNAME` y la identidad real del proceso.

El proceso se ejecutaba como `ZORRO\CodexSandboxOffline`, mientras que `USERNAME` identificaba a `danie`.

Al restringir las ACL utilizando el segundo valor, el proceso perdía acceso de lectura al archivo que había generado.

**Corrección aplicada:**

En `scripts/generate_deployment_secrets.py`, Codex modificó la identificación del propietario autorizado para utilizar la identidad efectiva del proceso.

Esta corrección conserva el propósito de restringir los permisos del archivo, permitiendo el acceso al proceso propietario legítimo.

### 33.3. Aislamiento de pruebas

Se mantuvieron las correcciones previas de `backend/tests/conftest.py`:

- Base SQLite temporal única administrada por pytest.
- Certificados de prueba generados en un directorio temporal.
- Inicialización de claves después de crear los directorios correspondientes.
- Eliminación de dependencias respecto a rutas fijas durante la limpieza.

La ejecución de pytest utilizó un directorio `--basetemp` nuevo dentro del proyecto.

### 33.4. Resultados automatizados

| Verificación | Resultado | Tiempo |
|---|---|---|
| Backend pytest | 97 PASS, 0 FAIL | 13,29 s |
| Frontend Vitest | 13 PASS | 2,42 s |
| Compilación TypeScript y Vite | PASS | 599 ms |
| Docker smoke tests | No ejecutados | — |
| Locust | No ejecutado | — |

La suite backend presentó una advertencia de deprecación relacionada con Starlette/httpx, sin impedir la ejecución.

La compilación frontend transformó 33 módulos satisfactoriamente.

### 33.5. Registro de transición experimental

Codex informó haber agregado una entrada a la bitácora existente de la Etapa 3.

El registro distingue la implementación y los benchmarks históricos producidos mediante Gemini CLI de las correcciones y verificaciones ejecutadas posteriormente por Codex.

Esta separación es necesaria para preservar la atribución de resultados cuando se consoliden las métricas experimentales.

### 33.6. Limitaciones pendientes

**OBS-H8-07-A — Docker no verificado.**

No se ejecutaron las pruebas Docker debido a que la configuración disponible comparte identificadores de recursos con el despliegue persistente.

Se requiere un entorno Docker independiente antes de realizar la validación final.

**OBS-H8-07-B — Directorios temporales históricos.**

Los directorios `.pytest-h8-06-*` permanecieron en el proyecto. Codex no los eliminó para respetar las restricciones de preservación.

**OBS-H8-07-C — Verificación de transferencias recíprocas.**

Las aserciones de restauración de saldos y auditoría fueron inspeccionadas, pero su ejecución efectiva en Docker continúa pendiente.

### 33.7. Impacto experimental D1–D5

**D1 — Esfuerzo:** Se registra una nueva intervención Codex que incluye diagnóstico ACL y ejecución de suites. Las mediciones del agente no deben mezclarse con las de Gemini.

**D2 — Calidad:** Se corrigió un fallo de permisos Windows y se obtuvo una suite backend completamente exitosa.

**D3 — Especificaciones:** No se reportaron modificaciones a los contratos o requisitos aprobados de Spec Kit.

**D4 — Cumplimiento:** Se verificaron exitosamente 97 pruebas backend, 13 frontend y la compilación de producción. Docker continúa pendiente.

**D5 — Correcciones humanas:** La intervención H8-07 resolvió los bloqueos principales de H8-06. Permanece una validación relacionada con el aislamiento del despliegue Docker.

### 33.8. Decisión humana

**GO — H8-07 aprobado.**

Se aceptan los resultados de las pruebas backend/frontend y la corrección del problema ACL.

Se autoriza H8-08 exclusivamente para verificar el despliegue Docker mediante recursos independientes.

La configuración original, las bases persistentes, las claves existentes y los benchmarks históricos deberán permanecer intactos.

### 33.9. Próxima interacción

**H8-08:** Despliegue Docker aislado, ejecución de nueve smoke tests y revisión de integridad financiera y de auditoría.

Una vez aprobado el cierre técnico, continuará la evaluación experimental correspondiente.

**Estado:** VERIFICACIÓN BACKEND/FRONTEND APROBADA — DOCKER PENDIENTE.

---

---

## 34. Hito 8 — Bloqueo de Docker y preparación de SonarQube

### Interacción H8-08 — Inspección de despliegue aislado

**Fecha local:** 2026-11-16  
**Agente:** Codex  
**Herramienta SDD:** GitHub Spec Kit  
**Evidencia:** Transcripción H8-08 proporcionada por el investigador.  
**Resultado:** Docker bloqueado; verificación pendiente.

### 34.1. Objetivo

Validar el despliegue de Shift Bank E3 mediante una configuración Docker completamente aislada, preservando los recursos persistentes y la evidencia experimental previa.

### 34.2. Inspección realizada

Codex inspeccionó:

- `deployment/docker-compose.yml`
- `deployment/smoke_test.py`
- Configuración de contenedores, puertos, redes y volúmenes.
- Referencias a secretos y certificados.
- Comportamiento de reinicio del backend durante las pruebas.

El agente identificó referencias a recursos fijos que impiden considerar seguro el despliegue habitual como entorno experimental desechable.

### 34.3. Incidencia principal

**INC-H8-08-A — Acceso denegado al motor Docker.**

El comando `docker version` no logró establecer comunicación con:

`npipe:////./pipe/docker_engine`

Docker CLI y Compose se encuentran instalados, pero el agente no dispone de acceso operativo confirmado al motor.

Por consiguiente, no pudo levantar un entorno aislado ni ejecutar las nueve verificaciones de despliegue.

### 34.4. Riesgos identificados

**H8-08-01 — Recursos compartidos.**

La configuración original define nombres fijos de contenedores, puertos, red y volumen.

**H8-08-02 — Material criptográfico.**

El despliegue referencia certificados y secretos existentes que no deben utilizarse en un experimento desechable sin garantizar su independencia.

**H8-08-03 — Ejecución de smoke tests.**

El script de pruebas utiliza referencias fijas al archivo Compose y al puerto HTTPS 8443.

Estas referencias deben parametrizarse para evitar que las pruebas reinicien el despliegue original.

### 34.5. Resultados

| Actividad | Resultado |
|---|---|
| Inspección de Compose | Realizada |
| Inspección del smoke test | Realizada |
| Acceso al motor Docker | Denegado |
| Validación de aislamiento operativo | No realizada |
| Smoke tests Docker | 0 ejecutados |
| Modificaciones de implementación | Ninguna reportada |
| Registro en bitácora | Realizado por Codex |

Los resultados Docker obtenidos anteriormente mediante Gemini CLI permanecen como evidencia histórica, pero no sustituyen la validación aislada solicitada.

### 34.6. Configuración SonarQube proporcionada por el investigador

Se registra la siguiente información para la evaluación estática posterior:

| Campo | Valor |
|---|---|
| Servidor SonarQube | `http://localhost:9000` |
| Clave del proyecto | `Shift-Bank---Stage-3---Spec-Kit` |
| Variable de entorno del token | `SONAR_TOKEN_SPECKIT3` |

El investigador también proporcionó un badge de estado del Quality Gate.

El token incluido en el enlace no se reproduce en la bitácora por seguridad.

**Estado de SonarQube:** No ejecutado durante H8-08.

Los resultados futuros deberán registrarse únicamente después de ejecutar el análisis y obtener métricas verificables del proyecto correspondiente.

### 34.7. Implicaciones experimentales D1–D5

**D1 — Esfuerzo:** Se registra tiempo de inspección y diagnóstico de Docker atribuible a Codex, sin ejecución de pruebas.

**D2 — Calidad:** Se identificaron dependencias de configuración que dificultan el aislamiento del despliegue.

**D3 — Especificaciones:** No se reportaron modificaciones a contratos ni requisitos aprobados.

**D4 — Cumplimiento:** La validación Docker aislada permanece pendiente; no se actualizan los resultados de aceptación.

**D5 — Retroalimentación:** Se registra una nueva intervención humana H8-09 para solucionar el acceso a Docker y completar las verificaciones.

### 34.8. Decisión humana

**GO para H8-09 — Recuperación del acceso Docker y preparación de despliegue aislado.**

Se autoriza diagnosticar el acceso al motor, preparar una configuración independiente y ejecutar pruebas únicamente cuando el aislamiento haya sido confirmado.

Se mantiene bloqueada la evaluación SonarQube hasta finalizar el cierre técnico.

### 34.9. Próxima interacción

**H8-09:** Recuperación del acceso Docker, aislamiento de recursos y ejecución de los nueve smoke tests.

**Posteriormente:** Evaluación SonarQube y consolidación experimental D1–D5.

**Estado:** IMPLEMENTACIÓN COMPLETA — DOCKER AISLADO PENDIENTE — SONARQUBE CONFIGURADO PARA EVALUACIÓN POSTERIOR.

---

---

## 35. Hito 8 — Diagnóstico del acceso Docker y decisión de cierre

**Interacción:** H8-09  
**Fecha:** 2026-11-16  
**Agente:** Codex  
**Herramienta SDD:** GitHub Spec Kit  
**Estado:** Acceso Docker recuperado parcialmente. Verificación aislada pendiente.

### 35.1. Resultados

Codex comprobó que Docker Desktop era accesible mediante un contexto de ejecución elevado.

El despliegue original estaba activo con contenedores `shift_bank_nginx` y `shift_bank_backend`, puertos 8080/8443, red y volúmenes persistentes existentes.

El agente modificó `deployment/smoke_test.py` para permitir especificar el archivo Compose del reinicio y calcular dinámicamente el puerto HTTPS esperado.

No ejecutó los smoke tests ni inició recursos adicionales.

### 35.2. Hallazgos

El bloqueo principal dejó de ser la disponibilidad del motor Docker y pasó a ser la preparación de un despliegue aislado.

No se registraron modificaciones a secretos, bases de datos ni contenedores originales.

El registro de H8-09 en la bitácora permanece pendiente.

### 35.3. Decisión humana

Se autoriza H8-10 para completar de manera integral la preparación, ejecución y corrección de las pruebas Docker aisladas.

No se autorizan modificaciones de los recursos originales ni la alteración de evidencia histórica.

Una vez obtenidos los resultados Docker, el siguiente paso será la evaluación SonarQube, seguida de la consolidación D1–D5.

### 35.4. Implicaciones D1–D5

- **D1:** Iteración de diagnóstico adicional atribuible a Codex.
- **D2:** Identificación de dependencias operacionales del despliegue.
- **D3:** Especificaciones existentes preservadas.
- **D4:** Sin nueva ejecución válida de Docker.
- **D5:** Intervención humana para reducir ciclos correctivos y concentrar el cierre.

**Estado:** IMPLEMENTACIÓN TERMINADA — VALIDACIÓN DOCKER PENDIENTE.

---

2
## 35. H8-10 — Isolated Docker verification (Codex, 2026-11-16)

**Attribution:** Codex prepared and executed this isolated verification. It does not alter attribution of Gemini implementation or historical Locust measurements.

- Prepared a temporary Compose override and fully resolved Compose file in `.sb-h810-967924cae6-v6rgv6n4/`. The generated deployment used project `sb-h810-967924cae6`, containers `sb-h810-967924cae6_backend` and `_nginx`, network `sb-h810-967924cae6_network`, volume `sb-h810-967924cae6_data`, and host ports 18080/18443. Disposable DB was on that named volume. It used temporary RSA/TLS certificates and generated test-only secrets; no values are recorded here.
- Before startup, resolved Compose JSON assertions checked exact unique container names, only ports 18080/18443 (base 8080/8443 were overridden), and the unique named volume/network. Host port bind checks succeeded. Prior Docker inventory showed the original containers using 8080/8443, original network `shift_bank_network`, and existing volumes `shift_bank_data`, `shift_bank_h6_data`, and `shift_bank_smoke_data`; isolated identifiers did not overlap.
- Built and started only the isolated project using `scripts/run_isolated_docker_smoke.py`; both containers became healthy/started. The existing deployment was not restarted or modified.
- Smoke tests **1–9 passed**: HTTP→HTTPS redirect to 18443; SPA over TLS; health/keys/database; seeded accounts; encrypted transfer; MFA challenge and encrypted confirmation; valid HMAC audit verification (8 records); unauthorized audit rejection (401); restart persistence with valid audit.
- Balance invariants: initial Checking COP 5,000,000.00 and Savings COP 15,000,000.00. Both reciprocal transfer pairs asserted exact per-account balances equal to the initial snapshot and aggregate conservation (COP 20,000,000.00). No limits were raised or reset.
- Read-only SQLite inspection inside isolated backend: accounts 2/2 encrypted, limits 2/2 encrypted, transfer amounts 6/6 encrypted (`enc:v1:` prefix).
- After verification, isolated nginx and backend containers were stopped; isolated volume and generated evidence/config remain available for review. No original volumes/resources or production certs/secrets were changed.
- SonarQube was not run. Human review remains required.


---

## 36. Hito 8 — Validación Docker aislada y cierre técnico

### Interacción H8-10 — Verificación final de despliegue

**Fecha:** 2026-11-16  
**Agente:** Codex  
**Herramienta SDD:** GitHub Spec Kit  
**Evidencia:** `Pasted text(20261116-091116).txt`  
**Resultado:** HITO 8 APROBADO.

### 36.1. Objetivo

Completar la validación Docker pendiente mediante un despliegue completamente aislado, preservando la implementación original, los recursos persistentes y los resultados experimentales anteriores.

### 36.2. Implementación del entorno aislado

Codex creó el script:

`scripts/run_isolated_docker_smoke.py`

Este permite preparar una configuración temporal de Docker Compose con recursos independientes.

Se verificaron las siguientes separaciones:

| Recurso | Despliegue original | Despliegue aislado |
|---|---|---|
| HTTP | 8080 | 18080 |
| HTTPS | 8443 | 18443 |
| Contenedores | `shift_bank_*` | `sb-h810-*` |
| Red | `shift_bank_network` | Red independiente |
| Volumen SQLite | Persistente original | Volumen experimental |
| Secretos | Originales | Generados para pruebas |
| Certificados | Originales | Temporales |

La configuración Compose resuelta fue revisada antes de iniciar los recursos.

### 36.3. Correcciones durante la ejecución

Se registraron errores iniciales relacionados con la definición de volúmenes, resolución de configuración y validación de identificadores.

Codex corrigió el script de aislamiento y volvió a ejecutar el procedimiento.

También modificó `deployment/smoke_test.py` para permitir seleccionar el proyecto Compose y verificar el puerto HTTPS correspondiente al entorno experimental.

Las correcciones permanecieron dentro del alcance autorizado H8-10.

### 36.4. Resultados de las pruebas Docker

| Prueba | Resultado |
|---|---|
| Redirección HTTP → HTTPS | PASS |
| Aplicación React sobre TLS | PASS |
| Health check backend | PASS |
| Consulta de cuentas | PASS |
| Transferencia cifrada | PASS |
| MFA y confirmación cifrada | PASS |
| Verificación autorizada de auditoría | PASS |
| Rechazo de verificación no autorizada | PASS |
| Persistencia tras reinicio | PASS |

**Resultado total: 9/9 PASS.**

### 36.5. Verificación financiera

Las pruebas incluyeron transferencias ordinarias y operaciones sujetas a MFA, seguidas de transferencias recíprocas.

Codex comprobó la restauración exacta de los saldos originales.

| Cuenta | Saldo después de las pruebas |
|---|---:|
| Checking | COP 5.000.000,00 |
| Savings | COP 15.000.000,00 |
| **Total** | **COP 20.000.000,00** |

No se reportaron modificaciones automáticas de límites ni reinicialización de cuentas persistentes.

### 36.6. Cifrado y auditoría

La ejecución verificó:

- Ocho registros de auditoría válidos.
- Integridad de la cadena criptográfica.
- Rechazo HTTP 401 para verificación no autorizada.
- Persistencia de saldos y registros tras reiniciar el backend.
- Cifrado en SQLite de dos balances, dos campos de límites y seis importes de transferencia.

La inspección de persistencia se efectuó mediante una consulta de solo lectura.

### 36.7. Preservación del entorno original

Los contenedores experimentales quedaron detenidos tras la verificación.

El volumen aislado y sus archivos temporales se conservaron para revisión.

Codex reportó que los contenedores, volúmenes, certificados, secretos y bases de datos originales no fueron modificados.

### 36.8. Archivos generados o modificados

- `deployment/smoke_test.py`: parametrización del proyecto Compose y del puerto HTTPS.
- `scripts/run_isolated_docker_smoke.py`: creación y ejecución del despliegue experimental aislado.
- `E3_SPECKIT_BITACORA_EXPERIMENTAL.md`: incorporación de la evidencia H8-10 atribuida a Codex.

### 36.9. Evaluación D1–D5

**D1 — Esfuerzo:** Se registra una interacción de Codex que incluye preparación del entorno, correcciones de Compose, ejecución Docker y registro de evidencia. La telemetría completa permanece pendiente de consolidación.

**D2 — Calidad:** La validación confirma que los mecanismos de cifrado, auditoría y despliegue funcionan bajo el escenario aislado ejecutado. El análisis SonarQube permanece pendiente.

**D3 — Especificaciones:** Se preservaron los contratos existentes y se añadieron herramientas de verificación reproducible.

**D4 — Cumplimiento:** Se obtuvieron 9/9 pruebas Docker exitosas, conservación monetaria exacta y persistencia criptográfica verificada.

**D5 — Correcciones:** Se registran errores y correcciones de configuración Docker durante H8-10, atribuibles exclusivamente a Codex.

### 36.10. Decisión humana

**GO — HITO 8 APROBADO.**

Se acepta la validación técnica de Shift Bank Etapa 3:

- 38/38 tareas implementadas.
- 97/97 pruebas backend aprobadas.
- 13/13 pruebas frontend aprobadas.
- Compilación de producción satisfactoria.
- 9/9 pruebas Docker aisladas aprobadas.
- Benchmark Locust previamente validado.
- Integridad financiera y auditoría verificadas.

La implementación y su validación técnica se consideran completas para el alcance del experimento.

### 36.11. Próxima fase

**H9-01 — Evaluación experimental final.**

Actividades pendientes:

1. Ejecutar SonarQube con el proyecto `Shift-Bank---Stage-3---Spec-Kit`.
2. Obtener métricas reales de calidad estática.
3. Consolidar las dimensiones experimentales D1–D5.
4. Preparar el informe final para revisión humana.

No se reproducen credenciales ni valores de tokens.

**Estado:** HITO 8 APROBADO — IMPLEMENTACIÓN Y VALIDACIÓN TÉCNICA COMPLETAS — EVALUACIÓN EXPERIMENTAL AUTORIZADA.

---


## 37. H9-01 — Evaluación experimental final parcial (Codex, 2026-11-16)

**Resultado:** evaluación parcial; análisis SonarQube y métricas autenticadas pendientes. Codex no reatribuye a Gemini trabajo propio, pruebas ejecutadas por Codex ni métricas de benchmarking previas.

- Se inspeccionaron `specs/003-shift-bank-stage3/`, `checklists/acceptance_review.md`, `tasks.md`, la guía de medición `../_codex_prep/02_EVIDENCIAS_Y_METRICAS.md`, `locust/reports/` y la bitácora. La especificación declara 35 FR y 38 escenarios; tasks reporta 38/38 completadas.
- Verificación funcional reportada desde evidencia H8: backend 97/97; Vitest 13/13; build PASS; Docker aislado 9/9. H8-10 verificó conservación por cuenta (Checking COP 5,000,000.00, Savings COP 15,000,000.00; total COP 20,000,000.00), 8 registros de auditoría válidos y persistencia tras reinicio. Consulta SQLite de solo lectura confirmó 2/2 balances, 2/2 límites y 6/6 importes cifrados.
- Benchmark histórico Gemini: intento 1 no conservó fondos (+COP 800); intento 2 conservó fondos pero usó TLS no verificado y careció de muestreo de concurrencia 1 Hz; intento 3: 30 usuarios/60 s, lectura p95 138.84 ms, transferencia p95 357.77 ms, 7,076 solicitudes operativas + 5 handshakes, 757 entradas HMAC verificadas y COP 600,000,000.00 conservados. Codex no repitió Locust.
- **SonarQube no ejecutado:** `SONAR_TOKEN_SPECKIT3` no estaba configurada en el entorno; `sonar-scanner` local no estaba disponible. No se intentó acceso anónimo ni se usó credencial alternativa. Quality Gate, reliability/security/maintainability, bugs/vulnerabilities/smells/debt, LOC/complexity/duplication y coverage: **N/D** para Stage 3.
- **D1:** tokens, costo, mensajes y tiempo activo/wall por herramienta N/D sin telemetría durable suficiente; no se estimaron. **D2:** Sonar pendiente; valores Tessl no se sustituyen por valores Spec Kit. **D3:** siete artefactos core previstos (`spec`, `plan`, `research`, `data-model`, API contract, quickstart, tasks) y checklist de aceptación; métricas de densidad/Req-CLOD y distribución N/D por falta de extracción con regla congelada. **D4:** resultados funcionales indicados arriba. **D5:** incidentes de facturación Gemini, aislamiento pytest/ACL Windows, ACL de identidad corregida y Compose aislado se describen con atribución Codex/Gemini separada.
- Informe derivado: `Spec Kit/reports/h9-01-final-experimental-evaluation.md`. N/D significa dato no disponible, nunca cero.
- No se modificó código para mejorar ratings; no se ejecutó SonarQube, no se hizo consolidación D1-D5 académica, y los benchmarks históricos permanecen sin cambios.

**Acción necesaria para cerrar H9-01:** configurar de manera segura `SONAR_TOKEN_SPECKIT3` en el entorno de ejecución y completar el escaneo/consulta autenticada; no compartir el token en chat ni guardarlo en archivos del proyecto.

---

## 37. Hito 9 — Consolidación experimental parcial y bloqueo de SonarQube

### Interacción H9-01 — Preparación de evaluación final

**Fecha:** 2026-11-16  
**Agente:** Codex  
**Herramienta SDD:** GitHub Spec Kit  
**Evidencia:** Transcripción H9-01 proporcionada por el investigador.  
**Resultado:** Evaluación parcialmente completada.

### 37.1. Objetivo

Realizar el análisis estático mediante SonarQube y consolidar las cinco dimensiones experimentales D1–D5 utilizando exclusivamente los resultados verificables de Shift Bank Etapa 3.

### 37.2. Fuentes inspeccionadas

Codex reportó haber consultado:

- Especificaciones aprobadas de la Etapa 3.
- Guía de estandarización de métricas.
- Bitácora experimental de Spec Kit.
- Matriz de aceptación final.
- Resultados históricos de los tres benchmarks Locust.
- Documentación de preparación y transferencia entre agentes.

### 37.3. Resultados de SonarQube

El agente comprobó que la variable de entorno `SONAR_TOKEN_SPECKIT3` no estaba disponible en su proceso.

También informó que no encontró una instalación local de `sonar-scanner`.

Debido a estas condiciones, no ejecutó el análisis de código.

| Métrica | Resultado |
|---|---|
| Quality Gate | N/D |
| Reliability | N/D |
| Security | N/D |
| Maintainability | N/D |
| Duplicación | N/D |
| Cobertura SonarQube | N/D |
| Deuda técnica | N/D |

**N/D significa no disponible, no un resultado de cero.**

No se generó evidencia nueva de calidad estática durante esta interacción.

### 37.4. Consolidación experimental preliminar

**D1 — Esfuerzo y consumo**

No se encontraron mediciones duraderas suficientes para consolidar completamente tokens, costos y tiempos de ejecución.

Codex conservó los valores faltantes como N/D, sin estimarlos artificialmente ni combinar telemetría de Gemini con la de Codex.

**D2 — Calidad del código**

La evaluación SonarQube permanece pendiente.

Los resultados funcionales y de pruebas automatizadas no se utilizaron como sustitutos de métricas de análisis estático.

**D3 — Artefactos de especificación**

Codex identificó siete artefactos principales y la lista de aceptación.

Se registraron 35 requisitos funcionales, 38 escenarios y 38 tareas completadas.

Las métricas derivadas que requieren extracción uniforme permanecen pendientes.

**D4 — Cumplimiento funcional**

La consolidación recuperó los siguientes resultados históricos:

| Evidencia | Resultado |
|---|---|
| Backend | 97/97 PASS |
| Frontend | 13/13 PASS |
| Build | PASS |
| Docker aislado | 9/9 PASS |
| Conservación monetaria Docker | COP 20.000.000 exactos |
| Cifrado persistente | Verificado en los campos inspeccionados |
| Auditoría | Verificada |
| Locust | Tercer intento validado |

No se repitieron las pruebas durante H9-01.

**D5 — Correcciones y retrabajo**

El informe preliminar distingue las incidencias de implementación de Gemini CLI y las intervenciones correctivas posteriores de Codex.

Se identificaron como eventos relevantes la interrupción de facturación de Google Cloud, la corrección del aislamiento de pruebas, los problemas de ACL Windows y el despliegue Docker aislado.

La cuantificación definitiva permanece pendiente.

### 37.5. Artefactos generados

Codex creó el archivo:

`reports/h9-01-final-experimental-evaluation.md`

El documento recoge los resultados disponibles y señala explícitamente las métricas pendientes.

También informó haber agregado los hallazgos a la bitácora experimental existente.

No se reportaron modificaciones a la implementación bancaria, los benchmarks históricos ni las especificaciones aprobadas.

### 37.6. Hallazgos de revisión humana

**H9-01-01 — Credencial no disponible.**

La variable requerida para autenticar SonarQube no estaba configurada en el entorno del agente.

**H9-01-02 — Analizador no disponible.**

No se encontró una instalación local del ejecutable SonarScanner.

**H9-01-03 — Telemetría parcial.**

Los resultados disponibles no permiten calcular todos los indicadores de esfuerzo sin introducir supuestos no respaldados por evidencia.

Estas limitaciones deben permanecer explícitas en el informe final.

### 37.7. Decisión humana

**GO para H9-02 — Finalización de SonarQube y métricas.**

Se acepta el reporte preliminar como base de consolidación.

Se autoriza configurar el acceso seguro a SonarQube, ejecutar el análisis, obtener sus métricas y completar el informe con los datos realmente disponibles.

No se autoriza modificar código únicamente para mejorar las calificaciones estáticas.

### 37.8. Próxima interacción

**H9-02:** Ejecución SonarQube, consolidación final D1–D5 y presentación del informe experimental para revisión humana.

**Estado:** IMPLEMENTACIÓN Y PRUEBAS COMPLETAS — EVALUACIÓN EXPERIMENTAL PENDIENTE DE SONARQUBE.

---


## 38. H9-02 — Diagnóstico SonarQube (Codex, 2026-11-16)

- Proceso/usuario/máquina: comprobación de presencia de `SONAR_TOKEN_SPECKIT3` dio **unset** en los tres scopes; no se leyó ni mostró ningún valor.
- Conectividad no autenticada únicamente al endpoint de salud del sistema: `GET http://localhost:9000/api/system/status` respondió HTTP 200, estado `UP`.
- `sonar-scanner` no está instalado localmente. No se ejecutó análisis ni consultas autenticadas del proyecto; no se intentó acceso anónimo ni se tomó token de otro origen.
- Por tanto, Quality Gate, ratings de reliability/security/maintainability, bugs, vulnerabilidades, smells, deuda, LOC, duplicación, cobertura e ID del análisis son N/D. Los resultados Tessl/E2 no sustituyen a Stage 3 Spec Kit.
- Informe H9-01 actualizado: `Spec Kit/reports/h9-01-final-experimental-evaluation.md`. D1/D3 permanecen N/D donde faltan telemetría y extracción normalizada reproducible; D4 recoge pruebas y benchmarks con atribución conservada; D5 documenta incidentes/correcciones Codex separados del trabajo/mediciones Gemini.

**Bloqueo externo y acción exacta:** configure el secreto `SONAR_TOKEN_SPECKIT3` en el entorno seguro del proceso que inicia el agente Codex y abra una sesión nueva. No pegue el token en el chat ni lo guarde en archivos del repositorio. Después se podrá invocar un scanner compatible (por ejemplo, scanner CLI en contenedor Docker ya disponible), ejecutar el análisis con el proyecto `Shift-Bank---Stage-3---Spec-Kit` y recuperar Quality Gate/métricas con autenticación basada únicamente en esa variable.

**H9-02 permanece incompleto** hasta contar con el token en ese entorno y registrar el análisis/medidas reales.

## 39. H9-03 — Reintento de cierre SonarQube (Codex, 2026-11-16)

- Presencia de `SONAR_TOKEN_SPECKIT3` comprobada sin leer ni imprimir el valor: ausente en scopes Process, User y Machine del entorno visible para esta sesión.
- `http://localhost:9000/api/system/status`: HTTP 200, estado `UP`.
- No se usó el secreto escrito en el mensaje del usuario; la instrucción requiere autenticación exclusivamente mediante la variable de entorno. No se ejecutó scanner ni se consultaron endpoints autenticados. No se intentó acceso anónimo al proyecto.
- Quality Gate, métricas y analysis ID continúan N/D. El informe H9-01 se actualizó con el nuevo resultado de presencia por scopes y conserva el resumen D1-D5 basado únicamente en evidencia disponible.

**Acción humana exacta:** configure `SONAR_TOKEN_SPECKIT3` en el entorno del proceso que lanza esta sesión de Codex y abra una sesión nueva. No envíe el token por chat ni lo copie a archivos del repositorio. La sesión deberá confirmar solo `SET=True`, ejecutar scanner compatible para `Shift-Bank---Stage-3---Spec-Kit` y recuperar resultados autenticados.

**H9-03 sin cierre:** falta la disponibilidad segura de la variable en el proceso del agente; no hay métricas Sonar nuevas.

## 40. H9 — Consolidación final de evaluación experimental (Codex, 2026-11-16)

**Fuentes Sonar suministradas por el investigador:** `Spec Kit/reports/sonarqube_metrics_speckit3.json` y `Spec Kit/reports/sonarqube_quality_gate_speckit3.json`. Codex leyó los archivos; no ejecutó ni repitió análisis Sonar.

- Proyecto: key `Shift-Bank---Stage-3---Spec-Kit`, coincide con `component.key` del JSON de métricas.
- Quality Gate: `NONE`; lista `conditions` vacía. No puede reportarse PASS ni FAIL.
- CAYC status: `compliant`, conforme al campo del JSON; no equivale a Quality Gate aprobado.
- `component.measures` está vacío. Analysis ID, versiones del scanner/servidor vinculadas al análisis y todas las medidas solicitadas (ratings reliability/security/maintainability, bugs, vulnerabilidades, smells, deuda, LOC, duplicación y coverage) son N/D.
- Reporte actualizado: `Spec Kit/reports/h9-01-final-experimental-evaluation.md`. D1 (telemetría por agente) y submétricas D3 sin extracción normalizada permanecen N/D. D4 y D5 integran únicamente evidencia registrada, separando Gemini CLI de Codex; no se estimaron tokens, costos, tiempos ni métricas ausentes.
- Resultados funcionales ya documentados: 38/38 tareas; backend 97/97; frontend 13/13; build PASS; Docker aislado 9/9. Tres intentos Locust históricos conservados según sus reportes y atribución.
- No se ejecutaron análisis, Docker, Locust ni suites de pruebas en H9. No se modificó código de aplicación.

**Conclusión:** cierre de la consolidación documental D1–D5 con vacíos señalados explícitamente; la evidencia Sonar recibida es incompleta y no permite una conclusión de calidad estática ni de gate. Para esa conclusión se requiere export con measures pobladas, status/conditions del gate calculados y metadatos de análisis. Se entrega para revisión humana.

## 41. H9 — Resultados SonarQube validados y cierre documental (Codex, 2026-11-16)

**Procedencia:** archivos suministrados por el investigador tras análisis SonarQube manual sobre snapshot aislado: `Spec Kit/reports/sonarqube_metrics_speckit3_validated.json` y `Spec Kit/reports/sonarqube_quality_gate_speckit3_validated.json`. Codex leyó/exportó cifras; no reejecutó SonarScanner. La atribución de implementación/benchmark a Gemini CLI y las correcciones/verificación H8 a Codex permanecen separadas.

| Métrica exportada | Valor |
|---|---:|
| Project key / qualifier | `Shift-Bank---Stage-3---Spec-Kit` / TRK |
| Quality Gate | OK; conditions vacías; ignoredConditions=false |
| CAYC status | compliant |
| Bugs / reliability rating | 3 / 3.0 (C) |
| Vulnerabilities / security rating | 1 / 2.0 (B) |
| Security hotspots | 0 |
| Code smells / maintainability rating | 70 / 1.0 (A) |
| Deuda técnica (sqale_index) | 508 min = 8 h 28 min |
| NCLOC | 6,204 |
| Duplicated lines density | 0.0% |
| Coverage | 0.0 reportado; el JSON no incluye alcance/importación del reporte de cobertura. No interpretar como porcentaje de pruebas ejecutadas. |
| Incidencias clásicas agregadas | 74 = 3 bugs + 1 vulnerability + 70 smells; densidad calculada 74 / 6.204 = 11.93 incidencias/KLOC. No se suman métricas MQR.

Analysis ID/fecha, versiones del scanner/servidor, SHA/revisión del snapshot, configuración/exclusiones, condiciones de gate y cobertura instrumentada/importada: N/D en los dos JSON. Aunque el status exportado es OK, conditions está vacío; se reporta sin inferir umbrales. El snapshot aislado limita atribución exacta al árbol de trabajo actual.

El informe `Spec Kit/reports/h9-01-final-experimental-evaluation.md` fue actualizado. D1 tokens/costos/tiempos por agente y medidas D3 normalizadas faltantes permanecen N/D; D4 incorpora resultados registrados (38/38 tasks, 97/97 backend, 13/13 frontend, build PASS, Docker 9/9; tres benchmarks conservados); D5 conserva incidentes/remediaciones con atribución Gemini/Codex. Coverage 0.0 no representa 0% tests pasados.

**Conclusión:** consolidación documental D1–D5 lista para revisión humana con N/D y limitaciones de reproducibilidad indicados. Quality Gate exportado OK; calidad estática reporta 3 bugs, 1 vulnerabilidad, 70 smells, rating C/B/A, 0 hotspots, deuda 508 min, 0% duplicación, 6,204 NCLOC y cobertura exportada 0.0 sin contexto de importación. No se modificó código ni se reejecutaron pruebas, Docker, Locust o Sonar.


---

## 39. Hito 9 — Validación de SonarQube y cierre experimental

**Fecha:** 2026-11-16  
**Agente de consolidación:** Codex  
**Herramienta SDD:** GitHub Spec Kit  
**Evidencia:** Exportaciones SonarQube validadas e informe H9.  
**Resultado:** Evaluación consolidada, pendiente de aprobación documental final.

### 39.1. Análisis SonarQube

El investigador ejecutó manualmente SonarScanner sobre una copia aislada del código fuente para evitar conflictos de acceso con los directorios temporales de pytest.

La ejecución finalizó satisfactoriamente y SonarQube procesó el análisis.

El proceso utilizó SonarScanner 5.1.0 y SonarQube Server 26.9.0, con 23 archivos indexados.

### 39.2. Resultados medidos

| Métrica | Resultado |
|---|---:|
| Quality Gate | OK |
| Bugs | 3 |
| Reliability Rating | C |
| Vulnerabilidades | 1 |
| Security Rating | B |
| Security Hotspots | 0 |
| Code Smells | 70 |
| Maintainability Rating | A |
| Deuda técnica | 508 minutos |
| Líneas de código (NCLOC) | 6.204 |
| Duplicación | 0,0% |
| Cobertura reportada | 0,0% |
| Incidencias por KLOC | 11,93 |

El Quality Gate reportó `OK`, aunque la exportación no proporcionó condiciones individuales ni umbrales.

La cobertura reportada no cuenta con evidencia suficiente de importación para interpretarse como cobertura efectiva de las pruebas.

### 39.3. Consolidación D1–D5

**D1 — Esfuerzo:** Se conservan como N/D las mediciones de tokens, costos y tiempos que no cuentan con telemetría verificable. No se combinan arbitrariamente registros de Gemini CLI y Codex.

**D2 — Calidad:** Se incorporan las métricas reales de SonarQube. Se documentan tres bugs, una vulnerabilidad y 70 code smells, aun cuando el Quality Gate sea OK.

**D3 — Especificaciones:** Se conservan los artefactos aprobados, los 35 requisitos funcionales, los 38 escenarios y las 38 tareas completadas. Las métricas normalizadas que carecen de extracción reproducible permanecen N/D.

**D4 — Cumplimiento:** Se mantienen los resultados verificables: 97/97 pruebas backend, 13/13 frontend, compilación de producción exitosa, 9/9 pruebas Docker aisladas y benchmark Locust histórico validado.

**D5 — Intervenciones:** Se preserva el registro de correcciones, bloqueos y cambios de agente, con atribución diferenciada para Gemini CLI y Codex.

### 39.4. Limitaciones de reproducibilidad

El análisis SonarQube fue ejecutado sobre una copia temporal aislada.

Aunque permitió finalizar el análisis, la exportación no identifica una revisión Git exacta ni demuestra equivalencia completa con el árbol de trabajo original.

Tampoco se dispone de identificadores de análisis y metadatos suficientes para reconstruir todas las condiciones del Quality Gate.

Estas limitaciones deben señalarse en el informe académico.

### 39.5. Decisión humana

**GO — Cierre documental de la Etapa 3.**

Se consideran completadas las actividades de implementación, pruebas funcionales, benchmark y análisis estático previstas en el proceso ejecutado.

La consolidación experimental está disponible para revisión, conservando explícitamente los indicadores N/D.

Se autoriza únicamente la revisión final de consistencia, procedencia y documentación, sin nuevas iteraciones de implementación.

**Estado:** ETAPA 3 — EVIDENCIA CONSOLIDADA — CIERRE DOCUMENTAL PENDIENTE.

---


**Cierre final de documentación (complemento de la sección 41; sin nuevo hito):** la evidencia de ejecución registrada indica SonarScanner 5.1.0, SonarQube 26.9.0, snapshot aislado y 23 archivos indexados. No se asigna revisión Git. Quality Gate exportado `OK` no incluye condiciones; coverage exportada 0.0% carece de contexto verificable de importación. Se confirma que el informe final conserva métricas disponibles y marca como N/D D1 y submétricas D3 sin evidencia. La atribución Gemini CLI/Codex permanece separada. Se acepta el paquete documental para revisión humana, sujeto a las limitaciones de reproducibilidad indicadas en el informe.
