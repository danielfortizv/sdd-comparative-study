"""Capa de base de datos: conexión sqlite3 y esquema (Requisito 9.2).

Usa el módulo `sqlite3` incorporado, sin ORM. El esquema almacena montos como
centavos enteros (`INTEGER`) y fechas como texto ISO-8601 UTC, tal como fija el diseño.
"""

import sqlite3
from pathlib import Path

from . import crypto
from .config import DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS customer (
    id   TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS account (
    id            TEXT PRIMARY KEY,
    customer_id   TEXT NOT NULL,
    kind          TEXT NOT NULL,
    display_name  TEXT NOT NULL,
    balance_cents INTEGER NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customer (id),
    UNIQUE (customer_id, kind)
);

CREATE TABLE IF NOT EXISTS transfer (
    id           TEXT PRIMARY KEY,
    reference    TEXT UNIQUE,
    from_kind    TEXT NOT NULL,
    to_kind      TEXT NOT NULL,
    amount_cents INTEGER NOT NULL,
    description  TEXT NOT NULL,
    status       TEXT NOT NULL,
    requires_mfa INTEGER NOT NULL,
    created_at   TEXT NOT NULL,
    expires_at   TEXT,
    completed_at TEXT
);
"""


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Abre una conexión sqlite3 con filas por nombre y claves foráneas activadas.

    Etapa 3 (Tarea 9, design.md §2.8/§5.1/DT-7): se fija `PRAGMA journal_mode=WAL` al abrir
    la conexión, ANTES de cualquier transacción explícita. WAL es una propiedad **persistente**
    del archivo de base de datos (una vez aplicado queda en modo WAL para conexiones futuras),
    así que establecerlo en cada apertura es idempotente y barato. Se ejecuta aquí (no dentro de
    `migrate`) para no colocar el PRAGMA dentro de la transacción `BEGIN...COMMIT` de la
    migración, donde SQLite lo ignoraría. Para DB en memoria (`:memory:`) el modo permanece
    `memory`, lo cual es correcto y no rompe el aislamiento por prueba.
    """
    path = str(db_path or DB_PATH)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Crea las tablas del esquema si no existen."""
    conn.executescript(_SCHEMA)
    conn.commit()


# --- Migración de la Etapa 2 (Tarea 7) ----------------------------------------
#
# Evolución aditiva, idempotente y transaccional del esquema heredado de la Etapa 1.
# Alcance de la Tarea 7: andamiaje transaccional + extensión de la tabla `transfer`.
# El DDL de las tablas nuevas (beneficiary, recurring_schedule, schedule_execution,
# transfer_limit) con sus FKs/unicidad/índices pertenece a la Tarea 8 y NO se define aquí.

# Columnas nuevas de `transfer` (Tarea 7). Cada entrada es (nombre, cláusula de tipo para ADD
# COLUMN). `type` lleva DEFAULT 'internal' NOT NULL para clasificar las filas heredadas sin
# necesidad de backfill; el backfill (7.4) es una salvaguarda adicional.
_TRANSFER_NEW_COLUMNS: list[tuple[str, str]] = [
    ("type", "TEXT NOT NULL DEFAULT 'internal'"),
    ("beneficiary_id", "TEXT"),
    ("beneficiary_snapshot", "TEXT"),
    ("settled_at", "TEXT"),
    ("refunded", "INTEGER NOT NULL DEFAULT 0"),
    ("schedule_id", "TEXT"),
]

# --- DDL de las tablas nuevas de la Etapa 2 (Tarea 8) -------------------------
#
# Montos en centavos enteros (INTEGER); fechas ISO-8601 UTC (TEXT). FKs declaradas en las
# tablas nuevas (SQLite aplica FKs declaradas en CREATE TABLE con `PRAGMA foreign_keys=ON`).
# Nota de limitación (F13): las columnas `transfer.beneficiary_id` y `transfer.schedule_id`
# se añadieron por `ALTER TABLE` en la Tarea 7 y SQLite no permite añadir una cláusula FK a una
# tabla existente sin reconstruirla; para no reconstruir destructivamente la tabla heredada
# `transfer` (preservando sus datos y su contrato), esas dos referencias NO llevan FK declarada.
# La integridad en ese sentido se garantiza a nivel de servicio en tareas posteriores. Todas las
# FKs entre las tablas NUEVAS sí se declaran.
# Cada entrada es una sentencia DDL independiente. Se ejecutan con `conn.execute()` (una por
# una) dentro de la transacción explícita de `migrate`; NO se usa `executescript`, que haría un
# COMMIT implícito y rompería la atomicidad/rollback de la migración (F11).
_STAGE2_TABLES: list[str] = [
    """CREATE TABLE IF NOT EXISTS beneficiary (
        id              TEXT PRIMARY KEY,
        customer_id     TEXT NOT NULL,
        name            TEXT NOT NULL,
        bank            TEXT NOT NULL,
        routing_number  TEXT NOT NULL,
        account_number  TEXT NOT NULL,
        created_at      TEXT NOT NULL,
        deleted_at      TEXT,
        FOREIGN KEY (customer_id) REFERENCES customer (id)
    )""",
    """CREATE TABLE IF NOT EXISTS recurring_schedule (
        id                   TEXT PRIMARY KEY,
        customer_id          TEXT NOT NULL,
        type                 TEXT NOT NULL,
        from_kind            TEXT NOT NULL,
        to_kind              TEXT,
        beneficiary_id       TEXT,
        beneficiary_snapshot TEXT,
        amount_cents         INTEGER NOT NULL,
        description          TEXT NOT NULL DEFAULT '',
        frequency            TEXT NOT NULL,
        status               TEXT NOT NULL,
        requires_mfa         INTEGER NOT NULL DEFAULT 0,
        authorized           INTEGER NOT NULL DEFAULT 0,
        next_run_at          TEXT NOT NULL,
        created_at           TEXT NOT NULL,
        FOREIGN KEY (customer_id) REFERENCES customer (id),
        FOREIGN KEY (beneficiary_id) REFERENCES beneficiary (id)
    )""",
    """CREATE TABLE IF NOT EXISTS transfer_limit (
        customer_id        TEXT PRIMARY KEY,
        per_transfer_cents INTEGER NOT NULL,
        daily_cents        INTEGER NOT NULL,
        updated_at         TEXT NOT NULL,
        FOREIGN KEY (customer_id) REFERENCES customer (id)
    )""",
    """CREATE TABLE IF NOT EXISTS schedule_execution (
        id          TEXT PRIMARY KEY,
        schedule_id TEXT NOT NULL,
        due_at      TEXT NOT NULL,
        outcome     TEXT NOT NULL,
        transfer_id TEXT,
        created_at  TEXT NOT NULL,
        UNIQUE (schedule_id, due_at),
        FOREIGN KEY (schedule_id) REFERENCES recurring_schedule (id),
        FOREIGN KEY (transfer_id) REFERENCES transfer (id)
    )""",
]

# Índices de la Etapa 2 (Tarea 8, F13): soporte de historial, consumo diario, selección de
# schedules vencidos y lookup de beneficiarios por propietario.
_STAGE2_INDEXES: list[str] = [
    "CREATE INDEX IF NOT EXISTS idx_transfer_created_at ON transfer (created_at)",
    "CREATE INDEX IF NOT EXISTS idx_transfer_type_status ON transfer (type, status)",
    "CREATE INDEX IF NOT EXISTS idx_schedule_due ON recurring_schedule (status, next_run_at)",
    "CREATE INDEX IF NOT EXISTS idx_beneficiary_customer ON beneficiary (customer_id, deleted_at)",
]

# --- DDL de auditoría de la Etapa 3 (Tarea 9) ---------------------------------
#
# design.md §2.1 (audit_log), §2.9/§5.1 (audit_anchor), §2.4 (triggers append-only).
# Todo aditivo e idempotente (CREATE ... IF NOT EXISTS). Se ejecuta por sentencia con
# `conn.execute()` dentro de la transacción explícita de `migrate` (no `executescript`, que
# haría COMMIT implícito y rompería la atomicidad/rollback de la migración, F11).
#
# `audit_log` (§2.1): bitácora append-only encadenada con HMAC. `seq` AUTOINCREMENT da orden
# total monotónico; `payload` es JSON canónico con metadatos NO sensibles; `prev_hmac`/
# `entry_hmac` encadenan las entradas (la génesis usa prev_hmac="").
#
# `audit_anchor` (§2.9/§5.1): ancla de cola de una sola fila (CHECK id=1) que persiste el último
# `seq`/`entry_hmac` fuera de `audit_log`, permitiendo que `verify_chain` detecte la truncación
# del final de la cola (dentro del modelo de amenazas de §10/§2.9).
_STAGE3_AUDIT_TABLES: list[str] = [
    """CREATE TABLE IF NOT EXISTS audit_log (
        seq         INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type  TEXT NOT NULL,
        outcome     TEXT NOT NULL,
        entity_ref  TEXT,
        occurred_at TEXT NOT NULL,
        payload     TEXT NOT NULL,
        prev_hmac   TEXT NOT NULL,
        entry_hmac  TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS audit_anchor (
        id        INTEGER PRIMARY KEY CHECK (id = 1),
        last_seq  INTEGER NOT NULL,
        last_hmac TEXT NOT NULL
    )""",
]

# Triggers de endurecimiento append-only (§2.4, R6.1/R6.2): abortan cualquier UPDATE o DELETE
# ordinario sobre `audit_log`. No son WORM absoluto frente a un DBA que altere el esquema
# (limitación documentada en §2.4/§10), pero impiden la mutación desde la aplicación o SQL
# casual. `CREATE TRIGGER IF NOT EXISTS` los hace idempotentes en cada arranque.
_STAGE3_AUDIT_TRIGGERS: list[str] = [
    """CREATE TRIGGER IF NOT EXISTS audit_log_no_update
       BEFORE UPDATE ON audit_log
       BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END""",
    """CREATE TRIGGER IF NOT EXISTS audit_log_no_delete
       BEFORE DELETE ON audit_log
       BEGIN SELECT RAISE(ABORT, 'audit_log is append-only'); END""",
]


# --- DDL de la Etapa 4 (multidivisa, Event Sourcing, CQRS, idempotencia) ------
#
# design.md §1.1–§1.4. Evolución ADITIVA, idempotente y transaccional sobre el esquema heredado,
# dentro de la MISMA transacción explícita de `migrate` (sin `executescript`, F11). No se elimina
# ninguna tabla/columna heredada.

# §1.1 — columnas nuevas de `account` (currency/public_id/version) para el modelo multidivisa y la
# concurrencia optimista (D-01/D-02/D-09/D-14, DK-02). `currency` lleva DEFAULT 'USD' NOT NULL
# para clasificar las filas heredadas sin backfill destructivo; `version` arranca en 0.
_STAGE4_ACCOUNT_COLUMNS: list[tuple[str, str]] = [
    ("currency", "TEXT NOT NULL DEFAULT 'USD'"),
    ("public_id", "TEXT"),
    ("version", "INTEGER NOT NULL DEFAULT 0"),
]

# También se clasifica `transfer.currency` (aditivo) para que las internas/ACH heredadas queden en
# USD, coherente con la fixture D-02 (no mezcla de monedas en una fila).
_STAGE4_TRANSFER_COLUMNS: list[tuple[str, str]] = [
    ("currency", "TEXT NOT NULL DEFAULT 'USD'"),
]

# §1.2 — almacén de eventos de dominio append-only, SEPARADO de `audit_log` (D-05). Una fila por
# cuenta afectada; `UNIQUE(aggregate_id, aggregate_ver)` impide aplicar dos veces la misma versión
# (anti-duplicado). `operation_id` agrupa un evento compuesto (p. ej. una conversión de 2 cuentas).
_STAGE4_EVENT_TABLES: list[str] = [
    """CREATE TABLE IF NOT EXISTS domain_event (
        seq           INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id      TEXT NOT NULL UNIQUE,
        event_type    TEXT NOT NULL,
        aggregate_id  TEXT NOT NULL,
        aggregate_ver INTEGER NOT NULL,
        operation_id  TEXT NOT NULL,
        currency      TEXT NOT NULL,
        amount_minor  INTEGER NOT NULL,
        payload       TEXT NOT NULL,
        occurred_at   TEXT NOT NULL,
        UNIQUE (aggregate_id, aggregate_ver)
    )""",
    # §1.3 — read model CQRS. Fuente autoritativa de las consultas de saldo; se actualiza en la
    # MISMA transacción que `domain_event`. `version` debe igualar `account.version`.
    """CREATE TABLE IF NOT EXISTS account_projection (
        account_id    TEXT PRIMARY KEY,
        public_id     TEXT NOT NULL,
        kind          TEXT NOT NULL,
        currency      TEXT NOT NULL,
        balance_minor INTEGER NOT NULL,
        version       INTEGER NOT NULL,
        updated_at    TEXT NOT NULL
    )""",
    # §1.4 — registro de idempotencia (D-13). `request_hash` permite distinguir replay exacto
    # (mismo payload) de reuse con payload distinto (-> 409).
    """CREATE TABLE IF NOT EXISTS idempotency_key (
        id            TEXT PRIMARY KEY,
        operation     TEXT NOT NULL,
        request_hash  TEXT NOT NULL,
        response_json TEXT NOT NULL,
        status_code   INTEGER NOT NULL,
        created_at    TEXT NOT NULL
    )""",
    # Etapa 4 (Tarea 14, D-07) — operaciones v2 (conversión/transferencia) pendientes de MFA
    # cuando el equivalente USD SIN redondear > USD 1,000.00. Guarda el plan validado para
    # aplicarlo al confirmar el código MFA, sin mover saldos hasta entonces. `reference` es el
    # identificador público de confirmación; `expires_at` la ventana MFA heredada (5 min).
    """CREATE TABLE IF NOT EXISTS v2_pending_mfa (
        reference     TEXT PRIMARY KEY,
        operation     TEXT NOT NULL,
        from_public   TEXT NOT NULL,
        to_public     TEXT NOT NULL,
        amount_minor  INTEGER NOT NULL,
        dest_minor    INTEGER NOT NULL,
        rate          TEXT NOT NULL,
        idempotency_key TEXT NOT NULL,
        status        TEXT NOT NULL,
        created_at    TEXT NOT NULL,
        expires_at    TEXT NOT NULL
    )""",
]

_STAGE4_EVENT_INDEXES: list[str] = [
    "CREATE INDEX IF NOT EXISTS idx_event_aggregate ON domain_event (aggregate_id, aggregate_ver)",
    "CREATE INDEX IF NOT EXISTS idx_event_operation ON domain_event (operation_id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_account_public_id ON account (public_id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_account_kind_ccy ON account (customer_id, kind, currency)",
]

# Triggers append-only del almacén de eventos (mismo patrón que `audit_log`): abortan UPDATE/DELETE
# ordinarios. No son WORM absoluto frente a un DBA que altere el esquema (limitación documentada),
# pero impiden la mutación desde la aplicación o SQL casual (D-05, inmutabilidad de eventos).
_STAGE4_EVENT_TRIGGERS: list[str] = [
    """CREATE TRIGGER IF NOT EXISTS domain_event_no_update
       BEFORE UPDATE ON domain_event
       BEGIN SELECT RAISE(ABORT, 'domain_event is append-only'); END""",
    """CREATE TRIGGER IF NOT EXISTS domain_event_no_delete
       BEFORE DELETE ON domain_event
       BEGIN SELECT RAISE(ABORT, 'domain_event is append-only'); END""",
]


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    """Devuelve True si `column` ya existe en `table` (vía PRAGMA table_info).

    SQLite no soporta `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`, por lo que la existencia se
    comprueba antes de intentar la alteración (Tarea 7.2).
    """
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    existing = {r["name"] for r in rows}
    return column in existing


def migrate(conn: sqlite3.Connection) -> None:
    """Migración aditiva, idempotente y transaccional de la Etapa 2 (Tarea 7).

    - Transaccional: todo ocurre dentro de una única transacción; ante cualquier fallo se
      revierte por completo (ROLLBACK), sin dejar el esquema a medias (F11).
    - Idempotente: es seguro re-ejecutarla en cada arranque (las alteraciones son condicionales
      a la existencia de la columna).
    - Preserva la Etapa 1: no toca la tabla `account` ni las filas históricas de `transfer`;
      solo añade columnas nuevas y normaliza `type` para las filas heredadas (F12).

    Nota de alcance: la Tarea 7 evoluciona la tabla heredada `transfer`; la Tarea 8 crea las
    tablas nuevas de la Etapa 2 y sus índices/constraints; la Tarea 9 (Etapa 3) añade el esquema
    de auditoría (`audit_log`/`audit_anchor` + triggers append-only). Todo es aditivo, idempotente
    y vive dentro de esta misma transacción explícita.
    """
    try:
        conn.execute("BEGIN")

        # Tarea 8 — Crear las tablas nuevas (idempotente). Se usa `conn.execute` por sentencia
        # (no `executescript`, que haría COMMIT implícito y rompería la transacción).
        for stmt in _STAGE2_TABLES:
            conn.execute(stmt)

        # 7.3 — Añadir columnas nuevas a `transfer` solo si faltan. Debe ir ANTES de crear
        # índices que referencian esas columnas (p. ej. idx_transfer_type_status sobre `type`).
        for name, type_clause in _TRANSFER_NEW_COLUMNS:
            if not _column_exists(conn, "transfer", name):
                conn.execute(f"ALTER TABLE transfer ADD COLUMN {name} {type_clause}")

        # 7.4 — Backfill de robustez: clasificar como 'internal' cualquier fila heredada cuyo
        # `type` haya quedado NULL (p. ej. si la columna existiera de una migración previa sin
        # default). Redundante con el DEFAULT, garantiza que ninguna fila quede sin clasificar.
        conn.execute("UPDATE transfer SET type = 'internal' WHERE type IS NULL")

        # Tarea 8 — Crear los índices al final, cuando ya existen todas las columnas (incluida
        # `transfer.type`, de la que depende idx_transfer_type_status). Idempotente.
        for stmt in _STAGE2_INDEXES:
            conn.execute(stmt)

        # Tarea 9 (Etapa 3) — Esquema de auditoría: tablas `audit_log`/`audit_anchor` y triggers
        # append-only. Aditivo e idempotente; dentro de la misma transacción explícita (el PRAGMA
        # journal_mode=WAL se fija aparte, en get_connection, fuera de cualquier transacción).
        for stmt in _STAGE3_AUDIT_TABLES:
            conn.execute(stmt)
        for stmt in _STAGE3_AUDIT_TRIGGERS:
            conn.execute(stmt)

        # Etapa 4 (Tarea 5) — multidivisa + Event Sourcing + CQRS + idempotencia. Aditivo e
        # idempotente, dentro de la misma transacción. Primero las columnas nuevas de `account`
        # y `transfer` (condicionales a existencia, como la Etapa 2), luego las tablas/índices/
        # triggers nuevos. Los índices únicos de `account` van DESPUÉS de añadir `public_id`/
        # `currency` (de los que dependen).
        for name, type_clause in _STAGE4_ACCOUNT_COLUMNS:
            if not _column_exists(conn, "account", name):
                conn.execute(f"ALTER TABLE account ADD COLUMN {name} {type_clause}")
        for name, type_clause in _STAGE4_TRANSFER_COLUMNS:
            if not _column_exists(conn, "transfer", name):
                conn.execute(f"ALTER TABLE transfer ADD COLUMN {name} {type_clause}")
        conn.execute("UPDATE account SET currency = 'USD' WHERE currency IS NULL")
        conn.execute("UPDATE transfer SET currency = 'USD' WHERE currency IS NULL")
        for stmt in _STAGE4_EVENT_TABLES:
            conn.execute(stmt)
        for stmt in _STAGE4_EVENT_INDEXES:
            conn.execute(stmt)
        for stmt in _STAGE4_EVENT_TRIGGERS:
            conn.execute(stmt)

        conn.commit()
    except Exception:
        conn.rollback()
        raise


# --- Migración de cifrado de datos existentes (Tarea 8, R3) -------------------
#
# design.md §1.6 / §8 G3. Recorre las columnas sensibles de los registros ya existentes y
# cifra EN SU LUGAR cualquier valor en claro (aún no cifrado). Pensada para los registros
# heredados/pre-existentes creados antes de activar el cifrado en escritura (Tarea 7); desde
# la Tarea 7 el camino normal ya cifra al escribir, por lo que en una DB "nueva" esta
# migración es un no-op idempotente.
#
# Cada entrada es (tabla, columna, cláusula WHERE que acota las filas candidatas). El WHERE
# excluye NULL para no procesar filas sin snapshot; los valores vacíos y los ya cifrados se
# filtran en Python antes de recifrar (idempotencia, R3.1).
_ENCRYPTION_TARGETS: list[tuple[str, str, str]] = [
    ("beneficiary", "account_number", "account_number IS NOT NULL"),
    ("beneficiary", "routing_number", "routing_number IS NOT NULL"),
    ("transfer", "beneficiary_snapshot",
     "type = 'ach' AND beneficiary_snapshot IS NOT NULL"),
    ("recurring_schedule", "beneficiary_snapshot", "beneficiary_snapshot IS NOT NULL"),
]


def migrate_encryption(conn: sqlite3.Connection) -> None:
    """Migración de cifrado idempotente y transaccional de los registros sensibles (Tarea 8).

    Recorre las columnas sensibles (`beneficiary.account_number`/`routing_number`,
    `transfer.beneficiary_snapshot` de filas ACH, `recurring_schedule.beneficiary_snapshot`)
    y cifra EN SU LUGAR cualquier valor en claro pendiente de migrar (design.md §1.6).

    Garantías:

    - **Idempotente (R3.1):** usa `crypto.is_encrypted(value)` para omitir los valores ya
      cifrados; solo cifra valores no nulos, no vacíos y que todavía no tienen el prefijo
      `enc:v1:`. Re-ejecutarla no vuelve a cifrar ni corrompe (el token cifrado se deja igual).
    - **Transaccional con ROLLBACK total (R3.2):** toda la migración ocurre dentro de una
      única transacción explícita (`BEGIN` ... `COMMIT`, mismo patrón que `migrate`). Ante
      cualquier excepción (p. ej. un valor corrupto/no decodificable o un fallo de `encrypt`)
      hace `ROLLBACK` completo: no queda una mezcla inconsistente de filas cifradas y en claro.
      No se usa `executescript` (haría COMMIT implícito y rompería la atomicidad).
    - **Sin claro al terminar (R3.4):** tras un COMMIT exitoso ningún identificador sensible
      queda en texto plano en las columnas objetivo.
    - **Preserva datos y contratos (R3.3):** no toca columnas no sensibles (nombre, banco,
      saldos, montos) ni otras tablas; se integra tras `migrate` en el arranque y es segura de
      re-ejecutar en cada arranque.

    La clave activa la provee `crypto.encrypt` (configuración externa fail-closed, Tarea 5/6).
    """
    try:
        conn.execute("BEGIN")

        for table, column, where in _ENCRYPTION_TARGETS:
            # Se lee el rowid para una actualización precisa fila-a-fila, independiente de las
            # claves primarias de cada tabla (todas las tablas tienen rowid implícito).
            rows = conn.execute(
                f"SELECT rowid AS _rid, {column} AS _val FROM {table} WHERE {where}"
            ).fetchall()
            for row in rows:
                value = row["_val"]
                # Omitir nulos/vacíos y los valores ya cifrados (idempotencia, R3.1).
                if value is None or value == "" or crypto.is_encrypted(value):
                    continue
                token = crypto.encrypt(value)
                conn.execute(
                    f"UPDATE {table} SET {column} = ? WHERE rowid = ?",
                    (token, row["_rid"]),
                )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
