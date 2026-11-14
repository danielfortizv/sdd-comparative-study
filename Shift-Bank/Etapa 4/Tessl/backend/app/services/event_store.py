import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.models import DomainEvent, Account
from backend.app.services.audit_service import acquire_sqlite_write_lock


class ConcurrencyConflictException(Exception):
    """Raised when an optimistic concurrency check fails."""
    def __init__(self, code: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def append_domain_event(
    db: Session,
    event_type: str,
    aggregate_id: str,
    account_ids: List[int],
    payload: Dict[str, Any],
    correlation_id: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    expected_versions: Optional[Dict[int, int]] = None,
) -> DomainEvent:
    """
    Atomically verify expected account versions, append an immutable domain event to domain_events,
    and increment the versions of all affected accounts.
    """
    # Ensure immediate write transaction locking to serialize concurrent writes
    acquire_sqlite_write_lock(db)

    # 1. Optimistic Concurrency Control Check
    if expected_versions:
        for acc_id, expected_ver in expected_versions.items():
            acc = db.query(Account).filter(Account.id == acc_id).first()
            if acc:
                # Expire cached account instance so version verification inspects fresh committed DB state
                db.expire(acc)
                acc = db.query(Account).filter(Account.id == acc_id).first()
            if not acc:
                raise ConcurrencyConflictException(
                    code="ACCOUNT_NOT_FOUND",
                    message=f"Account with ID {acc_id} not found for version check",
                )
            if acc.version != expected_ver:
                raise ConcurrencyConflictException(
                    code="ACCOUNT_VERSION_CONFLICT",
                    message=f"Account {acc.account_number} version mismatch. Expected {expected_ver}, found {acc.version}",
                    details={
                        "account_id": acc_id,
                        "account_number": acc.account_number,
                        "expected_version": expected_ver,
                        "current_version": acc.version,
                    },
                )

    # 2. Advance versions for all affected accounts if this is a state-changing event
    version_updates = {}
    if event_type in (
        "InternalTransferCompleted",
        "CurrencyConversionCompleted",
        "AchTransferInitiated",
        "AchTransferFailed",
    ):
        for acc_id in account_ids:
            acc = db.query(Account).filter(Account.id == acc_id).first()
            if acc:
                acc.version += 1
                version_updates[acc_id] = acc.version

    # Ensure payload carries versions
    if version_updates:
        payload["updated_versions"] = version_updates

    # Compute aggregate version
    last_event = (
        db.query(DomainEvent)
        .filter(DomainEvent.aggregate_id == aggregate_id)
        .order_by(DomainEvent.aggregate_version.desc())
        .first()
    )
    new_aggregate_version = (last_event.aggregate_version + 1) if last_event else 1

    # 3. Create DomainEvent
    event_id = str(uuid.uuid4())
    event_record = DomainEvent(
        event_id=event_id,
        event_type=event_type,
        aggregate_id=aggregate_id,
        aggregate_version=new_aggregate_version,
        account_ids=json.dumps(account_ids),
        payload=json.dumps(payload, default=str),
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
        created_at=datetime.now(timezone.utc),
    )
    db.add(event_record)
    db.flush()
    return event_record


def get_all_events(db: Session, after_id: int = 0, limit: int = 100000) -> List[DomainEvent]:
    """Retrieve ordered domain events for projection rebuilding and audits."""
    return (
        db.query(DomainEvent)
        .filter(DomainEvent.id > after_id)
        .order_by(DomainEvent.id.asc())
        .limit(limit)
        .all()
    )


def get_events_for_account(db: Session, account_id: int) -> List[DomainEvent]:
    """Retrieve all ordered domain events affecting a specific account."""
    all_events = db.query(DomainEvent).order_by(DomainEvent.id.asc()).all()
    matching = []
    for ev in all_events:
        try:
            ids = json.loads(ev.account_ids)
            if account_id in ids:
                matching.append(ev)
        except Exception:
            continue
    return matching
