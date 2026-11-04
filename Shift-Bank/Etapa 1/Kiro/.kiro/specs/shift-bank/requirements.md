# Requisitos — Shift Bank (Etapa 1)

## Introducción

Shift Bank (Etapa 1) es una aplicación bancaria de alcance acotado que representa a un
único cliente autenticado de forma simulada (mock). El cliente posee exactamente dos
cuentas propias —Checking y Savings— y la única operación financiera soportada es la
transferencia de dinero entre esas dos cuentas propias.

El sistema aplica reglas de validación sobre los montos y los saldos, incorpora un flujo
de autenticación multifactor (MFA) simulada para transferencias sensibles (montos iguales
o superiores a COP 1,000,000) y mantiene un historial de transferencias que incluye dos
registros históricos pre-sembrados que no deben re-aplicarse a los saldos iniciales.

Alcance técnico de la etapa: backend en Python con FastAPI; persistencia en SQLite usando
el módulo `sqlite3` incorporado (sin ORM); cálculos monetarios con `Decimal` y valores de
API como cadenas decimales (decimal-string); frontend en React con TypeScript y CSS puro
(Vanilla CSS). No se requiere ningún servicio externo de autenticación ni de MFA. Toda la
funcionalidad fuera de este documento queda explícitamente fuera de alcance para la Etapa 1.

### Términos y convenciones

- **Moneda:** todos los montos están expresados en pesos colombianos (COP).
- **Decimal-string:** los montos monetarios se transportan en la API como cadenas de texto
  que representan un valor decimal exacto (p. ej. `"1000000.00"`), y se operan internamente
  con `Decimal` para evitar errores de punto flotante.
- **Cuentas:** el sistema expone únicamente los nombres amigables `Checking` y `Savings`.
- **Transferencia sensible:** transferencia cuyo monto es mayor o igual a COP 1,000,000.
- **Estados de una transferencia:** `PENDING_MFA`, `COMPLETED`, `FAILED`, `EXPIRED`.
  Las transferencias por debajo del umbral de MFA se crean directamente como `COMPLETED`.

---

## Requisitos

### Requisito 1 — Cliente autenticado y cuentas pre-sembradas

**Historia de usuario:** Como cliente autenticado de Shift Bank, quiero ingresar a una sesión
que ya reconoce mis dos cuentas con sus saldos iniciales, para poder operar de inmediato sin
registrarme ni configurar cuentas.

#### Criterios de aceptación

1. CUANDO la aplicación inicia, ENTONCES el sistema DEBERÁ representar exactamente un cliente
   autenticado de forma simulada (mock), sin requerir un flujo de inicio de sesión real ni un
   servicio de autenticación externo.
2. CUANDO el estado inicial se siembra, ENTONCES el sistema DEBERÁ crear exactamente dos
   cuentas pertenecientes al cliente: una cuenta Checking y una cuenta Savings.
3. CUANDO las cuentas se siembran, ENTONCES el sistema DEBERÁ establecer el saldo inicial de
   Checking en COP 5,000,000 y el saldo inicial de Savings en COP 15,000,000.
4. CUANDO se calcula el saldo inicial de las cuentas, ENTONCES el sistema NO DEBERÁ aplicar
   las transferencias históricas pre-sembradas sobre esos saldos iniciales (los saldos
   iniciales ya son los saldos de partida definitivos).
5. EN TODO MOMENTO el sistema DEBERÁ restringir todas las operaciones a este único cliente y
   a sus dos cuentas propias.

### Requisito 2 — Presentación de cuentas con nombres amigables

**Historia de usuario:** Como cliente, quiero ver mis cuentas identificadas solo por nombres
claros (Checking y Savings), para no exponerme a identificadores técnicos innecesarios.

#### Criterios de aceptación

1. CUANDO la interfaz muestra una cuenta, ENTONCES el sistema DEBERÁ mostrar únicamente el
   nombre amigable `Checking` o `Savings`.
2. CUANDO la interfaz muestra cualquier información de cuentas o de transferencias, ENTONCES
   el sistema NO DEBERÁ exponer números de cuenta, UUID, identificadores de base de datos ni
   ningún otro identificador interno.
3. CUANDO el frontend necesita referirse a una cuenta para una operación, ENTONCES el sistema
   DEBERÁ hacerlo mediante un identificador de cuenta que no se muestre al usuario, de modo
   que la capa de presentación solo exhiba el nombre amigable.

### Requisito 3 — Transferencia entre cuentas propias

**Historia de usuario:** Como cliente, quiero mover dinero entre mi cuenta Checking y mi
cuenta Savings, para administrar mis fondos entre mis propias cuentas.

#### Criterios de aceptación

1. CUANDO el cliente solicita una transferencia, ENTONCES el sistema DEBERÁ permitir
   únicamente transferencias entre la cuenta Checking y la cuenta Savings del propio cliente.
2. CUANDO el cliente intenta transferir hacia la misma cuenta de origen, ENTONCES el sistema
   DEBERÁ rechazar la transferencia.
3. CUANDO el cliente especifica un monto menor o igual a cero, ENTONCES el sistema DEBERÁ
   rechazar la transferencia.
4. CUANDO el cliente solicita una transferencia cuyo monto supera el saldo disponible de la
   cuenta de origen, ENTONCES el sistema DEBERÁ rechazar la transferencia por fondos
   insuficientes.
5. CUANDO el sistema procesa cualquier monto monetario, ENTONCES el sistema DEBERÁ usar
   manejo seguro con `Decimal` y transportar los valores de la API como cadenas decimales
   (decimal-string), evitando aritmética de punto flotante.
6. EN TODO MOMENTO el sistema NO DEBERÁ ofrecer depósitos, retiros, consignaciones de nómina,
   compras, pagos con tarjeta ni ningún otro tipo de transacción distinto de la transferencia
   entre las dos cuentas propias.

### Requisito 4 — Transferencias históricas pre-sembradas

**Historia de usuario:** Como cliente, quiero ver desde el inicio un historial con mis
transferencias previas, para tener contexto de mi actividad reciente.

#### Criterios de aceptación

1. CUANDO el estado inicial se siembra, ENTONCES el sistema DEBERÁ crear exactamente dos
   transferencias históricas completadas.
2. CUANDO se siembran las transferencias históricas, ENTONCES el sistema DEBERÁ registrar una
   transferencia de COP 500,000 de Savings a Checking.
3. CUANDO se siembran las transferencias históricas, ENTONCES el sistema DEBERÁ registrar una
   transferencia de COP 100,000 de Checking a Savings.
4. CUANDO se registran las transferencias históricas, ENTONCES el sistema DEBERÁ tratarlas
   como registros históricos (ya completados) y NO DEBERÁ volver a aplicarlas sobre los saldos
   de partida definidos en el Requisito 1.

### Requisito 5 — Historial de transferencias

**Historia de usuario:** Como cliente, quiero consultar el historial de mis transferencias,
para revisar fecha, dirección, monto y descripción de cada movimiento.

#### Criterios de aceptación

1. CUANDO el cliente consulta el historial, ENTONCES el sistema DEBERÁ mostrar, por cada
   transferencia, la fecha, la dirección (cuenta de origen hacia cuenta de destino), el monto
   y la descripción.
2. CUANDO el sistema muestra el historial, ENTONCES el sistema NO DEBERÁ estar obligado a
   mostrar el saldo resultante de cada movimiento.
3. CUANDO el sistema muestra la dirección y el monto de una transferencia, ENTONCES el sistema
   DEBERÁ respetar la regla de nombres amigables del Requisito 2 (sin exponer identificadores
   internos) y presentar el monto como cadena decimal exacta.

### Requisito 6 — Umbral de MFA para transferencias sensibles

**Historia de usuario:** Como cliente, quiero que las transferencias de bajo monto se ejecuten
de inmediato y que las de alto monto exijan una verificación adicional, para equilibrar
comodidad y seguridad.

#### Criterios de aceptación

1. CUANDO el cliente solicita una transferencia por un monto menor a COP 1,000,000 que supera
   las validaciones del Requisito 3, ENTONCES el sistema DEBERÁ ejecutarla normalmente sin
   requerir MFA, dejándola en estado `COMPLETED`.
2. CUANDO el cliente solicita una transferencia por un monto mayor o igual a COP 1,000,000,
   ENTONCES el sistema DEBERÁ requerir autenticación multifactor (MFA) simulada antes de
   ejecutarla.
3. CUANDO una transferencia sensible requiere MFA, ENTONCES el sistema DEBERÁ crearla en
   estado `PENDING_MFA` antes de ejecutarla.
4. CUANDO una transferencia está en estado `PENDING_MFA`, ENTONCES el sistema NO DEBERÁ
   modificar los saldos de ninguna cuenta mientras la transferencia siga pendiente.

### Requisito 7 — Confirmación y verificación de MFA

**Historia de usuario:** Como cliente, quiero confirmar una transferencia sensible con un
código MFA, para autorizar explícitamente los movimientos de alto monto.

#### Criterios de aceptación

1. EN TODO MOMENTO el código MFA válido DEBERÁ ser `123456` (código simulado fijo), sin
   depender de ningún servicio externo de MFA.
2. CUANDO el cliente envía un código MFA incorrecto para una transferencia en `PENDING_MFA`,
   ENTONCES el sistema DEBERÁ mantener la transferencia en `PENDING_MFA` y permitir reintentar
   la confirmación.
3. CUANDO el cliente envía el código MFA correcto para una transferencia en `PENDING_MFA` que
   aún es válida y cuyo origen tiene fondos suficientes, ENTONCES el sistema DEBERÁ cambiar la
   transferencia a estado `COMPLETED`.
4. CUANDO una transferencia pasa a `COMPLETED` por confirmación de MFA, ENTONCES el sistema
   DEBERÁ actualizar los saldos de ambas cuentas de forma atómica (ambos cambios se aplican
   por completo o no se aplica ninguno).
5. EN TODO MOMENTO el sistema NO DEBERÁ implementar ningún mecanismo de bloqueo (lockout) por
   intentos fallidos de MFA.

### Requisito 8 — Expiración y fallo de transferencias pendientes de MFA

**Historia de usuario:** Como cliente, quiero que una solicitud de MFA deje de ser válida tras
un tiempo o si mis fondos cambian, para que no se ejecuten transferencias desactualizadas.

#### Criterios de aceptación

1. CUANDO una transferencia entra en `PENDING_MFA`, ENTONCES el sistema DEBERÁ establecer una
   ventana de validez de cinco (5) minutos para completarla.
2. CUANDO transcurren más de cinco minutos desde que la transferencia entró en `PENDING_MFA`
   sin una confirmación exitosa, ENTONCES el sistema DEBERÁ marcar la transferencia como
   `EXPIRED`.
3. CUANDO una transferencia está en estado `EXPIRED`, ENTONCES el sistema NO DEBERÁ permitir
   completarla, incluso si se envía el código MFA correcto.
4. CUANDO el cliente envía el código MFA correcto para una transferencia en `PENDING_MFA`
   pero el saldo de la cuenta de origen ya es insuficiente para el monto, ENTONCES el sistema
   DEBERÁ fallar la confirmación y marcar la transferencia como `FAILED`.
5. CUANDO una transferencia pasa a `EXPIRED` o `FAILED`, ENTONCES el sistema NO DEBERÁ
   modificar los saldos de ninguna cuenta.

### Requisito 9 — Alcance técnico de la Etapa 1

**Historia de usuario:** Como responsable del proyecto, quiero que la implementación se ciña a
un conjunto técnico definido, para mantener el alcance de la Etapa 1 bajo control.

#### Criterios de aceptación

1. CUANDO se implementa el backend, ENTONCES el sistema DEBERÁ usar Python con FastAPI.
2. CUANDO se implementa la persistencia, ENTONCES el sistema DEBERÁ usar SQLite a través del
   módulo `sqlite3` incorporado de Python, sin usar un ORM.
3. CUANDO se implementa el frontend, ENTONCES el sistema DEBERÁ usar React con TypeScript.
4. CUANDO se aplican estilos al frontend, ENTONCES el sistema DEBERÁ usar CSS puro (Vanilla
   CSS) y NO DEBERÁ depender de un framework de CSS.
5. EN TODO MOMENTO la implementación DEBERÁ limitarse al alcance de la Etapa 1 descrito en
   este documento, sin añadir funcionalidades fuera de él.
