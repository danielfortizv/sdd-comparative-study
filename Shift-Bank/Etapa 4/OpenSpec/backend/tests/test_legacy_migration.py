"""Atomic synthetic COP/USD migration tests using isolated temporary SQLite files."""
import json
import sys
import unittest
from datetime import timezone
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import audit
import legacy_migration
from migration_preflight_fixtures import TemporaryMigrationDatabase


class LegacyMigrationTest(unittest.TestCase):
    def setUp(self):
        self.fixture = TemporaryMigrationDatabase()
        self.fixture.__enter__()

    def tearDown(self):
        self.fixture.__exit__(None, None, None)

    def migrate(self, **kwargs):
        conn = self.fixture.connect()
        try:
            return legacy_migration.migrate_legacy_state(
                conn, checked_at=self.fixture.CHECKED_AT, **kwargs
            )
        finally:
            conn.close()

    @staticmethod
    def table_snapshot(conn):
        names = [row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )]
        result = {}
        for table in names:
            columns = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
            if table == "audit_state":
                order = "singleton"
            elif table == "domain_events":
                order = "event_sequence"
            elif table == "audit_entries":
                order = "sequence"
            else:
                order = columns[0] if columns else "rowid"
            result[table] = tuple(tuple(row) for row in conn.execute(f"SELECT * FROM {table} ORDER BY {order}"))
        return result

    def test_initial_snapshot_converts_accounts_limits_and_history_once(self):
        conn = self.fixture.connect()
        old_audit = tuple(tuple(row) for row in conn.execute("SELECT * FROM audit_entries ORDER BY sequence"))
        old_transactions = tuple(tuple(row) for row in conn.execute("SELECT * FROM transactions ORDER BY id"))
        conn.close()

        result = self.migrate()
        self.assertEqual("migrated", result["status"])
        self.assertEqual({"acc_checking": "1250.00", "acc_savings": "3750.00"}, result["accounts"])
        self.assertEqual({"usr_101": {"per_transfer": "1250.00", "daily": "2500.00"}}, result["limits"])
        self.assertEqual(2, result["history_records_preserved"])
        self.assertEqual(4, result["domain_events_added"])

        conn = self.fixture.connect()
        try:
            accounts = {r["id"]: dict(r) for r in conn.execute("SELECT * FROM accounts ORDER BY id")}
            self.assertEqual(("1250.00", "USD", "CHK-1001", "active", 0),
                             tuple(accounts["acc_checking"][k] for k in ("balance", "currency", "public_reference", "migration_state", "account_version")))
            self.assertEqual(("3750.00", "USD", "SAV-2001", "active", 0),
                             tuple(accounts["acc_savings"][k] for k in ("balance", "currency", "public_reference", "migration_state", "account_version")))
            self.assertEqual(("0.00", "EUR", "EUR-3001"), tuple(accounts["EUR-3001"][k] for k in ("balance", "currency", "public_reference")))
            self.assertEqual(("0.00", "GBP", "GBP-4001"), tuple(accounts["GBP-4001"][k] for k in ("balance", "currency", "public_reference")))
            self.assertEqual(old_transactions, tuple(tuple(row) for row in conn.execute("SELECT * FROM transactions ORDER BY id")))
            self.assertEqual(2, conn.execute("SELECT COUNT(*) FROM migration_history_provenance WHERE posting_effect='non_posting'").fetchone()[0])
            events = conn.execute("SELECT operation_id,event_type,currency,amount_minor_units,payload_json FROM domain_events ORDER BY event_sequence").fetchall()
            self.assertEqual(4, len(events))
            self.assertEqual({"migration_opening_snapshot"}, {r["event_type"] for r in events})
            self.assertEqual({"USD", "EUR", "GBP"}, {r["currency"] for r in events})
            self.assertFalse(any("tx_seed" in r["operation_id"] for r in events))
            self.assertEqual(old_audit, tuple(tuple(row) for row in conn.execute("SELECT * FROM audit_entries WHERE sequence<=? ORDER BY sequence", (len(old_audit),))))
            self.assertTrue(audit.verify_connection(conn)["valid"])
            conversions = conn.execute("SELECT entity_type,entity_id,setting,source_amount,rounded_usd,effective_usd,residual_cents_numerator,residual_cents_denominator FROM migration_conversions ORDER BY entity_type,entity_id,setting").fetchall()
            checking = next(r for r in conversions if r["entity_id"] == "acc_checking")
            self.assertEqual(("5000000.00", "1250.00", "1250.00", "0", "1"), tuple(checking[k] for k in ("source_amount", "rounded_usd", "effective_usd", "residual_cents_numerator", "residual_cents_denominator")))
        finally:
            conn.close()

    def test_repeat_is_noop_and_conflicting_identity_or_snapshot_rejects(self):
        first = self.migrate()
        conn = self.fixture.connect()
        before = self.table_snapshot(conn)
        conn.close()
        repeated = self.migrate(migration_id=first["migration_id"], expected_source_fingerprint=first["source_fingerprint"])
        self.assertEqual("already_migrated", repeated["status"])
        conn = self.fixture.connect()
        self.assertEqual(before, self.table_snapshot(conn))
        conn.close()
        with self.assertRaises(legacy_migration.LegacyMigrationError) as error:
            self.migrate(migration_id="mig_conflict")
        self.assertEqual("migration_identity_conflict", error.exception.code)
        with self.assertRaises(legacy_migration.LegacyMigrationError) as error:
            self.migrate(expected_source_fingerprint="0" * 64)
        self.assertEqual("source_snapshot_conflict", error.exception.code)

    def test_preflight_rejection_leaves_all_tables_and_financial_rows_unchanged(self):
        self.fixture.add_pending_ach()
        conn = self.fixture.connect()
        before = self.table_snapshot(conn)
        conn.close()
        with self.assertRaises(legacy_migration.LegacyMigrationError) as error:
            self.migrate()
        self.assertIn("preflight_rejected:pending_ach", error.exception.code)
        conn = self.fixture.connect()
        self.assertEqual(before, self.table_snapshot(conn))
        self.assertNotIn("migration_batches", legacy_migration._tables(conn))
        conn.close()

    def test_all_migration_preflight_blockers_abort_without_writes(self):
        blockers = (
            ("pending_mfa", lambda f, c: f.add_pending_mfa("internal")),
            ("active_schedule", lambda f, c: f.add_schedule("active")),
            ("paused_schedule", lambda f, c: f.add_schedule("paused")),
            ("current_day_usage", lambda f, c: f.add_current_day_transfer()),
            ("ambiguous_identity", lambda f, c: c.execute("UPDATE accounts SET public_reference='WRONG-REF' WHERE id='acc_checking'")),
            ("unreconcilable_balance", lambda f, c: c.execute("UPDATE accounts SET balance='invalid' WHERE id='acc_checking'")),
            ("unreconcilable_limit", lambda f, c: c.execute("UPDATE transfer_limits SET daily='invalid' WHERE user_id='usr_101'")),
            ("invalid_audit", lambda f, c: c.execute("UPDATE audit_state SET head_hash=? WHERE singleton=1", ("0" * 64,))),
        )
        for label, prepare in blockers:
            with self.subTest(blocker=label), TemporaryMigrationDatabase() as fixture:
                conn = fixture.connect()
                try:
                    prepare(fixture, conn)
                    before = self.table_snapshot(conn)
                    with self.assertRaises(legacy_migration.LegacyMigrationError):
                        legacy_migration.migrate_legacy_state(conn, checked_at=fixture.CHECKED_AT)
                    self.assertEqual(before, self.table_snapshot(conn))
                    self.assertNotIn("migration_batches", legacy_migration._tables(conn))
                finally:
                    if conn.in_transaction:
                        conn.rollback()
                    conn.close()

    def test_interruption_before_commit_rolls_back_accounts_limits_events_audit_and_provenance(self):
        conn = self.fixture.connect()
        before = self.table_snapshot(conn)

        def interrupt(_conn):
            raise RuntimeError("synthetic interruption")

        with self.assertRaises(legacy_migration.LegacyMigrationError) as error:
            legacy_migration.migrate_legacy_state(conn, checked_at=self.fixture.CHECKED_AT, before_commit=interrupt)
        self.assertEqual("migration_write_or_verification_failed", error.exception.code)
        self.assertFalse(conn.in_transaction)
        self.assertEqual(before, self.table_snapshot(conn))
        conn.close()

    def test_failed_reconciliation_rolls_back_every_write(self):
        conn = self.fixture.connect()
        before = self.table_snapshot(conn)
        original = legacy_migration._verify_reconciliation
        legacy_migration._verify_reconciliation = lambda _conversions: False
        try:
            with self.assertRaises(legacy_migration.LegacyMigrationError) as error:
                legacy_migration.migrate_legacy_state(conn, checked_at=self.fixture.CHECKED_AT)
        finally:
            legacy_migration._verify_reconciliation = original
        self.assertEqual("reconciliation_failed", error.exception.code)
        self.assertEqual(before, self.table_snapshot(conn))
        conn.close()

    def test_half_up_residual_minimum_and_ceiling_rules_are_exact(self):
        half_up = legacy_migration._convert("20.00", "tie")
        self.assertEqual(Fraction(1, 2), half_up["exact_cents"])
        self.assertEqual(1, half_up["rounded_cents"])
        self.assertEqual(Fraction(-1, 2), half_up["residual_cents"])

        minimum = legacy_migration._convert("20.00", "minimum", ceiling_cents=500_000)
        self.assertEqual(1, minimum["effective_cents"])
        with self.assertRaises(legacy_migration.LegacyMigrationError) as error:
            legacy_migration._convert("19.99", "below-minimum", ceiling_cents=500_000)
        self.assertEqual("converted_limit_below_minimum", error.exception.code)

        capped = legacy_migration._convert("25000000.00", "cap", ceiling_cents=500_000)
        self.assertEqual(625_000, capped["rounded_cents"])
        self.assertEqual(500_000, capped["effective_cents"])
        self.assertEqual(125_000, capped["cap_adjustment_cents"])

    def test_limit_cap_and_below_minimum_abort_without_mutation(self):
        conn = self.fixture.connect()
        conn.execute("UPDATE transfer_limits SET per_transfer='25000000.00' WHERE user_id='usr_101'")
        conn.close()
        result = self.migrate()
        self.assertEqual("5000.00", result["limits"]["usr_101"]["per_transfer"])
        conn = self.fixture.connect()
        adjustment = conn.execute("SELECT cap_adjustment_usd FROM migration_conversions WHERE setting='per_transfer'").fetchone()[0]
        self.assertEqual("1250.00", adjustment)
        conn.close()

        with TemporaryMigrationDatabase() as fixture:
            conn = fixture.connect()
            conn.execute("UPDATE transfer_limits SET per_transfer='19.99' WHERE user_id='usr_101'")
            before = self.table_snapshot(conn)
            with self.assertRaises(legacy_migration.LegacyMigrationError) as error:
                legacy_migration.migrate_legacy_state(conn, checked_at=fixture.CHECKED_AT)
            self.assertEqual("converted_limit_below_minimum", error.exception.code)
            self.assertEqual(before, self.table_snapshot(conn))
            conn.close()

    def test_actual_source_balances_and_per_user_limit_tie_values_are_converted(self):
        conn = self.fixture.connect()
        conn.execute("UPDATE accounts SET balance='6000000.00' WHERE id='acc_checking'")
        conn.execute(
            "INSERT INTO transfer_limits(user_id,per_transfer,daily,updated_at) VALUES(?,?,?,?)",
            ("usr_202", "20.00", "20.00", "2026-11-16T00:00:00Z"),
        )
        conn.close()

        result = self.migrate()
        self.assertEqual("1500.00", result["accounts"]["acc_checking"])
        self.assertEqual({"per_transfer": "0.01", "daily": "0.01"}, result["limits"]["usr_202"])
        conn = self.fixture.connect()
        try:
            residuals = conn.execute(
                "SELECT setting,residual_cents_numerator,residual_cents_denominator "
                "FROM migration_conversions WHERE entity_type='limit' AND entity_id='usr_202' ORDER BY setting"
            ).fetchall()
            self.assertEqual([("daily", "-1", "2"), ("per_transfer", "-1", "2")],
                             [(r["setting"], r["residual_cents_numerator"], r["residual_cents_denominator"]) for r in residuals])
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
