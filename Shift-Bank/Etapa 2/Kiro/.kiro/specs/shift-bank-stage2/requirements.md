# Requisitos — Shift Bank (Etapa 2: Complejidad funcional y estado)

## Introducción

La Etapa 2 extiende la aplicación Shift Bank de la Etapa 1 (desarrollo brownfield) sin
reescribir su arquitectura ni alterar su comportamiento observable. Sobre el mismo cliente
mock ya autenticado y sus dos cuentas propias (Checking y Savings), la Etapa 2 incorpora tres
capacidades nuevas:

1. **Transferencias ACH a terceros** (beneficiarios guardados o ad hoc), con validación de
   formato, ciclo de vida `pending → settled | failed`, débito inmediato tras autorización,
   settlement automático y reembolso exactamente-una-vez en caso de fallo.
2. **Pagos recurrentes** (internos y ACH) con frecuencia diaria, semanal y mensual, ejecutados
   automáticamente por un scheduler en segundo plano, con controles de pausa/reanudación/
   cancelación.
3. **Límites de transacción dinámicos** (por transferencia y diario acumulado), configurables
   por el usuario y aplicados de forma consistente a transferencias internas, ACH y ejecuciones
   recurrentes.

Esta especificación se construye sobre el baseline heredado de la Etapa 1 y lo preserva. Las
decisiones de negocio abiertas fueron resueltas por el investigador antes de redactar estos
requisitos (decisiones **E2-KIRO-D01** a **E2-KIRO-D05**).

### Baseline heredado (Etapa 1) — autoritativo y preservado

El comportamiento observado de la Etapa 1 es la línea base y debe preservarse sin regresión:

- Backend Python/FastAPI sobre `sqlite3` sin ORM; frontend React + TypeScript con CSS puro.
- Dinero en **centavos enteros** (`INTEGER`) internamente; **COP**; transporte en API como
  cadenas decimales (decimal-string) con exactamente 2 decimales; cálculo con `Decimal`.
- Cliente mock único ya autenticado, dos cuentas (Checking 5.000.000,00; Savings
  15.000.000,00), dos transferencias históricas sembradas que no afectan los saldos iniciales.
- Transferencias internas checking↔savings con estados en MAYÚSCULAS: `PENDING_MFA`,
  `COMPLETED`, `FAILED`, `EXPIRED`.
- MFA simulada: umbral **≥ 1.000.000 COP**, código fijo **`123456`**, ventana de **5 minutos**,
  reintentos permitidos sin lockout, re-verificación de fondos al confirmar, atomicidad de
  saldos.
- La API nunca expone identificadores internos (UUID, IDs de base de datos, números de cuenta).

### Decisiones del investigador incorporadas

- **E2-KIRO-D01** — Límites por defecto: por transferencia **5.000.000 COP**, diario
  acumulado **10.000.000 COP**; configurables; aplican a internas, ACH y recurrentes.
- **E2-KIRO-D02** — Pagos recurrentes ejecutados por un **scheduler activo en segundo plano**,
  idempotente, testable de forma determinista, sin endpoint administrativo público.
- **E2-KIRO-D03** — Estados internos en MAYÚSCULAS preservados; estados ACH en minúsculas
  (`pending`/`settled`/`failed`); historial unificado con campo de tipo `internal`/`ach`.
- **E2-KIRO-D04** — Las ACH directas requieren MFA si monto **≥ 1.000.000 COP** (mismo umbral
  de E1); los límites y los fondos se comprueban **antes** de completar la MFA.
- **E2-KIRO-D05** — Historial de internas sin cambios de forma; las entradas ACH añaden datos
  del beneficiario con el **número de cuenta enmascarado** (solo últimos 4 dígitos).
- **E2-KIRO-D06** — Reanudación de recurrentes **sin catch-up**: las ocurrencias perdidas
  durante una pausa se saltan; al reanudar, la siguiente fecha se recalcula desde la
  reanudación, sin pagos duplicados ni débitos acumulados.

### Términos y convenciones

- **ACH (simulada):** transferencia saliente a un tercero externo. No existe red de
  compensación real ni validación ABA externa; solo validación de formato.
- **Beneficiario:** destinatario externo de una ACH (nombre, banco, routing, número de cuenta).
  *Guardado* (persistido y reutilizable) o *ad hoc* (provisto para una sola operación).
- **Transferencia sensible:** monto ≥ COP 1.000.000 (umbral MFA heredado), aplicable a
  internas y ACH.
- **Estados ACH:** `pending` (autorizada, debitada, en proceso), `settled` (liquidada),
  `failed` (fallida tras débito, con reembolso exactamente-una-vez).
- **Schedule:** definición de un pago recurrente. Estados: `active`, `paused`, `cancelled`.
- **Día (para límites):** frontera de día en **UTC** (contrato LIM-06).
- **Intervalos de recurrencia:** diario = 1 día, semanal = 7 días, mensual = 30 días
  (contrato REC-02; 30 días no es un mes calendario).
- **decimal-string:** monto transportado en la API como cadena decimal exacta con 2 decimales.

### Convención de criterios de aceptación (EARS)

Los criterios siguen el estilo EARS heredado de la Etapa 1: "CUANDO … ENTONCES el sistema
DEBERÁ …", "SI … ENTONCES el sistema DEBERÁ …", y "EN TODO MOMENTO el sistema DEBERÁ …". Cada
criterio describe comportamiento observable y verificable.

### Alcance excluido (fuera de la Etapa 2)

- Red ACH real, compensación, validación ABA externa o transferencias de dinero reales.
- Registro o inicio de sesión real, verificación de identidad.
- Funcionalidad de Etapa 3/4 (cifrado de extremo a extremo, auditoría inmutable,
  multi-moneda, Event Sourcing/CQRS).
- Un endpoint administrativo público cuyo único fin sea disparar los pagos recurrentes.

---

## Requisitos

## A. Transferencias ACH externas y beneficiarios

### Requisito 1 — Gestión de beneficiarios (guardados y ad hoc)

**Historia de usuario:** Como cliente de Shift Bank, quiero guardar beneficiarios externos y
también poder usar uno puntual sin guardarlo, para enviar transferencias ACH de forma cómoda y
segura.

#### Criterios de aceptación

1. CUANDO el cliente crea un beneficiario guardado con datos válidos, ENTONCES el sistema
   DEBERÁ persistirlo asociado al cliente mock y permitir recuperarlo en operaciones futuras.
   _(ACH-01, ACH-02; A03)_
2. CUANDO el cliente inicia una transferencia ACH, ENTONCES el sistema DEBERÁ permitir
   seleccionar un beneficiario guardado existente O proporcionar un beneficiario ad hoc para
   esa operación. _(ACH-01; A03, A04)_
3. CUANDO el cliente proporciona un beneficiario ad hoc, ENTONCES el sistema DEBERÁ permitir
   opcionalmente guardarlo como beneficiario reutilizable en la misma operación. _(ACH-01,
   ACH-09; A04)_
4. EN TODO MOMENTO el sistema DEBERÁ restringir la creación, recuperación y gestión de
   beneficiarios al cliente mock, sin exponer ni permitir el acceso a datos de otro usuario.
   _(ACH-02)_
5. CUANDO el cliente lista o consulta beneficiarios, ENTONCES el sistema DEBERÁ devolver el
   nombre, el banco y el número de cuenta **enmascarado** (solo los últimos 4 dígitos), sin
   exponer el número de cuenta completo ni identificadores internos. _(ACH-02, D05; Req. 2 E1)_
6. CUANDO el cliente elimina un beneficiario guardado, ENTONCES el sistema DEBERÁ dejar de
   ofrecerlo para nuevas operaciones, PERO NO DEBERÁ invalidar transferencias ACH ya
   autorizadas ni pagos recurrentes ya autorizados que lo referencien. _(ACH-02, REC-11)_

### Requisito 2 — Validación de formato de beneficiario ACH

**Historia de usuario:** Como cliente, quiero que el sistema valide los datos del beneficiario
antes de permitir la transferencia, para evitar errores de captura.

#### Criterios de aceptación

1. CUANDO se captura un beneficiario (guardado o ad hoc), ENTONCES el sistema DEBERÁ exigir
   nombre, banco, número de routing y número de cuenta. _(ACH-03)_
2. CUANDO se valida el número de routing, ENTONCES el sistema DEBERÁ aceptarlo solo si contiene
   exactamente **9 dígitos numéricos**, y rechazarlo en cualquier otro caso (p. ej. 8 dígitos o
   caracteres no numéricos). _(ACH-03, ACH-10; A05)_
3. CUANDO se valida el número de cuenta, ENTONCES el sistema DEBERÁ aceptarlo solo si contiene
   entre **4 y 17 dígitos numéricos** (inclusive), y rechazarlo fuera de ese rango (p. ej. 3 o
   18 dígitos). _(ACH-03; A06)_
4. CUANDO el cliente introduce un número de routing inválido en el formulario, ENTONCES el
   sistema DEBERÁ señalar el error durante la captura, antes del envío, e impedir el envío
   hasta que sea válido. _(ACH-10; A05)_
5. EN TODO MOMENTO el sistema DEBERÁ validar únicamente el **formato** de routing y cuenta, sin
   contactar a ningún banco externo ni realizar validación ABA real. _(ACH-03)_

### Requisito 3 — Creación y autorización de transferencias ACH

**Historia de usuario:** Como cliente, quiero enviar dinero a un beneficiario externo mediante
ACH, autorizando con MFA las transferencias sensibles, para pagar a terceros de forma segura.

#### Criterios de aceptación

1. CUANDO el cliente solicita una transferencia ACH, ENTONCES el sistema DEBERÁ validar que el
   monto es positivo y tiene como máximo **2 decimales**, que la cuenta de origen existe, que
   los fondos son suficientes y que se cumplen todos los límites vigentes. _(ACH-04; A09)_
2. CUANDO el monto ACH es menor a COP 1.000.000 y supera todas las validaciones, ENTONCES el
   sistema DEBERÁ autorizar la transferencia sin requerir MFA. _(ACH-04, D04)_
3. CUANDO el monto ACH es mayor o igual a COP 1.000.000, ENTONCES el sistema DEBERÁ requerir
   MFA simulada (código `123456`, ventana de 5 minutos) antes de autorizar la transferencia, y
   NO DEBERÁ debitar la cuenta hasta que la MFA tenga éxito. _(ACH-04, HER-04, D04; A13)_
4. CUANDO se evalúan las validaciones de una ACH sensible, ENTONCES el sistema DEBERÁ comprobar
   los **límites** y los **fondos antes** de completar la autorización MFA, de modo que un
   código MFA correcto nunca permita superar un límite ni transferir con fondos insuficientes.
   _(LIM-07, HER-04, D04; A14)_
5. CUANDO una transferencia ACH queda autorizada (con o sin MFA), ENTONCES el sistema DEBERÁ
   registrarla en estado `pending`, **debitar de inmediato** el monto de la cuenta de origen y
   mostrarla como `pending` en el historial. _(ACH-05, D04; A07)_
6. CUANDO la autorización MFA de una ACH sensible falla o expira, ENTONCES el sistema NO DEBERÁ
   producir ningún débito en la cuenta de origen. _(D04; A08)_
7. EN TODO MOMENTO el débito inmediato de una ACH `pending` DEBERÁ aplicarse de forma atómica y
   consistente, sin dejar la cuenta en estado inconsistente ante un fallo. _(ACH-08, HER-05)_
8. CUANDO el cliente solicita una transferencia ACH con un monto **menor o igual a cero** o con
   **más de dos decimales**, ENTONCES el sistema DEBERÁ rechazarla, NO DEBERÁ producir ningún
   débito en la cuenta de origen, y DEBERÁ hacerlo de forma consistente con el modelo monetario
   heredado de la Etapa 1 (centavos enteros, COP, cálculo con `Decimal`; coherente con el
   Requisito 3.3 de la Etapa 1: monto no positivo rechazado). _(ACH-04; A09)_

### Requisito 4 — Liquidación (settlement) automática de transferencias ACH

**Historia de usuario:** Como cliente, quiero que mis transferencias ACH avancen a liquidadas
automáticamente, para reflejar el progreso de la operación sin intervención manual.

#### Criterios de aceptación

1. EN TODO MOMENTO una transferencia ACH DEBERÁ ser elegible para liquidación **únicamente** si
   es una ACH autorizada que se encuentra actualmente en estado `pending`; las transferencias en
   estado `settled` o `failed` NO DEBERÁN ser elegibles. _(ACH-06; A07)_
2. CUANDO una transferencia ACH `pending` satisface la **condición de liquidación de la
   simulación documentada**, ENTONCES el sistema DEBERÁ avanzarla automáticamente a `settled` y
   registrar su marca de tiempo de liquidación. La condición de elegibilidad DEBERÁ ser
   **determinista e independientemente verificable** (p. ej. evaluable con un reloj inyectable);
   el mecanismo de planificación y el retardo de simulación concretos se establecerán en la fase
   de diseño, sin introducir una red bancaria real ni reglas de negocio financieras arbitrarias.
   _(ACH-06, D02; A07)_
3. CUANDO una transferencia ACH pasa a `settled`, ENTONCES el sistema NO DEBERÁ volver a
   debitar la cuenta de origen (el débito ya ocurrió al crearse en `pending`). _(ACH-06; A07)_
4. EN TODO MOMENTO la liquidación DEBERÁ ser idempotente: reprocesar o reintentar la transición
   de una ACH ya `settled` o `failed` NO DEBERÁ alterar saldos ni duplicar efectos. _(ACH-08;
   A07)_

### Requisito 5 — Fallo de transferencias ACH y reembolso exactamente-una-vez

**Historia de usuario:** Como cliente, quiero que, si una transferencia ACH falla, se me
reintegre exactamente el monto debitado, para no perder dinero por un fallo del proceso.

#### Criterios de aceptación

1. CUANDO una transferencia ACH previamente debitada falla, ENTONCES el sistema DEBERÁ marcarla
   como `failed` y reembolsar a la cuenta de origen **exactamente el monto** que había sido
   debitado. _(ACH-07; A08)_
2. EN TODO MOMENTO el reembolso de una ACH fallida DEBERÁ aplicarse **exactamente una vez**,
   incluso si la transición a `failed` se reintenta o reprocesa (sin doble reembolso). _(ACH-07,
   ACH-08; A08)_
3. CUANDO se registra el fallo de una ACH, ENTONCES el sistema NO DEBERÁ requerir obligatoriamente
   un asiento contable compensatorio adicional visible en el contrato público, siempre que el
   saldo persistido y el registro de la transferencia queden consistentes. _(ACH-07)_
4. EN TODO MOMENTO ni las transiciones de estado duplicadas ni el reprocesamiento ordinario
   DEBERÁN producir doble débito ni doble reembolso; el saldo y los registros persistidos
   DEBERÁN permanecer consistentes. _(ACH-08; A08)_

### Requisito 6 — Historial unificado con transferencias internas y ACH

**Historia de usuario:** Como cliente, quiero ver en un solo historial tanto mis transferencias
internas como las ACH, distinguiéndolas con claridad, para entender toda mi actividad.

#### Criterios de aceptación

1. CUANDO el cliente consulta el historial, ENTONCES el sistema DEBERÁ incluir tanto las
   transferencias internas como las ACH, y cada entrada DEBERÁ identificar su tipo (`internal`
   o `ach`). _(ACH-05, D03; A01, A07)_
2. CUANDO el historial incluye una transferencia interna, ENTONCES el sistema DEBERÁ preservar
   su representación de Etapa 1 sin cambios de forma (incluido `direction { from, to }` con
   nombres amigables y los estados en MAYÚSCULAS `PENDING_MFA`/`COMPLETED`/`FAILED`/`EXPIRED`).
   _(D03, D05, HER-01, HER-02; A01, A02)_
3. CUANDO el historial incluye una transferencia ACH, ENTONCES el sistema DEBERÁ exponer su
   estado en minúsculas (`pending`/`settled`/`failed`) y una representación del beneficiario con
   nombre, banco y número de cuenta **enmascarado** (solo los últimos 4 dígitos). _(D03, D05)_
4. EN TODO MOMENTO el historial NO DEBERÁ exponer números de cuenta de beneficiario completos,
   identificadores internos ni otra información bancaria sensible innecesaria. _(D05; Req. 2 E1)_
5. CUANDO el sistema expone montos en el historial, ENTONCES los DEBERÁ presentar como cadenas
   decimales exactas con 2 decimales (decimal-string). _(HER-01; Req. 5 E1)_

### Requisito 7 — Experiencia de usuario de transferencias ACH

**Historia de usuario:** Como cliente, quiero un formulario de ACH claro, con validación
inmediata y visibilidad del estado, para completar transferencias externas con confianza.

> Cobertura de ACH-09 (cuatro comportamientos de UI requeridos): (a) diferenciar interno vs ACH
> → criterio 7.1; (b) seleccionar beneficiario guardado o ad hoc → criterio 7.1; (c) ofrecer la
> opción de guardar un beneficiario nuevo → criterio 7.2; (d) mostrar el estado de la
> transferencia ACH → criterio 7.4.

#### Criterios de aceptación

1. CUANDO el cliente usa la interfaz, ENTONCES el sistema DEBERÁ **diferenciar claramente las
   transferencias internas de las ACH** y **permitir seleccionar un beneficiario guardado o ad
   hoc** para una ACH. _(ACH-09 [a][b])_
2. CUANDO el cliente captura un beneficiario ad hoc, ENTONCES la interfaz DEBERÁ **ofrecer la
   opción de guardarlo** y transferir en la misma operación. _(ACH-09 [c]; A04)_
3. CUANDO el cliente introduce un routing o un número de cuenta con formato inválido, ENTONCES
   la interfaz DEBERÁ mostrar retroalimentación inmediata y evitar el envío hasta corregirlo.
   _(ACH-10; A05, A06)_
4. CUANDO una transferencia ACH cambia de estado (`pending`/`settled`/`failed`), ENTONCES la
   interfaz DEBERÁ **mostrar el estado actual** de forma comprensible para el usuario.
   _(ACH-09 [d])_

## B. Pagos recurrentes

### Requisito 8 — Creación de pagos recurrentes

**Historia de usuario:** Como cliente, quiero programar pagos que se repitan automáticamente,
internos o ACH, para no tener que iniciarlos manualmente cada vez.

#### Criterios de aceptación

1. CUANDO el cliente crea un pago recurrente, ENTONCES el sistema DEBERÁ aceptar un origen
   válido, un destino válido (cuenta interna o beneficiario ACH) y un monto válido (positivo,
   máximo 2 decimales). _(REC-01; A17)_
2. CUANDO se define la frecuencia, ENTONCES el sistema DEBERÁ permitir **diaria, semanal o
   mensual**, interpretadas como incrementos de **1, 7 y 30 días** respectivamente. _(REC-02;
   A16)_
3. CUANDO se crea un schedule, ENTONCES el sistema DEBERÁ inicializarlo en estado `active`.
   _(REC-03)_
4. CUANDO el cliente proporciona una fecha de inicio futura válida, ENTONCES el sistema DEBERÁ
   usarla como **primera fecha de vencimiento**. _(REC-04)_
5. CUANDO el cliente no proporciona fecha de inicio, ENTONCES el sistema DEBERÁ fijar la primera
   ejecución tras **un intervalo completo** configurado, nunca de inmediato en la creación.
   _(REC-04; A15)_
6. CUANDO el schedule corresponde a un pago sensible (monto ≥ COP 1.000.000), ENTONCES el
   sistema DEBERÁ requerir autorización MFA **en el momento de la creación** del schedule, y NO
   DEBERÁ requerir MFA interactiva en cada ejecución automática. _(REC-09, D02, D04)_
7. CUANDO se crea un schedule ACH, ENTONCES el sistema DEBERÁ retener datos de destino
   suficientes para ejecutarlo aunque el beneficiario guardado se elimine posteriormente.
   _(REC-11)_

### Requisito 9 — Estados del schedule y controles de ciclo de vida

**Historia de usuario:** Como cliente, quiero pausar, reanudar o cancelar mis pagos recurrentes,
para controlar su ejecución.

#### Criterios de aceptación

1. CUANDO el cliente pausa un schedule `active`, ENTONCES el sistema DEBERÁ ponerlo en estado
   `paused`. _(REC-06; A18)_
2. CUANDO el cliente reanuda un schedule `paused`, ENTONCES el sistema DEBERÁ volverlo `active`
   y elegible para ejecución. _(REC-06; A18)_
3. CUANDO el cliente cancela un schedule, ENTONCES el sistema DEBERÁ ponerlo en estado
   `cancelled`, que es **terminal**. _(REC-06, REC-07; A18)_
4. CUANDO se intenta reanudar o modificar un schedule `cancelled`, ENTONCES el sistema DEBERÁ
   rechazar la transición sin mutar el estado (la cancelación no se revierte). _(REC-07; A18)_
5. EN TODO MOMENTO los schedules en estado `paused` o `cancelled` NO DEBERÁN ejecutarse, aun si
   su fecha de vencimiento ya pasó. _(REC-08; A18)_
6. CUANDO un schedule `paused` se reanuda, ENTONCES el sistema DEBERÁ **saltar** las ocurrencias
   cuya fecha de vencimiento pasó durante la pausa (sin ejecutarlas retroactivamente) y
   **recalcular la siguiente fecha de vencimiento desde la fecha de reanudación** usando el
   intervalo de recurrencia configurado (1, 7 o 30 días), sin producir pagos duplicados ni
   débitos acumulados inmediatos. _(REC-06, REC-08, REC-02, D06; A18)_
7. EN TODO MOMENTO un schedule `cancelled` DEBERÁ permanecer terminal y NO DEBERÁ poder
   reanudarse ni recalcular fechas de vencimiento. _(REC-07, D06; A18)_

### Requisito 10 — Ejecución automática por scheduler en segundo plano

**Historia de usuario:** Como cliente, quiero que mis pagos recurrentes se ejecuten solos al
vencer, sin abrir la aplicación, para que ocurran a tiempo.

#### Criterios de aceptación

1. CUANDO un schedule `active` alcanza su fecha de vencimiento, ENTONCES el sistema DEBERÁ
   ejecutarlo automáticamente mediante un proceso en segundo plano, sin requerir que el usuario
   abra la aplicación, haga una petición a la API ni dispare la ejecución manualmente. _(REC-05,
   D02; A17)_
2. EN TODO MOMENTO el proceso de ejecución automática DEBERÁ operar mientras el backend está en
   ejecución, con arranque y apagado limpios de la aplicación. _(D02)_
3. CUANDO una ocurrencia programada se ejecuta, ENTONCES el sistema DEBERÁ garantizar que esa
   ocurrencia individual **no se ejecute más de una vez**, incluso si el procesamiento se
   reintenta. _(D02; ACH-08)_
4. CUANDO una ejecución recurrente tiene éxito, ENTONCES el sistema DEBERÁ actualizar saldos y
   movimientos conforme al tipo (interno o ACH) y calcular la **siguiente** fecha de
   vencimiento según la frecuencia. _(REC-05; A17)_
5. EN TODO MOMENTO la lógica de "ejecutar schedules vencidos" DEBERÁ ser verificable de forma
   **determinista** (p. ej. con un reloj inyectable), sin depender exclusivamente de la espera
   en tiempo real. _(D02)_
6. EN TODO MOMENTO el sistema NO DEBERÁ exponer un endpoint administrativo público cuyo único
   fin sea disparar los pagos recurrentes. _(D02; contrato §3, §7)_

### Requisito 11 — Revalidación y manejo de fallos en cada ejecución recurrente

**Historia de usuario:** Como cliente, quiero que cada ejecución recurrente respete mis fondos y
límites vigentes, y que un fallo no deje el pago atascado, para que el sistema se mantenga
consistente.

#### Criterios de aceptación

1. CUANDO una ocurrencia recurrente va a ejecutarse, ENTONCES el sistema DEBERÁ revalidar los
   fondos disponibles, los límites vigentes (por transferencia y diario) y las reglas de negocio
   aplicables en ese momento. _(REC-09, LIM-08, D01, D02; A19)_
2. CUANDO una ejecución recurrente falla por fondos insuficientes o por exceder un límite,
   ENTONCES el sistema DEBERÁ registrar el fallo **sin debitar** y avanzar la siguiente fecha de
   vencimiento, de modo que el schedule no quede atascado. _(REC-10, LIM-08; A19)_
3. CUANDO una ejecución recurrente de tipo ACH ocurre, ENTONCES el sistema DEBERÁ aplicar el
   mismo ciclo de vida ACH (`pending` con débito inmediato, settlement, reembolso
   exactamente-una-vez en fallo) que una ACH directa. _(REC-01, ACH-05..08)_
4. EN TODO MOMENTO una ejecución recurrente sensible NO DEBERÁ solicitar MFA interactiva; la
   autorización se concedió al crear el schedule (Requisito 8.6). _(REC-09, D02, D04)_

### Requisito 12 — Gestión y visualización de pagos recurrentes (frontend)

**Historia de usuario:** Como cliente, quiero ver y administrar mis pagos recurrentes, para
saber su estado y próxima ejecución.

#### Criterios de aceptación

1. CUANDO el cliente consulta sus pagos recurrentes, ENTONCES la interfaz DEBERÁ listar el
   estado de cada schedule (`active`/`paused`/`cancelled`) y su **próxima fecha de vencimiento**.
   _(REC-12)_
2. CUANDO el cliente administra un schedule, ENTONCES la interfaz DEBERÁ soportar su creación y
   las acciones de pausar, reanudar y cancelar. _(REC-12; A18)_
3. CUANDO ocurre una acción o un cambio de estado en un schedule, ENTONCES la interfaz DEBERÁ
   mostrar retroalimentación comprensible para el usuario. _(REC-12)_

## C. Límites de transacción dinámicos

### Requisito 13 — Configuración de límites por transferencia y diario

**Historia de usuario:** Como cliente, quiero definir cuánto puedo transferir por operación y
por día, para controlar mi exposición.

#### Criterios de aceptación

1. CUANDO el sistema inicia sin límites configurados por el usuario, ENTONCES el sistema DEBERÁ
   usar los valores por defecto aprobados: **5.000.000 COP** por transferencia y **10.000.000
   COP** diario acumulado. _(LIM-01, D01)_
2. CUANDO el cliente consulta sus límites, ENTONCES la interfaz DEBERÁ mostrar los valores
   vigentes y, opcionalmente, el consumo del día y la disponibilidad restante. _(LIM-02; A10)_
3. CUANDO el cliente edita un límite con un valor válido, ENTONCES el sistema DEBERÁ
   persistirlo y aplicarlo a las transferencias posteriores. _(LIM-01, LIM-02; A10)_
4. CUANDO el cliente envía una actualización de límite inválida (p. ej. valor negativo o con
   precisión monetaria fuera del contrato), ENTONCES el sistema DEBERÁ rechazarla sin modificar
   los límites vigentes. _(LIM-09; A09)_
5. EN TODO MOMENTO los límites configurados DEBERÁN mantenerse en el modelo monetario heredado
   (centavos enteros, COP). _(D01, HER-01)_

### Requisito 14 — Aplicación de los límites

**Historia de usuario:** Como cliente, quiero que los límites se apliquen de forma consistente a
todas mis transferencias, para que el control sea efectivo.

#### Criterios de aceptación

1. CUANDO una transferencia (interna, ACH o ejecución recurrente) excede el **límite por
   transferencia** vigente, ENTONCES el sistema DEBERÁ rechazarla, con independencia de que haya
   fondos suficientes o de un código MFA correcto. _(LIM-03, LIM-07; A11, A14)_
2. CUANDO una transferencia haría que el **consumo diario acumulado** superara el límite diario
   vigente, ENTONCES el sistema DEBERÁ rechazarla. _(LIM-04; A12)_
3. CUANDO el consumo diario se calcula, ENTONCES el sistema DEBERÁ usar una frontera de **día
   UTC** documentada, contando las transferencias internas `COMPLETED` y las ACH `pending`/
   `settled`, y **excluyendo** las ACH `failed` tras su reembolso, sin doble conteo de
   transiciones. _(LIM-06; A12)_
4. CUANDO una transferencia alcanza **exactamente** el límite por transferencia o el límite
   diario disponible, ENTONCES el sistema DEBERÁ permitirla si todas las demás validaciones
   pasan. _(LIM-05; A11, A12)_
5. CUANDO una transferencia sensible requiere MFA, ENTONCES el sistema DEBERÁ comprobar los
   límites **antes** de completar la autorización MFA, de modo que un código correcto nunca
   permita superar un límite. _(LIM-07, D04; A14)_
6. CUANDO cada ejecución recurrente ocurre, ENTONCES el sistema DEBERÁ re-evaluar los límites
   vigentes y el saldo disponible en ese momento. _(LIM-08, D02; A19)_

## D. Compatibilidad con la Etapa 1 (invariantes heredados)

### Requisito 15 — Preservación del comportamiento de la Etapa 1

**Historia de usuario:** Como responsable del experimento, quiero que toda la funcionalidad de
la Etapa 1 siga intacta tras añadir la Etapa 2, para evaluar una evolución brownfield sin
regresiones.

#### Criterios de aceptación

1. EN TODO MOMENTO las cuentas, los saldos, el historial y las consultas existentes de la Etapa
   1 DEBERÁN seguir funcionando. _(HER-01; A01)_
2. EN TODO MOMENTO las transferencias internas y sus registros de débito/crédito DEBERÁN
   permanecer correctos y con los mismos estados en MAYÚSCULAS y la misma forma de API. _(HER-02,
   D03; A02)_
3. EN TODO MOMENTO el sistema DEBERÁ conservar el modelo monetario heredado: centavos enteros,
   moneda COP y decimal-string en la API. _(HER-01, D01)_
4. EN TODO MOMENTO el sistema DEBERÁ preservar el esquema MFA heredado: código `123456`, umbral
   1.000.000 COP, expiración de 5 minutos, reintento sin lockout y las transiciones de estado
   existentes. _(HER-03, D04; A13)_
5. EN TODO MOMENTO el sistema DEBERÁ preservar los campos de respuesta de API y la funcionalidad
   del frontend existentes, sin renombrar, eliminar ni reestructurar los campos de las
   transferencias internas. _(HER-01, D03, D05; A01)_
6. EN TODO MOMENTO el sistema DEBERÁ mantener el modelo de cliente mock ya autenticado, sin
   registro, sin autenticación real, sin API bancaria real y sin funcionalidad de Etapa 3/4.
   _(HER-06)_
7. EN TODO MOMENTO los fallos de negocio o de persistencia NO DEBERÁN dejar saldos ni estados de
   transacción inconsistentes. _(HER-05; A08)_
8. EN TODO MOMENTO el sistema NO DEBERÁ modificar los saldos heredados ni las transacciones
   históricas sembradas de la Etapa 1. _(D01, HER-01)_

### Requisito 16 — Alcance técnico de la Etapa 2

**Historia de usuario:** Como responsable del proyecto, quiero que la Etapa 2 reutilice el stack
heredado y no introduzca dependencias innecesarias, para mantener comparabilidad y control del
alcance.

#### Criterios de aceptación

1. CUANDO se implementa el backend de la Etapa 2, ENTONCES el sistema DEBERÁ seguir usando
   Python/FastAPI sobre `sqlite3` sin ORM, compatible con la arquitectura heredada. _(HER-01)_
2. CUANDO se implementa el frontend de la Etapa 2, ENTONCES el sistema DEBERÁ seguir usando
   React con TypeScript y CSS puro, preservando el renderizado existente de las transferencias
   internas. _(D05, HER-01)_
3. CUANDO el esquema de base de datos evoluciona para la Etapa 2, ENTONCES el sistema DEBERÁ
   hacerlo de forma que las bases de datos ya sembradas de la Etapa 1 sigan siendo válidas, sin
   alterar los datos heredados. _(HER-01, HER-05)_
4. EN TODO MOMENTO la implementación DEBERÁ limitarse al alcance aprobado de la Etapa 2 (ACH,
   recurrentes, límites) y a las decisiones E2-KIRO-D01..D05, sin añadir funcionalidad fuera de
   alcance. _(contrato §7)_

---

## Trazabilidad al contrato funcional común

### Capacidad A — ACH (ACH-01..10)

| Contrato | Requisitos |
|---|---|
| ACH-01 | 1.1, 1.2, 1.3 |
| ACH-02 | 1.1, 1.4, 1.5, 1.6, 6.4 |
| ACH-03 | 2.1, 2.2, 2.3, 2.5 |
| ACH-04 | 3.1, 3.2, 3.3, 3.8 |
| ACH-05 | 3.5, 6.1, 6.3 |
| ACH-06 | 4.1, 4.2, 4.3 |
| ACH-07 | 5.1, 5.2, 5.3 |
| ACH-08 | 3.7, 4.4, 5.2, 5.4, 10.3 |
| ACH-09 | 7.1 [a][b], 7.2 [c], 7.4 [d] |
| ACH-10 | 2.2, 2.4, 7.3 |

### Capacidad B — Recurrentes (REC-01..12)

| Contrato | Requisitos |
|---|---|
| REC-01 | 8.1, 11.3 |
| REC-02 | 8.2 |
| REC-03 | 8.3 |
| REC-04 | 8.4, 8.5 |
| REC-05 | 10.1, 10.4 |
| REC-06 | 9.1, 9.2, 9.3, 9.6, 12.2 |
| REC-07 | 9.3, 9.4, 9.7 |
| REC-08 | 9.5, 9.6 |
| REC-09 | 8.6, 11.1, 11.4 |
| REC-10 | 11.2 |
| REC-11 | 1.6, 8.7 |
| REC-12 | 12.1, 12.2, 12.3 |

### Capacidad C — Límites (LIM-01..09)

| Contrato | Requisitos |
|---|---|
| LIM-01 | 13.1, 13.3 |
| LIM-02 | 13.2, 13.3 |
| LIM-03 | 14.1 |
| LIM-04 | 14.2 |
| LIM-05 | 14.4 |
| LIM-06 | 14.3 |
| LIM-07 | 3.4, 14.1, 14.5 |
| LIM-08 | 11.1, 14.6 |
| LIM-09 | 13.4 |

### Invariantes heredados (HER-01..06)

| Contrato | Requisitos |
|---|---|
| HER-01 | 6.2, 13.5, 15.1, 15.3, 15.5, 15.8, 16.1, 16.3 |
| HER-02 | 6.2, 15.2 |
| HER-03 | 15.4 |
| HER-04 | 3.3, 3.4 |
| HER-05 | 3.7, 5.4, 15.7, 16.3 |
| HER-06 | 15.6 |

### Escenarios de aceptación (A01..A21)

| Escenario | Requisitos | Escenario | Requisitos |
|---|---|---|---|
| A01 | 6.1, 6.2, 15.1, 15.5 | A12 | 14.2, 14.3, 14.4 |
| A02 | 6.2, 15.2 | A13 | 3.3, 15.4 |
| A03 | 1.1, 1.2 | A14 | 3.4, 14.1, 14.5 |
| A04 | 1.2, 1.3, 7.2 | A15 | 8.5, 10.1 |
| A05 | 2.2, 2.4, 7.3 | A16 | 8.2 |
| A06 | 2.3, 7.3 | A17 | 8.1, 10.1, 10.4 |
| A07 | 3.5, 4.2, 4.3, 4.4, 6.1 | A18 | 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 12.2 |
| A08 | 3.6, 5.1, 5.2, 15.7 | A19 | 11.1, 11.2, 14.6 |
| A09 | 3.1, 3.8 | A20 | (obligación de verificación; ver nota) |
| A10 | 13.2, 13.3 | A21 | 7.x, 12.x (inspección manual de UI) |
| A11 | 14.1, 14.4 | | |

> **Nota sobre A20 y A21:** A20 y A21 son escenarios de **verificación**, no requisitos
> funcionales, y se mantienen como obligaciones de verificación (no se convierten en requisitos
> funcionales artificiales).
>
> **A20 — obligación de verificación.** El futuro `tasks.md` DEBERÁ incluir explícitamente:
> (1) la **creación de una suite de pruebas de regresión de la Etapa 1**, dado que la aplicación
> heredada no tiene pruebas automatizadas; (2) la **ejecución de las pruebas de regresión** de
> la funcionalidad heredada; (3) la **ejecución de las nuevas pruebas de aceptación de la Etapa
> 2**; (4) la **ejecución del build de producción del frontend**; y (5) el **registro de los
> resultados y fallos reales** de las pruebas. La ejecución de estas tareas pertenece a la fase
> posterior; aquí solo se documenta la obligación.
>
> **A21 — obligación de verificación manual, separada de A20.** Inspección manual de la UI en
> navegador (navegación, formularios, validación, estado y controles de schedules), reportando
> lo realmente observado. Se mantiene como obligación independiente de A20.

---

## Relación con las especificaciones heredadas de la Etapa 1

Esta especificación es una **feature spec nueva** (`shift-bank-stage2`) que **no modifica** la
spec heredada `shift-bank` (Requisitos 1–9 de la Etapa 1). Los requisitos de la Etapa 2
**referencian** los invariantes heredados (HER-01..06 y los Requisitos 1–9 de E1) como línea
base a preservar, en lugar de duplicarlos. En particular:

- Los Requisitos 15 y 16 encapsulan la preservación de la Etapa 1 y su alcance técnico.
- Las transferencias internas (E1 Req. 3, 5–8) se preservan y se referencian desde los
  Requisitos 6, 14 y 15, sin reescribirse.
- El esquema MFA (E1 Req. 6–8) se reutiliza para ACH (Requisito 3) y para la autorización de
  schedules sensibles (Requisito 8.6), conforme a E2-KIRO-D04.

---

## Ambigüedades, supuestos y brechas restantes

1. **Supuesto técnico (dentro de la libertad de Kiro, D03/D05 punto 7):** el historial unificado
   se expone extendiendo el recurso existente `GET /api/transfers`; la forma concreta de los
   campos ACH (nombres, anidamiento) se decidirá en `design.md`. No afecta a la compatibilidad
   hacia atrás de las entradas internas.
2. **Supuesto de disparo del settlement ACH (D02/contrato):** "settlement automático" (ACH-06) y
   "ejecución recurrente automática" (REC-05) comparten el mecanismo de scheduler en segundo
   plano aprobado en D02; el contrato no exige un endpoint público para ninguno. El acoplamiento
   concreto se resolverá en diseño.
3. **Brecha heredada conocida (no es contradicción):** la Etapa 1 no incluye suite de pruebas
   automatizadas. A20 exige ejecutar "todos los tests de E1"; al no existir, la introducción de
   una suite será parte de `tasks.md`, no de este documento.
4. **Sin contradicciones materiales abiertas:** las cinco ambigüedades iniciales (A–E) quedaron
   resueltas por E2-KIRO-D01..D05 y están reflejadas sin conflicto en estos requisitos.

Ninguna de estas notas introduce una decisión de negocio nueva: son supuestos técnicos dentro
de la libertad arquitectónica concedida, o brechas heredadas a tratar en fases posteriores.
