import uuid
import sqlite3
import database
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
import os
from main import app


def _versions(client, *account_ids):
    accounts = {row["id"]: row for row in client.get("/api/accounts").json()}
    return {account_id: accounts[account_id]["version"] for account_id in account_ids}


def test_accounts_keep_cop_and_add_all_d02_accounts():
    client = TestClient(app)
    rows = {row["id"]: row for row in client.get("/api/accounts").json()}
    assert set(rows) == {"acc_checking_123", "acc_savings_456", "CHK-1001", "SAV-2001", "EUR-3001", "GBP-4001"}
    assert all("currency" in row and "balance" in row for row in rows.values())
    assert all("estimated_usd_total" not in row for row in rows.values())
    assert (rows["acc_checking_123"]["balance"], rows["acc_checking_123"]["currency"]) == ("5000000.00", "COP")
    assert (rows["acc_savings_456"]["balance"], rows["acc_savings_456"]["currency"]) == ("15000000.00", "COP")
    assert [(rows[x]["balance"], rows[x]["currency"]) for x in ("CHK-1001", "SAV-2001", "EUR-3001", "GBP-4001")] == [
        ("2500.00", "USD"), ("10000.00", "USD"), ("0.00", "EUR"), ("0.00", "GBP")]


def test_internal_transfer_atomic_exact_replay_and_changed_key_conflict():
    client = TestClient(app)
    source, destination = "CHK-1001", "SAV-2001"
    expected = _versions(client, source, destination)
    key = str(uuid.uuid4())
    payload = {"source_account_id": source, "destination_account_id": destination,
               "amount": "25.50", "expected_versions": expected}
    first = client.post("/api/transfers", json=payload, headers={"Idempotency-Key": key})
    assert first.status_code == 200, first.text
    assert first.json()["source_version"] == expected[source] + 1
    raw = sqlite3.connect(database.get_db_path())
    stored_event = raw.execute("SELECT payload_json FROM domain_events ORDER BY sequence DESC LIMIT 1").fetchone()[0]
    stored_response = raw.execute("SELECT response_json FROM idempotency_records WHERE idempotency_key=?", (key,)).fetchone()[0]
    stored_projection = raw.execute("SELECT amount_minor FROM history_projection ORDER BY rowid DESC LIMIT 1").fetchone()[0]
    assert stored_event.startswith("enc:v1:")
    assert stored_response.startswith("enc:v1:")
    assert stored_projection.startswith("enc:v1:")
    raw.close()
    replay = client.post("/api/transfers", json=payload, headers={"Idempotency-Key": key})
    assert replay.status_code == 200 and replay.json() == first.json()
    changed = {**payload, "amount": "26.00"}
    conflict = client.post("/api/transfers", json=changed, headers={"Idempotency-Key": key})
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "IDEMPOTENCY_KEY_CONFLICT"


def test_concurrent_exact_idempotency_replays_return_one_committed_result():
    source, destination = "CHK-1001", "SAV-2001"
    expected = _versions(TestClient(app), source, destination)
    payload = {"source_account_id":source,"destination_account_id":destination,"amount":"1.00","expected_versions":expected}
    key = str(uuid.uuid4())
    def send():
        return TestClient(app).post("/api/transfers",json=payload,headers={"Idempotency-Key":key})
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _i: send(), range(2)))
    assert [r.status_code for r in responses] == [200,200]
    assert responses[0].json() == responses[1].json()


def test_stale_versions_and_cross_currency_transfer_rejected_without_effects():
    client = TestClient(app)
    stale = {"source_account_id": "CHK-1001", "destination_account_id": "SAV-2001",
             "amount": "1.00", "expected_versions": {"CHK-1001": -1, "SAV-2001": 0}}
    response = client.post("/api/transfers", json=stale, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "ACCOUNT_VERSION_CONFLICT"
    cop = {"source_account_id": "acc_checking_123", "destination_account_id": "CHK-1001",
           "amount": "1.00", "expected_versions": _versions(client, "acc_checking_123", "CHK-1001")}
    response = client.post("/api/transfers", json=cop, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_CURRENCY"


def test_conversion_exact_rate_and_cop_conversion_rejection():
    client = TestClient(app)
    source, destination = "CHK-1001", "EUR-3001"
    payload = {"source_account_id": source, "destination_account_id": destination,
               "source_amount": "100.00", "expected_versions": _versions(client, source, destination)}
    balances_before = {row["id"]: row["balance"] for row in client.get("/api/accounts").json()}
    key = str(uuid.uuid4())
    response = client.post("/api/conversions", json=payload, headers={"Idempotency-Key": key})
    assert response.status_code == 200, response.text
    assert response.json()["destination_amount"] == "90.00"
    balances_after = {row["id"]: row["balance"] for row in client.get("/api/accounts").json()}
    from decimal import Decimal
    assert Decimal(balances_before[source]) - Decimal(balances_after[source]) == Decimal("100.00")
    assert Decimal(balances_after[destination]) - Decimal(balances_before[destination]) == Decimal("90.00")
    assert (response.json()["rate_numerator"], response.json()["rate_denominator"]) == (9, 10)
    history = client.get(f"/api/accounts/{source}/history").json()
    conversion_entry = next(row for row in history if row["id"] == response.json()["id"])
    assert conversion_entry["currency"] == "USD"
    assert conversion_entry["counter_amount"] == "90.00"
    assert conversion_entry["counter_currency"] == "EUR"
    assert (conversion_entry["rate_numerator"], conversion_entry["rate_denominator"]) == (9, 10)
    replay = client.post("/api/conversions", json=payload, headers={"Idempotency-Key": key})
    assert replay.status_code == 200 and replay.json() == response.json()
    changed = {**payload, "source_amount": "101.00"}
    changed_response = client.post("/api/conversions", json=changed, headers={"Idempotency-Key": key})
    assert changed_response.status_code == 409
    assert changed_response.json()["detail"]["code"] == "IDEMPOTENCY_KEY_CONFLICT"
    stale = {**payload, "expected_versions": {source: -1, destination: 0}}
    stale_response = client.post("/api/conversions", json=stale, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert stale_response.status_code == 409
    assert stale_response.json()["detail"]["code"] == "ACCOUNT_VERSION_CONFLICT"
    before_no_funds = _versions(client, "EUR-3001", "GBP-4001")
    no_funds = {"source_account_id":"EUR-3001","destination_account_id":"GBP-4001","source_amount":"1000.00","expected_versions":before_no_funds}
    no_funds_response = client.post("/api/conversions",json=no_funds,headers={"Idempotency-Key":str(uuid.uuid4())})
    assert no_funds_response.status_code == 400
    assert no_funds_response.json()["detail"]["code"] == "INSUFFICIENT_FUNDS"
    assert _versions(client, "EUR-3001", "GBP-4001") == before_no_funds
    cop = {"source_account_id": "acc_checking_123", "destination_account_id": "EUR-3001",
           "source_amount": "1.00", "expected_versions": _versions(client, "acc_checking_123", "EUR-3001")}
    rejected = client.post("/api/conversions", json=cop, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert rejected.status_code == 422


def test_mfa_threshold_creates_pending_then_versioned_confirmation():
    client = TestClient(app)
    source, destination = "acc_checking_123", "acc_savings_456"
    payload = {"source_account_id": source, "destination_account_id": destination,
               "amount": "1000000.00", "expected_versions": _versions(client, source, destination)}
    pending = client.post("/api/transfers", json=payload, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert pending.status_code == 202, pending.text
    assert pending.json()["status"] == "PENDING_MFA"
    before = _versions(client, source, destination)
    confirmed = client.post(f"/api/transfers/{pending.json()['id']}/confirm-mfa", json={"code": "123456"})
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "COMPLETED"
    after = _versions(client, source, destination)
    assert after[source] == before[source] + 1
    assert after[destination] == before[destination] + 1


def test_two_commands_with_same_expected_versions_only_one_commits():
    client = TestClient(app)
    source, destination = "CHK-1001", "SAV-2001"
    expected = _versions(client, source, destination)
    payload = {"source_account_id": source, "destination_account_id": destination,
               "amount": "1.00", "expected_versions": expected}
    first = client.post("/api/transfers", json=payload, headers={"Idempotency-Key": str(uuid.uuid4())})
    second = client.post("/api/transfers", json=payload, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "ACCOUNT_VERSION_CONFLICT"


def test_concurrent_commands_race_on_same_versions():
    source, destination = "CHK-1001", "SAV-2001"
    client = TestClient(app)
    expected = _versions(client, source, destination)
    def send():
        isolated = TestClient(app)
        body = {"source_account_id":source,"destination_account_id":destination,"amount":"1.00","expected_versions":expected}
        return isolated.post("/api/transfers",json=body,headers={"Idempotency-Key":str(uuid.uuid4())})
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _i: send(), range(2)))
    assert sorted(r.status_code for r in results) == [200,409]


def test_projection_diagnostics_are_admin_protected_and_replay_is_deterministic():
    client = TestClient(app)
    assert client.get("/api/projections/status").status_code == 401
    headers = {"X-Audit-Admin-Key": os.environ["AUDIT_ADMIN_KEY"]}
    first = client.get("/api/projections/status", headers=headers)
    assert first.status_code == 200
    replay = client.post("/api/projections/rebuild", headers=headers)
    assert replay.status_code == 200
    second = client.get("/api/projections/status", headers=headers)
    assert replay.json()["event_stream_hash"] == second.json()["event_stream_hash"]
