"""Utilidades compartidas de transacción financiera (Etapa 2, Tarea 10).

Proveen un límite transaccional explícito y reutilizable para componer varias operaciones de
repositorio dentro de una **única** transacción SQLite `BEGIN IMMEDIATE`, de modo que las
futuras operaciones financieras de la Etapa 2 (transferencias internas con límites, autorización
y débito ACH, settlement/fallo ACH, ejecución recurrente, idempotencia durable) puedan ejecutar
lectura → validación → movimiento → persistencia de estado sin commits intermedios.

Alcance de la Tarea 10: SOLO la infraestructura transaccional compartida. NO implementa ninguna
de esas operaciones de negocio.

Diseño (DD-4, F8/F9, F11):
- `financial_transaction(conn)` es un context manager que abre `BEGIN IMMEDIATE` al entrar,
  hace `COMMIT` si el bloque termina sin excepción y `ROLLBACK` si se propaga una excepción.
- El **llamador es el dueño** de la transacción; todas las operaciones de repositorio dentro del
  bloque usan la misma `conn`, por lo que comparten la transacción y se confirman/revierten
  juntas (atomicidad; sin actualizaciones parciales).
- **Política de anidamiento (documentada):** no se soportan transacciones anidadas. Si ya hay
  una transacción activa en la conexión, se lanza `TransactionError` en lugar de abrir otra
  (evita commits/rollbacks ambiguos). No se usan savepoints: no son necesarios para el alcance.
- Sin commits ocultos: el helper no usa `executescript` (que haría un COMMIT implícito) y no
  ejecuta más SQL que el control de transacción.
- Compatible con `app.db.get_connection` heredado (sqlite3, `check_same_thread=False`,
  `PRAGMA foreign_keys=ON`). No introduce pooling, locks distribuidos ni estado global mutable.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator


class TransactionError(RuntimeError):
    """Se solicitó abrir una transacción financiera cuando ya había una activa."""


@contextmanager
def financial_transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Context manager de transacción financiera atómica (`BEGIN IMMEDIATE` … `COMMIT`).

    Uso:
        with financial_transaction(conn):
            repository.op_a(conn, ...)
            repository.op_b(conn, ...)
        # COMMIT automático al salir sin excepción; ROLLBACK si algo lanzó.

    - Adquiere el lock de escritura al inicio (`BEGIN IMMEDIATE`), serializando a un único
      escritor en SQLite (soporte de F8/F9 para concurrencia entre conexiones distintas).
    - No permite anidamiento: si la conexión ya está en transacción (`conn.in_transaction`),
      lanza `TransactionError` sin tocar la transacción existente.
    """
    if conn.in_transaction:
        raise TransactionError(
            "Ya hay una transacción activa en esta conexión; "
            "financial_transaction no abre transacciones anidadas."
        )

    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.rollback()
        raise
    else:
        conn.commit()
