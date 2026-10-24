import sqlite3
import uuid
import json
import time
from datetime import datetime, timezone
from typing import Optional, Tuple
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from ..schemas.transfer import TransferRequest, TransferResponse, TransferItem, AccountBalanceSummary
from ..schemas.account import format_cents_to_usd
from ..config import IDEMPOTENCY_CACHE_TTL_SECONDS

def check_idempotency_cache(conn: sqlite3.Connection, key: str) -> Optional[JSONResponse]:
    """Retrieve cached response if key exists and is within TTL."""
    cursor = conn.execute(
        "SELECT response_status, response_body, created_at FROM idempotency_cache WHERE key = ?",
        (key,),
    )
    row = cursor.fetchone()
    if row:
        now = int(time.time())
        if now - row["created_at"] < IDEMPOTENCY_CACHE_TTL_SECONDS:
            return JSONResponse(
                status_code=row["response_status"],
                content=json.loads(row["response_body"]),
            )
    return None

def store_idempotency_cache(
    conn: sqlite3.Connection, key: str, status_code: int, body_dict: dict
) -> None:
    """Store transfer response in idempotency cache."""
    now = int(time.time())
    with conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO idempotency_cache (key, response_status, response_body, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (key, status_code, json.dumps(body_dict), now),
        )

def execute_standard_transfer(
    conn: sqlite3.Connection,
    customer_id: str,
    request: TransferRequest,
    idempotency_key: Optional[str] = None,
) -> TransferResponse:
    """
    Execute standard own-account transfer (<= $1,000.00) atomically.
    Enforces ACID transactions, debit/credit, dual movements, and balance conservation.
    """
    # 1. Validate distinct accounts (FR-3)
    if request.from_account_id == request.to_account_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "SAME_ACCOUNT_TRANSFER_NOT_ALLOWED",
                "message": "Source and destination accounts must be different.",
            },
        )

    # 2. Validate positive amount (FR-4)
    if request.amount_cents <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "INVALID_TRANSFER_AMOUNT",
                "message": "Transfer amount must be strictly greater than zero.",
            },
        )

    # 3. Check idempotency cache (FR-7, AD-5)
    if idempotency_key:
        cached_response = check_idempotency_cache(conn, idempotency_key)
        if cached_response:
            return cached_response

    # Begin atomic transaction (AD-2)
    conn.execute("BEGIN IMMEDIATE;")
    try:
        # Check customer balance sum before transfer for conservation invariant
        cursor = conn.execute(
            "SELECT SUM(balance_cents) as total FROM account WHERE customer_id = ?",
            (customer_id,),
        )
        sum_before = cursor.fetchone()["total"]

        # Fetch and verify source account
        cursor = conn.execute(
            "SELECT id, nickname, balance_cents, customer_id FROM account WHERE id = ?",
            (request.from_account_id,),
        )
        source = cursor.fetchone()
        if not source or source["customer_id"] != customer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "UNAUTHORIZED_ACCOUNT",
                    "message": "Source account not found or does not belong to authenticated customer.",
                },
            )

        # Fetch and verify destination account
        cursor = conn.execute(
            "SELECT id, nickname, balance_cents, customer_id FROM account WHERE id = ?",
            (request.to_account_id,),
        )
        dest = cursor.fetchone()
        if not dest or dest["customer_id"] != customer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "UNAUTHORIZED_ACCOUNT",
                    "message": "Destination account not found or does not belong to authenticated customer.",
                },
            )

        # Verify sufficient funds (FR-5)
        if request.amount_cents > source["balance_cents"]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "INSUFFICIENT_FUNDS",
                    "message": f"Source account balance is insufficient for transfer amount.",
                    "details": {
                        "available_cents": source["balance_cents"],
                        "requested_cents": request.amount_cents,
                    },
                },
            )

        new_source_balance = source["balance_cents"] - request.amount_cents
        new_dest_balance = dest["balance_cents"] + request.amount_cents

        # 4. Atomic balance updates
        cursor = conn.execute(
            "UPDATE account SET balance_cents = balance_cents - ? WHERE id = ? AND balance_cents >= ?",
            (request.amount_cents, request.from_account_id, request.amount_cents),
        )
        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "INSUFFICIENT_FUNDS",
                    "message": "Source account balance check failed during update.",
                },
            )

        conn.execute(
            "UPDATE account SET balance_cents = balance_cents + ? WHERE id = ?",
            (request.amount_cents, request.to_account_id),
        )

        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        transfer_id = f"TRF-{uuid.uuid4().hex[:8].upper()}"

        # 5. Insert Transfer record (FR-6)
        conn.execute(
            """
            INSERT INTO transfer (id, source_account_id, destination_account_id, amount_cents, status, idempotency_key, created_at)
            VALUES (?, ?, ?, ?, 'COMPLETED', ?, ?)
            """,
            (transfer_id, request.from_account_id, request.to_account_id, request.amount_cents, idempotency_key, now_iso),
        )

        # 6. Insert Dual-Entry Movements (FR-13, AD-7)
        # Source Debit
        conn.execute(
            """
            INSERT INTO movement (transfer_id, account_id, direction, amount_cents, running_balance_cents, counterparty_account_id, timestamp)
            VALUES (?, ?, 'DEBIT', ?, ?, ?, ?)
            """,
            (transfer_id, request.from_account_id, request.amount_cents, new_source_balance, request.to_account_id, now_iso),
        )
        # Destination Credit
        conn.execute(
            """
            INSERT INTO movement (transfer_id, account_id, direction, amount_cents, running_balance_cents, counterparty_account_id, timestamp)
            VALUES (?, ?, 'CREDIT', ?, ?, ?, ?)
            """,
            (transfer_id, request.to_account_id, request.amount_cents, new_dest_balance, request.from_account_id, now_iso),
        )

        # 7. Verify Balance Conservation Invariant (AD-2)
        cursor = conn.execute(
            "SELECT SUM(balance_cents) as total FROM account WHERE customer_id = ?",
            (customer_id,),
        )
        sum_after = cursor.fetchone()["total"]
        if sum_after != sum_before:
            raise RuntimeError(
                f"Balance conservation violation: before={sum_before}, after={sum_after}"
            )

        # Commit transaction
        conn.execute("COMMIT;")

        response_data = TransferResponse(
            transfer=TransferItem(
                id=transfer_id,
                source_account_id=request.from_account_id,
                destination_account_id=request.to_account_id,
                amount_cents=request.amount_cents,
                amount_formatted=format_cents_to_usd(request.amount_cents),
                status="COMPLETED",
                created_at=now_iso,
            ),
            status="COMPLETED",
            source_account=AccountBalanceSummary(
                id=request.from_account_id,
                balance_cents=new_source_balance,
                balance_formatted=format_cents_to_usd(new_source_balance),
            ),
            destination_account=AccountBalanceSummary(
                id=request.to_account_id,
                balance_cents=new_dest_balance,
                balance_formatted=format_cents_to_usd(new_dest_balance),
            ),
        )

        # Cache response for idempotency
        if idempotency_key:
            store_idempotency_cache(conn, idempotency_key, 200, response_data.model_dump())

        return response_data

    except HTTPException:
        conn.execute("ROLLBACK;")
        raise
    except Exception as exc:
        conn.execute("ROLLBACK;")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "TRANSFER_TRANSACTION_FAILED",
                "message": f"Transfer transaction rolled back: {str(exc)}",
            },
        )
