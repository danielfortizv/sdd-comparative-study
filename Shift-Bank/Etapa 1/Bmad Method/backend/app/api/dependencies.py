import sqlite3
from typing import Optional
from fastapi import Header, Depends, HTTPException, status
from ..core.database import db_dependency

def get_current_customer(
    x_customer_id: Optional[str] = Header(None, alias="X-Customer-Id"),
    conn: sqlite3.Connection = Depends(db_dependency),
) -> sqlite3.Row:
    if not x_customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "MISSING_CUSTOMER_CONTEXT", "message": "X-Customer-Id header is required."}
        )

    cursor = conn.execute("SELECT id, full_name, email FROM customer WHERE id = ?", (x_customer_id,))
    customer = cursor.fetchone()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "UNAUTHORIZED_CUSTOMER", "message": "Customer identity not recognized or unauthorized."}
        )

    return customer
