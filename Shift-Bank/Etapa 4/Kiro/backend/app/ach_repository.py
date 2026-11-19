"""Acceso a datos para beneficiarios y transferencias ACH (Etapa 2, Fase D).

SQL puro sobre la conexión heredada (sin ORM). Las mutaciones financieras ACH se exponen como
operaciones SIN commit, pensadas para componerse dentro de `financial_transaction` (punto 4:
creación de la fila ACH + débito en una única transacción; NO se reproduce el patrón interno de
commit-antes-del-efecto-financiero).

Montos en centavos enteros; fechas ISO-8601 UTC.
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass

from . import crypto


@dataclass
class Beneficiary:
    id: str
    name: str
    bank: str
    routing_number: str
    account_number: str


# --- Beneficiarios (Tarea 19) --------------------------------------------------

def create_beneficiary_no_commit(conn: sqlite3.Connection, *, customer_id: str, name: str,
                                 bank: str, routing_number: str, account_number: str,
                                 created_at: str) -> str:
    """Inserta un beneficiario SIN commit (se compone en la transacción del llamador).

    Variante sin commit añadida en la Etapa 3 (Tarea 13, design.md §2.7): el router de
    beneficiarios la compone DENTRO de una `financial_transaction` junto con el `append` de
    auditoría `BENEFICIARY_CREATED`, de modo que la fila y su rastro de auditoría se confirmen
    atómicamente (R5.2) y un fallo de auditoría revierta también el alta (fail-closed, R7.2).

    Cifrado en reposo (Tarea 7, design.md §1.5): los identificadores bancarios sensibles
    (routing/cuenta) se almacenan SOLO como tokens `enc:v1:...`. `name`/`bank` NO son
    identificadores sensibles según D-E3-01 y se dejan en claro (límite de alcance).
    """
    bid = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO beneficiary
           (id, customer_id, name, bank, routing_number, account_number, created_at, deleted_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, NULL)""",
        (bid, customer_id, name, bank,
         crypto.encrypt(routing_number), crypto.encrypt(account_number), created_at),
    )
    return bid


def create_beneficiary(conn: sqlite3.Connection, *, customer_id: str, name: str, bank: str,
                       routing_number: str, account_number: str, created_at: str) -> str:
    """Crea un beneficiario CON su propio commit (variante heredada autocontenida).

    La usa la ruta `ach_service.create_ach` (save_adhoc), donde el alta del beneficiario ocurre
    ANTES de abrir la `financial_transaction` de la ACH (no hay anidamiento). En esa ruta el
    evento `ACH_*` ya cubre la operación, por lo que NO se emite `BENEFICIARY_CREATED` (decisión
    documentada en Tarea 13: el alta de beneficiario se audita solo en el `POST /api/beneficiaries`
    explícito). El alta explícita del router usa `create_beneficiary_no_commit` + auditoría atómica.
    """
    bid = create_beneficiary_no_commit(
        conn, customer_id=customer_id, name=name, bank=bank,
        routing_number=routing_number, account_number=account_number, created_at=created_at)
    conn.commit()
    return bid


def _decrypt_beneficiary_row(row: sqlite3.Row) -> dict:
    """Descifra routing/cuenta de una fila `beneficiary` y devuelve un dict en claro.

    Cifrado en reposo (Tarea 7, design.md §1.5): las columnas sensibles se guardan como tokens
    `enc:v1:...`. La capa de servicio y `beneficiaries.public_view` siguen operando sobre texto
    en claro, por lo que el descifrado ocurre aquí, en el borde de E/S del repositorio. Se
    devuelve un `dict` (acceso por clave idéntico al de `sqlite3.Row` para los llamadores).
    """
    return {
        "id": row["id"],
        "name": row["name"],
        "bank": row["bank"],
        "routing_number": crypto.decrypt(row["routing_number"]),
        "account_number": crypto.decrypt(row["account_number"]),
    }


def list_beneficiaries(conn: sqlite3.Connection, customer_id: str) -> list[dict]:
    """Lista los beneficiarios NO borrados del cliente (propiedad: filtra por customer_id).

    Descifra routing/cuenta al construir las filas de retorno (design.md §1.5).
    """
    rows = conn.execute(
        """SELECT id, name, bank, routing_number, account_number
           FROM beneficiary
           WHERE customer_id = ? AND deleted_at IS NULL
           ORDER BY created_at""",
        (customer_id,),
    ).fetchall()
    return [_decrypt_beneficiary_row(r) for r in rows]


def get_beneficiary(conn: sqlite3.Connection, customer_id: str, beneficiary_id: str):
    """Beneficiario por id, SOLO si pertenece al cliente y no está borrado (aislamiento ACH-02).

    Descifra routing/cuenta en la fila devuelta (design.md §1.5).
    """
    row = conn.execute(
        """SELECT id, name, bank, routing_number, account_number
           FROM beneficiary
           WHERE id = ? AND customer_id = ? AND deleted_at IS NULL""",
        (beneficiary_id, customer_id),
    ).fetchone()
    return _decrypt_beneficiary_row(row) if row is not None else None


def soft_delete_beneficiary_no_commit(conn: sqlite3.Connection, customer_id: str,
                                      beneficiary_id: str, deleted_at: str) -> bool:
    """Borrado lógico SIN commit; devuelve True si se marcó (del cliente y no borrado aún).

    Variante sin commit (Etapa 3, Tarea 13): el router la compone con el `append` de auditoría
    `BENEFICIARY_DELETED` dentro de UNA `financial_transaction`, de modo que la baja y su rastro
    de auditoría sean atómicos (R5.2). Devuelve si realmente transicionó, para que el router
    decida auditar solo cuando hubo cambio (una baja de un id inexistente no audita).
    """
    cur = conn.execute(
        "UPDATE beneficiary SET deleted_at = ? WHERE id = ? AND customer_id = ? AND deleted_at IS NULL",
        (deleted_at, beneficiary_id, customer_id),
    )
    return cur.rowcount > 0


def soft_delete_beneficiary(conn: sqlite3.Connection, customer_id: str, beneficiary_id: str,
                            deleted_at: str) -> bool:
    """Borrado lógico CON su propio commit (variante heredada autocontenida)."""
    ok = soft_delete_beneficiary_no_commit(conn, customer_id, beneficiary_id, deleted_at)
    conn.commit()
    return ok


# --- Transferencias ACH --------------------------------------------------------

def create_ach_no_commit(conn: sqlite3.Connection, *, transfer_id: str, reference: str,
                         from_kind: str, amount_cents: int, description: str, status: str,
                         requires_mfa: bool, created_at: str, expires_at: str | None,
                         beneficiary_id: str | None, beneficiary_snapshot: str,
                         schedule_id: str | None = None) -> None:
    """Inserta una fila ACH SIN commit (se compone en la transacción financiera, punto 4).

    `type='ach'`. El débito (cuando aplica) se ejecuta en la MISMA transacción vía
    `debit_source_no_commit`, de modo que nunca se commitea una ACH `pending` sin su débito.
    `schedule_id` (opcional) traza la ocurrencia recurrente que originó la ACH (Tarea 30); es
    `NULL` para las ACH interactivas de la Fase D (compatibilidad hacia atrás).
    """
    # Cifrado en reposo (Tarea 7, design.md §1.5): el `beneficiary_snapshot` es un JSON que
    # contiene cuenta/routing; se cifra el JSON COMPLETO como un único token `enc:v1:...` antes
    # del INSERT. El llamador siempre entrega JSON en CLARO (ruta interactiva o recurrente, donde
    # el snapshot ya se descifró al leer el schedule), de modo que aquí se cifra EXACTAMENTE una
    # vez (sin doble cifrado).
    conn.execute(
        """INSERT INTO transfer
           (id, reference, from_kind, to_kind, amount_cents, description, status, requires_mfa,
            created_at, expires_at, completed_at, type, beneficiary_id, beneficiary_snapshot,
            settled_at, refunded, schedule_id)
           VALUES (?, ?, ?, '', ?, ?, ?, ?, ?, ?, NULL, 'ach', ?, ?, NULL, 0, ?)""",
        (
            transfer_id, reference, from_kind, amount_cents, description, status,
            1 if requires_mfa else 0, created_at, expires_at, beneficiary_id,
            crypto.encrypt(beneficiary_snapshot),
            schedule_id,
        ),
    )


def debit_source_no_commit(conn: sqlite3.Connection, *, from_kind: str, amount_cents: int) -> None:
    """Debita la cuenta de origen SIN commit (uso dentro de la transacción financiera)."""
    conn.execute(
        "UPDATE account SET balance_cents = balance_cents - ? WHERE kind = ?",
        (amount_cents, from_kind),
    )


def set_ach_status_no_commit(conn: sqlite3.Connection, *, transfer_id: str, status: str,
                             settled_at: str | None = None) -> None:
    """Fija el estado ACH SIN commit."""
    conn.execute(
        "UPDATE transfer SET status = ?, settled_at = ? WHERE id = ?",
        (status, settled_at, transfer_id),
    )


def get_ach_by_reference(conn: sqlite3.Connection, reference: str):
    """ACH por referencia. Descifra `beneficiary_snapshot` en la fila devuelta (design.md §1.5).

    Devuelve un `dict` (acceso por clave idéntico al de `sqlite3.Row`) con el snapshot ya en
    claro, de modo que cualquier reutilización posterior vea JSON legible.
    """
    row = conn.execute(
        """SELECT id, reference, from_kind, amount_cents, description, status, requires_mfa,
                  created_at, expires_at, settled_at, refunded, beneficiary_snapshot
           FROM transfer WHERE reference = ? AND type = 'ach'""",
        (reference,),
    ).fetchone()
    if row is None:
        return None
    data = dict(row)
    snap = data.get("beneficiary_snapshot")
    if snap is not None:
        data["beneficiary_snapshot"] = crypto.decrypt(snap)
    return data


def get_ach_by_id(conn: sqlite3.Connection, transfer_id: str):
    return conn.execute(
        """SELECT id, reference, from_kind, amount_cents, status, refunded
           FROM transfer WHERE id = ? AND type = 'ach'""",
        (transfer_id,),
    ).fetchone()


def settle_ach_no_commit(conn: sqlite3.Connection, *, transfer_id: str, settled_at: str) -> int:
    """Transición `pending → settled` con guarda. Devuelve filas afectadas (idempotente)."""
    cur = conn.execute(
        "UPDATE transfer SET status = 'settled', settled_at = ? "
        "WHERE id = ? AND type = 'ach' AND status = 'pending'",
        (settled_at, transfer_id),
    )
    return cur.rowcount


def fail_and_refund_no_commit(conn: sqlite3.Connection, *, transfer_id: str, from_kind: str,
                              amount_cents: int) -> int:
    """Transición `pending → failed` + reembolso exactamente-una-vez (guarda `refunded=0`).

    Devuelve filas afectadas por la transición. Si la guarda no aplica (ya failed/refunded),
    devuelve 0 y NO reembolsa de nuevo. Uso dentro de la transacción financiera.
    """
    cur = conn.execute(
        "UPDATE transfer SET status = 'failed', refunded = 1 "
        "WHERE id = ? AND type = 'ach' AND status = 'pending' AND refunded = 0",
        (transfer_id,),
    )
    if cur.rowcount == 1:
        # Reembolso del monto exacto al origen (una sola vez).
        conn.execute(
            "UPDATE account SET balance_cents = balance_cents + ? WHERE kind = ?",
            (amount_cents, from_kind),
        )
    return cur.rowcount


def list_pending_ach(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """ACH en estado `pending` (para el barrido de settlement del scheduler, Tarea 32)."""
    return conn.execute(
        """SELECT id, from_kind, amount_cents, created_at
           FROM transfer WHERE type = 'ach' AND status = 'pending'"""
    ).fetchall()
