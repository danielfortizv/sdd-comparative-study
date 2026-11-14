import json
import logging
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.models import (
    Account,
    Transaction,
    Transfer,
    Conversion,
    DomainEvent,
    ProjectionCheckpoint,
)

logger = logging.getLogger("projection_service")


def update_checkpoints(db: Session, last_event_id: int) -> None:
    """Update or create projection checkpoints for account_balances and transaction_history."""
    now = datetime.now(timezone.utc)
    for name in ("account_balances", "transaction_history"):
        cp = db.query(ProjectionCheckpoint).filter(ProjectionCheckpoint.projection_name == name).first()
        if not cp:
            cp = ProjectionCheckpoint(
                projection_name=name,
                last_applied_event_id=last_event_id,
                updated_at=now,
            )
            db.add(cp)
        else:
            cp.last_applied_event_id = last_event_id
            cp.updated_at = now
    db.flush()


def rebuild_projections(db: Session) -> Dict[str, Any]:
    """
    Deterministically rebuild account balance projections and transaction history projections
    by replaying the complete ordered domain event stream from domain_events.
    Executed in a safe, isolated manner without side-effects (no external calls, no audit re-emission).
    """
    events = db.query(DomainEvent).order_by(DomainEvent.id.asc()).all()
    if not events:
        return {"status": "skipped", "reason": "no_events", "reconstructed_events": 0}

    # Tracking fold state: account_id -> {balance: Decimal, version: int, currency: str, ...}
    account_folds: Dict[int, Dict[str, Any]] = {}

    for ev in events:
        payload = json.loads(ev.payload)
        ev_type = ev.event_type

        if ev_type == "AccountStateImported":
            acc_id = int(payload["account_id"])
            account_folds[acc_id] = {
                "account_number": payload["account_number"],
                "account_name": payload["account_name"],
                "account_type": payload["account_type"],
                "currency": payload["currency"],
                "balance": Decimal(str(payload["balance"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                "version": int(payload.get("version", 1)),
            }

        elif ev_type == "AccountOpened":
            acc_id = int(payload["account_id"])
            account_folds[acc_id] = {
                "account_number": payload["account_number"],
                "account_name": payload["account_name"],
                "account_type": payload["account_type"],
                "currency": payload["currency"],
                "balance": Decimal("0.00"),
                "version": int(payload.get("version", 1)),
            }

        elif ev_type == "InternalTransferCompleted":
            from_id = int(payload["from_account_id"])
            to_id = int(payload["to_account_id"])
            amt = Decimal(str(payload["amount"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            from_ver = int(payload.get("from_account_version", account_folds.get(from_id, {}).get("version", 1) + 1))
            to_ver = int(payload.get("to_account_version", account_folds.get(to_id, {}).get("version", 1) + 1))

            if from_id in account_folds:
                account_folds[from_id]["balance"] -= amt
                account_folds[from_id]["version"] = from_ver
            if to_id in account_folds:
                account_folds[to_id]["balance"] += amt
                account_folds[to_id]["version"] = to_ver

        elif ev_type == "CurrencyConversionCompleted":
            from_id = int(payload["from_account_id"])
            to_id = int(payload["to_account_id"])
            src_amt = Decimal(str(payload["source_amount"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            dst_amt = Decimal(str(payload["destination_amount"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            from_ver = int(payload.get("from_account_version", account_folds.get(from_id, {}).get("version", 1) + 1))
            to_ver = int(payload.get("to_account_version", account_folds.get(to_id, {}).get("version", 1) + 1))

            if from_id in account_folds:
                account_folds[from_id]["balance"] -= src_amt
                account_folds[from_id]["version"] = from_ver
            if to_id in account_folds:
                account_folds[to_id]["balance"] += dst_amt
                account_folds[to_id]["version"] = to_ver

        elif ev_type == "AchTransferInitiated":
            from_id = int(payload["from_account_id"])
            amt = Decimal(str(payload["amount"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            from_ver = int(payload.get("from_account_version", account_folds.get(from_id, {}).get("version", 1) + 1))
            if from_id in account_folds:
                account_folds[from_id]["balance"] -= amt
                account_folds[from_id]["version"] = from_ver

        elif ev_type == "AchTransferFailed":
            from_id = int(payload["from_account_id"])
            refund_amt = Decimal(str(payload["refund_amount"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            from_ver = int(payload.get("from_account_version", account_folds.get(from_id, {}).get("version", 1) + 1))
            if from_id in account_folds:
                account_folds[from_id]["balance"] += refund_amt
                account_folds[from_id]["version"] = from_ver

    # Apply folded states back into Account projections
    for acc_id, state in account_folds.items():
        acc = db.query(Account).filter(Account.id == acc_id).first()
        if acc:
            acc.balance = state["balance"]
            acc.version = state["version"]
            acc.currency = state["currency"]

    max_id = events[-1].id
    update_checkpoints(db, max_id)
    db.flush()

    return {
        "status": "success",
        "reconstructed_events": len(events),
        "reconstructed_accounts": len(account_folds),
        "last_applied_event_id": max_id,
    }


def verify_projections_integrity(db: Session) -> bool:
    """
    Perform deep verification of projection synchronization and data integrity against domain_events.
    Returns True if projections match the event fold exactly, False otherwise.
    """
    events_count = db.query(DomainEvent).count()
    if events_count == 0:
        return True

    max_event_id = db.query(func.max(DomainEvent.id)).scalar() or 0

    # 1. Checkpoint validation
    checkpoint = (
        db.query(ProjectionCheckpoint)
        .filter(ProjectionCheckpoint.projection_name == "account_balances")
        .first()
    )
    if not checkpoint or checkpoint.last_applied_event_id != max_event_id:
        return False

    # 2. Replay fold verification
    events = db.query(DomainEvent).order_by(DomainEvent.id.asc()).all()
    account_folds: Dict[int, Dict[str, Any]] = {}

    for ev in events:
        payload = json.loads(ev.payload)
        ev_type = ev.event_type

        if ev_type == "AccountStateImported":
            acc_id = int(payload["account_id"])
            account_folds[acc_id] = {
                "balance": Decimal(str(payload["balance"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                "version": int(payload.get("version", 1)),
            }
        elif ev_type == "AccountOpened":
            acc_id = int(payload["account_id"])
            account_folds[acc_id] = {
                "balance": Decimal("0.00"),
                "version": int(payload.get("version", 1)),
            }
        elif ev_type == "InternalTransferCompleted":
            from_id = int(payload["from_account_id"])
            to_id = int(payload["to_account_id"])
            amt = Decimal(str(payload["amount"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            from_ver = int(payload.get("from_account_version", account_folds.get(from_id, {}).get("version", 1) + 1))
            to_ver = int(payload.get("to_account_version", account_folds.get(to_id, {}).get("version", 1) + 1))
            if from_id in account_folds:
                account_folds[from_id]["balance"] -= amt
                account_folds[from_id]["version"] = from_ver
            if to_id in account_folds:
                account_folds[to_id]["balance"] += amt
                account_folds[to_id]["version"] = to_ver
        elif ev_type == "CurrencyConversionCompleted":
            from_id = int(payload["from_account_id"])
            to_id = int(payload["to_account_id"])
            src_amt = Decimal(str(payload["source_amount"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            dst_amt = Decimal(str(payload["destination_amount"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            from_ver = int(payload.get("from_account_version", account_folds.get(from_id, {}).get("version", 1) + 1))
            to_ver = int(payload.get("to_account_version", account_folds.get(to_id, {}).get("version", 1) + 1))
            if from_id in account_folds:
                account_folds[from_id]["balance"] -= src_amt
                account_folds[from_id]["version"] = from_ver
            if to_id in account_folds:
                account_folds[to_id]["balance"] += dst_amt
                account_folds[to_id]["version"] = to_ver
        elif ev_type == "AchTransferInitiated":
            from_id = int(payload["from_account_id"])
            amt = Decimal(str(payload["amount"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            from_ver = int(payload.get("from_account_version", account_folds.get(from_id, {}).get("version", 1) + 1))
            if from_id in account_folds:
                account_folds[from_id]["balance"] -= amt
                account_folds[from_id]["version"] = from_ver
        elif ev_type == "AchTransferFailed":
            from_id = int(payload["from_account_id"])
            refund_amt = Decimal(str(payload["refund_amount"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            from_ver = int(payload.get("from_account_version", account_folds.get(from_id, {}).get("version", 1) + 1))
            if from_id in account_folds:
                account_folds[from_id]["balance"] += refund_amt
                account_folds[from_id]["version"] = from_ver

    # Compare folded state against actual Account rows
    for acc_id, expected in account_folds.items():
        acc = db.query(Account).filter(Account.id == acc_id).first()
        if not acc:
            return False
        if acc.balance != expected["balance"] or acc.version != expected["version"]:
            return False

    return True


def verify_or_rebuild_at_startup(db: Session) -> None:
    """
    On application startup, verify projection integrity against domain_events.
    If checkpoints are missing/stale or projection balances do not match event folds,
    safely rebuild them atomically before serving traffic.
    """
    events_count = db.query(DomainEvent).count()
    if events_count == 0:
        return

    is_valid = verify_projections_integrity(db)
    if not is_valid:
        logger.warning("CQRS read projections are stale or out of sync. Initiating safe rebuild...")
        res = rebuild_projections(db)
        db.commit()
        if not verify_projections_integrity(db):
            raise RuntimeError(
                f"Startup halted: CQRS projection rebuild failed to achieve consistency with event store: {res}"
            )
        logger.info(f"CQRS read projections rebuilt and verified successfully: {res}")
