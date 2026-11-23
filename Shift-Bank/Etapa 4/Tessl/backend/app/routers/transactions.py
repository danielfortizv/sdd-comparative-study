from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.schemas import TransactionResponse
from backend.app.services import account_service

router = APIRouter(prefix="/api/transactions", tags=["Transactions"])


@router.get("", response_model=List[TransactionResponse], status_code=status.HTTP_200_OK)
def list_transactions(
    account_id: Optional[int] = Query(None, description="Optional account ID filter"),
    db: Session = Depends(get_db),
):
    """Retrieve transaction history for the authenticated user, optionally filtered by account ID."""
    return account_service.get_user_transactions(
        db=db,
        user_id=account_service.DEFAULT_USER_ID,
        account_id=account_id,
    )
