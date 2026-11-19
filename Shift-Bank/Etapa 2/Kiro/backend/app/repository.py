"""Repositorio: acceso a datos con SQL puro (sqlite3), sin ORM.

Única capa que habla con la base de datos. Convierte filas a dataclasses internas y
ejecuta las mutaciones de saldo dentro de una transacción atómica (Requisito 7.4).
"""

import sqlite3
import uuid
from dataclasses import dataclass

_SELECT_SCHEDULE_BY_ID = "SELECT * FROM recurring_schedule WHERE id = ?"


@dataclass
class Account:
    kind: str
    display_name: str
    balance_cents: int


@dataclass
class Transfer:
    id: str
    reference: str | None
    from_kind: str
    to_kind: str
    amount_cents: int
    description: str
    status: str
    requires_mfa: int
    created_at: str
    expires_at: str | None
    completed_at: str | None


def _row_to_account(row: sqlite3.Row) -> Account:
    return Account(
        kind=row["kind"],
        display_name=row["display_name"],
        balance_cents=row["balance_cents"],
    )


def _row_to_transfer(row: sqlite3.Row) -> Transfer:
    return Transfer(
        id=row["id"],
        reference=row["reference"],
        from_kind=row["from_kind"],
        to_kind=row["to_kind"],
        amount_cents=row["amount_cents"],
        description=row["description"],
        status=row["status"],
        requires_mfa=row["requires_mfa"],
        created_at=row["created_at"],
        expires_at=row["expires_at"],
        completed_at=row["completed_at"],
    )


# --- Cuentas (Tarea 6) ---------------------------------------------------------

def list_accounts(conn: sqlite3.Connection) -> list[Account]:
    """Devuelve las cuentas en orden fijo (checking, savings)."""
    rows = conn.execute(
        "SELECT kind, display_name, balance_cents FROM account"
    ).fetchall()
    accounts = [_row_to_account(r) for r in rows]
    order = {"checking": 0, "savings": 1}
    accounts.sort(key=lambda a: order.get(a.kind, 99))
    return accounts


def get_account(conn: sqlite3.Connection, kind: str) -> Account | None:
    row = conn.execute(
        "SELECT kind, display_name, balance_cents FROM account WHERE kind = ?",
        (kind,),
    ).fetchone()
    return _row_to_account(row) if row else None


# --- Transferencias (Tarea 7) --------------------------------------------------

def create_transfer(
    conn: sqlite3.Connection,
    *,
    from_kind: str,
    to_kind: str,
    amount_cents: int,
    description: str,
    status: str,
    requires_mfa: bool,
    created_at: str,
    expires_at: str | None,
    reference: str | None,
    completed_at: str | None = None,
) -> Transfer:
    transfer_id = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO transfer
           (id, reference, from_kind, to_kind, amount_cents, description,
            status, requires_mfa, created_at, expires_at, completed_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            transfer_id,
            reference,
            from_kind,
            to_kind,
            amount_cents,
            description,
            status,
            1 if requires_mfa else 0,
            created_at,
            expires_at,
            completed_at,
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM transfer WHERE id = ?", (transfer_id,)).fetchone()
    return _row_to_transfer(row)


def get_transfer_by_reference(conn: sqlite3.Connection, reference: str) -> Transfer | None:
    row = conn.execute(
        "SELECT * FROM transfer WHERE reference = ?", (reference,)
    ).fetchone()
    return _row_to_transfer(row) if row else None


def list_transfers(conn: sqlite3.Connection) -> list[Transfer]:
    """Historial ordenado por fecha de creación descendente (Requisito 5.1)."""
    rows = conn.execute(
        "SELECT * FROM transfer ORDER BY created_at DESC, rowid DESC"
    ).fetchall()
    return [_row_to_transfer(r) for r in rows]


def update_transfer_status(
    conn: sqlite3.Connection,
    transfer_id: str,
    status: str,
    *,
    completed_at: str | None = None,
) -> None:
    conn.execute(
        "UPDATE transfer SET status = ?, completed_at = ? WHERE id = ?",
        (status, completed_at, transfer_id),
    )
    conn.commit()


def apply_transfer(
    conn: sqlite3.Connection,
    *,
    transfer_id: str,
    from_kind: str,
    to_kind: str,
    amount_cents: int,
    completed_at: str,
) -> None:
    """Aplica el movimiento de saldos y marca COMPLETED de forma atómica (Requisito 7.4).

    Todo ocurre dentro de una única transacción (BEGIN IMMEDIATE ... COMMIT): se descuenta
    del origen, se abona al destino y se actualiza el estado; o no se aplica nada.
    """
    try:
        conn.execute("BEGIN IMMEDIATE")
        apply_transfer_in_tx(
            conn,
            transfer_id=transfer_id,
            from_kind=from_kind,
            to_kind=to_kind,
            amount_cents=amount_cents,
            completed_at=completed_at,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def apply_transfer_in_tx(
    conn: sqlite3.Connection,
    *,
    transfer_id: str,
    from_kind: str,
    to_kind: str,
    amount_cents: int,
    completed_at: str,
) -> None:
    """Movimiento de saldos + COMPLETED SIN gestionar la transacción (Etapa 2, Tarea 16).

    Ejecuta las mismas sentencias que `apply_transfer` pero NO abre ni cierra transacción: el
    llamador debe invocarla dentro de una transacción activa (p. ej. `financial_transaction`),
    de modo que la verificación de límites/consumo y el débito queden en la MISMA transacción
    atómica (F8/F9). `apply_transfer` se conserva para el comportamiento heredado.
    """
    conn.execute(
        "UPDATE account SET balance_cents = balance_cents - ? WHERE kind = ?",
        (amount_cents, from_kind),
    )
    conn.execute(
        "UPDATE account SET balance_cents = balance_cents + ? WHERE kind = ?",
        (amount_cents, to_kind),
    )
    conn.execute(
        "UPDATE transfer SET status = ?, completed_at = ? WHERE id = ?",
        ("COMPLETED", completed_at, transfer_id),
    )


# --- Pagos recurrentes: schedules (Etapa 2, Fase E, Tarea 27) -----------------
#
# Acceso a datos de `recurring_schedule` con SQL puro (sin ORM). La creación de un schedule es
# una operación de configuración (no mueve saldos), por lo que persiste con su propio commit,
# de forma análoga a `create_beneficiary`. La ejecución financiera de las ocurrencias (débito,
# idempotencia durable con `schedule_execution`) corresponde a tareas posteriores (30/31) y NO
# se implementa aquí.


@dataclass
class Schedule:
    id: str
    customer_id: str
    type: str
    from_kind: str
    to_kind: str | None
    beneficiary_id: str | None
    beneficiary_snapshot: str | None
    amount_cents: int
    description: str
    frequency: str
    status: str
    requires_mfa: int
    authorized: int
    next_run_at: str
    created_at: str


def _row_to_schedule(row: sqlite3.Row) -> Schedule:
    return Schedule(
        id=row["id"],
        customer_id=row["customer_id"],
        type=row["type"],
        from_kind=row["from_kind"],
        to_kind=row["to_kind"],
        beneficiary_id=row["beneficiary_id"],
        beneficiary_snapshot=row["beneficiary_snapshot"],
        amount_cents=row["amount_cents"],
        description=row["description"],
        frequency=row["frequency"],
        status=row["status"],
        requires_mfa=row["requires_mfa"],
        authorized=row["authorized"],
        next_run_at=row["next_run_at"],
        created_at=row["created_at"],
    )


def create_schedule(
    conn: sqlite3.Connection,
    *,
    customer_id: str,
    type: str,
    from_kind: str,
    to_kind: str | None,
    beneficiary_id: str | None,
    beneficiary_snapshot: str | None,
    amount_cents: int,
    description: str,
    frequency: str,
    status: str,
    requires_mfa: bool,
    authorized: bool,
    next_run_at: str,
    created_at: str,
) -> Schedule:
    """Inserta un `recurring_schedule` y devuelve la fila creada (con su propio commit).

    No aplica ningún movimiento de saldo: crear un schedule es configuración, no una
    transferencia. El `beneficiary_snapshot` (JSON) se conserva para ACH, de modo que el
    schedule siga siendo ejecutable aunque el beneficiario guardado se elimine después (REC-11).
    """
    schedule_id = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO recurring_schedule
           (id, customer_id, type, from_kind, to_kind, beneficiary_id, beneficiary_snapshot,
            amount_cents, description, frequency, status, requires_mfa, authorized,
            next_run_at, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            schedule_id,
            customer_id,
            type,
            from_kind,
            to_kind,
            beneficiary_id,
            beneficiary_snapshot,
            amount_cents,
            description,
            frequency,
            status,
            1 if requires_mfa else 0,
            1 if authorized else 0,
            next_run_at,
            created_at,
        ),
    )
    conn.commit()
    row = conn.execute(
        _SELECT_SCHEDULE_BY_ID, (schedule_id,)
    ).fetchone()
    return _row_to_schedule(row)


def get_schedule(conn: sqlite3.Connection, schedule_id: str) -> Schedule | None:
    row = conn.execute(
        _SELECT_SCHEDULE_BY_ID, (schedule_id,)
    ).fetchone()
    return _row_to_schedule(row) if row else None


def list_due_schedules(conn: sqlite3.Connection, now_iso: str) -> list[Schedule]:
    """Schedules elegibles para ejecución automática (Tarea 30, Req. 10.1/10.4).

    Selecciona SOLO los `active` y `authorized=1` cuyo `next_run_at <= now`. Un schedule
    `paused`/`cancelled` nunca se ejecuta (Req. 9.5), y un schedule sensible no autorizado
    tampoco (nunca debe correr sin la autorización concedida en creación, Req. 11.4). El orden
    por `next_run_at` es determinista y aprovecha `idx_schedule_due`.
    """
    rows = conn.execute(
        """SELECT * FROM recurring_schedule
           WHERE status = 'active' AND authorized = 1 AND next_run_at <= ?
           ORDER BY next_run_at, id""",
        (now_iso,),
    ).fetchall()
    return [_row_to_schedule(r) for r in rows]


# --- Pagos recurrentes: ejecución durable de ocurrencias (Tarea 30) -----------
#
# Helpers SIN commit, pensados para componerse DENTRO de `financial_transaction` (una sola
# transacción `BEGIN IMMEDIATE` por ocurrencia). El llamador es dueño de la transacción; estos
# helpers nunca hacen `commit`/`rollback` (a diferencia de `create_schedule`/
# `update_schedule_status`, que sí commitean y por tanto NO deben usarse dentro de la
# transacción financiera).


def insert_schedule_execution_no_commit(
    conn: sqlite3.Connection,
    *,
    execution_id: str,
    schedule_id: str,
    due_at: str,
    outcome: str,
    transfer_id: str | None,
    created_at: str,
) -> None:
    """Inserta la fila `schedule_execution` SIN commit (idempotencia durable, DD-7/F10).

    La restricción `UNIQUE(schedule_id, due_at)` rechaza cualquier segundo intento de ejecutar la
    MISMA ocurrencia (reintento, tick solapado, re-ejecución tras crash con la fecha aún sin
    avanzar): el `INSERT` lanza `sqlite3.IntegrityError` y aborta la transacción sin repetir el
    efecto financiero. `due_at` es la identidad de la ocurrencia (el vencimiento original), no el
    instante de ejecución.
    """
    conn.execute(
        """INSERT INTO schedule_execution
           (id, schedule_id, due_at, outcome, transfer_id, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (execution_id, schedule_id, due_at, outcome, transfer_id, created_at),
    )


def create_internal_transfer_no_commit(
    conn: sqlite3.Connection,
    *,
    transfer_id: str,
    from_kind: str,
    to_kind: str,
    amount_cents: int,
    description: str,
    status: str,
    created_at: str,
    completed_at: str | None,
    schedule_id: str | None,
) -> None:
    """Inserta una fila de transferencia interna SIN commit (Tarea 30).

    Replica las columnas que `create_transfer` fija para una interna (misma semántica de Etapa
    1/2: `type='internal'`, `requires_mfa=0`, `reference=NULL`), añadiendo `schedule_id` para
    trazar la ocurrencia recurrente que la originó. NO gestiona la transacción: se compone con el
    débito/crédito dentro de la misma `financial_transaction`.
    """
    conn.execute(
        """INSERT INTO transfer
           (id, reference, from_kind, to_kind, amount_cents, description, status, requires_mfa,
            created_at, expires_at, completed_at, type, beneficiary_id, beneficiary_snapshot,
            settled_at, refunded, schedule_id)
           VALUES (?, NULL, ?, ?, ?, ?, ?, 0, ?, NULL, ?, 'internal', NULL, NULL, NULL, 0, ?)""",
        (
            transfer_id, from_kind, to_kind, amount_cents, description, status,
            created_at, completed_at, schedule_id,
        ),
    )


def set_execution_transfer_id_no_commit(
    conn: sqlite3.Connection, execution_id: str, transfer_id: str
) -> None:
    """Enlaza la fila de ejecución con su movimiento SIN commit (Tarea 30).

    La fila `schedule_execution` se inserta PRIMERO (con `transfer_id=NULL`) para que la
    `UNIQUE(schedule_id, due_at)` actúe como guarda de idempotencia antes de cualquier efecto
    financiero; una vez creado el movimiento dentro de la MISMA transacción, se enlaza aquí. Esto
    respeta la FK `schedule_execution.transfer_id → transfer.id` (el movimiento ya existe).
    """
    conn.execute(
        "UPDATE schedule_execution SET transfer_id = ? WHERE id = ?",
        (transfer_id, execution_id),
    )


def advance_schedule_next_run_in_tx(
    conn: sqlite3.Connection, schedule_id: str, next_run_at: str
) -> None:
    """Avanza `next_run_at` del schedule SIN commit (Tarea 30).

    Variante transaccional de la actualización de fecha: no abre ni cierra transacción (a
    diferencia de `update_schedule_status`, que commitea). Se usa dentro de la transacción
    financiera de la ocurrencia, de modo que el avance de fecha, la fila de ejecución y el
    movimiento se confirmen o se reviertan juntos (F10).
    """
    conn.execute(
        "UPDATE recurring_schedule SET next_run_at = ? WHERE id = ?",
        (next_run_at, schedule_id),
    )


def list_schedules(conn: sqlite3.Connection, customer_id: str) -> list[Schedule]:
    """Lista los schedules del cliente (propiedad: filtra por `customer_id`)."""
    rows = conn.execute(
        "SELECT * FROM recurring_schedule WHERE customer_id = ? ORDER BY created_at",
        (customer_id,),
    ).fetchall()
    return [_row_to_schedule(r) for r in rows]


# --- Pagos recurrentes: ciclo de vida (Etapa 2, Fase E, Tarea 29) -------------
#
# Transiciones de estado del schedule (pausar/reanudar/cancelar). Son operaciones de
# configuración (no mueven saldos), por lo que persisten con su propio commit, igual que
# `create_schedule`. La reanudación sin catch-up (D06) recalcula `next_run_at` en el servicio;
# aquí solo se persiste el nuevo estado y, opcionalmente, el nuevo `next_run_at`.


def update_schedule_status(
    conn: sqlite3.Connection,
    schedule_id: str,
    status: str,
    *,
    next_run_at: str | None = None,
) -> Schedule:
    """Actualiza el estado del schedule y, opcionalmente, su `next_run_at` (con su commit).

    Cuando `next_run_at` es `None` se conserva el valor existente (pausar/cancelar no recalculan
    fechas); al reanudar, el servicio pasa el `next_run_at` recalculado desde la reanudación
    (D06). Devuelve la fila actualizada.
    """
    if next_run_at is None:
        conn.execute(
            "UPDATE recurring_schedule SET status = ? WHERE id = ?",
            (status, schedule_id),
        )
    else:
        conn.execute(
            "UPDATE recurring_schedule SET status = ?, next_run_at = ? WHERE id = ?",
            (status, next_run_at, schedule_id),
        )
    conn.commit()
    row = conn.execute(
        _SELECT_SCHEDULE_BY_ID, (schedule_id,)
    ).fetchone()
    return _row_to_schedule(row)
