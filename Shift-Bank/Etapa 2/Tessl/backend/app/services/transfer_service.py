from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from backend.app.models import Transfer, Transaction
from backend.app.schemas import TransferRequest
from backend.app.services import account_service, mfa_service

SENSITIVE_THRESHOLD = 1000.00


class MfaRequiredException(Exception):
    """Exception raised when an internal transfer exceeds threshold without PIN."""

    def __init__(
        self,
        detail: str = "MFA_REQUIRED",
        message: str = "Security PIN required for transfers over $1,000",
    ):
        self.detail = detail
        self.message = message


def execute_transfer(
    db: Session,
    user_id: int,
    request: TransferRequest,
) -> Transfer:
    """
    Executes an internal transfer between the authenticated user's accounts.
    Validates accounts, balances, and MFA PIN for sensitive transfers (> $1,000.00).
    """
    if request.from_account_id == request.to_account_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot transfer to the same account",
        )

    # Verify both accounts exist and belong to the user
    from_acc = account_service.get_account_by_id(db, request.from_account_id, user_id)
    to_acc = account_service.get_account_by_id(db, request.to_account_id, user_id)

    # Check sufficient funds
    if round(from_acc.balance, 2) < round(request.amount, 2):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient funds in source account",
        )

    # Check sensitive transfer MFA trigger
    if request.amount > SENSITIVE_THRESHOLD:
        if not request.pin or not request.pin.strip():
            raise MfaRequiredException()
        # Verify PIN (will raise 400 or 423 if invalid or locked)
        mfa_service.verify_pin(db, user_id, request.pin.strip())

    # Execute atomic transfer
    now = datetime.now(timezone.utc)
    from_acc.balance = round(from_acc.balance - request.amount, 2)
    to_acc.balance = round(to_acc.balance + request.amount, 2)

    transfer = Transfer(
        from_account_id=from_acc.id,
        to_account_id=to_acc.id,
        amount=round(request.amount, 2),
        status="completed",
        description=request.description or f"Transfer from {from_acc.account_name} to {to_acc.account_name}",
        created_at=now,
    )
    db.add(transfer)
    db.flush()

    # Create debit transaction for sender
    debit_desc = request.description or f"Transfer to {to_acc.account_name}"
    debit_tx = Transaction(
        account_id=from_acc.id,
        transfer_id=transfer.id,
        transaction_type="debit",
        amount=round(request.amount, 2),
        balance_after=from_acc.balance,
        description=debit_desc,
        reference=f"TRF-{transfer.id:05d}-OUT",
        created_at=now,
    )

    # Create credit transaction for recipient
    credit_desc = request.description or f"Transfer from {from_acc.account_name}"
    credit_tx = Transaction(
        account_id=to_acc.id,
        transfer_id=transfer.id,
        transaction_type="credit",
        amount=round(request.amount, 2),
        balance_after=to_acc.balance,
        description=credit_desc,
        reference=f"TRF-{transfer.id:05d}-IN",
        created_at=now,
    )

    db.add_all([debit_tx, credit_tx])
    db.commit()
    db.refresh(transfer)
    return transfer
