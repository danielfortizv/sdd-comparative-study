import sqlite3

import database
import pytest
from event_store import append_event, read_events
from projections import rebuild_projection


def test_event_store_append_only_and_projection_replay(tmp_path):
    path = str(tmp_path / "events.sqlite")
    database.init_db(path)
    conn = sqlite3.connect(path)
    events = read_events(conn)
    assert len(events) == 8
    assert [e["sequence"] for e in events] == sorted(e["sequence"] for e in events)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE domain_events SET event_type='Changed' WHERE sequence=1")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM domain_events WHERE sequence=1")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE accounts SET currency='EUR' WHERE id='CHK-1001'")
    conn.rollback()
    assert rebuild_projection(conn) == 8
    assert rebuild_projection(conn) == 8
    assert rebuild_projection(conn) == 8
    conn.close()


def test_history_import_event_has_no_balance_effect(tmp_path):
    path = str(tmp_path / "history.sqlite")
    database.init_db(path)
    conn = sqlite3.connect(path)
    before = conn.execute("SELECT id,balance_minor FROM accounts ORDER BY id").fetchall()
    conn.execute("BEGIN")
    imported = [e for e in read_events(conn) if e["event_type"] == "LegacyHistoryImported"]
    assert len(imported) == 2
    assert conn.execute("SELECT id,balance_minor FROM accounts ORDER BY id").fetchall() == before
    conn.rollback()
    conn.close()


def test_unknown_event_type_rejected_and_stream_payload_is_encrypted(tmp_path):
    path = str(tmp_path / "invalid-event.sqlite")
    database.init_db(path)
    conn = sqlite3.connect(path)
    row = conn.execute("SELECT payload_json FROM domain_events LIMIT 1").fetchone()
    assert row[0].startswith("enc:v1:")
    with pytest.raises(ValueError, match="Unknown event type"):
        append_event(conn.cursor(), event_id="bad", command_id="bad", event_type="UnknownEvent",
                     account_ids=[], payload={})
    conn.rollback()
    conn.close()


def test_replay_rejects_version_gap_and_event_id_reuse(tmp_path):
    from event_store import append_event
    path = str(tmp_path / "gap.sqlite")
    database.init_db(path)
    conn = sqlite3.connect(path)
    opening = read_events(conn)
    source = next(e["payload"]["account_id"] for e in opening if e["event_type"] == "ReferenceAccountProvisioned")
    destination = "SAV-2001"
    payload = {"legs":[
        {"account_id":source,"delta_minor":-100,"currency":"USD","version":2},
        {"account_id":destination,"delta_minor":100,"currency":"USD","version":2}],
        "source_amount_minor":100,"destination_amount_minor":100,"rate_numerator":1,"rate_denominator":1,"transfer_id":"gap-transfer"}
    append_event(conn.cursor(),event_id="gap-event",command_id="gap-command",event_type="InternalTransferCompleted",
                 account_ids=[source,destination],payload=payload)
    conn.commit()
    with pytest.raises(ValueError, match="version invariant"):
        rebuild_projection(conn)
    with pytest.raises(sqlite3.IntegrityError):
        append_event(conn.cursor(),event_id="gap-event",command_id="again",event_type="InternalTransferCompleted",
                     account_ids=[source,destination],payload={**payload,"legs":[{**payload["legs"][0],"version":1},{**payload["legs"][1],"version":1}]})
    conn.rollback()
    conn.close()


def test_event_validator_rejects_non_conserving_internal_transfer(tmp_path):
    from event_store import append_event
    path = str(tmp_path / "conservation.sqlite")
    database.init_db(path)
    conn = sqlite3.connect(path)
    with pytest.raises(ValueError, match="conserve"):
        append_event(conn.cursor(), event_id="bad-conservation", command_id="bad", event_type="InternalTransferCompleted",
                     account_ids=["CHK-1001", "SAV-2001"], payload={"transfer_id":"bad-transfer","legs":[
                         {"account_id":"CHK-1001","delta_minor":-100,"currency":"USD","version":1},
                         {"account_id":"SAV-2001","delta_minor":99,"currency":"USD","version":1}]})
    conn.rollback()
    conn.close()
