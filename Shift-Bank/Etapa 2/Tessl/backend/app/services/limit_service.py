from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.models import TransferLimit, Transfer, Account
from backend.app.schemas import TransferLimitsResponse


DEFAULT_PER_TRANSACTION_LIMIT = 5000.00
DEFAULT_DAILY_LIMIT = 10000.00


def get_or_create_limits(db: Session, user_id: int) -> TransferLimit:
    """Retrieve or initialize default transfer limits for a user."""
    limits = db.query(TransferLimit).filter(TransferLimit.user_id == user_id).first()
    if not limits:
        limits = TransferLimit(
            user_id=user_id,
            per_transaction_limit=DEFAULT_PER_TRANSACTION_LIMIT,
            daily_limit=DEFAULT_DAILY_LIMIT,
        )
        db.add(limits)
        db.commit()
        db.refresh(limits)
    return limits


def calculate_daily_total(db: Session, user_id: int, target_date: Optional[datetime] = None) -> float:
    """
    Calculate the total sum of transfers (internal and ACH) initiated on the target calendar day (UTC).
    Only includes successful or in-flight transfers ('completed', 'pending', 'settled').
    """
    if target_date is None:
        target_date = datetime.now(timezone.utc)

    start_of_day = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0, tzinfo=timezone.utc)
    end_of_day = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59, 999999, tzinfo=timezone.utc)

    # Join with Account to filter by user's source accounts
    total = (
        db.query(func.coalesce(func.sum(Transfer.amount), 0.0))
        .join(Account, Transfer.from_account_id == Account.id)
        .filter(
            Account.user_id == user_id,
            Transfer.status.in_(["completed", "pending", "settled"]),
            Transfer.created_at >= start_of_day,
            Transfer.created_at <= end_of_day,
        )
        .scalar()
    )
    return round(float(total), 2)


def get_limits_summary(db: Session, user_id: int) -> TransferLimitsResponse:
    """Return user's transfer limits along with current daily usage and remaining limit."""
    limits = get_or_create_limits(db, user_id)
    daily_total = calculate_daily_total(db, user_id)
    remaining = max(0.0, round(limits.daily_limit - daily_total, 2))

    return TransferLimitsResponse(
        per_transaction_limit=limits.per_transaction_limit,
        daily_limit=limits.daily_limit,
        current_daily_total=daily_total,
        remaining_daily_limit=remaining,
    )


def validate_transfer_limits(db: Session, user_id: int, amount: float):
    """
    Validates that a transfer amount does not exceed the per-transaction limit
    and does not cause cumulative transfers for today to exceed the daily limit.
    Raises HTTP 400 Bad Request on violation.
    """
    limits = get_or_create_limits(db, user_id)
    rounded_amount = round(amount, 2)

    # 1. Check per-transaction limit
    if rounded_amount > limits.per_transaction_limit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transfer amount ${rounded_amount:,.2f} exceeds per-transaction limit of ${limits.per_transaction_limit:,.2f}",
        )

    # 2. Check daily cumulative limit
    current_daily = calculate_daily_total(db, user_id)
    if round(current_daily + rounded_amount, 2) > limits.daily_limit:
        remaining = max(0.0, round(limits.daily_limit - current_daily, 2))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Transfer amount ${rounded_amount:,.2f} would exceed daily limit of ${limits.daily_limit:,.2f}. "
                f"Remaining limit for today is ${remaining:,.2f}."
            ),
        )


def update_limits(db: Session, user_id: int, per_transaction_limit: float, daily_limit: float) -> TransferLimitsResponse:
    """Update transfer limits for user with validation."""
    if per_transaction_limit <= 0 or daily_limit <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Transfer limits must be strictly positive",
        )

    if per_transaction_limit > daily_limit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Per-transaction limit cannot exceed daily limit",
        )

    limits = get_or_create_limits(db, user_id)
    limits.per_transaction_limit = round(per_transaction_limit, 2)
    limits.daily_limit = round(daily_limit, 2)
    db.commit()
    db.refresh(limits)

    return get_limits_summary(db, user_id)
