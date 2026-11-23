import uuid

import pytest
import database
import services


def test_audit_failure_rolls_back_event_projection_transfer_and_idempotency(monkeypatch):
    conn = database.get_connection()
    try:
        before = conn.cursor().execute("SELECT id,balance_minor,version FROM accounts WHERE id IN ('CHK-1001','SAV-2001') ORDER BY id").fetchall()
        counts = conn.cursor().execute("SELECT (SELECT COUNT(*) FROM domain_events),(SELECT COUNT(*) FROM transfers),(SELECT COUNT(*) FROM idempotency_records)").fetchone()
        monkeypatch.setattr(services, "append_audit_record", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("injected audit failure")))
        versions = dict(conn.cursor().execute("SELECT id,version FROM accounts WHERE id IN ('CHK-1001','SAV-2001')").fetchall())
        payload = {"source_account_id":"CHK-1001","destination_account_id":"SAV-2001","amount":"1.00",
                   "expected_versions":versions}
        with pytest.raises(RuntimeError, match="injected audit failure"):
            services.execute_stage4_command(conn,"TRANSFER",str(uuid.uuid4()),payload)
        after = conn.cursor().execute("SELECT id,balance_minor,version FROM accounts WHERE id IN ('CHK-1001','SAV-2001') ORDER BY id").fetchall()
        after_counts = conn.cursor().execute("SELECT (SELECT COUNT(*) FROM domain_events),(SELECT COUNT(*) FROM transfers),(SELECT COUNT(*) FROM idempotency_records)").fetchone()
        assert before == after
        assert counts == after_counts
    finally:
        conn.close()
