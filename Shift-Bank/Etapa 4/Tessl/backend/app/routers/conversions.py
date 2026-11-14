from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session
from typing import Optional
from backend.app.database import get_db
from backend.app.schemas import (
    ConversionRequest,
    ConversionResponse,
    MfaRequiredResponse,
    ErrorResponse,
)
from backend.app.services import conversion_service, account_service

router = APIRouter(prefix="/api/conversions", tags=["Currency Conversions"])


@router.post(
    "",
    response_model=ConversionResponse,
    status_code=status.HTTP_200_OK,
    responses={
        428: {"model": MfaRequiredResponse, "description": "MFA Security PIN required"},
        400: {"model": ErrorResponse, "description": "Business validation or idempotency error"},
        409: {"model": ErrorResponse, "description": "Concurrency or idempotency key conflict"},
    },
)
def create_conversion(
    request: ConversionRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    """Execute an atomic currency conversion between distinct multicurrency accounts."""
    return conversion_service.execute_conversion(
        db=db,
        request=request,
        idempotency_key=idempotency_key,
        user_id=account_service.DEFAULT_USER_ID,
    )
