"""Capa de base de datos: conexión sqlite3 y esquema (Requisito 9.2).

Usa el módulo `sqlite3` incorporado, sin ORM. El esquema almacena montos como
centavos enteros (`INTEGER`) y fechas como texto ISO-8601 UTC, tal como fija el diseño.
"""

import sqlite3
from pathlib import Path

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
    """Abre una conexión sqlite3 con filas por nombre y claves foráneas activadas."""
    path = str(db_path or DB_PATH)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
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

    Nota de alcance (Tarea 7): aquí solo se evoluciona la tabla heredada `transfer`. La creación
    de las tablas nuevas y sus índices/constraints corresponde a la Tarea 8.
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

        conn.commit()
    except Exception:
        conn.rollback()
        raise
