"""Authenticated encryption and restart-safe migration for external bank details."""
from __future__ import annotations

import base64
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


PREFIX = "sbenc:v1:"
VERSION = 1
SENSITIVE_FIELDS = {
    "beneficiaries": ("name", "bank_name", "routing_number", "account_number"),
    "ach_transfers": ("recipient_name", "bank_name", "routing_number", "account_number"),
    "recurring_schedules": ("recipient_name", "bank_name", "routing_number", "account_number"),
}


class EncryptionError(Exception):
    """Safe-to-report encryption failure without data or key material."""


def _keyring() -> tuple[dict[str, bytes], str]:
    raw = os.environ.get("SHIFT_BANK_ENCRYPTION_KEYS", "")
    key_file = os.environ.get("SHIFT_BANK_ENCRYPTION_KEYS_FILE", "")
    if key_file:
        try:
            raw = Path(key_file).read_text(encoding="utf-8").strip()
        except OSError:
            raise EncryptionError("Sensitive data protection key is unavailable") from None
    active = os.environ.get("SHIFT_BANK_ACTIVE_KEY_VERSION", "")
    if not raw or not active:
        raise EncryptionError("Sensitive data protection key is unavailable")
    try:
        encoded = json.loads(raw)
        if not isinstance(encoded, dict) or not encoded:
            raise ValueError
        keys = {}
        for version, value in encoded.items():
            if not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", version):
                raise ValueError
            key = base64.b64decode(value, validate=True)
            if len(key) != 32:
                raise ValueError
            keys[version] = key
        if active not in keys:
            raise ValueError
        return keys, active
    except (ValueError, TypeError):
        raise EncryptionError("Sensitive data protection key configuration is invalid") from None


def validate_key_configuration() -> None:
    """Fail startup/readiness when the external data-key configuration is unusable."""
    _keyring()


def _aad(table: str, record_id: str, field: str) -> bytes:
    return f"shift-bank:{table}:{record_id}:{field}:v{VERSION}".encode("utf-8")


def encrypt_value(value: str, table: str, record_id: str, field: str) -> str:
    if not isinstance(value, str):
        raise EncryptionError("Sensitive value is invalid")
    keys, active = _keyring()
    nonce = os.urandom(12)
    ciphertext = AESGCM(keys[active]).encrypt(nonce, value.encode("utf-8"), _aad(table, record_id, field))
    payload = base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii").rstrip("=")
    return f"{PREFIX}{active}:{payload}"


def decrypt_value(value: str, table: str, record_id: str, field: str) -> str:
    if not isinstance(value, str) or not value.startswith(PREFIX):
        raise EncryptionError("Sensitive data migration is required")
    try:
        version, payload = value[len(PREFIX):].split(":", 1)
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", version):
            raise ValueError
        keys, _ = _keyring()
        key = keys.get(version)
        if key is None:
            raise EncryptionError("Required sensitive data protection key version is unavailable")
        raw = base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
        if len(raw) < 12 + 16:
            raise ValueError
        return AESGCM(key).decrypt(raw[:12], raw[12:], _aad(table, record_id, field)).decode("utf-8")
    except EncryptionError:
        raise
    except (ValueError, InvalidTag):
        raise EncryptionError("Sensitive data integrity verification failed") from None


def protect_record(table: str, record_id: str, record: dict) -> dict:
    protected = dict(record)
    for field in SENSITIVE_FIELDS[table]:
        if protected.get(field) is not None:
            protected[field] = encrypt_value(protected[field], table, record_id, field)
    return protected


def reveal_record(table: str, record: dict) -> dict:
    revealed = dict(record)
    for field in SENSITIVE_FIELDS[table]:
        if revealed.get(field) is not None:
            revealed[field] = decrypt_value(revealed[field], table, revealed["id"], field)
    return revealed


def migrate_sensitive_data(conn: sqlite3.Connection) -> int:
    """Encrypt legacy rows atomically; reruns verify encrypted rows and are idempotent."""
    conn.execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
        version TEXT PRIMARY KEY, completed_at TEXT NOT NULL)""")
    conn.execute("BEGIN IMMEDIATE")
    changed = 0
    try:
        for table, fields in SENSITIVE_FIELDS.items():
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()
            for row in rows:
                record = dict(row)
                for field in fields:
                    value = record[field]
                    if value is None:
                        continue
                    if not isinstance(value, str):
                        raise EncryptionError("Sensitive data migration encountered an unsupported value")
                    if value.startswith(PREFIX):
                        # Validates key availability, record binding, format and tag.
                        original = decrypt_value(value, table, record["id"], field)
                        key_version = value[len(PREFIX):].split(":", 1)[0]
                        if key_version != _keyring()[1]:
                            rotated = encrypt_value(original, table, record["id"], field)
                            if decrypt_value(rotated, table, record["id"], field) != original:
                                raise EncryptionError("Sensitive data migration verification failed")
                            conn.execute(f"UPDATE {table} SET {field}=? WHERE id=?", (rotated, record["id"]))
                            record[field] = rotated
                            changed += 1
                    else:
                        if value.startswith("sbenc:"):
                            raise EncryptionError("Unsupported sensitive data ciphertext version")
                        original = value
                        value = encrypt_value(original, table, record["id"], field)
                        if decrypt_value(value, table, record["id"], field) != original:
                            raise EncryptionError("Sensitive data migration verification failed")
                        conn.execute(f"UPDATE {table} SET {field}=? WHERE id=?", (value, record["id"]))
                        record[field] = value
                        changed += 1
        conn.execute("INSERT OR REPLACE INTO schema_migrations(version,completed_at) VALUES(?,?)",
                     ("sensitive-banking-data-v1", datetime.now(timezone.utc).isoformat()))
        conn.commit()
        return changed
    except Exception:
        conn.rollback()
        raise
