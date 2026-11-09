import sqlite3
from typing import Optional
from fastapi import APIRouter, Depends, Header
from ..api.dependencies import get_current_customer
from ..core.database import db_dependency
from ..schemas.transfer import TransferRequest, TransferResponse
from ..services.transfer_service import execute_standard_transfer

router = APIRouter(prefix="/transfers", tags=["transfers"])

@router.post("", response_model=TransferResponse)
def create_transfer(
    request: TransferRequest,
    customer: sqlite3.Row = Depends(get_current_customer),
    conn: sqlite3.Connection = Depends(db_dependency),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """Initiate and execute a transfer between owned accounts."""
    return execute_standard_transfer(conn, customer["id"], request, idempotency_key)
