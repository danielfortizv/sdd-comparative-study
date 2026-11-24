# E3 OpenSpec — Registro de continuación y descubrimiento

**Nombre recomendado:** `E3_OPENSPEC_REGISTRO_CONTINUACION_DESCUBRIMIENTO_2026-11-16.md`

**Ubicación:** `Etapa 3/_experiment_logs/OpenSpec/`

**Fecha:** 16 de noviembre de 2026  
**Iteración:** N/D (número histórico no proporcionado)  
**Caso de estudio:** Shift Bank  
**Etapa:** 3 — Opción A  
**Framework SDD:** OpenSpec  
**Agente implementador:** OpenAI Codex CLI

## 1. Objetivo

Continuar la tercera etapa de Shift Bank a partir del cierre experimental de OpenSpec E2, preservando el estado heredado y preparando las decisiones necesarias para especificar las nuevas capacidades de cifrado, auditoría inmutable, pruebas de carga y despliegue.

## 2. Estado inicial

La Etapa 2 de OpenSpec se encontraba cerrada experimentalmente.

Resultados reportados de E2:

- 22/22 tareas completadas.
- 22 pruebas backend aprobadas.
- 5 pruebas frontend aprobadas.
- Build de producción satisfactorio.
- Validación estricta OpenSpec aprobada.
- 91 escenarios de especificación.
- Quality Gate inicial y final: OK.
- 5 bugs y 41 Code Smells reportados en ambos análisis.
- Auditoría funcional: 15 PASS, 5 PARTIAL, 0 FAIL y 1 NOT EXECUTED.

Versiones históricas conocidas:

- OpenSpec: 1.11.0.
- Codex CLI al cierre de E2: 0.168.0.
- Versión y modelo efectivos de la sesión E3: N/D.

La implementación utiliza Python/FastAPI, React/TypeScript/Vite y persistencia SQLite directa.

## 3. Acciones realizadas

Según el reporte de preparación atribuido a Codex, el 16 de noviembre de 2026:

1. Se preparó el directorio independiente de OpenSpec E3 a partir de su propia E2.
2. Se copiaron 62 archivos.
3. Se verificaron 50 coincidencias SHA-256 respecto del manifiesto final de E2.
4. Se identificaron 12 archivos adicionales correspondientes a adaptadores OpenSpec heredados de `.gemini`.
5. Se ejecutaron las regresiones backend y frontend.
6. Se comprobó la compilación de producción.
7. Se ejecutó la validación estricta de OpenSpec.
8. Se verificó byte a byte la semilla común `SEED-3.md`.
9. Se conservó intacta la Etapa 2.
10. Se inició el descubrimiento de E3.

No se reportó implementación funcional de los nuevos requisitos.

## 4. Contratos heredados

El cambio `stage2-banking-enhancements` permanece activo, con sus 22 tareas completadas, sin archivar ni sincronizar.

Se identificó que el contrato funcional efectivo comprende cuatro especificaciones principales y siete especificaciones delta heredadas.

El desarrollo de E3 deberá conservar las funcionalidades de cuentas, saldos, transferencias internas, ACH, beneficiarios, MFA, pagos recurrentes y límites dinámicos.

## 5. Decisiones humanas

Las decisiones materiales propuestas para aprobación del investigador se agrupan en:

- D-E3-01: alcance de cifrado sensible, protección de claves, fallos seguros y migración.
- D-E3-02: auditoría append-only, encadenamiento criptográfico, atomicidad y modelo de amenazas.
- D-E3-03: parámetros de Locust, distribución de operaciones, SLOs y aislamiento.
- D-E3-04: despliegue local mediante contenedores, HTTPS, persistencia y secretos externos.

**Estado de aprobación al redactar este registro:** pendiente.

No se ha autorizado la implementación de E3. Tampoco se ha acreditado una aprobación nueva de especificaciones.

## 6. Archivos afectados

**Directorio de trabajo:** `Etapa 3/OpenSpec/`

**Directorio de evidencia:** `Etapa 3/_experiment_logs/OpenSpec/`

Archivos copiados según reporte: 62.

De ellos, 50 presentan coincidencia con el manifiesto SHA-256 de E2 y 12 corresponden a adaptadores adicionales heredados.

Inventario detallado de rutas modificadas o añadidas: N/D en la evidencia aportada a esta conversación.

`SEED-3.md`: integridad verificada según Codex.

No se han identificado modificaciones funcionales de E3 en este registro.

## 7. Pruebas y verificaciones

| Verificación | Resultado reportado |
|---|---|
| SHA-256 | 50/50 coincidencias |
| Backend | 22/22 PASS |
| Frontend | 5/5 PASS |
| Build TypeScript/Vite | PASS |
| OpenSpec strict validation | 5 PASS, 0 FAIL |
| Semilla común | Verificada byte a byte |
| Aislamiento de E2 | Sin modificaciones reportadas |

**Nivel de evidencia:** resultados comunicados por Codex; los artefactos crudos no fueron inspeccionados independientemente durante esta conversación.

No se realizaron nuevas ejecuciones para redactar este registro.

## 8. Errores, riesgos y correcciones

Errores técnicos nuevos confirmados: N/D.

Bloqueos técnicos confirmados: ninguno reportado.

Riesgos pendientes:

- Interpretar incompletamente las especificaciones heredadas debido al cambio E2 todavía activo.
- Implementar requisitos de seguridad sin una frontera funcional previamente aprobada.
- Reducir la comparabilidad experimental al adoptar decisiones técnicas particulares de otras herramientas.
- Confundir afirmaciones del agente con resultados independientemente verificados.

Correcciones ejecutadas durante esta continuación: N/D.

## 9. Métricas disponibles

### D1 — Esfuerzo y consumo

Tokens de entrada: N/D.  
Tokens de caché: N/D.  
Tokens de salida: N/D.  
Costo: N/D.  
Mensajes: N/D.  
Llamadas a herramientas: N/D.  
Tiempo: N/D.

### D2 — Calidad del código

Resultados históricos E2 conocidos: 5 bugs, 41 Code Smells y Quality Gate OK en ambos cortes.

Medición propia de E3: pendiente.

### D3 — Especificaciones

Escenarios de especificación reportados en E2: 91.

Cantidad y líneas de nuevas especificaciones E3: N/D; todavía no generadas.

### D4 — Expectativa funcional

Matriz externa de aceptación E3: AC-01 a AC-16.

Evaluación de ejecución E3: pendiente.

### D5 — Retroalimentación

Se identificaron cuatro grupos de decisiones materiales que requieren aprobación del investigador.

Número de mensajes y correcciones normalizados: N/D.

## 10. Desviaciones metodológicas

Se conserva el cambio de agente de Gemini CLI a OpenAI Codex CLI, documentado previamente durante E2.

Debe registrarse la versión y el modelo efectivo de E3 sin asumir que coinciden con la configuración histórica.

La documentación común E3 se utiliza para alinear requisitos y criterios de evaluación, no para transferir soluciones ni defectos particulares de otras herramientas.

## 11. Estado final

**Avance global estimado de OpenSpec E3: 10 %.**

Preparación y migración: completadas según Codex.

Descubrimiento inicial: reportado como realizado.

Decisiones E3: pendientes de aprobación.

Especificaciones nuevas E3: pendientes.

Implementación, Locust, despliegue, SonarQube y cierre D1–D5: pendientes.

## 12. Próximos pasos

1. Obtener la aprobación explícita de las cuatro decisiones materiales.
2. Generar los artefactos E3 mediante el workflow nativo de OpenSpec.
3. Validar las especificaciones y solicitar aprobación del investigador.
4. Implementar las capacidades aprobadas con verificaciones focalizadas.
5. Ejecutar mediciones, evaluación de calidad y cierre académico basado en evidencia reproducible.

# E3 OpenSpec — Registro de especificación y validación

**Archivo recomendado:** `E3_OPENSPEC_REGISTRO_02_ESPECIFICACIONES.md`

**Fecha:** 16 de noviembre de 2026  
**Iteración:** Ciclo de especificaciones E3; ordinal de interacción N/D  
**Caso:** Shift Bank — Etapa 3, Opción A  
**Framework SDD:** OpenSpec 1.11.0  
**Agente:** OpenAI Codex CLI  
**Cambio:** `stage3-banking-security-load-deployment`

## 1. Objetivo

Transformar los requisitos aprobados de la tercera etapa en especificaciones verificables mediante el flujo nativo de OpenSpec, conservando el contrato funcional heredado de E1/E2 y evitando modificaciones prematuras de la implementación.

## 2. Estado inicial

La preparación de E3 se encontraba terminada según el reporte anterior de Codex.

Se disponía de una copia independiente de E2, con 50 coincidencias SHA-256 verificadas, pruebas heredadas aprobadas y semilla E3 intacta.

No existía implementación funcional de los nuevos requisitos de cifrado, auditoría, carga o despliegue.

El cambio histórico `stage2-banking-enhancements` permanecía activo, con sus 22 tareas completadas.

## 3. Acciones realizadas

Codex utilizó OpenSpec 1.11.0 y su esquema `spec-driven`.

El flujo ejecutado incluyó:

1. Lectura del contexto disponible y los contratos heredados.
2. Inspección de versión, esquemas e instrucciones nativas.
3. Creación del cambio `stage3-banking-security-load-deployment`.
4. Generación de propuesta, diseño, especificaciones y tareas.
5. Verificación individual del nuevo cambio.
6. Validación estricta global del repositorio.
7. Recuento de requisitos y escenarios de aceptación.

No se ejecutó el flujo OpenSpec de implementación.

## 4. Archivos creados

Directorio:

`Etapa 3/OpenSpec/openspec/changes/stage3-banking-security-load-deployment/`

| Archivo | Líneas añadidas reportadas |
|---|---:|
| `proposal.md` | 28 |
| `design.md` | 39 |
| `tasks.md` | 35 |
| `specs/banking-data-protection/spec.md` | 53 |
| `specs/transaction-audit/spec.md` | 57 |
| `specs/load-testing/spec.md` | 57 |
| `specs/local-deployment/spec.md` | 46 |
| `specs/banking-compatibility/spec.md` | 38 |
| **Total Markdown** | **353** |

El scaffold nativo también generó `.openspec.yaml`.

El agente reportó ocho archivos Markdown editados o creados, con 353 líneas añadidas.

Los cinco archivos `spec.md` representan 251 líneas de ese total. Estas cifras proceden de los conteos del diff reportado por Codex y todavía deben contrastarse con el inventario físico definitivo para calcular D3.

## 5. Decisiones y diseño

El prompt proporcionado estableció cuatro decisiones:

- D-E3-01: cifrado autenticado, protección en tránsito y reposo, migración y manejo de claves.
- D-E3-02: auditoría append-only, verificación criptográfica, atomicidad y concurrencia.
- D-E3-03: Locust con 30 usuarios, ramp-up 5/s, 60 segundos estables y mezcla 60/30/10.
- D-E3-04: Docker Compose, HTTPS, persistencia aislada, secretos externos y scheduler único.

Codex interpretó estas decisiones como aprobadas por aparecer expresamente en el prompt.

**Limitación de trazabilidad:** no consta en la salida proporcionada un registro independiente de aprobación humana anterior a la creación de las especificaciones.

Entre las decisiones técnicas documentadas se reportan cifrado autenticado con claves versionadas, migración transaccional idempotente, auditoría encadenada mediante mecanismo criptográfico autenticado, coordinación de escrituras SQLite y un único scheduler activo.

## 6. Contratos heredados

El agente reportó haber considerado cuatro especificaciones principales:

- `bank-accounts`
- `mfa`
- `transaction-history`
- `transfers`

También consideró siete deltas del cambio E2 activo:

- `bank-accounts`
- `mfa`
- `transaction-history`
- `transfers`
- `ach-transfers`
- `transfer-limits`
- `recurring-payments`

El cambio histórico no fue archivado, sincronizado ni modificado, según Codex.

## 7. Verificaciones y resultados

| Verificación | Resultado |
|---|---|
| Versión OpenSpec | 1.11.0 |
| Validación del cambio nuevo | PASS |
| `openspec.cmd validate --all --strict` | 6 PASS, 0 FAIL |
| Requisitos nuevos | 18 |
| Escenarios de aceptación | 43 |
| Pruebas backend nuevas | No ejecutadas |
| Pruebas frontend nuevas | No ejecutadas |
| Build E3 | No ejecutado |
| Locust | No ejecutado |
| SonarQube E3 | No ejecutado |

Los resultados de validación corresponden a artefactos de OpenSpec, no a pruebas funcionales de la aplicación.

La ejecución reportada se limitó a especificaciones.

## 8. Errores, incidencias y riesgos

No se reportaron errores finales de validación.

Durante el descubrimiento se intentó localizar un archivo de reglas de Tessl y el contrato común E2 en rutas que no existían.

Codex informó que utilizó el paquete de preparación E3 y las especificaciones heredadas disponibles. No se aportó evidencia de acceso a código de otras herramientas.

Se identificaron cambios preexistentes no relacionados en el worktree. El agente informó que permanecieron intactos.

Las especificaciones fueron validadas estructuralmente, pero su contenido completo no fue inspeccionado independientemente durante esta revisión.

## 9. Métricas D1–D5

### D1 — Esfuerzo y consumo

- Tok In: N/D.
- Tok Cache: N/D.
- Tok Out: N/D.
- Costo: N/D.
- Msgs normalizados: N/D.
- Tool Calls: N/D.
- Tiempo estandarizado de procesamiento: N/D.

La interfaz de Codex mostró `Worked for 4m 4s`. Se conserva como indicador de duración presentado por la herramienta, sin asumir que equivale al tiempo activo normalizado de D1.

### D2 — Calidad del código

No se implementó ni analizó código nuevo mediante SonarQube durante esta iteración.

### D3 — Especificaciones

- Artefactos Markdown nuevos: 8.
- Líneas Markdown añadidas reportadas: 353.
- Especificaciones de capacidades: 5 archivos.
- Líneas en los cinco `spec.md`: 251, según el diff.
- Requisitos reportados: 18.
- Escenarios de aceptación: 43.
- Densidad de los cinco `spec.md`: 50,2 líneas por archivo.
- Ratio código/especificación: N/D.

La selección oficial de archivos D3 debe confirmarse con el criterio homogéneo de la guía.

### D4 — Expectativa funcional

No se ejecutaron casos externos de aceptación AC-01 a AC-16.

Estado de cumplimiento funcional de E3: no verificado.

### D5 — Retroalimentación

Se utilizó un prompt principal para la generación de especificaciones, seguido por acciones autónomas del agente.

No se reportaron solicitudes adicionales de decisiones materiales durante esta ejecución.

Las interacciones normalizadas y llamadas a herramientas requieren consulta de la telemetría original.

## 10. Desviaciones metodológicas

Se mantiene la desviación histórica asociada al uso de OpenAI Codex CLI en sustitución del agente Gemini CLI inicialmente previsto por el estudio.

El agente no encontró todas las fuentes complementarias en las rutas solicitadas.

Se preservó la independencia de la implementación OpenSpec frente a otras herramientas SDD.

La aprobación humana de las especificaciones todavía debe registrarse explícitamente antes del siguiente bloque funcional.

## 11. Estado final

**Avance global estimado E3: 24 %.**

Se completó la generación de especificaciones y se obtuvo validación estricta satisfactoria según Codex.

La implementación de E3 no ha comenzado.

Quedan pendientes la aprobación del contrato de especificación, la implementación de cifrado y auditoría, Locust, despliegue, SonarQube y cierre académico.

## 12. Próximo paso

Registrar la aprobación explícita del cambio `stage3-banking-security-load-deployment` y ejecutar el primer bloque de implementación mediante el flujo nativo OpenSpec.

El primer bloque abarcará cifrado, migración de datos heredados, integración frontend/backend y regresión bancaria.

La auditoría inmutable se implementará posteriormente, una vez verificados los resultados del cifrado.

# Shift Bank — Etapa 3 — OpenSpec
## Registro académico: Bloque 1 — Cifrado y migración

**Fecha:** 2026-11-16  
**Herramienta SDD:** OpenSpec 1.11.0  
**Agente implementador:** OpenAI Codex CLI  
**Cambio:** `stage3-banking-security-load-deployment`  
**Fase:** Implementación de cifrado de datos sensibles  
**Estado:** Bloque 1 completado según la verificación del agente  
**Avance global estimado:** 45 %

### 1. Objetivo

Implementar el primer bloque funcional de la Etapa 3, correspondiente a la protección criptográfica de información bancaria sensible, migración segura de registros existentes e integración con las operaciones heredadas de Shift Bank.

La implementación debía conservar el comportamiento de cuentas, transferencias internas, ACH, beneficiarios, MFA y programaciones recurrentes.

### 2. Estado inicial

La preparación y especificación de Etapa 3 estaban completadas.

El cambio OpenSpec contaba con:

| Indicador | Valor |
|---|---:|
| Requisitos | 18 |
| Escenarios de aceptación | 43 |
| Especificaciones de capacidades | 5 |
| Tareas de implementación | 21 |
| Tareas inicialmente completadas | 0 |
| Validación estricta de especificaciones | 6 aprobadas |

El código había sido heredado de la implementación final de OpenSpec E2 y verificado mediante regresiones.

### 3. Implementación realizada

El agente utilizó el flujo nativo `openspec-apply-change`.

Se implementó cifrado autenticado AES-256-GCM para los identificadores bancarios sensibles de beneficiarios, datos ACH y programaciones recurrentes.

El esquema emplea nonces aleatorios de 96 bits y metadatos autenticados que vinculan los valores cifrados con su tabla, registro y campo.

Las claves se suministran externamente, mediante variables de entorno o archivo de claves, y utilizan identificadores versionados para permitir rotación.

Se implementó una migración de datos SQLite heredados que transforma los campos sensibles en representaciones cifradas. El agente reportó comportamiento idempotente, validación del contenido cifrado y rollback ante errores.

Se conservaron los flujos bancarios autorizados mediante descifrado en el backend.

Para la protección en tránsito, se implementó el rechazo de solicitudes sensibles realizadas mediante HTTP y controles equivalentes en el frontend.

### 4. Archivos modificados

**Archivos creados:**

- `backend/encryption.py`
- `backend/SECURITY.md`
- `backend/tests/test_encryption.py`
- `frontend/src/api.mjs`
- `frontend/src/api.d.mts`

**Archivos modificados:**

- `backend/banking.py`
- `backend/database.py`
- `backend/main.py`
- `backend/requirements.txt`
- `backend/tests/test_api.py`
- `backend/tests/test_banking.py`
- `frontend/src/App.tsx`
- `frontend/tests/validation.test.mjs`
- `openspec/changes/stage3-banking-security-load-deployment/design.md`
- `openspec/changes/stage3-banking-security-load-deployment/tasks.md`

Se añadió la dependencia `cryptography>=42,<51`; el agente reportó la versión instalada 50.0.2.

### 5. Errores y correcciones

Durante el proceso se registraron fallos en pruebas inicialmente ejecutadas y problemas de invocación de comandos.

El agente corrigió una prueba de alteración criptográfica para modificar efectivamente un byte cifrado y no únicamente los bits no utilizados de su representación Base64.

Una regresión backend reveló que cierta respuesta de historial todavía contenía información cifrada. Se corrigió la ruta de descifrado, preservando la protección en el almacenamiento y los valores autorizados de la API.

También se ajustaron las pruebas de integración y el tratamiento de claves versionadas.

La implementación final incluyó un escenario de migración para recifrar registros bajo una versión de clave activa más reciente antes de retirar la anterior.

### 6. Verificación final

| Verificación | Resultado |
|---|---|
| Pruebas backend | 35 aprobadas |
| Pruebas frontend | 8 aprobadas |
| Build TypeScript/Vite | Aprobado |
| Validación estricta OpenSpec | 6 aprobadas, 0 fallidas |
| Tareas completadas | 7 de 21 |
| Tareas pendientes | 14 |

Las pruebas reportadas cubrieron cifrado y descifrado, detección de alteraciones, claves inválidas o ausentes, rotación, migración, rollback, reinicio, HTTPS y regresión bancaria heredada.

Las pruebas utilizaron datos sintéticos, bases SQLite temporales y certificados de prueba.

### 7. Métricas de esfuerzo

| Métrica | Valor |
|---|---|
| Tiempo mostrado por Codex | 16 min 58 s |
| Tokens de entrada | N/D |
| Tokens cacheados | N/D |
| Tokens de salida | N/D |
| Tool Calls | N/D |
| Costo | N/D |

El tiempo corresponde al indicador mostrado por Codex y no equivale necesariamente al tiempo total activo de procesamiento.

No se dispone de telemetría adicional suficientemente verificada para este bloque.

### 8. Consideraciones de seguridad

El servidor puede descifrar los datos para ejecutar operaciones autorizadas. Por tanto, el diseño debe describirse como protección de transporte y almacenamiento con descifrado autorizado en el backend, sin atribuirle propiedades de conocimiento cero.

Las claves externas y su custodia constituyen una responsabilidad operativa que deberá verificarse durante el despliegue.

Los controles HTTPS se validaron mediante pruebas, pero la terminación TLS del sistema desplegado sigue pendiente.

Se identificó una modificación del documento `design.md` durante la implementación relacionada con la separación de claves. Debe comprobarse su coherencia con el diseño previamente aprobado y conservar su justificación. No se presume incumplimiento únicamente por la existencia de esta edición.

### 9. Evaluación metodológica

La implementación respetó la separación entre especificación y código, al ejecutarse después de la autorización del investigador.

El agente utilizó el flujo nativo de OpenSpec, actualizó las tareas correspondientes y ejecutó pruebas de regresión.

Se preservó el aislamiento respecto a las implementaciones de las otras herramientas y a las etapas anteriores.

No se implementaron funcionalidades de auditoría, pruebas de carga ni despliegue durante este bloque.

### 10. Estado y próximo paso

El Bloque 1 se considera completado de acuerdo con los resultados reportados por Codex.

La siguiente actividad es el **Bloque 2: auditoría transaccional inmutable y atomicidad financiera**, con pruebas de integridad, fallos y concurrencia multiproceso.

Las tareas pendientes de Locust, Docker Compose, SonarQube y cierre se mantienen fuera de este bloque.

**Resultado: BLOQUE 1 COMPLETADO — APTO PARA CONTINUAR CON EL BLOQUE 2.**

# Shift Bank — Etapa 3 — OpenSpec
## Registro académico: Bloque 2 — Auditoría transaccional y atomicidad

**Fecha:** 16 de noviembre de 2026  
**Herramienta SDD:** OpenSpec 1.11.0  
**Agente:** OpenAI Codex CLI  
**Cambio:** `stage3-banking-security-load-deployment`  
**Estado:** Bloque 2 completado según el reporte del agente  
**Avance global estimado:** 65 %

### 1. Objetivo

Implementar la auditoría transaccional inmutable dentro del modelo de amenazas aprobado, preservar la consistencia financiera ante errores y comprobar las garantías de integridad mediante pruebas funcionales, de concurrencia y de fallo.

### 2. Estado inicial

El Bloque 1 había terminado con cifrado de datos sensibles y migración SQLite. El cambio OpenSpec tenía 7 de 21 tareas completadas.

El estado previo registraba 35 pruebas backend aprobadas, 8 pruebas frontend aprobadas y validación estricta correcta.

### 3. Implementación realizada

Se creó un módulo de auditoría basado en eventos canónicos enlazados mediante HMAC-SHA-256, utilizando una clave de auditoría proporcionada externamente.

Se implementaron restricciones SQLite para impedir operaciones ordinarias de modificación o eliminación de registros de auditoría, así como un mecanismo de verificación de la cadena y su punto de control.

Se integraron eventos de auditoría con operaciones financieras, incluyendo transferencias internas, ACH, límites, beneficiarios, MFA y pagos recurrentes.

La persistencia financiera y sus registros de auditoría utilizan transacciones SQLite coordinadas, con rollback cuando falla la escritura del evento requerido.

Se habilitó verificación administrativa protegida mediante HTTPS y autorización diferenciada.

### 4. Pruebas de integridad y concurrencia

La implementación fue sometida a pruebas de:

- Alteración, eliminación, inserción y reordenamiento de registros.
- Integridad de cadena después de reinicio.
- Fallos inducidos de persistencia.
- Rechazos por MFA y sus eventos de auditoría.
- Consistencia de saldos y límites ante rollback.
- Concurrencia mediante procesos independientes.
- Lecturas y escrituras simultáneas sobre conexiones SQLite separadas.

La prueba multiproceso utilizó cuatro procesos del sistema operativo, cada uno realizando seis transferencias y consultas. Se reportaron 24 transferencias completadas y 25 eventos de auditoría con cadena válida.

Una prueba de dos conexiones confirmó que los lectores podían observar la instantánea previamente confirmada hasta que el escritor completara atómicamente la actualización financiera y su evento de auditoría.

### 5. Incidentes y correcciones

Durante la ejecución se encontraron y corrigieron inconsistencias en fixtures de prueba, manejo de conexiones y expectativas sobre el orden de detección de alteraciones de la cadena.

También se identificó que las dependencias frontend no estaban instaladas en la copia de trabajo, lo que inicialmente impedía ejecutar el build. Se instalaron desde el lockfile y posteriormente el build se completó.

Se documentó que el diseño de cifrado del Bloque 1 emplea claves de datos versionadas proporcionadas externamente, en lugar de una jerarquía obligatoria de claves envueltas. Codex consideró esta decisión compatible con las especificaciones aprobadas.

El agente configuró SQLite en modo WAL, con tiempo de espera de 250 ms para bloqueos y reintentos acotados. Este comportamiento deberá observarse durante las pruebas de carga posteriores.

### 6. Resultados de verificación

| Verificación | Resultado |
|---|---|
| Pruebas de auditoría | 13 aprobadas |
| Regresión backend completa | 48 aprobadas |
| Regresión frontend completa | 8 aprobadas |
| Build TypeScript/Vite | Aprobado |
| Validación estricta OpenSpec | 6 aprobadas, 0 fallidas |
| Tareas OpenSpec completadas | 13/21 |
| Nuevas tareas completadas en Bloque 2 | 6 |

El agente reportó evidencia de atomicidad financiera ante fallos inducidos y consistencia criptográfica de los eventos registrados.

### 7. Archivos afectados

Se creó `backend/audit.py` y `backend/tests/test_audit.py`.

Se modificaron componentes de `backend/banking.py`, `backend/database.py`, `backend/main.py`, la configuración documental de seguridad, los fixtures de prueba y el checklist de tareas del cambio OpenSpec.

La evidencia técnica se registró en:

`Etapa 3/_experiment_logs/OpenSpec/pruebas/E3_OPENSPEC_BLOCK2_AUDIT.md`

### 8. Métricas de esfuerzo

| Métrica | Valor |
|---|---|
| Duración mostrada por Codex | 18 min 31 s |
| Tokens de entrada | N/D |
| Tokens de caché | N/D |
| Tokens de salida | N/D |
| Llamadas a herramientas | N/D |
| Costo | N/D |

La duración corresponde al indicador visible de ejecución y no representa necesariamente tiempo activo de procesamiento. No se calcularon costos sin evidencia de consumo y tarifas.

### 9. Limitaciones

El esquema de auditoría proporciona resistencia a modificaciones ordinarias y capacidad de detección criptográfica dentro del modelo de amenazas acordado. No constituye una garantía absoluta frente a un adversario con control completo de la base de datos, aplicación y secretos.

No se ha evaluado todavía el rendimiento bajo la carga común de E3 ni el comportamiento del sistema dentro de los contenedores definitivos.

Durante la instalación frontend se reportaron tres advertencias de dependencias, sin que el agente efectuara actualizaciones adicionales.

### 10. Evaluación metodológica y continuidad

El agente siguió el flujo nativo `openspec-apply-change`, implementó tareas del cambio previamente aprobado, realizó correcciones a partir de pruebas y preservó los resultados de regresión.

El Bloque 2 se considera completado según la evidencia reportada. No se ejecutaron pruebas Locust, despliegue Docker ni análisis SonarQube en esta iteración.

La siguiente fase corresponde al Hito 5 del protocolo E3: ejecución del benchmark Locust con 30 usuarios, subida de 5 usuarios/s, 60 segundos de estado estable, mezcla 60/30/10 y verificación de los umbrales de latencia y errores establecidos.

**Resultado: BLOQUE 2 COMPLETADO. CONTINUACIÓN AUTORIZABLE HACIA EL BLOQUE 3 — LOCUST.**

# Shift Bank — Etapa 3 — OpenSpec
## Registro académico: Bloque 3 — Pruebas de carga con Locust

**Fecha:** 16 de noviembre de 2026  
**Herramienta SDD:** OpenSpec 1.11.0  
**Agente:** OpenAI Codex CLI  
**Cambio:** `stage3-banking-security-load-deployment`  
**Estado:** Bloque 3 completado según Codex  
**Avance global estimado:** 75 %

### 1. Objetivo

Implementar un banco de pruebas de carga reproducible para Shift Bank mediante Locust, evaluando el rendimiento de consultas y transferencias reales bajo el perfil común de la Etapa 3.

La evaluación debía preservar las reglas financieras, los mecanismos de cifrado y la auditoría transaccional, utilizando exclusivamente una base de datos sintética aislada.

### 2. Estado inicial

Antes del Bloque 3 se habían completado 13 de las 21 tareas del cambio OpenSpec.

La aplicación contaba con protección criptográfica de datos sensibles, migración SQLite, auditoría encadenada mediante HMAC-SHA-256, pruebas de atomicidad financiera y regresiones aprobadas.

### 3. Implementación

Codex utilizó el flujo nativo de implementación de OpenSpec.

Se incorporó un módulo de pruebas en `backend/loadtest/`, compuesto por el archivo de tareas Locust, utilidades de cálculo y un ejecutor reproducible.

Se añadió `backend/requirements-loadtest.txt` y un conjunto de pruebas automatizadas de las métricas y condiciones del benchmark.

El ejecutor creó un entorno temporal con:

- Base SQLite sintética seleccionada mediante `SHIFT_BANK_DB`.
- Claves de cifrado y auditoría desechables.
- Certificado TLS de prueba con verificación habilitada.
- Proceso FastAPI real sobre HTTPS.
- Recopilación de eventos individuales de Locust.

Se aplicaron pesos 6:3:1 para aproximar la distribución funcional aprobada, verificando posteriormente las proporciones observadas.

### 4. Configuración experimental

| Parámetro | Valor |
|---|---:|
| Usuarios concurrentes | 30 |
| Tasa de incorporación | 5 usuarios/s |
| Ramp-up medido | 5,029 s |
| Estado estable verificado | 60,003 s |
| Consultas de saldo esperadas | 60 % |
| Consultas de historial esperadas | 30 % |
| Transferencias esperadas | 10 % |
| SLO p95 lecturas | Menor a 200 ms |
| SLO p95 transferencias | Menor a 500 ms |
| Errores inesperados permitidos | Menos del 1 % |

La medición de estado estable se efectuó después de constatar la activación de los 30 usuarios.

### 5. Resultados de RUN_01

**Identificador:** `RUN_01_20261116T201253Z`

| Operación | Solicitudes estables | Distribución | p50 | p95 | p99 |
|---|---:|---:|---:|---:|---:|
| Saldos | 4.471 | 60,443 % | 8,291 ms | 47,391 ms | 251,434 ms |
| Historial | 2.195 | 29,674 % | 26,805 ms | 177,468 ms | 348,980 ms |
| Transferencias internas | 731 | 9,882 % | 40,479 ms | 437,330 ms | 1.091,890 ms |
| Lecturas combinadas | 6.666 | 90,118 % | 16,460 ms | 121,835 ms | 416,632 ms |

Se observaron **7.397 solicitudes durante el estado estable**, equivalentes a 123,277 solicitudes/s.

La ejecución completa, incluyendo ramp-up, produjo 7.755 solicitudes, con rendimiento promedio reportado de 119,250 solicitudes/s.

No se reportaron errores inesperados, rechazos bancarios esperados ni fallos de Locust.

### 6. Integridad financiera y auditoría

Durante la ejecución completa se completaron 766 transferencias internas.

Se contrastaron con 766 transacciones persistidas y sus eventos de auditoría correspondientes.

Los saldos finales reportados fueron:

| Cuenta | Saldo final |
|---|---:|
| Checking | COP 4.999.234,00 |
| Savings | COP 15.000.766,00 |
| **Total conservado** | **COP 20.000.000,00** |

La cadena de auditoría se verificó como válida con 767 entradas.

### 7. Incidentes y correcciones

Durante el desarrollo del ejecutor se realizaron ajustes a las importaciones y a la recopilación de métricas del benchmark.

La ejecución completa de pruebas backend encontró una interferencia causada por la importación de Locust durante el descubrimiento de `unittest`. La carga de Locust aplicaba modificaciones de `gevent` a módulos de sockets y threading, afectando las pruebas heredadas de API.

Codex corrigió la prueba de pesos de tareas para analizar los decoradores mediante el AST de Python sin importar Locust.

Las pruebas de regresión volvieron a completarse satisfactoriamente.

### 8. Verificación final

| Indicador | Resultado |
|---|---|
| Pruebas backend | 53 aprobadas |
| Pruebas frontend | 8 aprobadas |
| Build TypeScript/Vite | Aprobado |
| OpenSpec estricto | 6 aprobadas, 0 fallidas |
| Tareas OpenSpec completadas | 17/21 |
| Tareas nuevas completadas | 4 |
| Umbrales de aceptación | Todos aprobados |

### 9. Análisis de resultados

El sistema cumplió los criterios establecidos para latencia p95 y tasa de errores inesperados.

Sin embargo, el tiempo p99 de transferencias alcanzó 1.091,890 ms. Este resultado evidencia una cola de latencia superior a un segundo, aunque no constituye incumplimiento de los SLO definidos.

Los resultados corresponden al entorno aislado de FastAPI utilizado para Locust y no deben interpretarse automáticamente como rendimiento de la futura implementación contenedorizada.

El funcionamiento de la auditoría y las operaciones financieras fue preservado durante el benchmark.

### 10. Métricas de esfuerzo

| Métrica | Valor |
|---|---|
| Duración mostrada por Codex | 20 min 1 s |
| Tokens de entrada | N/D |
| Tokens cacheados | N/D |
| Tokens de salida | N/D |
| Tool Calls | N/D |
| Costo | N/D |

No se inventaron métricas de CPU, memoria, tokens o consumo financiero ausentes en los registros.

### 11. Evidencias

Las evidencias originales se encuentran en:

`Etapa 3/_experiment_logs/OpenSpec/locust/`

Archivos principales:

- `E3_OPENSPEC_LOCUST_METODOLOGIA.md`
- `E3_OPENSPEC_LOCUST_RUN_01.json`
- `E3_OPENSPEC_LOCUST_EVALUATION.md`
- CSV de solicitudes individuales, estadísticas, fallos y usuarios activos.
- Registros de ejecución y del servidor.

RUN_01 debe conservarse sin modificaciones para garantizar la reproducibilidad.

### 12. Continuidad

El Bloque 3 se considera completado según la evidencia reportada por Codex.

La siguiente actividad corresponde al despliegue local mediante Docker Compose, HTTPS, almacenamiento persistente, secretos externos y scheduler único.

**Resultado: BLOQUE 3 COMPLETADO — LISTO PARA BLOQUE 4 DE DESPLIEGUE.**

# Shift Bank — Etapa 3 — OpenSpec
## Registro académico: Bloque 4 — Despliegue seguro

**Fecha:** 16 de noviembre de 2026  
**Framework:** OpenSpec 1.11.0  
**Agente:** Codex CLI  
**Cambio:** `stage3-banking-security-load-deployment`  
**Estado:** Bloque 4 completado según la salida de Codex  
**Avance global estimado:** 85 %

### 1. Objetivo

Implementar y comprobar el despliegue local de Shift Bank mediante contenedores, conservando cifrado, auditoría, operaciones financieras, persistencia y ejecución única de tareas programadas.

### 2. Estado inicial

El cambio OpenSpec tenía 17 de 21 tareas completadas.

Se habían implementado el cifrado, la auditoría transaccional y las pruebas de carga. El benchmark Locust RUN_01 había aprobado los umbrales establecidos.

### 3. Implementación

Se implementó un despliegue Docker Compose compuesto por un backend FastAPI/Uvicorn y un frontend de producción servido mediante Nginx.

Se incorporaron HTTPS, redirección HTTP, proxy inverso, healthchecks, almacenamiento SQLite persistente, ejecución sin privilegios root y provisión externa de secretos.

Se configuró un único proceso backend encargado de la ejecución de ACH y programaciones recurrentes.

Se crearon archivos Dockerfile, configuración Compose y Nginx, scripts de generación de configuración local y herramientas de verificación funcional del despliegue.

### 4. Verificación operativa

La prueba final identificada como `DEPLOYMENT_20261116T211350Z` reportó 50 comprobaciones aprobadas de 50 ejecutadas.

Se verificaron rutas HTTPS, redirección, lectura de cuentas e historial, transferencias reales, protección de beneficiarios, autorización MFA, liquidación ACH y validación de la cadena de auditoría.

Se realizaron dos reinicios del backend y se comprobaron la persistencia de saldos, historial, datos cifrados y auditoría, así como la recuperación de programaciones sin duplicaciones reportadas.

Las pruebas también comprobaron el rechazo seguro del arranque ante ausencia de claves de cifrado, clave de auditoría o credencial administrativa.

### 5. Incidentes y correcciones

Durante el proceso existieron intentos fallidos de verificación por causas relacionadas con el propio ejecutor experimental y la configuración de la base de datos.

Se detectaron expectativas incorrectas sobre el endpoint de historial, esperas insuficientes para los healthchecks, errores en la comparación de resultados y una ruta SQLite que contenía una secuencia de salto de línea literal.

El agente corrigió estas condiciones, preservó los resultados intermedios y repitió los controles con una ruta normalizada.

La ejecución final quedó registrada con 50 verificaciones aprobadas.

También se corrigió una advertencia de inicialización de Nginx relacionada con la modificación de un archivo de configuración de solo lectura.

### 6. Resultados finales

| Indicador | Resultado |
|---|---|
| Pruebas de despliegue | 50/50 aprobadas |
| Pruebas backend | 53 aprobadas |
| Pruebas frontend | 8 aprobadas |
| Build TypeScript/Vite | Aprobado |
| Validación estricta OpenSpec | 6 aprobadas |
| Tareas OpenSpec | 21/21 completadas |
| Casos externos | AC-01, AC-12, AC-13 y AC-14 reportados como aprobados |
| Tiempo mostrado por Codex | 1 h 8 min 49 s |

Se reportaron tres advertencias de dependencias npm: una moderada y dos altas. No se realizaron actualizaciones de dependencias para resolverlas durante este bloque.

### 7. Aislamiento y preservación

El despliegue utilizó un proyecto Docker Compose independiente de las otras herramientas SDD.

Codex detuvo únicamente los contenedores de este experimento al terminar y conservó el volumen sintético para reproducibilidad.

No se modificaron las etapas anteriores ni se ejecutó SonarQube durante esta fase.

### 8. Evidencias

Se registraron los siguientes archivos principales en `Etapa 3/_experiment_logs/OpenSpec/pruebas/`:

- `E3_OPENSPEC_DEPLOYMENT_ACCEPTANCE.json`
- `E3_OPENSPEC_BLOCK4_DEPLOYMENT.md`
- `E3_OPENSPEC_DOCKER_ENVIRONMENT.md`
- `E3_OPENSPEC_BLOCK4_REGRESSION.md`

También se conservaron intentos fallidos, registros de construcción, arranque, correcciones y verificaciones posteriores.

### 9. Limitaciones

El despliegue fue local y utilizó certificados de prueba. No constituye una evaluación de confianza TLS pública ni de disponibilidad de producción.

El contenedor y su volumen emplearon datos sintéticos. La evaluación no incluyó un entorno bancario real.

No se dispone de telemetría confiable de tokens ni de costos para este bloque. El tiempo mostrado por Codex no necesariamente equivale al tiempo activo del agente.

### 10. Próxima fase

La implementación funcional E3 se encuentra terminada según el checklist OpenSpec.

Se inicia el Hito 7: medición de calidad SonarQube con cobertura importada, utilizando el proyecto independiente `Shift-Bank---Stage-3---OpenSpec`.

Posteriormente se realizará una ronda correctiva limitada y una segunda medición comparable, siguiendo los hitos 8 y 9 del protocolo.

**Resultado: BLOQUE 4 COMPLETADO — ETAPA 3 AL 85 % — SONARQUBE PENDIENTE.**

# Shift Bank — Etapa 3 — OpenSpec
## Hito 7: Ejecución del análisis inicial SonarQube

**Fecha:** 16 de noviembre de 2026  
**Herramienta SDD:** OpenSpec 1.11.0  
**Agente:** OpenAI Codex CLI, con ejecución local posterior mediante PowerShell  
**Proyecto SonarQube:** `Shift-Bank---Stage-3---OpenSpec`  
**Estado:** Análisis enviado exitosamente; pendiente de confirmar procesamiento del servidor  
**Avance global:** 85 %

### 1. Objetivo

Ejecutar la primera medición de calidad estática del código de Shift Bank E3, incorporando los informes de cobertura disponibles y preservando los resultados iniciales antes de realizar correcciones.

### 2. Incidentes previos

La automatización desarrollada inicialmente por Codex no pudo continuar debido a dos problemas:

1. Un intento de interpretar como JSON la versión del servidor, recibida como texto plano.
2. Una respuesta HTTP 403 al consultar el historial de análisis del proyecto.

Para superar estos bloqueos se ejecutó SonarScanner directamente mediante un script PowerShell independiente, evitando la consulta previa al historial. El token se suministró localmente sin mostrar su valor.

### 3. Ejecución

El análisis utilizó SonarScanner CLI 8.1.0.6389 y SonarQube Community Build 26.9.0.129388.

El scanner indexó 20 archivos y detectó cuatro lenguajes.

El analizador Python informó 10 archivos analizados, mientras que el componente JavaScript/TypeScript/CSS informó otros 10.

Se procesaron los reportes:

- `sonarqube/reports/backend-coverage-sonar.xml`
- `sonarqube/reports/frontend-lcov-sonar.info`

El resultado final del scanner fue `EXECUTION SUCCESS` y se informó que el reporte había sido cargado al servidor.

### 4. Identificación del análisis

**Compute Engine Task ID:** `ea27677b-df48-4d54-9b89-25ac686bce41`

**Analysis ID:** N/D, pendiente de obtener.

**Quality Gate:** N/D, pendiente de consultar.

**Hallazgos:** N/D, pendiente de consultar.

**Tiempo total de ejecución del scanner:** 46,643 segundos.

### 5. Evidencia

El registro original se encuentra en:

`Etapa 3/_experiment_logs/OpenSpec/sonarqube/E3_OPENSPEC_SONAR_SCAN_20261116T193919.log`

### 6. Consideraciones metodológicas

El éxito del scanner demuestra que el informe fue generado y enviado, pero todavía se debe confirmar el procesamiento del Compute Engine.

Se debe verificar que los archivos analizados coincidan con el ámbito de código productivo previsto, debido a la diferencia entre los 20 archivos indexados y los 14 archivos del inventario inicial.

La cobertura importada debe confirmarse con las métricas calculadas por SonarQube. No se debe asumir que el porcentaje de los informes previos coincide necesariamente con la cobertura agregada del proyecto.

No se realizaron correcciones de código durante esta medición.

### 7. Próximo paso

Recuperar las métricas D2, el estado del Quality Gate y el listado de hallazgos. Congelar la medición inicial y preparar una ronda correctiva basada exclusivamente en los problemas observados.

**Resultado: ESCANEO INICIAL ENVIADO CORRECTAMENTE. MÉTRICAS PENDIENTES DE CONSOLIDACIÓN.**


# Shift Bank — E3 OpenSpec
## Hito 7 — Auditoría inicial y limitación de acceso a SonarQube

**Fecha:** 16 de noviembre de 2026  
**Herramienta:** OpenSpec 1.11.0  
**Agente:** OpenAI Codex CLI  
**Estado:** Análisis enviado; recuperación de métricas pendiente  
**Avance global estimado:** 85 %

### Objetivo

Recuperar y documentar las métricas iniciales de calidad de SonarQube, sin modificar el código ni repetir el análisis.

### Resultados

El scanner confirmó `ANALYSIS SUCCESSFUL` y `EXECUTION SUCCESS`.

**Compute Engine Task ID:** `ea27677b-df48-4d54-9b89-25ac686bce41`

El agente intentó consultar los endpoints de tareas, historial, métricas, Quality Gate, incidencias y Security Hotspots, pero recibió respuestas HTTP 401.

Por tanto, no fue posible confirmar el procesamiento del servidor ni recuperar el identificador definitivo de análisis.

### Verificación del alcance

Se reconciliaron los 20 archivos indexados:

| Categoría | Archivos |
|---|---:|
| Producción backend | 5 |
| Producción frontend | 9 |
| Pruebas backend | 5 |
| Pruebas frontend | 1 |
| Total | 20 |

No se identificaron omisiones materiales en el alcance configurado.

### Cobertura disponible

| Indicador | Resultado |
|---|---|
| Cobertura backend mediante coverage.py | 89,28 % |
| Cobertura de tres módulos JS medidos | 100 % |
| Cobertura de interfaces React TSX | N/D |
| Cobertura consolidada de SonarQube | N/D |

El registro original del scanner confirmó el procesamiento de los informes de cobertura Python y JavaScript, pero no se recuperó todavía el porcentaje calculado por SonarQube.

### Limitación

La autenticación utilizada no permitió acceder a las API de lectura. Los códigos HTTP 401 no representan ausencia de defectos.

No se realizaron modificaciones al código, especificaciones ni configuración del análisis.

### Próximo paso

Utilizar una credencial de tipo User Token con permisos de lectura para recuperar y congelar la medición inicial. Posteriormente, realizar una única ronda correctiva y una medición final comparable.

**Estado: HITO 7 PENDIENTE DE CONSOLIDACIÓN.**

# Shift Bank — Etapa 3 — OpenSpec
## Hito 7 — Métricas iniciales de SonarQube

**Fecha de extracción:** 17 de noviembre de 2026  
**Proyecto:** `Shift-Bank---Stage-3---OpenSpec`  
**Herramienta:** SonarQube Community Build 26.9  
**Estado:** Métricas iniciales recuperadas; verificación de correspondencia con el análisis original pendiente  
**Avance global estimado:** 90 %

### 1. Objetivo

Consolidar las métricas iniciales de calidad estática de la implementación OpenSpec correspondiente a la Etapa 3 de Shift Bank, antes de realizar correcciones sobre los hallazgos.

### 2. Procedimiento

El análisis inicial fue enviado previamente a SonarQube mediante SonarScanner CLI 8.1.0.6389.

Posteriormente se recuperaron sus métricas mediante la API del proyecto.

La primera consulta agrupada devolvió HTTP 404 debido a una clave de métrica no admitida por el servidor. El extractor fue corregido para consultar las claves individualmente.

Se recuperaron 25 métricas válidas. La clave `software_quality_maintainability_debt` no fue admitida.

Las consultas de Quality Gate, incidencias y Compute Engine respondieron HTTP 200. El endpoint de Security Hotspots respondió HTTP 403.

### 3. Resultados D2

| Indicador | Resultado |
|---|---:|
| NCLOC | 1.859 |
| Líneas físicas | 2.219 |
| Bugs | 5 |
| Vulnerabilidades | 0 |
| Code Smells | 47 |
| Hallazgos totales | 52 |
| Hallazgos/KLOC | 27,972 |
| Deuda técnica | 301 minutos |
| Complejidad ciclomática | 528 |
| Complejidad cognitiva | 464 |
| Duplicación | 0,0 % |
| Cobertura total | 80,7 % |
| Cobertura de líneas | 80,8 % |
| Líneas por cubrir | 1.163 |
| Líneas sin cubrir | 223 |
| Reliability Rating | C |
| Security Rating | A |
| Maintainability Rating | A |
| Quality Gate | OK |

El número de hallazgos por KLOC fue calculado como:

52 / (1.859 / 1.000) = 27,972.

La deuda técnica equivale a 5 horas y 1 minuto de remediación estimada.

### 4. Análisis

El sistema obtuvo un Quality Gate satisfactorio, aunque presentó cinco incidencias de fiabilidad y 47 hallazgos de mantenibilidad.

La ausencia de vulnerabilidades reportadas no implica que el sistema esté libre de todos los riesgos de seguridad.

La cobertura consolidada alcanzó el 80,7 %. Este porcentaje corresponde al alcance evaluado por SonarQube y debe distinguirse de la cobertura backend previamente obtenida mediante coverage.py.

La duplicación reportada fue de 0,0 %.

El acceso a la lista detallada de Security Hotspots quedó limitado por un HTTP 403, aunque la métrica agregada recuperada fue cero.

### 5. Evidencia

La extracción original se encuentra en:

`Etapa 3/_experiment_logs/OpenSpec/sonarqube/EXTRACCION_INICIAL_20261117T141345069/`

Archivos principales:

- `resumen.json`
- `measures.json`
- `issues.json`
- `quality_gate.json`
- `ce.json`
- `hotspots.json`

La extracción no ejecutó otro escaneo ni modificó código.

### 6. Continuidad

La siguiente actividad corresponde al Hito 8: revisión y corrección focalizada de incidencias reales de SonarQube.

Se priorizarán los bugs de fiabilidad, los hallazgos de seguridad comprobados y las correcciones de mantenibilidad justificadas.

Posteriormente se realizará una medición final con el mismo alcance y configuración, a fin de comparar las métricas antes y después de las correcciones.

**Estado: MÉTRICAS INICIALES RECUPERADAS — SIGUIENTE FASE: CORRECCIÓN FOCALIZADA.**

# Shift Bank — Etapa 3 — OpenSpec
## Hito 9 — Medición final de calidad y comparación SonarQube

**Fecha:** 17 de noviembre de 2026  
**Framework:** OpenSpec 1.11.0  
**Herramienta de análisis:** SonarQube Community Build 26.9  
**Estado:** Escaneo y extracción final exitosos  
**Avance global estimado:** 95 %

### Objetivo

Evaluar el efecto de una única ronda focalizada de correcciones sobre la calidad del código mediante una segunda medición de SonarQube, conservando la configuración experimental de la medición inicial.

### Procedimiento

Después de completar las correcciones y regenerar los informes de cobertura, se intentó ejecutar el escaneo final.

El primer intento falló porque el reporte de cobertura Python contenía una ruta absoluta de Windows incompatible con la ejecución de SonarScanner dentro de Docker.

Se corrigió el elemento `source` del archivo XML para apuntar a `/usr/src/backend`, sin cambiar los resultados de cobertura ni el código del sistema.

El escaneo posterior finalizó con `EXECUTION SUCCESS`.

La tarea de Compute Engine `82f9f447-63ba-462a-8d43-f71582e4f365` terminó con estado `SUCCESS`, y se recuperaron las métricas finales mediante la API.

### Resultados comparativos

| Indicador | Inicial | Final |
|---|---:|---:|
| NCLOC | 1.859 | 1.866 |
| Bugs | 5 | 0 |
| Vulnerabilidades | 0 | 0 |
| Code Smells | 47 | 34 |
| Hallazgos/KLOC | 27,972 | 18,221 |
| Deuda técnica (minutos) | 301 | 223 |
| Complejidad ciclomática | 528 | 528 |
| Complejidad cognitiva | 464 | 464 |
| Cobertura global | 80,7 % | 80,8 % |
| Cobertura de líneas | 80,8 % | 80,9 % |
| Duplicación | 0,0 % | 0,0 % |
| Fiabilidad | C | A |
| Seguridad | A | A |
| Mantenibilidad | A | A |
| Quality Gate | OK | OK |

### Interpretación

La intervención se asoció con la eliminación de los cinco bugs reportados inicialmente y una reducción neta de 13 Code Smells.

Los hallazgos totales disminuyeron de 52 a 34, equivalente a una reducción aproximada del 34,6 %.

La deuda técnica estimada se redujo en 78 minutos, aproximadamente el 25,9 %.

La fiabilidad mejoró de C a A, mientras que las calificaciones de seguridad y mantenibilidad permanecieron en A.

No hubo cambios en las métricas agregadas de complejidad ni en la duplicación reportada.

La cobertura global aumentó ligeramente, del 80,7 % al 80,8 %. Esta mejora debe interpretarse considerando que el número de líneas por cubrir también cambió.

### Limitaciones

La comparación por identificador individual de incidencia permanece pendiente de consolidación. Por tanto, no se atribuye automáticamente la reducción neta de 18 hallazgos a las 19 correcciones realizadas.

El endpoint de detalle de Security Hotspots permaneció inaccesible con HTTP 403, aunque la métrica agregada reportó cero.

La comparación requiere confirmar la clasificación de un archivo adicional indexado en el análisis final.

El Quality Gate conservó el estado OK; su utilidad depende de las condiciones efectivamente configuradas.

### Evidencia

**Medición inicial:** `EXTRACCION_INICIAL_20261117T141345069`

**Medición final:** `EXTRACCION_FINAL_20261117T145759941`

**Tarea final:** `82f9f447-63ba-462a-8d43-f71582e4f365`

Ambas extracciones se conservaron por separado bajo `Etapa 3/_experiment_logs/OpenSpec/sonarqube/`.

### Conclusión

La medición final evidencia una mejora cuantificable de la fiabilidad y la mantenibilidad del sistema tras la ronda correctiva.

La evaluación técnica de SonarQube está completada. El cierre académico definitivo requiere consolidar la trazabilidad de incidencias, los criterios AC-01–AC-16 y las dimensiones D1–D5.

**Resultado: HITO 9 COMPLETADO — CIERRE DOCUMENTAL PENDIENTE.**

