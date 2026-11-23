import base64
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import database
from encryption import EncryptionError, decrypt_value, encrypt_value, migrate_sensitive_data
import banking


def encoded_key(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


class EncryptionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db = database.DB_PATH
        self.old_keys = os.environ.get("SHIFT_BANK_ENCRYPTION_KEYS")
        self.old_active = os.environ.get("SHIFT_BANK_ACTIVE_KEY_VERSION")
        self.old_audit = os.environ.get("SHIFT_BANK_AUDIT_KEY")
        self.old_https = os.environ.get("SHIFT_BANK_TRUSTED_PROXY_IPS")
        database.DB_PATH = Path(self.tmp.name) / "synthetic.sqlite3"
        os.environ["SHIFT_BANK_ENCRYPTION_KEYS"] = json.dumps({"v1": encoded_key(b"1"*32), "v2": encoded_key(b"2"*32)})
        os.environ["SHIFT_BANK_ACTIVE_KEY_VERSION"] = "v1"
        os.environ["SHIFT_BANK_AUDIT_KEY"] = encoded_key(b"u"*32)
        database.init_db()

    def tearDown(self):
        database.DB_PATH = self.old_db
        self.tmp.cleanup()
        self._restore("SHIFT_BANK_ENCRYPTION_KEYS", self.old_keys)
        self._restore("SHIFT_BANK_ACTIVE_KEY_VERSION", self.old_active)
        self._restore("SHIFT_BANK_AUDIT_KEY", self.old_audit)
        self._restore("SHIFT_BANK_TRUSTED_PROXY_IPS", self.old_https)

    @staticmethod
    def _restore(name, value):
        if value is None: os.environ.pop(name, None)
        else: os.environ[name] = value

    def test_authenticated_encryption_round_trip(self):
        cipher = encrypt_value("123456789", "beneficiaries", "ben_test", "routing_number")
        self.assertTrue(cipher.startswith("sbenc:v1:v1:"))
        self.assertNotIn("123456789", cipher)
        self.assertEqual("123456789", decrypt_value(cipher, "beneficiaries", "ben_test", "routing_number"))

    def test_ciphertext_tampering_and_record_binding_are_rejected(self):
        cipher = encrypt_value("123456789", "beneficiaries", "ben_test", "routing_number")
        prefix, payload = cipher.rsplit(":", 1)
        raw = bytearray(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        raw[-1] ^= 1
        changed = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
        with self.assertRaisesRegex(EncryptionError, "integrity verification"):
            decrypt_value(prefix + ":" + changed, "beneficiaries", "ben_test", "routing_number")
        with self.assertRaisesRegex(EncryptionError, "integrity verification"):
            decrypt_value(cipher, "beneficiaries", "ben_other", "routing_number")

    def test_missing_invalid_and_obsolete_key_versions_fail_closed(self):
        cipher = encrypt_value("123456789", "beneficiaries", "ben_test", "routing_number")
        os.environ.pop("SHIFT_BANK_ENCRYPTION_KEYS")
        with self.assertRaisesRegex(EncryptionError, "unavailable"):
            encrypt_value("123456789", "beneficiaries", "ben_test", "routing_number")
        os.environ["SHIFT_BANK_ENCRYPTION_KEYS"] = "not-json"
        with self.assertRaisesRegex(EncryptionError, "configuration is invalid"):
            encrypt_value("123456789", "beneficiaries", "ben_test", "routing_number")
        os.environ["SHIFT_BANK_ENCRYPTION_KEYS"] = json.dumps({"v2": encoded_key(b"2"*32)})
        os.environ["SHIFT_BANK_ACTIVE_KEY_VERSION"] = "v2"
        with self.assertRaisesRegex(EncryptionError, "version is unavailable"):
            decrypt_value(cipher, "beneficiaries", "ben_test", "routing_number")

    def test_plaintext_is_never_accepted_by_decryption(self):
        with self.assertRaisesRegex(EncryptionError, "migration is required"):
            decrypt_value("123456789", "beneficiaries", "ben_test", "routing_number")

    def test_rotation_writes_with_active_version_and_retains_old_key_reads(self):
        old_cipher = encrypt_value("123456789", "beneficiaries", "ben_test", "routing_number")
        os.environ["SHIFT_BANK_ACTIVE_KEY_VERSION"] = "v2"
        new_cipher = encrypt_value("987654321", "beneficiaries", "ben_test", "routing_number")
        self.assertIn(":v2:", new_cipher)
        self.assertEqual("123456789", decrypt_value(old_cipher, "beneficiaries", "ben_test", "routing_number"))
        self.assertEqual("987654321", decrypt_value(new_cipher, "beneficiaries", "ben_test", "routing_number"))

    def test_startup_migration_reencrypts_old_version_before_old_key_removal(self):
        beneficiary = banking.beneficiary_create({"name":"N", "bank_name":"B", "routing_number":"123456789", "account_number":"00001234"})
        os.environ["SHIFT_BANK_ACTIVE_KEY_VERSION"] = "v2"
        conn = database.get_db_connection()
        try:
            migrated = migrate_sensitive_data(conn)
            stored = conn.execute("SELECT routing_number FROM beneficiaries WHERE id=?", (beneficiary["id"],)).fetchone()[0]
            self.assertGreater(migrated, 0)
            self.assertIn(":v2:", stored)
        finally: conn.close()
        os.environ["SHIFT_BANK_ENCRYPTION_KEYS"] = json.dumps({"v2": encoded_key(b"2"*32)})
        self.assertEqual("123456789", banking.beneficiaries()[0]["routing_number"])

    def test_legacy_migration_encrypts_records_and_is_idempotent(self):
        conn = database.get_db_connection()
        try:
            conn.execute("INSERT INTO beneficiaries VALUES(?,?,?,?,?,?,?,?)", ("ben_legacy", "usr_101", "Legacy", "Example Bank", "123456789", "00001234", "2026-01-01", "2026-01-01"))
        finally: conn.close()
        ach = banking.submit_ach({"source_account_id":"acc_checking", "amount":"100", "name":"ACH Legacy", "bank_name":"Legacy Bank", "routing_number":"987654321", "account_number":"00005678"})
        schedule = banking.create_schedule({"transfer_type":"ach", "source_account_id":"acc_checking", "amount":"100", "frequency":"daily", "name":"Schedule Legacy", "bank_name":"Legacy Bank", "routing_number":"111222333", "account_number":"00009012"})
        conn = database.get_db_connection()
        try:
            for table, record_id, values in (
                ("ach_transfers", ach["transfer_id"], {"recipient_name":"ACH Legacy", "bank_name":"Legacy Bank", "routing_number":"987654321", "account_number":"00005678"}),
                ("recurring_schedules", schedule["schedule_id"], {"recipient_name":"Schedule Legacy", "bank_name":"Legacy Bank", "routing_number":"111222333", "account_number":"00009012"}),
            ):
                for field, value in values.items():
                    conn.execute(f"UPDATE {table} SET {field}=? WHERE id=?", (value, record_id))
            first = migrate_sensitive_data(conn)
            second = migrate_sensitive_data(conn)
            row = conn.execute("SELECT * FROM beneficiaries WHERE id='ben_legacy'").fetchone()
            self.assertEqual(12, first)
            self.assertEqual(0, second)
            self.assertTrue(row["account_number"].startswith("sbenc:v1:"))
            self.assertEqual("00001234", banking.beneficiaries()[0]["account_number"])
            self.assertEqual("00005678", banking.ach_history()[0]["account_number"])
            self.assertEqual("00009012", banking.list_schedules()[0]["account_number"])
        finally: conn.close()

    def test_migration_failure_rolls_back_every_row(self):
        conn = database.get_db_connection()
        try:
            conn.execute("DELETE FROM schema_migrations WHERE version='sensitive-banking-data-v1'")
            conn.execute("INSERT INTO beneficiaries VALUES(?,?,?,?,?,?,?,?)", ("ben_a", "usr_101", "A", "Bank", "123456789", "1234", "2026-01-01", "2026-01-01"))
            conn.execute("INSERT INTO beneficiaries VALUES(?,?,?,?,?,?,?,?)", ("ben_b", "usr_101", "B", "Bank", "sbenc:v99:broken", "5678", "2026-01-01", "2026-01-01"))
            with self.assertRaisesRegex(EncryptionError, "Unsupported"):
                migrate_sensitive_data(conn)
            self.assertEqual("123456789", conn.execute("SELECT routing_number FROM beneficiaries WHERE id='ben_a'").fetchone()[0])
            self.assertIsNone(conn.execute("SELECT 1 FROM schema_migrations WHERE version='sensitive-banking-data-v1'").fetchone())
        finally: conn.close()

    def test_migration_without_key_rolls_back_and_does_not_emit_plaintext(self):
        conn = database.get_db_connection()
        try:
            conn.execute("INSERT INTO beneficiaries VALUES(?,?,?,?,?,?,?,?)", ("ben_a", "usr_101", "A", "Bank", "123456789", "1234", "2026-01-01", "2026-01-01"))
            os.environ.pop("SHIFT_BANK_ENCRYPTION_KEYS")
            with self.assertRaisesRegex(EncryptionError, "unavailable"):
                migrate_sensitive_data(conn)
            self.assertEqual("123456789", conn.execute("SELECT routing_number FROM beneficiaries WHERE id='ben_a'").fetchone()[0])
        finally: conn.close()

    def test_restart_reopens_encrypted_records_with_external_key(self):
        created = banking.beneficiary_create({"name":"N", "bank_name":"B", "routing_number":"123456789", "account_number":"00001234"})
        env = dict(os.environ, SHIFT_BANK_DB=str(database.DB_PATH))
        script = "import sys; sys.path.insert(0, r'" + str(Path(__file__).resolve().parents[1]) + "'); import database,banking; database.init_db(); print(banking.beneficiaries()[0]['account_number'])"
        reopened = subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, text=True, check=True)
        self.assertEqual("00001234", reopened.stdout.strip())
        self.assertEqual(created["id"], banking.beneficiaries()[0]["id"])

    def test_new_ach_and_schedule_records_are_encrypted_and_readable(self):
        beneficiary = banking.beneficiary_create({"name":"N", "bank_name":"B", "routing_number":"123456789", "account_number":"00001234"})
        result = banking.submit_ach({"source_account_id":"acc_checking", "amount":"100", "beneficiary_id":beneficiary["id"]})
        schedule = banking.create_schedule({"transfer_type":"ach", "source_account_id":"acc_checking", "amount":"100", "frequency":"daily", "beneficiary_id":beneficiary["id"]})
        conn = database.get_db_connection()
        try:
            ach = conn.execute("SELECT account_number FROM ach_transfers WHERE id=?", (result["transfer_id"],)).fetchone()[0]
            sch = conn.execute("SELECT account_number FROM recurring_schedules WHERE id=?", (schedule["schedule_id"],)).fetchone()[0]
            self.assertTrue(ach.startswith("sbenc:v1:")); self.assertTrue(sch.startswith("sbenc:v1:"))
        finally: conn.close()
        self.assertEqual("00001234", banking.ach_history()[0]["account_number"])
        self.assertEqual("00001234", banking.list_schedules()[0]["account_number"])

    def test_obsolete_or_corrupted_persisted_record_blocks_startup(self):
        conn = database.get_db_connection()
        try:
            conn.execute("INSERT INTO beneficiaries VALUES(?,?,?,?,?,?,?,?)", ("ben_a", "usr_101", "A", "Bank", "sbenc:v99:broken", "1234", "2026-01-01", "2026-01-01"))
        finally: conn.close()
        with self.assertRaisesRegex(EncryptionError, "Unsupported"):
            database.init_db()


if __name__ == "__main__": unittest.main()
