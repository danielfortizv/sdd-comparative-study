# Requirements Document

> Documento canónico de requisitos de la Etapa 3 (Opción A) en el formato nativo de Kiro. Los
> encabezados canónicos en inglés (`Requirements Document`, `Introduction`, `Requirements`,
> `Glossary`) satisfacen el validador; el contenido se mantiene en español por coherencia con
> las especificaciones heredadas de las Etapas 1 y 2.

## Introduction

## Introducción

La Etapa 3 extiende la aplicación Shift Bank heredada de la Etapa 2 (desarrollo brownfield) sin
reescribir su arquitectura por capas (FastAPI + `sqlite3` sin ORM, configuración por constantes
en `app/config.py` y ruta de base de datos `DB_PATH`; frontend React + TypeScript con CSS puro)
ni alterar su comportamiento bancario observable. Sobre el mismo cliente mock ya autenticado, la
Etapa 3 incorpora cuatro capacidades transversales:

1. **Cifrado de datos bancarios sensibles** en reposo (a nivel de campo en SQLite) y en
   tránsito (HTTPS/TLS). No es cifrado de conocimiento cero: el backend puede descifrar datos
   autorizados para operar.
2. **Auditoría transaccional inmutable y verificable** mediante una bitácora append-only
   encadenada con HMAC, atómica con el cambio financiero.
3. **Pruebas de carga reproducibles** que caracterizan rendimiento y verifican la corrección
   financiera bajo concurrencia.
4. **Despliegue contenedorizado** local con Docker Compose (backend FastAPI + Nginx), HTTPS en
   Nginx, secretos externos y persistencia en volumen.

Esta especificación se construye sobre el baseline heredado de las Etapas 1 y 2 y lo preserva.
Las decisiones de negocio abiertas fueron resueltas por el investigador durante el
descubrimiento (decisiones **D-E3-01** a **D-E3-04**) antes de redactar estos requisitos. El
contrato externo de aceptación es la matriz **AC-01 .. AC-16** (ver Verificación y trazabilidad).

### Baseline heredado (Etapas 1 y 2) — autoritativo y preservado

- Backend Python/FastAPI sobre `sqlite3` sin ORM; frontend React + TypeScript con CSS puro.
- Configuración por constantes en `app/config.py`; la ruta de la base de datos es `DB_PATH`
  (objeto `Path`). **No** se usa SQLAlchemy ni `DATABASE_URL`; las conexiones se abren con
  `app.db.get_connection()` (sqlite3, `check_same_thread=False`, `PRAGMA foreign_keys=ON`).
- Dinero en **centavos enteros** (`INTEGER`); **COP**; transporte en API como cadenas decimales
  con exactamente 2 decimales; cálculo con `Decimal`.
- Cliente mock único ya autenticado; dos cuentas propias (Checking, Savings); transferencias
  internas con estados en MAYÚSCULAS (`PENDING_MFA`, `COMPLETED`, `FAILED`, `EXPIRED`).
- MFA simulada: umbral **>= 1.000.000 COP**, código fijo **`123456`**, ventana de **5 minutos**,
  reintentos sin lockout, re-verificación de fondos al confirmar, atomicidad de saldos.
- ACH a terceros (`pending_auth`/`pending`/`settled`/`failed`), beneficiarios guardados/ad hoc,
  settlement automático y reembolso **exactamente-una-vez**; historial unificado `internal`/`ach`.
- Pagos recurrentes (diario/semanal/mensual) por un **único** scheduler de fondo idempotente;
  reanudación sin catch-up.
- Límites dinámicos por transferencia y diario acumulado (día UTC), aplicados a internas, ACH y
  recurrentes.
- Atomicidad financiera con `BEGIN IMMEDIATE` vía el context manager `txn.financial_transaction`;
  idempotencia durable por `UNIQUE` + guarda de estado. La API nunca expone identificadores
  internos (UUID, IDs, números de cuenta completos).
- Migración de esquema **aditiva, idempotente y transaccional** en el arranque (`db.migrate`).

### Decisiones del investigador incorporadas (descubrimiento Etapa 3)

- **D-E3-01 — Cifrado (A+B).** Cifrar identificadores bancarios sensibles **en reposo** (a nivel
  de campo) y **en tránsito** (HTTPS/TLS). No es conocimiento cero; el backend puede descifrar
  datos autorizados. Cifrado autenticado con verificación de integridad (AEAD); claves
  provisionadas externamente (variables de entorno aceptables en esta simulación local); sin
  secretos embebidos ni respaldo en texto plano; manejo seguro de claves ausentes/inválidas/
  obsoletas; migración idempotente de registros con rollback ante fallo. Campos en alcance:
  número de cuenta de beneficiario, número de routing, `beneficiary_snapshot` y copias
  persistidas equivalentes de identificadores bancarios sensibles.
- **D-E3-02 — Auditoría inmutable transaccional.** Bitácora append-only, endurecida frente a
  UPDATE/DELETE ordinarios, con cadena criptográficamente verificable por **HMAC** y material de
  clave provisionado externamente. Alcance: transiciones financieras (exitosas y rechazadas),
  fallos y bloqueos de MFA, settlement/reembolso ACH, ejecuciones recurrentes, cambios de
  beneficiario, actualizaciones de límites y cambios de ciclo de vida de schedules; las
  consultas de solo lectura no se auditan. La entrada de auditoría se confirma **atómicamente**
  con el cambio financiero; el fallo de persistencia de auditoría impide mutaciones financieras
  parciales no autorizadas (fail-closed). No se reclama inmutabilidad absoluta frente a un
  administrador que controle base de datos, aplicación y todos los secretos.
- **D-E3-03 — Pruebas de carga reproducibles.** Locust como dependencia **solo de pruebas**;
  objetivo doble (rendimiento + corrección bajo concurrencia). Configuración obligatoria: 30
  usuarios, ramp-up 5 usuarios/segundo, 60 s de carga sostenida tras el ramp-up; mezcla 60%
  lecturas de saldo / 30% lecturas de historial / 10% transferencias internas reales. Umbrales:
  p95 lectura < 200 ms, p95 transferencia < 500 ms, errores inesperados < 1%, cero violaciones de
  invariantes. DB sintética aislada (aislamiento antes de importar la app), semillas fijas,
  controles bancarios preservados, medición de la distribución real de peticiones HTTP, reporte
  completo de métricas y preservación de resultados legibles por máquina.
- **D-E3-04 — Despliegue contenedorizado.** Docker Compose local con dos servicios (backend
  FastAPI + assets de producción React servidos por Nginx). Nginx termina HTTPS y hace
  reverse-proxy al backend por la red interna aislada; certificados autofirmados provisionados
  externamente aceptables en local; redirección HTTP->HTTPS. Secretos por variables de entorno o
  `.env` no versionado, con `.env.example` versionado sin secretos reales; arranque fail-closed
  ante claves faltantes/ inválidas. Volumen persistente aislado para SQLite incluida la cadena de
  auditoría; init/migración idempotentes; sin datos históricos ni secretos horneados en imágenes;
  exactamente un scheduler de recurrentes activo. Verificación de despliegue solo local.

### Convención de criterios de aceptación (EARS)

Los criterios siguen el estilo EARS heredado: "CUANDO ... ENTONCES el sistema DEBERÁ ...", "SI
... ENTONCES el sistema DEBERÁ ...", y "EN TODO MOMENTO el sistema DEBERÁ ...". Cada criterio
referencia entre paréntesis la decisión (D-E3-0x) y el caso de aceptación externo (AC-xx) que lo
respalda.

---

## Requirements

## Requisitos

## Parte I — Requisitos funcionales (FR)

## A. Cifrado de datos bancarios sensibles (D-E3-01)

### Requisito 1 — Cifrado en reposo de identificadores sensibles

**Historia de usuario:** Como responsable de seguridad de Shift Bank, quiero que los
identificadores bancarios sensibles se almacenen cifrados en la base de datos, para que quien
lea el archivo SQLite no pueda ver valores en texto plano.

#### Criterios de aceptación

1. CUANDO el sistema persiste un beneficiario (guardado o ad hoc guardado), ENTONCES el sistema
   DEBERÁ almacenar el número de cuenta y el número de routing cifrados con un esquema AEAD,
   nunca en texto plano. _(D-E3-01; AC-02, AC-04)_
2. CUANDO el sistema persiste una instantánea de beneficiario (`beneficiary_snapshot`) en una
   transferencia ACH o en un schedule recurrente, ENTONCES el sistema DEBERÁ cifrar los
   identificadores bancarios sensibles contenidos en esa instantánea. _(D-E3-01; AC-02, AC-04)_
3. EN TODO MOMENTO el sistema DEBERÁ cifrar toda copia persistida equivalente de un
   identificador bancario sensible, sin dejar ninguna copia en claro en el archivo SQLite.
   _(D-E3-01; AC-02, AC-04)_
4. CUANDO el sistema lee un registro cifrado para una operación bancaria autorizada, ENTONCES el
   sistema DEBERÁ descifrarlo en la capa de servicio y verificar su integridad antes de usarlo.
   _(D-E3-01; AC-02)_
5. EN TODO MOMENTO el sistema DEBERÁ preservar el comportamiento observable heredado: las
   respuestas de la API siguen exponiendo el número de cuenta **enmascarado** (últimos 4
   dígitos) y el routing según el contrato de la Etapa 2, sin exponer texto cifrado ni material
   de clave. _(D-E3-01; AC-01, AC-02)_
6. EN TODO MOMENTO el cifrado en reposo DEBERÁ aplicarse sin alterar el modelo de dinero
   (centavos enteros), los contratos de montos decimal-string ni la lógica financiera heredada.
   _(D-E3-01; AC-01)_

### Requisito 2 — Gestión del ciclo de vida de claves y manejo de fallos

**Historia de usuario:** Como operador del sistema, quiero que las claves de cifrado se
provisionen externamente y que el sistema maneje con seguridad las claves ausentes, inválidas u
obsoletas, para no exponer datos ni operar en un estado inseguro.

#### Criterios de aceptación

1. EN TODO MOMENTO el sistema DEBERÁ obtener el material de clave de cifrado de una fuente
   externa (variable de entorno en esta simulación local) y NUNCA DEBERÁ contener secretos
   embebidos en el código ni en imágenes. _(D-E3-01; AC-02, AC-03)_
2. SI la clave de cifrado requerida está ausente o es inválida al arrancar o al operar, ENTONCES
   el sistema DEBERÁ fallar de forma cerrada (rechazar la operación o no arrancar) en lugar de
   recurrir a texto plano. _(D-E3-01; AC-02, AC-03)_
3. EN TODO MOMENTO el sistema NO DEBERÁ ofrecer ningún respaldo en texto plano ni ruta
   alternativa que escriba o lea identificadores sensibles sin cifrar. _(D-E3-01; AC-02, AC-03)_
4. CUANDO un valor cifrado se persiste, ENTONCES el sistema DEBERÁ registrar en él la
   información de **versión de clave** necesaria para seleccionar la clave de descifrado
   correcta, permitiendo manejar claves obsoletas de forma determinista. _(D-E3-01; AC-03)_
5. SI un registro fue cifrado con una clave obsoleta o desconocida, o su integridad AEAD no
   verifica (texto cifrado manipulado), ENTONCES el sistema DEBERÁ rechazarlo de forma segura
   (error controlado), sin devolver datos incorrectos ni operar con datos manipulados. _(D-E3-01;
   AC-03)_
6. EN TODO MOMENTO el material de clave NO DEBERÁ registrarse en logs, respuestas de API ni
   mensajes de error. _(D-E3-01; AC-02, AC-03)_

### Requisito 3 — Migración de cifrado de registros existentes

**Historia de usuario:** Como operador, quiero migrar los registros sensibles existentes a su
forma cifrada de manera idempotente y reversible ante fallo, para no perder ni corromper datos
bancarios heredados.

#### Criterios de aceptación

1. CUANDO se ejecuta la migración de cifrado, ENTONCES el sistema DEBERÁ cifrar los registros
   sensibles existentes en su lugar, de forma **idempotente** (re-ejecutarla no vuelve a cifrar
   lo ya cifrado ni corrompe datos). _(D-E3-01; AC-04)_
2. SI la migración de cifrado falla a mitad de camino o detecta corrupción, ENTONCES el sistema
   DEBERÁ revertir por completo (rollback transaccional) sin dejar una mezcla inconsistente de
   registros cifrados y en claro. _(D-E3-01; AC-04)_
3. EN TODO MOMENTO la migración de cifrado DEBERÁ preservar los datos bancarios heredados y los
   contratos de API, integrándose con la migración aditiva idempotente existente del arranque
   (`db.migrate`). _(D-E3-01; AC-01, AC-04)_
4. CUANDO la migración termina con éxito, ENTONCES el sistema DEBERÁ garantizar que no queda
   ningún identificador sensible en texto plano en la base de datos. _(D-E3-01; AC-02, AC-04)_

### Requisito 4 — Seguridad en tránsito (HTTPS/TLS)

**Historia de usuario:** Como cliente, quiero que mi comunicación con la aplicación viaje
cifrada, para que no pueda ser interceptada en la red.

#### Criterios de aceptación

1. CUANDO un cliente accede a la aplicación desplegada, ENTONCES el sistema DEBERÁ servir el
   tráfico sobre HTTPS/TLS, con la terminación TLS en Nginx. _(D-E3-01, D-E3-04; AC-12)_
2. CUANDO un cliente accede por HTTP en el despliegue, ENTONCES el sistema DEBERÁ redirigirlo a
   HTTPS. _(D-E3-04; AC-12)_
3. EN TODO MOMENTO el reverse-proxy DEBERÁ reenviar las peticiones de API al backend por la red
   interna aislada de Docker, sin exponer el backend directamente al exterior. _(D-E3-04; AC-12)_
4. CUANDO se use un certificado autofirmado provisionado externamente en el entorno local,
   ENTONCES el sistema DEBERÁ aceptarlo para TLS sin versionar el material privado del
   certificado en el repositorio. _(D-E3-01, D-E3-04; AC-12)_

## B. Auditoría transaccional inmutable y verificable (D-E3-02)

### Requisito 5 — Alcance y contenido de la auditoría

**Historia de usuario:** Como auditor, quiero que toda operación bancaria relevante y los
cambios de configuración sensibles queden registrados, para poder reconstruir qué ocurrió.

#### Criterios de aceptación

1. CUANDO ocurre una transición de estado financiero (creación de transferencia interna,
   confirmación de MFA, COMPLETED/FAILED/EXPIRED, creación/autorización ACH, settlement ACH,
   fallo+reembolso ACH, ejecución o fallo de una ocurrencia recurrente), ENTONCES el sistema
   DEBERÁ registrar una entrada de auditoría que la describa. _(D-E3-02; AC-05, AC-07)_
2. CUANDO ocurre una acción de configuración sensible (alta/baja de beneficiario, actualización
   de límites, cambio de ciclo de vida de un schedule: pausar/reanudar/cancelar), ENTONCES el
   sistema DEBERÁ registrar una entrada de auditoría. _(D-E3-02; AC-05)_
3. CUANDO una operación bancaria es **rechazada** (fondos insuficientes, límite excedido, MFA
   incorrecta, bloqueo), ENTONCES el sistema DEBERÁ registrar la operación rechazada como
   auditable, sin confirmar ninguna mutación bancaria no autorizada. _(D-E3-02; AC-07, AC-08)_
4. EN TODO MOMENTO cada entrada de auditoría DEBERÁ registrar al menos: tipo de evento,
   resultado (éxito/rechazo), marca de tiempo UTC, referencia a la entidad afectada (sin
   exponer identificadores internos ni datos sensibles en claro) y los metadatos de la cadena
   (secuencia y HMAC). _(D-E3-02; AC-05)_
5. EN TODO MOMENTO las consultas de **solo lectura** (listar cuentas, historial, beneficiarios,
   límites) NO DEBERÁN generar entradas de auditoría. _(D-E3-02; AC-05)_
6. EN TODO MOMENTO las entradas de auditoría NO DEBERÁN contener identificadores bancarios
   sensibles en texto plano. _(D-E3-01, D-E3-02; AC-02, AC-05)_

### Requisito 6 — Inmutabilidad e integridad de la cadena

**Historia de usuario:** Como auditor, quiero que la bitácora sea append-only y verificable
criptográficamente, para detectar cualquier manipulación.

#### Criterios de aceptación

1. EN TODO MOMENTO la bitácora de auditoría DEBERÁ ser append-only: el sistema solo inserta
   entradas nuevas y no ofrece ninguna ruta de aplicación para actualizar o borrar entradas.
   _(D-E3-02; AC-05, AC-06)_
2. EN TODO MOMENTO el sistema DEBERÁ endurecer la tabla de auditoría frente a UPDATE/DELETE
   ordinarios (mecanismos a nivel de base de datos), de modo que una modificación ordinaria sea
   impedida o detectable. _(D-E3-02; AC-06)_
3. CUANDO se registra una entrada, ENTONCES el sistema DEBERÁ calcular un HMAC que encadene la
   entrada con la anterior (sobre el HMAC previo y la serialización canónica de la entrada),
   usando material de clave provisionado externamente. _(D-E3-02; AC-05, AC-06)_
4. CUANDO se ejecuta la rutina de verificación, ENTONCES el sistema DEBERÁ recomputar los HMAC y
   DEBERÁ detectar manipulación de contenido, entradas reordenadas, cadenas rotas y registros
   intermedios faltantes. _(D-E3-02; AC-05, AC-06)_
5. SI una entrada fue alterada, insertada o eliminada en medio de la cadena, ENTONCES la
   verificación DEBERÁ fallar identificando el punto de ruptura. _(D-E3-02; AC-06)_
6. EN TODO MOMENTO el sistema DEBERÁ reconocer los **límites del modelo de amenazas**: la
   verificación detecta manipulación y eliminación/ inserción intermedia, pero la **truncación
   del final de la cadena** (eliminar las últimas entradas conservando un estado consistente)
   solo es detectable con un ancla externa (p. ej. persistir el último HMAC/longitud fuera de la
   tabla). Sin ese ancla, la truncación del extremo NO es plenamente detectable; no se reclama
   inmutabilidad absoluta frente a un administrador con control total. _(D-E3-02; AC-06)_

### Requisito 7 — Atomicidad auditoría-transacción y fail-closed

**Historia de usuario:** Como responsable de integridad, quiero que el registro de auditoría y
el cambio financiero se confirmen juntos, para que nunca exista un cambio de dinero sin su
rastro de auditoría, ni mutaciones parciales ante fallo de auditoría o PIN inválido.

#### Criterios de aceptación

1. CUANDO un cambio financiero exitoso se confirma, ENTONCES el sistema DEBERÁ confirmar su
   entrada de auditoría en la **misma** transacción `BEGIN IMMEDIATE`, de forma atómica. _(D-E3-02;
   AC-07)_
2. SI la persistencia de la entrada de auditoría falla, ENTONCES el sistema DEBERÁ revertir el
   cambio financiero asociado (fail-closed), sin dejar saldos, transferencias ni beneficiarios
   parciales. _(D-E3-02; AC-07)_
3. SI la confirmación de MFA recibe un PIN inválido, ENTONCES el sistema NO DEBERÁ aplicar
   ningún débito ni cambio de estado financiero, PERO la operación rechazada DEBERÁ quedar
   auditada. _(D-E3-02; AC-07, AC-08)_
4. CUANDO una operación es rechazada, ENTONCES el sistema DEBERÁ poder auditar ese rechazo sin
   confirmar ninguna mutación financiera. _(D-E3-02; AC-07, AC-08)_
5. EN TODO MOMENTO la escritura de auditoría DEBERÁ preservar los invariantes financieros
   heredados (conservación del dinero, exactamente-una-vez de ACH/recurrentes, límites, máquina
   de estados). _(D-E3-02; AC-01, AC-07)_

### Requisito 8 — Verificación de auditoría, acceso y concurrencia

**Historia de usuario:** Como auditor autorizado, quiero verificar la integridad de la bitácora
de forma controlada y que esa integridad se sostenga bajo operaciones concurrentes.

#### Criterios de aceptación

1. CUANDO se solicita la verificación de integridad, ENTONCES el sistema DEBERÁ ofrecer una
   rutina/operación que valide toda la cadena y reporte el resultado (íntegra o punto de fallo).
   _(D-E3-02; AC-05)_
2. EN TODO MOMENTO el acceso a la verificación administrativa de auditoría DEBERÁ estar
   protegido (no expuesto como endpoint público anónimo), consistente con el modelo de cliente
   mock heredado. _(D-E3-02; AC-05)_
3. CUANDO múltiples operaciones financieras concurrentes generan entradas de auditoría, ENTONCES
   el sistema DEBERÁ producir una cadena consistente y verificable (secuencia bien definida),
   apoyándose en la serialización de escritura (`BEGIN IMMEDIATE`) heredada. _(D-E3-02; AC-09)_
4. CUANDO se audita bajo concurrencia de **procesos independientes** que comparten el mismo
   archivo SQLite, ENTONCES el sistema DEBERÁ mantener la verificabilidad de la cadena bajo el
   modelo lector/escritor de SQLite (un único escritor; lectores concurrentes), sin bloquear
   innecesariamente las lecturas. _(D-E3-02; AC-09)_

## C. Pruebas de carga reproducibles (D-E3-03)

### Requisito 9 — Caracterización de rendimiento

**Historia de usuario:** Como ingeniero, quiero una prueba de carga reproducible que caracterice
el rendimiento con una configuración fija, para establecer un baseline comparable.

#### Criterios de aceptación

1. CUANDO se ejecuta la prueba de carga, ENTONCES el sistema DEBERÁ usar **Locust** con la
   configuración exacta aprobada: **30 usuarios concurrentes**, **ramp-up de 5 usuarios/segundo**
   y **60 segundos de carga sostenida DESPUÉS del ramp-up**. _(D-E3-03; AC-10)_
2. CUANDO se ejecuta la prueba de carga, ENTONCES la mezcla DEBERÁ ser **60% lecturas de saldo /
   30% lecturas de historial / 10% transferencias internas reales**. _(D-E3-03; AC-10)_
3. CUANDO finaliza la prueba, ENTONCES el sistema DEBERÁ reportar p50/p95/p99 de latencia,
   throughput, conteos de peticiones, rechazos de negocio esperados, errores inesperados, el
   entorno y los parámetros exactos de ejecución. _(D-E3-03; AC-11)_
4. CUANDO se reporta la distribución de trabajo, ENTONCES el sistema DEBERÁ medir la
   **distribución real de peticiones HTTP observada**, no solo los pesos de tareas de Locust.
   _(D-E3-03; AC-11)_
5. EN TODO MOMENTO la caracterización DEBERÁ considerarse APROBADA solo si: p95 de lectura
   **< 200 ms**, p95 de transferencia **< 500 ms** y errores inesperados **< 1%**
   (estrictamente). _(D-E3-03; AC-11)_
6. CUANDO la prueba produce resultados, ENTONCES el sistema DEBERÁ **preservar los resultados
   legibles por máquina** originales como evidencia, sin sobrescribirlos. _(D-E3-03; AC-11,
   AC-16)_
7. EN TODO MOMENTO NO SE DEBERÁ optimizar la aplicación antes de capturar el primer baseline
   válido. _(D-E3-03; AC-11)_

### Requisito 10 — Reproducibilidad y corrección bajo concurrencia

**Historia de usuario:** Como ingeniero, quiero que la prueba de carga sea reproducible y
verifique que no se violan invariantes financieros ni de auditoría bajo concurrencia.

#### Criterios de aceptación

1. EN TODO MOMENTO la prueba de carga DEBERÁ usar una **base de datos SQLite sintética aislada**,
   nunca datos históricos, y DEBERÁ configurar el aislamiento **antes de importar la aplicación**.
   _(D-E3-03; AC-10)_
2. EN TODO MOMENTO la prueba DEBERÁ usar datos y configuración reproducibles, con semillas
   aleatorias fijas donde aplique. _(D-E3-03; AC-10)_
3. CUANDO la prueba genera transferencias, ENTONCES DEBERÁ mantenerlas pequeñas y válidas y NO
   DEBERÁ eludir las validaciones de MFA, saldo ni límites heredadas. _(D-E3-03; AC-01, AC-10)_
4. CUANDO la prueba termina, ENTONCES el sistema DEBERÁ verificar la **consistencia financiera**
   y la **integridad de la cadena de auditoría** tras la ejecución. _(D-E3-03; AC-09)_
5. EN TODO MOMENTO la prueba DEBERÁ considerarse fallida si se detecta **cualquier** violación de
   invariante financiero, con independencia de las métricas de rendimiento. _(D-E3-03; AC-09)_
6. CUANDO sea útil, ENTONCES pruebas de concurrencia enfocadas (procesos independientes, dos
   conexiones lector/escritor) PODRÁN complementar el benchmark sin sustituir la configuración
   obligatoria. _(D-E3-03; AC-09)_

## D. Despliegue contenedorizado (D-E3-04)

### Requisito 11 — Topología de despliegue contenedorizado

**Historia de usuario:** Como operador, quiero desplegar la aplicación localmente con Docker
Compose en dos servicios, para reproducir el entorno de forma consistente.

#### Criterios de aceptación

1. CUANDO se despliega la aplicación, ENTONCES el sistema DEBERÁ definir dos servicios en Docker
   Compose: backend FastAPI y assets de producción React servidos por **Nginx**. _(D-E3-04;
   AC-12)_
2. EN TODO MOMENTO Nginx DEBERÁ servir los assets estáticos y actuar como reverse-proxy del
   backend por la red interna aislada; el backend NO DEBERÁ exponerse directamente al exterior.
   _(D-E3-04; AC-12)_
3. EN TODO MOMENTO el despliegue DEBERÁ garantizar que exactamente **un** scheduler de pagos
   recurrentes esté activo. _(D-E3-04, baseline E2; AC-13)_
4. EN TODO MOMENTO los contenedores DEBERÁN ejecutarse como usuario **no root** donde sea
   factible. _(D-E3-04; AC-13)_
5. EN TODO MOMENTO el despliegue NO DEBERÁ requerir hosting externo, Kubernetes ni CI/CD
   adicional. _(D-E3-04; AC-12)_

### Requisito 12 — Configuración, secretos y persistencia del despliegue

**Historia de usuario:** Como operador, quiero gestionar secretos y persistencia de forma
segura, para no exponer claves ni perder datos ni la cadena de auditoría.

#### Criterios de aceptación

1. EN TODO MOMENTO el despliegue DEBERÁ tomar los secretos de variables de entorno o de un
   `.env` **no versionado**, con un `.env.example` versionado que **no** contenga secretos
   reales. _(D-E3-01, D-E3-04; AC-12, AC-13)_
2. SI faltan o son inválidas las claves de cifrado o de auditoría requeridas, ENTONCES el
   despliegue DEBERÁ **fallar de forma cerrada** (no arrancar). _(D-E3-01, D-E3-02, D-E3-04;
   AC-12, AC-13)_
3. EN TODO MOMENTO el despliegue DEBERÁ persistir la base de datos SQLite —incluida la cadena de
   auditoría— en un **volumen Docker persistente aislado**. _(D-E3-04; AC-13)_
4. CUANDO el contenedor del backend arranca, ENTONCES el sistema DEBERÁ ejecutar init y
   migración de forma **idempotente**, sin duplicar datos. _(D-E3-04, baseline E1/E2; AC-04,
   AC-13)_
5. EN TODO MOMENTO las imágenes NO DEBERÁN contener bases de datos históricas ni secretos
   horneados. _(D-E3-04; AC-12, AC-13)_

### Requisito 13 — Verificación local del despliegue

**Historia de usuario:** Como operador, quiero evidenciar localmente que el despliegue funciona
de forma segura, para dar por válido el entregable sin hosting externo.

#### Criterios de aceptación

1. CUANDO se valida el despliegue, ENTONCES el sistema DEBERÁ demostrar `docker compose config`,
   build y arranque correctos de ambos servicios, con **healthchecks** saludables. _(D-E3-04;
   AC-12)_
2. CUANDO se ejecutan pruebas de humo, ENTONCES el sistema DEBERÁ verificar HTTPS, la
   redirección HTTP->HTTPS, el proxy de rutas de API y una llamada representativa sobre TLS.
   _(D-E3-01, D-E3-04; AC-12)_
3. CUANDO se ejecuta la verificación funcional, ENTONCES el sistema DEBERÁ comprobar operaciones
   bancarias, MFA, cifrado y verificación de auditoría sobre el entorno desplegado. _(D-E3-01,
   D-E3-02, D-E3-04; AC-13)_
4. CUANDO el despliegue se reinicia, ENTONCES el sistema DEBERÁ verificar la **supervivencia** de
   los datos cifrados y de la cadena de auditoría tras el reinicio. _(D-E3-04; AC-13)_
5. CUANDO faltan claves requeridas, ENTONCES la verificación DEBERÁ demostrar el comportamiento
   **fail-closed** del arranque. _(D-E3-01, D-E3-02, D-E3-04; AC-12, AC-13)_
6. EN TODO MOMENTO la verificación DEBERÁ usar **volúmenes de prueba desechables y aislados**,
   sin tocar datos reales. _(D-E3-04; AC-13)_

## E. Compatibilidad y preservación (transversal)

### Requisito 14 — Preservación del comportamiento bancario heredado

**Historia de usuario:** Como cliente existente, quiero que todas las capacidades bancarias de
las Etapas 1 y 2 sigan funcionando igual, para no sufrir regresiones.

#### Criterios de aceptación

1. EN TODO MOMENTO el sistema DEBERÁ preservar sin cambios de forma las APIs y contratos
   heredados: cuentas, historial unificado, transferencias internas, MFA, ACH, recurrentes y
   límites dinámicos. _(baseline E1/E2; AC-01)_
2. EN TODO MOMENTO el sistema DEBERÁ preservar los invariantes financieros: conservación del
   dinero, atomicidad `BEGIN IMMEDIATE`, exactamente-una-vez de ACH/recurrentes, día UTC de
   límites y la máquina de estados heredada. _(baseline E1/E2; AC-01)_
3. EN TODO MOMENTO el sistema DEBERÁ preservar la ausencia de exposición de identificadores
   internos y el enmascarado de números de cuenta en la API. _(baseline E2, D-E3-01; AC-01,
   AC-02)_
4. CUANDO se añaden cifrado y auditoría, ENTONCES el sistema DEBERÁ hacerlo de forma **aditiva**,
   sin eliminar ni alterar endpoints, estados ni formatos existentes. _(baseline E2; AC-01)_

---

## Parte II — Requisitos no funcionales (NFR)

### Requisito 15 — Seguridad

1. EN TODO MOMENTO el sistema DEBERÁ usar cifrado autenticado (AEAD) en reposo y TLS en
   tránsito; sin algoritmos caseros. _(D-E3-01; AC-02, AC-12)_
2. EN TODO MOMENTO el sistema NO DEBERÁ registrar secretos, material de clave, texto cifrado
   crudo ni identificadores sensibles en claro. _(D-E3-01, D-E3-02; AC-02)_
3. EN TODO MOMENTO el sistema DEBERÁ fallar de forma cerrada ante condiciones inseguras.
   _(D-E3-01, D-E3-02; AC-03, AC-07)_

### Requisito 16 — Rendimiento

1. CUANDO opera bajo la carga aprobada, ENTONCES el sistema DEBERÁ cumplir p95 de lectura
   < 200 ms y p95 de transferencia < 500 ms, con errores inesperados < 1%. _(D-E3-03; AC-11)_
2. EN TODO MOMENTO el sobrecoste de cifrado y auditoría NO DEBERÁ violar los umbrales ni
   introducir dependencias de runtime no relacionadas. _(D-E3-01, D-E3-02, D-E3-03; AC-11)_

### Requisito 17 — Confiabilidad y concurrencia

1. EN TODO MOMENTO el sistema DEBERÁ mantener la corrección financiera y la verificabilidad de
   auditoría bajo concurrencia dentro del modelo lector/escritor de SQLite (un único escritor;
   múltiples lectores), sin bloquear innecesariamente las lecturas. _(D-E3-02, D-E3-03; AC-09)_
2. EN TODO MOMENTO el sistema DEBERÁ comportarse de forma correcta ante concurrencia de
   **procesos independientes** que comparten el mismo archivo SQLite, sin corromper datos ni la
   cadena de auditoría. _(D-E3-02, D-E3-03; AC-09)_
3. EN TODO MOMENTO el despliegue DEBERÁ garantizar exactamente un scheduler de recurrentes,
   preservando exactamente-una-vez. _(D-E3-04, baseline E2; AC-13)_

### Requisito 18 — Mantenibilidad y alcance de dependencias

1. EN TODO MOMENTO las nuevas capacidades DEBERÁN seguir el estilo por capas heredado (routers
   -> service -> repository -> sqlite3, sin ORM, config por constantes/`DB_PATH`) y no
   introducir dependencias de runtime innecesarias; Locust DEBERÁ ser dependencia **solo de
   pruebas**. _(D-E3-03, baseline E1/E2; AC-10)_
2. EN TODO MOMENTO la biblioteca criptográfica DEBERÁ ser estándar y revisada (no criptografía
   propia), seleccionada y justificada en la fase de diseño nativa de Kiro. _(D-E3-01, D-E3-02;
   AC-02, AC-05)_

### Requisito 19 — Obligaciones de verificación y evidencia de regresión

**Nota:** define **obligaciones de verificación**, no nuevas funcionalidades bancarias.

1. CUANDO se cierra la Etapa 3, ENTONCES el sistema DEBERÁ evidenciar la suite backend
   (**Pytest**) completa, preservando stdout y los fallos intermedios. _(baseline E1/E2; AC-14)_
2. CUANDO se cierra la Etapa 3, ENTONCES el sistema DEBERÁ evidenciar las pruebas de frontend
   (**Vitest**, si están configuradas) y el **build de producción del frontend** (`tsc && vite
   build`). _(baseline E2; AC-14)_
3. CUANDO se mide calidad estática, ENTONCES el sistema DEBERÁ registrar una medición
   **SonarQube** de baseline (antes de remediación) y final, con **idéntico alcance** y
   **cobertura importada**, sin fabricar resultados. _(obligación de verificación; AC-15)_
4. CUANDO se documentan métricas, ENTONCES el sistema DEBERÁ verificarlas contra la evidencia
   original (JSON, salida de CLI, evidencia cruda), preservándola de forma reproducible sin
   sobrescribirla. _(D-E3-03, D-E3-04; AC-16)_

---

## Parte III — Límites del modelo de amenazas

1. **No es conocimiento cero.** El backend posee las claves y puede descifrar para operar;
   protege frente a lectura del archivo en reposo y a escucha en la red, no frente al backend
   autorizado. _(D-E3-01)_
2. **Administrador con control total.** No se reclama inmutabilidad absoluta frente a un
   administrador que controle base de datos, aplicación y todos los secretos (incluida la clave
   HMAC): tal actor podría reconstruir una cadena consistente. _(D-E3-02)_
3. **Truncación del extremo.** La verificación detecta manipulación, reordenamiento y
   eliminación/ inserción intermedia; la truncación del final solo es detectable con un ancla
   externa (último HMAC/longitud persistido fuera de la tabla). _(D-E3-02)_
4. **Endurecimiento append-only.** Las restricciones a nivel de base de datos frente a
   UPDATE/DELETE dificultan la alteración ordinaria pero no son WORM absoluto frente a un DBA.
   _(D-E3-02)_
5. **Simulación local.** TLS con certificado autofirmado y claves por variable de entorno son
   aceptables localmente; no representan una postura de producción (KMS, rotación, CA). _(D-E3-01,
   D-E3-04)_
6. **Carga acotada por SQLite.** El throughput de escritura está acotado por el único escritor;
   la caracterización mide el sistema tal cual. _(D-E3-03)_

---

## Parte IV — No-objetivos (fuera de alcance)

- Cifrado de conocimiento cero / E2EE cliente-a-almacén donde el servidor no pueda descifrar.
- Red ACH real, compensación, validación ABA externa o movimiento de dinero real.
- Registro o inicio de sesión real, verificación de identidad, múltiples usuarios.
- Hosting externo, Kubernetes, orquestación en la nube o infraestructura de CI/CD.
- KMS gestionado, rotación automática de claves o CA de confianza más allá del manejo seguro de
  claves ausentes/ inválidas/ obsoletas.
- Garantía WORM absoluta de la auditoría frente a un administrador con control total.
- Optimización de rendimiento antes del primer baseline válido de carga.
- Multi-moneda, Event Sourcing/CQRS u otra funcionalidad de Etapa 4.

---

## Parte V — Verificación y trazabilidad (AC-01 .. AC-16)

Matriz de aceptación externa autoritativa del investigador. Cada requisito referencia arriba los
AC que lo respaldan.

| AC | Caso de aceptación externo | Requisitos |
|----|----------------------------|------------|
| AC-01 | Regresión de la funcionalidad bancaria heredada | 1, 3, 7, 10, 14 |
| AC-02 | Cifrado de campos sensibles, evidencia de payload, descifrado autorizado, sin fallback inseguro | 1, 2, 14, 15 |
| AC-03 | Integridad de cifrado, texto cifrado manipulado, claves ausentes/obsoletas, rechazo seguro | 2, 15 |
| AC-04 | Cifrado en reposo, migración idempotente, rollback ante corrupción | 1, 3, 12 |
| AC-05 | Cadena de auditoría hash/HMAC válida y verificable | 5, 6, 8, 18 |
| AC-06 | Detección de manipulación y rechazo de UPDATE/DELETE ordinarios | 6 |
| AC-07 | Atomicidad financiera; fallo de auditoría o PIN inválido sin saldos/transferencias/beneficiarios parciales | 5, 7, 15 |
| AC-08 | Auditoría durable de fallo/lockout de MFA sin mutaciones no autorizadas | 5, 7 |
| AC-09 | Concurrencia real multiproceso y dos conexiones lector/escritor sin bloquear lecturas innecesariamente | 8, 10, 17 |
| AC-10 | Carga Locust reproducible: 30 usuarios, ramp 5/s, 60 s steady, mezcla 60/30/10, DB aislada | 9, 10, 18 |
| AC-11 | SLOs de rendimiento, evidencia exportada y distribución real de peticiones medida | 9, 16 |
| AC-12 | Build/arranque de contenedores, HTTPS, healthchecks, redirección, proxy, rutas, secretos externos | 4, 11, 12, 13, 15 |
| AC-13 | Despliegue persistente seguro, volumen aislado, no-root, supervivencia de cifrado y auditoría al reiniciar | 11, 12, 13, 17 |
| AC-14 | Regresión completa Pytest, Vitest y build de frontend, con stdout y fallos intermedios preservados | 19 |
| AC-15 | Baseline y medición final de SonarQube reproducibles, mismo alcance y cobertura importada | 19 |
| AC-16 | Documentación y métricas verificadas contra JSON/CLI/evidencia cruda original | 19 |

Todos los AC-01..AC-16 tienen al menos un requisito asociado; todos los requisitos 1..19
referencian al menos un AC o el baseline heredado.

---

## Glossary

## Glosario

- **Identificador bancario sensible:** número de cuenta de beneficiario, número de routing y
  cualquier copia persistida de estos (p. ej. dentro de `beneficiary_snapshot` o de instantáneas
  equivalentes en filas de recurrentes/transferencias).
- **En reposo / en tránsito:** datos escritos en el archivo SQLite / datos entre el navegador y
  el backend.
- **AEAD:** cifrado autenticado con datos asociados; garantiza confidencialidad e integridad y
  detecta manipulación del texto cifrado.
- **Cadena de auditoría:** secuencia append-only de entradas donde cada entrada incluye un HMAC
  que la liga a la anterior; una alteración de una entrada pasada rompe la cadena y es detectable.
- **Fail-closed:** ante una condición insegura (clave ausente/ inválida, fallo de auditoría) el
  sistema rechaza la operación en lugar de continuar de forma insegura.
- **Invariante financiero:** conservación del dinero, exactamente-una-vez de ACH/recurrentes,
  respeto de límites y de la máquina de estados heredada.
- **`financial_transaction`:** context manager heredado (`BEGIN IMMEDIATE` ... COMMIT/ROLLBACK)
  que agrupa las operaciones financieras en una única transacción atómica.
- **`DB_PATH`:** constante en `app/config.py` con la ruta del archivo SQLite; mecanismo real de
  configuración de base de datos (no SQLAlchemy ni `DATABASE_URL`).
- **p50/p95/p99:** percentiles de latencia observada por tipo de operación.
- **AC-01..AC-16:** matriz de aceptación externa autoritativa del investigador (Parte V).
- **SLO:** objetivo de nivel de servicio (aquí, umbrales de latencia y tasa de error).

