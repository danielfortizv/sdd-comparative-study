import logging
from typing import Optional
from decimal import Decimal, ROUND_HALF_UP
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.services.crypto_service import encrypt_at_rest, decrypt_at_rest

logger = logging.getLogger("migration_service")


class MigrationResult(BaseModel):
    success: bool
    migrated_records: int
    skipped_records: int
    verified_records: int
    error_message: Optional[str] = None


class MigrationVerificationError(RuntimeError):
    """Raised when post-migration data integrity verification fails."""
    pass


def run_migration(db: Session) -> MigrationResult:
    """Explicitly, idempotently, and atomically migrate existing sensitive records in the Stage 3 SQLite database.

    Inspects beneficiaries, transfers, and recurring_schedules.
    Records already containing the 'enc:v1:' prefix are skipped.
    Legacy plaintext records are encrypted at rest with AES-256-GCM.
    Runs a 100% verification pass before committing.
    Rolls back atomically on any failure without data loss.
    """
    migrated_count = 0
    skipped_count = 0
    verified_count = 0

    try:
        # We perform migration within an atomic transaction block
        # 1. Beneficiaries
        ben_rows = db.execute(
            text("SELECT id, routing_number, account_number FROM beneficiaries")
        ).fetchall()

        for row in ben_rows:
            ben_id, routing, account = row[0], row[1], row[2]
            needs_update = False
            new_routing = routing
            new_account = account

            if routing and not routing.startswith("enc:v1:"):
                new_routing = encrypt_at_rest(routing)
                needs_update = True
                migrated_count += 1
            elif routing:
                skipped_count += 1

            if account and not account.startswith("enc:v1:"):
                new_account = encrypt_at_rest(account)
                needs_update = True
                migrated_count += 1
            elif account:
                skipped_count += 1

            if needs_update:
                db.execute(
                    text(
                        "UPDATE beneficiaries SET routing_number = :r, account_number = :a WHERE id = :id"
                    ),
                    {"r": new_routing, "a": new_account, "id": ben_id},
                )

        # 2. Transfers
        tx_rows = db.execute(
            text("SELECT id, routing_number, account_number FROM transfers WHERE transfer_type = 'ach'")
        ).fetchall()

        for row in tx_rows:
            tx_id, routing, account = row[0], row[1], row[2]
            needs_update = False
            new_routing = routing
            new_account = account

            if routing and not routing.startswith("enc:v1:"):
                new_routing = encrypt_at_rest(routing)
                needs_update = True
                migrated_count += 1
            elif routing:
                skipped_count += 1

            if account and not account.startswith("enc:v1:"):
                new_account = encrypt_at_rest(account)
                needs_update = True
                migrated_count += 1
            elif account:
                skipped_count += 1

            if needs_update:
                db.execute(
                    text(
                        "UPDATE transfers SET routing_number = :r, account_number = :a WHERE id = :id"
                    ),
                    {"r": new_routing, "a": new_account, "id": tx_id},
                )

        # 3. Recurring Schedules
        sched_rows = db.execute(
            text("SELECT id, routing_number, account_number FROM recurring_schedules WHERE transfer_type = 'ach'")
        ).fetchall()

        for row in sched_rows:
            sched_id, routing, account = row[0], row[1], row[2]
            needs_update = False
            new_routing = routing
            new_account = account

            if routing and not routing.startswith("enc:v1:"):
                new_routing = encrypt_at_rest(routing)
                needs_update = True
                migrated_count += 1
            elif routing:
                skipped_count += 1

            if account and not account.startswith("enc:v1:"):
                new_account = encrypt_at_rest(account)
                needs_update = True
                migrated_count += 1
            elif account:
                skipped_count += 1

            if needs_update:
                db.execute(
                    text(
                        "UPDATE recurring_schedules SET routing_number = :r, account_number = :a WHERE id = :id"
                    ),
                    {"r": new_routing, "a": new_account, "id": sched_id},
                )

        # 4. Post-Migration Verification Pass
        check_bens = db.execute(
            text("SELECT id, routing_number, account_number FROM beneficiaries")
        ).fetchall()
        for r in check_bens:
            if r[1]:
                if not r[1].startswith("enc:v1:"):
                    raise MigrationVerificationError(f"Beneficiary {r[0]} routing_number not encrypted")
                dec_r = decrypt_at_rest(r[1])
                if dec_r is None or len(dec_r) != 9:
                    raise MigrationVerificationError(f"Beneficiary {r[0]} routing_number invalid or decrypt failed")
                verified_count += 1
            if r[2]:
                if not r[2].startswith("enc:v1:"):
                    raise MigrationVerificationError(f"Beneficiary {r[0]} account_number not encrypted")
                dec_a = decrypt_at_rest(r[2])
                if dec_a is None or len(dec_a) < 4:
                    raise MigrationVerificationError(f"Beneficiary {r[0]} account_number invalid or decrypt failed")
                verified_count += 1

        check_txs = db.execute(
            text("SELECT id, routing_number, account_number FROM transfers WHERE transfer_type = 'ach'")
        ).fetchall()
        for r in check_txs:
            if r[1]:
                if not r[1].startswith("enc:v1:"):
                    raise MigrationVerificationError(f"Transfer {r[0]} routing_number not encrypted")
                dec_r = decrypt_at_rest(r[1])
                if dec_r is None:
                    raise MigrationVerificationError(f"Transfer {r[0]} routing_number decrypt failed")
                verified_count += 1
            if r[2]:
                if not r[2].startswith("enc:v1:"):
                    raise MigrationVerificationError(f"Transfer {r[0]} account_number not encrypted")
                dec_a = decrypt_at_rest(r[2])
                if dec_a is None:
                    raise MigrationVerificationError(f"Transfer {r[0]} account_number decrypt failed")
                verified_count += 1

        check_scheds = db.execute(
            text("SELECT id, routing_number, account_number FROM recurring_schedules WHERE transfer_type = 'ach'")
        ).fetchall()
        for r in check_scheds:
            if r[1]:
                if not r[1].startswith("enc:v1:"):
                    raise MigrationVerificationError(f"Schedule {r[0]} routing_number not encrypted")
                dec_r = decrypt_at_rest(r[1])
                if dec_r is None:
                    raise MigrationVerificationError(f"Schedule {r[0]} routing_number decrypt failed")
                verified_count += 1
            if r[2]:
                if not r[2].startswith("enc:v1:"):
                    raise MigrationVerificationError(f"Schedule {r[0]} account_number not encrypted")
                dec_a = decrypt_at_rest(r[2])
                if dec_a is None:
                    raise MigrationVerificationError(f"Schedule {r[0]} account_number decrypt failed")
                verified_count += 1

        db.commit()
        logger.info(
            f"Encryption migration completed: {migrated_count} migrated, {skipped_count} skipped, {verified_count} verified."
        )
        return MigrationResult(
            success=True,
            migrated_records=migrated_count,
            skipped_records=skipped_count,
            verified_records=verified_count,
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Encryption migration failed: {e}. Atomic rollback executed.")
        return MigrationResult(
            success=False,
            migrated_records=migrated_count,
            skipped_records=skipped_count,
            verified_records=verified_count,
            error_message=str(e),
        )


def run_stage4_event_sourcing_migration(db: Session) -> MigrationResult:
    """
    Perform a one-time, transactional, idempotent migration of Stage 3 account state
    and transaction history into initial domain events.
    1. Reads actual persisted accounts dynamically (no hardcoding).
    2. Emits AccountStateImported for existing accounts.
    3. Provisions EUR and GBP accounts (AccountOpened) with 0.00 if missing.
    4. Emits LegacyTransactionImported for existing transactions without altering balances.
    5. Reconstructs and verifies balances before committing.
    """
    from backend.app.models import Account, Transaction, DomainEvent, ProjectionCheckpoint
    from backend.app.services.event_store import append_domain_event
    from backend.app.services.projection_service import update_checkpoints, verify_projections_integrity

    migrated_count = 0
    skipped_count = 0
    verified_count = 0

    try:
        # Check idempotency: if AccountStateImported events already exist, skip
        existing_import = db.query(DomainEvent).filter(DomainEvent.event_type == "AccountStateImported").first()
        if existing_import:
            accounts = db.query(Account).all()
            return MigrationResult(
                success=True,
                migrated_records=0,
                skipped_records=len(accounts),
                verified_records=len(accounts),
            )

        # 1. Dynamically read existing accounts
        existing_accounts = db.query(Account).order_by(Account.id.asc()).all()
        user_id = 1
        if existing_accounts:
            user_id = existing_accounts[0].user_id

        # Import each existing account as an AccountStateImported event
        for acc in existing_accounts:
            payload = {
                "account_id": acc.id,
                "account_number": acc.account_number,
                "account_name": acc.account_name,
                "account_type": acc.account_type,
                "currency": acc.currency,
                "balance": str(acc.balance),
                "version": acc.version or 1,
            }
            append_domain_event(
                db=db,
                event_type="AccountStateImported",
                aggregate_id=f"banking:{acc.user_id}",
                account_ids=[acc.id],
                payload=payload,
            )
            migrated_count += 1

        # 2. Provision EUR and GBP accounts if missing (D-02)
        eur_acc = db.query(Account).filter(Account.currency == "EUR").first()
        if not eur_acc:
            eur_acc = Account(
                user_id=user_id,
                account_number="EUR-3001",
                account_type="checking",
                account_name="Euro Account",
                balance=Decimal("0.00"),
                currency="EUR",
                version=1,
            )
            db.add(eur_acc)
            db.flush()
            append_domain_event(
                db=db,
                event_type="AccountOpened",
                aggregate_id=f"banking:{user_id}",
                account_ids=[eur_acc.id],
                payload={
                    "account_id": eur_acc.id,
                    "account_number": eur_acc.account_number,
                    "account_name": eur_acc.account_name,
                    "account_type": eur_acc.account_type,
                    "currency": "EUR",
                    "balance": "0.00",
                    "version": 1,
                },
            )
            migrated_count += 1

        gbp_acc = db.query(Account).filter(Account.currency == "GBP").first()
        if not gbp_acc:
            gbp_acc = Account(
                user_id=user_id,
                account_number="GBP-4001",
                account_type="savings",
                account_name="British Pound Account",
                balance=Decimal("0.00"),
                currency="GBP",
                version=1,
            )
            db.add(gbp_acc)
            db.flush()
            append_domain_event(
                db=db,
                event_type="AccountOpened",
                aggregate_id=f"banking:{user_id}",
                account_ids=[gbp_acc.id],
                payload={
                    "account_id": gbp_acc.id,
                    "account_number": gbp_acc.account_number,
                    "account_name": gbp_acc.account_name,
                    "account_type": gbp_acc.account_type,
                    "currency": "GBP",
                    "balance": "0.00",
                    "version": 1,
                },
            )
            migrated_count += 1

        # 3. Capture historical transactions as non-balance-changing LegacyTransactionImported events
        existing_txs = db.query(Transaction).order_by(Transaction.id.asc()).all()
        for tx in existing_txs:
            tx_payload = {
                "transaction_id": tx.id,
                "account_id": tx.account_id,
                "transfer_id": tx.transfer_id,
                "transaction_type": tx.transaction_type,
                "amount": str(tx.amount),
                "balance_after": str(tx.balance_after),
                "description": tx.description,
                "reference": tx.reference,
                "status": tx.status,
                "created_at": tx.created_at.isoformat() if tx.created_at else None,
            }
            append_domain_event(
                db=db,
                event_type="LegacyTransactionImported",
                aggregate_id=f"banking:{user_id}",
                account_ids=[tx.account_id],
                payload=tx_payload,
            )
            migrated_count += 1

        # 4. Initialize Projection Checkpoints
        last_ev = db.query(DomainEvent).order_by(DomainEvent.id.desc()).first()
        if last_ev:
            update_checkpoints(db, last_ev.id)

        # 5. Verification pass: Replay and verify balances match database exactly
        if not verify_projections_integrity(db):
            raise MigrationVerificationError("Stage 4 Event Sourcing migration integrity verification failed")

        db.commit()
        logger.info(f"Stage 4 Event Sourcing migration committed: {migrated_count} events generated and verified.")
        return MigrationResult(
            success=True,
            migrated_records=migrated_count,
            skipped_records=skipped_count,
            verified_records=migrated_count,
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Stage 4 Event Sourcing migration failed: {e}. Atomic rollback executed.")
        return MigrationResult(
            success=False,
            migrated_records=migrated_count,
            skipped_records=skipped_count,
            verified_records=verified_count,
            error_message=str(e),
        )


if __name__ == "__main__":
    from backend.app.database import SessionLocal
    db = SessionLocal()
    try:
        res = run_migration(db)
        print(f"Encryption Migration completed: {res}")
        res4 = run_stage4_event_sourcing_migration(db)
        print(f"Stage 4 Migration completed: {res4}")
    finally:
        db.close()
