from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.schemas import TransferLimitsResponse, TransferLimitsUpdateRequest
from backend.app.services import limit_service
from backend.app.services.account_service import DEFAULT_USER_ID

router = APIRouter(prefix="/api/limits", tags=["Transfer Limits"])


@router.get("", response_model=TransferLimitsResponse, status_code=status.HTTP_200_OK)
def get_limits(db: Session = Depends(get_db)):
    """Retrieve user's configured transfer limits and today's usage/remaining balance."""
    return limit_service.get_limits_summary(db, DEFAULT_USER_ID)


@router.put("", response_model=TransferLimitsResponse, status_code=status.HTTP_200_OK)
def update_limits(
    request: TransferLimitsUpdateRequest,
    db: Session = Depends(get_db),
):
    """Update configured per-transaction and daily cumulative transfer limits."""
    return limit_service.update_limits(
        db=db,
        user_id=DEFAULT_USER_ID,
        per_transaction_limit=request.per_transaction_limit,
        daily_limit=request.daily_limit,
    )
