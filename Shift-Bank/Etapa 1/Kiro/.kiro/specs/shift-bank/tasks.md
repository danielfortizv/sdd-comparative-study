# Plan de implementación — Shift Bank (Etapa 1)

> Cada tarea deriva directamente de un requisito aprobado o es trabajo de implementación
> necesario para cumplirlo. Las referencias `_Requisitos: X.Y_` apuntan a los criterios de
> aceptación del artefacto de requisitos. No se añaden funcionalidades, tecnologías ni
> decisiones fuera de lo aprobado. Las tareas son incrementales y se enfocan solo en código
> (sin pasos operativos manuales).

## Backend — base y utilidades

- [ ] 1. Inicializar el proyecto backend (FastAPI + sqlite3) y la configuración
  - Crear `backend/requirements.txt` con FastAPI, Uvicorn y Pydantic (sin ORM).
  - Crear `backend/app/config.py` con constantes: ruta de la DB, umbral de MFA
    (COP 1,000,000), código MFA fijo (`123456`) y TTL de MFA (5 minutos).
  - Crear el paquete `backend/app/` con los módulos vacíos previstos en el diseño.
  - _Requisitos: 7.1, 9.1, 9.2, 9.5_

- [ ] 2. Implementar utilidades monetarias decimal-safe (`money.py`)
  - `cents_to_decimal`, `decimal_to_cents` (centavos enteros ↔ `Decimal`, 2 decimales,
    `ROUND_HALF_UP`).
  - `parse_amount` (string → `Decimal`, rechaza no numérico y >2 decimales) y
    `format_amount` (`Decimal` → cadena decimal canónica con 2 decimales).
  - _Requisitos: 3.5_

- [ ] 3. Implementar la capa de base de datos (`db.py`) y el esquema SQLite
  - Abrir la conexión `sqlite3` con `check_same_thread=False` y PRAGMAs de integridad
    (claves foráneas activadas).
  - Crear el esquema de las tablas `customer`, `account` y `transfer` tal como se define en
    el diseño (montos como `INTEGER` de centavos; fechas ISO-8601 UTC).
  - _Requisitos: 9.2_

## Backend — siembra de estado inicial

- [ ] 4. Implementar la siembra de cliente y cuentas (`seed.py`)
  - Insertar exactamente un cliente mock y exactamente dos cuentas (`checking`, `savings`)
    con `display_name` `Checking`/`Savings`.
  - Fijar los saldos iniciales directamente: Checking = 5,000,000.00; Savings = 15,000,000.00
    (en centavos).
  - Hacer la siembra idempotente (no re-sembrar si ya existe el estado).
  - _Requisitos: 1.1, 1.2, 1.3, 1.5_

- [ ] 5. Sembrar las dos transferencias históricas como registros (sin aplicar saldos)
  - Insertar dos filas `COMPLETED`, `requires_mfa=0`, `expires_at=NULL`: 500,000 Savings→Checking
    y 100,000 Checking→Savings, con `created_at` en el pasado y descripción.
  - Garantizar explícitamente que la siembra NO modifica los saldos fijados en la tarea 4
    (los históricos son datos independientes, no derivan saldos).
  - _Requisitos: 4.1, 4.2, 4.3, 4.4, 1.4_

## Backend — acceso a datos

- [ ] 6. Implementar el repositorio de cuentas (`repository.py`)
  - Consultar las dos cuentas por `kind`, devolviendo `display_name` y `balance_cents`.
  - Consultar una cuenta por `kind` para validaciones de fondos.
  - _Requisitos: 1.5, 2.3_

- [ ] 7. Implementar el repositorio de transferencias y la aplicación atómica de saldos
  - Crear transferencia (con estado inicial, `requires_mfa`, `created_at`, `expires_at`).
  - Leer transferencia por su `reference` opaco; listar el historial ordenado por fecha desc.
  - Actualizar estado de la transferencia (`COMPLETED`/`FAILED`/`EXPIRED`).
  - Implementar `apply_transfer` que, dentro de una única transacción SQLite
    (`BEGIN IMMEDIATE … COMMIT`), descuente del origen y abone al destino de forma atómica.
  - _Requisitos: 7.4, 5.1_

## Backend — reglas de negocio (service)

- [ ] 8. Implementar validaciones de creación de transferencia (`service.py`)
  - Rechazar misma cuenta (`SAME_ACCOUNT`), monto ≤ 0 (`NON_POSITIVE_AMOUNT`) y monto
    inválido/formato (`INVALID_AMOUNT`).
  - Rechazar fondos insuficientes al crear (`INSUFFICIENT_FUNDS`), comparando en centavos.
  - Restringir las operaciones a las dos cuentas propias (`checking`/`savings`).
  - _Requisitos: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

- [ ] 9. Implementar la decisión de umbral de MFA y la creación según el caso
  - Si `amount < 1,000,000`: aplicar saldos atómicamente y crear la transferencia como
    `COMPLETED` (ejecución inmediata).
  - Si `amount ≥ 1,000,000`: crear la transferencia en `PENDING_MFA` con `expires_at = now + 5min`,
    emitir un `reference` opaco y NO modificar saldos.
  - _Requisitos: 6.1, 6.2, 6.3, 6.4_

- [ ] 10. Implementar expiración perezosa de transferencias pendientes
  - Al leer o confirmar una transferencia en `PENDING_MFA`, si `now > expires_at`, marcarla
    `EXPIRED` y persistir; tratar `EXPIRED` como terminal.
  - _Requisitos: 8.1, 8.2, 8.3_

- [ ] 11. Implementar la confirmación de MFA y las transiciones de estado
  - Validar el código contra el valor fijo `123456`.
  - Código incorrecto (y aún válida) → permanece `PENDING_MFA`, permite reintento, sin lockout.
  - Expirada → `EXPIRED`, no completa.
  - Código correcto pero fondos ya insuficientes → `FAILED`, sin cambios de saldo.
  - Código correcto, válida y con fondos → aplicar saldos atómicamente y marcar `COMPLETED`.
  - _Requisitos: 7.1, 7.2, 7.3, 7.4, 7.5, 8.4, 8.5_

## Backend — esquemas y API

- [ ] 12. Definir los esquemas Pydantic de request/response (`schemas.py`)
  - Modelos con montos como cadenas decimales (decimal-string) para entrada y salida.
  - Respuestas de cuentas e historial que exponen solo nombres amigables (sin IDs internos).
  - Forma de error consistente `{ error: { code, message } }`.
  - _Requisitos: 2.1, 2.2, 3.5, 5.3_

- [ ] 13. Implementar el router de cuentas (`routers/accounts.py`)
  - `GET /api/accounts` que devuelve las dos cuentas con `name` amigable y `balance`
    (decimal-string), sin identificadores internos.
  - _Requisitos: 2.1, 2.2, 1.5_

- [ ] 14. Implementar el router de transferencias (`routers/transfers.py`)
  - `POST /api/transfers`: crea la transferencia referenciando cuentas por `checking`/`savings`;
    responde `201` con `COMPLETED` o `PENDING_MFA` (+`reference`, +`expires_at`) según el umbral,
    tal como fija el contrato de API del diseño.
  - `POST /api/transfers/{reference}/mfa`: confirma con el código; mapea los estados a HTTP
    (incorrecto 401, expirado/fondos/estado terminal 409, éxito 200).
  - `GET /api/transfers`: historial con fecha, dirección (nombres amigables), monto y
    descripción; sin saldo resultante ni identificadores internos.
  - Mapear las excepciones de dominio a los códigos HTTP de la tabla del diseño.
  - _Requisitos: 2.2, 3.1, 5.1, 5.2, 5.3, 6.1, 6.2, 6.3, 7.3, 8.3, 8.4_

- [ ] 15. Ensamblar la aplicación FastAPI (`main.py`)
  - Crear la app, registrar routers, habilitar CORS para el frontend y ejecutar la siembra
    en el arranque (idempotente).
  - _Requisitos: 9.1, 1.1_

## Frontend — base y cliente de API

- [ ] 16. Inicializar el proyecto frontend (React + TypeScript, Vanilla CSS)
  - Crear el scaffold con React + TypeScript (Vite), `index.html`, `tsconfig.json`,
    `package.json` y la entrada `main.tsx`/`App.tsx`.
  - Configurar estilos con CSS puro (sin framework de CSS).
  - _Requisitos: 9.3, 9.4_

- [ ] 17. Implementar el cliente de API y los tipos (`api/client.ts`, `types.ts`)
  - Funciones `getAccounts`, `createTransfer`, `confirmMfa`, `getHistory`, enviando y
    recibiendo montos como `string` (decimal-string, nunca `number`).
  - Normalizar los errores `{ error: { code, message } }` a mensajes legibles.
  - _Requisitos: 2.2, 3.5_

## Frontend — componentes de UI

- [ ] 18. Implementar el panel de cuentas (`AccountsPanel.tsx`)
  - Mostrar las dos cuentas usando solo `Checking`/`Savings` y su saldo formateado; no mostrar
    ningún identificador interno.
  - _Requisitos: 2.1, 2.2_

- [ ] 19. Implementar el formulario de transferencia (`TransferForm.tsx`)
  - Selección de origen/destino (Checking/Savings), monto y descripción; evitar en la UI que
    destino = origen (la validación autoritativa es del backend).
  - Enviar la creación y, si la respuesta es `PENDING_MFA`, abrir el diálogo de MFA.
  - _Requisitos: 3.1, 3.2, 6.1, 6.2_

- [ ] 20. Implementar el diálogo de MFA (`MfaDialog.tsx`)
  - Pedir el código, mostrar un contador hacia `expires_at`, permitir reintentos ante código
    incorrecto, y manejar `COMPLETED`/`EXPIRED`/`FAILED` con el mensaje correspondiente.
  - No reflejar cambios de saldo hasta que la confirmación sea `COMPLETED`.
  - _Requisitos: 6.4, 7.2, 7.3, 8.2, 8.3, 8.4_

- [ ] 21. Implementar el historial (`HistoryList.tsx`)
  - Listar fecha, dirección (Checking→Savings con nombres amigables), monto (decimal-string)
    y descripción; no mostrar saldo resultante ni identificadores internos.
  - _Requisitos: 5.1, 5.2, 5.3, 2.2_

- [ ] 22. Integrar el estado de la app y el refresco de datos (`App.tsx`)
  - Orquestar cuentas, historial y pending MFA; recargar cuentas e historial tras cada
    operación completada.
  - _Requisitos: 2.1, 5.1, 6.4, 7.3_
