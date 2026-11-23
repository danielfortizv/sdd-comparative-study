# Requirements Document

> Documento canónico de requisitos de la Etapa 4 (Opción A) en el formato nativo de Kiro. Los
> encabezados canónicos en inglés (`Requirements Document`, `Introduction`, `Requirements`,
> `Glossary`) satisfacen el validador; el contenido se mantiene en español por coherencia con
> las especificaciones heredadas de las Etapas 1, 2 y 3.

## Introduction

## Introducción

La Etapa 4 evoluciona de forma **disruptiva** el modelo bancario de Shift Bank heredado de la
Etapa 3 (desarrollo brownfield) hacia cuentas **multidivisa**, **conversión de divisas** con
tasas racionales exactas, **Event Sourcing** del dominio monetario y **CQRS**, sin reescribir la
arquitectura por capas (FastAPI + `sqlite3` sin ORM, configuración por constantes en
`app/config.py`, `DB_PATH`; frontend React + TypeScript con CSS puro) y preservando el
comportamiento y las salvaguardas bancarias observables de las Etapas 1–3. No es una aplicación
nueva ni una funcionalidad construida desde cero.

Sobre el mismo cliente mock ya autenticado, la Etapa 4 incorpora:

1. **Cuentas multidivisa** con identidad de moneda explícita (USD, EUR, GBP), identificadores
   públicos inmutables de cuenta (CHK-1001, SAV-2001, EUR-3001, GBP-4001) y saldos/historiales
   con moneda inequívoca.
2. **Conversión de divisas simulada** vía un endpoint dedicado, con tasas racionales fijas,
   precisión y redondeo deterministas (`ROUND_HALF_UP` una sola vez al final) y conservación de
   balance.
3. **Event Sourcing** del dominio de cuentas/transacciones: eventos de dominio durables en un
   almacén **separado** de la bitácora de auditoría HMAC heredada, con reconstrucción
   determinista del estado.
4. **CQRS**: separación de comandos (cambios de estado) y consultas (lecturas de saldo/historial)
   mediante proyecciones derivadas de los eventos, refrescadas atómicamente y reconstruibles.
5. **Idempotencia** por `Idempotency-Key` UUID y **concurrencia optimista** por versión de cuenta
   esperada, para prevenir dobles débitos/créditos, aplicación duplicada de eventos y saldos
   inconsistentes.
6. **Compatibilidad transversal**: internas, ACH, recurrentes, límites dinámicos, MFA, cifrado y
   auditoría siguen válidos y seguros bajo el modelo multidivisa, con límites y MFA expresados en
   **equivalente USD**.

Esta especificación se construye sobre el baseline heredado de las Etapas 1–3 y lo preserva. Las
decisiones de negocio abiertas fueron resueltas por el investigador antes de redactar estos
requisitos: las decisiones comunes **D-01 a D-14** de la guía de replicación de la Etapa 4, más
cinco decisiones de diseño aprobadas para esta ejecución de Kiro (**DK-01 a DK-05**, ver
Glosario). El contrato externo de aceptación es la matriz **AC4-01 .. AC4-20** (ver Verificación y
trazabilidad).

### Baseline heredado (Etapas 1–3) — autoritativo y preservado

- Backend Python/FastAPI sobre `sqlite3` sin ORM; frontend React + TypeScript con CSS puro.
  Configuración por constantes en `app/config.py`; ruta de base de datos `DB_PATH` (objeto
  `Path`). Conexiones por `app.db.get_connection()` (`check_same_thread=False`,
  `PRAGMA foreign_keys=ON`, `journal_mode=WAL`).
- Dinero en **centavos enteros** (`INTEGER`) en SQLite, `Decimal` en Python, transporte en API
  como **cadenas decimales** con 2 decimales; `BigInt`/centavos en frontend; sin floats
  financieros.
- Atomicidad financiera con `BEGIN IMMEDIATE` vía `txn.financial_transaction` (único escritor).
- Transferencias internas (estados MAYÚSCULAS), MFA simulada (código `123456`, ventana 5 min,
  reintento sin lockout), ACH (`pending_auth`/`pending`/`settled`/`failed` con reembolso
  exactamente-una-vez), recurrentes por un **único** scheduler idempotente, límites dinámicos
  (día UTC) para internas/ACH/recurrentes.
- Cifrado AES-256-GCM en reposo de identificadores sensibles; auditoría append-only encadenada
  con HMAC + ancla de cola, atómica con el cambio financiero; despliegue Docker Compose
  (Nginx TLS → FastAPI), secretos externos, volumen persistente.
- La API nunca expone identificadores internos (UUID); los números de cuenta de beneficiario van
  enmascarados.

### Decisión común crítica incorporada — Reset experimental de la fixture (D-02, DK-01)

La Etapa 3 de Kiro siembra **COP 5,000,000.00** (checking) y **COP 15,000,000.00** (savings), en
centavos enteros y SIN columna de moneda. La D-02 requiere una fixture distinta. El investigador
autoriza un **reset controlado de la fixture experimental** de la Etapa 4:

- CHK-1001: **USD 2,500.00**, SAV-2001: **USD 10,000.00**, EUR-3001: **EUR 0.00**,
  GBP-4001: **GBP 0.00**.
- Esto **NO** es una conversión COP→USD ni una migración que preserve valor monetario. Es una
  **discontinuidad experimental** declarada: cambia moneda, identidad de cuenta y valor por
  decisión de fixture, no por tipo de cambio.
- El estado y la evidencia originales de la Etapa 3 (COP) se preservan **sin modificación** en
  `Etapa 3/Kiro` y en los logs de preparación; la Etapa 4 parte de una fixture inicial separada.
- La verificación de preservación de datos, de migración y de rollback se hace sobre propiedades
  **estructurales** (migración aditiva/idempotente/transaccional/reversible; reconstrucción
  determinista desde eventos; sin doble conteo), **sin** afirmar equivalencia de valor COP↔USD.

### Convención de criterios de aceptación (EARS)

Los criterios siguen el estilo EARS heredado: "CUANDO ... ENTONCES el sistema DEBERÁ ...", "SI
... ENTONCES el sistema DEBERÁ ...", y "EN TODO MOMENTO el sistema DEBERÁ ...". Cada criterio
referencia entre paréntesis la decisión (D-0x / DK-0x) y el caso de aceptación externo (AC4-xx).

---

## Requirements

## Requisitos

## Parte I — Requisitos funcionales (FR)

## A. Cuentas multidivisa e identidad (D-01, D-02, D-10)

### Requisito 1 — Identidad de moneda por cuenta

**Historia de usuario:** Como titular de Shift Bank, quiero que cada cuenta tenga una moneda
explícita y fija, para ver saldos e historiales con una divisa inequívoca y no mezclar monedas en
un mismo saldo.

#### Criterios de aceptación

1. EN TODO MOMENTO cada cuenta DEBERÁ tener exactamente **una** moneda fija del conjunto
   soportado {USD, EUR, GBP}, establecida en su creación y nunca modificada. _(D-01; AC4-01)_
2. EN TODO MOMENTO el sistema NO DEBERÁ mezclar saldos de monedas distintas en un único saldo ni
   en un único total de cuenta. _(D-01; AC4-01)_
3. CUANDO el sistema expone una cuenta por la API, ENTONCES DEBERÁ incluir su **código de moneda
   ISO-4217** y su identificador público de cuenta, de modo que el saldo sea inequívoco. _(D-01,
   D-02; AC4-01, AC4-02)_
4. EN TODO MOMENTO el conjunto de monedas soportadas DEBERÁ limitarse a {USD, EUR, GBP}; una
   moneda fuera del conjunto DEBERÁ rechazarse con un error de dominio controlado. _(D-01;
   AC4-01)_

### Requisito 2 — Identificadores públicos de cuenta y fixture inicial

**Historia de usuario:** Como titular, quiero identificadores de cuenta estables y legibles, para
referenciar mis cuentas sin exponer identificadores internos.

#### Criterios de aceptación

1. EN TODO MOMENTO cada cuenta DEBERÁ tener un **identificador público inmutable** distinto de su
   identificador interno (UUID), que la API expone en lugar del interno. _(D-02, DK-02; AC4-02)_
2. CUANDO el sistema inicializa la fixture experimental de la Etapa 4, ENTONCES DEBERÁ crear
   exactamente estas cuentas: **CHK-1001 USD 2,500.00**, **SAV-2001 USD 10,000.00**,
   **EUR-3001 EUR 0.00**, **GBP-4001 GBP 0.00**. _(D-02, DK-01; AC4-03)_
3. EN TODO MOMENTO la identidad interna de cuenta heredada (identificadores SQLite) DEBERÁ
   preservarse; los identificadores públicos y la moneda se introducen de forma **aditiva**,
   adaptando las restricciones de unicidad según D-01/D-02 (una cuenta por `(tipo, moneda)` del
   cliente mock). _(D-02, DK-02; AC4-02, AC4-03)_
4. EN TODO MOMENTO el reset de fixture de la Etapa 4 DEBERÁ documentarse como **discontinuidad
   experimental** declarada (no una conversión COP→USD) y NO DEBERÁ modificar el estado ni la
   evidencia de la Etapa 3. _(D-02, DK-01; AC4-03, AC4-19)_
5. CUANDO la API lista las cuentas, ENTONCES DEBERÁ hacerlo en un orden determinista y estable.
   _(D-02; AC4-02)_

### Requisito 3 — Modelo monetario multidivisa exacto

**Historia de usuario:** Como responsable financiero, quiero aritmética monetaria exacta por
moneda, para que no haya pérdida de precisión ni floats financieros.

#### Criterios de aceptación

1. EN TODO MOMENTO el backend DEBERÁ representar los montos como `Decimal`/centavos enteros por
   moneda y el frontend como `BigInt`/unidades menores; el transporte en API DEBERÁ ser cadena
   decimal de **exactamente 2 decimales**. _(D-03; AC4-04)_
2. EN TODO MOMENTO el sistema NO DEBERÁ usar aritmética de punto flotante para dinero ni aplicar
   cargos/comisiones. _(D-03; AC4-04)_
3. CUANDO el sistema valida un monto de entrada, ENTONCES DEBERÁ rechazar valores no decimales,
   no finitos, negativos (donde no proceda) o con más de 2 decimales, con un error de dominio
   controlado. _(D-03; AC4-04)_
4. EN TODO MOMENTO cada monto expuesto o persistido DEBERÁ ir asociado inequívocamente a su
   moneda. _(D-01, D-03; AC4-01, AC4-04)_

## B. Conversión de divisas y transferencias (D-03, D-04)

### Requisito 4 — Conversión de divisas con tasas racionales exactas

**Historia de usuario:** Como titular, quiero convertir entre mis cuentas de distinta moneda con
una tasa clara y exacta, para saber cuánto recibo sin ambigüedad.

#### Criterios de aceptación

1. CUANDO el titular solicita una conversión vía `/api/conversions`, ENTONCES el sistema DEBERÁ
   usar **tasas racionales fijas** (sin servicio externo de tasas en vivo) y calcular el destino
   aplicando `ROUND_HALF_UP` **una sola vez al final**. _(D-03; AC4-05)_
2. CUANDO una conversión se completa, ENTONCES el sistema DEBERÁ exponer: la **tasa aplicada**, el
   **monto y moneda de origen**, el **monto y moneda de destino** y los **registros de
   transacción** resultantes. _(D-03; AC4-05)_
3. EN TODO MOMENTO una conversión DEBERÁ debitar la cuenta de origen y abonar la de destino de
   forma atómica, conservando el balance según las reglas de redondeo definidas (sin crear ni
   destruir valor fuera del redondeo documentado). _(D-03; AC4-05, AC4-06)_
4. SI una moneda de origen o destino no está soportada, o las cuentas no permiten la conversión
   solicitada, ENTONCES el sistema DEBERÁ rechazar la operación con un error controlado, sin
   mover saldos. _(D-01, D-03; AC4-05)_
5. EN TODO MOMENTO las reglas de precisión, redondeo y conservación de balance DEBERÁN aplicarse
   de forma **consistente y determinista** para la misma entrada. _(D-03; AC4-05, AC4-06)_

### Requisito 5 — Transferencias internas misma-moneda

**Historia de usuario:** Como titular, quiero transferir entre mis cuentas de la misma moneda,
para mover fondos sin un cambio de divisa implícito.

#### Criterios de aceptación

1. CUANDO el titular crea una transferencia interna, ENTONCES el sistema DEBERÁ permitirla **solo
   si origen y destino comparten la misma moneda**. _(D-04; AC4-07)_
2. SI una transferencia interna cruza monedas distintas, ENTONCES el sistema DEBERÁ rechazarla y
   DEBERÁ indicar que los cambios de divisa pasan exclusivamente por `/api/conversions`. _(D-04;
   AC4-07)_
3. EN TODO MOMENTO las transferencias internas DEBERÁN preservar la máquina de estados, la
   validación de fondos, el umbral de MFA y los límites heredados, ahora expresados en
   equivalente USD (ver Requisitos 9 y 10). _(D-04, D-07; AC4-07, AC4-01)_

## C. Event Sourcing y CQRS (D-05, D-06, D-09)

### Requisito 6 — Almacén de eventos de dominio durable y separado

**Historia de usuario:** Como responsable de integridad del dominio, quiero un almacén de eventos
durable que registre las transiciones de estado, para reconstruir el estado de las cuentas sin
confundirlo con la auditoría.

#### Criterios de aceptación

1. EN TODO MOMENTO el sistema DEBERÁ persistir los eventos de dominio en un almacén SQLite
   **append-only** dedicado, **separado** de la bitácora de auditoría HMAC heredada (`audit_log`).
   _(D-05; AC4-08)_
2. EN TODO MOMENTO cada evento de dominio DEBERÁ registrar al menos: tipo de evento, cuenta(s)
   afectada(s), la **versión** resultante por cuenta, moneda, monto en unidades menores,
   marca de tiempo UTC y los datos necesarios para reconstruir la transición. _(D-05, D-09;
   AC4-08, AC4-09)_
3. EN TODO MOMENTO el almacén de eventos NO DEBERÁ confundirse con, ni sustituirse por, la
   bitácora de auditoría; ambos coexisten con propósitos distintos. _(D-05; AC4-08)_
4. CUANDO la fixture inicial y las transferencias históricas sembradas se representan como
   eventos, ENTONCES el sistema DEBERÁ hacerlo **sin doble conteo** del saldo (migración que no
   duplica ni pierde valor). _(D-05, DK-01; AC4-08, AC4-14)_
5. EN TODO MOMENTO los eventos DEBERÁN definir **límites de evento** claros (qué transición de
   negocio representa cada evento) y ser inmutables una vez escritos. _(D-05; AC4-08)_

### Requisito 7 — Eventos compuestos y versionado por cuenta

**Historia de usuario:** Como responsable de integridad, quiero que las operaciones que afectan a
varias cuentas incrementen la versión de cada cuenta afectada una sola vez, para habilitar
concurrencia optimista fiable.

#### Criterios de aceptación

1. CUANDO una operación afecta a una o varias cuentas (transferencia, conversión, ACH,
   recurrente), ENTONCES el sistema DEBERÁ emitir un evento (posiblemente **compuesto**) que
   incremente la versión de **cada cuenta afectada en +1**, exactamente una vez por cuenta y
   operación. _(D-09; AC4-09)_
2. EN TODO MOMENTO una ACH DEBERÁ debitar en estado `pending`, liquidar (`settled`) **sin segundo
   débito** y, en caso de fallo, reembolsar con un **único** reembolso; los eventos
   correspondientes DEBERÁN reflejar esas transiciones sin aplicar efectos duplicados. _(D-09;
   AC4-09, AC4-11)_
3. EN TODO MOMENTO la versión de una cuenta DEBERÁ ser monótona creciente y derivable del número
   de eventos aplicados a esa cuenta. _(D-09, D-14; AC4-09, AC4-13)_

### Requisito 8 — Proyecciones CQRS y reconstrucción determinista

**Historia de usuario:** Como titular, quiero que mis lecturas de saldo e historial sean
consistentes con los comandos aplicados, para ver siempre un estado coherente.

#### Criterios de aceptación

1. EN TODO MOMENTO el sistema DEBERÁ separar el modelo/manejo de **comandos** (cambios de estado)
   del modelo/manejo de **consultas** (saldo e historial). _(D-06; AC4-10)_
2. CUANDO un comando emite eventos, ENTONCES el sistema DEBERÁ actualizar las **proyecciones de
   lectura** de forma **síncrona y atómica** con la persistencia de esos eventos (misma
   transacción `BEGIN IMMEDIATE`). _(D-06, D-11; AC4-10, AC4-12)_
3. CUANDO se solicita una reconstrucción, ENTONCES el sistema DEBERÁ **reconstruir las
   proyecciones de forma determinista** reaplicando los eventos desde el almacén, obteniendo el
   mismo estado. _(D-06; AC4-10, AC4-14)_
4. SI se detecta una inconsistencia entre eventos y proyección, ENTONCES el sistema DEBERÁ
   **fallar de forma cerrada** (rechazar la operación afectada) en lugar de servir un estado
   incoherente. _(D-06; AC4-10, AC4-12)_
5. EN TODO MOMENTO el comportamiento observable de las consultas DEBERÁ permanecer compatible con
   los flujos bancarios de la aplicación (formas de respuesta e invariantes heredados). _(D-06;
   AC4-10, AC4-01)_

## D. Idempotencia y concurrencia optimista (D-13, D-14)

### Requisito 9 — Idempotencia por `Idempotency-Key`

**Historia de usuario:** Como integrador, quiero reintentar operaciones de forma segura con una
clave de idempotencia, para no duplicar débitos ni créditos ante reintentos de red.

#### Criterios de aceptación

1. EN TODO MOMENTO las operaciones de transferencia interna, conversión FX y ACH DEBERÁN requerir
   un header `Idempotency-Key` con formato **UUID**; su ausencia o formato inválido DEBERÁ
   rechazarse con un error controlado. _(D-13; AC4-15)_
2. CUANDO se recibe un **replay exacto** (misma clave y mismo payload), ENTONCES el sistema DEBERÁ
   devolver el resultado original **sin aplicar nuevos efectos** (sin segundo débito/crédito, sin
   eventos nuevos). _(D-13; AC4-15, AC4-16)_
3. SI se reutiliza una `Idempotency-Key` con un **payload distinto**, ENTONCES el sistema DEBERÁ
   responder **409** (conflicto de idempotencia) sin aplicar efectos. _(D-13; AC4-15)_
4. EN TODO MOMENTO el registro de idempotencia DEBERÁ persistirse **atómicamente** con el efecto
   de la operación (misma transacción), de modo que no exista un efecto sin su registro ni un
   registro sin su efecto. _(D-11, D-13; AC4-15, AC4-12)_

### Requisito 10 — Concurrencia optimista por versión de cuenta

**Historia de usuario:** Como integrador, quiero declarar la versión de cuenta esperada, para que
una solicitud obsoleta no sobrescriba un cambio más reciente.

#### Criterios de aceptación

1. EN TODO MOMENTO las operaciones de cambio de estado DEBERÁN requerir la(s) **versión(es) de
   cuenta esperada(s)** para la(s) cuenta(s) afectada(s). _(D-14; AC4-13)_
2. SI la versión esperada no coincide con la versión actual de la cuenta, ENTONCES el sistema
   DEBERÁ responder **409 `ACCOUNT_VERSION_CONFLICT`** sin aplicar efectos. _(D-14; AC4-13)_
3. CUANDO una solicitud llega con `Idempotency-Key`, ENTONCES el sistema DEBERÁ evaluar el
   **replay idempotente ANTES** de la validación de versión de cuenta (un replay exacto no falla
   por versión). _(D-13, D-14; AC4-13, AC4-15)_
4. CUANDO una operación se aplica con éxito, ENTONCES la versión de cada cuenta afectada DEBERÁ
   incrementarse exactamente una vez, haciendo obsoleta cualquier solicitud concurrente que
   esperaba la versión anterior. _(D-09, D-14; AC4-09, AC4-13)_

## E. Límites, MFA y restricciones de divisa (D-07, D-08)

### Requisito 11 — Límites dinámicos y MFA en equivalente USD

**Historia de usuario:** Como titular, quiero que los límites y el umbral de MFA se midan en un
equivalente USD común, para que apliquen de forma coherente a cualquier moneda.

#### Criterios de aceptación

1. EN TODO MOMENTO el límite por operación DEBERÁ ser **USD 5,000.00 equivalente** y el límite
   diario acumulado **USD 10,000.00 equivalente** (día UTC), aplicados a internas, conversiones,
   ACH y recurrentes. _(D-07; AC4-17)_
2. CUANDO el equivalente USD **sin redondear** de una operación es **estrictamente mayor que
   USD 1,000.00**, ENTONCES el sistema DEBERÁ requerir MFA (código fijo `123456`, ventana 5 min,
   reintento sin lockout). _(D-07; AC4-17)_
3. EN TODO MOMENTO el cálculo del equivalente USD para límites/MFA DEBERÁ usar las mismas tasas
   racionales fijas, sin introducir floats, y la verificación autoritativa DEBERÁ ejecutarse
   **dentro** de la transacción financiera (sin TOCTOU). _(D-03, D-07; AC4-17, AC4-12)_
4. EN TODO MOMENTO el orden de comprobaciones DEBERÁ ser fondos → límites → (si aplica) MFA, y un
   PIN correcto NUNCA DEBERÁ saltar un límite o una comprobación de fondos. _(D-07; AC4-17,
   AC4-07)_

### Requisito 12 — Restricciones de divisa para ACH y recurrentes

**Historia de usuario:** Como titular, quiero reglas claras de moneda para ACH y pagos
recurrentes, para evitar operaciones cross-currency no soportadas.

#### Criterios de aceptación

1. EN TODO MOMENTO las transferencias ACH DEBERÁN originarse **solo desde una cuenta USD**. _(D-08;
   AC4-18)_
2. EN TODO MOMENTO los recurrentes **internos** DEBERÁN permanecer en la **misma moneda** (origen
   y destino). _(D-08; AC4-18)_
3. EN TODO MOMENTO los recurrentes **ACH** DEBERÁN ser **solo USD**. _(D-08; AC4-18)_
4. SI una solicitud ACH o recurrente viola estas restricciones de moneda, ENTONCES el sistema
   DEBERÁ rechazarla con un error controlado, sin mover saldos ni crear schedules. _(D-08;
   AC4-18)_
5. EN TODO MOMENTO el ciclo de vida ACH (débito en `pending`, settlement sin doble débito, un
   único reembolso) y la ejecución recurrente idempotente (único scheduler) DEBERÁN preservarse
   bajo el modelo multidivisa. _(D-08, D-09; AC4-11, AC4-18)_

## F. Seguridad, auditoría y atomicidad (D-11)

### Requisito 13 — Preservación de cifrado, auditoría y atomicidad compuesta

**Historia de usuario:** Como responsable de seguridad, quiero que el cifrado y la auditoría
sigan válidos y que evento, proyección, auditoría, idempotencia y versión se confirmen juntos,
para no dejar estados parciales.

#### Criterios de aceptación

1. EN TODO MOMENTO el sistema DEBERÁ preservar el cifrado AES-256-GCM en reposo de los
   identificadores sensibles y la auditoría append-only encadenada con HMAC (+ ancla de cola),
   verificables por recomputación. _(D-11; AC4-12, AC4-20)_
2. CUANDO un comando se confirma, ENTONCES el sistema DEBERÁ aplicar de forma **atómica** en la
   misma transacción `BEGIN IMMEDIATE`: evento(s) de dominio, actualización de proyección(es),
   entrada de auditoría, registro de idempotencia y actualización de versión de cuenta. _(D-11,
   D-06, D-13, D-14; AC4-12)_
3. SI cualquiera de esos efectos falla al persistir, ENTONCES el sistema DEBERÁ revertir todo el
   conjunto (fail-closed), sin aplicar un subconjunto parcial. _(D-11; AC4-12)_
4. EN TODO MOMENTO los fallos DEBERÁN ser **auditables** y las entradas de auditoría NO DEBERÁN
   contener identificadores sensibles en texto plano ni material de clave. _(D-11; AC4-12,
   AC4-20)_
5. EN TODO MOMENTO el sistema DEBERÁ prevenir dobles débitos, dobles créditos, aplicación
   duplicada de eventos y saldos inconsistentes. _(D-09, D-11, D-13; AC4-09, AC4-12, AC4-15)_

## G. Frontend multidivisa (D-10)

### Requisito 14 — Dashboard y formateo de moneda

**Historia de usuario:** Como titular, quiero ver mis saldos por moneda con formato claro, para
entender mi posición sin confundir divisas.

#### Criterios de aceptación

1. EN TODO MOMENTO el dashboard DEBERÁ mostrar los totales **separados por moneda**, sin sumar
   monedas distintas en un único total. _(D-10; AC4-19)_
2. CUANDO se muestra un total estimado en USD, ENTONCES DEBERÁ etiquetarse como **solo para
   visualización** (estimado, no autoritativo). _(D-10; AC4-19)_
3. EN TODO MOMENTO el frontend DEBERÁ representar los montos como cadena/`BigInt` (nunca `number`)
   y formatearlos con su moneda y 2 decimales. _(D-03, D-10; AC4-04, AC4-19)_
4. CUANDO se muestran historial y detalles de conversión, ENTONCES el frontend DEBERÁ mostrar la
   moneda de cada monto y, en conversiones, la tasa aplicada, origen y destino. _(D-03, D-10;
   AC4-05, AC4-19)_
5. EN TODO MOMENTO el frontend DEBERÁ preservar los flujos heredados (transferencias internas,
   ACH, recurrentes, límites, MFA) de forma aditiva y compatible. _(D-10; AC4-19, AC4-01)_

## H. Migración, regresión, carga y despliegue (D-05, D-12)

### Requisito 15 — Migración de esquema y fixture controlada

**Historia de usuario:** Como operador, quiero que la evolución de esquema y la fixture de la
Etapa 4 sean aditivas, idempotentes, transaccionales y reversibles, para no corromper datos ni la
auditoría heredada.

#### Criterios de aceptación

1. CUANDO el backend arranca, ENTONCES el sistema DEBERÁ aplicar una migración de esquema
   **aditiva, idempotente y transaccional** que añada moneda, identificadores públicos, el
   almacén de eventos, las proyecciones y las tablas de idempotencia/versión, sin eliminar
   tablas/columnas heredadas. _(D-05, D-12, DK-03; AC4-14)_
2. SI la migración falla a mitad de camino, ENTONCES el sistema DEBERÁ revertir por completo
   (rollback transaccional), dejando intacta la fixture previa y la cadena de auditoría. _(D-05,
   D-12; AC4-14)_
3. CUANDO se inicializa la fixture experimental de la Etapa 4, ENTONCES el sistema DEBERÁ sembrar
   las cuentas D-02 y representar el estado inicial e históricas como eventos **sin doble
   conteo**, verificable por reconstrucción determinista. _(D-02, D-05, DK-01; AC4-03, AC4-08,
   AC4-14)_
4. EN TODO MOMENTO la verificación de migración y rollback DEBERÁ basarse en propiedades
   estructurales (idempotencia, atomicidad, reconstrucción determinista, ausencia de doble
   conteo), **sin** afirmar equivalencia de valor COP↔USD. _(D-05, DK-01; AC4-14, AC4-19)_
5. EN TODO MOMENTO el estado y la evidencia de la Etapa 3 DEBERÁN permanecer sin modificación.
   _(DK-01; AC4-19)_

### Requisito 16 — Regresión, carga y despliegue preservados

**Historia de usuario:** Como ingeniero, quiero que las capacidades heredadas sigan verdes y que
la carga y el despliegue sigan siendo válidos, para no introducir regresiones.

#### Criterios de aceptación

1. EN TODO MOMENTO el sistema DEBERÁ preservar FastAPI, React, SQLite y la capacidad de
   despliegue Docker Compose/Nginx/TLS; NO DEBERÁ reclamar despliegue verificado sin observarlo.
   _(D-12; AC4-20)_
2. CUANDO se ejecuta la regresión completa, ENTONCES el sistema DEBERÁ ejecutar la suite backend
   (Pytest), las pruebas frontend (Vitest) y el build de producción, preservando la evidencia
   cruda. NO DEBERÁ afirmarse que pruebas preexistentes pasan sin haber observado su resultado.
   _(D-12; AC4-20)_
3. CUANDO se ejecuta la carga, ENTONCES el sistema DEBERÁ reutilizar el arnés Locust heredado con
   DB sintética aislada, verificando invariantes financieros post-carga bajo el modelo
   multidivisa, y preservando resultados legibles por máquina. _(D-12; AC4-20)_
4. CUANDO se ejecutan análisis de calidad, ENTONCES los escaneos SonarQube PRE y POST DEBERÁN ser
   **controlados por el investigador** (gates), comparables 1:1, y una verificación sin servicio
   disponible o sin evidencia NO DEBERÁ marcarse como aprobada. _(D-12; AC4-20)_

---

## Parte II — Requisitos no funcionales (NFR)

### Requisito 17 — Seguridad

1. EN TODO MOMENTO el sistema DEBERÁ preservar cifrado AEAD en reposo y TLS en tránsito, sin
   algoritmos caseros, y fallar de forma cerrada ante claves ausentes/inválidas. _(D-11, D-12;
   AC4-12, AC4-20)_
2. EN TODO MOMENTO el sistema NO DEBERÁ registrar secretos, material de clave, texto cifrado crudo
   ni identificadores sensibles en claro en logs, respuestas o errores. _(D-11; AC4-12)_
3. EN TODO MOMENTO la API NO DEBERÁ exponer identificadores internos (UUID); usará los
   identificadores públicos de cuenta y el enmascarado de beneficiarios heredado. _(D-02, D-11;
   AC4-02, AC4-12)_

### Requisito 18 — Exactitud y determinismo monetario

1. EN TODO MOMENTO los cálculos monetarios y de conversión DEBERÁN ser **deterministas y exactos**
   para la misma entrada (tasas racionales, `ROUND_HALF_UP` una vez), sin floats financieros.
   _(D-03; AC4-04, AC4-05)_
2. EN TODO MOMENTO la conservación de balance DEBERÁ sostenerse según las reglas de redondeo
   documentadas, sin crear ni destruir valor fuera de ellas. _(D-03; AC4-06)_

### Requisito 19 — Confiabilidad y concurrencia

1. EN TODO MOMENTO el sistema DEBERÁ mantener la corrección financiera, la consistencia de
   proyecciones y la verificabilidad de la auditoría bajo concurrencia dentro del modelo
   lector/escritor de SQLite (único escritor; múltiples lectores). _(D-06, D-09, D-11; AC4-09,
   AC4-12)_
2. EN TODO MOMENTO la idempotencia y la concurrencia optimista DEBERÁN prevenir dobles
   efectos y la aplicación duplicada de eventos ante reintentos y solicitudes concurrentes.
   _(D-13, D-14; AC4-15, AC4-13)_
3. EN TODO MOMENTO el despliegue DEBERÁ garantizar exactamente **un** scheduler de recurrentes,
   preservando exactamente-una-vez. _(D-08, D-12; AC4-11, AC4-18)_

### Requisito 20 — Mantenibilidad y alcance de dependencias

1. EN TODO MOMENTO las nuevas capacidades DEBERÁN seguir el estilo por capas heredado (routers →
   service → repository → `sqlite3`, sin ORM, config por constantes/`DB_PATH`) y reutilizar las
   utilidades heredadas (`money`, `txn.financial_transaction`, `audit`, `crypto`, scheduler)
   siempre que sea posible. _(D-12, DK-03, DK-05; AC4-20)_
2. EN TODO MOMENTO el sistema NO DEBERÁ introducir una base de datos, broker de mensajes, vendor
   cloud, API de FX ni biblioteca de event-store externa no aprobada por el investigador. _(SEED-4
   §Decisiones; AC4-20)_
3. EN TODO MOMENTO Locust DEBERÁ permanecer como dependencia **solo de pruebas/dev**. _(D-12;
   AC4-20)_

---

## Glossary

## Glosario

### Decisiones comunes de la Etapa 4 (guía de replicación) — D-01 .. D-14

- **D-01:** Una moneda fija por cuenta (USD, EUR o GBP); no mezclar saldos heterogéneos.
- **D-02:** Preservar CHK-1001 (USD 2,500.00) y SAV-2001 (USD 10,000.00); añadir EUR-3001 y
  GBP-4001 con saldo 0.00.
- **D-03:** Backend `Decimal`, frontend `BigInt`/centavos, cadenas de dos decimales; tasas
  racionales fijas; `ROUND_HALF_UP` una sola vez al final; sin cargos ni floats financieros.
- **D-04:** Transferencias internas solo misma moneda; los cambios entre divisas pasan
  exclusivamente por `/api/conversions`.
- **D-05:** SQLite append-only para eventos de dominio, separado de la auditoría histórica;
  migración sin doble conteo.
- **D-06:** Proyecciones CQRS síncronas y atómicas con eventos; reconstrucción determinista;
  fail-closed ante inconsistencia.
- **D-07:** Límite USD equivalente por operación 5,000.00 y diario 10,000.00; MFA si equivalente
  USD sin redondear > 1,000.00.
- **D-08:** ACH solo desde USD; recurrentes internos misma moneda; recurrentes ACH solo USD.
- **D-09:** Eventos compuestos con versiones +1 por cuenta afectada; ACH débito en `pending`,
  settlement sin doble débito, fracaso con un único reembolso.
- **D-10:** Dashboard con totales separados por moneda; USD estimado solo para visualización.
- **D-11:** Cifrado AES-GCM, auditoría encadenada HMAC y atomicidad
  evento–proyección–auditoría–idempotencia; fallos auditables.
- **D-12:** Conservar FastAPI, React, SQLite y capacidad de despliegue Compose/Nginx/TLS; no
  inventar despliegue verificado.
- **D-13:** `Idempotency-Key` UUID obligatorio para transferencias internas/FX/ACH; replay exacto
  sin nuevos efectos; reuse con payload distinto → 409.
- **D-14:** Versiones de cuenta esperadas obligatorias; solicitudes obsoletas → 409
  `ACCOUNT_VERSION_CONFLICT`; replay idempotente precede a validación de versión.

### Decisiones de diseño aprobadas para esta ejecución de Kiro — DK-01 .. DK-05

- **DK-01 — Reset experimental de fixture.** Fixture inicial de la Etapa 4 con los saldos D-02
  (CHK-1001 USD 2,500.00; SAV-2001 USD 10,000.00; EUR-3001 EUR 0.00; GBP-4001 GBP 0.00). NO es
  conversión COP→USD; discontinuidad experimental declarada; la Etapa 3 (COP) y su evidencia se
  preservan sin modificación.
- **DK-02 — Identidad de cuenta.** Preservar los identificadores internos SQLite heredados e
  introducir identificadores públicos **inmutables** y campos de **moneda** explícitos; adaptar
  las restricciones de unicidad y las APIs según D-01/D-02.
- **DK-03 — Modelo transaccional.** Preservar `BEGIN IMMEDIATE` (`txn.financial_transaction`),
  haciendo atómicos evento(s), proyección(es), auditoría, idempotencia y versión de cuenta donde
  se requiera.
- **DK-04 — Orden de validación.** El replay idempotente se comprueba **antes** de la validación
  de versión de cuenta (D-13/D-14).
- **DK-05 — Preservación de invariantes.** Preservar todas las salvaguardas de seguridad y
  bancarias heredadas (fondos, MFA, límites, estados, ACH exactamente-una-vez, recurrentes,
  cifrado, auditoría) bajo el modelo multidivisa.

### Matriz de aceptación externa (resumen de referencia)

- **AC4-01** Identidad de moneda y no-mezcla · **AC4-02** Identificadores públicos/sin internos ·
  **AC4-03** Fixture D-02 y discontinuidad · **AC4-04** Modelo monetario exacto · **AC4-05**
  Conversión y datos expuestos · **AC4-06** Conservación de balance/redondeo · **AC4-07** Internas
  misma-moneda · **AC4-08** Almacén de eventos separado · **AC4-09** Eventos compuestos/versión ·
  **AC4-10** CQRS/proyecciones · **AC4-11** ACH exactamente-una-vez · **AC4-12** Atomicidad
  compuesta/fail-closed · **AC4-13** Concurrencia optimista 409 · **AC4-14** Migración/rebuild sin
  doble conteo · **AC4-15** Idempotencia replay/409 · **AC4-16** Replay sin nuevos efectos ·
  **AC4-17** Límites/MFA en equivalente USD · **AC4-18** Restricciones de divisa ACH/recurrentes ·
  **AC4-19** Dashboard multidivisa y evidencia de discontinuidad · **AC4-20** Regresión/carga/
  despliegue/SonarQube controlados.
