import sqlite3
from typing import List
from fastapi import APIRouter, Depends
from ..api.dependencies import get_current_customer
from ..core.database import db_dependency
from ..schemas.account import AccountResponse
from ..services.account_service import get_accounts_for_customer

router = APIRouter(prefix="/accounts", tags=["accounts"])

@router.get("", response_model=List[AccountResponse])
def list_accounts(
    customer: sqlite3.Row = Depends(get_current_customer),
    conn: sqlite3.Connection = Depends(db_dependency),
) -> List[AccountResponse]:
    """Retrieve all accounts owned by the authenticated customer."""
    return get_accounts_for_customer(conn, customer["id"])
