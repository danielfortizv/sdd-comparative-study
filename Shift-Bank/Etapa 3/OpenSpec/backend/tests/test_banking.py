import sys
import tempfile
import threading
import unittest
import os
import base64
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import database
import banking


def parse_iso(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class BankingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        database.DB_PATH = Path(self.tmp.name) / "isolated.sqlite3"
        self._old_keys = os.environ.get("SHIFT_BANK_ENCRYPTION_KEYS")
        self._old_active = os.environ.get("SHIFT_BANK_ACTIVE_KEY_VERSION")
        self._old_audit = os.environ.get("SHIFT_BANK_AUDIT_KEY")
        os.environ["SHIFT_BANK_ENCRYPTION_KEYS"] = '{"test-v1":"' + base64.b64encode(b"t" * 32).decode() + '"}'
        os.environ["SHIFT_BANK_ACTIVE_KEY_VERSION"] = "test-v1"
        os.environ["SHIFT_BANK_AUDIT_KEY"] = base64.b64encode(b"u" * 32).decode()
        database.init_db()
        self.base = datetime(2026, 11, 16, 12, tzinfo=timezone.utc)

    def tearDown(self):
        self.tmp.cleanup()
        if self._old_keys is None: os.environ.pop("SHIFT_BANK_ENCRYPTION_KEYS", None)
        else: os.environ["SHIFT_BANK_ENCRYPTION_KEYS"] = self._old_keys
        if self._old_active is None: os.environ.pop("SHIFT_BANK_ACTIVE_KEY_VERSION", None)
        else: os.environ["SHIFT_BANK_ACTIVE_KEY_VERSION"] = self._old_active
        if self._old_audit is None: os.environ.pop("SHIFT_BANK_AUDIT_KEY", None)
        else: os.environ["SHIFT_BANK_AUDIT_KEY"] = self._old_audit

    def account(self, ident):
        conn = database.get_db_connection()
        try: return Decimal(conn.execute("SELECT balance FROM accounts WHERE id=?", (ident,)).fetchone()[0])
        finally: conn.close()

    def test_repeatable_migration_preserves_rows_and_settings(self):
        banking.save_limits("4000000", "9000000", self.base)
        banking.create_internal({"source_account_id":"acc_checking","destination_account_id":"acc_savings","amount":"100"},self.base)
        before=(self.account("acc_checking"),self.account("acc_savings"))
        database.init_db(); database.init_db()
        self.assertEqual(before,(self.account("acc_checking"),self.account("acc_savings")))
        self.assertEqual("4000000.00",banking.get_limits()["per_transfer"])
        conn=database.get_db_connection()
        try: self.assertEqual(3,conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0])
        finally: conn.close()

    def test_stage1_database_migrates_without_reseeding_or_losing_history(self):
        conn=database.get_db_connection()
        try:
            conn.execute("DROP TABLE transfer_limits")
            conn.execute("DROP TABLE beneficiaries")
            conn.execute("DROP TABLE ach_transfers")
            conn.execute("DROP TABLE recurring_occurrences")
            conn.execute("DROP TABLE recurring_schedules")
            conn.execute("ALTER TABLE transactions RENAME TO stage2_transactions")
            conn.execute("CREATE TABLE transactions(id TEXT PRIMARY KEY,source_account_id TEXT NOT NULL,source_account_name TEXT NOT NULL,destination_account_id TEXT NOT NULL,destination_account_name TEXT NOT NULL,amount TEXT NOT NULL,timestamp TEXT NOT NULL,status TEXT NOT NULL)")
            conn.execute("INSERT INTO transactions SELECT id,source_account_id,source_account_name,destination_account_id,destination_account_name,amount,timestamp,status FROM stage2_transactions")
            conn.execute("DROP TABLE stage2_transactions")
            conn.execute("UPDATE accounts SET balance='4321000.00' WHERE id='acc_checking'")
        finally: conn.close()
        database.init_db()
        conn=database.get_db_connection()
        try:
            self.assertEqual("4321000.00",conn.execute("SELECT balance FROM accounts WHERE id='acc_checking'").fetchone()[0])
            self.assertEqual(2,conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0])
            self.assertIsNotNone(conn.execute("SELECT completed_at FROM transactions LIMIT 1").fetchone())
        finally: conn.close()

    def test_invalid_limit_update_preserves_saved_values_and_reduction_is_immediate(self):
        banking.save_limits("1000000","3000000",self.base)
        for bad in ("0", "-1", "1.001", "not money"):
            with self.assertRaises(banking.BankingError): banking.save_limits(bad,"4000000",self.base)
            self.assertEqual("1000000.00",banking.get_limits()["per_transfer"])
        banking.create_internal({"source_account_id":"acc_checking","destination_account_id":"acc_savings","amount":"500000"},self.base)
        banking.save_limits("1000000","100000",self.base+timedelta(seconds=1))
        with self.assertRaisesRegex(banking.BankingError,"daily limit"):
            banking.create_internal({"source_account_id":"acc_checking","destination_account_id":"acc_savings","amount":"1"},self.base+timedelta(seconds=2))
        self.assertEqual(Decimal("4500000"),self.account("acc_checking"))

    def test_amount_precision_and_limits_boundaries(self):
        for bad in ("0", "-1", "abc", "1.001", "NaN"):
            with self.subTest(bad=bad), self.assertRaises(banking.BankingError): banking.amount(bad)
        self.assertEqual("0.50",banking.money(banking.amount(".5")))
        banking.save_limits("5000000", "5000000",self.base)
        banking.create_internal({"source_account_id":"acc_checking","destination_account_id":"acc_savings","amount":"5000000.00"},self.base)
        conn=database.get_db_connection()
        try: pending=conn.execute("SELECT id FROM transactions WHERE status='PENDING_MFA'").fetchone()[0]
        finally: conn.close()
        banking.confirm_internal(pending,"123456",self.base+timedelta(seconds=1))
        conn=database.get_db_connection()
        try: self.assertEqual(Decimal("5000000.00"),banking.daily_usage(conn,self.base+timedelta(seconds=2)))
        finally: conn.close()
        self.assertEqual(Decimal("0.00"),self.account("acc_checking"))

    def test_internal_transfer_counts_once_and_mfa_revalidates(self):
        banking.save_limits("6000000","6000000",self.base)
        pending=banking.create_internal({"source_account_id":"acc_checking","destination_account_id":"acc_savings","amount":"1500000"},self.base)
        self.assertEqual("PENDING_MFA",pending["status"])
        self.assertEqual(Decimal("5000000"),self.account("acc_checking"))
        banking.save_limits("1400000","6000000",self.base+timedelta(seconds=30))
        with self.assertRaisesRegex(banking.BankingError,"per-transfer"):
            banking.confirm_internal(pending["transfer_id"],"123456",self.base+timedelta(seconds=31))
        banking.save_limits("6000000","6000000",self.base+timedelta(seconds=32))
        self.assertEqual("COMPLETED",banking.confirm_internal(pending["transfer_id"],"123456",self.base+timedelta(seconds=33))["status"])
        conn=database.get_db_connection()
        try: self.assertEqual(Decimal("1500000.00"),banking.daily_usage(conn,self.base+timedelta(seconds=34)))
        finally: conn.close()

    def test_internal_transfer_conserves_total_balance(self):
        before = self.account("acc_checking") + self.account("acc_savings")
        banking.create_internal({"source_account_id":"acc_checking","destination_account_id":"acc_savings","amount":"250000.25"},self.base)
        after = self.account("acc_checking") + self.account("acc_savings")
        self.assertEqual(before, after)
        self.assertEqual(Decimal("4749999.75"), self.account("acc_checking"))
        self.assertEqual(Decimal("15250000.25"), self.account("acc_savings"))

    def test_insufficient_funds_isolated_from_transfer_limit(self):
        banking.save_limits("6000000","10000000",self.base)
        with self.assertRaisesRegex(banking.BankingError,"Insufficient funds"):
            banking.create_internal({"source_account_id":"acc_checking","destination_account_id":"acc_savings","amount":"6000000"},self.base)
        self.assertEqual(Decimal("5000000"),self.account("acc_checking"))
        self.assertEqual(Decimal("15000000"),self.account("acc_savings"))

    def test_ach_insufficient_funds_rejects_before_acceptance(self):
        banking.save_limits("6000000","10000000",self.base)
        with self.assertRaisesRegex(banking.BankingError,"Insufficient funds"):
            banking.submit_ach({"source_account_id":"acc_checking","amount":"6000000","name":"X","bank_name":"Y","routing_number":"123456789","account_number":"4567"},self.base)
        self.assertEqual(Decimal("5000000"),self.account("acc_checking"))
        conn=database.get_db_connection()
        try: self.assertEqual(0,conn.execute("SELECT COUNT(*) FROM ach_transfers").fetchone()[0])
        finally: conn.close()

    def valid_recipient(self):
        return {"name":"A Beneficiary","bank_name":"Demo Bank","routing_number":"123456789","account_number":"1234"}

    def test_beneficiary_validation_and_snapshot(self):
        data=self.valid_recipient(); saved=banking.beneficiary_create(data,self.base)
        with self.assertRaisesRegex(banking.BankingError,"(?i)routing"):
            banking.beneficiary_update(saved["id"],{**data,"routing_number":"12345678x"},self.base)
        for account in ("123", "123456789012345678", "12x4"):
            with self.subTest(account=account), self.assertRaisesRegex(banking.BankingError,"Account number"):
                banking.beneficiary_update(saved["id"],{**data,"account_number":account},self.base)
        result=banking.submit_ach({"source_account_id":"acc_checking","beneficiary_id":saved["id"],"amount":"100","save_recipient":False},self.base)
        banking.beneficiary_update(saved["id"],{**data,"name":"Changed"},self.base)
        banking.beneficiary_delete(saved["id"])
        conn=database.get_db_connection()
        try:
            stored=conn.execute("SELECT recipient_name,routing_number,account_number FROM ach_transfers WHERE id=?",(result["transfer_id"],)).fetchone()
            self.assertTrue(stored["recipient_name"].startswith("sbenc:v1:"))
            self.assertTrue(stored["routing_number"].startswith("sbenc:v1:"))
            self.assertTrue(stored["account_number"].startswith("sbenc:v1:"))
        finally: conn.close()
        self.assertEqual("A Beneficiary",next(item for item in banking.all_history() if item["transfer_id"]==result["transfer_id"])["recipient_name"])

    def test_ach_pending_settlement_failure_once_and_midnight_usage(self):
        banking.save_limits("5000000","10000000",self.base)
        before_midnight=datetime(2026,11,16,23,59,40,tzinfo=timezone.utc)
        accepted=banking.submit_ach({"source_account_id":"acc_checking","amount":"250000","name":"X","bank_name":"Y","routing_number":"123456789","account_number":"4567"},before_midnight)
        aid=accepted["transfer_id"]
        self.assertEqual(Decimal("4750000"),self.account("acc_checking"))
        conn=database.get_db_connection()
        try: self.assertEqual(Decimal("250000"),banking.daily_usage(conn,before_midnight))
        finally: conn.close()
        after=datetime(2026,11,17,0,0,15,tzinfo=timezone.utc)
        self.assertEqual("failed",banking.process_ach(after,{aid})[0]["status"])
        self.assertEqual([],banking.process_ach(after,{aid}))
        self.assertEqual(Decimal("5000000"),self.account("acc_checking"))
        conn=database.get_db_connection()
        try:
            self.assertEqual(Decimal("0"),banking.daily_usage(conn,before_midnight))
            self.assertEqual(Decimal("0"),banking.daily_usage(conn,after))
            row=conn.execute("SELECT status,failure_code,refund_applied FROM ach_transfers WHERE id=?",(aid,)).fetchone()
            self.assertEqual(("failed",banking.FAILURE_CODE,1),tuple(row))
        finally: conn.close()

    def test_sensitive_ach_no_debit_until_mfa_then_settles_without_debit(self):
        req={"source_account_id":"acc_checking","amount":"1000000","name":"X","bank_name":"Y","routing_number":"123456789","account_number":"4567"}
        pending=banking.submit_ach(req,self.base)
        self.assertEqual(Decimal("5000000"),self.account("acc_checking"))
        self.assertEqual("pending",banking.confirm_ach(pending["transfer_id"],"123456",self.base+timedelta(seconds=10))["status"])
        after=self.account("acc_checking")
        self.assertEqual([],banking.process_ach(self.base+timedelta(seconds=39)))
        self.assertEqual("settled",banking.process_ach(self.base+timedelta(seconds=40))[0]["status"])
        self.assertEqual(after,self.account("acc_checking"))
        conn=database.get_db_connection()
        try:
            settled=conn.execute("SELECT status,settled_at FROM ach_transfers WHERE id=?",(pending["transfer_id"],)).fetchone()
            self.assertEqual("settled",settled["status"]); self.assertIsNotNone(settled["settled_at"])
        finally: conn.close()
        database.init_db()  # restart-safe state remains settled and is not debited again
        banking.process_ach(self.base+timedelta(seconds=41))
        self.assertEqual(after,self.account("acc_checking"))

    def test_ach_mfa_wrong_code_retry_expiry_and_daily_limit_revalidation(self):
        request={"source_account_id":"acc_checking","amount":"1000000","name":"X","bank_name":"Y","routing_number":"123456789","account_number":"4567"}
        pending=banking.submit_ach(request,self.base)
        with self.assertRaisesRegex(banking.BankingError,"Invalid MFA"):
            banking.confirm_ach(pending["transfer_id"],"000000",self.base+timedelta(seconds=1))
        banking.save_limits("5000000","999999",self.base+timedelta(seconds=2))
        with self.assertRaisesRegex(banking.BankingError,"daily limit"):
            banking.confirm_ach(pending["transfer_id"],"123456",self.base+timedelta(seconds=3))
        self.assertEqual(Decimal("5000000"),self.account("acc_checking"))
        expiry_start=self.base+timedelta(days=1)
        banking.save_limits("5000000","1000000",expiry_start)
        expired=banking.submit_ach(request,expiry_start)
        with self.assertRaisesRegex(banking.BankingError,"expired"):
            banking.confirm_ach(expired["transfer_id"],"123456",expiry_start+timedelta(minutes=5,seconds=1))
        conn=database.get_db_connection()
        try: self.assertEqual("EXPIRED",conn.execute("SELECT status FROM ach_transfers WHERE id=?",(expired["transfer_id"],)).fetchone()[0])
        finally: conn.close()

    def test_abandoned_mfa_records_expire_without_confirmation(self):
        transfer=banking.create_internal({"source_account_id":"acc_checking","destination_account_id":"acc_savings","amount":"1000000"},self.base)
        ach=banking.submit_ach({"source_account_id":"acc_checking","amount":"1000000","name":"X","bank_name":"Y","routing_number":"123456789","account_number":"4567"},self.base)
        schedule=banking.create_schedule({"transfer_type":"internal","source_account_id":"acc_checking","destination_account_id":"acc_savings","amount":"1000000","frequency":"daily"},self.base)
        self.assertEqual(3,banking.expire_pending_mfa(self.base+timedelta(minutes=5,seconds=1)))
        conn=database.get_db_connection()
        try:
            self.assertEqual("EXPIRED",conn.execute("SELECT status FROM transactions WHERE id=?",(transfer["transfer_id"],)).fetchone()[0])
            self.assertEqual("EXPIRED",conn.execute("SELECT status FROM ach_transfers WHERE id=?",(ach["transfer_id"],)).fetchone()[0])
            self.assertEqual("EXPIRED",conn.execute("SELECT status FROM recurring_schedules WHERE id=?",(schedule["schedule_id"],)).fetchone()[0])
        finally: conn.close()

    def test_schedule_anchor_controls_and_rec_d03(self):
        data={"transfer_type":"internal","source_account_id":"acc_checking","destination_account_id":"acc_savings","amount":"100","frequency":"weekly","start_date":"2026-11-18"}
        created=banking.create_schedule(data,self.base)
        self.assertEqual("2026-11-18T00:00:00.000000Z",created["next_execution_at"])
        sch=banking.list_schedules()[0]
        self.assertEqual(7,sch["interval_days"])
        self.assertEqual("paused",banking.control_schedule(created["schedule_id"],"pause",self.base)["status"])
        resumed=banking.control_schedule(created["schedule_id"],"resume",datetime(2026,11,20,tzinfo=timezone.utc))
        self.assertEqual("2026-11-25T00:00:00.000000Z",resumed["next_execution_at"])
        banking.control_schedule(created["schedule_id"],"cancel",self.base)
        with self.assertRaises(banking.BankingError): banking.control_schedule(created["schedule_id"],"resume",self.base)
        sensitive={**data,"amount":"1000000","start_date":"2026-11-17"}
        draft=banking.create_schedule(sensitive,self.base)
        conn=database.get_db_connection()
        try: conn.execute("UPDATE recurring_schedules SET cadence_anchor=? WHERE id=?",(banking.iso(self.base+timedelta(seconds=100)),draft["schedule_id"]))
        finally: conn.close()
        with self.assertRaisesRegex(banking.BankingError,"first execution time has passed"):
            banking.confirm_schedule(draft["schedule_id"],"123456",self.base+timedelta(seconds=101))
        self.assertEqual("EXPIRED",next(s for s in banking.list_schedules() if s["id"]==draft["schedule_id"])["status"])
        self.assertEqual(Decimal("5000000"),self.account("acc_checking"))

    def test_recurring_execution_is_idempotent_and_failed_attempt_advances(self):
        sch=banking.create_schedule({"transfer_type":"internal","source_account_id":"acc_checking","destination_account_id":"acc_savings","amount":"100","frequency":"daily"},self.base)
        due=self.base+timedelta(days=1)
        first=banking.process_schedules(due)
        self.assertEqual(1,len(first)); bal=self.account("acc_checking")
        database.init_db()  # restarting retains the advanced cadence and occurrence
        self.assertEqual([],banking.process_schedules(due))
        self.assertEqual(bal,self.account("acc_checking"))
        self.assertEqual(1,len(banking.list_schedules()[0]["executions"]))

    def test_schedule_frequency_mfa_revalidation_failures_and_restart_skip(self):
        banking.save_limits("2000000","10000000",self.base)
        monthly=banking.create_schedule({"transfer_type":"internal","source_account_id":"acc_checking","destination_account_id":"acc_savings","amount":"100","frequency":"monthly"},self.base)
        self.assertEqual(30,(parse_iso(monthly["next_execution_at"])-self.base).days)
        draft=banking.create_schedule({"transfer_type":"internal","source_account_id":"acc_checking","destination_account_id":"acc_savings","amount":"1500000","frequency":"daily"},self.base)
        banking.save_limits("1000000","10000000",self.base+timedelta(seconds=5))
        with self.assertRaisesRegex(banking.BankingError,"per-transfer"):
            banking.confirm_schedule(draft["schedule_id"],"123456",self.base+timedelta(seconds=6))
        self.assertEqual("PENDING_MFA",next(s for s in banking.list_schedules() if s["id"]==draft["schedule_id"])["status"])
        # Offline recovery skips all due occurrences while retaining the original anchor.
        banking.recover_schedules(self.base+timedelta(days=33))
        monthly_state=next(s for s in banking.list_schedules() if s["id"]==monthly["schedule_id"])
        self.assertEqual(self.base+timedelta(days=60),parse_iso(monthly_state["next_execution_at"]))
        # A valid schedule that fails for insufficient funds advances and has no monetary effect.
        banking.save_limits("5000000","10000000",self.base+timedelta(days=34))
        poor=banking.create_schedule({"transfer_type":"internal","source_account_id":"acc_checking","destination_account_id":"acc_savings","amount":"5000000","frequency":"daily"},self.base)
        banking.confirm_schedule(poor["schedule_id"],"123456",self.base+timedelta(seconds=10))
        conn=database.get_db_connection()
        try: conn.execute("UPDATE accounts SET balance='2000000.00' WHERE id='acc_checking'")
        finally: conn.close()
        before=self.account("acc_checking")
        failed=banking.process_schedules(self.base+timedelta(days=1))
        self.assertTrue(any(r["schedule_id"]==poor["schedule_id"] and r["status"]=="failed" for r in failed))
        self.assertEqual(before,self.account("acc_checking"))
        poor_state=next(s for s in banking.list_schedules() if s["id"]==poor["schedule_id"])
        self.assertEqual("failed",poor_state["executions"][0]["status"])
        self.assertEqual(self.base+timedelta(days=2),parse_iso(poor_state["next_execution_at"]))

    def test_recurring_limit_failure_is_recorded_without_debit(self):
        banking.save_limits("2000000","10000000",self.base)
        schedule=banking.create_schedule({"transfer_type":"internal","source_account_id":"acc_checking","destination_account_id":"acc_savings","amount":"1500000","frequency":"daily"},self.base)
        banking.confirm_schedule(schedule["schedule_id"],"123456",self.base+timedelta(seconds=1))
        banking.save_limits("1000000","10000000",self.base+timedelta(seconds=2))
        before=self.account("acc_checking")
        result=banking.process_schedules(self.base+timedelta(days=1))
        self.assertEqual("failed",result[0]["status"])
        self.assertIn("per-transfer",result[0]["failure_reason"])
        self.assertEqual(before,self.account("acc_checking"))
        conn=database.get_db_connection()
        try: self.assertEqual(Decimal("0"),banking.daily_usage(conn,self.base+timedelta(days=1)))
        finally: conn.close()

    def test_internal_mfa_completion_across_utc_midnight_uses_completion_date(self):
        created=datetime(2026,11,16,23,59,30,tzinfo=timezone.utc)
        pending=banking.create_internal({"source_account_id":"acc_checking","destination_account_id":"acc_savings","amount":"1000000"},created)
        confirmed=datetime(2026,11,17,0,0,10,tzinfo=timezone.utc)
        banking.confirm_internal(pending["transfer_id"],"123456",confirmed)
        conn=database.get_db_connection()
        try:
            self.assertEqual(Decimal("0"),banking.daily_usage(conn,created))
            self.assertEqual(Decimal("1000000"),banking.daily_usage(conn,confirmed))
        finally: conn.close()

    def test_recurring_ach_is_one_history_entry_and_settlement_updates_occurrence(self):
        rec=self.valid_recipient()
        sch=banking.create_schedule({"transfer_type":"ach","source_account_id":"acc_checking","amount":"100","frequency":"daily",**rec},self.base)
        due=self.base+timedelta(days=1)
        processed=banking.process_schedules(due)
        self.assertEqual(1,len(processed))
        conn=database.get_db_connection()
        try:
            aid=conn.execute("SELECT id FROM ach_transfers WHERE occurrence_id IS NOT NULL").fetchone()[0]
            self.assertEqual(1,len([r for r in banking.all_history() if r.get("schedule_id")==sch["schedule_id"]]))
        finally: conn.close()
        banking.process_ach(due+timedelta(seconds=31))
        scheduled=next(s for s in banking.list_schedules() if s["id"]==sch["schedule_id"])
        self.assertEqual("settled",scheduled["executions"][0]["status"])
        self.assertEqual(Decimal("4999900"),self.account("acc_checking"))

    def test_history_filters_include_internal_counterparty_and_external_debit_only(self):
        banking.create_internal({"source_account_id":"acc_savings","destination_account_id":"acc_checking","amount":"100"},self.base)
        banking.submit_ach({"source_account_id":"acc_checking","amount":"100","name":"Outside","bank_name":"Bank","routing_number":"123456789","account_number":"4567"},self.base)
        checking=banking.all_history("acc_checking")
        self.assertTrue(any(item["transfer_type"]=="internal" and item["destination_account_id"]=="acc_checking" for item in checking))
        ach=next(item for item in checking if item["transfer_type"]=="ach")
        self.assertIsNone(ach["destination_account_id"])
        self.assertEqual("Outside",ach["recipient_name"])


    def test_concurrent_ach_requests_cannot_overdraw(self):
        banking.save_limits("5000000","10000000",self.base)
        barrier=threading.Barrier(2); outcomes=[]
        req={"source_account_id":"acc_checking","amount":"700000","name":"X","bank_name":"Y","routing_number":"123456789","account_number":"4567"}
        conn=database.get_db_connection()
        try: conn.execute("UPDATE accounts SET balance='1000000.00' WHERE id='acc_checking'")
        finally: conn.close()
        def send():
            barrier.wait()
            try: outcomes.append(banking.submit_ach(req,self.base)["status"])
            except banking.BankingError: outcomes.append("rejected")
        threads=[threading.Thread(target=send) for _ in range(2)]
        [t.start() for t in threads]; [t.join() for t in threads]
        self.assertCountEqual(["pending","rejected"],outcomes)
        self.assertGreaterEqual(self.account("acc_checking"),Decimal("0"))


if __name__ == "__main__": unittest.main()
