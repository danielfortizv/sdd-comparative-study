import re
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from backend.app.models import RecurringSchedule, Account, Beneficiary, Transfer, Transaction
from backend.app.schemas import RecurringScheduleCreateRequest
from backend.app.services import account_service, mfa_service, limit_service
from backend.app.services.transfer_service import MfaRequiredException, SENSITIVE_THRESHOLD


def _advance_date(current_date: datetime, frequency: str) -> datetime:
    """Calculates the next execution date based on frequency."""
    if frequency == "daily":
        return current_date + timedelta(days=1)
    elif frequency == "weekly":
        return current_date + timedelta(days=7)
    elif frequency == "monthly":
        # Approximate 30 days for month advance
        return current_date + timedelta(days=30)
    return current_date + timedelta(days=1)


def create_recurring_schedule(
    db: Session,
    user_id: int,
    request: RecurringScheduleCreateRequest,
) -> RecurringSchedule:
    """
    Creates and persists a recurring transfer schedule for internal or ACH transfers.
    Validates accounts, beneficiaries, frequencies, and verifies MFA PIN upfront if amount > $1,000.
    """
    # 1. Verify source account exists and belongs to user
    from_acc = account_service.get_account_by_id(db, request.from_account_id, user_id)

    # 2. Validate transfer type specific fields
    to_acc_id = None
    ben_id = None
    recipient_name = None
    routing_number = None
    account_number = None
    bank_name = None

    if request.transfer_type == "internal":
        if not request.to_account_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="to_account_id is required for internal transfers",
            )
        if request.from_account_id == request.to_account_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot transfer to the same account",
            )
        to_acc = account_service.get_account_by_id(db, request.to_account_id, user_id)
        to_acc_id = to_acc.id
    elif request.transfer_type == "ach":
        if request.beneficiary_id:
            ben = db.query(Beneficiary).filter(Beneficiary.id == request.beneficiary_id, Beneficiary.user_id == user_id).first()
            if not ben:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Beneficiary {request.beneficiary_id} not found")
            ben_id = ben.id
            recipient_name = ben.name
            routing_number = ben.routing_number
            account_number = ben.account_number
            bank_name = ben.bank_name
        else:
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

            if not re.fullmatch(r"^\d{9}$", routing_number):
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Routing number must be exactly 9 digits")
            if not re.fullmatch(r"^\d{4,17}$", account_number):
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Account number must be between 4 and 17 digits")

    # 3. Check MFA PIN requirement for sensitive recurring setup (> $1,000)
    if request.amount > SENSITIVE_THRESHOLD:
        if not request.pin or not request.pin.strip():
            raise MfaRequiredException()
        mfa_service.verify_pin(db, user_id, request.pin.strip(), commit=False)

    now = datetime.now(timezone.utc)
    if request.start_date is not None:
        next_exec = request.start_date
    else:
        next_exec = _advance_date(now, request.frequency)

    desc = request.description
    if not desc:
        if request.transfer_type == "internal":
            to_acc = account_service.get_account_by_id(db, to_acc_id, user_id)
            desc = f"Recurring transfer to {to_acc.account_name} ({request.frequency})"
        else:
            desc = f"Recurring ACH transfer to {recipient_name} ({request.frequency})"

    schedule = RecurringSchedule(
        user_id=user_id,
        transfer_type=request.transfer_type,
        from_account_id=from_acc.id,
        to_account_id=to_acc_id,
        beneficiary_id=ben_id,
        recipient_name=recipient_name,
        routing_number=routing_number,
        account_number=account_number,
        bank_name=bank_name,
        amount=round(request.amount, 2),
        frequency=request.frequency,
        status="active",
        description=desc,
        next_execution_date=next_exec,
        created_at=now,
    )
    db.add(schedule)
    db.flush()

    from backend.app.services import audit_service
    audit_service.record_audit_event(
        db=db,
        event_type="recurring_schedule_created",
        status="SUCCESS",
        details={
            "schedule_id": schedule.id,
            "transfer_type": schedule.transfer_type,
            "amount": schedule.amount,
            "frequency": schedule.frequency,
        },
        actor_id=user_id,
    )

    db.commit()
    db.refresh(schedule)
    return schedule


def get_user_schedules(db: Session, user_id: int) -> List[RecurringSchedule]:
    """Retrieve all recurring payment schedules configured by user."""
    return (
        db.query(RecurringSchedule)
        .filter(RecurringSchedule.user_id == user_id)
        .order_by(RecurringSchedule.created_at.desc())
        .all()
    )


def get_schedule_by_id(db: Session, schedule_id: int, user_id: int) -> RecurringSchedule:
    """Retrieve a single schedule by ID or raise 404."""
    schedule = (
        db.query(RecurringSchedule)
        .filter(RecurringSchedule.id == schedule_id, RecurringSchedule.user_id == user_id)
        .first()
    )
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recurring schedule {schedule_id} not found",
        )
    return schedule


def pause_schedule(db: Session, schedule_id: int, user_id: int) -> RecurringSchedule:
    """Pause an active recurring schedule."""
    from backend.app.services import audit_service
    schedule = get_schedule_by_id(db, schedule_id, user_id)
    if schedule.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot pause a cancelled recurring schedule",
        )
    if schedule.status == "paused":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Schedule is already paused",
        )
    schedule.status = "paused"
    audit_service.record_audit_event(
        db=db,
        event_type="recurring_schedule_paused",
        status="SUCCESS",
        details={"schedule_id": schedule.id},
        actor_id=user_id,
    )
    db.commit()
    db.refresh(schedule)
    return schedule


def resume_schedule(db: Session, schedule_id: int, user_id: int) -> RecurringSchedule:
    """Resume a paused recurring schedule."""
    from backend.app.services import audit_service
    schedule = get_schedule_by_id(db, schedule_id, user_id)
    if schedule.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot resume a cancelled recurring schedule",
        )
    if schedule.status == "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Schedule is already active",
        )
    schedule.status = "active"
    audit_service.record_audit_event(
        db=db,
        event_type="recurring_schedule_resumed",
        status="SUCCESS",
        details={"schedule_id": schedule.id},
        actor_id=user_id,
    )
    db.commit()
    db.refresh(schedule)
    return schedule


def cancel_schedule(db: Session, schedule_id: int, user_id: int) -> RecurringSchedule:
    """Cancel a recurring schedule permanently."""
    from backend.app.services import audit_service
    schedule = get_schedule_by_id(db, schedule_id, user_id)
    schedule.status = "cancelled"
    audit_service.record_audit_event(
        db=db,
        event_type="recurring_schedule_cancelled",
        status="SUCCESS",
        details={"schedule_id": schedule.id},
        actor_id=user_id,
    )
    db.commit()
    db.refresh(schedule)
    return schedule


def execute_due_recurring_schedules(
    db: Session,
    target_time: Optional[datetime] = None,
) -> List[dict]:
    """
    Evaluates active recurring payment schedules whose next_execution_date <= target_time.
    Executes transfers autonomously without interactive PIN, verifying balance and daily limits.
    Advances next_execution_date on both success and failure and emits audit events.
    """
    from backend.app.services import audit_service

    if target_time is None:
        target_time = datetime.now(timezone.utc)

    due_schedules = (
        db.query(RecurringSchedule)
        .filter(
            RecurringSchedule.status == "active",
            RecurringSchedule.next_execution_date <= target_time,
        )
        .all()
    )

    results = []
    now = datetime.now(timezone.utc)

    for schedule in due_schedules:
        user_id = schedule.user_id
        from_acc = db.query(Account).filter(Account.id == schedule.from_account_id).first()

        # Check balance
        has_sufficient_balance = from_acc is not None and round(from_acc.balance, 2) >= round(schedule.amount, 2)

        # Check limits
        limits = limit_service.get_or_create_limits(db, user_id)
        current_daily = limit_service.calculate_daily_total(db, user_id, now)
        within_single_limit = round(schedule.amount, 2) <= limits.per_transaction_limit
        within_daily_limit = round(current_daily + schedule.amount, 2) <= limits.daily_limit

        if not (has_sufficient_balance and within_single_limit and within_daily_limit):
            # Record failed execution attempt and advance to next due date
            schedule.failure_count += 1
            schedule.next_execution_date = _advance_date(schedule.next_execution_date, schedule.frequency)
            audit_service.record_audit_event(
                db=db,
                event_type="recurring_payment_executed",
                status="FAILURE",
                details={
                    "schedule_id": schedule.id,
                    "amount": schedule.amount,
                    "reason": "Insufficient balance or transfer limit exceeded",
                },
                actor_id=user_id,
            )
            db.commit()
            results.append({
                "schedule_id": schedule.id,
                "status": "failed",
                "reason": "Insufficient balance or transfer limit exceeded",
            })
            continue

        # Execute transfer
        if schedule.transfer_type == "internal":
            to_acc = db.query(Account).filter(Account.id == schedule.to_account_id).first()
            if not to_acc:
                schedule.failure_count += 1
                schedule.next_execution_date = _advance_date(schedule.next_execution_date, schedule.frequency)
                audit_service.record_audit_event(
                    db=db,
                    event_type="recurring_payment_executed",
                    status="FAILURE",
                    details={
                        "schedule_id": schedule.id,
                        "amount": schedule.amount,
                        "reason": f"Destination account {schedule.to_account_id} not found",
                    },
                    actor_id=user_id,
                )
                db.commit()
                continue

            from_acc.balance = round(from_acc.balance - schedule.amount, 2)
            to_acc.balance = round(to_acc.balance + schedule.amount, 2)

            transfer = Transfer(
                transfer_type="internal",
                from_account_id=from_acc.id,
                to_account_id=to_acc.id,
                amount=round(schedule.amount, 2),
                status="completed",
                description=schedule.description or f"Recurring transfer to {to_acc.account_name}",
                created_at=now,
            )
            db.add(transfer)
            db.flush()

            debit_tx = Transaction(
                account_id=from_acc.id,
                transfer_id=transfer.id,
                transaction_type="debit",
                amount=round(schedule.amount, 2),
                balance_after=from_acc.balance,
                description=transfer.description,
                reference=f"REC-{schedule.id:04d}-{transfer.id:05d}-OUT",
                status="completed",
                created_at=now,
            )
            credit_tx = Transaction(
                account_id=to_acc.id,
                transfer_id=transfer.id,
                transaction_type="credit",
                amount=round(schedule.amount, 2),
                balance_after=to_acc.balance,
                description=f"Recurring transfer from {from_acc.account_name}",
                reference=f"REC-{schedule.id:04d}-{transfer.id:05d}-IN",
                status="completed",
                created_at=now,
            )
            db.add_all([debit_tx, credit_tx])

        elif schedule.transfer_type == "ach":
            from_acc.balance = round(from_acc.balance - schedule.amount, 2)

            transfer = Transfer(
                transfer_type="ach",
                from_account_id=from_acc.id,
                to_account_id=None,
                beneficiary_id=schedule.beneficiary_id,
                recipient_name=schedule.recipient_name,
                routing_number=schedule.routing_number,
                account_number=schedule.account_number,
                bank_name=schedule.bank_name,
                amount=round(schedule.amount, 2),
                status="pending",
                description=schedule.description or f"Recurring ACH to {schedule.recipient_name}",
                created_at=now,
            )
            db.add(transfer)
            db.flush()

            debit_tx = Transaction(
                account_id=from_acc.id,
                transfer_id=transfer.id,
                transaction_type="debit",
                amount=round(schedule.amount, 2),
                balance_after=from_acc.balance,
                description=transfer.description,
                reference=f"REC-ACH-{schedule.id:04d}-{transfer.id:05d}-OUT",
                status="pending",
                created_at=now,
            )
            db.add(debit_tx)

        # Update schedule execution tracking
        schedule.last_executed_at = now
        schedule.next_execution_date = _advance_date(schedule.next_execution_date, schedule.frequency)

        # Record audit event for successful execution
        audit_service.record_audit_event(
            db=db,
            event_type="recurring_payment_executed",
            status="SUCCESS",
            details={
                "schedule_id": schedule.id,
                "transfer_type": schedule.transfer_type,
                "amount": schedule.amount,
                "transfer_id": transfer.id,
            },
            actor_id=user_id,
        )

        db.commit()
        db.refresh(schedule)

        results.append({
            "schedule_id": schedule.id,
            "status": "success",
            "transfer_id": transfer.id,
            "next_execution_date": schedule.next_execution_date,
        })

    return results
