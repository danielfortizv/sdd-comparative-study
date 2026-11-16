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
