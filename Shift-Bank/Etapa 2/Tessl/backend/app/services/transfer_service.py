import re
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from backend.app.models import Transfer, Transaction, Beneficiary
from backend.app.schemas import TransferRequest, AchTransferRequest
from backend.app.services import account_service, mfa_service, limit_service

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
    Validates accounts, balances, transfer limits, and MFA PIN for sensitive transfers (> $1,000.00).
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

    # Check dynamic transfer limits (hard cap)
    limit_service.validate_transfer_limits(db, user_id, request.amount)

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
        transfer_type="internal",
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
        status="completed",
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
        status="completed",
        created_at=now,
    )

    db.add_all([debit_tx, credit_tx])
    db.commit()
    db.refresh(transfer)
    return transfer


def execute_ach_transfer(
    db: Session,
    user_id: int,
    request: AchTransferRequest,
) -> Transfer:
    """
    Executes an external ACH transfer to a beneficiary or ad-hoc account.
    Validates source account, beneficiary details, balances, limits, and MFA PIN.
    Immediately debits source balance and creates transfer in 'pending' status.
    """
    # 1. Verify source account exists and belongs to user
    from_acc = account_service.get_account_by_id(db, request.from_account_id, user_id)

    # 2. Check sufficient funds
    if round(from_acc.balance, 2) < round(request.amount, 2):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient funds in source account",
        )

    # 3. Resolve beneficiary details
    beneficiary_id = None
    if request.beneficiary_id is not None:
        beneficiary = (
            db.query(Beneficiary)
            .filter(Beneficiary.id == request.beneficiary_id, Beneficiary.user_id == user_id)
            .first()
        )
        if not beneficiary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Beneficiary with ID {request.beneficiary_id} not found",
            )
        beneficiary_id = beneficiary.id
        recipient_name = beneficiary.name
        routing_number = beneficiary.routing_number
        account_number = beneficiary.account_number
        bank_name = beneficiary.bank_name
    else:
        # Ad-hoc entry: verify all required fields are present
        if not (request.recipient_name and request.recipient_name.strip()):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Recipient name is required")
        if not (request.routing_number and request.routing_number.strip()):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Routing number is required")
        if not (request.account_number and request.account_number.strip()):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Account number is required")
        if not (request.bank_name and request.bank_name.strip()):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Bank name is required")

        recipient_name = request.recipient_name.strip()
        routing_number = request.routing_number.strip()
        account_number = request.account_number.strip()
        bank_name = request.bank_name.strip()

        # Format validation
        if not re.fullmatch(r"^\d{9}$", routing_number):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Routing number must be exactly 9 digits")
        if not re.fullmatch(r"^\d{4,17}$", account_number):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Account number must be between 4 and 17 digits")

        # Save beneficiary if requested
        if request.save_beneficiary:
            new_ben = Beneficiary(
                user_id=user_id,
                name=recipient_name,
                routing_number=routing_number,
                account_number=account_number,
                bank_name=bank_name,
            )
            db.add(new_ben)
            db.flush()
            beneficiary_id = new_ben.id

    # 4. Check dynamic transfer limits (hard cap)
    limit_service.validate_transfer_limits(db, user_id, request.amount)

    # 5. Check sensitive transfer MFA trigger
    if request.amount > SENSITIVE_THRESHOLD:
        if not request.pin or not request.pin.strip():
            raise MfaRequiredException()
        mfa_service.verify_pin(db, user_id, request.pin.strip())

    # 6. Execute debit and create pending ACH transfer
    now = datetime.now(timezone.utc)
    from_acc.balance = round(from_acc.balance - request.amount, 2)

    transfer = Transfer(
        transfer_type="ach",
        from_account_id=from_acc.id,
        to_account_id=None,
        beneficiary_id=beneficiary_id,
        recipient_name=recipient_name,
        routing_number=routing_number,
        account_number=account_number,
        bank_name=bank_name,
        amount=round(request.amount, 2),
        status="pending",
        description=request.description or f"ACH Transfer to {recipient_name} ({bank_name})",
        created_at=now,
    )
    db.add(transfer)
    db.flush()

    # Record pending debit transaction
    debit_tx = Transaction(
        account_id=from_acc.id,
        transfer_id=transfer.id,
        transaction_type="debit",
        amount=round(request.amount, 2),
        balance_after=from_acc.balance,
        description=transfer.description,
        reference=f"ACH-{transfer.id:05d}-OUT",
        status="pending",
        created_at=now,
    )
    db.add(debit_tx)
    db.commit()
    db.refresh(transfer)
    return transfer


def settle_ach_transfer(db: Session, transfer_id: int) -> Optional[Transfer]:
    """Settle an ACH transfer transitioning it from 'pending' to 'settled'."""
    transfer = db.query(Transfer).filter(Transfer.id == transfer_id, Transfer.transfer_type == "ach").first()
    if not transfer or transfer.status != "pending":
        return transfer

    now = datetime.now(timezone.utc)
    transfer.status = "settled"
    transfer.settled_at = now

    # Update associated transactions
    for tx in transfer.transactions:
        tx.status = "completed"

    db.commit()
    db.refresh(transfer)
    return transfer


def fail_ach_transfer(db: Session, transfer_id: int, reason: str = "ACH network rejected") -> Optional[Transfer]:
    """Fail an ACH transfer, refunding the debited balance to the source account."""
    transfer = db.query(Transfer).filter(Transfer.id == transfer_id, Transfer.transfer_type == "ach").first()
    if not transfer or transfer.status != "pending":
        return transfer

    from_acc = db.query(account_service.Account).filter(account_service.Account.id == transfer.from_account_id).first()
    if from_acc:
        from_acc.balance = round(from_acc.balance + transfer.amount, 2)

    transfer.status = "failed"
    for tx in transfer.transactions:
        tx.status = "failed"
        tx.description = f"{tx.description} (Failed: {reason})"

    db.commit()
    db.refresh(transfer)
    return transfer


def process_pending_ach_transfers(db: Session) -> List[Transfer]:
    """Background task helper to settle all in-flight pending ACH transfers."""
    pending_transfers = (
        db.query(Transfer)
        .filter(Transfer.transfer_type == "ach", Transfer.status == "pending")
        .all()
    )
    settled = []
    for trf in pending_transfers:
        s = settle_ach_transfer(db, trf.id)
        if s:
            settled.append(s)
    return settled
