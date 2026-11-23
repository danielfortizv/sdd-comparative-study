from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from backend.app.models import MfaState

MOCK_PIN = "1234"
MAX_ATTEMPTS = 3
SENSITIVE_THRESHOLD = Decimal("1000.00")


def get_or_create_mfa_state(db: Session, user_id: int) -> MfaState:
    """Retrieve or initialize the MFA state for the given user."""
    state = db.query(MfaState).filter(MfaState.user_id == user_id).first()
    if not state:
        state = MfaState(
            user_id=user_id,
            failed_attempts=0,
            is_locked=False,
            threshold=SENSITIVE_THRESHOLD,
        )
        db.add(state)
        db.commit()
        db.refresh(state)
    return state


def get_mfa_status(db: Session, user_id: int) -> dict:
    """Get the current MFA configuration and lockout status."""
    state = get_or_create_mfa_state(db, user_id)
    remaining = max(0, MAX_ATTEMPTS - state.failed_attempts)
    return {
        "threshold": state.threshold,
        "locked": state.is_locked,
        "remaining_attempts": remaining,
    }


def verify_pin(db: Session, user_id: int, pin: str, commit: bool = True) -> bool:
    """
    Validate the provided PIN against the mock PIN.
    Tracks failed attempts and applies lockout if 3 consecutive failures occur.
    Guarantees security state changes and audit events commit atomically.
    When commit=False (during financial transfers), successful verification avoids
    prematurely committing or releasing transaction locks, allowing the outer transaction
    to commit the entire financial operation atomically.
    """
    from backend.app.services import audit_service

    state = get_or_create_mfa_state(db, user_id)

    if state.is_locked:
        db.rollback()
        audit_service.record_audit_event(
            db=db,
            event_type="mfa_lockout_rejected",
            status="FAILURE",
            details={"reason": "MFA_ACCOUNT_LOCKED", "max_attempts": MAX_ATTEMPTS},
            actor_id=user_id,
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="MFA verification is locked due to 3 failed attempts. Please contact support.",
        )

    if pin == MOCK_PIN:
        # Success: reset failed attempts and record audit event
        state.failed_attempts = 0
        audit_service.record_audit_event(
            db=db,
            event_type="mfa_verified",
            status="SUCCESS",
            details={"auth_method": "security_pin", "status": "verified"},
            actor_id=user_id,
        )
        if commit:
            db.commit()
        return True

    # Failed attempt: rollback any caller-staged financial mutations before recording failure state
    db.rollback()
    state = get_or_create_mfa_state(db, user_id)
    state.failed_attempts += 1

    if state.failed_attempts >= MAX_ATTEMPTS:
        state.is_locked = True
        audit_service.record_audit_event(
            db=db,
            event_type="mfa_locked",
            status="FAILURE",
            details={"reason": "MFA_LOCKED", "attempts": MAX_ATTEMPTS},
            actor_id=user_id,
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="MFA verification is locked due to 3 failed attempts. Please contact support.",
        )

    remaining = MAX_ATTEMPTS - state.failed_attempts
    audit_service.record_audit_event(
        db=db,
        event_type="mfa_attempt_failed",
        status="FAILURE",
        details={"failed_attempt_number": state.failed_attempts, "remaining_attempts": remaining},
        actor_id=user_id,
    )
    db.commit()
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Invalid Security PIN. {remaining} attempt(s) remaining.",
    )


def reset_lockout(db: Session, user_id: int) -> MfaState:
    """Admin/testing helper to reset lockout and failed attempts."""
    state = get_or_create_mfa_state(db, user_id)
    state.failed_attempts = 0
    state.is_locked = False
    db.commit()
    db.refresh(state)
    return state
