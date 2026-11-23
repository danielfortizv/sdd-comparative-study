import uuid
import pytest
from fastapi.testclient import TestClient


def test_transfer_under_threshold_executes_without_pin(client: TestClient):
    """Transfers <= $1,000 execute immediately without requiring MFA PIN."""
    accounts = client.get("/api/accounts").json()
    checking = next(a for a in accounts if a["account_number"] == "CHK-1001")
    savings = next(a for a in accounts if a["account_number"] == "SAV-2001")

    payload = {
        "from_account_id": checking["id"],
        "to_account_id": savings["id"],
        "amount": 250.00,
        "expected_from_version": checking["version"],
        "expected_to_version": savings["version"],
        "description": "Savings boost",
    }
    response = client.post("/api/transfers", json=payload, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["amount"] == "250.00"
    assert data["status"] == "completed"

    # Verify balances updated atomically
    updated_checking = client.get(f"/api/accounts/{checking['id']}").json()
    updated_savings = client.get(f"/api/accounts/{savings['id']}").json()
    assert updated_checking["balance"] == "2250.00"  # 2500 - 250
    assert updated_savings["balance"] == "10250.00"  # 10000 + 250
    assert updated_checking["version"] == checking["version"] + 1
    assert updated_savings["version"] == savings["version"] + 1


def test_transfer_over_threshold_requires_pin(client: TestClient):
    """Transfers > $1,000 without PIN return HTTP 428 Precondition Required with MFA_REQUIRED and message."""
    accounts = client.get("/api/accounts").json()
    checking = next(a for a in accounts if a["account_number"] == "CHK-1001")
    savings = next(a for a in accounts if a["account_number"] == "SAV-2001")

    payload = {
        "from_account_id": savings["id"],
        "to_account_id": checking["id"],
        "amount": 1500.00,
        "expected_from_version": savings["version"],
        "expected_to_version": checking["version"],
        "description": "Large transfer without PIN",
    }
    response = client.post("/api/transfers", json=payload, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert response.status_code == 428
    assert response.json() == {
        "detail": "MFA_REQUIRED",
        "message": "Security PIN required for transfers over $1,000",
    }

    # Verify balances NOT modified
    assert client.get(f"/api/accounts/{savings['id']}").json()["balance"] == "10000.00"


def test_transfer_exact_boundary_1000_executes_without_pin(client: TestClient):
    """Transfers of exactly $1,000.00 execute immediately without requiring MFA PIN."""
    accounts = client.get("/api/accounts").json()
    checking = next(a for a in accounts if a["account_number"] == "CHK-1001")
    savings = next(a for a in accounts if a["account_number"] == "SAV-2001")

    payload = {
        "from_account_id": checking["id"],
        "to_account_id": savings["id"],
        "amount": 1000.00,
        "expected_from_version": checking["version"],
        "expected_to_version": savings["version"],
        "description": "Exact boundary transfer of $1,000.00",
    }
    response = client.post("/api/transfers", json=payload, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["amount"] == "1000.00"

    # Verify balances updated
    assert client.get(f"/api/accounts/{checking['id']}").json()["balance"] == "1500.00"
    assert client.get(f"/api/accounts/{savings['id']}").json()["balance"] == "11000.00"


def test_transfer_exact_boundary_1000_01_without_pin_returns_http_428(client: TestClient):
    """Transfers of boundary amount $1,000.01 without PIN return HTTP 428 with full contract."""
    accounts = client.get("/api/accounts").json()
    checking = next(a for a in accounts if a["account_number"] == "CHK-1001")
    savings = next(a for a in accounts if a["account_number"] == "SAV-2001")

    initial_tx_count = len(client.get("/api/transactions").json())

    payload = {
        "from_account_id": savings["id"],
        "to_account_id": checking["id"],
        "amount": 1000.01,
        "expected_from_version": savings["version"],
        "expected_to_version": checking["version"],
        "description": "Boundary amount exceeding threshold by $0.01",
    }
    response = client.post("/api/transfers", json=payload, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert response.status_code == 428
    assert response.json() == {
        "detail": "MFA_REQUIRED",
        "message": "Security PIN required for transfers over $1,000",
    }

    # Verify rejected transfer does not alter balances or transaction history
    assert client.get(f"/api/accounts/{savings['id']}").json()["balance"] == "10000.00"
    assert client.get(f"/api/accounts/{checking['id']}").json()["balance"] == "2500.00"
    assert len(client.get("/api/transactions").json()) == initial_tx_count


def test_transfer_exact_boundary_1000_01_with_valid_pin_succeeds(client: TestClient):
    """Transfers of boundary amount $1,000.01 with valid PIN execute successfully."""
    accounts = client.get("/api/accounts").json()
    checking = next(a for a in accounts if a["account_number"] == "CHK-1001")
    savings = next(a for a in accounts if a["account_number"] == "SAV-2001")

    initial_tx_count = len(client.get("/api/transactions").json())

    payload = {
        "from_account_id": savings["id"],
        "to_account_id": checking["id"],
        "amount": 1000.01,
        "expected_from_version": savings["version"],
        "expected_to_version": checking["version"],
        "description": "Authorized boundary transfer of $1,000.01",
        "pin": "1234",
    }
    response = client.post("/api/transfers", json=payload, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["amount"] == "1000.01"

    # Verify balances updated atomically
    assert client.get(f"/api/accounts/{savings['id']}").json()["balance"] == "8999.99"
    assert client.get(f"/api/accounts/{checking['id']}").json()["balance"] == "3500.01"

    new_txs = client.get("/api/transactions").json()
    assert len(new_txs) == initial_tx_count + 2


def test_transfer_over_threshold_with_valid_pin_succeeds(client: TestClient):
    """Transfers > $1,000 with valid Security PIN ('1234') execute successfully."""
    accounts = client.get("/api/accounts").json()
    checking = next(a for a in accounts if a["account_number"] == "CHK-1001")
    savings = next(a for a in accounts if a["account_number"] == "SAV-2001")

    payload = {
        "from_account_id": savings["id"],
        "to_account_id": checking["id"],
        "amount": 2000.00,
        "expected_from_version": savings["version"],
        "expected_to_version": checking["version"],
        "description": "Large authorized transfer",
        "pin": "1234",
    }
    response = client.post("/api/transfers", json=payload, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert response.status_code == 200
    assert response.json()["status"] == "completed"

    assert client.get(f"/api/accounts/{savings['id']}").json()["balance"] == "8000.00"
    assert client.get(f"/api/accounts/{checking['id']}").json()["balance"] == "4500.00"


def test_transfer_to_same_account_fails(client: TestClient):
    """Transfer fails with HTTP 400 when from_account_id equals to_account_id."""
    accounts = client.get("/api/accounts").json()
    checking = accounts[0]

    payload = {
        "from_account_id": checking["id"],
        "to_account_id": checking["id"],
        "amount": 100.00,
        "expected_from_version": checking["version"],
        "expected_to_version": checking["version"],
    }
    response = client.post("/api/transfers", json=payload, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert response.status_code == 400
    assert "same account" in response.text.lower()


def test_transfer_cross_currency_fails(client: TestClient):
    """Transfer between different currencies fails with HTTP 400 CROSS_CURRENCY_NOT_PERMITTED (D-04)."""
    accounts = client.get("/api/accounts").json()
    usd_acc = next(a for a in accounts if a["currency"] == "USD")
    eur_acc = next(a for a in accounts if a["currency"] == "EUR")

    payload = {
        "from_account_id": usd_acc["id"],
        "to_account_id": eur_acc["id"],
        "amount": 50.00,
        "expected_from_version": usd_acc["version"],
        "expected_to_version": eur_acc["version"],
    }
    response = client.post("/api/transfers", json=payload, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert response.status_code == 400
    assert "CROSS_CURRENCY_NOT_PERMITTED" in response.text or "currency" in response.text.lower()


def test_transfer_insufficient_funds_fails(client: TestClient):
    """Transfer fails with HTTP 400 when amount exceeds source account balance."""
    accounts = client.get("/api/accounts").json()
    checking = next(a for a in accounts if a["account_number"] == "CHK-1001")
    savings = next(a for a in accounts if a["account_number"] == "SAV-2001")

    payload = {
        "from_account_id": checking["id"],  # Balance: 2500
        "to_account_id": savings["id"],
        "amount": 3000.00,  # Exceeds balance
        "expected_from_version": checking["version"],
        "expected_to_version": savings["version"],
        "pin": "1234",
    }
    response = client.post("/api/transfers", json=payload, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert response.status_code == 400
    assert "insufficient funds" in response.text.lower()


def test_transfer_non_positive_amount_fails(client: TestClient):
    """Transfer fails with HTTP 422 if amount is <= 0."""
    accounts = client.get("/api/accounts").json()
    payload = {
        "from_account_id": accounts[0]["id"],
        "to_account_id": accounts[1]["id"],
        "amount": 0.0,
        "expected_from_version": 1,
        "expected_to_version": 1,
    }
    response = client.post("/api/transfers", json=payload, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert response.status_code == 422


def test_transfer_more_than_two_decimals_fails(client: TestClient):
    """Transfer fails with HTTP 422 if amount has more than 2 decimal places."""
    accounts = client.get("/api/accounts").json()
    payload = {
        "from_account_id": accounts[0]["id"],
        "to_account_id": accounts[1]["id"],
        "amount": 50.123,
        "expected_from_version": 1,
        "expected_to_version": 1,
    }
    response = client.post("/api/transfers", json=payload, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert response.status_code == 422


def test_transfer_non_existent_account_fails(client: TestClient):
    """Transfer fails with HTTP 404 if source or destination does not exist."""
    accounts = client.get("/api/accounts").json()
    payload = {
        "from_account_id": accounts[0]["id"],
        "to_account_id": 99999,
        "amount": 50.00,
        "expected_from_version": 1,
        "expected_to_version": 1,
    }
    response = client.post("/api/transfers", json=payload, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert response.status_code == 404


def test_transfer_missing_expected_versions_fails(client: TestClient):
    """Transfer fails with HTTP 422 if expected_from_version or expected_to_version is missing (D-14)."""
    accounts = client.get("/api/accounts").json()
    checking = accounts[0]
    savings = accounts[1]

    # Missing expected_from_version
    p1 = {
        "from_account_id": checking["id"],
        "to_account_id": savings["id"],
        "amount": 25.00,
        "expected_to_version": savings["version"],
    }
    r1 = client.post("/api/transfers", json=p1, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert r1.status_code == 422

    # Missing expected_to_version
    p2 = {
        "from_account_id": checking["id"],
        "to_account_id": savings["id"],
        "amount": 25.00,
        "expected_from_version": checking["version"],
    }
    r2 = client.post("/api/transfers", json=p2, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert r2.status_code == 422


def test_transfer_invalid_expected_versions_fails(client: TestClient):
    """Transfer fails with HTTP 422 if expected versions are negative or invalid (D-14)."""
    accounts = client.get("/api/accounts").json()
    checking = accounts[0]
    savings = accounts[1]

    payload = {
        "from_account_id": checking["id"],
        "to_account_id": savings["id"],
        "amount": 25.00,
        "expected_from_version": -1,
        "expected_to_version": savings["version"],
    }
    response = client.post("/api/transfers", json=payload, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert response.status_code == 422


def test_transfer_optimistic_concurrency_conflict(client: TestClient):
    """Transfer fails with HTTP 409 ACCOUNT_VERSION_CONFLICT when expected versions are stale (D-14)."""
    accounts = client.get("/api/accounts").json()
    checking = accounts[0]
    savings = accounts[1]

    # Stale expected_from_version
    p1 = {
        "from_account_id": checking["id"],
        "to_account_id": savings["id"],
        "amount": 25.00,
        "expected_from_version": checking["version"] + 99,
        "expected_to_version": savings["version"],
    }
    r1 = client.post("/api/transfers", json=p1, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert r1.status_code == 409
    assert "ACCOUNT_VERSION_CONFLICT" in r1.text

    # Stale expected_to_version
    p2 = {
        "from_account_id": checking["id"],
        "to_account_id": savings["id"],
        "amount": 25.00,
        "expected_from_version": checking["version"],
        "expected_to_version": savings["version"] + 99,
    }
    r2 = client.post("/api/transfers", json=p2, headers={"Idempotency-Key": str(uuid.uuid4())})
    assert r2.status_code == 409
    assert "ACCOUNT_VERSION_CONFLICT" in r2.text


def test_transfer_idempotency_before_version_check(client: TestClient):
    """Idempotent retry returns committed result even if account versions have changed (D-14)."""
    accounts = client.get("/api/accounts").json()
    checking = accounts[0]
    savings = accounts[1]

    idemp_key = str(uuid.uuid4())
    payload = {
        "from_account_id": checking["id"],
        "to_account_id": savings["id"],
        "amount": 30.00,
        "expected_from_version": checking["version"],
        "expected_to_version": savings["version"],
        "description": "Original transfer",
    }

    # Initial transfer succeeds
    r1 = client.post("/api/transfers", json=payload, headers={"Idempotency-Key": idemp_key})
    assert r1.status_code == 200
    orig_data = r1.json()

    # Replay with same key and same payload: returns identical result even though account versions have incremented
    r2 = client.post("/api/transfers", json=payload, headers={"Idempotency-Key": idemp_key})
    assert r2.status_code == 200
    assert r2.json()["id"] == orig_data["id"]


def test_concurrent_transfers_same_version_conflict_d14(tmp_path, monkeypatch):
    """
    D-14 Concurrency Test:
    When two simultaneous requests genuinely compete using the same expected account version,
    exactly one transfer must succeed (200), and the competing request must be rejected with
    HTTP 409 ACCOUNT_VERSION_CONFLICT, ensuring zero duplicate debits or events.
    """
    import threading
    from decimal import Decimal
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from backend.app.database import Base
    from backend.app.models import Account, Transfer, DomainEvent, Transaction
    from backend.app.schemas import TransferRequest
    from backend.app.services.account_service import seed_initial_data
    from backend.app.services.migration_service import run_stage4_event_sourcing_migration
    from backend.app.services import transfer_service, audit_service, event_store
    from backend.app.services.projection_service import verify_projections_integrity

    db_path = tmp_path / "concurrent_d14_test.db"
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

    # Verify initial accounts: Checking (id=1) has $2,500.00 and version=1
    check_db = Session()
    try:
        chk_init = check_db.query(Account).filter(Account.id == 1).first()
        sav_init = check_db.query(Account).filter(Account.id == 2).first()
        assert chk_init.version == 1
        assert sav_init.version == 1
        assert chk_init.balance == Decimal("2500.00")
        assert sav_init.balance == Decimal("10000.00")
    finally:
        check_db.close()

    # Synchronize execution: barrier ensures both threads have loaded accounts with version 1
    # before either calls append_domain_event and commits
    barrier = threading.Barrier(2)
    original_append = transfer_service.append_domain_event

    def synchronized_append(*args, **kwargs):
        barrier.wait()
        return original_append(*args, **kwargs)

    monkeypatch.setattr(transfer_service, "append_domain_event", synchronized_append)

    results = []
    errors = []

    def worker_transfer(amount_str: str, key_str: str):
        db = Session()
        try:
            req = TransferRequest(
                from_account_id=1,
                to_account_id=2,
                amount=amount_str,
                expected_from_version=1,
                expected_to_version=1,
                description=f"Concurrent transfer of {amount_str}",
            )
            trf = transfer_service.execute_transfer(
                db=db,
                user_id=1,
                request=req,
                idempotency_key=key_str,
            )
            results.append({"status": 200, "transfer_id": trf.id, "amount": amount_str})
        except Exception as e:
            errors.append(e)
        finally:
            db.close()

    key1 = str(uuid.uuid4())
    key2 = str(uuid.uuid4())

    t1 = threading.Thread(target=worker_transfer, args=("10.00", key1))
    t2 = threading.Thread(target=worker_transfer, args=("20.00", key2))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Verification:
    # 1. Exactly one transfer must succeed
    assert len(results) == 1, f"Expected exactly 1 success, but got {len(results)} successes: {results}"
    assert len(errors) == 1, f"Expected exactly 1 error, but got {len(errors)} errors: {errors}"

    # 2. Competing stale-version operation must raise HTTPException 409 with ACCOUNT_VERSION_CONFLICT
    err = errors[0]
    from fastapi import HTTPException
    assert isinstance(err, HTTPException), f"Expected HTTPException but got {type(err)}: {err}"
    assert err.status_code == 409, f"Expected HTTP 409 but got {err.status_code}: {err.detail}"
    err_code = err.detail.get("code") if isinstance(err.detail, dict) else str(err.detail)
    assert err_code == "ACCOUNT_VERSION_CONFLICT", f"Expected ACCOUNT_VERSION_CONFLICT, got {err.detail}"

    # 3. Check database consistency:
    # Exactly one financial domain event and one transfer
    verify_db = Session()
    try:
        transfers = verify_db.query(Transfer).all()
        events = verify_db.query(DomainEvent).filter(DomainEvent.event_type == "InternalTransferCompleted").all()
        txs = verify_db.query(Transaction).all()
        chk = verify_db.query(Account).filter(Account.id == 1).first()
        sav = verify_db.query(Account).filter(Account.id == 2).first()

        assert len(transfers) == 1
        assert len(events) == 1
        # Seed has 3 transactions, + 2 (1 debit, 1 credit) from winning transfer = 5
        assert len(txs) == 5

        # Winner was 10.00 or 20.00
        won_amt = Decimal(results[0]["amount"])
        assert chk.balance == Decimal("2500.00") - won_amt
        assert sav.balance == Decimal("10000.00") + won_amt
        assert chk.version == 2
        assert sav.version == 2

        # Projection integrity is 100% valid
        assert verify_projections_integrity(verify_db) is True
    finally:
        verify_db.close()
        engine.dispose()


