import uuid

import pytest
import sqlite3
import database

from idempotency import fingerprint, lookup, validate_key


def test_idempotency_key_validation_fingerprint_and_conflict():
    key = str(uuid.uuid4())
    assert validate_key(key) == key
    with pytest.raises(ValueError):
        validate_key("not-a-uuid")
    one = fingerprint("TRANSFER", {"amount": "1.00", "expected_versions": {"a": 0}})
    same = fingerprint("TRANSFER", {"expected_versions": {"a": 0}, "amount": "1.00"})
    changed = fingerprint("TRANSFER", {"amount": "2.00", "expected_versions": {"a": 0}})
    assert one == same and one != changed


@pytest.fixture
def database_connection(tmp_path):
    path = str(tmp_path / "idempotency.sqlite")
    database.init_db(path)
    conn = sqlite3.connect(path)
    yield conn
    conn.close()


def test_exact_replay_lookup_precedes_version_validation(database_connection):
    cursor = database_connection.cursor()
    cursor.execute("INSERT INTO idempotency_records VALUES(?,?,?,?,?)",
                   (str(uuid.uuid4()), "TRANSFER", "digest", '{"ok":true}', "2026-11-16T00:00:00Z"))
    key = cursor.execute("SELECT idempotency_key FROM idempotency_records").fetchone()[0]
    assert lookup(cursor, key, "digest") == '{"ok":true}'
    assert lookup(cursor, key, "different") == "CONFLICT"
