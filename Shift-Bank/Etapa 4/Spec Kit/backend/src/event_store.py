"""Append-only SQLite storage for monetary domain events."""
import json
import sqlite3
from datetime import datetime, timezone


def append_event(cursor: sqlite3.Cursor, *, event_id: str, command_id: str, event_type: str,
                 account_ids: list[str], payload: dict, occurred_at: str | None = None,
                 schema_version: int = 1) -> int:
    from services import encrypt_val
    from event_handlers import validate_event_payload
    validate_event_payload(event_type, payload)
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    cursor.execute(
        "INSERT INTO domain_events(event_id,command_id,event_type,schema_version,occurred_at,account_ids_json,payload_json) VALUES(?,?,?,?,?,?,?)",
        (event_id, command_id, event_type, schema_version,
         occurred_at or datetime.now(timezone.utc).isoformat(),
         json.dumps(account_ids, separators=(",", ":"), sort_keys=True),
         encrypt_val(payload_json)),
    )
    return int(cursor.lastrowid)


def read_events(conn: sqlite3.Connection, after_sequence: int = 0) -> list[dict]:
    rows = conn.execute(
        "SELECT sequence,event_id,command_id,event_type,schema_version,occurred_at,account_ids_json,payload_json FROM domain_events WHERE sequence>? ORDER BY sequence",
        (after_sequence,),
    ).fetchall()
    from services import decrypt_val
    return [dict(sequence=r[0], event_id=r[1], command_id=r[2], event_type=r[3],
                 schema_version=r[4], occurred_at=r[5], account_ids=json.loads(r[6]), payload=json.loads(decrypt_val(r[7])))
            for r in rows]
