import json
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from backend.app.models import IdempotencyRecord


class IdempotencyConflictException(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def validate_idempotency_key_header(key: Optional[str]) -> str:
    """Validate that Idempotency-Key HTTP header is present and is a valid UUID."""
    if not key or not key.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "MISSING_IDEMPOTENCY_KEY", "message": "Idempotency-Key HTTP header is required"},
        )
    trimmed = key.strip()
    try:
        parsed = uuid.UUID(trimmed)
        return str(parsed)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_IDEMPOTENCY_KEY", "message": "Idempotency-Key HTTP header must be a valid UUID"},
        )


def compute_fingerprint(params: Dict[str, Any]) -> str:
    """Compute SHA-256 fingerprint from canonical business parameters."""
    canonical_json = json.dumps(params, sort_keys=True, default=str)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def check_existing_idempotency(
    db: Session, idempotency_key: str, fingerprint: str
) -> Optional[Dict[str, Any]]:
    """
    Check if the idempotency key was previously committed.
    If same key and matching fingerprint: return committed response payload dictionary.
    If same key but different fingerprint: raise HTTP 409 Conflict.
    If not found: return None.
    """
    record = (
        db.query(IdempotencyRecord)
        .filter(IdempotencyRecord.idempotency_key == idempotency_key)
        .first()
    )
    if not record:
        return None

    if record.request_fingerprint != fingerprint:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "IDEMPOTENCY_KEY_REUSE",
                "message": "Idempotency key was previously committed with different request parameters",
            },
        )

    return json.loads(record.response_payload)


def record_idempotency_commit(
    db: Session,
    idempotency_key: str,
    operation_type: str,
    operation_id: str,
    fingerprint: str,
    response_data: Dict[str, Any],
) -> IdempotencyRecord:
    """Persist idempotency record atomically within the same transaction."""
    record = IdempotencyRecord(
        idempotency_key=idempotency_key,
        operation_type=operation_type,
        operation_id=operation_id,
        request_fingerprint=fingerprint,
        response_payload=json.dumps(response_data, default=str),
        created_at=datetime.now(timezone.utc),
    )
    db.add(record)
    db.flush()
    return record
