import uuid
import pytest
from decimal import Decimal
from sqlalchemy import text
from fastapi.testclient import TestClient


def test_transfers_missing_idempotency_key_returns_400(client: TestClient):
    """POST /api/transfers without Idempotency-Key header returns HTTP 400 MISSING_IDEMPOTENCY_KEY."""
    payload = {
        "from_account_id": 1,
        "to_account_id": 2,
        "amount": "25.00",
        "expected_from_version": 1,
        "expected_to_version": 1,
        "description": "Missing header test",
    }
    res = client.post("/api/transfers", json=payload, headers={"omit_idempotency_key": "true"})
    assert res.status_code == 400
    data = res.json()
    assert data["code"] == "MISSING_IDEMPOTENCY_KEY"
    assert "required" in data["message"].lower()


def test_transfers_invalid_idempotency_key_returns_400(client: TestClient):
    """POST /api/transfers with non-UUID Idempotency-Key returns HTTP 400 INVALID_IDEMPOTENCY_KEY."""
    payload = {
        "from_account_id": 1,
        "to_account_id": 2,
        "amount": "25.00",
        "expected_from_version": 1,
        "expected_to_version": 1,
        "description": "Invalid key test",
    }
    res = client.post("/api/transfers", json=payload, headers={"Idempotency-Key": "not-a-valid-uuid"})
    assert res.status_code == 400
    data = res.json()
    assert data["code"] == "INVALID_IDEMPOTENCY_KEY"
    assert "valid uuid" in data["message"].lower()


def test_transfers_empty_idempotency_key_returns_400(client: TestClient):
    """POST /api/transfers with blank/whitespace Idempotency-Key returns HTTP 400 MISSING_IDEMPOTENCY_KEY."""
    payload = {
        "from_account_id": 1,
        "to_account_id": 2,
        "amount": "25.00",
        "expected_from_version": 1,
        "expected_to_version": 1,
        "description": "Empty key test",
    }
    res = client.post("/api/transfers", json=payload, headers={"Idempotency-Key": "   "})
    assert res.status_code == 400
    data = res.json()
    assert data["code"] == "MISSING_IDEMPOTENCY_KEY"


def test_conversions_missing_idempotency_key_returns_400(client: TestClient):
    """POST /api/conversions without Idempotency-Key header returns HTTP 400 MISSING_IDEMPOTENCY_KEY."""
    payload = {
        "from_account_id": 1,
        "to_account_id": 3,
        "source_amount": "50.00",
        "expected_from_version": 1,
        "expected_to_version": 1,
        "description": "Conversion missing header",
    }
    res = client.post("/api/conversions", json=payload, headers={"omit_idempotency_key": "true"})
    assert res.status_code == 400
    data = res.json()
    assert data["code"] == "MISSING_IDEMPOTENCY_KEY"


def test_conversions_invalid_idempotency_key_returns_400(client: TestClient):
    """POST /api/conversions with malformed Idempotency-Key returns HTTP 400 INVALID_IDEMPOTENCY_KEY."""
    payload = {
        "from_account_id": 1,
        "to_account_id": 3,
        "source_amount": "50.00",
        "expected_from_version": 1,
        "expected_to_version": 1,
        "description": "Conversion invalid header",
    }
    res = client.post("/api/conversions", json=payload, headers={"Idempotency-Key": "malformed-key-xyz"})
    assert res.status_code == 400
    data = res.json()
    assert data["code"] == "INVALID_IDEMPOTENCY_KEY"


def test_ach_transfers_missing_idempotency_key_returns_400(client: TestClient):
    """POST /api/transfers/ach without Idempotency-Key header returns HTTP 400 MISSING_IDEMPOTENCY_KEY."""
    payload = {
        "from_account_id": 1,
        "amount": "30.00",
        "expected_from_version": 1,
        "recipient_name": "Test ACH Recipient",
        "routing_number": "123456789",
        "account_number": "987654321",
        "bank_name": "Chase Bank",
        "description": "ACH missing header",
    }
    res = client.post("/api/transfers/ach", json=payload, headers={"omit_idempotency_key": "true"})
    assert res.status_code == 400
    data = res.json()
    assert data["code"] == "MISSING_IDEMPOTENCY_KEY"


def test_ach_transfers_invalid_idempotency_key_returns_400(client: TestClient):
    """POST /api/transfers/ach with non-UUID Idempotency-Key returns HTTP 400 INVALID_IDEMPOTENCY_KEY."""
    payload = {
        "from_account_id": 1,
        "amount": "30.00",
        "expected_from_version": 1,
        "recipient_name": "Test ACH Recipient",
        "routing_number": "123456789",
        "account_number": "987654321",
        "bank_name": "Chase Bank",
        "description": "ACH invalid header",
    }
    res = client.post("/api/transfers/ach", json=payload, headers={"Idempotency-Key": "1234-invalid-uuid"})
    assert res.status_code == 400
    data = res.json()
    assert data["code"] == "INVALID_IDEMPOTENCY_KEY"


def test_transfers_identical_replay_no_duplicate_side_effects(client: TestClient, db_session):
    """Repeating identical transfer returns committed result with zero duplicate events, txs, audits, or limits."""
    acc1 = client.get("/api/accounts/1").json()
    acc2 = client.get("/api/accounts/2").json()

    idemp_key = str(uuid.uuid4())
    payload = {
        "from_account_id": acc1["id"],
        "to_account_id": acc2["id"],
        "amount": "100.00",
        "expected_from_version": acc1["version"],
        "expected_to_version": acc2["version"],
        "description": "Idempotent payment",
    }

    # Initial execution
    res1 = client.post("/api/transfers", json=payload, headers={"Idempotency-Key": idemp_key})
    assert res1.status_code == 200
    data1 = res1.json()

    # Capture state after first execution
    events_after_1 = db_session.execute(text("SELECT COUNT(*) FROM domain_events")).scalar()
    txs_after_1 = db_session.execute(text("SELECT COUNT(*) FROM transactions")).scalar()
    transfers_after_1 = db_session.execute(text("SELECT COUNT(*) FROM transfers")).scalar()
    audits_after_1 = db_session.execute(text("SELECT COUNT(*) FROM audit_logs WHERE event_type = 'transfer_internal'")).scalar()
    idemp_after_1 = db_session.execute(text("SELECT COUNT(*) FROM idempotency_records")).scalar()
    limits_after_1 = client.get("/api/limits").json()["current_daily_total"]
    acc1_after_1 = client.get("/api/accounts/1").json()["balance"]
    acc2_after_1 = client.get("/api/accounts/2").json()["balance"]

    # Replay identical request with same key
    res2 = client.post("/api/transfers", json=payload, headers={"Idempotency-Key": idemp_key})
    assert res2.status_code == 200
    data2 = res2.json()

    # Must return exact same transfer representation
    assert data2["id"] == data1["id"]
    assert data2["operation_id"] == data1["operation_id"]
    assert data2["amount"] == "100.00"

    # Verify zero duplicate financial side effects
    events_after_2 = db_session.execute(text("SELECT COUNT(*) FROM domain_events")).scalar()
    txs_after_2 = db_session.execute(text("SELECT COUNT(*) FROM transactions")).scalar()
    transfers_after_2 = db_session.execute(text("SELECT COUNT(*) FROM transfers")).scalar()
    audits_after_2 = db_session.execute(text("SELECT COUNT(*) FROM audit_logs WHERE event_type = 'transfer_internal'")).scalar()
    idemp_after_2 = db_session.execute(text("SELECT COUNT(*) FROM idempotency_records")).scalar()
    limits_after_2 = client.get("/api/limits").json()["current_daily_total"]
    acc1_after_2 = client.get("/api/accounts/1").json()["balance"]
    acc2_after_2 = client.get("/api/accounts/2").json()["balance"]

    assert events_after_2 == events_after_1
    assert txs_after_2 == txs_after_1
    assert transfers_after_2 == transfers_after_1
    assert audits_after_2 == audits_after_1
    assert idemp_after_2 == idemp_after_1
    assert limits_after_2 == limits_after_1
    assert acc1_after_2 == acc1_after_1
    assert acc2_after_2 == acc2_after_1


def test_transfers_conflicting_parameters_returns_409(client: TestClient):
    """Reusing same Idempotency-Key with different parameters returns HTTP 409 IDEMPOTENCY_KEY_REUSE."""
    acc1 = client.get("/api/accounts/1").json()
    acc2 = client.get("/api/accounts/2").json()

    idemp_key = str(uuid.uuid4())
    payload = {
        "from_account_id": acc1["id"],
        "to_account_id": acc2["id"],
        "amount": "50.00",
        "expected_from_version": acc1["version"],
        "expected_to_version": acc2["version"],
        "description": "Original transfer",
    }

    res1 = client.post("/api/transfers", json=payload, headers={"Idempotency-Key": idemp_key})
    assert res1.status_code == 200

    # Conflicting amount with same idempotency key
    conflict_payload = {**payload, "amount": "75.00"}
    res2 = client.post("/api/transfers", json=conflict_payload, headers={"Idempotency-Key": idemp_key})
    assert res2.status_code == 409
    data2 = res2.json()
    assert data2["code"] == "IDEMPOTENCY_KEY_REUSE"
    assert "different request parameters" in data2["message"].lower()


def test_conversions_identical_replay_no_duplicate_side_effects(client: TestClient, db_session):
    """Repeating identical conversion returns original result with zero duplicate events or audit records."""
    usd = client.get("/api/accounts/1").json()
    eur = client.get("/api/accounts/3").json()

    idemp_key = str(uuid.uuid4())
    payload = {
        "from_account_id": usd["id"],
        "to_account_id": eur["id"],
        "source_amount": "50.00",
        "expected_from_version": usd["version"],
        "expected_to_version": eur["version"],
        "description": "Original FX conversion",
    }

    res1 = client.post("/api/conversions", json=payload, headers={"Idempotency-Key": idemp_key})
    assert res1.status_code == 200
    data1 = res1.json()

    events_after_1 = db_session.execute(text("SELECT COUNT(*) FROM domain_events")).scalar()
    txs_after_1 = db_session.execute(text("SELECT COUNT(*) FROM transactions")).scalar()
    convs_after_1 = db_session.execute(text("SELECT COUNT(*) FROM conversions")).scalar()

    # Replay
    res2 = client.post("/api/conversions", json=payload, headers={"Idempotency-Key": idemp_key})
    assert res2.status_code == 200
    data2 = res2.json()

    assert data2["id"] == data1["id"]
    assert data2["operation_id"] == data1["operation_id"]
    assert data2["destination_amount"] == data1["destination_amount"]

    events_after_2 = db_session.execute(text("SELECT COUNT(*) FROM domain_events")).scalar()
    txs_after_2 = db_session.execute(text("SELECT COUNT(*) FROM transactions")).scalar()
    convs_after_2 = db_session.execute(text("SELECT COUNT(*) FROM conversions")).scalar()

    assert events_after_2 == events_after_1
    assert txs_after_2 == txs_after_1
    assert convs_after_2 == convs_after_1


def test_conversions_conflicting_parameters_returns_409(client: TestClient):
    """Reusing conversion Idempotency-Key with different source_amount returns HTTP 409 IDEMPOTENCY_KEY_REUSE."""
    usd = client.get("/api/accounts/1").json()
    eur = client.get("/api/accounts/3").json()

    idemp_key = str(uuid.uuid4())
    payload = {
        "from_account_id": usd["id"],
        "to_account_id": eur["id"],
        "source_amount": "40.00",
        "expected_from_version": usd["version"],
        "expected_to_version": eur["version"],
        "description": "FX test",
    }

    res1 = client.post("/api/conversions", json=payload, headers={"Idempotency-Key": idemp_key})
    assert res1.status_code == 200

    conflict_payload = {**payload, "source_amount": "80.00"}
    res2 = client.post("/api/conversions", json=conflict_payload, headers={"Idempotency-Key": idemp_key})
    assert res2.status_code == 409
    data2 = res2.json()
    assert data2["code"] == "IDEMPOTENCY_KEY_REUSE"


def test_ach_transfers_identical_replay_no_duplicate_side_effects(client: TestClient, db_session):
    """Repeating identical ACH transfer returns original result without duplicate debits or events."""
    acc = client.get("/api/accounts/1").json()

    idemp_key = str(uuid.uuid4())
    payload = {
        "from_account_id": acc["id"],
        "amount": "45.00",
        "expected_from_version": acc["version"],
        "recipient_name": "ACME Supplier",
        "routing_number": "123456789",
        "account_number": "987654321",
        "bank_name": "Supplier Bank",
        "description": "ACH bill payment",
    }

    res1 = client.post("/api/transfers/ach", json=payload, headers={"Idempotency-Key": idemp_key})
    assert res1.status_code == 200
    data1 = res1.json()

    events_after_1 = db_session.execute(text("SELECT COUNT(*) FROM domain_events")).scalar()
    txs_after_1 = db_session.execute(text("SELECT COUNT(*) FROM transactions")).scalar()
    bal_after_1 = client.get("/api/accounts/1").json()["balance"]

    # Replay
    res2 = client.post("/api/transfers/ach", json=payload, headers={"Idempotency-Key": idemp_key})
    assert res2.status_code == 200
    data2 = res2.json()

    assert data2["id"] == data1["id"]
    assert data2["operation_id"] == data1["operation_id"]

    events_after_2 = db_session.execute(text("SELECT COUNT(*) FROM domain_events")).scalar()
    txs_after_2 = db_session.execute(text("SELECT COUNT(*) FROM transactions")).scalar()
    bal_after_2 = client.get("/api/accounts/1").json()["balance"]

    assert events_after_2 == events_after_1
    assert txs_after_2 == txs_after_1
    assert bal_after_2 == bal_after_1


def test_ach_transfers_conflicting_parameters_returns_409(client: TestClient):
    """Reusing ACH transfer Idempotency-Key with different amount returns HTTP 409 IDEMPOTENCY_KEY_REUSE."""
    acc = client.get("/api/accounts/1").json()

    idemp_key = str(uuid.uuid4())
    payload = {
        "from_account_id": acc["id"],
        "amount": "20.00",
        "expected_from_version": acc["version"],
        "recipient_name": "Vendor A",
        "routing_number": "123456789",
        "account_number": "987654321",
        "bank_name": "Vendor Bank",
    }

    res1 = client.post("/api/transfers/ach", json=payload, headers={"Idempotency-Key": idemp_key})
    assert res1.status_code == 200

    conflict_payload = {**payload, "amount": "40.00"}
    res2 = client.post("/api/transfers/ach", json=conflict_payload, headers={"Idempotency-Key": idemp_key})
    assert res2.status_code == 409
    data2 = res2.json()
    assert data2["code"] == "IDEMPOTENCY_KEY_REUSE"


def test_stale_version_replay_succeeds_before_d14_validation(client: TestClient):
    """Idempotency check occurs BEFORE D-14 version validation: retrying committed operation succeeds."""
    acc1 = client.get("/api/accounts/1").json()
    acc2 = client.get("/api/accounts/2").json()

    idemp_key_1 = str(uuid.uuid4())
    payload_1 = {
        "from_account_id": acc1["id"],
        "to_account_id": acc2["id"],
        "amount": "15.00",
        "expected_from_version": acc1["version"],
        "expected_to_version": acc2["version"],
        "description": "Transfer 1",
    }

    # Execute transfer 1 -> increments versions from (1, 1) to (2, 2)
    res1 = client.post("/api/transfers", json=payload_1, headers={"Idempotency-Key": idemp_key_1})
    assert res1.status_code == 200
    data1 = res1.json()

    # Execute transfer 2 -> increments versions from (2, 2) to (3, 3)
    idemp_key_2 = str(uuid.uuid4())
    payload_2 = {
        "from_account_id": acc1["id"],
        "to_account_id": acc2["id"],
        "amount": "20.00",
        "expected_from_version": 2,
        "expected_to_version": 2,
        "description": "Transfer 2",
    }
    res2 = client.post("/api/transfers", json=payload_2, headers={"Idempotency-Key": idemp_key_2})
    assert res2.status_code == 200

    # Current account versions are now (3, 3).
    # Replay transfer 1 with payload_1 (which has stale versions 1, 1).
    # Because idempotency is evaluated BEFORE D-14 version checks, it must return HTTP 200 with original transfer 1.
    res1_replay = client.post("/api/transfers", json=payload_1, headers={"Idempotency-Key": idemp_key_1})
    assert res1_replay.status_code == 200
    assert res1_replay.json()["id"] == data1["id"]

    # In contrast, an uncommitted NEW transfer with stale versions (1, 1) must be rejected with HTTP 409
    payload_stale_new = {
        "from_account_id": acc1["id"],
        "to_account_id": acc2["id"],
        "amount": "10.00",
        "expected_from_version": 1,
        "expected_to_version": 1,
        "description": "New transfer with stale version",
    }
    res_stale = client.post("/api/transfers", json=payload_stale_new, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert res_stale.status_code == 409
    assert res_stale.json()["code"] == "ACCOUNT_VERSION_CONFLICT"


def test_failed_attempt_does_not_commit_idempotency_record_and_preserves_audit(client: TestClient, db_session):
    """Failed operations (e.g. insufficient funds) rollback, log durable failure audit, and do not commit idempotency."""
    acc1 = client.get("/api/accounts/1").json()
    acc2 = client.get("/api/accounts/2").json()

    idemp_key = str(uuid.uuid4())
    excessive_amount_payload = {
        "from_account_id": acc1["id"],
        "to_account_id": acc2["id"],
        "amount": "999999.00",
        "expected_from_version": acc1["version"],
        "expected_to_version": acc2["version"],
        "description": "Insufficient funds test",
    }

    # Attempt transfer with insufficient funds
    res_fail = client.post("/api/transfers", json=excessive_amount_payload, headers={"Idempotency-Key": idemp_key})
    assert res_fail.status_code == 400

    # Ensure no idempotency record was committed for this key
    idemp_record = db_session.execute(
        text("SELECT COUNT(*) FROM idempotency_records WHERE idempotency_key = :key"),
        {"key": idemp_key},
    ).scalar()
    assert idemp_record == 0

    # Ensure failure audit log exists
    failure_audits = db_session.execute(
        text("SELECT COUNT(*) FROM audit_logs WHERE status = 'FAILURE' AND event_type = 'transfer_internal'")
    ).scalar()
    assert failure_audits >= 1

    # Now execute a valid transfer with the same idempotency key
    valid_payload = {
        "from_account_id": acc1["id"],
        "to_account_id": acc2["id"],
        "amount": "10.00",
        "expected_from_version": acc1["version"],
        "expected_to_version": acc2["version"],
        "description": "Valid retry after earlier validation failure",
    }
    res_success = client.post("/api/transfers", json=valid_payload, headers={"Idempotency-Key": idemp_key})
    assert res_success.status_code == 200
    assert res_success.json()["amount"] == "10.00"


def test_transfers_replay_fallthrough_prevented_when_transfer_entity_missing(client: TestClient, db_session):
    """
    Regression test for D-13 replay fallthrough:
    When an idempotency record exists but the underlying Transfer row cannot be queried,
    the system must fail-closed with a structured integrity error (HTTP 500 IDEMPOTENT_RECORD_CORRUPTED),
    and must NEVER fall through to re-execute the transfer, re-debit accounts, or emit new events.
    """
    acc1 = client.get("/api/accounts/1").json()
    acc2 = client.get("/api/accounts/2").json()

    idemp_key = str(uuid.uuid4())
    payload = {
        "from_account_id": acc1["id"],
        "to_account_id": acc2["id"],
        "amount": "30.00",
        "expected_from_version": acc1["version"],
        "expected_to_version": acc2["version"],
        "description": "Initial transfer for fallthrough test",
    }

    # Initial transfer succeeds
    res1 = client.post("/api/transfers", json=payload, headers={"Idempotency-Key": idemp_key})
    assert res1.status_code == 200
    trf_id = res1.json()["id"]

    # Capture state after initial commit
    events_after_1 = db_session.execute(text("SELECT COUNT(*) FROM domain_events")).scalar()
    txs_after_1 = db_session.execute(text("SELECT COUNT(*) FROM transactions")).scalar()
    bal1_after_1 = client.get("/api/accounts/1").json()["balance"]
    bal2_after_1 = client.get("/api/accounts/2").json()["balance"]

    # Simulate inconsistent state: remove Transfer record while leaving IdempotencyRecord committed
    db_session.execute(text("DELETE FROM transfers WHERE id = :tid"), {"tid": trf_id})
    db_session.commit()

    # Replay identical transfer request
    res_replay = client.post("/api/transfers", json=payload, headers={"Idempotency-Key": idemp_key})

    # Must fail-closed with structured integrity error (HTTP 500 IDEMPOTENT_RECORD_CORRUPTED)
    assert res_replay.status_code == 500
    data = res_replay.json()
    assert data["code"] == "IDEMPOTENT_RECORD_CORRUPTED"
    assert "could not be retrieved" in data["message"].lower()

    # Ensure no side-effects occurred: no new events, no new txs, no balance changes
    events_after_replay = db_session.execute(text("SELECT COUNT(*) FROM domain_events")).scalar()
    txs_after_replay = db_session.execute(text("SELECT COUNT(*) FROM transactions")).scalar()
    bal1_after_replay = client.get("/api/accounts/1").json()["balance"]
    bal2_after_replay = client.get("/api/accounts/2").json()["balance"]

    assert events_after_replay == events_after_1
    assert txs_after_replay == txs_after_1
    assert bal1_after_replay == bal1_after_1
    assert bal2_after_replay == bal2_after_1


def test_ach_transfers_replay_fallthrough_prevented_when_transfer_entity_missing(client: TestClient, db_session):
    """
    Regression test for D-13 ACH replay fallthrough:
    When an idempotency record exists for an ACH transfer but the Transfer row cannot be queried,
    the system must fail-closed with HTTP 500 IDEMPOTENT_RECORD_CORRUPTED and never fall through to re-debit.
    """
    acc1 = client.get("/api/accounts/1").json()

    idemp_key = str(uuid.uuid4())
    payload = {
        "from_account_id": acc1["id"],
        "amount": "40.00",
        "expected_from_version": acc1["version"],
        "recipient_name": "Supplier Corp",
        "routing_number": "123456789",
        "account_number": "987654321",
        "bank_name": "Chase Bank",
        "description": "ACH transfer for fallthrough test",
    }

    # Initial ACH transfer succeeds
    res1 = client.post("/api/transfers/ach", json=payload, headers={"Idempotency-Key": idemp_key})
    assert res1.status_code == 200
    trf_id = res1.json()["id"]

    events_after_1 = db_session.execute(text("SELECT COUNT(*) FROM domain_events")).scalar()
    bal1_after_1 = client.get("/api/accounts/1").json()["balance"]

    # Simulate missing Transfer record
    db_session.execute(text("DELETE FROM transfers WHERE id = :tid"), {"tid": trf_id})
    db_session.commit()

    # Replay identical ACH request
    res_replay = client.post("/api/transfers/ach", json=payload, headers={"Idempotency-Key": idemp_key})

    # Must fail-closed with structured integrity error
    assert res_replay.status_code == 500
    data = res_replay.json()
    assert data["code"] == "IDEMPOTENT_RECORD_CORRUPTED"
    assert "could not be retrieved" in data["message"].lower()

    # Verify no duplicate debits or events
    events_after_replay = db_session.execute(text("SELECT COUNT(*) FROM domain_events")).scalar()
    bal1_after_replay = client.get("/api/accounts/1").json()["balance"]

    assert events_after_replay == events_after_1
    assert bal1_after_replay == bal1_after_1

