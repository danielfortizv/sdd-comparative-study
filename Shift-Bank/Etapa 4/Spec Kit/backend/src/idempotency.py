"""Canonical request fingerprints and ordered idempotency lookups."""
import hashlib
import json
import uuid


def validate_key(value: str) -> str:
    try:
        parsed = uuid.UUID(value)
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Idempotency-Key must be a UUID") from None
    return str(parsed)


def fingerprint(command_type: str, payload: dict) -> str:
    canonical = json.dumps({"type": command_type, "payload": payload}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def lookup(cursor, key: str, digest: str):
    row = cursor.execute("SELECT request_fingerprint,response_json FROM idempotency_records WHERE idempotency_key=?", (key,)).fetchone()
    if row is None:
        return None
    if row[0] != digest:
        return "CONFLICT"
    from services import decrypt_val
    return decrypt_val(row[1])


def store(cursor, key: str, command_type: str, digest: str, response_json: str, created_at: str):
    from services import encrypt_val
    cursor.execute("INSERT INTO idempotency_records(idempotency_key,command_type,request_fingerprint,response_json,created_at) VALUES(?,?,?,?,?)",
                   (key, command_type, digest, encrypt_val(response_json), created_at))
