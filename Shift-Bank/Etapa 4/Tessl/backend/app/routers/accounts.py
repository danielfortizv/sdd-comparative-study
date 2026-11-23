from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.schemas import AccountResponse
from backend.app.services import account_service

router = APIRouter(prefix="/api/accounts", tags=["Accounts"])


@router.get("", response_model=List[AccountResponse], status_code=status.HTTP_200_OK)
def list_accounts(db: Session = Depends(get_db)):
    """Retrieve all accounts for the authenticated mock user."""
    return account_service.get_user_accounts(db, user_id=account_service.DEFAULT_USER_ID)


@router.get("/{account_id}", response_model=AccountResponse, status_code=status.HTTP_200_OK)
def get_account(account_id: int, db: Session = Depends(get_db)):
    """Retrieve details for a specific user account."""
    return account_service.get_account_by_id(db, account_id, user_id=account_service.DEFAULT_USER_ID)
