import sqlite3
from typing import List
from ..schemas.account import AccountResponse

def get_accounts_for_customer(conn: sqlite3.Connection, customer_id: str) -> List[AccountResponse]:
    """Retrieve all accounts owned by the customer sorted by id."""
    cursor = conn.execute(
        """
        SELECT id, customer_id, nickname, account_type, balance_cents
        FROM account
        WHERE customer_id = ?
        ORDER BY id ASC
        """,
        (customer_id,),
    )
    rows = cursor.fetchall()
    return [AccountResponse.from_row(row) for row in rows]
