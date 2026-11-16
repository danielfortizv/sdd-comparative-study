"""Domain Services for Shift Bank Stage 2 & Stage 3

This module encapsulates core business logic for:
- Authenticated field-level encryption at rest and exact Python Decimal arithmetic (E3-ENC-01).
- Append-only, tamper-evident HMAC-SHA256 audit logging with contiguous sequencing (E3-AUD-01).
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
    AuditVerificationResponse,
    BeneficiaryCreate,
    BeneficiaryResponse,
    LimitResponse,
    LimitUpdate,
    RecurringScheduleCreate,
    RecurringScheduleResponse,
)
from crypto import (
    compute_hmac,
    compute_payload_digest,
    decrypt_at_rest,
    encrypt_at_rest,
    get_audit_signing_key,
    is_encrypted,
)
from database import get_connection, get_next_audit_sequence


def decrypt_val(val: str | None) -> str | None:
    """Helper to decrypt an at-rest ciphertext string if encrypted."""
    if val is None:
        return None
    if is_encrypted(val):
        return decrypt_at_rest(val)
    return val


def encrypt_val(val: str | None) -> str | None:
    """Helper to encrypt a string for at-rest storage.
    Fails closed: never falls back to plaintext if encryption fails (FR-006, E3-ENC-01).
    """
    if val is None:
        return None
    if is_encrypted(val):
        return val
    return encrypt_at_rest(val)


def encrypt_if_configured(val: str | None) -> str | None:
    return encrypt_val(val)


# ==============================================================================
# Audit Ledger Domain Services (E3-AUD-01, FR-014..FR-023, T020..T022)
# ==============================================================================

def append_audit_record(
    cursor: sqlite3.Cursor,
    event_type: str,
    actor_id: str = "user_mock_001",
    resource_id: str | None = None,
    payload_metadata: dict | None = None,
    timestamp: str | None = None,
) -> int:
    """
    Appends an immutable, chained audit log record within the current active database transaction (FR-014..FR-017).
    Guarantees contiguous sequence numbers and keyed HMAC-SHA256 linkage to previous entry.
    """
    now_iso = timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    seq_id, previous_hash = get_next_audit_sequence(cursor)

    meta = payload_metadata or {}
    payload_digest = compute_payload_digest(meta)

    res_str = resource_id or ""
    chain_message = f"{previous_hash}{seq_id}{now_iso}{event_type}{actor_id}{res_str}{payload_digest}".encode("utf-8")
    signing_key = get_audit_signing_key()
    record_hmac = compute_hmac(signing_key, chain_message)

    cursor.execute("""
        INSERT INTO audit_logs (id, timestamp, event_type, actor_id, resource_id, payload_digest, previous_hash, record_hmac)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """, (seq_id, now_iso, event_type, actor_id, resource_id, payload_digest, previous_hash, record_hmac))

    return seq_id


def log_rejection_audit_event(
    event_type: str,
    actor_id: str = "user_mock_001",
    resource_id: str | None = None,
    metadata: dict | None = None,
) -> None:
    """
    Records a rejection or authorization failure event in a separate atomic audit transaction (FR-018).
    If audit persistence fails, prioritizes security by raising an exception rather than proceeding unrecorded.
    """
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE;")
        cursor = conn.cursor()
        append_audit_record(
            cursor=cursor,
            event_type=event_type,
            actor_id=actor_id,
            resource_id=resource_id,
            payload_metadata=metadata,
        )
        conn.commit()
    except Exception as e:
        try:
            conn.execute("ROLLBACK;")
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Security audit logging failed: {e}"
        )
    finally:
        conn.close()


def verify_audit_ledger(
    conn: sqlite3.Connection,
    expected_head_hash: str | None = None,
    expected_count: int | None = None,
) -> AuditVerificationResponse:
    """
    Verifies the integrity of the audit ledger from genesis to head (FR-021..FR-023).
    Validates sequence continuity, previous_hash linkage, and entry HMAC-SHA256 digests.
    Detects tail truncation when expected_head_hash/expected_count checkpoints are provided.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT id, timestamp, event_type, actor_id, resource_id, payload_digest, previous_hash, record_hmac FROM audit_logs ORDER BY id ASC;")
    rows = cursor.fetchall()

    signing_key = get_audit_signing_key()
    prev_hash = "0000000000000000000000000000000000000000000000000000000000000000"
    expected_seq = 1

    for row in rows:
        seq_id, ts, event_type, actor_id, res_id, digest, row_prev_hash, record_hmac = row

        # 1. Sequence continuity check
        if seq_id != expected_seq:
            return AuditVerificationResponse(
                is_valid=False,
                verified_records=expected_seq - 1,
                latest_sequence=seq_id,
                latest_hash=record_hmac,
                details=f"Sequence discontinuity: Expected {expected_seq} but found {seq_id}",
                broken_sequence=seq_id,
            )

        # 2. Previous hash link check
        if row_prev_hash != prev_hash:
            return AuditVerificationResponse(
                is_valid=False,
                verified_records=expected_seq - 1,
                latest_sequence=seq_id,
                latest_hash=record_hmac,
                details=f"Hash chain broken at sequence {seq_id}: previous_hash does not match predecessor",
                broken_sequence=seq_id,
            )

        # 3. Recompute HMAC check
        res_str = res_id or ""
        chain_message = f"{row_prev_hash}{seq_id}{ts}{event_type}{actor_id}{res_str}{digest}".encode("utf-8")
        expected_hmac = compute_hmac(signing_key, chain_message)

        if record_hmac != expected_hmac:
            return AuditVerificationResponse(
                is_valid=False,
                verified_records=expected_seq - 1,
                latest_sequence=seq_id,
                latest_hash=record_hmac,
                details=f"HMAC mismatch at sequence {seq_id}: Record data or digest has been altered",
                broken_sequence=seq_id,
            )

        prev_hash = record_hmac
        expected_seq += 1

    total_verified = len(rows)
    latest_hash = rows[-1][7] if rows else prev_hash
    latest_seq = rows[-1][0] if rows else 0

    # 4. Check external trusted checkpoint if supplied (FR-023)
    if expected_count is not None:
        if latest_seq < expected_count:
            return AuditVerificationResponse(
                is_valid=False,
                verified_records=total_verified,
                latest_sequence=latest_seq,
                latest_hash=latest_hash,
                details=f"Tail truncation detected: Expected at least {expected_count} records from trusted checkpoint, but found only {latest_seq}",
                broken_sequence=latest_seq + 1,
                tail_truncation_detected=True,
                expected_head=expected_head_hash,
            )
        elif latest_seq == expected_count and expected_head_hash and latest_hash != expected_head_hash:
            return AuditVerificationResponse(
                is_valid=False,
                verified_records=total_verified,
                latest_sequence=latest_seq,
                latest_hash=latest_hash,
                details=f"Tail tampering detected: Head hash {latest_hash} does not match trusted checkpoint {expected_head_hash}",
                broken_sequence=latest_seq,
                tail_truncation_detected=True,
                expected_head=expected_head_hash,
            )

    return AuditVerificationResponse(
        is_valid=True,
        verified_records=total_verified,
        latest_sequence=latest_seq,
        latest_hash=latest_hash,
        details="Audit chain verified intact from genesis to head.",
        broken_sequence=None,
        tail_truncation_detected=False,
    )


# ==============================================================================
# Limits Domain Services (LIM-01..09)
# ==============================================================================

def get_utc_day_boundaries(reference_time: datetime | None = None) -> tuple[str, str]:
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
        dec_str = decrypt_val(row[0])
        total += Decimal(dec_str)
    return total


def get_limits(conn: sqlite3.Connection, user_id: str = "user_mock_001") -> LimitResponse:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT per_transfer_limit, daily_limit, updated_at FROM limits WHERE user_id = ?;",
        (user_id,)
    )
    row = cursor.fetchone()

    if not row:
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        enc_per = encrypt_val("5000000.00")
        enc_daily = encrypt_val("10000000.00")
        cursor.execute("""
            INSERT OR REPLACE INTO limits (id, user_id, per_transfer_limit, daily_limit, updated_at)
            VALUES ('lim_mock_001', ?, ?, ?, ?);
        """, (user_id, enc_per, enc_daily, now_iso))
        conn.commit()
        per_transfer_str, daily_str, updated_at = "5000000.00", "10000000.00", now_iso
    else:
        per_transfer_str, daily_str, updated_at = row
        per_transfer_str = decrypt_val(per_transfer_str)
        daily_str = decrypt_val(daily_str)

    per_transfer_dec = Decimal(per_transfer_str)
    daily_dec = Decimal(daily_str)

    consumption_dec = get_daily_consumption(conn, user_id)
    remaining_availability = max(Decimal("0.00"), daily_dec - consumption_dec)

    return LimitResponse(
        per_transfer_limit=f"{per_transfer_dec:.2f}",
        daily_limit=f"{daily_dec:.2f}",
        current_daily_consumption=f"{consumption_dec:.2f}",
        remaining_daily_availability=f"{remaining_availability:.2f}",
        updated_at=updated_at,
    )


def update_limits(conn: sqlite3.Connection, payload: LimitUpdate, user_id: str = "user_mock_001") -> LimitResponse:
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cursor = conn.cursor()

    per_dec = Decimal(payload.per_transfer_limit)
    daily_dec = Decimal(payload.daily_limit)

    enc_per = encrypt_val(f"{per_dec:.2f}")
    enc_daily = encrypt_val(f"{daily_dec:.2f}")

    conn.execute("BEGIN IMMEDIATE;")
    try:
        cursor.execute("""
            INSERT INTO limits (id, user_id, per_transfer_limit, daily_limit, updated_at)
            VALUES ('lim_mock_001', ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                per_transfer_limit = excluded.per_transfer_limit,
                daily_limit = excluded.daily_limit,
                updated_at = excluded.updated_at;
        """, (user_id, enc_per, enc_daily, now_iso))

        # Atomic audit log write (FR-014..FR-017)
        append_audit_record(
            cursor=cursor,
            event_type="LIMITS_UPDATED",
            actor_id=user_id,
            resource_id="lim_mock_001",
            payload_metadata={
                "per_transfer_limit": f"{per_dec:.2f}",
                "daily_limit": f"{daily_dec:.2f}",
            },
        )
        conn.commit()
    except Exception:
        conn.execute("ROLLBACK;")
        raise

    return get_limits(conn, user_id)


def validate_transfer_limits(
    conn: sqlite3.Connection,
    amount: Decimal,
    user_id: str = "user_mock_001",
    cursor: sqlite3.Cursor | None = None,
) -> None:
    limits = get_limits(conn, user_id)
    per_transfer_limit = Decimal(limits.per_transfer_limit)
    remaining_availability = Decimal(limits.remaining_daily_availability)

    if amount > per_transfer_limit:
        meta = {
            "reason": "Exceeded per-transfer limit",
            "amount": f"{amount:.2f}",
            "limit": f"{per_transfer_limit:.2f}",
        }
        if cursor is not None:
            append_audit_record(
                cursor=cursor,
                event_type="TRANSFER_REJECTED",
                actor_id=user_id,
                resource_id="REJECTED_OPERATION",
                payload_metadata=meta,
            )
        else:
            log_rejection_audit_event(
                event_type="TRANSFER_REJECTED",
                actor_id=user_id,
                metadata=meta,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transfer amount {amount:.2f} exceeds per-transfer limit of {per_transfer_limit:.2f}."
        )

    if amount > remaining_availability:
        meta = {
            "reason": "Exceeded daily remaining availability",
            "amount": f"{amount:.2f}",
            "remaining": f"{remaining_availability:.2f}",
        }
        if cursor is not None:
            append_audit_record(
                cursor=cursor,
                event_type="TRANSFER_REJECTED",
                actor_id=user_id,
                resource_id="REJECTED_OPERATION",
                payload_metadata=meta,
            )
        else:
            log_rejection_audit_event(
                event_type="TRANSFER_REJECTED",
                actor_id=user_id,
                metadata=meta,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transfer amount {amount:.2f} exceeds remaining daily limit availability of {remaining_availability:.2f}."
        )


# ==============================================================================
# Beneficiary Domain Services (User Story 2)
# ==============================================================================

def list_beneficiaries(conn: sqlite3.Connection, user_id: str = "user_mock_001") -> list[BeneficiaryResponse]:
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
            name=decrypt_val(r[1]),
            bank_name=decrypt_val(r[2]),
            routing_number=decrypt_val(r[3]),
            account_number=decrypt_val(r[4]),
            created_at=r[5],
        )
        for r in rows
    ]


def create_beneficiary(
    conn: sqlite3.Connection,
    payload: BeneficiaryCreate,
    user_id: str = "user_mock_001",
) -> BeneficiaryResponse:
    ben_id = f"ben_{uuid.uuid4().hex[:8]}"
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    cursor = conn.cursor()
    conn.execute("BEGIN IMMEDIATE;")
    try:
        cursor.execute("""
            INSERT INTO beneficiaries (id, user_id, name, bank_name, routing_number, account_number, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (
            ben_id, user_id,
            encrypt_val(payload.name),
            encrypt_val(payload.bank_name),
            encrypt_val(payload.routing_number),
            encrypt_val(payload.account_number),
            now_iso
        ))

        # Atomic audit log write (FR-014..FR-017)
        acc_masked = f"***{payload.account_number[-3:]}" if len(payload.account_number) >= 3 else "***"
        append_audit_record(
            cursor=cursor,
            event_type="BENEFICIARY_CREATED",
            actor_id=user_id,
            resource_id=ben_id,
            payload_metadata={
                "name": payload.name,
                "bank_name": payload.bank_name,
                "account_number": acc_masked,
            },
        )
        conn.commit()
    except Exception:
        conn.execute("ROLLBACK;")
        raise

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
    cursor = conn.cursor()
    conn.execute("BEGIN IMMEDIATE;")
    try:
        cursor.execute("DELETE FROM beneficiaries WHERE id = ? AND user_id = ?;", (beneficiary_id, user_id))
        deleted = cursor.rowcount > 0
        if deleted:
            append_audit_record(
                cursor=cursor,
                event_type="BENEFICIARY_DELETED",
                actor_id=user_id,
                resource_id=beneficiary_id,
            )
        conn.commit()
        return deleted
    except Exception:
        conn.execute("ROLLBACK;")
        raise


# ==============================================================================
# ACH Transfer Domain Services (User Story 2)
# ==============================================================================

def process_ach_transfer(
    conn: sqlite3.Connection,
    payload: AchTransferCreate,
    user_id: str = "user_mock_001",
) -> tuple[int, AchTransferResponse]:
    amount = Decimal(payload.amount)
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, balance FROM accounts WHERE id = ?;", (payload.source_account_id,))
    source_acc = cursor.fetchone()
    if not source_acc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Source account does not exist.")

    src_id, src_name, src_balance_str = source_acc
    source_balance = Decimal(decrypt_val(src_balance_str))

    if source_balance < amount:
        log_rejection_audit_event(
            event_type="ACH_TRANSFER_REJECTED",
            actor_id=user_id,
            metadata={"reason": "Insufficient funds", "amount": f"{amount:.2f}", "balance": f"{source_balance:.2f}"},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient funds. Required {amount:.2f} but {src_name} has {source_balance:.2f}."
        )

    validate_transfer_limits(conn, amount, user_id)

    transfer_id = f"tr_ach_{uuid.uuid4().hex[:8]}"
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    conn.execute("BEGIN IMMEDIATE;")
    try:
        if payload.save_beneficiary:
            cursor.execute("SELECT id, routing_number, account_number FROM beneficiaries WHERE user_id = ?;", (user_id,))
            bens = cursor.fetchall()
            existing_ben = next(
                (b for b in bens if decrypt_val(b[1]) == payload.routing_number and decrypt_val(b[2]) == payload.account_number),
                None
            )
            if not existing_ben:
                new_ben_id = f"ben_{uuid.uuid4().hex[:8]}"
                cursor.execute("""
                    INSERT INTO beneficiaries (id, user_id, name, bank_name, routing_number, account_number, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                """, (
                    new_ben_id, user_id,
                    encrypt_val(payload.recipient_name),
                    encrypt_val(payload.bank_name),
                    encrypt_val(payload.routing_number),
                    encrypt_val(payload.account_number),
                    now_iso
                ))
                append_audit_record(
                    cursor=cursor,
                    event_type="BENEFICIARY_CREATED",
                    actor_id=user_id,
                    resource_id=new_ben_id,
                    payload_metadata={"name": payload.recipient_name, "bank": payload.bank_name},
                )

        acc_masked = f"***{payload.account_number[-3:]}" if len(payload.account_number) >= 3 else "***"

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
                transfer_id, src_id,
                encrypt_val(f"{amount:.2f}"),
                now_iso, expires_at_iso,
                encrypt_val(payload.recipient_name),
                encrypt_val(payload.bank_name),
                encrypt_val(payload.routing_number),
                encrypt_val(payload.account_number)
            ))

            append_audit_record(
                cursor=cursor,
                event_type="ACH_TRANSFER_PENDING_MFA",
                actor_id=user_id,
                resource_id=transfer_id,
                payload_metadata={"amount": f"{amount:.2f}", "recipient": payload.recipient_name, "account": acc_masked},
            )
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

        new_balance = source_balance - amount
        cursor.execute("UPDATE accounts SET balance = ? WHERE id = ?;", (encrypt_val(f"{new_balance:.2f}"), src_id))
        cursor.execute("""
            INSERT INTO transfers (
                id, source_account_id, destination_account_id, amount, status, created_at, expires_at,
                transfer_type, recipient_name, bank_name, routing_number, account_number
            )
            VALUES (?, ?, NULL, ?, 'PENDING', ?, NULL, 'ACH', ?, ?, ?, ?);
        """, (
            transfer_id, src_id,
            encrypt_val(f"{amount:.2f}"),
            now_iso,
            encrypt_val(payload.recipient_name),
            encrypt_val(payload.bank_name),
            encrypt_val(payload.routing_number),
            encrypt_val(payload.account_number)
        ))

        append_audit_record(
            cursor=cursor,
            event_type="ACH_TRANSFER_PENDING",
            actor_id=user_id,
            resource_id=transfer_id,
            payload_metadata={"amount": f"{amount:.2f}", "recipient": payload.recipient_name, "account": acc_masked},
        )
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


def settle_eligible_ach_transfers(conn: sqlite3.Connection, delay_seconds: int = 10) -> int:
    cutoff_dt = datetime.now(timezone.utc) - timedelta(seconds=delay_seconds)
    cutoff_iso = cutoff_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    cursor = conn.cursor()
    conn.execute("BEGIN IMMEDIATE;")
    try:
        cursor.execute("""
            SELECT id FROM transfers
            WHERE transfer_type = 'ACH'
              AND status = 'PENDING'
              AND created_at <= ?;
        """, (cutoff_iso,))
        eligible_ids = [r[0] for r in cursor.fetchall()]

        cursor.execute("""
            UPDATE transfers
            SET status = 'SETTLED', settled_at = ?
            WHERE transfer_type = 'ACH'
              AND status = 'PENDING'
              AND created_at <= ?;
        """, (now_iso, cutoff_iso))

        for tx_id in eligible_ids:
            append_audit_record(
                cursor=cursor,
                event_type="ACH_TRANSFER_SETTLED",
                actor_id="system_scheduler",
                resource_id=tx_id,
            )

        conn.commit()
        return len(eligible_ids)
    except Exception:
        conn.execute("ROLLBACK;")
        raise


def fail_ach_transfer(conn: sqlite3.Connection, transfer_id: str) -> dict:
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cursor = conn.cursor()

    conn.execute("BEGIN IMMEDIATE;")
    try:
        cursor.execute(
            "SELECT id, source_account_id, amount, status, transfer_type FROM transfers WHERE id = ?;",
            (transfer_id,)
        )
        row = cursor.fetchone()
        if not row:
            conn.execute("ROLLBACK;")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transfer not found.")

        _id, src_id, amount_str, current_status, _type = row
        refund_amount = Decimal(decrypt_val(amount_str))

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

        cursor.execute("SELECT balance FROM accounts WHERE id = ?;", (src_id,))
        acc_row = cursor.fetchone()
        if acc_row:
            current_bal = Decimal(decrypt_val(acc_row[0]))
            new_bal = current_bal + refund_amount
            cursor.execute("UPDATE accounts SET balance = ? WHERE id = ?;", (encrypt_val(f"{new_bal:.2f}"), src_id))

        append_audit_record(
            cursor=cursor,
            event_type="ACH_TRANSFER_FAILED",
            actor_id="system_scheduler",
            resource_id=transfer_id,
            payload_metadata={"refund_amount": f"{refund_amount:.2f}"},
        )
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
# Recurring Payment Schedule Domain Services (User Story 3)
# ==============================================================================

def _calculate_first_due_date(now_utc: datetime, frequency: str, start_date: str | None) -> str:
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
    now_utc = datetime.now(timezone.utc)
    now_iso = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    amount = Decimal(payload.amount)

    cursor = conn.cursor()

    cursor.execute("SELECT id, name FROM accounts WHERE id = ?;", (payload.source_account_id,))
    source_acc = cursor.fetchone()
    if not source_acc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Source account does not exist.")
    src_id, src_name = source_acc

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

    next_due_date = _calculate_first_due_date(now_utc, payload.frequency, payload.start_date)
    schedule_id = f"rec_{uuid.uuid4().hex[:8]}"

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
            encrypt_val(payload.recipient_name),
            encrypt_val(payload.bank_name),
            encrypt_val(payload.routing_number),
            encrypt_val(payload.account_number),
            encrypt_val(f"{amount:.2f}"),
            payload.frequency, sched_status, payload.start_date, next_due_date,
            mfa_expires_at, now_iso
        ))

        append_audit_record(
            cursor=cursor,
            event_type="RECURRING_SCHEDULE_CREATED",
            actor_id=user_id,
            resource_id=schedule_id,
            payload_metadata={"amount": f"{amount:.2f}", "frequency": payload.frequency, "status": sched_status},
        )
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
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cursor = conn.cursor()

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
        rec_name = decrypt_val(r[6])
        bank = decrypt_val(r[7])
        acc = decrypt_val(r[9])
        amt = Decimal(decrypt_val(r[10]))

        dest_display = _format_schedule_destination({
            "transfer_type": r[1],
            "destination_account_id": r[4],
            "dest_account_name": r[5],
            "recipient_name": rec_name,
            "bank_name": bank,
            "account_number": acc,
        })
        results.append(
            RecurringScheduleResponse(
                id=r[0],
                transfer_type=r[1],
                source_account_id=r[2],
                source_account=r[3],
                destination_display=dest_display,
                amount=f"{amt:.2f}",
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
            append_audit_record(cursor, "RECURRING_MFA_EXPIRED", user_id, schedule_id)
            conn.commit()
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="MFA verification window has expired.")

    if code != "123456":
        log_rejection_audit_event("RECURRING_MFA_FAILED", user_id, schedule_id, {"reason": "Invalid code"})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA verification code.")

    conn.execute("BEGIN IMMEDIATE;")
    try:
        cursor.execute("""
            UPDATE recurring_schedules
            SET status = 'ACTIVE', mfa_expires_at = NULL
            WHERE id = ?;
        """, (schedule_id,))

        append_audit_record(cursor, "RECURRING_MFA_VERIFIED", user_id, schedule_id)
        append_audit_record(cursor, "RECURRING_SCHEDULE_ACTIVATED", user_id, schedule_id)
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
        append_audit_record(cursor, "RECURRING_SCHEDULE_PAUSED", user_id, schedule_id)
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
        append_audit_record(cursor, "RECURRING_SCHEDULE_RESUMED", user_id, schedule_id)
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
        append_audit_record(cursor, "RECURRING_SCHEDULE_CANCELLED", user_id, schedule_id)
        conn.commit()
    except Exception:
        conn.execute("ROLLBACK;")
        raise

    return get_recurring_schedule(conn, schedule_id, user_id)


def execute_due_recurring_schedules(conn: sqlite3.Connection) -> tuple[int, int]:
    now_utc = datetime.now(timezone.utc)
    now_iso = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    cursor = conn.cursor()

    conn.execute("BEGIN IMMEDIATE;")
    processed_count = 0
    failed_count = 0

    try:
        cursor.execute("""
            UPDATE recurring_schedules
            SET status = 'EXPIRED'
            WHERE status = 'PENDING_MFA'
              AND mfa_expires_at IS NOT NULL
              AND mfa_expires_at < ?;
        """, (now_iso,))

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

            transfer_amount = Decimal(decrypt_val(s_amount_str))
            advanced_due_iso = _calculate_next_interval_due_date(s_due_iso, s_freq)

            cursor.execute("SELECT balance, name FROM accounts WHERE id = ?;", (s_src_id,))
            src_row = cursor.fetchone()
            if not src_row:
                failed_count += 1
                cursor.execute("UPDATE recurring_schedules SET next_due_date = ?, last_executed_at = ? WHERE id = ?;", (advanced_due_iso, now_iso, s_id))
                append_audit_record(cursor, "RECURRING_EXECUTION_FAILED", s_user_id, s_id, {"reason": "Source account missing"})
                continue

            src_balance = Decimal(decrypt_val(src_row[0]))
            if src_balance < transfer_amount:
                failed_count += 1
                cursor.execute("UPDATE recurring_schedules SET next_due_date = ?, last_executed_at = ? WHERE id = ?;", (advanced_due_iso, now_iso, s_id))
                append_audit_record(cursor, "RECURRING_EXECUTION_FAILED", s_user_id, s_id, {"reason": "Insufficient balance"})
                continue

            try:
                validate_transfer_limits(conn, transfer_amount, s_user_id)
            except HTTPException:
                failed_count += 1
                cursor.execute("UPDATE recurring_schedules SET next_due_date = ?, last_executed_at = ? WHERE id = ?;", (advanced_due_iso, now_iso, s_id))
                append_audit_record(cursor, "RECURRING_EXECUTION_FAILED", s_user_id, s_id, {"reason": "Limit exceeded"})
                continue

            # Execute Transfer
            new_src_balance = src_balance - transfer_amount
            cursor.execute("UPDATE accounts SET balance = ? WHERE id = ?;", (encrypt_val(f"{new_src_balance:.2f}"), s_src_id))

            tx_id = f"tr_rec_{uuid.uuid4().hex[:8]}"

            if s_type == "INTERNAL":
                cursor.execute("SELECT balance FROM accounts WHERE id = ?;", (s_dest_id,))
                dest_row = cursor.fetchone()
                if dest_row:
                    dest_balance = Decimal(decrypt_val(dest_row[0]))
                    new_dest_balance = dest_balance + transfer_amount
                    cursor.execute("UPDATE accounts SET balance = ? WHERE id = ?;", (encrypt_val(f"{new_dest_balance:.2f}"), s_dest_id))

                cursor.execute("""
                    INSERT INTO transfers (
                        id, source_account_id, destination_account_id, amount, status, created_at, expires_at, transfer_type
                    )
                    VALUES (?, ?, ?, ?, 'COMPLETED', ?, NULL, 'INTERNAL');
                """, (tx_id, s_src_id, s_dest_id, encrypt_val(f"{transfer_amount:.2f}"), now_iso))
            else:
                cursor.execute("""
                    INSERT INTO transfers (
                        id, source_account_id, destination_account_id, amount, status, created_at, expires_at,
                        transfer_type, recipient_name, bank_name, routing_number, account_number
                    )
                    VALUES (?, ?, NULL, ?, 'PENDING', ?, NULL, 'ACH', ?, ?, ?, ?);
                """, (
                    tx_id, s_src_id, encrypt_val(f"{transfer_amount:.2f}"), now_iso,
                    s_rec_name, s_bank_name, s_routing, s_account
                ))

            cursor.execute("""
                UPDATE recurring_schedules
                SET next_due_date = ?, last_executed_at = ?
                WHERE id = ?;
            """, (advanced_due_iso, now_iso, s_id))

            append_audit_record(
                cursor=cursor,
                event_type="RECURRING_TRANSFER_EXECUTED",
                actor_id=s_user_id,
                resource_id=s_id,
                payload_metadata={"amount": f"{transfer_amount:.2f}", "tx_id": tx_id},
            )
            processed_count += 1

        conn.commit()
        return (processed_count, failed_count)
    except Exception:
        conn.execute("ROLLBACK;")
        raise
