import sqlite3
import os

import pytest
import database
from crypto import decrypt_at_rest
from event_store import read_events
from fastapi.testclient import TestClient
from main import app


def test_new_financial_event_payload_is_aes_gcm_encrypted_and_authentication_fails_closed(tmp_path):
    path = str(tmp_path / "event-encryption.sqlite")
    database.init_db(path)
    raw = sqlite3.connect(path)
    stored = raw.execute("SELECT payload_json FROM domain_events LIMIT 1").fetchone()[0]
    assert stored.startswith("enc:v1:")
    raw.execute("DROP TRIGGER trg_domain_events_no_update")
    raw.execute("UPDATE domain_events SET payload_json=? WHERE sequence=1", ("enc:v1:invalid:broken",))
    raw.commit()
    raw.close()
    conn = sqlite3.connect(path)
    with pytest.raises(Exception):
        read_events(conn)
    conn.close()


def test_mfa_code_never_appears_in_event_or_hmac_audit_payloads():
    client = TestClient(app)
    accounts = {row["id"]: row for row in client.get("/api/accounts").json()}
    source, destination = "acc_checking_123", "acc_savings_456"
    body = {"source_account_id":source,"destination_account_id":destination,"amount":"1000000.00",
            "expected_versions":{source:accounts[source]["version"],destination:accounts[destination]["version"]}}
    pending = client.post("/api/transfers",json=body)
    assert pending.status_code == 202
    confirmed = client.post(f"/api/transfers/{pending.json()['id']}/confirm-mfa",json={"code":"123456"})
    assert confirmed.status_code == 200
    raw = sqlite3.connect(database.get_db_path())
    audit_values = raw.execute("SELECT event_type,actor_id,resource_id,payload_digest,previous_hash,record_hmac FROM audit_logs").fetchall()
    event_values = raw.execute("SELECT payload_json FROM domain_events").fetchall()
    raw.close()
    serialized = repr(audit_values + event_values)
    assert "123456" not in serialized
    assert os.environ["BANK_STORAGE_KEY"] not in serialized
