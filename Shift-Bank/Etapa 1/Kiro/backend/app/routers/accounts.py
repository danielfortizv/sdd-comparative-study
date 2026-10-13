"""Router de cuentas: GET /api/accounts (Requisitos 2.1, 2.2, 1.5)."""

from fastapi import APIRouter, Depends

from .. import repository
from ..db import get_connection
from ..money import format_cents
from ..schemas import AccountOut, AccountsResponse

router = APIRouter(prefix="/api", tags=["accounts"])


def _conn():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


@router.get("/accounts", response_model=AccountsResponse)
def get_accounts(conn=Depends(_conn)) -> AccountsResponse:
    accounts = repository.list_accounts(conn)
    return AccountsResponse(
        accounts=[
            AccountOut(name=a.display_name, balance=format_cents(a.balance_cents))
            for a in accounts
        ]
    )
