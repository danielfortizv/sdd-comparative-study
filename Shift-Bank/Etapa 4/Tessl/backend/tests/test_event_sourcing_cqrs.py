import uuid
import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import text
from backend.app.models import Account, Transaction, DomainEvent, ProjectionCheckpoint
from backend.app.services.migration_service import run_stage4_event_sourcing_migration
from backend.app.services.projection_service import (
    rebuild_projections,
    verify_projections_integrity,
    update_checkpoints,
)


def test_event_store_append_and_immutability(db_session):
    """Domain events must be append-only with SQLite triggers blocking UPDATE and DELETE (D-05)."""
    ev = DomainEvent(
        event_id=str(uuid.uuid4()),
        event_type="TestEvent",
        aggregate_id="banking:1",
        aggregate_version=1,
        account_ids="[1]",
        payload='{"test": true}',
    )
    db_session.add(ev)
    db_session.commit()
    db_session.refresh(ev)
    assert ev.id is not None

    # Attempt direct UPDATE: must raise error from trigger or ORM event listener
    with pytest.raises(Exception):
        ev.event_type = "TamperedEvent"
        db_session.commit()

    db_session.rollback()

    # Attempt direct DELETE: must raise error
    with pytest.raises(Exception):
        db_session.delete(ev)
        db_session.commit()

    db_session.rollback()


def test_migration_and_balance_reconstruction(client: TestClient, db_session):
    """Test dynamic migration generates AccountStateImported and AccountOpened events and verifies balances (D-05)."""
    # Migration was executed at startup by client fixture
    imported_events = (
        db_session.query(DomainEvent)
        .filter(DomainEvent.event_type.in_(["AccountStateImported", "AccountOpened"]))
        .all()
    )
    assert len(imported_events) >= 4  # USD checking, USD savings, EUR, GBP

    # Check that legacy transactions were imported as non-balance-changing events
    legacy_tx_events = (
        db_session.query(DomainEvent)
        .filter(DomainEvent.event_type == "LegacyTransactionImported")
        .all()
    )
    assert len(legacy_tx_events) >= 3

    # Checkpoint exists and is synchronized
    cp = db_session.query(ProjectionCheckpoint).filter(ProjectionCheckpoint.projection_name == "account_balances").first()
    assert cp is not None
    assert cp.last_applied_event_id > 0

    # Migration idempotency: running migration again produces no duplicate accounts or events
    res = run_stage4_event_sourcing_migration(db_session)
    assert res.success is True
    assert res.migrated_records == 0


def test_projection_rebuild_deterministic_replay(client: TestClient, db_session):
    """Deleting read projections and replaying domain events reconstructs exact balances and history (D-06)."""
    accounts_before = {a["id"]: (a["balance"], a["version"]) for a in client.get("/api/accounts").json()}

    # Perform a transfer and conversion to create events
    usd_acc = next(a for a in client.get("/api/accounts").json() if a["currency"] == "USD")
    eur_acc = next(a for a in client.get("/api/accounts").json() if a["currency"] == "EUR")

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

    expected_accounts_post = {a["id"]: (a["balance"], a["version"]) for a in client.get("/api/accounts").json()}

    # Corrupt or zero out account balances directly to simulate projection loss
    for acc in db_session.query(Account).all():
        acc.balance = Decimal("0.00")
        acc.version = 0
    db_session.commit()

    # Verify that projection integrity check detects corruption
    assert verify_projections_integrity(db_session) is False

    # Execute projection rebuild routine
    rebuild_res = rebuild_projections(db_session)
    db_session.commit()
    assert rebuild_res["status"] == "success"
    assert verify_projections_integrity(db_session) is True

    # Reconstructed balances and versions must match post-conversion state exactly
    reconstructed_accounts = {a["id"]: (a["balance"], a["version"]) for a in client.get("/api/accounts").json()}
    assert reconstructed_accounts == expected_accounts_post


def test_projection_checkpoint_stale_detection(client: TestClient, db_session):
    """Stale checkpoint is detected and reported as invalid (D-06)."""
    cp = db_session.query(ProjectionCheckpoint).filter(ProjectionCheckpoint.projection_name == "account_balances").first()
    assert cp is not None
    original_id = cp.last_applied_event_id

    # Artificially set checkpoint back
    cp.last_applied_event_id = 0
    db_session.commit()

    assert verify_projections_integrity(db_session) is False

    # Restore checkpoint
    cp.last_applied_event_id = original_id
    db_session.commit()
    assert verify_projections_integrity(db_session) is True
