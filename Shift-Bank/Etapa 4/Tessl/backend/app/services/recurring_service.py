import re
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from backend.app.models import RecurringSchedule, Account, Beneficiary, Transfer, Transaction, IdempotencyRecord
from backend.app.schemas import RecurringScheduleCreateRequest
from backend.app.services import account_service, mfa_service, limit_service
from backend.app.services.fx_service import get_usd_equivalent
from backend.app.services.transfer_service import MfaRequiredException
from backend.app.services.event_store import append_domain_event
from backend.app.services.projection_service import update_checkpoints
from backend.app.services.audit_service import record_audit_event, acquire_sqlite_write_lock
from backend.app.services.idempotency_service import record_idempotency_commit, compute_fingerprint


def _advance_date(current_date: datetime, frequency: str) -> datetime:
    """Calculates the next execution date based on frequency."""
    if frequency == "daily":
        return current_date + timedelta(days=1)
    elif frequency == "weekly":
        return current_date + timedelta(days=7)
    elif frequency == "monthly":
        return current_date + timedelta(days=30)
    return current_date + timedelta(days=1)


def create_recurring_schedule(
    db: Session,
    user_id: int,
    request: RecurringScheduleCreateRequest,
) -> RecurringSchedule:
    """
    Creates and persists a recurring transfer schedule for same-currency internal or USD ACH transfers.
    Validates same-currency constraint, beneficiaries, frequencies, limits, and verifies MFA PIN upfront if USD-equiv > $1,000.
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

        # Same-currency restriction (D-08)
        if from_acc.currency != to_acc.currency:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "RECURRING_REQUIRES_SAME_CURRENCY",
                    "message": "Recurring internal transfers are only permitted between accounts of the same currency.",
                },
            )
        to_acc_id = to_acc.id

    elif request.transfer_type == "ach":
        # USD-only restriction for ACH (D-08)
        if from_acc.currency != "USD":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "ACH_REQUIRES_USD_ACCOUNT",
                    "message": "Recurring ACH transfers are only permitted from USD accounts.",
                },
            )

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

    # 3. Check MFA PIN requirement for sensitive recurring setup (> $1,000 USD equivalent)
    usd_equiv = get_usd_equivalent(request.amount, from_acc.currency)
    if usd_equiv > Decimal("1000.00"):
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
        amount=request.amount,
        currency=from_acc.currency,
        frequency=request.frequency,
        status="active",
        description=desc,
        next_execution_date=next_exec,
        created_at=now,
    )
    db.add(schedule)
    db.flush()

    record_audit_event(
        db=db,
        event_type="recurring_schedule_created",
        status="SUCCESS",
        details={
            "schedule_id": schedule.id,
            "transfer_type": schedule.transfer_type,
            "amount": str(schedule.amount),
            "currency": schedule.currency,
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
    record_audit_event(
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
    record_audit_event(
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
    schedule = get_schedule_by_id(db, schedule_id, user_id)
    schedule.status = "cancelled"
    record_audit_event(
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
    Advances next_execution_date on both success and failure and emits audit and domain events.
    Hardened against concurrent scheduler execution via SQLite write lock, fresh due verification,
    and database-backed idempotency records.
    """
    if target_time is None:
        target_time = datetime.now(timezone.utc)

    # Acquire SQLite write lock to serialize concurrent scheduler ticks
    acquire_sqlite_write_lock(db)

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
        # Atomic re-query inside the locked transaction: confirm schedule is still active and due
        fresh_schedule = (
            db.query(RecurringSchedule)
            .filter(
                RecurringSchedule.id == schedule.id,
                RecurringSchedule.status == "active",
                RecurringSchedule.next_execution_date <= target_time,
            )
            .first()
        )
        if not fresh_schedule:
            continue

        det_idempotency_key = f"sched-{fresh_schedule.id}-{int(fresh_schedule.next_execution_date.timestamp())}"

        # Pre-execution check: verify if this exact schedule occurrence was already committed
        if (
            db.query(IdempotencyRecord)
            .filter(IdempotencyRecord.idempotency_key == det_idempotency_key)
            .first()
        ):
            continue

        user_id = fresh_schedule.user_id
        from_acc = db.query(Account).filter(Account.id == fresh_schedule.from_account_id).first()

        # Check balance
        has_sufficient_balance = from_acc is not None and from_acc.balance >= fresh_schedule.amount

        # Check limits in USD equivalent
        limits = limit_service.get_or_create_limits(db, user_id)
        current_daily = limit_service.calculate_daily_total(db, user_id, now)
        usd_equiv = get_usd_equivalent(fresh_schedule.amount, fresh_schedule.currency)
        within_single_limit = usd_equiv <= limits.per_transaction_limit
        within_daily_limit = (current_daily + usd_equiv) <= limits.daily_limit

        if not (has_sufficient_balance and within_single_limit and within_daily_limit):
            # Record failed execution attempt and advance to next due date
            fresh_schedule.failure_count += 1
            fresh_schedule.next_execution_date = _advance_date(fresh_schedule.next_execution_date, fresh_schedule.frequency)
            record_audit_event(
                db=db,
                event_type="recurring_payment_executed",
                status="FAILURE",
                details={
                    "schedule_id": fresh_schedule.id,
                    "amount": str(fresh_schedule.amount),
                    "currency": fresh_schedule.currency,
                    "reason": "Insufficient balance or transfer limit exceeded",
                },
                actor_id=user_id,
            )
            db.commit()
            results.append({
                "schedule_id": fresh_schedule.id,
                "status": "failed",
                "reason": "Insufficient balance or transfer limit exceeded",
            })
            continue

        operation_id = str(uuid.uuid4())

        try:
            # Execute transfer
            if fresh_schedule.transfer_type == "internal":
                to_acc = db.query(Account).filter(Account.id == fresh_schedule.to_account_id).first()
                if not to_acc:
                    fresh_schedule.failure_count += 1
                    fresh_schedule.next_execution_date = _advance_date(fresh_schedule.next_execution_date, fresh_schedule.frequency)
                    record_audit_event(
                        db=db,
                        event_type="recurring_payment_executed",
                        status="FAILURE",
                        details={
                            "schedule_id": fresh_schedule.id,
                            "amount": str(fresh_schedule.amount),
                            "reason": f"Destination account {fresh_schedule.to_account_id} not found",
                        },
                        actor_id=user_id,
                    )
                    db.commit()
                    continue

                from_new_ver = from_acc.version + 1
                to_new_ver = to_acc.version + 1
                from_acc.balance -= fresh_schedule.amount
                to_acc.balance += fresh_schedule.amount

                transfer = Transfer(
                    operation_id=operation_id,
                    transfer_type="internal",
                    from_account_id=from_acc.id,
                    to_account_id=to_acc.id,
                    amount=fresh_schedule.amount,
                    currency=fresh_schedule.currency,
                    from_account_version=from_new_ver,
                    to_account_version=to_new_ver,
                    status="completed",
                    description=fresh_schedule.description or f"Recurring transfer to {to_acc.account_name}",
                    created_at=now,
                )
                db.add(transfer)
                db.flush()

                debit_tx = Transaction(
                    account_id=from_acc.id,
                    transfer_id=transfer.id,
                    transaction_type="debit",
                    amount=fresh_schedule.amount,
                    balance_after=from_acc.balance,
                    currency=fresh_schedule.currency,
                    description=transfer.description,
                    reference=f"REC-{fresh_schedule.id:04d}-{transfer.id:05d}-OUT",
                    status="completed",
                    created_at=now,
                )
                credit_tx = Transaction(
                    account_id=to_acc.id,
                    transfer_id=transfer.id,
                    transaction_type="credit",
                    amount=fresh_schedule.amount,
                    balance_after=to_acc.balance,
                    currency=fresh_schedule.currency,
                    description=f"Recurring transfer from {from_acc.account_name}",
                    reference=f"REC-{fresh_schedule.id:04d}-{transfer.id:05d}-IN",
                    status="completed",
                    created_at=now,
                )
                db.add_all([debit_tx, credit_tx])

                ev = append_domain_event(
                    db=db,
                    event_type="InternalTransferCompleted",
                    aggregate_id=f"banking:{user_id}",
                    account_ids=[from_acc.id, to_acc.id],
                    payload={
                        "operation_id": operation_id,
                        "schedule_id": fresh_schedule.id,
                        "from_account_id": from_acc.id,
                        "to_account_id": to_acc.id,
                        "amount": str(fresh_schedule.amount),
                        "currency": fresh_schedule.currency,
                        "from_account_version": from_new_ver,
                        "to_account_version": to_new_ver,
                    },
                    idempotency_key=det_idempotency_key,
                )
                update_checkpoints(db, ev.id)

            elif fresh_schedule.transfer_type == "ach":
                from_new_ver = from_acc.version + 1
                from_acc.balance -= fresh_schedule.amount

                transfer = Transfer(
                    operation_id=operation_id,
                    transfer_type="ach",
                    from_account_id=from_acc.id,
                    to_account_id=None,
                    beneficiary_id=fresh_schedule.beneficiary_id,
                    recipient_name=fresh_schedule.recipient_name,
                    routing_number=fresh_schedule.routing_number,
                    account_number=fresh_schedule.account_number,
                    bank_name=fresh_schedule.bank_name,
                    amount=fresh_schedule.amount,
                    currency="USD",
                    from_account_version=from_new_ver,
                    status="pending",
                    description=fresh_schedule.description or f"Recurring ACH to {fresh_schedule.recipient_name}",
                    created_at=now,
                )
                db.add(transfer)
                db.flush()

                debit_tx = Transaction(
                    account_id=from_acc.id,
                    transfer_id=transfer.id,
                    transaction_type="debit",
                    amount=fresh_schedule.amount,
                    balance_after=from_acc.balance,
                    currency="USD",
                    description=transfer.description,
                    reference=f"REC-ACH-{fresh_schedule.id:04d}-{transfer.id:05d}-OUT",
                    status="pending",
                    created_at=now,
                )
                db.add(debit_tx)

                ev = append_domain_event(
                    db=db,
                    event_type="AchTransferInitiated",
                    aggregate_id=f"banking:{user_id}",
                    account_ids=[from_acc.id],
                    payload={
                        "operation_id": operation_id,
                        "schedule_id": fresh_schedule.id,
                        "from_account_id": from_acc.id,
                        "amount": str(fresh_schedule.amount),
                        "currency": "USD",
                        "from_account_version": from_new_ver,
                    },
                    idempotency_key=det_idempotency_key,
                )
                update_checkpoints(db, ev.id)

            # Update schedule execution tracking
            fresh_schedule.last_executed_at = now
            fresh_schedule.next_execution_date = _advance_date(fresh_schedule.next_execution_date, fresh_schedule.frequency)

            record_audit_event(
                db=db,
                event_type="recurring_payment_executed",
                status="SUCCESS",
                details={
                    "schedule_id": fresh_schedule.id,
                    "transfer_type": fresh_schedule.transfer_type,
                    "amount": str(fresh_schedule.amount),
                    "currency": fresh_schedule.currency,
                    "transfer_id": transfer.id,
                },
                actor_id=user_id,
            )

            # Atomic database-backed idempotency record commit (enforced by UNIQUE constraint on idempotency_key)
            record_idempotency_commit(
                db=db,
                idempotency_key=det_idempotency_key,
                operation_type="recurring",
                operation_id=operation_id,
                fingerprint=compute_fingerprint({
                    "schedule_id": fresh_schedule.id,
                    "from_account_id": fresh_schedule.from_account_id,
                    "amount": str(fresh_schedule.amount),
                    "frequency": fresh_schedule.frequency,
                    "execution_timestamp": int(fresh_schedule.next_execution_date.timestamp()),
                }),
                response_data={
                    "schedule_id": fresh_schedule.id,
                    "status": "success",
                    "transfer_id": transfer.id,
                },
            )

            db.commit()
            db.refresh(fresh_schedule)

            results.append({
                "schedule_id": fresh_schedule.id,
                "status": "success",
                "transfer_id": transfer.id,
                "next_execution_date": fresh_schedule.next_execution_date,
            })

        except Exception as exc:
            db.rollback()
            if isinstance(exc, IntegrityError) or "UNIQUE" in str(exc).upper():
                continue
            raise

    return results
