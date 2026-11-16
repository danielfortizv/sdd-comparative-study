import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from database import get_connection
from fastapi import APIRouter, HTTPException, Response, status
from fastapi.responses import JSONResponse
from models import (
    AccountResponse,
    AchTransferCreate,
    AchTransferResponse,
    BeneficiaryCreate,
    BeneficiaryResponse,
    HistoryEntryResponse,
    LimitResponse,
    LimitUpdate,
    MFACodeConfirm,
    MFAConfirmResponse,
    RecurringScheduleCreate,
    RecurringScheduleResponse,
    TransferCreate,
    TransferResponse,
)
from services import (
    cancel_recurring_schedule,
    confirm_recurring_schedule_mfa,
    create_beneficiary,
    create_recurring_schedule,
    delete_beneficiary,
    fail_ach_transfer,
    get_limits,
    list_beneficiaries,
    list_recurring_schedules,
    pause_recurring_schedule,
    process_ach_transfer,
    resume_recurring_schedule,
    update_limits,
    validate_transfer_limits,
)

router = APIRouter()


@router.get("/limits", response_model=LimitResponse)
def get_user_limits():
    """Retrieves current transfer limits, UTC consumption, and remaining availability (LIM-01, LIM-02)."""
    conn = get_connection()
    try:
        return get_limits(conn)
    finally:
        conn.close()


@router.put("/limits", response_model=LimitResponse)
def update_user_limits(payload: LimitUpdate):
    """Updates per-transfer and daily maximum limits with immediate effect (LIM-02, D-01, D-07)."""
    conn = get_connection()
    try:
        return update_limits(conn, payload)
    finally:
        conn.close()


# ==============================================================================
# Beneficiaries Endpoints (User Story 2, T023)
# ==============================================================================

@router.get("/beneficiaries", response_model=list[BeneficiaryResponse])
def get_all_beneficiaries():
    """Lists all saved external ACH beneficiaries belonging to the user (ACH-02)."""
    conn = get_connection()
    try:
        return list_beneficiaries(conn)
    finally:
        conn.close()


@router.post("/beneficiaries", response_model=BeneficiaryResponse, status_code=status.HTTP_201_CREATED)
def create_new_beneficiary(payload: BeneficiaryCreate):
    """Saves an external ACH beneficiary for future transfers (ACH-01..03, D-08)."""
    conn = get_connection()
    try:
        return create_beneficiary(conn, payload)
    finally:
        conn.close()


@router.delete("/beneficiaries/{beneficiary_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_beneficiary(beneficiary_id: str):
    """Deletes a saved ACH beneficiary while preserving past transaction snapshots (REC-11, D-08)."""
    conn = get_connection()
    try:
        deleted = delete_beneficiary(conn, beneficiary_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Beneficiary not found.")
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    finally:
        conn.close()

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
    """Retrieves chronological transaction history for a specific account.
    Uses LEFT JOIN and includes multi-state movements (COMPLETED, PENDING, SETTLED, FAILED) (F-02).
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # 1. Verify account exists in database
        cursor.execute("SELECT id, name FROM accounts WHERE id = ?;", (account_id,))
        account = cursor.fetchone()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found.")

        # 2. Query transfers (internal & ACH) where this account is either source or destination (F-02)
        cursor.execute("""
            SELECT t.id, t.source_account_id, t.destination_account_id, t.amount, t.status, t.created_at,
                   sa.name AS source_account_name, da.name AS destination_account_name,
                   t.transfer_type, t.recipient_name, t.bank_name
            FROM transfers t
            JOIN accounts sa ON t.source_account_id = sa.id
            LEFT JOIN accounts da ON t.destination_account_id = da.id
            WHERE (t.source_account_id = ? OR t.destination_account_id = ?)
              AND t.status IN ('COMPLETED', 'PENDING', 'SETTLED', 'FAILED')
            ORDER BY t.created_at DESC;
        """, (account_id, account_id))
        rows = cursor.fetchall()

        # 3. Format history records
        history = []
        for row in rows:
            t_id, src_id, _dest_id, amount, status_str, created_at, src_name, dest_name, tx_type, recipient_name, bank_name = row

            if tx_type == "ACH":
                direction = "outgoing"
                description = f"ACH Transfer to {recipient_name} ({bank_name}) - {status_str}"
            else:
                direction = "outgoing" if src_id == account_id else "incoming"
                if dest_name and src_name:
                    description = f"Transfer from {src_name} to {dest_name}"
                else:
                    description = f"Transfer to {dest_name}" if direction == "outgoing" else f"Transfer from {src_name}"

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
    finally:
        conn.close()


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
    try:
        cursor = conn.cursor()

        # Retrieve account names to return in response
        cursor.execute(
            "SELECT id, name, balance FROM accounts WHERE id IN (?, ?);",
            (payload.source_account_id, payload.destination_account_id)
        )
        rows = cursor.fetchall()
        accounts_dict = {row[0]: {"name": row[1], "balance": Decimal(row[2])} for row in rows}

        if payload.source_account_id not in accounts_dict or payload.destination_account_id not in accounts_dict:
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
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient funds. Required {transfer_amount:.2f} but {source_acc['name']} has {source_acc['balance']:.2f}."
            )

        # 4. Enforce dynamic limits BEFORE sensitive MFA interception (LIM-07, A14, F-09)
        validate_transfer_limits(conn, transfer_amount)

        # 5. Intercept sensitive transfers (amount >= COP 1,000,000)
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

        # 6. Standard Transfer Execution (< COP 1,000,000)
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
        try:
            conn.execute("ROLLBACK;")
        except Exception:
            pass
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected transaction error occurred: {e!s}"
        )
    finally:
        conn.close()


@router.post("/transfers/ach", response_model=AchTransferResponse)
def initiate_ach_transfer(payload: AchTransferCreate, response: Response):
    """Initiates an ACH transfer (ad hoc or saved beneficiary) with immediate debit (ACH-04..05).
    If amount >= COP 1,000,000, intercepts with PENDING_MFA (202 Accepted) (D-03).
    """
    conn = get_connection()
    try:
        status_code, resp_model = process_ach_transfer(conn, payload)
        response.status_code = status_code
        return resp_model
    finally:
        conn.close()


@router.post("/transfers/{transfer_id}/confirm-mfa", response_model=MFAConfirmResponse)
@router.post("/transfers/{transfer_id}/mfa", response_model=MFAConfirmResponse)
def confirm_mfa(transfer_id: str, payload: MFACodeConfirm):
    """Submits the MFA code to finalize a sensitive pending transfer (internal or ACH).
    Evaluates expiration, code validity, balance sufficiency, and limits atomically.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # 1. Fetch pending transfer record
        cursor.execute(
            "SELECT id, source_account_id, destination_account_id, amount, status, expires_at, transfer_type FROM transfers WHERE id = ?;",
            (transfer_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Transfer not found.")

        _tx_id, src_id, dest_id, amount_str, status_str, expires_at_iso, tx_type = row
        transfer_amount = Decimal(amount_str)

        # 2. Check if transfer status is currently PENDING_MFA
        if status_str != "PENDING_MFA":
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
            # Re-fetch source balance for re-validation
            cursor.execute("SELECT id, name, balance FROM accounts WHERE id = ?;", (src_id,))
            src_row = cursor.fetchone()
            if not src_row:
                raise HTTPException(status_code=400, detail="Source account not found.")

            source_balance = Decimal(src_row[2])

            # 6. Re-validate funds sufficiency at confirmation time
            if source_balance < transfer_amount:
                cursor.execute("UPDATE transfers SET status = 'FAILED' WHERE id = ?;", (transfer_id,))
                conn.commit()
                return JSONResponse(
                    status_code=409,
                    content={
                        "id": transfer_id,
                        "status": "FAILED",
                        "detail": "Insufficient funds at confirmation time."
                    }
                )

            # 7. Re-validate dynamic limits at confirmation time (HER-05)
            validate_transfer_limits(conn, transfer_amount)

            # 8. Execute balance math and status transition
            new_source_balance = source_balance - transfer_amount
            cursor.execute("UPDATE accounts SET balance = ? WHERE id = ?;", (f"{new_source_balance:.2f}", src_id))

            if tx_type == "ACH":
                # For ACH transfers: debits source balance and enters PENDING (ready for settlement)
                cursor.execute("UPDATE transfers SET status = 'PENDING' WHERE id = ?;", (transfer_id,))
                conn.commit()
                return MFAConfirmResponse(
                    id=transfer_id,
                    status="PENDING",
                    message="ACH transfer initiated and pending settlement."
                )
            else:
                # For INTERNAL transfers: credits destination account and enters COMPLETED
                cursor.execute("SELECT balance FROM accounts WHERE id = ?;", (dest_id,))
                dest_row = cursor.fetchone()
                if not dest_row:
                    raise HTTPException(status_code=400, detail="Destination account not found.")
                new_dest_balance = Decimal(dest_row[0]) + transfer_amount
                cursor.execute("UPDATE accounts SET balance = ? WHERE id = ?;", (f"{new_dest_balance:.2f}", dest_id))
                cursor.execute("UPDATE transfers SET status = 'COMPLETED' WHERE id = ?;", (transfer_id,))
                conn.commit()

                return MFAConfirmResponse(
                    id=transfer_id,
                    status="COMPLETED",
                    message="Transfer executed successfully."
                )

        except HTTPException:
            try:
                conn.execute("ROLLBACK;")
            except Exception:
                pass
            raise
        except Exception as e:  # noqa: BLE001
            try:
                conn.execute("ROLLBACK;")
            except Exception:
                pass
            raise HTTPException(
                status_code=500,
                detail=f"An unexpected confirmation transaction error occurred: {e!s}"
            )
    finally:
        conn.close()


# ==============================================================================
# Recurring Payment Schedule Endpoints (User Story 3, T034)
# ==============================================================================

@router.get("/recurring-schedules", response_model=list[RecurringScheduleResponse])
def get_user_recurring_schedules():
    """Lists all recurring payment schedules for the customer, automatically sweeping expired challenges (REC-01..12, F-08)."""
    conn = get_connection()
    try:
        return list_recurring_schedules(conn)
    finally:
        conn.close()


@router.post("/recurring-schedules", response_model=RecurringScheduleResponse)
def create_new_recurring_schedule(payload: RecurringScheduleCreate, response: Response):
    """Creates a recurring payment schedule for internal or ACH transfers (REC-01..04).
    If amount >= COP 1,000,000, enters PENDING_MFA with 202 Accepted (D-03).
    """
    conn = get_connection()
    try:
        status_code, resp_model = create_recurring_schedule(conn, payload)
        response.status_code = status_code
        return resp_model
    finally:
        conn.close()


@router.post("/recurring-schedules/{schedule_id}/confirm-mfa", response_model=RecurringScheduleResponse)
def confirm_schedule_mfa(schedule_id: str, payload: MFACodeConfirm):
    """Validates MFA verification code for a sensitive recurring schedule, activating it (D-03, D-05)."""
    conn = get_connection()
    try:
        return confirm_recurring_schedule_mfa(conn, schedule_id, payload.code)
    finally:
        conn.close()


@router.post("/recurring-schedules/{schedule_id}/pause", response_model=RecurringScheduleResponse)
def pause_schedule(schedule_id: str):
    """Pauses an ACTIVE recurring payment schedule (REC-06, A18)."""
    conn = get_connection()
    try:
        return pause_recurring_schedule(conn, schedule_id)
    finally:
        conn.close()


@router.post("/recurring-schedules/{schedule_id}/resume", response_model=RecurringScheduleResponse)
def resume_schedule(schedule_id: str):
    """Resumes a PAUSED recurring payment schedule back to ACTIVE (REC-08, A18)."""
    conn = get_connection()
    try:
        return resume_recurring_schedule(conn, schedule_id)
    finally:
        conn.close()


@router.post("/recurring-schedules/{schedule_id}/cancel", response_model=RecurringScheduleResponse)
def cancel_schedule(schedule_id: str):
    """Permanently cancels a recurring payment schedule (terminal state) (REC-07, A18)."""
    conn = get_connection()
    try:
        return cancel_recurring_schedule(conn, schedule_id)
    finally:
        conn.close()


# ==============================================================================
# Non-Public Test-Only Simulation Endpoints (F-03, F-05, D-04, D-06)
# ==============================================================================

@router.post("/test/ach/{transfer_id}/fail")
def trigger_test_ach_failure(transfer_id: str):
    """Test-only simulation endpoint to deterministically fail a PENDING ACH transfer and issue refund (ACH-07, F-03, F-05)."""
    from main import require_test_endpoints
    require_test_endpoints()

    conn = get_connection()
    try:
        return fail_ach_transfer(conn, transfer_id)
    finally:
        conn.close()


@router.post("/test/ach/settle-pending")
def trigger_test_ach_settlement():
    """Test-only simulation endpoint to force an immediate settlement sweep of eligible PENDING ACH transfers (ACH-06, D-06)."""
    from main import require_test_endpoints
    require_test_endpoints()

    from scheduler import run_ach_settlement_sweep_sync
    settled_count = run_ach_settlement_sweep_sync(delay_seconds=10)
    return {"settled_count": settled_count, "message": "Settlement sweep completed successfully."}


@router.post("/test/recurring/run-due")
def trigger_test_recurring_execution():
    """Test-only simulation endpoint to force an immediate execution sweep of due recurring schedules (REC-05, D-04)."""
    from main import require_test_endpoints
    require_test_endpoints()

    from scheduler import run_recurring_execution_sweep_sync
    processed_count, failed_count = run_recurring_execution_sweep_sync()
    return {
        "processed_count": processed_count,
        "failed_count": failed_count,
        "message": "Recurring execution sweep completed."
    }

