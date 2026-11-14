import logging
from typing import Optional
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
        # Check all beneficiaries
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

        # Check all ACH transfers
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

        # Check all ACH recurring schedules
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

        # Commit atomic migration transaction
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


if __name__ == "__main__":
    from backend.app.database import SessionLocal
    db = SessionLocal()
    try:
        res = run_migration(db)
        print(f"Migration completed: {res}")
    finally:
        db.close()
