from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.schemas import (
    TransferRequest,
    TransferResponse,
    AchTransferRequest,
    AchTransferResponse,
    MfaRequiredResponse,
    MfaVerifyRequest,
    MfaVerifyResponse,
    MfaStatusResponse,
)
from backend.app.services import transfer_service, mfa_service, account_service

router = APIRouter(prefix="/api", tags=["Transfers & MFA"])


@router.post(
    "/transfers",
    response_model=TransferResponse,
    status_code=status.HTTP_200_OK,
    responses={
        428: {"model": MfaRequiredResponse, "description": "MFA Security PIN required"},
    },
)
def create_transfer(
    request: TransferRequest,
    db: Session = Depends(get_db),
):
    """Execute an internal transfer between user accounts."""
    return transfer_service.execute_transfer(
        db=db,
        user_id=account_service.DEFAULT_USER_ID,
        request=request,
    )


@router.post(
    "/transfers/ach",
    response_model=AchTransferResponse,
    status_code=status.HTTP_200_OK,
    responses={
        428: {"model": MfaRequiredResponse, "description": "MFA Security PIN required"},
    },
)
def create_ach_transfer(
    request: AchTransferRequest,
    db: Session = Depends(get_db),
):
    """Execute an external ACH transfer to a beneficiary or ad-hoc account."""
    return transfer_service.execute_ach_transfer(
        db=db,
        user_id=account_service.DEFAULT_USER_ID,
        request=request,
    )


@router.post("/mfa/verify", response_model=MfaVerifyResponse, status_code=status.HTTP_200_OK)
def verify_mfa_pin(
    request: MfaVerifyRequest,
    db: Session = Depends(get_db),
):
    """Verify security PIN independently and return remaining attempts / lockout status."""
    is_valid = mfa_service.verify_pin(
        db=db,
        user_id=account_service.DEFAULT_USER_ID,
        pin=request.pin,
    )
    status_info = mfa_service.get_mfa_status(db, account_service.DEFAULT_USER_ID)
    return {
        "valid": is_valid,
        "remaining_attempts": status_info["remaining_attempts"],
        "locked": status_info["locked"],
    }


@router.get("/mfa/status", response_model=MfaStatusResponse, status_code=status.HTTP_200_OK)
def get_mfa_status(db: Session = Depends(get_db)):
    """Retrieve the MFA threshold and current lockout state."""
    return mfa_service.get_mfa_status(db, account_service.DEFAULT_USER_ID)
