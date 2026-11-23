import uuid
import logging
from decimal import Decimal
from typing import Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from backend.app.models import Account, Conversion, Transaction
from backend.app.schemas import ConversionRequest, ConversionResponse
from backend.app.services.account_service import get_account_by_id
from backend.app.services.fx_service import calculate_conversion, get_usd_equivalent
from backend.app.services.limit_service import validate_transfer_limits
from backend.app.services.mfa_service import verify_pin
from backend.app.services.transfer_service import MfaRequiredException
from backend.app.services.event_store import append_domain_event, ConcurrencyConflictException
from backend.app.services.projection_service import update_checkpoints
from backend.app.services.idempotency_service import (
    validate_idempotency_key_header,
    compute_fingerprint,
    check_existing_idempotency,
    record_idempotency_commit,
)
from backend.app.services.audit_service import record_audit_event

logger = logging.getLogger("conversion_service")


def execute_conversion(
    db: Session,
    request: ConversionRequest,
    idempotency_key: str,
    user_id: int = 1,
) -> ConversionResponse:
    """Execute atomic currency conversion according to D-01, D-03, D-04, D-07, D-09, D-11, D-13, and D-14."""
    validated_key = validate_idempotency_key_header(idempotency_key)

    # 1. Compute canonical fingerprint (business parameters only)
    fingerprint = compute_fingerprint({
        "from_account_id": request.from_account_id,
        "to_account_id": request.to_account_id,
        "source_amount": str(request.source_amount),
        "expected_from_version": request.expected_from_version,
        "expected_to_version": request.expected_to_version,
        "description": request.description,
    })

    # Check idempotent replay
    existing_result = check_existing_idempotency(db, validated_key, fingerprint)
    if existing_result:
        return ConversionResponse(**existing_result)

    # 2. Account Invariants
    if request.from_account_id == request.to_account_id:
        record_audit_event(
            db=db,
            event_type="currency_conversion",
            status="FAILURE",
            details={"error": "SAME_ACCOUNT_NOT_PERMITTED"},
            actor_id=user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "SAME_ACCOUNT_NOT_PERMITTED", "message": "Source and destination accounts must be distinct"},
        )

    from_acc = get_account_by_id(db, request.from_account_id, user_id)
    to_acc = get_account_by_id(db, request.to_account_id, user_id)

    if from_acc.currency == to_acc.currency:
        record_audit_event(
            db=db,
            event_type="currency_conversion",
            status="FAILURE",
            details={"error": "SAME_CURRENCY_NOT_PERMITTED", "currency": from_acc.currency},
            actor_id=user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "SAME_CURRENCY_NOT_PERMITTED", "message": "Currency conversion requires accounts with different currencies"},
        )

    # 3. Balance Check
    if from_acc.balance < request.source_amount:
        record_audit_event(
            db=db,
            event_type="currency_conversion",
            status="FAILURE",
            details={
                "error": "INSUFFICIENT_FUNDS",
                "available": str(from_acc.balance),
                "requested": str(request.source_amount),
            },
            actor_id=user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INSUFFICIENT_FUNDS", "message": f"Insufficient funds in account {from_acc.account_number}"},
        )

    # 4. FX Calculation
    try:
        dest_amount, rate_display, rate_num, rate_den, residual = calculate_conversion(
            source_amount=request.source_amount,
            source_currency=from_acc.currency,
            destination_currency=to_acc.currency,
        )
    except ValueError as e:
        record_audit_event(
            db=db,
            event_type="currency_conversion",
            status="FAILURE",
            details={"error": "CONVERSION_CALCULATION_ERROR", "reason": str(e)},
            actor_id=user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "CONVERSION_CALCULATION_ERROR", "message": str(e)},
        )

    # 5. Financial Limits Check (Evaluated in unrounded USD equivalent before MFA)
    usd_equiv = get_usd_equivalent(request.source_amount, from_acc.currency)
    try:
        validate_transfer_limits(db, user_id, request.source_amount, from_acc.currency)
    except HTTPException as e:
        record_audit_event(
            db=db,
            event_type="currency_conversion",
            status="FAILURE",
            details={"error": "LIMIT_EXCEEDED", "detail": str(e.detail)},
            actor_id=user_id,
        )
        raise e

    # 6. Mock MFA PIN Challenge if USD equivalent > 1,000.00
    if usd_equiv > Decimal("1000.00"):
        if not request.pin:
            raise MfaRequiredException(
                detail="MFA_REQUIRED",
                message="Security PIN required for conversions exceeding $1,000 USD equivalent",
            )
        verify_pin(db, user_id, request.pin, commit=False)

    # 7. Optimistic Concurrency Check and Atomic Event Append
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
        "source_currency": from_acc.currency,
        "destination_currency": to_acc.currency,
        "source_amount": str(request.source_amount),
        "destination_amount": str(dest_amount),
        "exchange_rate_display": str(rate_display),
        "rate_numerator": rate_num,
        "rate_denominator": rate_den,
        "rate_version": "v1.0-simulated",
        "rounding_residual": str(residual),
        "from_account_version": from_new_version,
        "to_account_version": to_new_version,
        "description": request.description,
    }

    try:
        domain_event = append_domain_event(
            db=db,
            event_type="CurrencyConversionCompleted",
            aggregate_id=f"banking:{user_id}",
            account_ids=[from_acc.id, to_acc.id],
            payload=event_payload,
            idempotency_key=validated_key,
            expected_versions=expected_versions,
        )
    except ConcurrencyConflictException as ce:
        record_audit_event(
            db=db,
            event_type="currency_conversion",
            status="FAILURE",
            details={"error": ce.code, "message": ce.message},
            actor_id=user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": ce.code, "message": ce.message, "details": ce.details},
        )

    # 8. Synchronous CQRS Projection Updates
    from_acc.balance -= request.source_amount
    to_acc.balance += dest_amount

    # Create Conversion record
    conversion = Conversion(
        operation_id=operation_id,
        from_account_id=from_acc.id,
        to_account_id=to_acc.id,
        source_currency=from_acc.currency,
        destination_currency=to_acc.currency,
        source_amount=request.source_amount,
        destination_amount=dest_amount,
        exchange_rate_display=rate_display,
        rate_numerator=rate_num,
        rate_denominator=rate_den,
        rate_version="v1.0-simulated",
        rounding_residual=residual,
        from_account_version=from_new_version,
        to_account_version=to_new_version,
        status="completed",
        description=request.description or f"Conversion from {from_acc.currency} to {to_acc.currency}",
    )
    db.add(conversion)
    db.flush()

    # Create debit Transaction
    debit_tx = Transaction(
        account_id=from_acc.id,
        conversion_id=conversion.id,
        transaction_type="debit",
        amount=request.source_amount,
        balance_after=from_acc.balance,
        currency=from_acc.currency,
        description=request.description or f"Converted to {to_acc.account_name} ({to_acc.currency})",
        reference=f"CNV-{conversion.id:05d}-OUT",
        source_amount=request.source_amount,
        source_currency=from_acc.currency,
        destination_amount=dest_amount,
        destination_currency=to_acc.currency,
        exchange_rate_display=rate_display,
        status="completed",
    )
    # Create credit Transaction
    credit_tx = Transaction(
        account_id=to_acc.id,
        conversion_id=conversion.id,
        transaction_type="credit",
        amount=dest_amount,
        balance_after=to_acc.balance,
        currency=to_acc.currency,
        description=request.description or f"Converted from {from_acc.account_name} ({from_acc.currency})",
        reference=f"CNV-{conversion.id:05d}-IN",
        source_amount=request.source_amount,
        source_currency=from_acc.currency,
        destination_amount=dest_amount,
        destination_currency=to_acc.currency,
        exchange_rate_display=rate_display,
        status="completed",
    )
    db.add_all([debit_tx, credit_tx])

    # Update checkpoints
    update_checkpoints(db, domain_event.id)

    # 9. Audit Log (SUCCESS)
    record_audit_event(
        db=db,
        event_type="currency_conversion",
        status="SUCCESS",
        details={
            "operation_id": operation_id,
            "from_account_id": from_acc.id,
            "to_account_id": to_acc.id,
            "source_currency": from_acc.currency,
            "destination_currency": to_acc.currency,
            "source_amount": str(request.source_amount),
            "destination_amount": str(dest_amount),
            "exchange_rate": str(rate_display),
            "conversion_id": conversion.id,
        },
        actor_id=user_id,
    )

    response_data = {
        "id": conversion.id,
        "operation_id": operation_id,
        "from_account_id": from_acc.id,
        "to_account_id": to_acc.id,
        "source_currency": from_acc.currency,
        "destination_currency": to_acc.currency,
        "source_amount": request.source_amount,
        "destination_amount": dest_amount,
        "exchange_rate_display": rate_display,
        "rate_numerator": rate_num,
        "rate_denominator": rate_den,
        "rate_version": "v1.0-simulated",
        "rounding_residual": residual,
        "from_account_version": from_new_version,
        "to_account_version": to_new_version,
        "status": "completed",
        "description": conversion.description,
        "created_at": conversion.created_at,
    }

    # 10. Record Idempotency
    record_idempotency_commit(
        db=db,
        idempotency_key=validated_key,
        operation_type="conversion",
        operation_id=operation_id,
        fingerprint=fingerprint,
        response_data=response_data,
    )

    db.commit()
    return ConversionResponse(**response_data)
