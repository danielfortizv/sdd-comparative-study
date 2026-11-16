"""Reglas de negocio: validaciones, umbral de MFA, máquina de estados y expiración.

Única autoridad de negocio (Requisitos 3, 6, 7, 8). Lanza `DomainError` tipado que los
routers mapean a códigos HTTP. Las comparaciones de fondos se hacen en centavos enteros.
"""

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from . import limit_service, repository
from .config import MFA_CODE, MFA_THRESHOLD, MFA_TTL_SECONDS
from .money import InvalidAmountError, decimal_to_cents, parse_amount
from .txn import financial_transaction

_VALID_KINDS = {"checking", "savings"}


class DomainError(Exception):
    """Error de dominio con un `code` estable para el mapeo a HTTP."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class CreateResult:
    status: str
    requires_mfa: bool
    reference: str | None
    expires_at: str | None


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


# --- Creación de transferencia (Tareas 8 y 9) ---------------------------------

def create_transfer(
    conn: sqlite3.Connection,
    *,
    from_kind: str,
    to_kind: str,
    amount_raw: str,
    description: str,
) -> CreateResult:
    """Valida y crea una transferencia; ejecuta directo o deja PENDING_MFA según el umbral."""
    # Restringir a las dos cuentas propias (Requisito 3.1, 3.6).
    if from_kind not in _VALID_KINDS or to_kind not in _VALID_KINDS:
        raise DomainError("NOT_FOUND", "Cuenta desconocida")

    # Misma cuenta (Requisito 3.2).
    if from_kind == to_kind:
        raise DomainError("SAME_ACCOUNT", "El origen y el destino no pueden ser la misma cuenta")

    # Monto válido / decimal-safe (Requisito 3.5).
    try:
        amount = parse_amount(amount_raw)
    except InvalidAmountError as exc:
        raise DomainError("INVALID_AMOUNT", str(exc)) from exc

    # Monto <= 0 (Requisito 3.3).
    if amount <= 0:
        raise DomainError("NON_POSITIVE_AMOUNT", "El monto debe ser mayor que cero")

    try:
        amount_cents = decimal_to_cents(amount)
    except InvalidAmountError as exc:
        raise DomainError("INVALID_AMOUNT", str(exc)) from exc

    source = repository.get_account(conn, from_kind)
    if source is None:
        raise DomainError("NOT_FOUND", "Cuenta de origen desconocida")

    # Fondos insuficientes al crear (Requisito 3.4).
    if amount_cents > source.balance_cents:
        raise DomainError("INSUFFICIENT_FUNDS", "Fondos insuficientes en la cuenta de origen")

    now = _now_utc()
    requires_mfa = amount >= MFA_THRESHOLD

    # Límites: feedback temprano (no autoritativo) antes de crear/MFA. La verificación
    # autoritativa se repite dentro de la transacción financiera (F8/F9, LIM-07). El orden es
    # fondos → límites → (si aplica) MFA (Requisito 14.5, D04).
    try:
        limit_service.check(conn, amount_cents, now)
    except limit_service.LimitError as exc:
        raise DomainError(exc.code, exc.message) from exc

    if not requires_mfa:
        # Ejecución inmediata (Requisito 6.1): crear la fila y, dentro de UNA transacción
        # financiera, revalidar límites y aplicar saldos atómicamente (F8/F9).
        created = repository.create_transfer(
            conn,
            from_kind=from_kind,
            to_kind=to_kind,
            amount_cents=amount_cents,
            description=description,
            status="PENDING_MFA",  # estado transitorio; se consolida al aplicar
            requires_mfa=False,
            created_at=_iso(now),
            expires_at=None,
            reference=None,
        )
        try:
            with financial_transaction(conn):
                # Revalidación autoritativa de límites + débito en la misma transacción.
                limit_service.check(conn, amount_cents, now)
                repository.apply_transfer_in_tx(
                    conn,
                    transfer_id=created.id,
                    from_kind=from_kind,
                    to_kind=to_kind,
                    amount_cents=amount_cents,
                    completed_at=_iso(now),
                )
        except limit_service.LimitError as exc:
            # El límite se superó entre el pre-chequeo y la transacción; no se debitó.
            repository.update_transfer_status(conn, created.id, "FAILED")
            raise DomainError(exc.code, exc.message) from exc
        return CreateResult(status="COMPLETED", requires_mfa=False, reference=None, expires_at=None)

    # Monto >= umbral (Requisito 6.2, 6.3, 6.4): crear PENDING_MFA sin tocar saldos.
    reference = uuid.uuid4().hex
    expires_at = _iso(now + timedelta(seconds=MFA_TTL_SECONDS))
    repository.create_transfer(
        conn,
        from_kind=from_kind,
        to_kind=to_kind,
        amount_cents=amount_cents,
        description=description,
        status="PENDING_MFA",
        requires_mfa=True,
        created_at=_iso(now),
        expires_at=expires_at,
        reference=reference,
    )
    return CreateResult(
        status="PENDING_MFA",
        requires_mfa=True,
        reference=reference,
        expires_at=expires_at,
    )


# --- Expiración perezosa (Tarea 10) -------------------------------------------

def _expire_if_needed(conn: sqlite3.Connection, transfer: repository.Transfer) -> repository.Transfer:
    """Si está PENDING_MFA y venció la ventana, marca EXPIRED y persiste (Requisito 8.2)."""
    if transfer.status == "PENDING_MFA" and transfer.expires_at is not None:
        if _now_utc() > _parse_iso(transfer.expires_at):
            repository.update_transfer_status(conn, transfer.id, "EXPIRED")
            transfer.status = "EXPIRED"
    return transfer


# --- Confirmación de MFA (Tarea 11) -------------------------------------------

def confirm_mfa(conn: sqlite3.Connection, *, reference: str, code: str) -> str:
    """Confirma una transferencia PENDING_MFA. Devuelve el estado final o lanza DomainError."""
    transfer = repository.get_transfer_by_reference(conn, reference)
    if transfer is None:
        raise DomainError("NOT_FOUND", "Referencia de transferencia inexistente")

    # Evaluar expiración perezosa antes de cualquier otra decisión (Requisito 8.3).
    transfer = _expire_if_needed(conn, transfer)

    if transfer.status == "EXPIRED":
        raise DomainError("EXPIRED", "La transferencia expiró y no puede completarse")

    # Estados terminales distintos de PENDING_MFA no se pueden confirmar.
    if transfer.status != "PENDING_MFA":
        raise DomainError("EXPIRED", f"La transferencia no está pendiente (estado {transfer.status})")

    # Código incorrecto: sigue PENDING_MFA, permite reintento, sin lockout (Requisito 7.2, 7.5).
    if code != MFA_CODE:
        raise DomainError("INVALID_MFA_CODE", "Código MFA incorrecto")

    # Código correcto: re-verificar fondos (Requisito 8.4).
    source = repository.get_account(conn, transfer.from_kind)
    if source is None or transfer.amount_cents > source.balance_cents:
        repository.update_transfer_status(conn, transfer.id, "FAILED")
        raise DomainError("INSUFFICIENT_FUNDS", "Fondos insuficientes al confirmar la transferencia")

    # Correcto, válida y con fondos: verificar límites y aplicar saldos en la MISMA transacción
    # financiera (LIM-07, A14: el límite se comprueba antes de completar; un PIN correcto nunca
    # salta un límite). Si el límite se supera, marca FAILED sin débito.
    now = _now_utc()
    try:
        with financial_transaction(conn):
            limit_service.check(conn, transfer.amount_cents, now)
            repository.apply_transfer_in_tx(
                conn,
                transfer_id=transfer.id,
                from_kind=transfer.from_kind,
                to_kind=transfer.to_kind,
                amount_cents=transfer.amount_cents,
                completed_at=_iso(now),
            )
    except limit_service.LimitError as exc:
        repository.update_transfer_status(conn, transfer.id, "FAILED")
        raise DomainError(exc.code, exc.message) from exc
    return "COMPLETED"


# --- Lectura del historial (apoya Tarea 14 / Requisito 5) ---------------------

def list_history(conn: sqlite3.Connection) -> list[repository.Transfer]:
    """Lista el historial aplicando expiración perezosa a los pendientes vencidos."""
    transfers = repository.list_transfers(conn)
    return [_expire_if_needed(conn, t) for t in transfers]
