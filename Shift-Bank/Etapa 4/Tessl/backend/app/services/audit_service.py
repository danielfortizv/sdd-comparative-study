import os
import json
import uuid
import hmac
import hashlib
import logging
import threading
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.models import AuditLog
from backend.app.database import SessionLocal

logger = logging.getLogger("audit_service")

GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

_session_factory = SessionLocal
_audit_lock = threading.Lock()


def set_session_factory(factory) -> None:
    """Set the database session factory (used for test isolation)."""
    global _session_factory
    _session_factory = factory


def get_audit_signing_key() -> bytes:
    """Retrieve and validate the HMAC-SHA256 audit secret key from the environment."""
    key = os.getenv("AUDIT_SECRET_KEY")
    if not key:
        if os.getenv("TESTING", "false").lower() == "true":
            return b"test_audit_secret_key_32bytes!!"
        raise ValueError("AUDIT_SECRET_KEY environment variable is missing or empty")
    return key.encode("utf-8") if isinstance(key, str) else key


def validate_audit_key_at_startup() -> None:
    """Validate audit key configuration at service startup."""
    key = get_audit_signing_key()
    if len(key) < 16:
        raise RuntimeError("AUDIT_SECRET_KEY must be at least 16 bytes for HMAC-SHA256 security")


class AuditPersistenceError(RuntimeError):
    """Raised when an audit record fails to persist to the ledger."""
    pass


def sanitize_error_code(err: Any) -> str:
    """Map raw exceptions or detail messages to structured, safe error codes.
    Guarantees user inputs, PINs, or raw database messages cannot enter audit logs.
    """
    if not err:
        return "UNKNOWN_ERROR"

    err_str = str(err).lower()

    if "mfa_required" in err_str:
        return "MFA_REQUIRED"
    if "insufficient funds" in err_str:
        return "INSUFFICIENT_FUNDS"
    if "per-transaction limit" in err_str or "exceeds per-transaction" in err_str:
        return "PER_TRANSACTION_LIMIT_EXCEEDED"
    if "daily limit" in err_str or "exceeds daily" in err_str:
        return "DAILY_LIMIT_EXCEEDED"
    if "cannot transfer to the same account" in err_str or "same account" in err_str:
        return "SAME_ACCOUNT_TRANSFER"
    if "cross_currency" in err_str or "cross-currency" in err_str:
        return "CROSS_CURRENCY_NOT_PERMITTED"
    if "same_currency" in err_str or "same currency" in err_str:
        return "SAME_CURRENCY_NOT_PERMITTED"
    if "account_version_conflict" in err_str or "version mismatch" in err_str:
        return "ACCOUNT_VERSION_CONFLICT"
    if "idempotency_key_reuse" in err_str:
        return "IDEMPOTENCY_KEY_REUSE"
    if "missing_idempotency_key" in err_str:
        return "MISSING_IDEMPOTENCY_KEY"
    if "invalid_idempotency_key" in err_str:
        return "INVALID_IDEMPOTENCY_KEY"
    if "ach_requires_usd_account" in err_str:
        return "ACH_REQUIRES_USD_ACCOUNT"
    if "recurring_requires_same_currency" in err_str:
        return "RECURRING_REQUIRES_SAME_CURRENCY"
    if "locked" in err_str or "lockout" in err_str:
        return "MFA_ACCOUNT_LOCKED"
    if "invalid security pin" in err_str or "invalid pin" in err_str:
        return "INVALID_SECURITY_PIN"
    if "key_expired" in err_str:
        return "KEY_EXPIRED"
    if "invalid_key_id" in err_str:
        return "INVALID_KEY_ID"
    if "invalid_encrypted_payload" in err_str:
        return "INVALID_ENCRYPTED_PAYLOAD"
    if "routing number" in err_str:
        return "INVALID_ROUTING_NUMBER"
    if "account number" in err_str:
        return "INVALID_ACCOUNT_NUMBER"
    if "not found" in err_str:
        if "beneficiary" in err_str:
            return "BENEFICIARY_NOT_FOUND"
        if "schedule" in err_str:
            return "SCHEDULE_NOT_FOUND"
        return "ACCOUNT_NOT_FOUND"
    if "already paused" in err_str:
        return "SCHEDULE_ALREADY_PAUSED"
    if "already active" in err_str:
        return "SCHEDULE_ALREADY_ACTIVE"
    if "cannot pause a cancelled" in err_str:
        return "CANNOT_PAUSE_CANCELLED_SCHEDULE"
    if "cannot resume a cancelled" in err_str:
        return "CANNOT_RESUME_CANCELLED_SCHEDULE"

    return "TRANSACTION_VALIDATION_ERROR"


def sanitize_audit_details(details: Dict[str, Any]) -> Dict[str, Any]:
    """Redact passwords, Security PINs, session keys, raw exception strings, and unmasked account numbers."""
    sanitized = {}
    for k, v in details.items():
        key_lower = k.lower()
        if any(secret_term in key_lower for secret_term in ("pin", "password", "secret", "private_key", "encrypted_key", "session_key")):
            continue

        if key_lower in ("error", "reason", "failure_reason"):
            sanitized[k] = sanitize_error_code(v)
            continue

        if "account" in key_lower and isinstance(v, str) and not v.startswith("****"):
            v_str = v.strip()
            if len(v_str) > 4:
                sanitized[k] = f"****{v_str[-4:]}"
            else:
                sanitized[k] = "****"
        else:
            sanitized[k] = v

    return sanitized


def compute_canonical_details_json(details: Dict[str, Any]) -> str:
    """Serialize sanitized details to canonical JSON (sorted keys, compact separators, safe default=str)."""
    sanitized = sanitize_audit_details(details)
    return json.dumps(sanitized, sort_keys=True, separators=(",", ":"), default=str)


def compute_audit_hash(
    previous_hash: str,
    event_id: str,
    timestamp_iso: str,
    event_type: str,
    actor_id: Optional[int],
    status: str,
    canonical_details_json: str,
) -> str:
    """Compute the SHA-256 digest of record attributes chained from previous_hash."""
    payload = f"{previous_hash}{event_id}{timestamp_iso}{event_type}{str(actor_id)}{status}{canonical_details_json}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compute_audit_signature(current_hash: str, signing_key: bytes) -> str:
    """Compute HMAC-SHA256 signature over current_hash."""
    return hmac.new(signing_key, current_hash.encode("utf-8"), hashlib.sha256).hexdigest()


def acquire_sqlite_write_lock(db: Session) -> None:
    """Ensure the SQLite connection holds an immediate write transaction.
    If the connection is not yet in an active write transaction, executes BEGIN IMMEDIATE
    to prevent concurrent processes from reading stale chain heads.
    """
    conn = db.connection()
    if conn.dialect.name == "sqlite":
        raw = getattr(conn.connection, "dbapi_connection", conn.connection)
        if hasattr(raw, "in_transaction") and not raw.in_transaction:
            conn.exec_driver_sql("BEGIN IMMEDIATE")


def record_audit_event(
    db: Session,
    event_type: str,
    status: str,
    details: Dict[str, Any],
    actor_id: Optional[int] = 1,
    event_id: Optional[str] = None,
    timestamp: Optional[datetime] = None,
) -> AuditLog:
    """Record an audit event into the append-only ledger within the caller's transaction.

    Protected by SQLite immediate write transactions (acquired selectively via BEGIN IMMEDIATE)
    and process mutex.
    Fails closed: if any error occurs, raises an exception preventing un-audited state mutation.
    """
    signing_key = get_audit_signing_key()

    if not event_id:
        event_id = str(uuid.uuid4())
    if not timestamp:
        timestamp = datetime.now(timezone.utc)

    timestamp_iso = timestamp.isoformat()
    canonical_details = compute_canonical_details_json(details)

    with _audit_lock:
        acquire_sqlite_write_lock(db)

        # Query latest entry to retrieve previous_hash
        last_entry = db.execute(
            text("SELECT id, current_hash FROM audit_logs ORDER BY id DESC LIMIT 1")
        ).fetchone()

        if last_entry is None:
            previous_hash = GENESIS_HASH
        else:
            previous_hash = last_entry[1]

        # Compute hash and signature
        current_hash = compute_audit_hash(
            previous_hash=previous_hash,
            event_id=event_id,
            timestamp_iso=timestamp_iso,
            event_type=event_type,
            actor_id=actor_id,
            status=status,
            canonical_details_json=canonical_details,
        )
        signature = compute_audit_signature(current_hash, signing_key)

        # Insert record into audit_logs table
        audit_entry = AuditLog(
            event_id=event_id,
            timestamp=timestamp_iso,
            event_type=event_type,
            actor_id=actor_id,
            status=status,
            details=canonical_details,
            previous_hash=previous_hash,
            current_hash=current_hash,
            signature=signature,
        )
        db.add(audit_entry)
        db.flush()
        return audit_entry


def record_failure_audit_event(
    event_type: str,
    details: Dict[str, Any],
    actor_id: Optional[int] = 1,
) -> None:
    """Record a failure audit event in a dedicated autonomous session post-rollback.

    Guarantees failure events are durably persisted even when business operations fail.
    Fails closed: raises AuditPersistenceError if the failure audit cannot be committed.
    """
    db = _session_factory()
    try:
        record_audit_event(
            db=db,
            event_type=event_type,
            status="FAILURE",
            details=details,
            actor_id=actor_id,
        )
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to record failure audit event: {e}")
        raise AuditPersistenceError(f"Failed to persist failure audit event to ledger: {e}") from e
    finally:
        db.close()


def verify_audit_chain(db: Session) -> Dict[str, Any]:
    """Verify integrity of the audit chain from genesis to the most recent record.

    Validates previous_hash linkage, recalculates SHA-256 hashes, and checks HMAC signatures.
    """
    signing_key = get_audit_signing_key()

    rows = db.execute(
        text(
            "SELECT id, event_id, timestamp, event_type, actor_id, status, details, "
            "previous_hash, current_hash, signature FROM audit_logs ORDER BY id ASC"
        )
    ).fetchall()

    if not rows:
        return {"valid": True, "total_records": 0}

    for idx, row in enumerate(rows):
        rec_id = row[0]
        event_id = row[1]
        ts = row[2]
        event_type = row[3]
        actor_id = row[4]
        status = row[5]
        details_json = row[6]
        prev_hash = row[7]
        curr_hash = row[8]
        sig = row[9]

        # 1. Verify previous_hash linkage
        if idx == 0:
            if prev_hash != GENESIS_HASH:
                return {
                    "valid": False,
                    "tampered_entry_id": rec_id,
                    "reason": "broken_chain",
                }
        else:
            preceding_row = rows[idx - 1]
            if prev_hash != preceding_row[8]:  # preceding row current_hash
                return {
                    "valid": False,
                    "tampered_entry_id": rec_id,
                    "reason": "broken_chain",
                }

        # 2. Recompute and verify current_hash
        ts_iso = str(ts)
        expected_hash = compute_audit_hash(
            previous_hash=prev_hash,
            event_id=event_id,
            timestamp_iso=ts_iso,
            event_type=event_type,
            actor_id=actor_id,
            status=status,
            canonical_details_json=details_json,
        )
        if expected_hash != curr_hash:
            return {
                "valid": False,
                "tampered_entry_id": rec_id,
                "reason": "hash_mismatch",
            }

        # 3. Recompute and verify HMAC-SHA256 signature
        expected_sig = compute_audit_signature(curr_hash, signing_key)
        if expected_sig != sig:
            return {
                "valid": False,
                "tampered_entry_id": rec_id,
                "reason": "signature_mismatch",
            }

    return {"valid": True, "total_records": len(rows)}
