"""Atomic synthetic COP-to-USD cutover for isolated Stage 4 databases.

The caller supplies a connection to the database under test. This module never
opens a database itself. A successful cutover uses the existing account,
preflight, event-store, and HMAC-audit infrastructure in one SQLite transaction.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from fractions import Fraction

import account_model
import audit
import event_store
import migration_preflight


RATE_COP_PER_USD = 4000
LIMIT_CEILINGS_CENTS = {"per_transfer": 500_000, "daily": 1_000_000}
_INITIAL_ACCOUNTS = (
    ("acc_checking", "CHK-1001", "Cuenta Corriente"),
    ("acc_savings", "SAV-2001", "Cuenta de Ahorros"),
)
_NEW_ACCOUNTS = (
    ("EUR-3001", "Cuenta EUR", "EUR"),
    ("GBP-4001", "Cuenta GBP", "GBP"),
)


class LegacyMigrationError(ValueError):
    """Safe, structured rejection for a synthetic legacy cutover."""

    def __init__(self, code: str, record_ids: tuple[str, ...] = ()):
        self.code = code
        self.record_ids = tuple(sorted(set(record_ids)))
        super().__init__(code)

    def as_dict(self) -> dict:
        return {"status": "rejected", "reason": self.code, "record_ids": list(self.record_ids)}


def _tables(conn: sqlite3.Connection) -> set[str]:
    return {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _money_to_cents(value: object, record_id: str) -> int:
    if not isinstance(value, str) or not re.fullmatch(r"\d+(?:\.\d{1,2})?", value):
        raise LegacyMigrationError("source_amount_unreconcilable", (record_id,))
    whole, dot, fraction = value.partition(".")
    return int(whole) * 100 + int((fraction + "00")[:2] if dot else "00")


def _cents_to_money(cents: int) -> str:
    return f"{cents // 100}.{cents % 100:02d}"


def _round_half_up(value: Fraction) -> int:
    """Round a non-negative exact value to an integer, with ties away from zero."""
    if value < 0:
        raise LegacyMigrationError("negative_financial_value")
    quotient, remainder = divmod(value.numerator, value.denominator)
    return quotient + (1 if 2 * remainder >= value.denominator else 0)


def _fraction_json(value: Fraction) -> dict[str, str]:
    return {"numerator": str(value.numerator), "denominator": str(value.denominator)}


def _source_rows(conn: sqlite3.Connection) -> dict[str, list[dict]]:
    """Canonical, nonsensitive source snapshot. Recipient credentials are excluded."""
    queries = {
        "accounts": "SELECT id,name,balance,currency,public_reference,migration_state,account_version FROM accounts ORDER BY id",
        "limits": "SELECT user_id,per_transfer,daily,updated_at FROM transfer_limits ORDER BY user_id",
        "transactions": "SELECT id,source_account_id,source_account_name,destination_account_id,destination_account_name,amount,timestamp,status,completed_at,failure_reason,occurrence_id FROM transactions ORDER BY id",
        "ach": "SELECT id,source_account_id,source_account_name,amount,status,created_at,accepted_at,settled_at,failed_at,beneficiary_id,failure_code,failure_reason,refund_applied,occurrence_id FROM ach_transfers ORDER BY id",
        "schedules": "SELECT id,user_id,transfer_type,source_account_id,source_account_name,destination_account_id,destination_account_name,amount,frequency,interval_days,cadence_anchor,next_execution_at,status,created_at,mfa_expires_at,authorized_at FROM recurring_schedules ORDER BY id",
        "occurrences": "SELECT id,schedule_id,scheduled_at,status,attempted_at,transaction_id,ach_transfer_id,failure_reason FROM recurring_occurrences ORDER BY id",
        "audit": "SELECT sequence,event_id,event_type,occurred_at,operation_id,outcome,previous_hash,event_hash FROM audit_entries ORDER BY sequence",
    }
    result: dict[str, list[dict]] = {}
    tables = _tables(conn)
    for name, query in queries.items():
        table = {
            "limits": "transfer_limits",
            "ach": "ach_transfers",
            "schedules": "recurring_schedules",
            "occurrences": "recurring_occurrences",
            "audit": "audit_entries",
        }.get(name, name)
        if table not in tables:
            raise LegacyMigrationError("source_schema_unreconcilable", (table,))
        result[name] = [dict(row) for row in conn.execute(query)]
    state = conn.execute(
        "SELECT singleton,sequence,head_hash,checkpoint_hmac FROM audit_state ORDER BY singleton"
    ).fetchall()
    result["audit_state"] = [dict(row) for row in state]
    return result


def source_fingerprint(conn: sqlite3.Connection) -> str:
    payload = json.dumps(_source_rows(conn), ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _install_migration_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS migration_batches(
            migration_id TEXT PRIMARY KEY,
            source_fingerprint TEXT NOT NULL UNIQUE,
            completed_at TEXT NOT NULL,
            details_json TEXT NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS migration_conversions(
            migration_id TEXT NOT NULL REFERENCES migration_batches(migration_id),
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            setting TEXT NOT NULL,
            source_currency TEXT NOT NULL CHECK(source_currency='COP'),
            source_amount TEXT NOT NULL,
            rate_cop_per_usd INTEGER NOT NULL CHECK(rate_cop_per_usd=4000),
            exact_usd_cents_numerator TEXT NOT NULL,
            exact_usd_cents_denominator TEXT NOT NULL,
            rounded_usd TEXT NOT NULL,
            effective_usd TEXT NOT NULL,
            residual_cents_numerator TEXT NOT NULL,
            residual_cents_denominator TEXT NOT NULL,
            cap_adjustment_usd TEXT NOT NULL,
            PRIMARY KEY(migration_id,entity_type,entity_id,setting)
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS migration_history_provenance(
            migration_id TEXT NOT NULL REFERENCES migration_batches(migration_id),
            source_table TEXT NOT NULL,
            source_record_id TEXT NOT NULL,
            source_currency TEXT NOT NULL CHECK(source_currency='COP'),
            posting_effect TEXT NOT NULL CHECK(posting_effect='non_posting'),
            source_record_json TEXT NOT NULL,
            PRIMARY KEY(migration_id,source_table,source_record_id)
        )"""
    )
    for table in ("migration_batches", "migration_conversions", "migration_history_provenance"):
        conn.execute(
            f"""CREATE TRIGGER IF NOT EXISTS {table}_no_update BEFORE UPDATE ON {table}
                BEGIN SELECT RAISE(ABORT, 'migration provenance is immutable'); END"""
        )
        conn.execute(
            f"""CREATE TRIGGER IF NOT EXISTS {table}_no_delete BEFORE DELETE ON {table}
                BEGIN SELECT RAISE(ABORT, 'migration provenance is immutable'); END"""
        )


def _convert(source_amount: object, record_id: str, *, ceiling_cents: int | None = None) -> dict:
    source_cents = _money_to_cents(source_amount, record_id)
    exact_cents = Fraction(source_cents, RATE_COP_PER_USD)
    rounded_cents = _round_half_up(exact_cents)
    if ceiling_cents is not None and rounded_cents < 1:
        raise LegacyMigrationError("converted_limit_below_minimum", (record_id,))
    effective_cents = min(rounded_cents, ceiling_cents) if ceiling_cents is not None else rounded_cents
    residual = exact_cents - rounded_cents
    cap_adjustment = rounded_cents - effective_cents
    # Prove the rounded conversion equation exactly. A cap is separately recorded.
    if exact_cents != Fraction(rounded_cents, 1) + residual:
        raise LegacyMigrationError("conversion_reconciliation_failed", (record_id,))
    return {
        "source_cents": source_cents,
        "exact_cents": exact_cents,
        "rounded_cents": rounded_cents,
        "effective_cents": effective_cents,
        "residual_cents": residual,
        "cap_adjustment_cents": cap_adjustment,
    }


def _record_conversion(conn: sqlite3.Connection, migration_id: str, entity_type: str,
                       entity_id: str, setting: str, source_amount: object, converted: dict) -> None:
    exact: Fraction = converted["exact_cents"]
    residual: Fraction = converted["residual_cents"]
    conn.execute(
        """INSERT INTO migration_conversions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            migration_id, entity_type, entity_id, setting, "COP",
            _cents_to_money(converted["source_cents"]), RATE_COP_PER_USD,
            str(exact.numerator), str(exact.denominator),
            _cents_to_money(converted["rounded_cents"]),
            _cents_to_money(converted["effective_cents"]),
            str(residual.numerator), str(residual.denominator),
            _cents_to_money(converted["cap_adjustment_cents"]),
        ),
    )


def _record_history(conn: sqlite3.Connection, migration_id: str) -> int:
    count = 0
    for table, query in (
        ("transactions", "SELECT id,source_account_id,destination_account_id,amount,timestamp,status,completed_at,occurrence_id FROM transactions ORDER BY id"),
        ("ach_transfers", "SELECT id,source_account_id,amount,status,created_at,accepted_at,settled_at,failed_at,refund_applied,occurrence_id FROM ach_transfers ORDER BY id"),
        ("recurring_schedules", "SELECT id,transfer_type,source_account_id,destination_account_id,amount,frequency,interval_days,cadence_anchor,next_execution_at,status,created_at,authorized_at FROM recurring_schedules ORDER BY id"),
        ("recurring_occurrences", "SELECT id,schedule_id,scheduled_at,status,attempted_at,transaction_id,ach_transfer_id FROM recurring_occurrences ORDER BY id"),
    ):
        for row in conn.execute(query):
            record_id = str(row["id"])
            payload = json.dumps(dict(row), ensure_ascii=True, sort_keys=True, separators=(",", ":"))
            conn.execute(
                "INSERT INTO migration_history_provenance VALUES(?,?,?,?,?,?)",
                (migration_id, table, record_id, "COP", "non_posting", payload),
            )
            count += 1
    return count


def _verify_reconciliation(conversions: list[dict]) -> bool:
    for item in conversions:
        exact: Fraction = item["exact_cents"]
        residual: Fraction = item["residual_cents"]
        rounded = item["rounded_cents"]
        effective = item["effective_cents"]
        cap_adjustment = item["cap_adjustment_cents"]
        if exact != Fraction(rounded, 1) + residual:
            return False
        if rounded != effective + cap_adjustment:
            return False
    return True


def _event_id(migration_id: str, account_id: str) -> str:
    return "evt_" + hashlib.sha256(f"{migration_id}:{account_id}".encode()).hexdigest()[:32]


def migrate_legacy_state(
    conn: sqlite3.Connection,
    *,
    checked_at: datetime,
    migration_id: str | None = None,
    expected_source_fingerprint: str | None = None,
    before_commit=None,
) -> dict:
    """Migrate a synthetic legacy DB atomically; does not open or select any DB.

    `before_commit` is a test seam for deterministic interruption injection.
    It is never used by production application flow.
    """
    if conn.in_transaction:
        raise LegacyMigrationError("transaction_already_active")
    conn.execute("BEGIN IMMEDIATE")
    try:
        tables = _tables(conn)
        if "migration_batches" in tables:
            batches = conn.execute(
                "SELECT migration_id,source_fingerprint FROM migration_batches ORDER BY completed_at"
            ).fetchall()
            if len(batches) == 1:
                batch = batches[0]
                if expected_source_fingerprint not in (None, batch["source_fingerprint"]):
                    raise LegacyMigrationError("source_snapshot_conflict")
                if migration_id not in (None, batch["migration_id"]):
                    raise LegacyMigrationError("migration_identity_conflict")
                verification = audit.verify_connection(conn)
                if not verification.get("valid"):
                    raise LegacyMigrationError("audit_chain_unverifiable")
                conn.commit()
                return {
                    "status": "already_migrated",
                    "migration_id": batch["migration_id"],
                    "source_fingerprint": batch["source_fingerprint"],
                }
            if batches:
                raise LegacyMigrationError("migration_state_ambiguous")

        preflight = migration_preflight.preflight_migration(conn, checked_at)
        if not preflight.eligible:
            codes = tuple(issue.code for issue in preflight.issues)
            record_ids = tuple(record for issue in preflight.issues for record in issue.record_ids)
            raise LegacyMigrationError("preflight_rejected:" + ",".join(codes), record_ids)

        snapshot_rows = _source_rows(conn)
        fingerprint = hashlib.sha256(
            json.dumps(snapshot_rows, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        deterministic_id = "mig_" + fingerprint
        if expected_source_fingerprint not in (None, fingerprint):
            raise LegacyMigrationError("source_snapshot_conflict")
        if migration_id not in (None, deterministic_id):
            raise LegacyMigrationError("migration_identity_conflict")
        migration_id = deterministic_id

        account_conversions: list[dict] = []
        for internal_id, public_ref, _name in _INITIAL_ACCOUNTS:
            row = conn.execute("SELECT balance FROM accounts WHERE id=?", (internal_id,)).fetchone()
            converted = _convert(row["balance"], internal_id)
            converted.update({"entity_type": "account", "entity_id": internal_id, "setting": "balance", "public_reference": public_ref})
            account_conversions.append(converted)

        limit_conversions: list[dict] = []
        limits = conn.execute("SELECT user_id,per_transfer,daily FROM transfer_limits ORDER BY user_id").fetchall()
        for row in limits:
            for setting in ("per_transfer", "daily"):
                converted = _convert(
                    row[setting], row["user_id"] + ":" + setting,
                    ceiling_cents=LIMIT_CEILINGS_CENTS[setting],
                )
                converted.update({"entity_type": "limit", "entity_id": row["user_id"], "setting": setting})
                limit_conversions.append(converted)

        all_conversions = account_conversions + limit_conversions
        if not _verify_reconciliation(all_conversions):
            raise LegacyMigrationError("reconciliation_failed")

        _install_migration_schema(conn)
        details = {
            "rate_cop_per_usd": RATE_COP_PER_USD,
            "source_fingerprint": fingerprint,
            "account_conversions": [
                {"internal_id": item["entity_id"], "public_reference": item["public_reference"],
                 "source_cop": _cents_to_money(item["source_cents"]),
                 "target_usd": _cents_to_money(item["effective_cents"]),
                 "residual_cents": _fraction_json(item["residual_cents"])}
                for item in account_conversions
            ],
            "history_posting_effect": "non_posting",
        }
        conn.execute(
            "INSERT INTO migration_batches VALUES(?,?,?,?)",
            (migration_id, fingerprint, checked_at.astimezone(timezone.utc).isoformat(),
             json.dumps(details, sort_keys=True, separators=(",", ":"))),
        )

        for item in all_conversions:
            _record_conversion(conn, migration_id, item["entity_type"], item["entity_id"],
                               item["setting"], _cents_to_money(item["source_cents"]), item)

        for item in account_conversions:
            conn.execute(
                """UPDATE accounts SET balance=?,currency='USD',public_reference=?,migration_state='active',account_version=0
                   WHERE id=? AND currency IS NULL AND migration_state='legacy_unmigrated'""",
                (_cents_to_money(item["effective_cents"]), item["public_reference"], item["entity_id"]),
            )
            if conn.execute("SELECT changes()").fetchone()[0] != 1:
                raise LegacyMigrationError("account_state_changed", (item["entity_id"],))

        for account_id, name, currency in _NEW_ACCOUNTS:
            conn.execute(
                """INSERT INTO accounts(id,name,balance,currency,public_reference,migration_state,account_version)
                   VALUES(?,?,?, ?,NULL,'active',0)""",
                (account_id, name, "0.00", currency),
            )
        conn.execute(
            "UPDATE accounts SET public_reference=id WHERE id IN ('EUR-3001','GBP-4001')"
        )

        for item in limit_conversions:
            column = item["setting"]
            conn.execute(
                f"UPDATE transfer_limits SET {column}=?,updated_at=? WHERE user_id=?",
                (_cents_to_money(item["effective_cents"]),
                 checked_at.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z"),
                 item["entity_id"]),
            )

        history_count = _record_history(conn, migration_id)
        event_data = []
        for item in account_conversions:
            event_data.append((item["entity_id"], "USD", item["effective_cents"], item))
        for account_id, _name, currency in _NEW_ACCOUNTS:
            event_data.append((account_id, currency, 0, None))
        for account_id, currency, amount_cents, item in event_data:
            payload = {
                "migration_id": migration_id,
                "boundary": "verified_balance_snapshot",
                "history_posting_effect": "non_posting",
                "source_currency": "COP" if item else None,
                "source_amount": _cents_to_money(item["source_cents"]) if item else "0.00",
                "rate_cop_per_usd": RATE_COP_PER_USD if item else None,
                "rounding_residual_cents": _fraction_json(item["residual_cents"]) if item else {"numerator": "0", "denominator": "1"},
            }
            event_store.append_event(
                conn, aggregate_type="account", aggregate_id=account_id,
                operation_id=migration_id, event_type="migration_opening_snapshot",
                currency=currency, amount_minor_units=amount_cents, payload=payload,
                occurred_at=checked_at, event_id=_event_id(migration_id, account_id),
            )

        if not _verify_reconciliation(all_conversions):
            raise LegacyMigrationError("reconciliation_failed")
        if len(event_data) != 4 or conn.execute(
            "SELECT COUNT(*) FROM domain_events WHERE operation_id=?", (migration_id,)
        ).fetchone()[0] != 4:
            raise LegacyMigrationError("migration_event_reconciliation_failed")
        audit.append_event(
            conn, "legacy_migration_completed", migration_id, "committed",
            {"migration_id": migration_id, "source_fingerprint": fingerprint,
             "converted_accounts": 2, "created_accounts": 2,
             "converted_limit_settings": len(limit_conversions),
             "history_records_preserved": history_count},
            occurred_at=checked_at,
        )
        if not audit.verify_connection(conn).get("valid"):
            raise LegacyMigrationError("audit_chain_unverifiable")
        if before_commit is not None:
            before_commit(conn)
        conn.commit()
        return {
            "status": "migrated",
            "migration_id": migration_id,
            "source_fingerprint": fingerprint,
            "accounts": {item["entity_id"]: _cents_to_money(item["effective_cents"]) for item in account_conversions},
            "limits": {
                item["entity_id"]: {setting["setting"]: _cents_to_money(setting["effective_cents"])
                                    for setting in limit_conversions if setting["entity_id"] == item["entity_id"]}
                for item in limit_conversions
            },
            "history_records_preserved": history_count,
            "domain_events_added": 4,
        }
    except LegacyMigrationError:
        if conn.in_transaction:
            conn.rollback()
        raise
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        # Deliberately suppress raw SQLite/audit exception text and values.
        raise LegacyMigrationError("migration_write_or_verification_failed") from None
