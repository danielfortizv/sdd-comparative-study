"""Domain Services for Shift Bank Stage 2

This module encapsulates core business logic for:
- Dynamic Limits calculation and enforcement within half-open UTC boundaries (LIM-01..09, D-01, D-07, F-04, F-09).
- External ACH Beneficiaries Create, List, and Delete with strict validation (ACH-01..03, D-08).
- Simulated Third-Party ACH Transfers with immediate debit, recipient snapshots, and MFA (ACH-04..10, D-06).
- Autonomous ACH Settlement after 10-second eligibility delay (ACH-06, F-03).
- Deterministic ACH Failure Simulation and Atomic Single Refund (ACH-07, F-05).
- Exact Decimal financial math and zero SQLite SUM() on TEXT columns.
"""

import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from models import (
    AchTransferCreate,
    AchTransferResponse,
    BeneficiaryCreate,
    BeneficiaryResponse,
    LimitResponse,
    LimitUpdate,
    RecurringScheduleCreate,
    RecurringScheduleResponse,
)


def get_utc_day_boundaries(reference_time: datetime | None = None) -> tuple[str, str]:
    """Returns normalized ISO-8601 UTC strings for [start_of_day, next_day_start) (F-04).
    This half-open window reliably aggregates all movements for the UTC day, including
    timestamps with fractional seconds, while strictly excluding the next day.
    """
    ref = reference_time or datetime.now(timezone.utc)
    ref_utc = ref.astimezone(timezone.utc)
    start_of_day = ref_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    next_day_start = start_of_day + timedelta(days=1)
    return (
        start_of_day.strftime("%Y-%m-%dT00:00:00Z"),
        next_day_start.strftime("%Y-%m-%dT00:00:00Z"),
    )


def get_daily_consumption(
    conn: sqlite3.Connection,
    user_id: str = "user_mock_001",
    reference_time: datetime | None = None,
) -> Decimal:
    """Calculates cumulative daily consumption for eligible transfers within the UTC day.
    Eligible statuses: 'COMPLETED', 'PENDING', 'SETTLED' (LIM-06, D-06).
    Excludes: 'FAILED' and 'EXPIRED'.
    PRECISION INVARIANT: Amounts are stored as TEXT; direct SQLite SUM() is strictly prohibited.
    Values are fetched and aggregated in Python Decimal.
    """
    start_iso, next_start_iso = get_utc_day_boundaries(reference_time)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT t.amount
        FROM transfers t
        WHERE t.source_account_id IN (SELECT id FROM accounts)
          AND t.created_at >= ? AND t.created_at < ?
          AND t.status IN ('COMPLETED', 'PENDING', 'SETTLED');
    """, (start_iso, next_start_iso))

    rows = cursor.fetchall()
    total = Decimal("0.00")
    for row in rows:
        total += Decimal(row[0])
    return total


def get_limits(conn: sqlite3.Connection, user_id: str = "user_mock_001") -> LimitResponse:
    """Retrieves configured limits and dynamically calculates current daily consumption
    and remaining daily availability (never negative, clamped to Decimal('0.00')) (D-07).
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT per_transfer_limit, daily_limit, updated_at FROM limits WHERE user_id = ?;",
        (user_id,)
    )
    row = cursor.fetchone()

    if not row:
        # Fallback to defaults if record missing (COP 5M / COP 10M) (D-01)
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        cursor.execute("""
            INSERT OR REPLACE INTO limits (id, user_id, per_transfer_limit, daily_limit, updated_at)
            VALUES ('lim_mock_001', ?, '5000000.00', '10000000.00', ?);
        """, (user_id, now_iso))
        conn.commit()
        per_transfer_str, daily_str, updated_at = "5000000.00", "10000000.00", now_iso
    else:
        per_transfer_str, daily_str, updated_at = row

    per_transfer_dec = Decimal(per_transfer_str)
    daily_dec = Decimal(daily_str)

    consumption_dec = get_daily_consumption(conn, user_id)
    remaining_dec = max(Decimal("0.00"), daily_dec - consumption_dec)

    return LimitResponse(
        per_transfer_limit=f"{per_transfer_dec:.2f}",
        daily_limit=f"{daily_dec:.2f}",
        current_daily_consumption=f"{consumption_dec:.2f}",
        remaining_daily_availability=f"{remaining_dec:.2f}",
        updated_at=updated_at,
    )


def update_limits(
    conn: sqlite3.Connection,
    payload: LimitUpdate,
    user_id: str = "user_mock_001",
) -> LimitResponse:
    """Updates per-transfer and daily limits with immediate effect (LIM-02, D-01, D-07)."""
    per_transfer_dec = Decimal(payload.per_transfer_limit)
    daily_dec = Decimal(payload.daily_limit)

    if per_transfer_dec <= 0 or daily_dec <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limits must be strictly positive amounts."
        )

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE limits
        SET per_transfer_limit = ?, daily_limit = ?, updated_at = ?
        WHERE user_id = ?;
    """, (f"{per_transfer_dec:.2f}", f"{daily_dec:.2f}", now_iso, user_id))

    if cursor.rowcount == 0:
        cursor.execute("""
            INSERT INTO limits (id, user_id, per_transfer_limit, daily_limit, updated_at)
            VALUES ('lim_mock_001', ?, ?, ?, ?);
        """, (user_id, f"{per_transfer_dec:.2f}", f"{daily_dec:.2f}", now_iso))

    conn.commit()
    return get_limits(conn, user_id)


def validate_transfer_limits(
    conn: sqlite3.Connection,
    amount: Decimal,
    user_id: str = "user_mock_001",
) -> None:
    """Validates dynamic limits strictly BEFORE sensitive MFA evaluation (LIM-07, A14, F-09).
    Rejects immediately with HTTP 400 Bad Request if transfer amount exceeds either limit.
    """
    limits = get_limits(conn, user_id)
    per_transfer_limit = Decimal(limits.per_transfer_limit)
    remaining_availability = Decimal(limits.remaining_daily_availability)

    if amount > per_transfer_limit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transfer amount {amount:.2f} exceeds per-transfer limit of {per_transfer_limit:.2f}."
        )

    if amount > remaining_availability:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transfer amount {amount:.2f} exceeds remaining daily limit availability of {remaining_availability:.2f}."
        )


# ==============================================================================
# Beneficiary Domain Services (User Story 2, T020)
# ==============================================================================

def list_beneficiaries(conn: sqlite3.Connection, user_id: str = "user_mock_001") -> list[BeneficiaryResponse]:
    """Retrieves all saved ACH beneficiaries belonging to the user (ACH-02)."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, bank_name, routing_number, account_number, created_at
        FROM beneficiaries
        WHERE user_id = ?
        ORDER BY created_at DESC;
    """, (user_id,))
    rows = cursor.fetchall()
    return [
        BeneficiaryResponse(
            id=r[0],
            name=r[1],
            bank_name=r[2],
            routing_number=r[3],
            account_number=r[4],
            created_at=r[5],
        )
        for r in rows
    ]


def create_beneficiary(
    conn: sqlite3.Connection,
    payload: BeneficiaryCreate,
    user_id: str = "user_mock_001",
) -> BeneficiaryResponse:
    """Creates and persists an external ACH beneficiary with strict routing and account validation (ACH-01..03, D-08)."""
    ben_id = f"ben_{uuid.uuid4().hex[:8]}"
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO beneficiaries (id, user_id, name, bank_name, routing_number, account_number, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?);
    """, (ben_id, user_id, payload.name, payload.bank_name, payload.routing_number, payload.account_number, now_iso))
    conn.commit()

    return BeneficiaryResponse(
        id=ben_id,
        name=payload.name,
        bank_name=payload.bank_name,
        routing_number=payload.routing_number,
        account_number=payload.account_number,
        created_at=now_iso,
    )


def delete_beneficiary(
    conn: sqlite3.Connection,
    beneficiary_id: str,
    user_id: str = "user_mock_001",
) -> bool:
    """Deletes a saved beneficiary belonging to the customer.
    Recipient snapshots in past transfers and recurring schedules are strictly preserved (REC-11, D-08).
    """
    cursor = conn.cursor()
    cursor.execute("DELETE FROM beneficiaries WHERE id = ? AND user_id = ?;", (beneficiary_id, user_id))
    conn.commit()
    return cursor.rowcount > 0


# ==============================================================================
# ACH Transfer Domain Services (User Story 2, T021)
# ==============================================================================

def process_ach_transfer(
    conn: sqlite3.Connection,
    payload: AchTransferCreate,
    user_id: str = "user_mock_001",
) -> tuple[int, AchTransferResponse]:
    """Processes an ACH transfer (ad hoc or saved beneficiary) with:
    - Pre-MFA dynamic limits validation (LIM-07, A14, F-09).
    - Immediate source debit for standard transfers (< COP 1M) in PENDING status (ACH-05, A07).
    - PENDING_MFA intercept for sensitive transfers (>= COP 1M) without immediate debit (D-03).
    - Immutable recipient snapshot capture (D-08).
    - Optional save beneficiary on creation (ACH-04).
    """
    amount = Decimal(payload.amount)
    cursor = conn.cursor()

    # 1. Verify source account exists and check balance
    cursor.execute("SELECT id, name, balance FROM accounts WHERE id = ?;", (payload.source_account_id,))
    source_acc = cursor.fetchone()
    if not source_acc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Source account does not exist.")

    src_id, src_name, src_balance_str = source_acc
    source_balance = Decimal(src_balance_str)

    if source_balance < amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient funds. Required {amount:.2f} but {src_name} has {source_balance:.2f}."
        )

    # 2. Dynamic limits validation evaluated strictly BEFORE MFA (F-09)
    validate_transfer_limits(conn, amount, user_id)

    transfer_id = f"tr_ach_{uuid.uuid4().hex[:8]}"
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    conn.execute("BEGIN IMMEDIATE;")
    try:
        # 3. Optional save beneficiary
        if payload.save_beneficiary:
            cursor.execute("""
                SELECT id FROM beneficiaries
                WHERE user_id = ? AND routing_number = ? AND account_number = ?;
            """, (user_id, payload.routing_number, payload.account_number))
            existing_ben = cursor.fetchone()
            if not existing_ben:
                new_ben_id = f"ben_{uuid.uuid4().hex[:8]}"
                cursor.execute("""
                    INSERT INTO beneficiaries (id, user_id, name, bank_name, routing_number, account_number, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                """, (new_ben_id, user_id, payload.recipient_name, payload.bank_name, payload.routing_number, payload.account_number, now_iso))

        # 4. Handle Sensitive ACH Transfer (amount >= COP 1,000,000.00) (D-03)
        if amount >= Decimal("1000000.00"):
            expires_at_dt = datetime.now(timezone.utc) + timedelta(minutes=5)
            expires_at_iso = expires_at_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

            cursor.execute("""
                INSERT INTO transfers (
                    id, source_account_id, destination_account_id, amount, status, created_at, expires_at,
                    transfer_type, recipient_name, bank_name, routing_number, account_number
                )
                VALUES (?, ?, NULL, ?, 'PENDING_MFA', ?, ?, 'ACH', ?, ?, ?, ?);
            """, (
                transfer_id, src_id, f"{amount:.2f}", now_iso, expires_at_iso,
                payload.recipient_name, payload.bank_name, payload.routing_number, payload.account_number
            ))
            conn.commit()

            return (
                status.HTTP_202_ACCEPTED,
                AchTransferResponse(
                    id=transfer_id,
                    transfer_type="ACH",
                    source_account=src_name,
                    recipient_name=payload.recipient_name,
                    bank_name=payload.bank_name,
                    routing_number=payload.routing_number,
                    account_number=payload.account_number,
                    amount=f"{amount:.2f}",
                    status="PENDING_MFA",
                    created_at=now_iso,
                    expires_at=expires_at_iso,
                ),
            )

        # 5. Standard ACH Transfer (< COP 1,000,000.00): Immediate Debit & PENDING status (ACH-05, A07)
        new_balance = source_balance - amount
        cursor.execute("UPDATE accounts SET balance = ? WHERE id = ?;", (f"{new_balance:.2f}", src_id))
        cursor.execute("""
            INSERT INTO transfers (
                id, source_account_id, destination_account_id, amount, status, created_at, expires_at,
                transfer_type, recipient_name, bank_name, routing_number, account_number
            )
            VALUES (?, ?, NULL, ?, 'PENDING', ?, NULL, 'ACH', ?, ?, ?, ?);
        """, (
            transfer_id, src_id, f"{amount:.2f}", now_iso,
            payload.recipient_name, payload.bank_name, payload.routing_number, payload.account_number
        ))
        conn.commit()
    except Exception:
        conn.execute("ROLLBACK;")
        raise

    return (
        status.HTTP_201_CREATED,
        AchTransferResponse(
            id=transfer_id,
            transfer_type="ACH",
            source_account=src_name,
            recipient_name=payload.recipient_name,
            bank_name=payload.bank_name,
            routing_number=payload.routing_number,
            account_number=payload.account_number,
            amount=f"{amount:.2f}",
            status="PENDING",
            created_at=now_iso,
            expires_at=None,
        ),
    )


# ==============================================================================
# Autonomous Settlement & Failure Simulation (User Story 2, T019, T022)
# ==============================================================================

def settle_eligible_ach_transfers(conn: sqlite3.Connection, delay_seconds: int = 10) -> int:
    """Settles all eligible PENDING ACH transfers older than delay_seconds (ACH-06, F-03).
    Guarantees no secondary debit occurs.
    """
    cutoff_dt = datetime.now(timezone.utc) - timedelta(seconds=delay_seconds)
    cutoff_iso = cutoff_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    cursor = conn.cursor()
    conn.execute("BEGIN IMMEDIATE;")
    try:
        cursor.execute("""
            UPDATE transfers
            SET status = 'SETTLED', settled_at = ?
            WHERE transfer_type = 'ACH'
              AND status = 'PENDING'
              AND created_at <= ?;
        """, (now_iso, cutoff_iso))
        settled_count = cursor.rowcount
        conn.commit()
        return settled_count
    except Exception:
        conn.execute("ROLLBACK;")
        raise


def fail_ach_transfer(conn: sqlite3.Connection, transfer_id: str) -> dict:
    """Simulates deterministic test-only ACH processing failure with atomic, single refund (ACH-07, F-05).
    Guarantees idempotency: returns 409 Conflict if already SETTLED or FAILED.
    """
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cursor = conn.cursor()

    conn.execute("BEGIN IMMEDIATE;")
    try:
        # Check if record exists
        cursor.execute(
            "SELECT id, source_account_id, amount, status, transfer_type FROM transfers WHERE id = ?;",
            (transfer_id,)
        )
        row = cursor.fetchone()
        if not row:
            conn.execute("ROLLBACK;")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transfer not found.")

        _id, src_id, amount_str, current_status, _type = row
        refund_amount = Decimal(amount_str)

        # Conditional update: only PENDING transfers can fail
        cursor.execute("""
            UPDATE transfers
            SET status = 'FAILED', failed_at = ?, refunded_at = ?
            WHERE id = ? AND status = 'PENDING';
        """, (now_iso, now_iso, transfer_id))

        if cursor.rowcount == 0:
            conn.execute("ROLLBACK;")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Transfer cannot be failed from its current status: {current_status}."
            )

        # Atomic single refund: credit source account balance
        cursor.execute("SELECT balance FROM accounts WHERE id = ?;", (src_id,))
        acc_row = cursor.fetchone()
        if acc_row:
            new_bal = Decimal(acc_row[0]) + refund_amount
            cursor.execute("UPDATE accounts SET balance = ? WHERE id = ?;", (f"{new_bal:.2f}", src_id))

        conn.commit()

        return {
            "id": transfer_id,
            "status": "FAILED",
            "refunded_amount": f"{refund_amount:.2f}",
            "message": "Simulated ACH failure processed and refund credited."
        }
    except HTTPException:
        raise
    except Exception:
        conn.execute("ROLLBACK;")
        raise


# ==============================================================================
# Recurring Payment Schedule Domain Services (User Story 3, T031, T032, T033)
# ==============================================================================

def _calculate_first_due_date(now_utc: datetime, frequency: str, start_date: str | None) -> str:
    """Calculates first due date per D-09:
    - Explicit future start date: YYYY-MM-DDT00:00:00Z. Must be strictly future relative to current UTC date.
    - Default (no start date): now_utc + interval (Daily = +24h, Weekly = +7d, Monthly = strictly +30d).
    """
    if start_date:
        today_utc_str = now_utc.strftime("%Y-%m-%d")
        if start_date <= today_utc_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"start_date '{start_date}' must be strictly future relative to current UTC date '{today_utc_str}'."
            )
        return f"{start_date}T00:00:00Z"

    if frequency == "DAILY":
        due_dt = now_utc + timedelta(days=1)
    elif frequency == "WEEKLY":
        due_dt = now_utc + timedelta(days=7)
    elif frequency == "MONTHLY":
        due_dt = now_utc + timedelta(days=30)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid recurring frequency: '{frequency}'."
        )

    return due_dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _calculate_next_interval_due_date(current_due_iso: str, frequency: str) -> str:
    """Advances due date by exactly one frequency interval (D-09, REC-02):
    - DAILY: +24h (+1 day)
    - WEEKLY: +7d (+7 days)
    - MONTHLY: strictly +30d (+30 days, not calendar month!)
    """
    due_dt = datetime.fromisoformat(current_due_iso.replace("Z", "+00:00"))
    if frequency == "DAILY":
        next_dt = due_dt + timedelta(days=1)
    elif frequency == "WEEKLY":
        next_dt = due_dt + timedelta(days=7)
    elif frequency == "MONTHLY":
        next_dt = due_dt + timedelta(days=30)
    else:
        next_dt = due_dt + timedelta(days=1)

    return next_dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _format_schedule_destination(row_dict: dict) -> str:
    """Helper to format destination_display string for schedule responses."""
    if row_dict["transfer_type"] == "INTERNAL":
        return row_dict.get("dest_account_name") or row_dict.get("destination_account_id") or "Internal Account"
    
    rec_name = row_dict.get("recipient_name") or "Beneficiary"
    bank = row_dict.get("bank_name") or "Bank"
    acc = row_dict.get("account_number") or ""
    masked_acc = f"***{acc[-3:]}" if len(acc) >= 3 else acc
    return f"{rec_name} ({bank} {masked_acc})".strip()


def create_recurring_schedule(
    conn: sqlite3.Connection,
    payload: RecurringScheduleCreate,
    user_id: str = "user_mock_001",
) -> tuple[int, RecurringScheduleResponse]:
    """Creates a recurring payment schedule for internal or ACH transfers (REC-01..12).
    - Never debits funds at creation time (D-03).
    - Sensitive schedules (>= COP 1M) enter PENDING_MFA with 300s window (D-03, D-05).
    - Preserves immutable recipient snapshot on creation (D-08).
    """
    now_utc = datetime.now(timezone.utc)
    now_iso = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    amount = Decimal(payload.amount)

    cursor = conn.cursor()

    # 1. Verify source account exists
    cursor.execute("SELECT id, name FROM accounts WHERE id = ?;", (payload.source_account_id,))
    source_acc = cursor.fetchone()
    if not source_acc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Source account does not exist.")
    src_id, src_name = source_acc

    # 2. Validate transfer type targets
    dest_account_name = None
    if payload.transfer_type == "INTERNAL":
        if not payload.destination_account_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="destination_account_id required for INTERNAL schedule.")
        if payload.destination_account_id == payload.source_account_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Source and destination accounts must be different.")
        cursor.execute("SELECT name FROM accounts WHERE id = ?;", (payload.destination_account_id,))
        dest_acc = cursor.fetchone()
        if not dest_acc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Destination account does not exist.")
        dest_account_name = dest_acc[0]

    # 3. Calculate first due date (D-09)
    next_due_date = _calculate_first_due_date(now_utc, payload.frequency, payload.start_date)

    schedule_id = f"rec_{uuid.uuid4().hex[:8]}"

    # 4. MFA evaluation at creation (D-03, D-05)
    if amount >= Decimal("1000000.00"):
        sched_status = "PENDING_MFA"
        expires_at_dt = now_utc + timedelta(minutes=5)
        mfa_expires_at = expires_at_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        resp_status = status.HTTP_202_ACCEPTED
    else:
        sched_status = "ACTIVE"
        mfa_expires_at = None
        resp_status = status.HTTP_201_CREATED

    dest_display = _format_schedule_destination({
        "transfer_type": payload.transfer_type,
        "destination_account_id": payload.destination_account_id,
        "dest_account_name": dest_account_name,
        "recipient_name": payload.recipient_name,
        "bank_name": payload.bank_name,
        "account_number": payload.account_number,
    })

    conn.execute("BEGIN IMMEDIATE;")
    try:
        cursor.execute("""
            INSERT INTO recurring_schedules (
                id, user_id, transfer_type, source_account_id, destination_account_id,
                recipient_name, bank_name, routing_number, account_number,
                amount, frequency, status, start_date, next_due_date,
                last_executed_at, mfa_expires_at, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?);
        """, (
            schedule_id, user_id, payload.transfer_type, src_id, payload.destination_account_id,
            payload.recipient_name, payload.bank_name, payload.routing_number, payload.account_number,
            f"{amount:.2f}", payload.frequency, sched_status, payload.start_date, next_due_date,
            mfa_expires_at, now_iso
        ))
        conn.commit()
    except Exception:
        conn.execute("ROLLBACK;")
        raise

    return (
        resp_status,
        RecurringScheduleResponse(
            id=schedule_id,
            transfer_type=payload.transfer_type,
            source_account_id=src_id,
            source_account=src_name,
            destination_display=dest_display,
            amount=f"{amount:.2f}",
            frequency=payload.frequency,
            status=sched_status,
            next_due_date=next_due_date,
            last_executed_at=None,
            mfa_expires_at=mfa_expires_at,
            created_at=now_iso,
        ),
    )


def list_recurring_schedules(conn: sqlite3.Connection, user_id: str = "user_mock_001") -> list[RecurringScheduleResponse]:
    """Lists all recurring schedules for the user, automatically sweeping expired challenges (REC-05, F-08)."""
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cursor = conn.cursor()

    # 1. On-demand expiration sweep of PENDING_MFA schedules (F-08)
    conn.execute("BEGIN IMMEDIATE;")
    try:
        cursor.execute("""
            UPDATE recurring_schedules
            SET status = 'EXPIRED'
            WHERE user_id = ?
              AND status = 'PENDING_MFA'
              AND mfa_expires_at IS NOT NULL
              AND mfa_expires_at < ?;
        """, (user_id, now_iso))
        conn.commit()
    except Exception:
        conn.execute("ROLLBACK;")
        raise

    # 2. Query schedules
    cursor.execute("""
        SELECT r.id, r.transfer_type, r.source_account_id, sa.name AS source_account_name,
               r.destination_account_id, da.name AS dest_account_name,
               r.recipient_name, r.bank_name, r.routing_number, r.account_number,
               r.amount, r.frequency, r.status, r.next_due_date, r.last_executed_at,
               r.mfa_expires_at, r.created_at
        FROM recurring_schedules r
        JOIN accounts sa ON r.source_account_id = sa.id
        LEFT JOIN accounts da ON r.destination_account_id = da.id
        WHERE r.user_id = ?
        ORDER BY r.created_at DESC;
    """, (user_id,))
    rows = cursor.fetchall()

    results = []
    for r in rows:
        dest_display = _format_schedule_destination({
            "transfer_type": r[1],
            "destination_account_id": r[4],
            "dest_account_name": r[5],
            "recipient_name": r[6],
            "bank_name": r[7],
            "account_number": r[9],
        })
        results.append(
            RecurringScheduleResponse(
                id=r[0],
                transfer_type=r[1],
                source_account_id=r[2],
                source_account=r[3],
                destination_display=dest_display,
                amount=f"{Decimal(r[10]):.2f}",
                frequency=r[11],
                status=r[12],
                next_due_date=r[13],
                last_executed_at=r[14],
                mfa_expires_at=r[15],
                created_at=r[16],
            )
        )
    return results


def get_recurring_schedule(conn: sqlite3.Connection, schedule_id: str, user_id: str = "user_mock_001") -> RecurringScheduleResponse:
    """Retrieves a single recurring schedule by ID."""
    schedules = list_recurring_schedules(conn, user_id)
    sched = next((s for s in schedules if s.id == schedule_id), None)
    if not sched:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurring schedule not found.")
    return sched


def confirm_recurring_schedule_mfa(
    conn: sqlite3.Connection,
    schedule_id: str,
    code: str,
    user_id: str = "user_mock_001",
) -> RecurringScheduleResponse:
    """Validates MFA verification code for a sensitive recurring schedule, activating it (D-03, D-05)."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, status, mfa_expires_at FROM recurring_schedules
        WHERE id = ? AND user_id = ?;
    """, (schedule_id, user_id))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurring schedule not found.")

    _id, current_status, mfa_expires_at = row

    if current_status == "EXPIRED":
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="MFA verification window has expired.")

    if current_status != "PENDING_MFA":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Schedule is not pending MFA confirmation (current status: {current_status}).")

    now_utc = datetime.now(timezone.utc)
    if mfa_expires_at:
        expiry_dt = datetime.fromisoformat(mfa_expires_at.replace("Z", "+00:00"))
        if now_utc > expiry_dt:
            conn.execute("BEGIN IMMEDIATE;")
            cursor.execute("UPDATE recurring_schedules SET status = 'EXPIRED' WHERE id = ?;", (schedule_id,))
            conn.commit()
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="MFA verification window has expired.")

    if code != "123456":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA verification code.")

    conn.execute("BEGIN IMMEDIATE;")
    try:
        cursor.execute("""
            UPDATE recurring_schedules
            SET status = 'ACTIVE', mfa_expires_at = NULL
            WHERE id = ?;
        """, (schedule_id,))
        conn.commit()
    except Exception:
        conn.execute("ROLLBACK;")
        raise

    return get_recurring_schedule(conn, schedule_id, user_id)


def pause_recurring_schedule(
    conn: sqlite3.Connection,
    schedule_id: str,
    user_id: str = "user_mock_001",
) -> RecurringScheduleResponse:
    """Transitions an ACTIVE recurring schedule to PAUSED (REC-06, A18)."""
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM recurring_schedules WHERE id = ? AND user_id = ?;", (schedule_id, user_id))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurring schedule not found.")

    current_status = row[0]
    if current_status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot pause schedule with status '{current_status}'. Only ACTIVE schedules can be paused."
        )

    conn.execute("BEGIN IMMEDIATE;")
    try:
        cursor.execute("UPDATE recurring_schedules SET status = 'PAUSED' WHERE id = ?;", (schedule_id,))
        conn.commit()
    except Exception:
        conn.execute("ROLLBACK;")
        raise

    return get_recurring_schedule(conn, schedule_id, user_id)


def resume_recurring_schedule(
    conn: sqlite3.Connection,
    schedule_id: str,
    user_id: str = "user_mock_001",
) -> RecurringScheduleResponse:
    """Transitions a PAUSED recurring schedule to ACTIVE (REC-08, A18)."""
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM recurring_schedules WHERE id = ? AND user_id = ?;", (schedule_id, user_id))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurring schedule not found.")

    current_status = row[0]
    if current_status != "PAUSED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot resume schedule with status '{current_status}'. Only PAUSED schedules can be resumed."
        )

    conn.execute("BEGIN IMMEDIATE;")
    try:
        cursor.execute("UPDATE recurring_schedules SET status = 'ACTIVE' WHERE id = ?;", (schedule_id,))
        conn.commit()
    except Exception:
        conn.execute("ROLLBACK;")
        raise

    return get_recurring_schedule(conn, schedule_id, user_id)


def cancel_recurring_schedule(
    conn: sqlite3.Connection,
    schedule_id: str,
    user_id: str = "user_mock_001",
) -> RecurringScheduleResponse:
    """Transitions a recurring schedule to terminal CANCELLED state (REC-07, A18)."""
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM recurring_schedules WHERE id = ? AND user_id = ?;", (schedule_id, user_id))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurring schedule not found.")

    current_status = row[0]
    if current_status == "CANCELLED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Schedule is already CANCELLED and cannot be modified."
        )

    conn.execute("BEGIN IMMEDIATE;")
    try:
        cursor.execute("UPDATE recurring_schedules SET status = 'CANCELLED' WHERE id = ?;", (schedule_id,))
        conn.commit()
    except Exception:
        conn.execute("ROLLBACK;")
        raise

    return get_recurring_schedule(conn, schedule_id, user_id)


def execute_due_recurring_schedules(conn: sqlite3.Connection) -> tuple[int, int]:
    """Autonomous execution sweep of all active overdue recurring payment schedules (REC-05, D-04, D-09).
    - Evaluates balance and dynamic limits on every execution.
    - On failure: advances next_due_date by interval without debiting funds (REC-10, A19).
    - On success: debits funds, logs transfer movement, advances next_due_date by interval.
    Returns (processed_count, failed_count).
    """
    now_utc = datetime.now(timezone.utc)
    now_iso = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    cursor = conn.cursor()

    conn.execute("BEGIN IMMEDIATE;")
    processed_count = 0
    failed_count = 0

    try:
        # 1. Sweep expired PENDING_MFA challenges (F-08)
        cursor.execute("""
            UPDATE recurring_schedules
            SET status = 'EXPIRED'
            WHERE status = 'PENDING_MFA'
              AND mfa_expires_at IS NOT NULL
              AND mfa_expires_at < ?;
        """, (now_iso,))

        # 2. Query due ACTIVE schedules
        cursor.execute("""
            SELECT id, user_id, transfer_type, source_account_id, destination_account_id,
                   recipient_name, bank_name, routing_number, account_number,
                   amount, frequency, next_due_date
            FROM recurring_schedules
            WHERE status = 'ACTIVE' AND next_due_date <= ?;
        """, (now_iso,))
        due_schedules = cursor.fetchall()

        for sched in due_schedules:
            (
                s_id, s_user_id, s_type, s_src_id, s_dest_id,
                s_rec_name, s_bank_name, s_routing, s_account,
                s_amount_str, s_freq, s_due_iso
            ) = sched

            transfer_amount = Decimal(s_amount_str)
            advanced_due_iso = _calculate_next_interval_due_date(s_due_iso, s_freq)

            # Re-check source balance
            cursor.execute("SELECT balance, name FROM accounts WHERE id = ?;", (s_src_id,))
            src_row = cursor.fetchone()
            if not src_row:
                failed_count += 1
                cursor.execute("UPDATE recurring_schedules SET next_due_date = ?, last_executed_at = ? WHERE id = ?;", (advanced_due_iso, now_iso, s_id))
                continue

            src_balance = Decimal(src_row[0])
            if src_balance < transfer_amount:
                # Insufficient funds: fail run and advance due date without debiting (REC-10, A19)
                failed_count += 1
                cursor.execute("UPDATE recurring_schedules SET next_due_date = ?, last_executed_at = ? WHERE id = ?;", (advanced_due_iso, now_iso, s_id))
                continue

            # Re-check dynamic limits (LIM-01..09)
            try:
                validate_transfer_limits(conn, transfer_amount, s_user_id)
            except HTTPException:
                # Exceeds limit: fail run and advance due date without debiting (REC-10, A19)
                failed_count += 1
                cursor.execute("UPDATE recurring_schedules SET next_due_date = ?, last_executed_at = ? WHERE id = ?;", (advanced_due_iso, now_iso, s_id))
                continue

            # Financial constraints satisfied: Execute Transfer
            new_src_balance = src_balance - transfer_amount
            cursor.execute("UPDATE accounts SET balance = ? WHERE id = ?;", (f"{new_src_balance:.2f}", s_src_id))

            tx_id = f"tr_rec_{uuid.uuid4().hex[:8]}"

            if s_type == "INTERNAL":
                cursor.execute("SELECT balance FROM accounts WHERE id = ?;", (s_dest_id,))
                dest_row = cursor.fetchone()
                if dest_row:
                    new_dest_balance = Decimal(dest_row[0]) + transfer_amount
                    cursor.execute("UPDATE accounts SET balance = ? WHERE id = ?;", (f"{new_dest_balance:.2f}", s_dest_id))

                cursor.execute("""
                    INSERT INTO transfers (
                        id, source_account_id, destination_account_id, amount, status, created_at, expires_at, transfer_type
                    )
                    VALUES (?, ?, ?, ?, 'COMPLETED', ?, NULL, 'INTERNAL');
                """, (tx_id, s_src_id, s_dest_id, f"{transfer_amount:.2f}", now_iso))
            else:
                # ACH Transfer enters PENDING status (ready for autonomous settlement)
                cursor.execute("""
                    INSERT INTO transfers (
                        id, source_account_id, destination_account_id, amount, status, created_at, expires_at,
                        transfer_type, recipient_name, bank_name, routing_number, account_number
                    )
                    VALUES (?, ?, NULL, ?, 'PENDING', ?, NULL, 'ACH', ?, ?, ?, ?);
                """, (
                    tx_id, s_src_id, f"{transfer_amount:.2f}", now_iso,
                    s_rec_name, s_bank_name, s_routing, s_account
                ))

            # Advance next_due_date by frequency interval and record last_executed_at
            cursor.execute("""
                UPDATE recurring_schedules
                SET next_due_date = ?, last_executed_at = ?
                WHERE id = ?;
            """, (advanced_due_iso, now_iso, s_id))

            processed_count += 1

        conn.commit()
        return (processed_count, failed_count)
    except Exception:
        conn.execute("ROLLBACK;")
        raise

