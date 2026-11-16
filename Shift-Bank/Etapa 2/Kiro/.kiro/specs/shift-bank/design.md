# Diseño — Shift Bank (Etapa 1)

## Visión general

Shift Bank (Etapa 1) es una aplicación cliente-servidor que modela a un único cliente
autenticado de forma simulada con exactamente dos cuentas propias (Checking y Savings) y una
única operación financiera: la transferencia entre esas dos cuentas. El diseño se centra en
tres pilares:

1. **Corrección monetaria:** todos los montos se manejan con `Decimal` en el backend y se
   transportan como cadenas decimales (decimal-string) en la API; en SQLite se almacenan como
   enteros de centavos (`INTEGER`) para evitar la aritmética imprecisa de `REAL`.
2. **Máquina de estados de transferencia:** una transferencia atraviesa estados bien
   definidos (`COMPLETED` directo, o `PENDING_MFA → COMPLETED | FAILED | EXPIRED`), con reglas
   explícitas sobre cuándo se tocan los saldos y cuándo no.
3. **Atomicidad:** la aplicación de una transferencia sobre los saldos ocurre dentro de una
   única transacción SQLite, de modo que ambos saldos cambian por completo o no cambia ninguno.

El backend es FastAPI sobre `sqlite3` (sin ORM); el frontend es React + TypeScript con CSS
puro. No hay servicios externos de autenticación ni de MFA: el cliente es un registro
sembrado y el código MFA es el valor fijo `123456`.

Este diseño cubre los Requisitos 1–9 del artefacto de requisitos aprobado. No introduce
funcionalidad fuera del alcance de la Etapa 1.

### Mapa de arquitectura

```
┌──────────────────────────────────────────────┐        ┌───────────────────────────────────────┐
│  Frontend (React + TypeScript, Vanilla CSS)   │        │  Backend (FastAPI, Python)            │
│                                               │        │                                       │
│  ┌─────────────┐   ┌───────────────────────┐  │  HTTP  │  ┌──────────┐  ┌──────────────────┐   │
│  │ AccountsView │──│ TransferForm / MFADlg │  │◀─────▶│  │ Routers  │─▶│ Service (reglas) │   │
│  └─────────────┘   └───────────────────────┘  │  JSON  │  └──────────┘  └────────┬─────────┘   │
│  ┌───────────────────────────────────────────┐│        │  ┌──────────────┐       │             │
│  │ HistoryView                               ││        │  │ Repository   │◀──────┘             │
│  └───────────────────────────────────────────┘│        │  │ (sqlite3)    │                     │
│         api client (decimal-string)           │        │  └──────┬───────┘                     │
└──────────────────────────────────────────────┘        │         ▼                             │
                                                         │   SQLite (INTEGER centavos)           │
                                                         └───────────────────────────────────────┘
```

### Decisiones de diseño y justificación

- **Dinero como centavos `INTEGER` en SQLite, `Decimal` en Python, string en API.**
  SQLite no tiene un tipo decimal exacto; `REAL` introduce error de punto flotante. Se
  almacenan centavos enteros (COP no usa subdivisiones circulantes, pero conservar dos
  decimales mantiene el patrón decimal-safe y evita suposiciones). La capa de repositorio
  convierte `INTEGER ↔ Decimal`; la capa de API convierte `Decimal ↔ str`. Alternativa
  descartada: almacenar `TEXT` decimal — complica comparaciones y sumas en SQL.
- **Umbral de MFA evaluado en el servicio, no en el cliente.** El cliente puede anticipar el
  diálogo de MFA, pero la autoridad sobre si una transferencia requiere MFA es del backend
  (Requisito 6), para que la regla no dependa de la UI.
- **Expiración perezosa (lazy) y verificada en cada acceso.** No se usa un job en segundo
  plano. El estado `EXPIRED` se determina comparando `expires_at` contra el instante actual
  cada vez que se lee o se intenta confirmar la transferencia (Requisito 8). Esto evita
  procesos de fondo y mantiene el alcance mínimo.
- **Re-verificación de fondos en el momento de confirmar MFA.** Como los saldos no se tocan
  durante `PENDING_MFA` (Requisito 6.4), al confirmar se vuelve a comprobar la suficiencia de
  fondos; si ya no alcanza, la transferencia pasa a `FAILED` (Requisito 8.4).
- **Identificadores internos ocultos a la UI.** El frontend referencia cuentas por su nombre
  amigable (`checking` / `savings`) como clave de operación; nunca se envían ni se muestran
  UUID ni IDs de base de datos (Requisito 2).

---

## Arquitectura

### Estructura de carpetas propuesta

```
Kiro/
├─ backend/
│  ├─ app/
│  │  ├─ main.py            # Creación de la app FastAPI, CORS, routers, startup (seed)
│  │  ├─ config.py          # Constantes: umbral MFA, código MFA, TTL, ruta DB
│  │  ├─ db.py              # Conexión sqlite3, PRAGMA, inicialización de esquema
│  │  ├─ money.py           # Helpers Decimal ↔ centavos ↔ decimal-string
│  │  ├─ seed.py            # Siembra de cliente, cuentas y transferencias históricas
│  │  ├─ repository.py      # Acceso a datos (SQL puro), transacciones atómicas
│  │  ├─ service.py         # Reglas de negocio (validaciones, MFA, máquina de estados)
│  │  ├─ schemas.py         # Modelos Pydantic de request/response (decimal-string)
│  │  └─ routers/
│  │     ├─ accounts.py     # GET /api/accounts
│  │     └─ transfers.py    # POST /api/transfers, POST /api/transfers/{id}/mfa, GET history
│  ├─ tests/                # (opcional en esta etapa; no se implementan salvo que se pidan)
│  └─ requirements.txt
├─ frontend/
│  ├─ index.html
│  ├─ package.json
│  ├─ tsconfig.json
│  ├─ vite.config.ts
│  └─ src/
│     ├─ main.tsx
│     ├─ App.tsx
│     ├─ api/client.ts      # fetch wrapper + tipos (montos como string)
│     ├─ types.ts           # tipos TS compartidos de la UI
│     ├─ components/
│     │  ├─ AccountsPanel.tsx
│     │  ├─ TransferForm.tsx
│     │  ├─ MfaDialog.tsx
│     │  └─ HistoryList.tsx
│     └─ styles/            # CSS puro (uno por componente o global)
└─ .kiro/specs/shift-bank/  # requirements.md, design.md, tasks.md
```

### Capas del backend

1. **Routers (FastAPI):** validan forma de entrada vía Pydantic, delegan al servicio y
   traducen excepciones de dominio a códigos HTTP. No contienen reglas de negocio.
2. **Service:** contiene todas las reglas (umbral de MFA, validaciones de monto, misma
   cuenta, fondos, máquina de estados, expiración perezosa). Es la única autoridad de negocio.
3. **Repository:** encapsula SQL (`sqlite3`), convierte filas a estructuras internas y ejecuta
   mutaciones dentro de transacciones. Es la única capa que habla con la base de datos.
4. **Money / Config / DB / Seed:** utilidades transversales.

### Modelo de concurrencia

La aplicación es de un solo cliente y de baja concurrencia. Aun así, la aplicación de saldos
se realiza dentro de una transacción SQLite explícita (`BEGIN IMMEDIATE … COMMIT`) para
garantizar atomicidad (Requisito 7.4). SQLite se abre con `check_same_thread=False` y acceso
serializado; FastAPI puede ejecutar los handlers de forma síncrona para simplificar.

---

## Modelo de datos (SQLite)

Se almacenan montos como **centavos enteros** (`INTEGER`). Fechas como texto ISO-8601 UTC.

### Tabla `customer`

| Columna | Tipo    | Notas                                   |
|---------|---------|-----------------------------------------|
| id      | TEXT PK | UUID del cliente mock (nunca expuesto)  |
| name    | TEXT    | Nombre del cliente (informativo)        |

Se siembra una única fila (Requisito 1.1).

### Tabla `account`

| Columna      | Tipo    | Notas                                             |
|--------------|---------|---------------------------------------------------|
| id           | TEXT PK | UUID interno (nunca expuesto a la UI)             |
| customer_id  | TEXT FK | Referencia a `customer.id`                        |
| kind         | TEXT    | `checking` o `savings` (clave estable de la UI)   |
| display_name | TEXT    | `Checking` o `Savings` (nombre amigable mostrado) |
| balance_cents| INTEGER | Saldo actual en centavos                          |

Restricción: `kind` es único por cliente. La columna `kind` es el identificador **no visible**
que el frontend usa para operar (Requisito 2.3); `display_name` es lo único que se muestra.

Siembra (Requisito 1.3): Checking = `500000000` centavos (COP 5,000,000);
Savings = `1500000000` centavos (COP 15,000,000).

### Tabla `transfer`

| Columna          | Tipo    | Notas                                                        |
|------------------|---------|--------------------------------------------------------------|
| id               | TEXT PK | UUID interno de la transferencia (nunca expuesto a la UI)    |
| from_kind        | TEXT    | `checking` o `savings` (origen)                              |
| to_kind          | TEXT    | `checking` o `savings` (destino)                             |
| amount_cents     | INTEGER | Monto en centavos                                            |
| description      | TEXT    | Descripción del movimiento                                   |
| status           | TEXT    | `PENDING_MFA` \| `COMPLETED` \| `FAILED` \| `EXPIRED`        |
| requires_mfa     | INTEGER | 0/1 (1 si monto ≥ umbral)                                    |
| created_at       | TEXT    | ISO-8601 UTC de creación                                     |
| expires_at       | TEXT    | ISO-8601 UTC; solo relevante en `PENDING_MFA` (created+5min) |
| completed_at     | TEXT    | ISO-8601 UTC cuando pasa a `COMPLETED` (NULL si no aplica)   |

Nota sobre identificadores: aunque `transfer.id` es un UUID interno, el frontend **sí** necesita
una referencia para confirmar MFA de una transferencia pendiente. Para no exponer identificadores
internos (Requisito 2.2), la API devuelve un **token de referencia opaco** por transferencia
pendiente (ver sección de API). Las transferencias del historial no exponen ningún id.

### Siembra de transferencias históricas (Requisito 4)

Se insertan dos filas con `status = COMPLETED`, `requires_mfa = 0`, `created_at` en el pasado,
`expires_at = NULL`:

- COP 500,000 de Savings a Checking → `from_kind=savings`, `to_kind=checking`, `amount_cents=50000000`.
- COP 100,000 de Checking a Savings → `from_kind=checking`, `to_kind=savings`, `amount_cents=10000000`.

**Importante (Requisito 4.4 y 1.4):** estas filas se insertan únicamente como *registros*
históricos. La siembra NO ejecuta la lógica de aplicación de saldos para ellas; los saldos de
las cuentas se fijan directamente a los valores del Requisito 1.3 y permanecen intactos por las
históricas. En otras palabras, el seed escribe saldos y transferencias históricas como datos
independientes, no deriva los saldos a partir de las transferencias.

---

## Manejo monetario (decimal-safe)

Módulo `money.py`:

- `cents_to_decimal(cents: int) -> Decimal`: `Decimal(cents) / Decimal(100)` cuantizado a 2
  decimales.
- `decimal_to_cents(value: Decimal) -> int`: cuantiza a 2 decimales y multiplica por 100,
  redondeando con `ROUND_HALF_UP`; valida que no haya pérdida.
- `parse_amount(raw: str) -> Decimal`: convierte la cadena decimal del request a `Decimal`,
  rechazando entradas no numéricas, con más de 2 decimales o con notación no decimal.
- `format_amount(value: Decimal) -> str`: produce la cadena decimal canónica con 2 decimales
  (p. ej. `"1000000.00"`) para las respuestas.

Reglas: la API nunca envía ni recibe números de punto flotante para montos; siempre strings
decimales (Requisito 3.5). Las comparaciones de suficiencia de fondos se hacen en centavos
enteros para exactitud total.

---

## Máquina de estados de la transferencia

```
                         monto ≤ 0  ─────────────▶ (rechazo 400, no se crea)
                         misma cuenta ───────────▶ (rechazo 400, no se crea)
 solicitud de           fondos insuficientes ────▶ (rechazo 400, no se crea)
 transferencia  ──────▶ validaciones OK
                           │
             monto < umbral│                 monto ≥ umbral
                           ▼                        ▼
                      aplica saldos            crea PENDING_MFA
                      atómicamente             (expires_at = now + 5min)
                           │                   (saldos NO cambian)
                           ▼                        │
                       COMPLETED        ┌───────────┼───────────────────────────┐
                                        ▼           ▼                           ▼
                             código correcto   código incorrecto         expiró (now>expires_at)
                             + aún válida       → sigue PENDING_MFA        → EXPIRED (no completa)
                             + fondos OK          (permite reintento)
                                   │
                      ┌────────────┴───────────┐
                      ▼                         ▼
             fondos suficientes          fondos insuficientes
             aplica saldos atóm.         → FAILED (saldos NO cambian)
                      ▼
                 COMPLETED
```

Reglas clave:

- En `PENDING_MFA` los saldos nunca cambian (Requisito 6.4). La aplicación de saldos ocurre
  solo en la transición a `COMPLETED`.
- La expiración se evalúa de forma perezosa: al leer o confirmar, si `now > expires_at` y el
  estado es `PENDING_MFA`, se marca `EXPIRED` y se persiste; `EXPIRED` es terminal
  (Requisito 8.2, 8.3).
- `FAILED`, `EXPIRED` y `COMPLETED` son terminales. Reintentar MFA solo es posible mientras el
  estado efectivo siga siendo `PENDING_MFA` (Requisito 7.2).
- No existe lockout por intentos fallidos (Requisito 7.5): el número de reintentos no se limita.

---

## API HTTP

Base URL: `/api`. Todos los montos viajan como cadenas decimales. Las respuestas de error usan
una forma consistente `{ "error": { "code": string, "message": string } }`.

### `GET /api/accounts`

Devuelve las dos cuentas con nombre amigable y saldo (sin IDs internos).

Respuesta `200`:
```json
{
  "accounts": [
    { "name": "Checking", "balance": "5000000.00" },
    { "name": "Savings",  "balance": "15000000.00" }
  ]
}
```

### `POST /api/transfers`

Crea una transferencia. El cuerpo referencia cuentas por su clave no visible (`from`/`to`
usando `checking`/`savings`), nunca por id interno.

Request:
```json
{ "from": "checking", "to": "savings", "amount": "250000.00", "description": "Ahorro mensual" }
```

Comportamiento:

- Valida misma cuenta, monto ≤ 0 y fondos insuficientes (Requisito 3) → `400` con `code`
  específico (`SAME_ACCOUNT`, `NON_POSITIVE_AMOUNT`, `INSUFFICIENT_FUNDS`).
- Si `amount < 1,000,000`: ejecuta de inmediato, aplica saldos atómicamente, responde `201`
  con `status: "COMPLETED"`.
- Si `amount ≥ 1,000,000`: crea `PENDING_MFA`, NO toca saldos, responde `201` con
  `status: "PENDING_MFA"`, `mfa_required: true`, `expires_at`, y un `reference` opaco para
  confirmar.

Respuesta (caso sin MFA) `201`:
```json
{ "status": "COMPLETED", "mfa_required": false }
```

Respuesta (caso con MFA) `201`:
```json
{
  "status": "PENDING_MFA",
  "mfa_required": true,
  "reference": "<token-opaco>",
  "expires_at": "2026-10-13T15:05:00Z"
}
```

El `reference` es un token opaco (no es el UUID interno; p. ej. identificador aleatorio o
UUID distinto emitido para la sesión del pending) que el cliente usa solo para confirmar MFA.

### `POST /api/transfers/{reference}/mfa`

Confirma una transferencia pendiente con el código MFA.

Request:
```json
{ "code": "123456" }
```

Comportamiento:

- Si la referencia no corresponde a una transferencia `PENDING_MFA` → `404` / `409` según el
  caso.
- Si está expirada (perezosa): marca `EXPIRED`, responde `409` con `code: "EXPIRED"`
  (Requisito 8.3).
- Si el código es incorrecto (y aún válida): mantiene `PENDING_MFA`, responde `401` con
  `code: "INVALID_MFA_CODE"` y permite reintentar (Requisito 7.2).
- Si el código es correcto pero los fondos ya no alcanzan: marca `FAILED`, responde `409` con
  `code: "INSUFFICIENT_FUNDS"` (Requisito 8.4).
- Si el código es correcto, válida y con fondos: aplica saldos atómicamente, marca
  `COMPLETED`, responde `200` con `status: "COMPLETED"` (Requisito 7.3, 7.4).

Respuesta (éxito) `200`:
```json
{ "status": "COMPLETED" }
```

### `GET /api/transfers`  (historial)

Devuelve el historial de transferencias ordenado por fecha descendente. Incluye las dos
históricas sembradas y las nuevas. No expone identificadores internos ni saldos resultantes.

Respuesta `200`:
```json
{
  "transfers": [
    {
      "date": "2026-10-13T15:04:00Z",
      "direction": { "from": "Checking", "to": "Savings" },
      "amount": "250000.00",
      "description": "Ahorro mensual",
      "status": "COMPLETED"
    }
  ]
}
```

Notas: `direction` usa nombres amigables (Requisito 5.1, 5.3). No se incluye saldo resultante
(Requisito 5.2). Se puede incluir `status` para que la UI distinga pendientes/fallidas/expiradas,
pero no es obligatorio mostrar saldo. El historial puede incluir o excluir estados no completados
según decisión de la UI; por defecto se muestran todas las transferencias con su estado.

### Mapa de errores HTTP

| Código de dominio      | HTTP | Situación                                              |
|------------------------|------|--------------------------------------------------------|
| `SAME_ACCOUNT`         | 400  | from == to                                             |
| `NON_POSITIVE_AMOUNT`  | 400  | amount ≤ 0                                              |
| `INVALID_AMOUNT`       | 400  | amount no parseable / >2 decimales                     |
| `INSUFFICIENT_FUNDS`   | 400  | fondos insuficientes al crear                          |
| `INSUFFICIENT_FUNDS`   | 409  | fondos insuficientes al confirmar MFA → FAILED         |
| `INVALID_MFA_CODE`     | 401  | código MFA incorrecto (sigue PENDING_MFA)              |
| `EXPIRED`              | 409  | transferencia expirada                                 |
| `NOT_FOUND`            | 404  | referencia inexistente                                 |

---

## Diseño del frontend (React + TypeScript, Vanilla CSS)

### Componentes

- **`App.tsx`**: orquesta el estado de alto nivel (cuentas, historial, pending MFA) y recarga
  datos tras cada operación.
- **`AccountsPanel.tsx`**: muestra las dos cuentas con `display_name` y saldo formateado. No
  muestra ningún identificador (Requisito 2).
- **`TransferForm.tsx`**: selección de origen/destino (Checking/Savings), monto y descripción.
  Deshabilita destino = origen en la UI, pero la validación autoritativa es del backend.
- **`MfaDialog.tsx`**: aparece cuando la respuesta de creación es `PENDING_MFA`. Pide el código,
  muestra un contador hacia `expires_at`, permite reintentos ante código incorrecto, y maneja
  los estados `EXPIRED`/`FAILED` mostrando el mensaje correspondiente.
- **`HistoryList.tsx`**: lista fecha, dirección (Checking→Savings con nombres amigables), monto
  y descripción; opcionalmente el estado. No muestra saldo resultante.

### Cliente de API (`api/client.ts`)

- Envía y recibe montos como `string` (nunca `number`) para preservar exactitud decimal.
- Expone funciones: `getAccounts()`, `createTransfer()`, `confirmMfa(reference, code)`,
  `getHistory()`.
- Normaliza los errores `{ error: { code, message } }` para que la UI muestre mensajes claros.

### Flujo de UI del MFA

1. El usuario envía una transferencia ≥ COP 1,000,000.
2. El backend responde `PENDING_MFA` + `reference` + `expires_at`; la UI abre `MfaDialog`.
3. El usuario ingresa el código:
   - Incorrecto → mensaje de error, el diálogo permanece abierto para reintentar.
   - Correcto y válido → `COMPLETED`; se cierran el diálogo y se refrescan cuentas e historial.
   - Expirado → mensaje de expiración; el diálogo se cierra y la transferencia queda `EXPIRED`.
   - Fondos insuficientes al confirmar → mensaje de fallo; transferencia `FAILED`.

Los saldos mostrados solo cambian tras un `COMPLETED` confirmado (coherente con Requisito 6.4).

---

## Manejo de errores

- **Validaciones de dominio** se lanzan como excepciones tipadas en el servicio
  (`DomainError` con `code`), y los routers las mapean a HTTP según la tabla anterior.
- **Entradas malformadas** (JSON inválido, campos faltantes) las captura Pydantic → `422`.
- **Montos inválidos** (no decimal, exceso de decimales) → `400 INVALID_AMOUNT`.
- **Estados terminales** al intentar confirmar MFA (`COMPLETED`/`FAILED`/`EXPIRED`) → `409`
  con el `code` correspondiente, sin alterar saldos.
- El frontend muestra mensajes legibles por `code` y nunca revela identificadores internos.

---

## Estrategia de pruebas

> No se implementan pruebas automáticas en esta etapa salvo que se soliciten explícitamente.
> Esta sección documenta la estrategia recomendada para la fase de implementación.

Casos de verificación recomendados (manuales o automatizados):

1. **Siembra:** al iniciar, Checking = 5,000,000.00 y Savings = 15,000,000.00; existen
   exactamente dos transferencias históricas (500,000 S→C y 100,000 C→S) y los saldos NO
   reflejan su aplicación (Requisitos 1, 4).
2. **Transferencia simple (< umbral):** 250,000 C→S ejecuta de inmediato, saldos actualizados
   atómicamente, aparece en historial como `COMPLETED` (Requisito 6.1).
3. **Rechazos:** misma cuenta, monto 0, monto negativo, y monto > saldo disponible → errores
   correspondientes y sin cambios de saldo (Requisito 3).
4. **MFA requerido:** 1,000,000 C→S crea `PENDING_MFA`, saldos sin cambios, devuelve
   `reference` y `expires_at` (Requisito 6.2–6.4).
5. **MFA código incorrecto:** sigue `PENDING_MFA`, permite reintentar (Requisito 7.2).
6. **MFA correcto:** pasa a `COMPLETED` y actualiza ambos saldos atómicamente (Requisito 7.3–7.4).
7. **Expiración:** tras 5 minutos, `PENDING_MFA` → `EXPIRED`; el código correcto ya no completa
   (Requisito 8.1–8.3).
8. **Fondos insuficientes al confirmar:** si entre la creación y la confirmación el saldo deja
   de alcanzar, confirmar con código correcto → `FAILED`, sin cambios de saldo (Requisito 8.4–8.5).
9. **Decimal-safe:** montos con decimales se transportan como string y suman/validan sin error
   de punto flotante (Requisito 3.5).
10. **Sin exposición de identificadores:** ninguna respuesta de UI contiene UUID/IDs/números de
    cuenta (Requisito 2).

---

## Trazabilidad diseño ↔ requisitos

| Requisito | Cubierto por                                                                 |
|-----------|------------------------------------------------------------------------------|
| 1         | `seed.py`, tablas `customer`/`account`, saldos fijados directamente           |
| 2         | API sin IDs, `kind` no visible, `reference` opaco, componentes de UI          |
| 3         | `service.py` (validaciones), `money.py`, `POST /api/transfers`                |
| 4         | `seed.py` (dos históricas como registros, sin aplicar saldos)                 |
| 5         | `GET /api/transfers`, `HistoryList.tsx`                                        |
| 6         | `service.py` (umbral), estado `PENDING_MFA`, saldos intactos                   |
| 7         | `POST /api/transfers/{ref}/mfa`, transacción atómica, sin lockout             |
| 8         | expiración perezosa, re-chequeo de fondos, estados `EXPIRED`/`FAILED`         |
| 9         | stack FastAPI + sqlite3 (sin ORM) + React/TS + Vanilla CSS, alcance acotado   |
