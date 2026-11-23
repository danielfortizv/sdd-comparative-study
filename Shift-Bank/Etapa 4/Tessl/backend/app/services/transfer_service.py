import re
import uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from backend.app.models import Transfer, Transaction, Beneficiary, Account
from backend.app.schemas import TransferRequest, AchTransferRequest
from backend.app.services import account_service, mfa_service, limit_service, audit_service
from backend.app.services.fx_service import get_usd_equivalent
from backend.app.services.event_store import append_domain_event, ConcurrencyConflictException
from backend.app.services.projection_service import update_checkpoints
from backend.app.services.idempotency_service import (
    validate_idempotency_key_header,
    compute_fingerprint,
    check_existing_idempotency,
    record_idempotency_commit,
)


class MfaRequiredException(Exception):
    """Exception raised when a transfer exceeds threshold without PIN."""

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
    idempotency_key: Optional[str] = None,
) -> Transfer:
    """
    Executes an internal transfer between the authenticated user's same-currency accounts.
    Validates same-currency constraint, balances, dynamic limits, MFA, and optimistic concurrency.
    Appends atomic InternalTransferCompleted event and updates CQRS read projections.
    """
    validated_key = validate_idempotency_key_header(idempotency_key)

    # Idempotency check if key provided
    fingerprint = compute_fingerprint({
        "from_account_id": request.from_account_id,
        "to_account_id": request.to_account_id,
        "amount": str(request.amount),
        "expected_from_version": request.expected_from_version,
        "expected_to_version": request.expected_to_version,
        "description": request.description,
    })
    existing = check_existing_idempotency(db, validated_key, fingerprint)
    if existing:
        trf_id = existing.get("id")
        trf = db.query(Transfer).filter(Transfer.id == trf_id).first()
        if trf:
            return trf
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "IDEMPOTENT_RECORD_CORRUPTED",
                "message": "Committed idempotency record exists but associated transfer entity could not be retrieved",
            },
        )

    try:
        if request.from_account_id == request.to_account_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "SAME_ACCOUNT_NOT_PERMITTED", "message": "Cannot transfer to the same account"},
            )

        # Verify both accounts exist and belong to the user
        from_acc = account_service.get_account_by_id(db, request.from_account_id, user_id)
        to_acc = account_service.get_account_by_id(db, request.to_account_id, user_id)

        # Check same-currency invariant (D-01, D-04)
        if from_acc.currency != to_acc.currency:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "CROSS_CURRENCY_NOT_PERMITTED",
                    "message": "Internal transfers are strictly same-currency. Please use currency conversion for cross-currency transfers.",
                },
            )

        # Check sufficient funds
        if from_acc.balance < request.amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient funds in source account",
            )

        # Check dynamic transfer limits in USD equivalent
        limit_service.validate_transfer_limits(db, user_id, request.amount, from_acc.currency)

        # Check sensitive transfer MFA trigger (> 1,000.00 USD equivalent)
        usd_equiv = get_usd_equivalent(request.amount, from_acc.currency)
        if usd_equiv > Decimal("1000.00"):
            if not request.pin or not request.pin.strip():
                raise MfaRequiredException()
            mfa_service.verify_pin(db, user_id, request.pin.strip(), commit=False)

        # Check optimistic concurrency
        expected_versions = {
            from_acc.id: request.expected_from_version,
            to_acc.id: request.expected_to_version,
        }

        operation_id = str(uuid.uuid4())
        from_new_version = from_acc.version + 1
        to_new_version = to_acc.version + 1

        event_payload = {
            "operation_id": operation_id,
            "from_account_id": from_acc.id,
            "to_account_id": to_acc.id,
            "currency": from_acc.currency,
            "amount": str(request.amount),
            "from_account_version": from_new_version,
            "to_account_version": to_new_version,
            "description": request.description,
        }

        try:
            domain_event = append_domain_event(
                db=db,
                event_type="InternalTransferCompleted",
                aggregate_id=f"banking:{user_id}",
                account_ids=[from_acc.id, to_acc.id],
                payload=event_payload,
                idempotency_key=validated_key,
                expected_versions=expected_versions,
            )
        except ConcurrencyConflictException as ce:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": ce.code, "message": ce.message, "details": ce.details},
            )

        # Synchronous CQRS projection updates
        now = datetime.now(timezone.utc)
        from_acc.balance -= request.amount
        to_acc.balance += request.amount

        transfer = Transfer(
            operation_id=operation_id,
            transfer_type="internal",
            from_account_id=from_acc.id,
            to_account_id=to_acc.id,
            amount=request.amount,
            currency=from_acc.currency,
            from_account_version=from_new_version,
            to_account_version=to_new_version,
            status="completed",
            description=request.description or f"Transfer from {from_acc.account_name} to {to_acc.account_name}",
            created_at=now,
        )
        db.add(transfer)
        db.flush()

        debit_desc = request.description or f"Transfer to {to_acc.account_name}"
        debit_tx = Transaction(
            account_id=from_acc.id,
            transfer_id=transfer.id,
            transaction_type="debit",
            amount=request.amount,
            balance_after=from_acc.balance,
            currency=from_acc.currency,
            description=debit_desc,
            reference=f"TRF-{transfer.id:05d}-OUT",
            status="completed",
            created_at=now,
        )

        credit_desc = request.description or f"Transfer from {from_acc.account_name}"
        credit_tx = Transaction(
            account_id=to_acc.id,
            transfer_id=transfer.id,
            transaction_type="credit",
            amount=request.amount,
            balance_after=to_acc.balance,
            currency=to_acc.currency,
            description=credit_desc,
            reference=f"TRF-{transfer.id:05d}-IN",
            status="completed",
            created_at=now,
        )
        db.add_all([debit_tx, credit_tx])

        update_checkpoints(db, domain_event.id)

        # Audit log (SUCCESS)
        audit_service.record_audit_event(
            db=db,
            event_type="transfer_internal",
            status="SUCCESS",
            details={
                "transfer_id": transfer.id,
                "operation_id": operation_id,
                "from_account_id": from_acc.id,
                "to_account_id": to_acc.id,
                "amount": f"{Decimal(str(request.amount)):.2f}",
                "currency": from_acc.currency,
                "reference": f"TRF-{transfer.id:05d}-OUT",
            },
            actor_id=user_id,
        )

        # Record idempotency if key present
        if validated_key and fingerprint:
            record_idempotency_commit(
                db=db,
                idempotency_key=validated_key,
                operation_type="transfer",
                operation_id=operation_id,
                fingerprint=fingerprint,
                response_data={
                    "id": transfer.id,
                    "operation_id": operation_id,
                    "from_account_id": from_acc.id,
                    "to_account_id": to_acc.id,
                    "amount": str(request.amount),
                    "currency": from_acc.currency,
                    "from_account_version": from_new_version,
                    "to_account_version": to_new_version,
                    "status": "completed",
                    "description": transfer.description,
                    "created_at": transfer.created_at.isoformat(),
                },
            )

        db.commit()
        db.refresh(transfer)
        return transfer

    except Exception as e:
        db.rollback()
        err_msg = getattr(e, "detail", str(e))
        is_limit = isinstance(e, HTTPException) and "limit" in str(err_msg).lower()
        event_type = "limit_breach" if is_limit else "transfer_internal"

        audit_service.record_failure_audit_event(
            event_type=event_type,
            details={
                "from_account_id": getattr(request, "from_account_id", None),
                "to_account_id": getattr(request, "to_account_id", None),
                "amount": f"{Decimal(str(getattr(request, 'amount', 0))):.2f}",
                "error": err_msg,
            },
            actor_id=user_id,
        )
        raise


def execute_ach_transfer(
    db: Session,
    user_id: int,
    request: AchTransferRequest,
    idempotency_key: Optional[str] = None,
) -> Transfer:
    """
    Executes an external ACH transfer to a beneficiary or ad-hoc account.
    Restricted strictly to USD source accounts (D-08).
    """
    validated_key = validate_idempotency_key_header(idempotency_key)

    fingerprint = compute_fingerprint({
        "from_account_id": request.from_account_id,
        "beneficiary_id": request.beneficiary_id,
        "recipient_name": request.recipient_name,
        "routing_number": str(request.routing_number) if request.routing_number else None,
        "account_number": str(request.account_number) if request.account_number else None,
        "bank_name": request.bank_name,
        "amount": str(request.amount),
        "expected_from_version": request.expected_from_version,
        "description": request.description,
    })
    existing = check_existing_idempotency(db, validated_key, fingerprint)
    if existing:
        trf_id = existing.get("id")
        trf = db.query(Transfer).filter(Transfer.id == trf_id).first()
        if trf:
            return trf
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "IDEMPOTENT_RECORD_CORRUPTED",
                "message": "Committed idempotency record exists but associated transfer entity could not be retrieved",
            },
        )

    try:
        from_acc = account_service.get_account_by_id(db, request.from_account_id, user_id)

        # Strict USD Currency Restriction (D-08)
        if from_acc.currency != "USD":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "ACH_REQUIRES_USD_ACCOUNT", "message": "ACH transfers are only permitted from USD accounts"},
            )

        if from_acc.balance < request.amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient funds in source account",
            )

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
            if not (request.recipient_name and request.recipient_name.strip()):
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Recipient name is required")
            if not (request.routing_number and str(request.routing_number).strip()):
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Routing number is required")
            if not (request.account_number and str(request.account_number).strip()):
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Account number is required")
            if not (request.bank_name and request.bank_name.strip()):
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Bank name is required")

            recipient_name = request.recipient_name.strip()
            routing_number = str(request.routing_number).strip()
            account_number = str(request.account_number).strip()
            bank_name = request.bank_name.strip()

            if not re.fullmatch(r"^\d{9}$", routing_number):
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Routing number must be exactly 9 digits")
            if not re.fullmatch(r"^\d{4,17}$", account_number):
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Account number must be between 4 and 17 digits")

        limit_service.validate_transfer_limits(db, user_id, request.amount, from_acc.currency)

        if request.amount > Decimal("1000.00"):
            if not request.pin or not request.pin.strip():
                raise MfaRequiredException()
            mfa_service.verify_pin(db, user_id, request.pin.strip(), commit=False)

        if request.beneficiary_id is None and request.save_beneficiary:
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
            audit_service.record_audit_event(
                db=db,
                event_type="beneficiary_created",
                status="SUCCESS",
                details={
                    "beneficiary_id": new_ben.id,
                    "name": new_ben.name,
                    "bank_name": new_ben.bank_name,
                },
                actor_id=user_id,
            )

        expected_versions = {
            from_acc.id: request.expected_from_version,
        }

        operation_id = str(uuid.uuid4())
        from_new_version = from_acc.version + 1

        event_payload = {
            "operation_id": operation_id,
            "from_account_id": from_acc.id,
            "amount": str(request.amount),
            "currency": "USD",
            "from_account_version": from_new_version,
            "recipient_name": recipient_name,
            "bank_name": bank_name,
            "description": request.description,
        }

        try:
            domain_event = append_domain_event(
                db=db,
                event_type="AchTransferInitiated",
                aggregate_id=f"banking:{user_id}",
                account_ids=[from_acc.id],
                payload=event_payload,
                idempotency_key=validated_key,
                expected_versions=expected_versions,
            )
        except ConcurrencyConflictException as ce:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": ce.code, "message": ce.message, "details": ce.details},
            )

        now = datetime.now(timezone.utc)
        from_acc.balance -= request.amount

        transfer = Transfer(
            operation_id=operation_id,
            transfer_type="ach",
            from_account_id=from_acc.id,
            to_account_id=None,
            beneficiary_id=beneficiary_id,
            recipient_name=recipient_name,
            routing_number=routing_number,
            account_number=account_number,
            bank_name=bank_name,
            amount=request.amount,
            currency="USD",
            from_account_version=from_new_version,
            status="pending",
            description=request.description or f"ACH Transfer to {recipient_name} ({bank_name})",
            created_at=now,
        )
        db.add(transfer)
        db.flush()

        debit_tx = Transaction(
            account_id=from_acc.id,
            transfer_id=transfer.id,
            transaction_type="debit",
            amount=request.amount,
            balance_after=from_acc.balance,
            currency="USD",
            description=transfer.description,
            reference=f"ACH-{transfer.id:05d}-OUT",
            status="pending",
            created_at=now,
        )
        db.add(debit_tx)

        update_checkpoints(db, domain_event.id)

        audit_service.record_audit_event(
            db=db,
            event_type="transfer_ach_initiated",
            status="SUCCESS",
            details={
                "transfer_id": transfer.id,
                "operation_id": operation_id,
                "from_account_id": from_acc.id,
                "recipient_name": recipient_name,
                "amount": f"{Decimal(str(request.amount)):.2f}",
                "reference": f"ACH-{transfer.id:05d}-OUT",
                "status": "pending",
            },
            actor_id=user_id,
        )

        if validated_key and fingerprint:
            record_idempotency_commit(
                db=db,
                idempotency_key=validated_key,
                operation_type="ach",
                operation_id=operation_id,
                fingerprint=fingerprint,
                response_data={
                    "id": transfer.id,
                    "operation_id": operation_id,
                    "from_account_id": from_acc.id,
                    "from_account_version": from_new_version,
                    "recipient_name": recipient_name,
                    "bank_name": bank_name,
                    "amount": str(request.amount),
                    "currency": "USD",
                    "status": "pending",
                    "description": transfer.description,
                    "created_at": transfer.created_at.isoformat(),
                },
            )

        db.commit()
        db.refresh(transfer)
        return transfer

    except Exception as e:
        db.rollback()
        err_msg = getattr(e, "detail", str(e))
        is_limit = isinstance(e, HTTPException) and "limit" in str(err_msg).lower()
        event_type = "limit_breach" if is_limit else "transfer_ach_initiated"

        audit_service.record_failure_audit_event(
            event_type=event_type,
            details={
                "from_account_id": getattr(request, "from_account_id", None),
                "amount": f"{Decimal(str(getattr(request, 'amount', 0))):.2f}",
                "error": err_msg,
            },
            actor_id=user_id,
        )
        raise


def settle_ach_transfer(db: Session, transfer_id: int) -> Optional[Transfer]:
    """Settle an ACH transfer transitioning it from 'pending' to 'settled'."""
    transfer = db.query(Transfer).filter(Transfer.id == transfer_id, Transfer.transfer_type == "ach").first()
    if not transfer or transfer.status != "pending":
        return transfer

    now = datetime.now(timezone.utc)
    transfer.status = "settled"
    transfer.settled_at = now

    for tx in transfer.transactions:
        tx.status = "completed"

    event_payload = {
        "transfer_id": transfer.id,
        "operation_id": transfer.operation_id,
        "from_account_id": transfer.from_account_id,
        "amount": str(transfer.amount),
        "status": "settled",
        "settled_at": now.isoformat(),
    }
    user_id = transfer.from_account.user_id if transfer.from_account else 1
    domain_event = append_domain_event(
        db=db,
        event_type="AchTransferSettled",
        aggregate_id=f"banking:{user_id}",
        account_ids=[transfer.from_account_id],
        payload=event_payload,
        correlation_id=transfer.operation_id,
    )
    update_checkpoints(db, domain_event.id)

    audit_service.record_audit_event(
        db=db,
        event_type="transfer_ach_settled",
        status="SUCCESS",
        details={
            "transfer_id": transfer.id,
            "settled_at": now.isoformat(),
            "amount": f"{Decimal(str(transfer.amount)):.2f}",
        },
        actor_id=user_id,
    )

    db.commit()
    db.refresh(transfer)
    return transfer


def fail_ach_transfer(db: Session, transfer_id: int, reason: str = "ACH network rejected") -> Optional[Transfer]:
    """Fail an ACH transfer, refunding the debited balance to the source account."""
    transfer = db.query(Transfer).filter(Transfer.id == transfer_id, Transfer.transfer_type == "ach").first()
    if not transfer or transfer.status != "pending":
        return transfer

    from_acc = db.query(Account).filter(Account.id == transfer.from_account_id).first()
    now = datetime.now(timezone.utc)
    user_id = from_acc.user_id if from_acc else 1

    from_new_version = (from_acc.version + 1) if from_acc else 1
    if from_acc:
        from_acc.balance += transfer.amount
        db.flush()

    transfer.status = "failed"
    for tx in transfer.transactions:
        tx.status = "failed"
        tx.description = f"{tx.description} (Failed: {reason})"

    # Insert refund transaction
    refund_tx = Transaction(
        account_id=transfer.from_account_id,
        transfer_id=transfer.id,
        transaction_type="credit",
        amount=transfer.amount,
        balance_after=from_acc.balance if from_acc else transfer.amount,
        currency="USD",
        description=f"ACH Refund: {transfer.description}",
        reference=f"ACH-{transfer.id:05d}-REFUND",
        status="completed",
        created_at=now,
    )
    db.add(refund_tx)

    event_payload = {
        "transfer_id": transfer.id,
        "operation_id": transfer.operation_id,
        "from_account_id": transfer.from_account_id,
        "refund_amount": str(transfer.amount),
        "from_account_version": from_new_version,
        "reason": reason,
    }
    domain_event = append_domain_event(
        db=db,
        event_type="AchTransferFailed",
        aggregate_id=f"banking:{user_id}",
        account_ids=[transfer.from_account_id],
        payload=event_payload,
        correlation_id=transfer.operation_id,
    )
    update_checkpoints(db, domain_event.id)

    audit_service.record_audit_event(
        db=db,
        event_type="transfer_ach_failed",
        status="FAILURE",
        details={
            "transfer_id": transfer.id,
            "amount": f"{Decimal(str(transfer.amount)):.2f}",
            "refunded": True,
            "reason": reason,
        },
        actor_id=user_id,
    )

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
