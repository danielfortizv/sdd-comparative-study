"""Append-only, HMAC-chained audit events sharing SQLite transactions with banking writes."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from functools import wraps


ZERO_HASH = "0" * 64
APPLICATION_ID = 0x53424155  # SBAU; distinguishes first audit bootstrap from later checkpoint loss.


class AuditError(Exception):
    """Safe audit persistence/configuration failure."""


class AuditIntegrityError(AuditError):
    """An existing audit chain cannot be safely extended."""


def _key() -> bytes:
    raw = os.environ.get("SHIFT_BANK_AUDIT_KEY", "")
    if not raw:
        raise AuditError("Audit integrity key is unavailable")
    try:
        key = base64.b64decode(raw, validate=True)
        if len(key) != 32:
            raise ValueError
        return key
    except (ValueError, TypeError):
        raise AuditError("Audit integrity key configuration is invalid") from None


def validate_key_configuration() -> None:
    """Fail startup/readiness when the external audit key is unusable."""
    _key()


def _canonical(value) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _entry_payload(sequence, event_id, event_type, occurred_at, operation_id, outcome, metadata, previous_hash):
    return _canonical({"sequence":sequence,"event_id":event_id,"event_type":event_type,"occurred_at":occurred_at,
                       "operation_id":operation_id,"outcome":outcome,"metadata":metadata,"previous_hash":previous_hash})


def _mac(key: bytes, message: str) -> str:
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).hexdigest()


def _checkpoint(key: bytes, sequence: int, head_hash: str) -> str:
    return _mac(key, f"shift-bank-audit-checkpoint:v1:{sequence}:{head_hash}")


def install_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""CREATE TABLE IF NOT EXISTS audit_entries (
        sequence INTEGER PRIMARY KEY,
        event_id TEXT NOT NULL UNIQUE,
        event_type TEXT NOT NULL,
        occurred_at TEXT NOT NULL,
        operation_id TEXT NOT NULL,
        outcome TEXT NOT NULL,
        metadata_json TEXT NOT NULL,
        previous_hash TEXT NOT NULL,
        event_hash TEXT NOT NULL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS audit_state (
        singleton INTEGER PRIMARY KEY CHECK(singleton=1),
        sequence INTEGER NOT NULL,
        head_hash TEXT NOT NULL,
        checkpoint_hmac TEXT NOT NULL)""")
    conn.execute("""CREATE TRIGGER IF NOT EXISTS audit_entries_no_update
        BEFORE UPDATE ON audit_entries BEGIN SELECT RAISE(ABORT,'audit entries are append-only'); END""")
    conn.execute("""CREATE TRIGGER IF NOT EXISTS audit_entries_no_delete
        BEFORE DELETE ON audit_entries BEGIN SELECT RAISE(ABORT,'audit entries are append-only'); END""")
    conn.execute("""CREATE TRIGGER IF NOT EXISTS audit_state_no_delete
        BEFORE DELETE ON audit_state BEGIN SELECT RAISE(ABORT,'audit checkpoint cannot be deleted'); END""")


def _verify_conn(conn: sqlite3.Connection) -> dict:
    key = _key()
    state = conn.execute("SELECT sequence,head_hash,checkpoint_hmac FROM audit_state WHERE singleton=1").fetchone()
    rows = conn.execute("SELECT * FROM audit_entries ORDER BY sequence").fetchall()
    if state is None:
        return {"valid":False,"first_invalid_sequence":1,"checked_entries":0,"head_sequence":0,"reason":"missing_checkpoint"}
    if not hmac.compare_digest(state["checkpoint_hmac"], _checkpoint(key,state["sequence"],state["head_hash"])):
        return {"valid":False,"first_invalid_sequence":state["sequence"],"checked_entries":0,"head_sequence":state["sequence"],"reason":"checkpoint_mismatch"}
    previous = ZERO_HASH
    expected = 1
    for row in rows:
        if row["sequence"] != expected or row["previous_hash"] != previous:
            return {"valid":False,"first_invalid_sequence":expected,"checked_entries":expected-1,"head_sequence":state["sequence"],"reason":"sequence_or_link_mismatch"}
        try:
            metadata = json.loads(row["metadata_json"])
            if _canonical(metadata) != row["metadata_json"]:
                raise ValueError
            payload = _entry_payload(row["sequence"],row["event_id"],row["event_type"],row["occurred_at"],row["operation_id"],row["outcome"],metadata,row["previous_hash"])
            expected_hash = _mac(key,payload)
        except (ValueError, TypeError):
            return {"valid":False,"first_invalid_sequence":expected,"checked_entries":expected-1,"head_sequence":state["sequence"],"reason":"invalid_entry_format"}
        if not hmac.compare_digest(row["event_hash"],expected_hash):
            return {"valid":False,"first_invalid_sequence":expected,"checked_entries":expected-1,"head_sequence":state["sequence"],"reason":"event_integrity_mismatch"}
        previous = row["event_hash"]
        expected += 1
    checked = expected - 1
    if checked != state["sequence"] or previous != state["head_hash"]:
        return {"valid":False,"first_invalid_sequence":checked+1,"checked_entries":checked,"head_sequence":state["sequence"],"reason":"checkpoint_chain_mismatch"}
    return {"valid":True,"first_invalid_sequence":None,"checked_entries":checked,"head_sequence":state["sequence"],"reason":None}


def verify_connection(conn: sqlite3.Connection) -> dict:
    try:
        return _verify_conn(conn)
    except sqlite3.Error:
        raise AuditError("Audit verification could not read persisted records") from None


def append_event(conn: sqlite3.Connection, event_type: str, operation_id: str, outcome: str, metadata: dict | None = None, occurred_at: datetime | None = None) -> int:
    if not conn.in_transaction:
        raise AuditError("Audit event must share an active database transaction")
    try:
        key = _key()
        current = _verify_conn(conn)
        if not current["valid"]:
            raise AuditIntegrityError(f"Audit chain integrity check failed at sequence {current['first_invalid_sequence']}")
        state = conn.execute("SELECT sequence,head_hash FROM audit_state WHERE singleton=1").fetchone()
        sequence = state["sequence"] + 1
        event_id = "aud_" + uuid.uuid4().hex
        timestamp = (occurred_at or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00","Z")
        safe_metadata = metadata or {}
        metadata_json = _canonical(safe_metadata)
        payload = _entry_payload(sequence,event_id,event_type,timestamp,operation_id,outcome,safe_metadata,state["head_hash"])
        event_hash = _mac(key,payload)
        conn.execute("INSERT INTO audit_entries VALUES(?,?,?,?,?,?,?,?,?)",(sequence,event_id,event_type,timestamp,operation_id,outcome,metadata_json,state["head_hash"],event_hash))
        conn.execute("UPDATE audit_state SET sequence=?,head_hash=?,checkpoint_hmac=? WHERE singleton=1",(sequence,event_hash,_checkpoint(key,sequence,event_hash)))
        return sequence
    except AuditError:
        raise
    except sqlite3.Error:
        raise AuditError("Audit event could not be persisted") from None


def initialize(conn: sqlite3.Connection) -> None:
    install_schema(conn)
    application_id = conn.execute("PRAGMA application_id").fetchone()[0]
    conn.execute("BEGIN IMMEDIATE")
    try:
        state = conn.execute("SELECT 1 FROM audit_state WHERE singleton=1").fetchone()
        entries = conn.execute("SELECT COUNT(*) FROM audit_entries").fetchone()[0]
        if state is None:
            if entries or application_id == APPLICATION_ID:
                raise AuditIntegrityError("Audit checkpoint is missing while audit entries exist")
            if application_id not in (0,APPLICATION_ID):
                raise AuditIntegrityError("Database application identifier is unexpected")
            key = _key()
            event_id = "aud_" + uuid.uuid4().hex
            timestamp = datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00","Z")
            metadata = {"scope":"stage3_auditing_started"}
            payload = _entry_payload(1,event_id,"audit_initialized",timestamp,"system","recorded",metadata,ZERO_HASH)
            head = _mac(key,payload)
            conn.execute("INSERT INTO audit_entries VALUES(1,?,?,?,?,?,?,?,?)",(event_id,"audit_initialized",timestamp,"system","recorded",_canonical(metadata),ZERO_HASH,head))
            conn.execute("INSERT INTO audit_state VALUES(1,1,?,?)",(head,_checkpoint(key,1,head)))
            conn.execute(f"PRAGMA application_id={APPLICATION_ID}")
        else:
            result = _verify_conn(conn)
            if not result["valid"]:
                raise AuditIntegrityError(f"Audit chain integrity check failed at sequence {result['first_invalid_sequence']}")
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def verify_database() -> dict:
    from database import get_db_connection
    conn = get_db_connection()
    try:
        return verify_connection(conn)
    finally:
        conn.close()


def _reason_code(message: str) -> str:
    text = message.lower()
    if "mfa session expired" in text: return "mfa_expired"
    if "invalid mfa" in text: return "mfa_invalid"
    if "insufficient funds" in text: return "insufficient_funds"
    if "limit" in text: return "transfer_limit"
    if "not found" in text: return "resource_not_found"
    if "amount" in text or "monetary" in text: return "invalid_amount"
    if "routing" in text or "account number" in text: return "invalid_recipient"
    return "business_rule_rejected"


def record_rejection(operation: str, message: str, subject_id: str | None = None) -> None:
    from database import get_db_connection
    reason = _reason_code(message)
    event_type = "mfa_attempt" if reason.startswith("mfa_") else f"{operation}_rejected"
    outcome = "expired" if reason == "mfa_expired" else "rejected"
    operation_id = subject_id or "req_" + uuid.uuid4().hex
    conn = get_db_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        append_event(conn,event_type,operation_id,outcome,{"operation":operation,"reason_code":reason})
        conn.commit()
    except Exception:
        if conn.in_transaction: conn.rollback()
        raise
    finally:
        conn.close()


def audit_rejections(operation: str):
    """Record failed business/MFA outcomes after the operation rolled back."""
    def decorate(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            try:
                return function(*args, **kwargs)
            except Exception as exc:
                from banking import BankingError
                if isinstance(exc,BankingError) and not getattr(exc,"audit_recorded",False):
                    subject = args[0] if args and isinstance(args[0],str) and args[0].startswith(("tx_","ach_","sch_","ben_")) else None
                    if subject is None and args and isinstance(args[0],dict):
                        subject = args[0].get("source_account_id")
                    record_rejection(operation,exc.message,subject)
                raise
        return wrapped
    return decorate
