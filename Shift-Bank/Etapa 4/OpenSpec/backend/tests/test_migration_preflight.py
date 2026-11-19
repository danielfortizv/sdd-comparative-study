"""Read-only migration preflight behavior against isolated legacy databases."""
import os
import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import event_store
import migration_preflight
from migration_preflight_fixtures import TemporaryMigrationDatabase


class MigrationPreflightTest(unittest.TestCase):
    def setUp(self):
        self.fixture = TemporaryMigrationDatabase()
        self.fixture.__enter__()

    def tearDown(self):
        self.fixture.__exit__(None, None, None)

    def check_read_only(self):
        conn = self.fixture.connect()
        conn.execute("BEGIN IMMEDIATE")
        before = self.fixture.snapshot(conn)
        result = migration_preflight.preflight_migration(conn, self.fixture.CHECKED_AT)
        after = self.fixture.snapshot(conn)
        self.assertEqual(before, after)
        self.assertTrue(conn.in_transaction)
        conn.rollback()
        conn.close()
        return result

    @staticmethod
    def issue(result, code):
        return next((item for item in result.issues if item.code == code), None)

    def test_eligible_legacy_state_is_accepted_and_seed_history_is_not_reposted(self):
        result = self.check_read_only()
        self.assertTrue(result.eligible)
        self.assertEqual((), result.issues)
        conn = self.fixture.connect()
        try:
            self.assertEqual(
                {"tx_seed_1", "tx_seed_2"},
                {row[0] for row in conn.execute("SELECT id FROM transactions")},
            )
            self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM domain_events").fetchone()[0])
        finally:
            conn.close()

    def test_pending_ach_is_rejected_with_only_its_record_id(self):
        record_id = self.fixture.add_pending_ach()
        result = self.check_read_only()
        rejection = self.issue(result, "pending_ach")
        self.assertFalse(result.eligible)
        self.assertIsNotNone(rejection)
        self.assertEqual((record_id,), rejection.record_ids)
        self.assertEqual({"eligible", "checked_at_utc", "issues"}, set(result.as_dict()))

    def test_pending_mfa_in_each_inherited_operation_store_is_rejected(self):
        for operation in ("internal", "ach", "schedule"):
            with self.subTest(operation=operation):
                with TemporaryMigrationDatabase() as fixture:
                    record_id = fixture.add_pending_mfa(operation)
                    conn = fixture.connect()
                    conn.execute("BEGIN IMMEDIATE")
                    before = fixture.snapshot(conn)
                    result = migration_preflight.preflight_migration(conn, fixture.CHECKED_AT)
                    self.assertEqual(before, fixture.snapshot(conn))
                    conn.rollback()
                    conn.close()
                    rejection = self.issue(result, "pending_mfa")
                    self.assertFalse(result.eligible)
                    self.assertIsNotNone(rejection)
                    self.assertIn(record_id, rejection.record_ids)

    def test_active_and_paused_recurring_schedules_are_rejected(self):
        for status, code in (("active", "active_recurring_schedule"), ("paused", "paused_recurring_schedule")):
            with self.subTest(status=status):
                with TemporaryMigrationDatabase() as fixture:
                    schedule_id = fixture.add_schedule(status)
                    conn = fixture.connect()
                    conn.execute("BEGIN IMMEDIATE")
                    before = fixture.snapshot(conn)
                    result = migration_preflight.preflight_migration(conn, fixture.CHECKED_AT)
                    self.assertEqual(before, fixture.snapshot(conn))
                    conn.rollback()
                    conn.close()
                    rejection = self.issue(result, code)
                    self.assertFalse(result.eligible)
                    self.assertIsNotNone(rejection)
                    self.assertEqual((schedule_id,), rejection.record_ids)

    def test_nonzero_current_day_usage_is_rejected_without_changes(self):
        self.fixture.add_current_day_transfer()
        result = self.check_read_only()
        self.assertIsNotNone(self.issue(result, "current_day_limit_usage_nonzero"))
        self.assertFalse(result.eligible)

    def test_currency_or_public_identity_mismatch_is_rejected(self):
        conn = self.fixture.connect()
        conn.execute("UPDATE accounts SET currency='USD' WHERE id='acc_checking'")
        conn.close()
        result = self.check_read_only()
        rejection = self.issue(result, "account_state_ambiguous")
        self.assertFalse(result.eligible)
        self.assertIsNotNone(rejection)
        self.assertIn("acc_checking", rejection.record_ids)

    def test_cross_column_internal_reference_collision_is_rejected(self):
        conn = self.fixture.connect()
        conn.execute(
            "INSERT INTO accounts (id,name,balance,public_reference) VALUES(?,?,?,?)",
            ("unexpected-account", "Synthetic", "0.00", "acc_checking"),
        )
        conn.close()
        result = self.check_read_only()
        self.assertFalse(result.eligible)
        rejection = self.issue(result, "account_state_ambiguous")
        self.assertIsNotNone(rejection)
        self.assertIn("unexpected-account", rejection.record_ids)

    def test_unreconcilable_balance_and_limit_configuration_are_rejected(self):
        for table, statement, code in (
            ("accounts", "UPDATE accounts SET balance='NaN' WHERE id='acc_checking'", "source_balance_unreconcilable"),
            ("transfer_limits", "UPDATE transfer_limits SET per_transfer='invalid' WHERE user_id='usr_101'", "source_configuration_unreconcilable"),
        ):
            with self.subTest(table=table):
                with TemporaryMigrationDatabase() as fixture:
                    conn = fixture.connect()
                    conn.execute(statement)
                    conn.close()
                    result = self.check_read_only_for(fixture)
                    self.assertFalse(result.eligible)
                    self.assertIsNotNone(self.issue(result, code))

    def check_read_only_for(self, fixture):
        conn = fixture.connect()
        conn.execute("BEGIN IMMEDIATE")
        before = fixture.snapshot(conn)
        result = migration_preflight.preflight_migration(conn, fixture.CHECKED_AT)
        self.assertEqual(before, fixture.snapshot(conn))
        conn.rollback()
        conn.close()
        return result

    def test_invalid_audit_chain_fails_closed_without_repair(self):
        conn = self.fixture.connect()
        conn.execute("UPDATE audit_state SET head_hash=? WHERE singleton=1", ("0" * 64,))
        conn.close()
        result = self.check_read_only()
        self.assertFalse(result.eligible)
        self.assertIsNotNone(self.issue(result, "audit_chain_unverifiable"))

    def test_missing_audit_key_fails_closed_without_disclosing_details(self):
        os.environ.pop("SHIFT_BANK_AUDIT_KEY", None)
        result = self.check_read_only()
        rejection = self.issue(result, "audit_chain_unverifiable")
        self.assertFalse(result.eligible)
        self.assertEqual((), rejection.record_ids)
        self.assertNotIn("key", repr(result.as_dict()).lower())

    def test_preflight_repeated_in_one_transaction_is_deterministic(self):
        conn = self.fixture.connect()
        conn.execute("BEGIN IMMEDIATE")
        before = self.fixture.snapshot(conn)
        first = migration_preflight.preflight_migration(conn, self.fixture.CHECKED_AT)
        second = migration_preflight.preflight_migration(conn, self.fixture.CHECKED_AT)
        self.assertEqual(first.as_dict(), second.as_dict())
        self.assertEqual(before, self.fixture.snapshot(conn))
        conn.rollback()
        conn.close()

    def test_changed_invalid_source_snapshot_is_rejected_on_next_preflight(self):
        first = self.check_read_only()
        self.assertTrue(first.eligible)
        conn = self.fixture.connect()
        conn.execute("UPDATE accounts SET balance='not-a-balance' WHERE id='acc_checking'")
        conn.close()
        second = self.check_read_only()
        self.assertFalse(second.eligible)
        self.assertIsNotNone(self.issue(second, "source_balance_unreconcilable"))

    def test_preexisting_domain_event_history_blocks_legacy_cutover(self):
        conn = self.fixture.connect()
        conn.execute("BEGIN IMMEDIATE")
        event_store.append_event(
            conn,
            aggregate_type="account",
            aggregate_id="acc_checking",
            operation_id="synthetic-stage4-op",
            event_type="synthetic_event",
            currency="USD",
            amount_minor_units=1,
            payload={},
        )
        conn.commit()
        conn.close()
        result = self.check_read_only()
        self.assertFalse(result.eligible)
        rejection = self.issue(result, "preexisting_domain_events")
        self.assertEqual(("domain_events",), rejection.record_ids)

    def test_preflight_requires_active_transaction_and_aware_time(self):
        conn = self.fixture.connect()
        result = migration_preflight.preflight_migration(conn, self.fixture.CHECKED_AT)
        self.assertEqual(("transaction_required",), tuple(issue.code for issue in result.issues))
        conn.execute("BEGIN IMMEDIATE")
        invalid_time = migration_preflight.preflight_migration(conn, datetime(2026, 11, 19, 12))
        self.assertEqual(("preflight_time_invalid",), tuple(issue.code for issue in invalid_time.issues))
        conn.rollback()
        conn.close()


if __name__ == "__main__":
    unittest.main()
