"""Reglas de negocio de transferencias ACH (Etapa 2, Fase D: Tareas 21–24).

Ciclo de vida ACH (minúsculas, D03): `pending_auth` (no financiero, sin débito) para sensibles
pendientes de MFA → `pending` (financieramente activo, con débito inmediato) → `settled` |
`failed` (reembolso exactamente-una-vez).

Orden de comprobaciones (D04, LIM-07): formato → fondos → límites → (si sensible) MFA. Un PIN
correcto nunca salta límites ni fondos. La creación de la fila `pending` y el débito ocurren en
UNA sola transacción financiera (punto 4; NO se reproduce el patrón interno de
commit-antes-del-efecto).

Settlement y fallo son disparados por el scheduler de fondo (Tarea 32); aquí se implementa la
LÓGICA, no su disparo autónomo (T-6). La condición de settlement usa un reloj inyectable y un
retardo configurable (simulación determinista).

_Requisitos: 1–7_ · _Contrato: ACH-01..10_ · _Decisión: D03, D04, D05_
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from . import ach_repository, beneficiaries, clock, limit_service
from .config import MFA_CODE, MFA_THRESHOLD, MFA_TTL_SECONDS
from .money import InvalidAmountError, decimal_to_cents, parse_amount
from .txn import financial_transaction

# Retardo de liquidación simulado (determinista; evaluado con reloj inyectable).
ACH_SETTLEMENT_DELAY_SECONDS = 60


class AchError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class AchCreateResult:
    status: str          # 'pending' | 'pending_auth'
    mfa_required: bool
    reference: str
    expires_at: str | None


def _customer_id(conn: sqlite3.Connection) -> str:
    row = conn.execute("SELECT id FROM customer LIMIT 1").fetchone()
    if row is None:
        raise AchError("NOT_FOUND", "Cliente no encontrado")
    return row["id"]


def _resolve_beneficiary(conn: sqlite3.Connection, customer_id: str, *, beneficiary_id, adhoc):
    """Devuelve (beneficiary_id | None, snapshot dict) a partir de guardado o ad hoc.

    Valida el formato en ambos casos. Para guardado, exige propiedad del cliente (ACH-02).
    """
    if beneficiary_id:
        row = ach_repository.get_beneficiary(conn, customer_id, beneficiary_id)
        if row is None:
            raise AchError("NOT_FOUND", "Beneficiario no encontrado")
        snap = {
            "name": row["name"], "bank": row["bank"],
            "routing_number": row["routing_number"], "account_number": row["account_number"],
        }
        return beneficiary_id, snap
    if adhoc:
        beneficiaries.validate_fields(
            name=adhoc.get("name", ""), bank=adhoc.get("bank", ""),
            routing_number=adhoc.get("routing_number", ""),
            account_number=adhoc.get("account_number", ""),
        )
        snap = {
            "name": adhoc["name"], "bank": adhoc["bank"],
            "routing_number": adhoc["routing_number"], "account_number": adhoc["account_number"],
        }
        return None, snap
    raise AchError("INVALID_BENEFICIARY", "Debe indicar un beneficiario guardado o ad hoc")


def create_ach(conn: sqlite3.Connection, *, amount_raw: str, description: str,
               from_kind: str = "checking", beneficiary_id: str | None = None,
               adhoc: dict | None = None, save_adhoc: bool = False) -> AchCreateResult:
    """Crea/autoriza una transferencia ACH (Tarea 21/22)."""
    customer_id = _customer_id(conn)

    # Resolver y validar el beneficiario (formato; propiedad si es guardado).
    resolved_bid, snapshot = _resolve_beneficiary(
        conn, customer_id, beneficiary_id=beneficiary_id, adhoc=adhoc)

    # Validar monto (positivo, <=2 decimales) — Req. 3.1/3.8.
    try:
        amount = parse_amount(amount_raw)
    except InvalidAmountError as exc:
        raise AchError("INVALID_AMOUNT", str(exc)) from exc
    if amount <= 0:
        raise AchError("NON_POSITIVE_AMOUNT", "El monto debe ser mayor que cero")
    try:
        amount_cents = decimal_to_cents(amount)
    except InvalidAmountError as exc:
        raise AchError("INVALID_AMOUNT", str(exc)) from exc

    # Fondos (Req. 3.1) — pre-chequeo; se revalida en la transacción.
    source = conn.execute(
        "SELECT balance_cents FROM account WHERE kind = ?", (from_kind,)).fetchone()
    if source is None:
        raise AchError("NOT_FOUND", "Cuenta de origen desconocida")
    if amount_cents > source["balance_cents"]:
        raise AchError("INSUFFICIENT_FUNDS", "Fondos insuficientes en la cuenta de origen")

    # Límites antes de MFA (LIM-07) — pre-chequeo; se revalida en la transacción.
    now = clock.system_clock.now_utc()
    try:
        limit_service.check(conn, amount_cents, now)
    except limit_service.LimitError as exc:
        raise AchError(exc.code, exc.message) from exc

    # Opción de guardar un ad hoc como beneficiario reutilizable (Req. 1.3).
    if adhoc and save_adhoc and resolved_bid is None:
        resolved_bid = ach_repository.create_beneficiary(
            conn, customer_id=customer_id, name=snapshot["name"], bank=snapshot["bank"],
            routing_number=snapshot["routing_number"], account_number=snapshot["account_number"],
            created_at=clock.iso(now))

    reference = uuid.uuid4().hex
    snapshot_json = json.dumps(snapshot)
    requires_mfa = amount >= MFA_THRESHOLD

    if requires_mfa:
        # Sensible: crear `pending_auth` SIN débito (F3, Req. 3.6). No se compone con débito.
        expires_at = clock.iso(now + timedelta(seconds=MFA_TTL_SECONDS))
        with financial_transaction(conn):
            ach_repository.create_ach_no_commit(
                conn, transfer_id=str(uuid.uuid4()), reference=reference, from_kind=from_kind,
                amount_cents=amount_cents, description=description, status="pending_auth",
                requires_mfa=True, created_at=clock.iso(now), expires_at=expires_at,
                beneficiary_id=resolved_bid, beneficiary_snapshot=snapshot_json)
        return AchCreateResult(status="pending_auth", mfa_required=True,
                               reference=reference, expires_at=expires_at)

    # No sensible: crear `pending` + débito en UNA transacción (punto 4; revalida límites/fondos).
    with financial_transaction(conn):
        _revalidate(conn, from_kind, amount_cents, now)
        ach_repository.create_ach_no_commit(
            conn, transfer_id=str(uuid.uuid4()), reference=reference, from_kind=from_kind,
            amount_cents=amount_cents, description=description, status="pending",
            requires_mfa=False, created_at=clock.iso(now), expires_at=None,
            beneficiary_id=resolved_bid, beneficiary_snapshot=snapshot_json)
        ach_repository.debit_source_no_commit(conn, from_kind=from_kind, amount_cents=amount_cents)
    return AchCreateResult(status="pending", mfa_required=False,
                           reference=reference, expires_at=None)


def _revalidate(conn: sqlite3.Connection, from_kind: str, amount_cents: int, now) -> None:
    """Revalida fondos y límites DENTRO de la transacción (F8/F9). Lanza AchError si falla."""
    src = conn.execute(
        "SELECT balance_cents FROM account WHERE kind = ?", (from_kind,)).fetchone()
    if src is None or amount_cents > src["balance_cents"]:
        raise AchError("INSUFFICIENT_FUNDS", "Fondos insuficientes en la cuenta de origen")
    try:
        limit_service.check(conn, amount_cents, now)
    except limit_service.LimitError as exc:
        raise AchError(exc.code, exc.message) from exc


def confirm_ach_mfa(conn: sqlite3.Connection, *, reference: str, code: str) -> str:
    """Confirma la MFA de una ACH `pending_auth`: la pasa a `pending` + débito (Tarea 22)."""
    row = ach_repository.get_ach_by_reference(conn, reference)
    if row is None:
        raise AchError("NOT_FOUND", "Referencia ACH inexistente")

    status = row["status"]
    now = clock.system_clock.now_utc()

    # Expiración perezosa del `pending_auth` (misma ventana MFA heredada).
    if status == "pending_auth" and row["expires_at"] is not None:
        if now > clock.parse_iso(row["expires_at"]):
            ach_repository.set_ach_status_no_commit(conn, transfer_id=row["id"], status="expired")
            conn.commit()
            raise AchError("EXPIRED", "La autorización ACH expiró")

    if status != "pending_auth":
        raise AchError("EXPIRED", f"La ACH no está pendiente de autorización (estado {status})")

    if code != MFA_CODE:
        raise AchError("INVALID_MFA_CODE", "Código MFA incorrecto")

    # Código correcto: revalidar fondos+límites y activar (pending + débito) en una transacción.
    from_kind = row["from_kind"]
    amount_cents = row["amount_cents"]
    try:
        with financial_transaction(conn):
            _revalidate(conn, from_kind, amount_cents, now)
            ach_repository.set_ach_status_no_commit(conn, transfer_id=row["id"], status="pending")
            ach_repository.debit_source_no_commit(conn, from_kind=from_kind, amount_cents=amount_cents)
    except AchError:
        # Fondos/límite insuficientes al confirmar → marcar failed (sin débito: no se aplicó).
        ach_repository.set_ach_status_no_commit(conn, transfer_id=row["id"], status="failed")
        conn.commit()
        raise
    return "pending"


def settle_ach(conn: sqlite3.Connection, transfer_id: str, *, now: datetime) -> bool:
    """Liquida una ACH elegible (`pending` cuyo retardo de simulación venció). Idempotente.

    Devuelve True si transicionó `pending → settled`. La elegibilidad es determinista (reloj
    inyectable). Disparo autónomo: Tarea 32 (scheduler); aquí solo la lógica (T-6).
    """
    row = ach_repository.get_ach_by_id(conn, transfer_id)
    if row is None or row["status"] != "pending":
        return False
    full = conn.execute("SELECT created_at FROM transfer WHERE id = ?", (transfer_id,)).fetchone()
    created = clock.parse_iso(full["created_at"])
    if now < created + timedelta(seconds=ACH_SETTLEMENT_DELAY_SECONDS):
        return False  # aún no elegible
    with financial_transaction(conn):
        affected = ach_repository.settle_ach_no_commit(
            conn, transfer_id=transfer_id, settled_at=clock.iso(now))
    return affected == 1


def fail_ach(conn: sqlite3.Connection, transfer_id: str) -> bool:
    """Marca `failed` una ACH `pending` y reembolsa exactamente-una-vez. Idempotente.

    Devuelve True si transicionó. Disparo: regla de simulación / gancho solo-de-test o scheduler
    (Tarea 32); aquí la lógica (T-6).
    """
    row = ach_repository.get_ach_by_id(conn, transfer_id)
    if row is None or row["status"] != "pending":
        return False
    with financial_transaction(conn):
        affected = ach_repository.fail_and_refund_no_commit(
            conn, transfer_id=transfer_id, from_kind=row["from_kind"],
            amount_cents=row["amount_cents"])
    return affected == 1
