import json
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from database import get_connection
from fastapi import APIRouter, Header, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from models import (
    AccountResponse,
    AchTransferCreate,
    AchTransferResponse,
    AuditRecordResponse,
    AuditVerificationResponse,
    BeneficiaryCreate,
    BeneficiaryResponse,
    CryptographicEnvelope,
    ConversionCreate,
    ConversionResponse,
    HealthResponse,
    HistoryEntryResponse,
    LimitResponse,
    LimitUpdate,
    MFACodeConfirm,
    MFAConfirmResponse,
    PublicKeyResponse,
    RecurringScheduleCreate,
    RecurringScheduleResponse,
    TransferCreate,
    TransferResponse,
)
from services import (
    append_audit_record,
    cancel_recurring_schedule,
    confirm_recurring_schedule_mfa,
    create_beneficiary,
    create_recurring_schedule,
    decrypt_val,
    delete_beneficiary,
    encrypt_val,
    fail_ach_transfer,
    get_limits,
    list_beneficiaries,
    list_recurring_schedules,
    log_rejection_audit_event,
    pause_recurring_schedule,
    process_ach_transfer,
    resume_recurring_schedule,
    update_limits,
    validate_transfer_limits,
    verify_audit_ledger,
    execute_stage4_command,
    confirm_stage4_mfa,
)
from crypto import (
    DecryptionError,
    get_audit_admin_key,
    load_private_key,
    load_public_key_pem,
    unwrap_and_decrypt_payload,
)

router = APIRouter()


def _decrypt_envelope_to_model(envelope: CryptographicEnvelope, target_model_cls):
    """
    Unwraps and decrypts an incoming client CryptographicEnvelope into the target Pydantic model.
    Raises HTTP 400 Bad Request on missing fields, corrupted ciphertext, tag mismatch, or schema errors.
    Plaintext processing is strictly prohibited (FR-005, FR-006).
    """
    try:
        data_bytes = unwrap_and_decrypt_payload(envelope.model_dump())
        data_dict = json.loads(data_bytes.decode("utf-8"))
        return target_model_cls(**data_dict)
    except DecryptionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid cryptographic envelope: {e}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid decrypted payload format: {e}"
        )


def _require_audit_admin(request: Request) -> None:
    """Verifies that the request includes valid administrative verification credentials (FR-022)."""
    try:
        expected_key = get_audit_admin_key()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Admin key configuration is unavailable."
        )
    provided_key = request.headers.get("X-Audit-Admin-Key")
    if not provided_key or provided_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Valid X-Audit-Admin-Key header required."
        )


# ==============================================================================
# Deployment Health Endpoints (E3-DEP-01, FR-035, T030)
# ==============================================================================

@router.get("/health", response_model=HealthResponse)
def get_health_status():
    """
    Healthcheck endpoint reporting backend health, database connectivity,
    scheduler status, and cryptographic key availability (FR-035, Scenario 4.7).
    Used by Docker Compose healthchecks and Nginx reverse proxy monitoring.
    """
    db_connected = False
    details = []

    # 1. Check database connectivity
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1;")
        cursor.fetchone()
        conn.close()
        db_connected = True
    except Exception as e:
        details.append(f"Database error: {e}")

    # 2. Check cryptographic keys (symmetric storage key, signing key, admin key, RSA keypair)
    crypto_keys_loaded = False
    try:
        import os
        storage_key = os.environ.get("BANK_STORAGE_KEY")
        signing_key = os.environ.get("AUDIT_SIGNING_KEY")
        admin_key = os.environ.get("AUDIT_ADMIN_KEY")
        pub_pem = load_public_key_pem()
        priv_key = load_private_key()
        if storage_key and signing_key and admin_key and pub_pem and priv_key:
            crypto_keys_loaded = True
        else:
            details.append("One or more required cryptographic keys are missing or unreadable.")
    except Exception as e:
        details.append(f"Crypto keys error: {e}")

    # 3. Check scheduler status
    from scheduler import is_scheduler_active
    scheduler_active = is_scheduler_active()

    if not db_connected or not crypto_keys_loaded:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "database": "connected" if db_connected else "error",
                "scheduler_active": scheduler_active,
                "crypto_keys_loaded": crypto_keys_loaded,
                "details": "; ".join(details) or "Backend service unhealthy.",
            }
        )

    return HealthResponse(
        status="healthy",
        database="connected",
        scheduler_active=scheduler_active,
        crypto_keys_loaded=True,
        environment=os.environ.get("ENVIRONMENT", "production"),
    )


# ==============================================================================
# Cryptographic Key Management Endpoints (E3-ENC-01, FR-004, T013)
# ==============================================================================

@router.get("/crypto/public-key", response_model=PublicKeyResponse)
def get_public_key():
    """Retrieves the active RSA public key in PEM format for client-to-server payload encryption (FR-004)."""
    return PublicKeyResponse(
        algorithm="RSA-OAEP-256",
        format="PEM",
        public_key=load_public_key_pem(),
        key_id="bank_pub_v1",
    )


# ==============================================================================
# Audit Verification & Inspection Endpoints (E3-AUD-01, FR-021..FR-023, T023)
# ==============================================================================

@router.get("/audit/verify", response_model=AuditVerificationResponse)
def verify_audit_trail(
    request: Request,
    expected_head_hash: str | None = None,
    expected_count: int | None = None,
):
    """
    Traverses the append-only audit trail and mathematically validates sequence continuity,
    cryptographic HMAC links, and payload digests (FR-021..FR-023).
    Requires administrative authorization header (FR-022).
    """
    _require_audit_admin(request)
    conn = get_connection()
    try:
        return verify_audit_ledger(conn, expected_head_hash, expected_count)
    finally:
        conn.close()


@router.get("/projections/status")
def get_projection_status(request: Request):
    """Returns authorized projection checkpoint metadata without financial payloads."""
    _require_audit_admin(request)
    from projections import projection_status
    conn = get_connection()
    try:
        return projection_status(conn)
    finally:
        conn.close()


@router.post("/projections/rebuild")
def rebuild_account_projection(request: Request):
    """Replays the immutable event stream under admin authorization; fails closed on invariant errors."""
    _require_audit_admin(request)
    from projections import projection_status, rebuild_projection
    conn = get_connection()
    try:
        count = rebuild_projection(conn)
        return {"rebuilt_events": count, **projection_status(conn)}
    except Exception:
        raise HTTPException(status_code=500, detail={"code":"PERSISTENCE_INTEGRITY_FAILURE","message":"Projection replay failed validation"}) from None
    finally:
        conn.close()


@router.get("/audit/records", response_model=list[AuditRecordResponse])
def get_audit_records(
    request: Request,
    limit: int = 50,
    offset: int = 0,
):
    """Retrieves paginated non-sensitive audit metadata for authorized administrators."""
    _require_audit_admin(request)
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, timestamp, event_type, actor_id, resource_id, payload_digest, previous_hash, record_hmac
            FROM audit_logs
            ORDER BY id ASC
            LIMIT ? OFFSET ?;
        """, (limit, offset))
        rows = cursor.fetchall()
        return [
            AuditRecordResponse(
                id=r[0],
                timestamp=r[1],
                event_type=r[2],
                actor_id=r[3],
                resource_id=r[4],
                payload_digest=r[5],
                previous_hash=r[6],
                record_hmac=r[7],
            )
            for r in rows
        ]
    finally:
        conn.close()


# ==============================================================================
# Dynamic Limits Endpoints
# ==============================================================================

@router.get("/limits", response_model=LimitResponse)
def get_user_limits():
    """Retrieves current transfer limits, UTC consumption, and remaining availability (LIM-01, LIM-02)."""
    conn = get_connection()
    try:
        return get_limits(conn)
    finally:
        conn.close()


@router.put("/limits", response_model=LimitResponse)
def update_user_limits(envelope: CryptographicEnvelope):
    """Updates per-transfer and daily maximum limits with immediate effect from encrypted envelope."""
    payload = _decrypt_envelope_to_model(envelope, LimitUpdate)
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
def create_new_beneficiary(envelope: CryptographicEnvelope):
    """Saves an external ACH beneficiary for future transfers from encrypted envelope (ACH-01..03, D-08)."""
    payload = _decrypt_envelope_to_model(envelope, BeneficiaryCreate)
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


# ==============================================================================
# Accounts & History Endpoints
# ==============================================================================

@router.get("/accounts", response_model=list[AccountResponse])
def get_accounts():
    """Retrieves all accounts with balances decrypted in memory."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, balance, currency, version FROM accounts ORDER BY name ASC;")
        rows = cursor.fetchall()
        conn.close()

        accounts = []
        for row in rows:
            accounts.append(AccountResponse(
                id=row[0],
                name=row[1],
                balance=decrypt_val(row[2]),
                currency=row[3],
                version=row[4]
            ))
        return accounts
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Database query error: {e!s}")


@router.get("/accounts/{account_id}/history", response_model=list[HistoryEntryResponse])
def get_account_history(account_id: str):
    """Retrieves chronological transaction history for a specific account with amounts and metadata decrypted."""
    conn = get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT id, name FROM accounts WHERE id = ?;", (account_id,))
        account = cursor.fetchone()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found.")

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

        history = []
        for row in rows:
            t_id, src_id, _dest_id, amount_enc, status_str, created_at, src_name, dest_name, tx_type, rec_name_enc, bank_enc = row

            amount = decrypt_val(amount_enc)
            recipient_name = decrypt_val(rec_name_enc)
            bank_name = decrypt_val(bank_enc)
            counter_amount = counter_currency = None
            rate_numerator = rate_denominator = None

            if tx_type == "ACH":
                direction = "outgoing"
                description = f"ACH Transfer to {recipient_name} ({bank_name}) - {status_str}"
            elif tx_type == "CONVERSION":
                direction = "outgoing" if src_id == account_id else "incoming"
                description = f"Currency conversion from {src_name} to {dest_name}"
                projection = cursor.execute("SELECT event_id FROM history_projection WHERE history_id=?", (f"{t_id}:{account_id}",)).fetchone()
                if projection:
                    raw_event = cursor.execute("SELECT payload_json FROM domain_events WHERE event_id=?", (projection[0],)).fetchone()
                    if raw_event:
                        event_payload = json.loads(decrypt_val(raw_event[0]))
                        rate_numerator = event_payload.get("rate_numerator")
                        rate_denominator = event_payload.get("rate_denominator")
                        if direction == "outgoing":
                            counter_amount = f"{Decimal(event_payload['destination_amount_minor']) / Decimal(100):.2f}"
                            counter_currency = cursor.execute("SELECT currency FROM accounts WHERE id=?", (_dest_id,)).fetchone()[0]
                        else:
                            counter_amount = f"{Decimal(event_payload['source_amount_minor']) / Decimal(100):.2f}"
                            counter_currency = cursor.execute("SELECT currency FROM accounts WHERE id=?", (src_id,)).fetchone()[0]
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
                date=created_at,
                currency=cursor.execute("SELECT currency FROM accounts WHERE id=?", (account_id,)).fetchone()[0],
                counter_amount=counter_amount,
                counter_currency=counter_currency,
                rate_numerator=rate_numerator,
                rate_denominator=rate_denominator
            ))
        return history

    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to fetch account history: {e!s}")
    finally:
        conn.close()


# ==============================================================================
# Transfers Endpoints (Internal & ACH)
# ==============================================================================

@router.post("/transfers", response_model=TransferResponse)
def initiate_transfer(envelope: CryptographicEnvelope, response: Response,
                      idempotency_key: str | None = Header(None, alias="Idempotency-Key")):
    """Initiates a standard or sensitive fund transfer from an encrypted client envelope.
    If amount is >= COP 1,000,000, enters PENDING_MFA state and returns 202 Accepted.
    Otherwise, executes atomically returning 200 OK.
    """
    payload = _decrypt_envelope_to_model(envelope, TransferCreate)

    if idempotency_key is None:
        raise HTTPException(status_code=422, detail={"code": "INVALID_IDEMPOTENCY_KEY", "message": "Idempotency-Key header is required"})
    conn = get_connection()
    try:
        result, replay = execute_stage4_command(conn, "TRANSFER", idempotency_key, payload.model_dump())
        if result["status"] == "PENDING_MFA":
            response.status_code = status.HTTP_202_ACCEPTED
        return TransferResponse.model_validate(result)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail={"code":"PERSISTENCE_INTEGRITY_FAILURE","message":"Transfer could not be persisted safely"}) from None
    finally:
        conn.close()

    if payload.source_account_id == payload.destination_account_id:
        raise HTTPException(
            status_code=400,
            detail="Source and destination accounts must be different."
        )

    try:
        transfer_amount = Decimal(payload.amount)
    except InvalidOperation:
        raise HTTPException(status_code=400, detail="Invalid transfer amount.")

    conn = get_connection()
    try:
        cursor = conn.cursor()

        # 1. Preliminary check of account existence, balances, and limits before acquiring write lock
        cursor.execute(
            "SELECT id, name, balance FROM accounts WHERE id IN (?, ?);",
            (payload.source_account_id, payload.destination_account_id)
        )
        rows = cursor.fetchall()
        accounts_dict = {row[0]: {"name": row[1], "balance": Decimal(decrypt_val(row[2]))} for row in rows}

        if payload.source_account_id not in accounts_dict or payload.destination_account_id not in accounts_dict:
            raise HTTPException(status_code=400, detail="One or both accounts do not exist.")

        source_acc = accounts_dict[payload.source_account_id]
        dest_acc = accounts_dict[payload.destination_account_id]

        transfer_id = f"tr_{uuid.uuid4().hex[:8]}"
        created_at_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        if source_acc["balance"] < transfer_amount:
            conn.execute("BEGIN TRANSACTION;")
            cursor.execute(
                """INSERT INTO transfers (id, source_account_id, destination_account_id, amount, status, created_at, expires_at)
                   VALUES (?, ?, ?, ?, 'FAILED', ?, NULL);""",
                (transfer_id, payload.source_account_id, payload.destination_account_id, encrypt_val(f"{transfer_amount:.2f}"), created_at_iso)
            )
            append_audit_record(
                cursor=cursor,
                event_type="TRANSFER_REJECTED",
                actor_id="user_mock_001",
                resource_id=transfer_id,
                payload_metadata={
                    "reason": "Insufficient funds",
                    "amount": f"{transfer_amount:.2f}",
                    "source": source_acc["name"],
                },
            )
            conn.commit()
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient funds. Required {transfer_amount:.2f} but {source_acc['name']} has {source_acc['balance']:.2f}."
            )

        validate_transfer_limits(conn, transfer_amount)

        if transfer_amount >= Decimal("1000000.00"):
            expires_at_dt = datetime.now(timezone.utc) + timedelta(minutes=5)
            expires_at_iso = expires_at_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

            conn.execute("BEGIN TRANSACTION;")
            cursor.execute(
                """INSERT INTO transfers (id, source_account_id, destination_account_id, amount, status, created_at, expires_at)
                   VALUES (?, ?, ?, ?, 'PENDING_MFA', ?, ?);""",
                (transfer_id, payload.source_account_id, payload.destination_account_id, encrypt_val(f"{transfer_amount:.2f}"), created_at_iso, expires_at_iso)
            )
            append_audit_record(
                cursor=cursor,
                event_type="TRANSFER_PENDING_MFA",
                actor_id="user_mock_001",
                resource_id=transfer_id,
                payload_metadata={
                    "amount": f"{transfer_amount:.2f}",
                    "source": source_acc["name"],
                    "dest": dest_acc["name"],
                },
            )
            conn.commit()

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

        # 2. Acquire exclusive write lock to re-read fresh balances and commit mutation atomically
        conn.execute("BEGIN IMMEDIATE;")
        cursor.execute(
            "SELECT id, balance FROM accounts WHERE id IN (?, ?);",
            (payload.source_account_id, payload.destination_account_id)
        )
        fresh_dict = {row[0]: Decimal(decrypt_val(row[1])) for row in cursor.fetchall()}

        if fresh_dict[payload.source_account_id] < transfer_amount:
            conn.execute("ROLLBACK;")
            raise HTTPException(status_code=400, detail="Insufficient funds at execution time.")

        # Re-validate limits under exclusive write lock so concurrent transfers cannot bypass remaining daily availability
        try:
            validate_transfer_limits(conn, transfer_amount, cursor=cursor)
        except HTTPException:
            conn.commit()  # Rejection audit log is committed atomically
            raise

        new_source_balance = fresh_dict[payload.source_account_id] - transfer_amount
        new_dest_balance = fresh_dict[payload.destination_account_id] + transfer_amount

        cursor.execute("UPDATE accounts SET balance = ? WHERE id = ?;", (encrypt_val(f"{new_source_balance:.2f}"), payload.source_account_id))
        cursor.execute("UPDATE accounts SET balance = ? WHERE id = ?;", (encrypt_val(f"{new_dest_balance:.2f}"), payload.destination_account_id))
        cursor.execute(
            """INSERT INTO transfers (id, source_account_id, destination_account_id, amount, status, created_at, expires_at)
               VALUES (?, ?, ?, ?, 'COMPLETED', ?, NULL);""",
            (transfer_id, payload.source_account_id, payload.destination_account_id, encrypt_val(f"{transfer_amount:.2f}"), created_at_iso)
        )
        append_audit_record(
            cursor=cursor,
            event_type="TRANSFER_COMPLETED",
            actor_id="user_mock_001",
            resource_id=transfer_id,
            payload_metadata={
                "amount": f"{transfer_amount:.2f}",
                "source": source_acc["name"],
                "dest": dest_acc["name"],
            },
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


@router.post("/conversions", response_model=ConversionResponse)
def create_conversion(envelope: CryptographicEnvelope,
                      idempotency_key: str | None = Header(None, alias="Idempotency-Key")):
    payload = _decrypt_envelope_to_model(envelope, ConversionCreate)
    if idempotency_key is None:
        raise HTTPException(status_code=422, detail={"code": "INVALID_IDEMPOTENCY_KEY", "message": "Idempotency-Key header is required"})
    conn = get_connection()
    try:
        result, _replay = execute_stage4_command(conn, "CONVERSION", idempotency_key, payload.model_dump())
        return ConversionResponse.model_validate(result)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail={"code":"PERSISTENCE_INTEGRITY_FAILURE","message":"Conversion could not be persisted safely"}) from None
    finally:
        conn.close()


@router.post("/transfers/ach", response_model=AchTransferResponse)
@router.post("/ach/transfers", response_model=AchTransferResponse)
def initiate_ach_transfer(envelope: CryptographicEnvelope, response: Response,
                          idempotency_key: str | None = Header(None, alias="Idempotency-Key")):
    """Initiates an ACH transfer from an encrypted client envelope."""
    payload = _decrypt_envelope_to_model(envelope, AchTransferCreate)
    conn = get_connection()
    try:
        if not idempotency_key:
            raise HTTPException(422, detail={"code":"INVALID_IDEMPOTENCY_KEY","message":"Idempotency-Key header is required"})
        from services import process_ach_transfer_stage4
        status_code, resp_model = process_ach_transfer_stage4(conn, payload, idempotency_key)
        response.status_code = status_code
        return resp_model
    finally:
        conn.close()


@router.post("/transfers/{transfer_id}/confirm-mfa", response_model=MFAConfirmResponse)
@router.post("/transfers/{transfer_id}/mfa", response_model=MFAConfirmResponse)
def confirm_mfa(transfer_id: str, envelope: CryptographicEnvelope,
                idempotency_key: str | None = Header(None, alias="Idempotency-Key")):
    """Submits encrypted MFA code to finalize a sensitive pending transfer."""
    payload = _decrypt_envelope_to_model(envelope, MFACodeConfirm)
    conn = get_connection()
    try:
        cursor = conn.cursor()
        stage4 = cursor.execute("SELECT stage4_command_id FROM transfers WHERE id=?", (transfer_id,)).fetchone()
        if stage4 and stage4[0]:
            if idempotency_key is None:
                raise HTTPException(status_code=422, detail={"code": "INVALID_IDEMPOTENCY_KEY", "message": "Idempotency-Key header is required"})
            try:
                result, _replay = confirm_stage4_mfa(conn, transfer_id, idempotency_key, payload)
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(status_code=500, detail={"code":"PERSISTENCE_INTEGRITY_FAILURE","message":"MFA confirmation could not be persisted safely"}) from None
            return MFAConfirmResponse.model_validate(result)

        cursor.execute(
            "SELECT id, source_account_id, destination_account_id, amount, status, expires_at, transfer_type FROM transfers WHERE id = ?;",
            (transfer_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Transfer not found.")

        _tx_id, src_id, dest_id, amount_enc, status_str, expires_at_iso, tx_type = row
        transfer_amount = Decimal(decrypt_val(amount_enc))

        if status_str != "PENDING_MFA":
            raise HTTPException(status_code=400, detail="Transfer is not pending MFA confirmation.")

        if expires_at_iso:
            expires_at_dt = datetime.fromisoformat(expires_at_iso.replace("Z", "+00:00"))
            current_time_dt = datetime.now(timezone.utc)

            if current_time_dt > expires_at_dt:
                conn.execute("BEGIN TRANSACTION;")
                cursor.execute("UPDATE transfers SET status = 'EXPIRED' WHERE id = ?;", (transfer_id,))
                append_audit_record(cursor, "MFA_EXPIRED", "user_mock_001", transfer_id)
                conn.commit()
                return JSONResponse(
                    status_code=410,
                    content={
                        "id": transfer_id,
                        "status": "EXPIRED",
                        "detail": "MFA verification window has expired."
                    }
                )

        if payload.code != "123456":
            log_rejection_audit_event("MFA_FAILED", "user_mock_001", transfer_id, {"reason": "Invalid verification code"})
            return JSONResponse(
                status_code=401,
                content={
                    "id": transfer_id,
                    "status": "PENDING_MFA",
                    "detail": "Invalid MFA verification code. Please retry."
                }
            )

        conn.execute("BEGIN TRANSACTION;")
        try:
            cursor.execute("SELECT id, name, balance FROM accounts WHERE id = ?;", (src_id,))
            src_row = cursor.fetchone()
            if not src_row:
                raise HTTPException(status_code=400, detail="Source account not found.")

            source_balance = Decimal(decrypt_val(src_row[2]))

            if source_balance < transfer_amount:
                cursor.execute("UPDATE transfers SET status = 'FAILED' WHERE id = ?;", (transfer_id,))
                append_audit_record(
                    cursor=cursor,
                    event_type="TRANSFER_FAILED",
                    actor_id="user_mock_001",
                    resource_id=transfer_id,
                    payload_metadata={"reason": "Insufficient balance at confirmation"},
                )
                conn.commit()
                return JSONResponse(
                    status_code=409,
                    content={
                        "id": transfer_id,
                        "status": "FAILED",
                        "detail": "Insufficient funds at confirmation time."
                    }
                )

            validate_transfer_limits(conn, transfer_amount)

            new_source_balance = source_balance - transfer_amount
            cursor.execute("UPDATE accounts SET balance = ? WHERE id = ?;", (encrypt_val(f"{new_source_balance:.2f}"), src_id))

            append_audit_record(cursor, "MFA_VERIFIED", "user_mock_001", transfer_id)

            if tx_type == "ACH":
                cursor.execute("UPDATE transfers SET status = 'PENDING' WHERE id = ?;", (transfer_id,))
                append_audit_record(
                    cursor=cursor,
                    event_type="ACH_TRANSFER_PENDING",
                    actor_id="user_mock_001",
                    resource_id=transfer_id,
                    payload_metadata={"amount": f"{transfer_amount:.2f}"},
                )
                conn.commit()
                return MFAConfirmResponse(
                    id=transfer_id,
                    status="PENDING",
                    message="ACH transfer initiated and pending settlement."
                )
            else:
                cursor.execute("SELECT balance FROM accounts WHERE id = ?;", (dest_id,))
                dest_row = cursor.fetchone()
                if not dest_row:
                    raise HTTPException(status_code=400, detail="Destination account not found.")
                new_dest_balance = Decimal(decrypt_val(dest_row[0])) + transfer_amount
                cursor.execute("UPDATE accounts SET balance = ? WHERE id = ?;", (encrypt_val(f"{new_dest_balance:.2f}"), dest_id))
                cursor.execute("UPDATE transfers SET status = 'COMPLETED' WHERE id = ?;", (transfer_id,))
                append_audit_record(
                    cursor=cursor,
                    event_type="TRANSFER_COMPLETED",
                    actor_id="user_mock_001",
                    resource_id=transfer_id,
                    payload_metadata={"amount": f"{transfer_amount:.2f}"},
                )
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
# Recurring Payment Schedule Endpoints
# ==============================================================================

@router.get("/recurring-schedules", response_model=list[RecurringScheduleResponse])
def get_user_recurring_schedules():
    """Lists all recurring payment schedules for the customer."""
    conn = get_connection()
    try:
        return list_recurring_schedules(conn)
    finally:
        conn.close()


@router.post("/recurring-schedules", response_model=RecurringScheduleResponse)
def create_new_recurring_schedule(envelope: CryptographicEnvelope, response: Response,
                                  idempotency_key: str | None = Header(None, alias="Idempotency-Key")):
    """Creates a recurring payment schedule from an encrypted client envelope."""
    payload = _decrypt_envelope_to_model(envelope, RecurringScheduleCreate)
    conn = get_connection()
    try:
        if not idempotency_key:
            raise HTTPException(422, detail={"code":"INVALID_IDEMPOTENCY_KEY","message":"Idempotency-Key header is required"})
        from services import create_recurring_schedule_stage4
        status_code, resp_model = create_recurring_schedule_stage4(conn, payload, idempotency_key)
        response.status_code = status_code
        return resp_model
    finally:
        conn.close()


@router.post("/recurring-schedules/{schedule_id}/confirm-mfa", response_model=RecurringScheduleResponse)
def confirm_schedule_mfa(schedule_id: str, envelope: CryptographicEnvelope,
                         idempotency_key: str | None = Header(None, alias="Idempotency-Key")):
    """Validates encrypted MFA code for a sensitive recurring schedule."""
    payload = _decrypt_envelope_to_model(envelope, MFACodeConfirm)
    conn = get_connection()
    try:
        if not idempotency_key:
            raise HTTPException(422,detail={"code":"INVALID_IDEMPOTENCY_KEY","message":"Idempotency-Key header is required"})
        from services import confirm_recurring_schedule_mfa_stage4
        return confirm_recurring_schedule_mfa_stage4(conn,schedule_id,payload,idempotency_key)
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
    """Test-only simulation endpoint to deterministically fail a PENDING ACH transfer and issue refund."""
    from main import require_test_endpoints
    require_test_endpoints()

    conn = get_connection()
    try:
        return fail_ach_transfer(conn, transfer_id)
    finally:
        conn.close()


@router.post("/test/ach/settle-pending")
def trigger_test_ach_settlement():
    """Test-only simulation endpoint to force an immediate settlement sweep of eligible PENDING ACH transfers."""
    from main import require_test_endpoints
    require_test_endpoints()

    from scheduler import run_ach_settlement_sweep_sync
    settled_count = run_ach_settlement_sweep_sync(delay_seconds=10)
    return {"settled_count": settled_count, "message": "Settlement sweep completed successfully."}


@router.post("/test/recurring/run-due")
def trigger_test_recurring_execution():
    """Test-only simulation endpoint to force an immediate execution sweep of due recurring schedules."""
    from main import require_test_endpoints
    require_test_endpoints()

    from scheduler import run_recurring_execution_sweep_sync
    processed_count, failed_count = run_recurring_execution_sweep_sync()
    return {
        "processed_count": processed_count,
        "failed_count": failed_count,
        "message": "Recurring execution sweep completed."
    }
