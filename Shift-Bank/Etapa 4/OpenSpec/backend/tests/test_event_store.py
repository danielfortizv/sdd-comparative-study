"""Focused Stage 4 domain-event storage tests using a temporary SQLite file."""
import base64
import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import database
import event_store


class DomainEventStoreTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_db_path = database.DB_PATH
        database.DB_PATH = Path(self.temp_dir.name) / "isolated-stage4.sqlite3"
        self.old_env = {
            name: os.environ.get(name)
            for name in (
                "SHIFT_BANK_ENCRYPTION_KEYS",
                "SHIFT_BANK_ACTIVE_KEY_VERSION",
                "SHIFT_BANK_AUDIT_KEY",
            )
        }
        os.environ["SHIFT_BANK_ENCRYPTION_KEYS"] = (
            '{"test-v1":"' + base64.b64encode(b"e" * 32).decode("ascii") + '"}'
        )
        os.environ["SHIFT_BANK_ACTIVE_KEY_VERSION"] = "test-v1"
        os.environ["SHIFT_BANK_AUDIT_KEY"] = base64.b64encode(b"a" * 32).decode("ascii")
        database.init_db()

    def tearDown(self):
        database.DB_PATH = self.old_db_path
        for name, value in self.old_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        self.temp_dir.cleanup()

    def connection(self):
        return database.get_db_connection()

    def append(self, conn, aggregate_id, amount, currency="USD", operation="op-1"):
        return event_store.append_event(
            conn,
            aggregate_type="account",
            aggregate_id=aggregate_id,
            operation_id=operation,
            event_type="balance_posted",
            currency=currency,
            amount_minor_units=amount,
            payload={"side": "debit" if amount < 0 else "credit"},
            occurred_at=datetime(2026, 11, 19, 12, tzinfo=timezone.utc),
        )

    def test_database_initialization_installs_durable_empty_event_store(self):
        conn = self.connection()
        try:
            self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM domain_events").fetchone()[0])
        finally:
            conn.close()

        database.init_db()
        conn = self.connection()
        try:
            self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM domain_events").fetchone()[0])
        finally:
            conn.close()

    def test_compound_account_events_have_global_and_aggregate_order(self):
        conn = self.connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            debit = self.append(conn, "acc_checking", -1234)
            credit = self.append(conn, "acc_savings", 1234)
            conn.commit()
            self.assertEqual((1, 1), (debit["event_sequence"], debit["aggregate_sequence"]))
            self.assertEqual((2, 1), (credit["event_sequence"], credit["aggregate_sequence"]))
            self.assertEqual("USD", debit["currency"])
            self.assertEqual(-1234, debit["amount_minor_units"])

            conn.execute("BEGIN IMMEDIATE")
            later = self.append(conn, "acc_checking", 5, operation="op-2")
            conn.commit()
            self.assertEqual(2, later["aggregate_sequence"])

            events = event_store.list_events(conn)
            self.assertEqual([1, 2, 3], [event["event_sequence"] for event in events])
            self.assertEqual(["acc_checking", "acc_savings", "acc_checking"], [event["aggregate_id"] for event in events])
        finally:
            conn.close()

        conn = self.connection()
        try:
            self.assertEqual(3, len(event_store.list_events(conn)))
        finally:
            conn.close()

    def test_append_requires_transaction_and_rejects_inexact_or_unsupported_values(self):
        conn = self.connection()
        try:
            with self.assertRaisesRegex(event_store.EventStoreError, "active transaction"):
                self.append(conn, "acc_checking", 100)

            conn.execute("BEGIN IMMEDIATE")
            with self.assertRaisesRegex(event_store.EventStoreError, "integer minor units"):
                self.append(conn, "acc_checking", 1.25)
            with self.assertRaisesRegex(event_store.EventStoreError, "integer minor units"):
                self.append(conn, "acc_checking", True)
            with self.assertRaisesRegex(event_store.EventStoreError, "binary floating-point"):
                event_store.append_event(
                    conn,
                    aggregate_type="account",
                    aggregate_id="acc_checking",
                    operation_id="op-float",
                    event_type="balance_posted",
                    currency="USD",
                    amount_minor_units=100,
                    payload={"amount": 1.25},
                )
            with self.assertRaisesRegex(event_store.EventStoreError, "Unsupported event currency"):
                self.append(conn, "acc_checking", 100, currency="COP")
            with self.assertRaisesRegex(event_store.EventStoreError, "either both"):
                event_store.append_event(
                    conn,
                    aggregate_type="account",
                    aggregate_id="acc_checking",
                    operation_id="op-missing-currency",
                    event_type="balance_posted",
                    amount_minor_units=100,
                    payload={},
                )
            with self.assertRaisesRegex(event_store.EventStoreError, "timezone-aware"):
                event_store.append_event(
                    conn,
                    aggregate_type="account",
                    aggregate_id="acc_checking",
                    operation_id="op-naive-time",
                    event_type="balance_posted",
                    currency="USD",
                    amount_minor_units=100,
                    payload={},
                    occurred_at=datetime(2026, 11, 19, 12),
                )
            conn.rollback()
            self.assertEqual([], event_store.list_events(conn))
        finally:
            conn.close()

    def test_events_cannot_be_updated_or_deleted_and_rollback_removes_append(self):
        conn = self.connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            event = self.append(conn, "acc_checking", -1)
            conn.commit()
            with self.assertRaisesRegex(sqlite3.IntegrityError, "append-only"):
                conn.execute("UPDATE domain_events SET amount_minor_units=0 WHERE event_id=?", (event["event_id"],))
            with self.assertRaisesRegex(sqlite3.IntegrityError, "append-only"):
                conn.execute("DELETE FROM domain_events WHERE event_id=?", (event["event_id"],))

            conn.execute("BEGIN IMMEDIATE")
            self.append(conn, "acc_checking", 1, operation="rolled-back")
            conn.rollback()
            stored = event_store.list_events(conn)
            self.assertEqual(1, len(stored))
            self.assertEqual(-1, stored[0]["amount_minor_units"])
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
