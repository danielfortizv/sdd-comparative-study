import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from database import get_connection
from fastapi import APIRouter, HTTPException, Response, status
from fastapi.responses import JSONResponse
from models import (
    AccountResponse,
    HistoryEntryResponse,
    MFACodeConfirm,
    MFAConfirmResponse,
    TransferCreate,
    TransferResponse,
)

router = APIRouter()

@router.get("/accounts", response_model=list[AccountResponse])
def get_accounts():
    """Retrieves all seeded accounts from the SQLite database."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, balance, currency FROM accounts ORDER BY name ASC;")
        rows = cursor.fetchall()
        conn.close()

        accounts = []
        for row in rows:
            accounts.append(AccountResponse(
                id=row[0],
                name=row[1],
                balance=row[2],
                currency=row[3]
            ))
        return accounts
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Database query error: {e!s}")


@router.get("/accounts/{account_id}/history", response_model=list[HistoryEntryResponse])
def get_account_history(account_id: str):
    """Retrieves chronological transaction history for a specific account."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # 1. Verify account exists in database
        cursor.execute("SELECT id, name FROM accounts WHERE id = ?;", (account_id,))
        account = cursor.fetchone()
        if not account:
            conn.close()
            raise HTTPException(status_code=404, detail="Account not found.")

        # 2. Query completed transfers where this account is either source or destination
        cursor.execute("""
            SELECT t.id, t.source_account_id, t.destination_account_id, t.amount, t.status, t.created_at,
                   sa.name, da.name
            FROM transfers t
            JOIN accounts sa ON t.source_account_id = sa.id
            JOIN accounts da ON t.destination_account_id = da.id
            WHERE (t.source_account_id = ? OR t.destination_account_id = ?)
              AND t.status = 'COMPLETED'
            ORDER BY t.created_at DESC;
        """, (account_id, account_id))
        rows = cursor.fetchall()
        conn.close()

        # 3. Format history records
        history = []
        for row in rows:
            t_id, src_id, _dest_id, amount, _status, created_at, src_name, dest_name = row
            
            # Determine direction from the perspective of the requested account_id
            direction = "outgoing" if src_id == account_id else "incoming"
            
            # Dynamic descriptive text
            description = f"Transfer from {src_name} to {dest_name}"

            history.append(HistoryEntryResponse(
                id=t_id,
                direction=direction,
                amount=amount,
                description=description,
                date=created_at
            ))
        return history

    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to fetch account history: {e!s}")


@router.post("/transfers", response_model=TransferResponse)
def initiate_transfer(payload: TransferCreate, response: Response):
    """Initiates a standard or sensitive fund transfer.
    If amount is >= COP 1,000,000, enters PENDING_MFA state and returns 202 Accepted.
    Otherwise, executes atomically and immediately returning 200 OK.
    """
    # 1. Validation: Source and destination must be different
    if payload.source_account_id == payload.destination_account_id:
        raise HTTPException(
            status_code=400,
            detail="Source and destination accounts must be different."
        )

    # Convert transfer amount to Decimal
    try:
        transfer_amount = Decimal(payload.amount)
    except InvalidOperation:
        raise HTTPException(status_code=400, detail="Invalid transfer amount.")

    # 2. Open connection
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Retrieve account names to return in response
        cursor.execute(
            "SELECT id, name, balance FROM accounts WHERE id IN (?, ?);",
            (payload.source_account_id, payload.destination_account_id)
        )
        rows = cursor.fetchall()
        accounts_dict = {row[0]: {"name": row[1], "balance": Decimal(row[2])} for row in rows}

        if payload.source_account_id not in accounts_dict or payload.destination_account_id not in accounts_dict:
            conn.close()
            raise HTTPException(status_code=400, detail="One or both accounts do not exist.")

        source_acc = accounts_dict[payload.source_account_id]
        dest_acc = accounts_dict[payload.destination_account_id]

        transfer_id = f"tr_{uuid.uuid4().hex[:8]}"
        created_at_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # 3. Check balance sufficiency first (overdraft validation)
        if source_acc["balance"] < transfer_amount:
            conn.execute("BEGIN TRANSACTION;")
            cursor.execute(
                """INSERT INTO transfers (id, source_account_id, destination_account_id, amount, status, created_at, expires_at)
                   VALUES (?, ?, ?, ?, 'FAILED', ?, NULL);""",
                (transfer_id, payload.source_account_id, payload.destination_account_id, f"{transfer_amount:.2f}", created_at_iso)
            )
            conn.commit()
            conn.close()
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient funds. Required {transfer_amount:.2f} but {source_acc['name']} has {source_acc['balance']:.2f}."
            )

        # 4. Intercept sensitive transfers (amount >= COP 1,000,000)
        if transfer_amount >= Decimal("1000000.00"):
            # Set 5 minutes expiration window
            expires_at_dt = datetime.now(timezone.utc) + timedelta(minutes=5)
            expires_at_iso = expires_at_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

            # Write PENDING_MFA record to SQLite database (no balance modification)
            conn.execute("BEGIN TRANSACTION;")
            cursor.execute(
                """INSERT INTO transfers (id, source_account_id, destination_account_id, amount, status, created_at, expires_at)
                   VALUES (?, ?, ?, ?, 'PENDING_MFA', ?, ?);""",
                (transfer_id, payload.source_account_id, payload.destination_account_id, f"{transfer_amount:.2f}", created_at_iso, expires_at_iso)
            )
            conn.commit()
            conn.close()

            # Override default status code with 202 Accepted
            response.status_code = status.HTTP_202_ACCEPTED
            return TransferResponse(
                id=transfer_id,
                source_account=source_acc["name"],
                destination_account=dest_acc["name"],
                amount=f"{transfer_amount:.2f}",
                status="PENDING_MFA",
                created_at=created_at_iso,
                expires_at=expires_at_iso
            )

        # 5. Standard Transfer Execution (< COP 1,000,000)
        conn.execute("BEGIN TRANSACTION;")
        # Calculate new balances
        new_source_balance = source_acc["balance"] - transfer_amount
        new_dest_balance = dest_acc["balance"] + transfer_amount

        cursor.execute("UPDATE accounts SET balance = ? WHERE id = ?;", (f"{new_source_balance:.2f}", payload.source_account_id))
        cursor.execute("UPDATE accounts SET balance = ? WHERE id = ?;", (f"{new_dest_balance:.2f}", payload.destination_account_id))
        cursor.execute(
            """INSERT INTO transfers (id, source_account_id, destination_account_id, amount, status, created_at, expires_at)
               VALUES (?, ?, ?, ?, 'COMPLETED', ?, NULL);""",
            (transfer_id, payload.source_account_id, payload.destination_account_id, f"{transfer_amount:.2f}", created_at_iso)
        )
        conn.commit()
        conn.close()

        return TransferResponse(
            id=transfer_id,
            source_account=source_acc["name"],
            destination_account=dest_acc["name"],
            amount=f"{transfer_amount:.2f}",
            status="COMPLETED",
            created_at=created_at_iso,
            expires_at=None
        )

    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        conn.execute("ROLLBACK;")
        conn.close()
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected transaction error occurred: {e!s}"
        )


@router.post("/transfers/{transfer_id}/mfa", response_model=MFAConfirmResponse)
def confirm_mfa(transfer_id: str, payload: MFACodeConfirm):
    """Submits the MFA code to finalize a sensitive pending transfer.
    Evaluates expiration, code validity, and balance sufficiency atomically.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Fetch pending transfer record
    cursor.execute(
        "SELECT id, source_account_id, destination_account_id, amount, status, expires_at FROM transfers WHERE id = ?;",
        (transfer_id,)
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Transfer not found.")

    _tx_id, src_id, dest_id, amount_str, status_str, expires_at_iso = row
    transfer_amount = Decimal(amount_str)

    # 2. Check if transfer status is currently PENDING_MFA
    if status_str != "PENDING_MFA":
        conn.close()
        raise HTTPException(status_code=400, detail="Transfer is not pending MFA confirmation.")

    # 3. On-Demand Expiration check
    if expires_at_iso:
        # Parse ISO timestamps to datetime objects (handling 'Z' or offset strings safely)
        expires_at_dt = datetime.fromisoformat(expires_at_iso.replace("Z", "+00:00"))
        current_time_dt = datetime.now(timezone.utc)

        if current_time_dt > expires_at_dt:
            # Atomic transition to EXPIRED
            conn.execute("BEGIN TRANSACTION;")
            cursor.execute("UPDATE transfers SET status = 'EXPIRED' WHERE id = ?;", (transfer_id,))
            conn.commit()
            conn.close()
            return JSONResponse(
                status_code=410,
                content={
                    "id": transfer_id,
                    "status": "EXPIRED",
                    "detail": "MFA verification window has expired."
                }
            )

    # 4. MFA Code Verification
    # Standard mock verification code is exactly "123456"
    if payload.code != "123456":
        conn.close()
        return JSONResponse(
            status_code=401,
            content={
                "id": transfer_id,
                "status": "PENDING_MFA",
                "detail": "Invalid MFA verification code. Please retry."
            }
        )

    # 5. Correct code submitted within window: Execute Atomic Transaction
    conn.execute("BEGIN TRANSACTION;")
    try:
        # Re-fetch source and destination current balances for re-validation
        cursor.execute(
            "SELECT id, name, balance FROM accounts WHERE id IN (?, ?);",
            (src_id, dest_id)
        )
        acc_rows = cursor.fetchall()
        accounts_dict = {r[0]: {"name": r[1], "balance": Decimal(r[2])} for r in acc_rows}

        source_acc = accounts_dict[src_id]
        dest_acc = accounts_dict[dest_id]

        # 6. Re-validate funds sufficiency at confirmation time
        if source_acc["balance"] < transfer_amount:
            # Balance insufficient: transition transfer record permanently to FAILED
            cursor.execute("UPDATE transfers SET status = 'FAILED' WHERE id = ?;", (transfer_id,))
            conn.commit()
            conn.close()
            return JSONResponse(
                status_code=409,
                content={
                    "id": transfer_id,
                    "status": "FAILED",
                    "detail": "Insufficient funds at confirmation time."
                }
            )

        # 7. Balance math in Decimal
        new_source_balance = source_acc["balance"] - transfer_amount
        new_dest_balance = dest_acc["balance"] + transfer_amount

        # Update accounts table
        cursor.execute("UPDATE accounts SET balance = ? WHERE id = ?;", (f"{new_source_balance:.2f}", src_id))
        cursor.execute("UPDATE accounts SET balance = ? WHERE id = ?;", (f"{new_dest_balance:.2f}", dest_id))
        
        # Update transfer record to COMPLETED
        cursor.execute("UPDATE transfers SET status = 'COMPLETED' WHERE id = ?;", (transfer_id,))

        conn.commit()
        conn.close()

        return MFAConfirmResponse(
            id=transfer_id,
            status="COMPLETED",
            message="Transfer executed successfully."
        )

    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        conn.execute("ROLLBACK;")
        conn.close()
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected confirmation transaction error occurred: {e!s}"
        )
