import sqlite3
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import database
import pytest
from fastapi import HTTPException
from conftest import _orig_request, create_test_client_envelope
from fastapi.testclient import TestClient
from main import app
from services import execute_due_recurring_schedules, fail_ach_transfer, settle_eligible_ach_transfers
from projections import rebuild_projection


def _accounts(client):
    return {row["id"]: row for row in client.get("/api/accounts").json()}


def _raw_encrypted_post(client, path, payload, key=None, inject_expected_versions=False):
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Idempotency-Key"] = key
    envelope = create_test_client_envelope(dict(payload), inject_expected_versions=inject_expected_versions)
    return _orig_request(client, "POST", path, json=envelope, headers=headers)


def _ach_payload(client, account_id="acc_checking_123", amount="100.00"):
    account = _accounts(client)[account_id]
    return {"source_account_id": account_id, "amount": amount, "recipient_name": "Synthetic Recipient",
            "bank_name": "Synthetic Bank", "routing_number": "123456789", "account_number": "12345678",
            "save_beneficiary": False, "expected_versions": {account_id: account["version"]}}


def test_transfer_raw_http_requires_idempotency_and_current_expected_versions():
    client = TestClient(app)
    accounts = _accounts(client)
    source, destination = "CHK-1001", "SAV-2001"
    payload = {"source_account_id": source, "destination_account_id": destination,
               "amount": "1.00", "expected_versions": {source: accounts[source]["version"], destination: accounts[destination]["version"]}}
    missing_key = _raw_encrypted_post(client, "/api/transfers", payload)
    assert missing_key.status_code == 422
    assert missing_key.json()["detail"]["code"] == "INVALID_IDEMPOTENCY_KEY"

    no_versions = dict(payload)
    no_versions.pop("expected_versions")
    missing_version = _raw_encrypted_post(client, "/api/transfers", no_versions, str(uuid.uuid4()))
    assert missing_version.status_code == 422
    assert missing_version.json()["detail"]["code"] == "MISSING_ACCOUNT_VERSION"

    stale = dict(payload, expected_versions={source: accounts[source]["version"] - 1, destination: accounts[destination]["version"]})
    conflict = _raw_encrypted_post(client, "/api/transfers", stale, str(uuid.uuid4()))
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "ACCOUNT_VERSION_CONFLICT"


def test_ach_requires_real_idempotency_header_and_expected_version():
    client = TestClient(app)
    payload = _ach_payload(client)
    response = _raw_encrypted_post(client, "/api/transfers/ach", payload)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_IDEMPOTENCY_KEY"
    payload.pop("expected_versions")
    response = _raw_encrypted_post(client, "/api/transfers/ach", payload, str(uuid.uuid4()))
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "MISSING_ACCOUNT_VERSION"


def test_recurring_create_raw_http_requires_idempotency_and_each_account_version():
    client = TestClient(app)
    accounts = _accounts(client)
    source, destination = "CHK-1001", "SAV-2001"
    payload = {"transfer_type": "INTERNAL", "source_account_id": source, "destination_account_id": destination,
               "amount": "1.00", "frequency": "DAILY",
               "expected_versions": {source: accounts[source]["version"], destination: accounts[destination]["version"]}}
    missing_key = _raw_encrypted_post(client, "/api/recurring-schedules", payload)
    assert missing_key.status_code == 422
    assert missing_key.json()["detail"]["code"] == "INVALID_IDEMPOTENCY_KEY"
    missing_destination = dict(payload, expected_versions={source: accounts[source]["version"]})
    missing_version = _raw_encrypted_post(client, "/api/recurring-schedules", missing_destination, str(uuid.uuid4()))
    assert missing_version.status_code == 422
    assert missing_version.json()["detail"]["code"] == "MISSING_ACCOUNT_VERSION"


def test_cop_ach_debit_replay_and_settlement_are_evented_once():
    client = TestClient(app)
    source_id = "acc_checking_123"
    before = _accounts(client)[source_id]
    payload = _ach_payload(client, source_id, "125.40")
    key = str(uuid.uuid4())
    first = _raw_encrypted_post(client, "/api/transfers/ach", payload, key)
    replay = _raw_encrypted_post(client, "/api/transfers/ach", payload, key)
    assert first.status_code == 201 and replay.status_code == 201
    assert first.json()["id"] == replay.json()["id"]
    after = _accounts(client)[source_id]
    assert after["balance"] == "4999874.60" and after["version"] == before["version"] + 1
    conn = sqlite3.connect(database.get_db_path())
    transfer_id = first.json()["id"]
    row = conn.execute("SELECT account_number,status FROM transfers WHERE id=?", (transfer_id,)).fetchone()
    assert row[0].startswith("enc:v1:") and row[1] == "PENDING"
    assert conn.execute("SELECT COUNT(*) FROM idempotency_records WHERE idempotency_key=?", (key,)).fetchone()[0] == 1
    event_count = conn.execute("SELECT COUNT(*) FROM domain_events WHERE event_type='AchTransferInitiated' AND command_id=(SELECT stage4_command_id FROM transfers WHERE id=?)", (transfer_id,)).fetchone()[0]
    assert event_count == 1
    conn.execute("UPDATE transfers SET created_at=? WHERE id=?", ((datetime.now(timezone.utc)-timedelta(seconds=9)).strftime("%Y-%m-%dT%H:%M:%SZ"), transfer_id))
    conn.commit()
    assert settle_eligible_ach_transfers(conn, delay_seconds=10) == 0
    conn.execute("UPDATE transfers SET created_at=? WHERE id=?", ((datetime.now(timezone.utc)-timedelta(seconds=11)).strftime("%Y-%m-%dT%H:%M:%SZ"), transfer_id))
    conn.commit()
    conn.close()
    settlement_conn=database.get_connection()
    assert settle_eligible_ach_transfers(settlement_conn, delay_seconds=10) == 1
    settlement_conn.close()
    settlement_conn=database.get_connection()
    assert settle_eligible_ach_transfers(settlement_conn, delay_seconds=10) == 0
    settlement_conn.close()
    settled = _accounts(client)[source_id]
    assert settled["balance"] == after["balance"] and settled["version"] == after["version"]
    conn = sqlite3.connect(database.get_db_path())
    assert conn.execute("SELECT COUNT(*) FROM domain_events WHERE event_type='AchTransferSettled' AND command_id=(SELECT stage4_command_id FROM transfers WHERE id=?)",(transfer_id,)).fetchone()[0] == 1
    assert settle_eligible_ach_transfers(conn, delay_seconds=10) == 0
    conn.close()


def test_usd_ach_is_supported_and_eur_gbp_are_rejected():
    client = TestClient(app)
    usd = _ach_payload(client, "CHK-1001", "10.00")
    response = _raw_encrypted_post(client, "/api/transfers/ach", usd, str(uuid.uuid4()))
    assert response.status_code == 201 and response.json()["currency"] == "USD"
    for account_id in ("EUR-3001", "GBP-4001"):
        payload = _ach_payload(client, account_id, "1.00")
        response = _raw_encrypted_post(client, "/api/transfers/ach", payload, str(uuid.uuid4()))
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "INVALID_CURRENCY"


def test_recurring_ach_currency_policy_supports_cop_usd_and_rejects_eur_gbp():
    client = TestClient(app)
    for account_id, expected_status in (("acc_checking_123", 201), ("CHK-1001", 201), ("EUR-3001", 422), ("GBP-4001", 422)):
        account = _accounts(client)[account_id]
        payload = {"transfer_type": "ACH", "source_account_id": account_id, "amount": "1.00",
                   "frequency": "DAILY", "recipient_name": "Recurring Recipient", "bank_name": "Synthetic Bank",
                   "routing_number": "123456789", "account_number": "12345678", "expected_versions": {account_id: account["version"]}}
        response = _raw_encrypted_post(client, "/api/recurring-schedules", payload, str(uuid.uuid4()))
        assert response.status_code == expected_status, response.text
        if expected_status == 422:
            assert response.json()["detail"]["code"] == "INVALID_CURRENCY"


def test_ach_failure_refunds_once_updates_audit_and_rebuilds_projection():
    client = TestClient(app)
    account_id = "CHK-1001"
    before = _accounts(client)[account_id]
    response = _raw_encrypted_post(client, "/api/transfers/ach", _ach_payload(client, account_id, "15.25"), str(uuid.uuid4()))
    assert response.status_code == 201
    transfer_id = response.json()["id"]
    debited = _accounts(client)[account_id]
    assert Decimal(debited["balance"]) == Decimal(before["balance"]) - Decimal("15.25")
    conn = database.get_connection()
    refund = fail_ach_transfer(conn, transfer_id)
    assert refund["status"] == "FAILED" and refund["refunded_amount"] == "15.25"
    with pytest.raises(HTTPException) as repeated:
        fail_ach_transfer(conn, transfer_id)
    assert repeated.value.status_code == 409
    assert repeated.value.detail["code"] == "TRANSFER_STATE_CONFLICT"
    assert conn.execute("SELECT COUNT(*) FROM domain_events WHERE event_type='AchTransferFailed' AND command_id=(SELECT stage4_command_id FROM transfers WHERE id=?)", (transfer_id,)).fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM history_projection WHERE history_id=?", (f"{transfer_id}:refund:{account_id}",)).fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM audit_logs WHERE resource_id=? AND event_type='ACH_TRANSFER_FAILED'", (transfer_id,)).fetchone()[0] == 1
    assert rebuild_projection(conn) > 0
    conn.close()
    after = _accounts(client)[account_id]
    assert after["balance"] == before["balance"]
    assert after["version"] == before["version"] + 2


def test_ach_beneficiary_bank_fields_are_validated_before_debit():
    client = TestClient(app)
    for field, invalid in (("routing_number", "12345678"), ("account_number", "123"), ("account_number", "1" * 18)):
        payload = _ach_payload(client, "CHK-1001", "1.00")
        payload[field] = invalid
        response = _raw_encrypted_post(client, "/api/transfers/ach", payload, str(uuid.uuid4()))
        assert response.status_code == 400
    assert _accounts(client)["CHK-1001"]["balance"] == "2500.00"


def test_ach_failure_and_settlement_race_has_one_terminal_event_and_at_most_one_refund():
    client = TestClient(app)
    source_id = "CHK-1001"
    before = _accounts(client)[source_id]
    from decimal import Decimal
    expected_balance = Decimal(before["balance"]) - Decimal("20.00")
    response = _raw_encrypted_post(client,"/api/transfers/ach",_ach_payload(client,source_id,"20.00"),str(uuid.uuid4()))
    assert response.status_code == 201
    transfer_id=response.json()["id"]
    conn=database.get_connection()
    conn.execute("UPDATE transfers SET created_at=? WHERE id=?",((datetime.now(timezone.utc)-timedelta(seconds=11)).strftime("%Y-%m-%dT%H:%M:%SZ"),transfer_id))
    conn.commit(); conn.close()
    def settle():
        c=database.get_connection()
        try:
            if settle_eligible_ach_transfers(c,10) != 1: raise RuntimeError("Transfer was not settled by this worker")
            return 1
        finally: c.close()
    def fail():
        c=database.get_connection()
        try: return fail_ach_transfer(c,transfer_id)
        finally: c.close()
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes=list(pool.map(lambda f: _capture(f), (settle,fail)))
    conn=database.get_connection()
    status_value=conn.execute("SELECT status FROM transfers WHERE id=?",(transfer_id,)).fetchone()[0]
    terminal_events=conn.execute("SELECT COUNT(*) FROM domain_events WHERE event_type IN ('AchTransferSettled','AchTransferFailed') AND command_id=(SELECT stage4_command_id FROM transfers WHERE id=?)",(transfer_id,)).fetchone()[0]
    conn.close()
    after=_accounts(client)[source_id]
    assert status_value in {"SETTLED","FAILED"} and terminal_events == 1
    assert after["version"] == before["version"] + (2 if status_value == "FAILED" else 1)
    assert Decimal(after["balance"]) == (Decimal(before["balance"]) if status_value == "FAILED" else expected_balance)
    assert sum(result == "ok" for result in outcomes) == 1
    conn = database.get_connection()
    with pytest.raises(HTTPException) as rejected:
        fail_ach_transfer(conn, transfer_id)
    assert rejected.value.status_code == 409
    assert rejected.value.detail["code"] == "TRANSFER_STATE_CONFLICT"
    assert settle_eligible_ach_transfers(conn, 10) == 0
    conn.close()


def _capture(call):
    try:
        call()
        return "ok"
    except Exception:
        return "conflict"


def test_recurring_occurrence_is_claimed_exactly_once_across_workers_and_replays():
    client=TestClient(app)
    accounts=_accounts(client)
    source,destination="CHK-1001","SAV-2001"
    payload={"transfer_type":"INTERNAL","source_account_id":source,"destination_account_id":destination,
             "amount":"7.25","frequency":"DAILY","expected_versions":{source:accounts[source]["version"],destination:accounts[destination]["version"]}}
    response=client.post("/api/recurring-schedules",json=payload)
    assert response.status_code==201,response.text
    schedule_id=response.json()["id"]
    conn=sqlite3.connect(database.get_db_path())
    due=(datetime.now(timezone.utc)-timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute("UPDATE recurring_schedules SET next_due_date=? WHERE id=?",(due,schedule_id)); conn.commit(); conn.close()
    def execute():
        c=database.get_connection()
        try: return execute_due_recurring_schedules(c)
        finally: c.close()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _: execute(), range(2)))
    assert sum(item[0] for item in results)==1
    conn=database.get_connection()
    assert conn.execute("SELECT COUNT(*) FROM recurring_occurrences WHERE schedule_id=?",(schedule_id,)).fetchone()[0]==1
    assert conn.execute("SELECT COUNT(*) FROM transfers WHERE stage4_command_id=(SELECT command_id FROM recurring_occurrences WHERE schedule_id=?)",(schedule_id,)).fetchone()[0]==1
    conn.close()
    conn=database.get_connection()
    assert rebuild_projection(conn) > 0
    conn.close()
