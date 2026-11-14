from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.models import TransferLimit, Transfer, Account, Conversion
from backend.app.schemas import TransferLimitsResponse
from backend.app.services.fx_service import get_usd_equivalent


DEFAULT_PER_TRANSACTION_LIMIT = Decimal("5000.00")
DEFAULT_DAILY_LIMIT = Decimal("10000.00")


def get_or_create_limits(db: Session, user_id: int) -> TransferLimit:
    """Retrieve or initialize default transfer limits for a user in USD."""
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


def calculate_daily_total(db: Session, user_id: int, target_date: Optional[datetime] = None) -> Decimal:
    """
    Calculate the total sum of transfers (internal and ACH) and conversions initiated on the target calendar day (UTC)
    in USD equivalent.
    Count each operation once using its source debit.
    """
    if target_date is None:
        target_date = datetime.now(timezone.utc)

    start_of_day = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0, tzinfo=timezone.utc)
    end_of_day = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59, 999999, tzinfo=timezone.utc)

    # 1. Internal & ACH Transfers
    transfers = (
        db.query(Transfer)
        .join(Account, Transfer.from_account_id == Account.id)
        .filter(
            Account.user_id == user_id,
            Transfer.status.in_(["completed", "pending", "settled"]),
            Transfer.created_at >= start_of_day,
            Transfer.created_at <= end_of_day,
        )
        .all()
    )

    total_usd = Decimal("0.00")
    for t in transfers:
        source_cur = t.currency or (t.from_account.currency if t.from_account else "USD")
        amt = Decimal(str(t.amount))
        total_usd += get_usd_equivalent(amt, source_cur)

    # 2. Conversions
    conversions = (
        db.query(Conversion)
        .join(Account, Conversion.from_account_id == Account.id)
        .filter(
            Account.user_id == user_id,
            Conversion.status == "completed",
            Conversion.created_at >= start_of_day,
            Conversion.created_at <= end_of_day,
        )
        .all()
    )

    for c in conversions:
        src_amt = Decimal(str(c.source_amount))
        total_usd += get_usd_equivalent(src_amt, c.source_currency)

    return total_usd.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def get_limits_summary(db: Session, user_id: int) -> TransferLimitsResponse:
    """Return user's transfer limits along with current daily usage and remaining limit."""
    limits = get_or_create_limits(db, user_id)
    daily_total = calculate_daily_total(db, user_id)
    remaining = max(Decimal("0.00"), (limits.daily_limit - daily_total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    return TransferLimitsResponse(
        per_transaction_limit=Decimal(str(limits.per_transaction_limit)),
        daily_limit=Decimal(str(limits.daily_limit)),
        current_daily_total=daily_total,
        remaining_daily_limit=remaining,
        reference_currency="USD",
    )


def validate_transfer_limits(db: Session, user_id: int, amount: Decimal, currency: str = "USD"):
    """
    Validates that a transfer amount does not exceed the per-transaction limit
    and does not cause cumulative transfers for today to exceed the daily limit.
    Evaluated in unrounded USD equivalent (D-07).
    Raises HTTP 400 Bad Request on violation.
    """
    limits = get_or_create_limits(db, user_id)
    usd_equivalent = get_usd_equivalent(Decimal(str(amount)), currency)

    # 1. Check per-transaction limit
    if usd_equivalent > limits.per_transaction_limit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transfer amount (USD equivalent ${usd_equivalent:,.2f}) exceeds per-transaction limit of ${limits.per_transaction_limit:,.2f}",
        )

    # 2. Check daily cumulative limit
    current_daily = calculate_daily_total(db, user_id)
    if (current_daily + usd_equivalent) > limits.daily_limit:
        remaining = max(Decimal("0.00"), (limits.daily_limit - current_daily).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Transfer amount (USD equivalent ${usd_equivalent:,.2f}) would exceed daily limit of ${limits.daily_limit:,.2f}. "
                f"Remaining limit for today is ${remaining:,.2f}."
            ),
        )


def update_limits(db: Session, user_id: int, per_transaction_limit: Decimal, daily_limit: Decimal) -> TransferLimitsResponse:
    """Update transfer limits for user with validation."""
    if per_transaction_limit <= Decimal("0.00") or daily_limit <= Decimal("0.00"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Limits must be strictly positive",
        )
    if per_transaction_limit > daily_limit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Per-transaction limit cannot exceed daily limit",
        )

    limits = get_or_create_limits(db, user_id)
    limits.per_transaction_limit = per_transaction_limit
    limits.daily_limit = daily_limit
    db.commit()
    db.refresh(limits)

    return get_limits_summary(db, user_id)
