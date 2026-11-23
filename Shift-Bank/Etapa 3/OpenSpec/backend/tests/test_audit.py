import base64
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from datetime import timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import audit
import banking
import database


class AuditTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db = database.DB_PATH
        self.old_env = {name:os.environ.get(name) for name in (
            "SHIFT_BANK_DB","SHIFT_BANK_ENCRYPTION_KEYS","SHIFT_BANK_ACTIVE_KEY_VERSION",
            "SHIFT_BANK_AUDIT_KEY","SHIFT_BANK_AUDIT_ADMIN_TOKEN")}
        database.DB_PATH = Path(self.tmp.name) / "audit-synthetic.sqlite3"
        os.environ["SHIFT_BANK_DB"] = str(database.DB_PATH)
        os.environ["SHIFT_BANK_ENCRYPTION_KEYS"] = json.dumps({"test-v1":base64.b64encode(b"e"*32).decode()})
        os.environ["SHIFT_BANK_ACTIVE_KEY_VERSION"] = "test-v1"
        os.environ["SHIFT_BANK_AUDIT_KEY"] = base64.b64encode(b"u"*32).decode()
        os.environ["SHIFT_BANK_AUDIT_ADMIN_TOKEN"] = "test-only-admin-token-32-bytes-long"
        database.init_db()

    def tearDown(self):
        database.DB_PATH = self.old_db
        self.tmp.cleanup()
        for name, value in self.old_env.items():
            if value is None: os.environ.pop(name, None)
            else: os.environ[name] = value

    def connect(self):
        return database.get_db_connection()

    def test_chain_verifies_and_contains_safe_banking_events(self):
        banking.create_internal({"source_account_id":"acc_checking","destination_account_id":"acc_savings","amount":"100"})
        beneficiary = banking.beneficiary_create({"name":"Safe Recipient","bank_name":"Example Bank","routing_number":"123456789","account_number":"1234"})
        conn = self.connect()
        try:
            result = audit.verify_connection(conn)
            self.assertTrue(result["valid"], result)
            types = [r[0] for r in conn.execute("SELECT event_type FROM audit_entries ORDER BY sequence")]
            self.assertIn("audit_initialized", types)
            self.assertIn("internal_transfer_completed", types)
            self.assertIn("beneficiary_changed", types)
            stored = " ".join(r[0] for r in conn.execute("SELECT metadata_json FROM audit_entries"))
            self.assertNotIn("123456789", stored)
            self.assertNotIn("1234", stored)
            self.assertNotIn("test-only-admin-token", stored)
        finally: conn.close()

    def test_sqlite_triggers_reject_updates_and_deletes_and_verifier_detects_bypass_tampering(self):
        conn = self.connect()
        try:
            with self.assertRaisesRegex(Exception,"append-only"):
                conn.execute("UPDATE audit_entries SET outcome='forged' WHERE sequence=1")
            with self.assertRaisesRegex(Exception,"append-only"):
                conn.execute("DELETE FROM audit_entries WHERE sequence=1")
            conn.execute("DROP TRIGGER audit_entries_no_update")
            conn.execute("UPDATE audit_entries SET outcome='forged' WHERE sequence=1")
            result = audit.verify_connection(conn)
            self.assertFalse(result["valid"])
            self.assertEqual(1,result["first_invalid_sequence"])
            self.assertEqual("event_integrity_mismatch",result["reason"])
        finally: conn.close()

    def test_deletion_or_reordering_is_detected_after_trigger_bypass(self):
        banking.create_internal({"source_account_id":"acc_checking","destination_account_id":"acc_savings","amount":"100"})
        conn = self.connect()
        try:
            conn.execute("DROP TRIGGER audit_entries_no_delete")
            conn.execute("DELETE FROM audit_entries WHERE sequence=2")
            result = audit.verify_connection(conn)
            self.assertFalse(result["valid"])
            self.assertEqual(2,result["first_invalid_sequence"])
        finally: conn.close()

    def test_missing_checkpoint_and_complete_chain_wipe_are_detected_after_bootstrap(self):
        conn = self.connect()
        try:
            conn.execute("DROP TRIGGER audit_state_no_delete")
            conn.execute("DELETE FROM audit_state")
            with self.assertRaisesRegex(audit.AuditIntegrityError, "checkpoint is missing"):
                audit.initialize(conn)
        finally: conn.close()

    def test_inserted_entry_without_key_is_detected(self):
        conn = self.connect()
        try:
            conn.execute("INSERT INTO audit_entries VALUES(2,?,?,?,?,?,?,?,?)",(
                "forged", "forged_event", "2026-01-01T00:00:00Z", "forged", "recorded", "{}", "0"*64, "0"*64))
            result = audit.verify_connection(conn)
            self.assertFalse(result["valid"])
            self.assertEqual(2,result["first_invalid_sequence"])
            self.assertEqual("sequence_or_link_mismatch",result["reason"])
        finally: conn.close()

    def test_reordered_entries_are_detected_after_trigger_bypass(self):
        banking.create_internal({"source_account_id":"acc_checking","destination_account_id":"acc_savings","amount":"100"})
        conn = self.connect()
        try:
            conn.execute("DROP TRIGGER audit_entries_no_update")
            conn.execute("UPDATE audit_entries SET sequence=sequence+100 WHERE sequence=1")
            conn.execute("UPDATE audit_entries SET sequence=sequence-99 WHERE sequence=2")
            conn.execute("UPDATE audit_entries SET sequence=1 WHERE sequence=101")
            result = audit.verify_connection(conn)
            self.assertFalse(result["valid"])
            self.assertEqual(1,result["first_invalid_sequence"])
        finally: conn.close()

    def test_audit_failure_rolls_back_beneficiary_change(self):
        conn=self.connect()
        try:
            conn.execute("CREATE TRIGGER injected_beneficiary_audit_failure BEFORE INSERT ON audit_entries WHEN NEW.event_type='beneficiary_changed' BEGIN SELECT RAISE(ABORT,'injected audit failure'); END")
        finally: conn.close()
        with self.assertRaisesRegex(audit.AuditError,"could not be persisted"):
            banking.beneficiary_create({"name":"Synthetic","bank_name":"Example","routing_number":"123456789","account_number":"1234"})
        conn=self.connect()
        try:
            self.assertEqual(0,conn.execute("SELECT COUNT(*) FROM beneficiaries").fetchone()[0])
            self.assertEqual(1,conn.execute("SELECT COUNT(*) FROM audit_entries").fetchone()[0])
        finally: conn.close()

    def test_invalid_mfa_is_durably_audited_without_authorizing_or_debiting(self):
        pending = banking.create_internal({"source_account_id":"acc_checking","destination_account_id":"acc_savings","amount":"1000000"})
        conn=self.connect()
        try: before = [r[0] for r in conn.execute("SELECT balance FROM accounts ORDER BY id")]
        finally: conn.close()
        with self.assertRaisesRegex(banking.BankingError,"Invalid MFA"):
            banking.confirm_internal(pending["transfer_id"],"999999")
        conn=self.connect()
        try: after = [r[0] for r in conn.execute("SELECT balance FROM accounts ORDER BY id")]
        finally: conn.close()
        conn = self.connect()
        try:
            event = conn.execute("SELECT outcome,metadata_json FROM audit_entries WHERE event_type='mfa_attempt' ORDER BY sequence DESC LIMIT 1").fetchone()
            status = conn.execute("SELECT status FROM transactions WHERE id=?",(pending["transfer_id"],)).fetchone()[0]
        finally: conn.close()
        self.assertEqual(before,after)
        self.assertEqual("PENDING_MFA",status)
        self.assertEqual("rejected",event["outcome"])
        self.assertNotIn("999999",event["metadata_json"])

    def test_audit_insert_failure_rolls_back_internal_transfer_and_limit_usage(self):
        before = banking.get_limits()["daily_usage"]
        conn = self.connect()
        try:
            conn.execute("CREATE TRIGGER injected_audit_failure BEFORE INSERT ON audit_entries WHEN NEW.event_type='internal_transfer_completed' BEGIN SELECT RAISE(ABORT,'injected audit failure'); END")
        finally: conn.close()
        with self.assertRaisesRegex(audit.AuditError,"could not be persisted"):
            banking.create_internal({"source_account_id":"acc_checking","destination_account_id":"acc_savings","amount":"100"})
        conn = self.connect()
        try:
            self.assertEqual("5000000.00",conn.execute("SELECT balance FROM accounts WHERE id='acc_checking'").fetchone()[0])
            self.assertEqual("15000000.00",conn.execute("SELECT balance FROM accounts WHERE id='acc_savings'").fetchone()[0])
            self.assertEqual(2,conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0])
        finally: conn.close()
        self.assertEqual(before,banking.get_limits()["daily_usage"])

    def test_audit_insert_failure_rolls_back_ach_refund_and_settlement_state(self):
        accepted = banking.submit_ach({"source_account_id":"acc_checking","amount":"100","name":"Recipient","bank_name":"Bank","routing_number":"123456789","account_number":"1234"})
        after_debit = "4999900.00"
        conn = self.connect()
        try:
            conn.execute("CREATE TRIGGER injected_refund_audit_failure BEFORE INSERT ON audit_entries WHEN NEW.event_type='ach_transfer_failed_refunded' BEGIN SELECT RAISE(ABORT,'injected audit failure'); END")
        finally: conn.close()
        due = banking.now_utc()+timedelta(seconds=31)
        with self.assertRaisesRegex(audit.AuditError,"could not be persisted"):
            banking.process_ach(due, {accepted["transfer_id"]})
        conn = self.connect()
        try:
            self.assertEqual(after_debit,conn.execute("SELECT balance FROM accounts WHERE id='acc_checking'").fetchone()[0])
            state = conn.execute("SELECT status,refund_applied FROM ach_transfers WHERE id=?",(accepted["transfer_id"],)).fetchone()
            self.assertEqual(("pending",0),(state["status"],state["refund_applied"]))
        finally: conn.close()

    def test_two_connection_wal_reader_sees_old_or_fully_committed_state(self):
        writer = self.connect(); reader = self.connect()
        try:
            reader.execute("BEGIN")
            old_balance = reader.execute("SELECT balance FROM accounts WHERE id='acc_checking'").fetchone()[0]
            old_count = reader.execute("SELECT COUNT(*) FROM audit_entries").fetchone()[0]
            writer.execute("BEGIN IMMEDIATE")
            writer.execute("UPDATE accounts SET balance='4999900.00' WHERE id='acc_checking'")
            audit.append_event(writer,"reader_writer_probe","probe_1","committed",{"source_account_id":"acc_checking"})
            self.assertEqual(old_balance,reader.execute("SELECT balance FROM accounts WHERE id='acc_checking'").fetchone()[0])
            self.assertEqual(old_count,reader.execute("SELECT COUNT(*) FROM audit_entries").fetchone()[0])
            writer.commit()
            self.assertEqual(old_balance,reader.execute("SELECT balance FROM accounts WHERE id='acc_checking'").fetchone()[0])
            reader.commit()
            self.assertEqual("4999900.00",reader.execute("SELECT balance FROM accounts WHERE id='acc_checking'").fetchone()[0])
            self.assertEqual(old_count+1,reader.execute("SELECT COUNT(*) FROM audit_entries").fetchone()[0])
        finally:
            if writer.in_transaction: writer.rollback()
            if reader.in_transaction: reader.rollback()
            writer.close(); reader.close()

    def test_sqlite_writer_wait_is_bounded_and_does_not_mutate_financial_state(self):
        blocker = self.connect(); blocker.execute("BEGIN IMMEDIATE")
        start = time.monotonic()
        try:
            with self.assertRaisesRegex(audit.AuditError,"Database is busy"):
                banking.create_internal({"source_account_id":"acc_checking","destination_account_id":"acc_savings","amount":"100"})
            elapsed = time.monotonic()-start
        finally:
            blocker.rollback(); blocker.close()
        self.assertLess(elapsed,3.0)
        conn=self.connect()
        try:
            self.assertEqual("5000000.00",conn.execute("SELECT balance FROM accounts WHERE id='acc_checking'").fetchone()[0])
            self.assertEqual(2,conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0])
        finally: conn.close()

    def test_four_processes_append_concurrent_transfers_and_restart_verifies_chain(self):
        process_count = 4
        transfer_count = 6
        start_file = Path(self.tmp.name) / "release-workers"
        worker = (
            "import sys,time,pathlib; sys.path.insert(0," + repr(str(Path(__file__).resolve().parents[1])) + "); "
            "import banking; gate=pathlib.Path(" + repr(str(start_file)) + "); "
            "while_not_used=False; "
        )
        # Use a short polling loop in each OS process so all writers start together.
        worker += "\nwhile not gate.exists(): time.sleep(.005)\n"
        worker += "import database\nfor _ in range(" + str(transfer_count) + "):\n conn=database.get_db_connection(); conn.execute(\"SELECT balance FROM accounts\").fetchall(); conn.close(); banking.create_internal({'source_account_id':'acc_checking','destination_account_id':'acc_savings','amount':'100'})\n"
        env = dict(os.environ, SHIFT_BANK_DB=str(database.DB_PATH))
        processes = [subprocess.Popen([sys.executable,"-c",worker],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for _ in range(process_count)]
        start_file.write_text("go",encoding="utf-8")
        failures=[]
        for process in processes:
            stdout,stderr=process.communicate(timeout=30)
            if process.returncode: failures.append((process.returncode,stdout,stderr))
        self.assertEqual([],failures)
        conn=self.connect()
        try:
            result=audit.verify_connection(conn)
            self.assertTrue(result["valid"],result)
            self.assertEqual(1+process_count*transfer_count,result["checked_entries"])
            self.assertEqual("4997600.00",conn.execute("SELECT balance FROM accounts WHERE id='acc_checking'").fetchone()[0])
            self.assertEqual(2+process_count*transfer_count,conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0])
        finally: conn.close()
        verify_script=("import sys,json; sys.path.insert(0,"+repr(str(Path(__file__).resolve().parents[1]))+"); import audit; print(json.dumps(audit.verify_database()))")
        restarted=subprocess.run([sys.executable,"-c",verify_script],env=env,capture_output=True,text=True,check=True,timeout=10)
        self.assertTrue(json.loads(restarted.stdout)["valid"])


if __name__ == "__main__": unittest.main()
