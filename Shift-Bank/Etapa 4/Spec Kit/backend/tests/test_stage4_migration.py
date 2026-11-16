import sqlite3
from decimal import Decimal

import database
import crypto
from fixtures.stage4_baseline import create_e3_database
from fixtures.stage4_accounts import D02_ACCOUNTS


def test_cutover_preserves_cop_and_imports_history_without_balance_effect(tmp_path):
    path = create_e3_database(str(tmp_path / "e3-copy.sqlite"))
    database.init_db(path)
    conn = sqlite3.connect(path)
    rows = dict((r[0], (crypto.decrypt_at_rest(r[1]) if r[1].startswith("enc:v1:") else r[1], r[2], int(crypto.decrypt_at_rest(r[3]) if r[3].startswith("enc:v1:") else r[3])))
                for r in conn.execute("SELECT id,balance,currency,balance_minor FROM accounts"))
    assert rows["acc_checking_123"] == ("5000000.00", "COP", 500000000)
    assert rows["acc_savings_456"] == ("15000000.00", "COP", 1500000000)
    for account_id, (name, currency, balance) in D02_ACCOUNTS.items():
        got = conn.execute("SELECT name,balance,currency,balance_minor FROM accounts WHERE id=?", (account_id,)).fetchone()
        raw_balance = crypto.decrypt_at_rest(got[1]) if got[1].startswith("enc:v1:") else got[1]
        minor = int(crypto.decrypt_at_rest(got[3]) if got[3].startswith("enc:v1:") else got[3])
        assert (got[0], raw_balance, got[2], minor) == (name, balance, currency, int(Decimal(balance) * 100))
    assert conn.execute("SELECT COUNT(*) FROM history_projection WHERE history_id='legacy-1:acc_checking_123'").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM domain_events WHERE event_type='LegacyHistoryImported'").fetchone()[0] == 1
    conn.close()


def test_cutover_repeat_is_idempotent(tmp_path):
    path = create_e3_database(str(tmp_path / "repeat.sqlite"))
    database.init_db(path)
    conn = sqlite3.connect(path)
    before = (conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0],
              conn.execute("SELECT COUNT(*) FROM domain_events").fetchone()[0],
              conn.execute("SELECT COUNT(*) FROM history_projection").fetchone()[0])
    database.migrate_stage4(conn)
    after = (conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0],
             conn.execute("SELECT COUNT(*) FROM domain_events").fetchone()[0],
             conn.execute("SELECT COUNT(*) FROM history_projection").fetchone()[0])
    assert before == after == (6, 7, 2)
    conn.close()


def test_conflicting_reference_account_rolls_back_cutover(tmp_path):
    path = create_e3_database(str(tmp_path / "conflict.sqlite"))
    conn = sqlite3.connect(path)
    conn.execute("INSERT INTO accounts VALUES('CHK-1001','Checking USD','999.00','USD')")
    conn.commit()
    try:
        database.init_db(path)
    except RuntimeError as exc:
        assert "Conflicting pre-existing D-02 account" in str(exc)
    else:
        raise AssertionError("Conflicting D-02 identity should fail closed")
    assert conn.execute("SELECT name FROM sqlite_master WHERE name='domain_events'").fetchone() is None
    stored = conn.execute("SELECT balance FROM accounts WHERE id='acc_checking_123'").fetchone()[0]
    assert (crypto.decrypt_at_rest(stored) if stored.startswith("enc:v1:") else stored) == "5000000.00"
    conn.close()
