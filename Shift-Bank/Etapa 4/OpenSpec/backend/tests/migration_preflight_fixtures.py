"""Reusable, temporary SQLite states for migration-preflight tests."""
import base64
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import banking
import database
import migration_preflight


class TemporaryMigrationDatabase:
    CHECKED_AT = datetime(2026, 11, 19, 12, tzinfo=timezone.utc)

    def __enter__(self):
        self._temporary = tempfile.TemporaryDirectory()
        self._old_db_path = database.DB_PATH
        self._old_environment = {
            name: os.environ.get(name)
            for name in (
                "SHIFT_BANK_ENCRYPTION_KEYS",
                "SHIFT_BANK_ACTIVE_KEY_VERSION",
                "SHIFT_BANK_AUDIT_KEY",
            )
        }
        database.DB_PATH = Path(self._temporary.name) / "isolated-migration.sqlite3"
        os.environ["SHIFT_BANK_ENCRYPTION_KEYS"] = (
            '{"preflight-v1":"' + base64.b64encode(b"e" * 32).decode("ascii") + '"}'
        )
        os.environ["SHIFT_BANK_ACTIVE_KEY_VERSION"] = "preflight-v1"
        os.environ["SHIFT_BANK_AUDIT_KEY"] = base64.b64encode(b"a" * 32).decode("ascii")
        database.init_db()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        database.DB_PATH = self._old_db_path
        for name, value in self._old_environment.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        self._temporary.cleanup()

    def connect(self):
        return database.get_db_connection()

    def begin_preflight(self):
        conn = self.connect()
        conn.execute("BEGIN IMMEDIATE")
        return conn, migration_preflight.preflight_migration(conn, self.CHECKED_AT)

    def add_pending_ach(self):
        return banking.submit_ach(
            {
                "source_account_id": "acc_checking",
                "amount": "25.00",
                "name": "Synthetic Recipient",
                "bank_name": "Synthetic Bank",
                "routing_number": "123456789",
                "account_number": "1234",
            },
            at=self.CHECKED_AT,
        )["transfer_id"]

    def add_pending_mfa(self, operation):
        if operation == "internal":
            return banking.create_internal(
                {
                    "source_account_id": "acc_checking",
                    "destination_account_id": "acc_savings",
                    "amount": "1000000.00",
                },
                at=self.CHECKED_AT,
            )["transfer_id"]
        if operation == "ach":
            return banking.submit_ach(
                {
                    "source_account_id": "acc_checking",
                    "amount": "1000000.00",
                    "name": "Synthetic Recipient",
                    "bank_name": "Synthetic Bank",
                    "routing_number": "123456789",
                    "account_number": "1234",
                },
                at=self.CHECKED_AT,
            )["transfer_id"]
        if operation == "schedule":
            return banking.create_schedule(
                {
                    "transfer_type": "internal",
                    "source_account_id": "acc_checking",
                    "destination_account_id": "acc_savings",
                    "amount": "1000000.00",
                    "frequency": "weekly",
                },
                at=self.CHECKED_AT,
            )["schedule_id"]
        raise ValueError("Unsupported synthetic MFA fixture")

    def add_schedule(self, status):
        result = banking.create_schedule(
            {
                "transfer_type": "internal",
                "source_account_id": "acc_checking",
                "destination_account_id": "acc_savings",
                "amount": "25.00",
                "frequency": "weekly",
            },
            at=self.CHECKED_AT,
        )
        if status == "paused":
            banking.control_schedule(result["schedule_id"], "pause", at=self.CHECKED_AT)
        elif status != "active":
            raise ValueError("Schedule fixture status must be active or paused")
        return result["schedule_id"]

    def add_current_day_transfer(self):
        return banking.create_internal(
            {
                "source_account_id": "acc_checking",
                "destination_account_id": "acc_savings",
                "amount": "25.00",
            },
            at=self.CHECKED_AT,
        )["id"]

    def snapshot(self, conn):
        queries = {
            "accounts": "SELECT id,balance,currency,public_reference,migration_state FROM accounts ORDER BY id",
            "transactions": "SELECT id,source_account_id,destination_account_id,amount,timestamp,status,completed_at FROM transactions ORDER BY id",
            "ach": "SELECT id,source_account_id,amount,status,created_at,accepted_at,settled_at,failed_at,refund_applied FROM ach_transfers ORDER BY id",
            "schedules": "SELECT id,transfer_type,source_account_id,destination_account_id,amount,status,next_execution_at FROM recurring_schedules ORDER BY id",
            "occurrences": "SELECT id,schedule_id,scheduled_at,status,attempted_at,transaction_id,ach_transfer_id FROM recurring_occurrences ORDER BY id",
            "limits": "SELECT user_id,per_transfer,daily,updated_at FROM transfer_limits ORDER BY user_id",
            "audit_entries": "SELECT sequence,event_id,event_type,operation_id,outcome,previous_hash,event_hash FROM audit_entries ORDER BY sequence",
            "audit_state": "SELECT singleton,sequence,head_hash,checkpoint_hmac FROM audit_state ORDER BY singleton",
            "domain_events": "SELECT event_sequence,event_id,aggregate_type,aggregate_id,aggregate_sequence,operation_id,event_type,currency,amount_minor_units,payload_json,occurred_at FROM domain_events ORDER BY event_sequence",
        }
        return {
            name: tuple(tuple(row) for row in conn.execute(query))
            for name, query in queries.items()
        }
