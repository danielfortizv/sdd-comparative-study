import uuid
import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from backend.app.models import Account, Conversion, DomainEvent, AuditLog


def test_conversion_fixed_rates_and_quantization(client: TestClient, db_session):
    """Test simulated conversion with D-03 reference rates and half-up rounding."""
    accounts = client.get("/api/accounts").json()
    usd_acc = next(a for a in accounts if a["currency"] == "USD")
    eur_acc = next(a for a in accounts if a["currency"] == "EUR")

    idempotency_key = str(uuid.uuid4())
    # 100.00 USD -> EUR at 0.90 rate = 90.00 EUR
    payload = {
        "from_account_id": usd_acc["id"],
        "to_account_id": eur_acc["id"],
        "source_amount": 100.00,
        "expected_from_version": usd_acc["version"],
        "expected_to_version": eur_acc["version"],
        "description": "Test USD to EUR conversion",
    }
    response = client.post("/api/conversions", json=payload, headers={"Idempotency-Key": idempotency_key})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["source_amount"] == "100.00"
    assert data["destination_amount"] == "90.00"
    assert data["source_currency"] == "USD"
    assert data["destination_currency"] == "EUR"
    assert data["rate_numerator"] == 9
    assert data["rate_denominator"] == 10
    assert data["from_account_version"] == usd_acc["version"] + 1
    assert data["to_account_version"] == eur_acc["version"] + 1

    # Verify updated accounts via CQRS query
    updated_usd = client.get(f"/api/accounts/{usd_acc['id']}").json()
    updated_eur = client.get(f"/api/accounts/{eur_acc['id']}").json()
    assert updated_usd["balance"] == f"{Decimal(str(usd_acc['balance'])) - Decimal('100.00'):.2f}"
    assert updated_eur["balance"] == f"{Decimal(str(eur_acc['balance'])) + Decimal('90.00'):.2f}"
    assert updated_usd["version"] == usd_acc["version"] + 1
    assert updated_eur["version"] == eur_acc["version"] + 1


def test_conversion_cross_rates_eur_to_gbp(client: TestClient, db_session):
    """EUR -> GBP derived from reference table: 0.80 / 0.90 = 8/9."""
    accounts = client.get("/api/accounts").json()
    usd_acc = next(a for a in accounts if a["currency"] == "USD")
    eur_acc = next(a for a in accounts if a["currency"] == "EUR")
    gbp_acc = next(a for a in accounts if a["currency"] == "GBP")

    # First fund EUR account from USD
    client.post(
        "/api/conversions",
        json={
            "from_account_id": usd_acc["id"],
            "to_account_id": eur_acc["id"],
            "source_amount": 100.00,
            "expected_from_version": usd_acc["version"],
            "expected_to_version": eur_acc["version"],
        },
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )

    eur_acc_updated = client.get(f"/api/accounts/{eur_acc['id']}").json()
    gbp_acc_current = client.get(f"/api/accounts/{gbp_acc['id']}").json()

    # Now convert 90.00 EUR -> GBP: 90 * 8/9 = 80.00 GBP
    response = client.post(
        "/api/conversions",
        json={
            "from_account_id": eur_acc["id"],
            "to_account_id": gbp_acc["id"],
            "source_amount": 90.00,
            "expected_from_version": eur_acc_updated["version"],
            "expected_to_version": gbp_acc_current["version"],
        },
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["source_amount"] == "90.00"
    assert data["destination_amount"] == "80.00"
    assert data["rate_numerator"] == 8
    assert data["rate_denominator"] == 9


def test_conversion_rejection_same_currency_or_same_account(client: TestClient):
    """Conversions require distinct accounts with different currencies (D-01, D-04)."""
    accounts = client.get("/api/accounts").json()
    usd_checking = next(a for a in accounts if a["account_number"] == "CHK-1001")
    usd_savings = next(a for a in accounts if a["account_number"] == "SAV-2001")

    # Same account
    resp_same_acc = client.post(
        "/api/conversions",
        json={
            "from_account_id": usd_checking["id"],
            "to_account_id": usd_checking["id"],
            "source_amount": 50.00,
            "expected_from_version": usd_checking["version"],
            "expected_to_version": usd_checking["version"],
        },
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert resp_same_acc.status_code == 400

    # Same currency accounts
    resp_same_cur = client.post(
        "/api/conversions",
        json={
            "from_account_id": usd_checking["id"],
            "to_account_id": usd_savings["id"],
            "source_amount": 50.00,
            "expected_from_version": usd_checking["version"],
            "expected_to_version": usd_savings["version"],
        },
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert resp_same_cur.status_code == 400
    assert "different currencies" in resp_same_cur.text or "SAME_CURRENCY" in resp_same_cur.text


def test_legacy_transfer_endpoint_rejects_cross_currency(client: TestClient):
    """Calling POST /api/transfers between different currencies fails with HTTP 400 (D-04)."""
    accounts = client.get("/api/accounts").json()
    usd_acc = next(a for a in accounts if a["currency"] == "USD")
    eur_acc = next(a for a in accounts if a["currency"] == "EUR")

    response = client.post(
        "/api/transfers",
        json={
            "from_account_id": usd_acc["id"],
            "to_account_id": eur_acc["id"],
            "amount": 50.00,
            "expected_from_version": usd_acc["version"],
            "expected_to_version": eur_acc["version"],
        },
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert response.status_code == 400
    assert "CROSS_CURRENCY_NOT_PERMITTED" in response.text or "currency" in response.text.lower()


def test_conversion_idempotency_and_conflict(client: TestClient):
    """Test idempotent replay on matching key and 409 conflict on mismatched params (D-13)."""
    accounts = client.get("/api/accounts").json()
    usd_acc = next(a for a in accounts if a["currency"] == "USD")
    eur_acc = next(a for a in accounts if a["currency"] == "EUR")

    idemp_key = str(uuid.uuid4())
    payload = {
        "from_account_id": usd_acc["id"],
        "to_account_id": eur_acc["id"],
        "source_amount": 50.00,
        "expected_from_version": usd_acc["version"],
        "expected_to_version": eur_acc["version"],
        "description": "Original conversion",
    }

    # First call: 200 OK
    res1 = client.post("/api/conversions", json=payload, headers={"Idempotency-Key": idemp_key})
    assert res1.status_code == 200
    orig_data = res1.json()

    # Replay with same key and same payload: returns identical cached result
    res2 = client.post("/api/conversions", json=payload, headers={"Idempotency-Key": idemp_key})
    assert res2.status_code == 200
    assert res2.json()["operation_id"] == orig_data["operation_id"]

    # Reuse same key with different amount: returns HTTP 409 Conflict
    conflict_payload = {**payload, "source_amount": 75.00}
    res3 = client.post("/api/conversions", json=conflict_payload, headers={"Idempotency-Key": idemp_key})
    assert res3.status_code == 409
    assert "IDEMPOTENCY_KEY_REUSE" in res3.text


def test_conversion_optimistic_concurrency_conflict(client: TestClient):
    """Test that stale account versions produce HTTP 409 ACCOUNT_VERSION_CONFLICT (D-14)."""
    accounts = client.get("/api/accounts").json()
    usd_acc = next(a for a in accounts if a["currency"] == "USD")
    eur_acc = next(a for a in accounts if a["currency"] == "EUR")

    # Stale version supplied
    stale_payload = {
        "from_account_id": usd_acc["id"],
        "to_account_id": eur_acc["id"],
        "source_amount": 20.00,
        "expected_from_version": usd_acc["version"] + 99,
        "expected_to_version": eur_acc["version"],
    }
    response = client.post(
        "/api/conversions",
        json=stale_payload,
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert response.status_code == 409
    assert "ACCOUNT_VERSION_CONFLICT" in response.text


def test_conversion_mfa_requirement_above_1000_usd_equivalent(client: TestClient):
    """Conversions with USD equivalent > 1000.00 trigger MFA PIN requirement (D-07)."""
    accounts = client.get("/api/accounts").json()
    usd_acc = next(a for a in accounts if a["currency"] == "USD")
    eur_acc = next(a for a in accounts if a["currency"] == "EUR")

    # USD 1500.00 > 1000.00 threshold
    payload = {
        "from_account_id": usd_acc["id"],
        "to_account_id": eur_acc["id"],
        "source_amount": 1500.00,
        "expected_from_version": usd_acc["version"],
        "expected_to_version": eur_acc["version"],
    }

    # Without PIN: returns HTTP 428
    res_mfa = client.post("/api/conversions", json=payload, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert res_mfa.status_code == 428

    # With invalid PIN: returns HTTP 400
    res_invalid_pin = client.post(
        "/api/conversions",
        json={**payload, "pin": "9999"},
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert res_invalid_pin.status_code == 400

    # With valid PIN: returns HTTP 200
    res_valid = client.post(
        "/api/conversions",
        json={**payload, "pin": "1234"},
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert res_valid.status_code == 200


def test_conversion_auditing_success_and_failure(client: TestClient, db_session):
    """Currency conversion emits independent HMAC audit entries on success and failure (D-11)."""
    accounts = client.get("/api/accounts").json()
    usd_acc = next(a for a in accounts if a["currency"] == "USD")
    eur_acc = next(a for a in accounts if a["currency"] == "EUR")

    # 1. Success conversion
    res = client.post(
        "/api/conversions",
        json={
            "from_account_id": usd_acc["id"],
            "to_account_id": eur_acc["id"],
            "source_amount": 25.00,
            "expected_from_version": usd_acc["version"],
            "expected_to_version": eur_acc["version"],
        },
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert res.status_code == 200

    audit_entry = (
        db_session.query(AuditLog)
        .filter(AuditLog.event_type == "currency_conversion", AuditLog.status == "SUCCESS")
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert audit_entry is not None
    assert "25.00" in audit_entry.details
    assert audit_entry.signature is not None


def test_conversion_missing_expected_versions_fails(client: TestClient):
    """Conversion fails with HTTP 422 if expected_from_version or expected_to_version is missing (D-14)."""
    accounts = client.get("/api/accounts").json()
    usd_acc = next(a for a in accounts if a["currency"] == "USD")
    eur_acc = next(a for a in accounts if a["currency"] == "EUR")

    # Missing expected_from_version
    p1 = {
        "from_account_id": usd_acc["id"],
        "to_account_id": eur_acc["id"],
        "source_amount": 10.00,
        "expected_to_version": eur_acc["version"],
    }
    r1 = client.post("/api/conversions", json=p1, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert r1.status_code == 422

    # Missing expected_to_version
    p2 = {
        "from_account_id": usd_acc["id"],
        "to_account_id": eur_acc["id"],
        "source_amount": 10.00,
        "expected_from_version": usd_acc["version"],
    }
    r2 = client.post("/api/conversions", json=p2, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert r2.status_code == 422


def test_conversion_invalid_expected_versions_fails(client: TestClient):
    """Conversion fails with HTTP 422 if expected versions are negative or invalid (D-14)."""
    accounts = client.get("/api/accounts").json()
    usd_acc = next(a for a in accounts if a["currency"] == "USD")
    eur_acc = next(a for a in accounts if a["currency"] == "EUR")

    p = {
        "from_account_id": usd_acc["id"],
        "to_account_id": eur_acc["id"],
        "source_amount": 10.00,
        "expected_from_version": -1,
        "expected_to_version": eur_acc["version"],
    }
    r = client.post("/api/conversions", json=p, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert r.status_code == 422


def test_concurrent_conversions_same_version_conflict_d14(tmp_path, monkeypatch):
    """
    D-14 Concurrency Test for Conversions:
    When two simultaneous conversion requests compete using the same expected account version,
    exactly one succeeds (200), and the competing request is rejected with HTTP 409 ACCOUNT_VERSION_CONFLICT.
    """
    import threading
    from decimal import Decimal
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from backend.app.database import Base
    from backend.app.models import Account, Conversion, DomainEvent
    from backend.app.schemas import ConversionRequest
    from backend.app.services.account_service import seed_initial_data
    from backend.app.services.migration_service import run_stage4_event_sourcing_migration
    from backend.app.services import conversion_service, audit_service, event_store
    from backend.app.services.projection_service import verify_projections_integrity

    db_path = tmp_path / "concurrent_conv_d14.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False, "timeout": 15},
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    audit_service.set_session_factory(Session)

    init_db = Session()
    try:
        seed_initial_data(init_db)
        run_stage4_event_sourcing_migration(init_db)
    finally:
        init_db.close()

    barrier = threading.Barrier(2)
    original_append = conversion_service.append_domain_event

    def synchronized_append(*args, **kwargs):
        barrier.wait()
        return original_append(*args, **kwargs)

    monkeypatch.setattr(conversion_service, "append_domain_event", synchronized_append)

    results = []
    errors = []

    def worker_conversion(source_amt: str, key_str: str):
        db = Session()
        try:
            req = ConversionRequest(
                from_account_id=1,
                to_account_id=3,
                source_amount=source_amt,
                expected_from_version=1,
                expected_to_version=1,
                description=f"Concurrent FX of {source_amt}",
            )
            res = conversion_service.execute_conversion(
                db=db,
                request=req,
                idempotency_key=key_str,
                user_id=1,
            )
            results.append({"status": 200, "conversion_id": res.id})
        except Exception as e:
            errors.append(e)
        finally:
            db.close()

    t1 = threading.Thread(target=worker_conversion, args=("10.00", str(uuid.uuid4())))
    t2 = threading.Thread(target=worker_conversion, args=("20.00", str(uuid.uuid4())))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert len(results) == 1, f"Expected exactly 1 success, got {len(results)}"
    assert len(errors) == 1, f"Expected exactly 1 error, got {len(errors)}"
    err = errors[0]
    from fastapi import HTTPException
    assert isinstance(err, HTTPException)
    assert err.status_code == 409
    err_code = err.detail.get("code") if isinstance(err.detail, dict) else str(err.detail)
    assert err_code == "ACCOUNT_VERSION_CONFLICT"

    verify_db = Session()
    try:
        assert verify_projections_integrity(verify_db) is True
    finally:
        verify_db.close()
        engine.dispose()


