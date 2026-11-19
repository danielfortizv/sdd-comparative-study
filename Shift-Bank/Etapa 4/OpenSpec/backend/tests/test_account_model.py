"""Currency-aware account identity tests on isolated SQLite databases."""
import base64
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import account_model
import banking
import database
import main


class AccountModelTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_db_path = database.DB_PATH
        database.DB_PATH = Path(self.temp_dir.name) / "isolated-accounts.sqlite3"
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

    def test_supported_currency_validation_is_exact(self):
        for currency in ("USD", "EUR", "GBP"):
            with self.subTest(currency=currency):
                self.assertEqual(currency, account_model.validate_currency(currency))
        for currency in ("COP", "usd", "", None, 1):
            with self.subTest(currency=currency), self.assertRaises(account_model.AccountCurrencyError):
                account_model.validate_currency(currency)

    def test_schema_persists_canonical_references_without_assigning_currency(self):
        conn = database.get_db_connection()
        try:
            rows = conn.execute(
                "SELECT id,balance,currency,public_reference,migration_state FROM accounts ORDER BY id"
            ).fetchall()
            self.assertEqual(2, len(rows))
            accounts = {row["id"]: dict(row) for row in rows}
            self.assertEqual("CHK-1001", accounts["acc_checking"]["public_reference"])
            self.assertEqual("SAV-2001", accounts["acc_savings"]["public_reference"])
            for account in accounts.values():
                self.assertIsNone(account["currency"])
                self.assertEqual("legacy_unmigrated", account["migration_state"])
            self.assertEqual("5000000.00", accounts["acc_checking"]["balance"])
            self.assertEqual("15000000.00", accounts["acc_savings"]["balance"])
            self.assertEqual(
                ("acc_checking", "CHK-1001"),
                tuple(account_model.resolve_account_reference(conn, "CHK-1001")[key] for key in ("id", "public_reference")),
            )
            self.assertEqual(
                "acc_checking", account_model.resolve_account_reference(conn, "acc_checking")["id"]
            )
            history = conn.execute("SELECT id,amount,source_account_id,destination_account_id FROM transactions ORDER BY id").fetchall()
            self.assertEqual(2, len(history))
            self.assertEqual({"tx_seed_1", "tx_seed_2"}, {row["id"] for row in history})
        finally:
            conn.close()

        api_accounts = {row["id"]: row for row in main.get_accounts()}
        self.assertEqual("CHK-1001", api_accounts["acc_checking"]["public_reference"])
        self.assertEqual("SAV-2001", api_accounts["acc_savings"]["public_reference"])
        self.assertIsNone(api_accounts["acc_checking"]["currency"])
        self.assertEqual("legacy_unmigrated", api_accounts["acc_checking"]["migration_state"])

    def test_canonical_ids_work_for_transfers_and_history_without_changing_stored_ids(self):
        result = banking.create_internal(
            {
                "source_account_id": "CHK-1001",
                "destination_account_id": "SAV-2001",
                "amount": "25.00",
            }
        )
        self.assertEqual("acc_checking", result["source_account_id"])
        self.assertEqual("acc_savings", result["destination_account_id"])
        history = banking.all_history("CHK-1001")
        self.assertEqual(3, len(history))
        self.assertTrue(any(item["transaction_id"] == result["id"] for item in history))

        conn = database.get_db_connection()
        try:
            stored = conn.execute(
                "SELECT source_account_id,destination_account_id FROM transactions WHERE id=?",
                (result["id"],),
            ).fetchone()
            self.assertEqual(("acc_checking", "acc_savings"), tuple(stored))
        finally:
            conn.close()

    def test_legacy_and_canonical_aliases_cannot_bypass_self_transfer_check(self):
        with self.assertRaisesRegex(banking.BankingError, "different"):
            banking.create_internal(
                {
                    "source_account_id": "acc_checking",
                    "destination_account_id": "CHK-1001",
                    "amount": "1.00",
                }
            )
        conn = database.get_db_connection()
        try:
            self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM transactions WHERE id NOT IN ('tx_seed_1','tx_seed_2')").fetchone()[0])
            self.assertEqual("5000000.00", conn.execute("SELECT balance FROM accounts WHERE id='acc_checking'").fetchone()[0])
        finally:
            conn.close()

    def test_repeat_initialization_preserves_currency_state_and_legacy_history(self):
        conn = database.get_db_connection()
        try:
            before_accounts = [tuple(row) for row in conn.execute(
                "SELECT id,balance,currency,public_reference,migration_state FROM accounts ORDER BY id"
            )]
            before_history = [tuple(row) for row in conn.execute(
                "SELECT id,source_account_id,destination_account_id,amount,timestamp,status FROM transactions ORDER BY id"
            )]
        finally:
            conn.close()

        database.init_db()
        conn = database.get_db_connection()
        try:
            after_accounts = [tuple(row) for row in conn.execute(
                "SELECT id,balance,currency,public_reference,migration_state FROM accounts ORDER BY id"
            )]
            after_history = [tuple(row) for row in conn.execute(
                "SELECT id,source_account_id,destination_account_id,amount,timestamp,status FROM transactions ORDER BY id"
            )]
            self.assertEqual(before_accounts, after_accounts)
            self.assertEqual(before_history, after_history)
        finally:
            conn.close()

    def test_unmigrated_or_ambiguous_account_states_fail_closed_for_stage4_currency_use(self):
        conn = database.get_db_connection()
        try:
            row = account_model.resolve_account_reference(conn, "acc_checking")
            with self.assertRaisesRegex(account_model.AccountCurrencyError, "migration is not complete"):
                account_model.require_spendable_currency(row)
            with self.assertRaisesRegex(sqlite3.IntegrityError, "CHECK constraint failed"):
                conn.execute("UPDATE accounts SET currency='COP' WHERE id='acc_checking'")

            conn.execute(
                "INSERT INTO accounts (id,name,balance) VALUES(?,?,?)",
                ("CHK-1001", "Conflicting identity", "0.00"),
            )
            with self.assertRaisesRegex(account_model.AccountModelError, "ambiguous"):
                account_model.resolve_account_reference(conn, "CHK-1001")
        finally:
            conn.close()

    def test_existing_legacy_schema_upgrade_preserves_balances_and_transaction_rows(self):
        old_path = Path(self.temp_dir.name) / "pre-stage4.sqlite3"
        old_conn = sqlite3.connect(str(old_path))
        old_conn.execute("CREATE TABLE accounts (id TEXT PRIMARY KEY,name TEXT NOT NULL,balance TEXT NOT NULL)")
        old_conn.executemany(
            "INSERT INTO accounts VALUES(?,?,?)",
            [("acc_checking", "Checking", "4321000.25"), ("acc_savings", "Savings", "16789000.75")],
        )
        old_conn.execute(
            """CREATE TABLE transactions (
                id TEXT PRIMARY KEY,source_account_id TEXT NOT NULL,source_account_name TEXT NOT NULL,
                destination_account_id TEXT NOT NULL,destination_account_name TEXT NOT NULL,
                amount TEXT NOT NULL,timestamp TEXT NOT NULL,status TEXT NOT NULL)"""
        )
        old_conn.execute(
            "INSERT INTO transactions VALUES(?,?,?,?,?,?,?,?)",
            ("legacy_tx", "acc_savings", "Savings", "acc_checking", "Checking", "12.34", "2026-01-01T00:00:00Z", "COMPLETED"),
        )
        old_conn.commit()
        old_conn.close()

        database.DB_PATH = old_path
        database.init_db()
        conn = database.get_db_connection()
        try:
            self.assertEqual(
                [("acc_checking", "4321000.25", "CHK-1001", None), ("acc_savings", "16789000.75", "SAV-2001", None)],
                [tuple(row) for row in conn.execute(
                    "SELECT id,balance,public_reference,currency FROM accounts ORDER BY id"
                )],
            )
            self.assertEqual(
                ("legacy_tx", "acc_savings", "acc_checking", "12.34"),
                tuple(conn.execute("SELECT id,source_account_id,destination_account_id,amount FROM transactions WHERE id='legacy_tx'").fetchone()),
            )
        finally:
            conn.close()

    def test_reference_conflict_rolls_back_schema_evolution(self):
        conflict_path = Path(self.temp_dir.name) / "conflicting-account-schema.sqlite3"
        conn = sqlite3.connect(str(conflict_path), isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute(
            "CREATE TABLE accounts (id TEXT PRIMARY KEY,name TEXT NOT NULL,balance TEXT NOT NULL,public_reference TEXT)"
        )
        conn.execute(
            "INSERT INTO accounts VALUES(?,?,?,?)",
            ("acc_checking", "Checking", "5000000.00", "WRONG-REFERENCE"),
        )
        with self.assertRaisesRegex(account_model.AccountModelError, "Conflicting public reference"):
            account_model.initialize_account_identity(conn)
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(accounts)")}
        self.assertEqual({"id", "name", "balance", "public_reference"}, columns)
        self.assertEqual(
            "5000000.00",
            conn.execute("SELECT balance FROM accounts WHERE id='acc_checking'").fetchone()[0],
        )
        self.assertEqual(
            0,
            conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name='idx_accounts_public_reference'"
            ).fetchone()[0],
        )
        conn.close()


if __name__ == "__main__":
    unittest.main()
