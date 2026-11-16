"""Synchronous, fail-closed account projection updates and deterministic replay."""
import hashlib
from datetime import datetime, timezone
import json
from decimal import Decimal

from event_store import read_events
from money import format_minor, convert_minor


def set_balance(cursor, account_id: str, minor: int, version: int):
    from services import encrypt_val
    row = cursor.execute("SELECT currency,version FROM accounts WHERE id=?", (account_id,)).fetchone()
    if row is None:
        raise ValueError(f"Missing projection account {account_id}")
    if version != row[1] + 1:
        raise ValueError(f"Account version gap for {account_id}")
    cursor.execute("UPDATE accounts SET balance=?,balance_minor=?,version=? WHERE id=? AND version=?",
                   (encrypt_val(format_minor(minor)), encrypt_val(str(minor)), version, account_id, version - 1))


def rebuild_projection(conn):
    """Rebuild into a temporary table, validate sequence and invariants, then atomically swap."""
    events = read_events(conn)
    balances = {}
    currencies = {}
    versions = {}
    expected_history = {}
    seen = set()
    account_names = {row[0]: row[1] for row in conn.execute("SELECT id,name FROM accounts").fetchall()}
    for event in events:
        if event["event_id"] in seen:
            raise ValueError("Duplicate event ID")
        seen.add(event["event_id"])
        typ, payload = event["event_type"], event["payload"]
        if typ in ("AccountOpeningBalanceSnapshot", "ReferenceAccountProvisioned"):
            aid = payload["account_id"]
            if aid in balances:
                raise ValueError("Duplicate account opening event")
            balances[aid] = int(payload["balance_minor"])
            currencies[aid] = payload["currency"]
            versions[aid] = 0
        elif typ == "LegacyHistoryImported":
            amount = int(payload["amount_minor"])
            source_id = payload.get("source_account_id")
            destination_id = payload.get("destination_account_id")
            for account_id, direction in ((source_id, "outgoing"), (destination_id, "incoming")):
                if account_id:
                    key = f"{payload['history_id']}:{account_id}"
                    expected_history[key] = (account_id, event["event_id"], direction, amount,
                                             currencies.get(account_id, payload.get("currency", "COP")),
                                             event["occurred_at"],
                                             f"Legacy {payload.get('transfer_type','INTERNAL')} {payload.get('status','').lower()}")
            continue
        elif typ in ("InternalTransferCompleted", "CurrencyConversionCompleted"):
            legs = payload["legs"]
            for leg in legs:
                aid, delta, currency, expected = leg["account_id"], int(leg["delta_minor"]), leg["currency"], int(leg["version"])
                if aid not in balances or currencies[aid] != currency or expected != versions[aid] + 1:
                    raise ValueError("Event account/currency/version invariant failed")
                balances[aid] += delta
                versions[aid] = expected
            if typ == "InternalTransferCompleted" and sum(int(x["delta_minor"]) for x in legs) != 0:
                raise ValueError("Internal transfer does not conserve value")
            if typ == "CurrencyConversionCompleted":
                source_leg, destination_leg = legs
                converted, numerator, denominator = convert_minor(-int(source_leg["delta_minor"]), source_leg["currency"], destination_leg["currency"])
                if (int(destination_leg["delta_minor"]) != converted or payload.get("rate_numerator") != numerator
                        or payload.get("rate_denominator") != denominator):
                    raise ValueError("Conversion rate/result invariant failed during replay")
            source_id, destination_id = legs[0]["account_id"], legs[1]["account_id"]
            transfer_id = payload["transfer_id"]
            for leg in legs:
                account_id = leg["account_id"]
                outgoing = int(leg["delta_minor"]) < 0
                if typ == "CurrencyConversionCompleted":
                    description = f"Currency conversion from {account_names[source_id]} to {account_names[destination_id]}"
                else:
                    other = destination_id if outgoing else source_id
                    description = f"Transfer {'to' if outgoing else 'from'} {account_names[other]}"
                history_key = f"{transfer_id}:{account_id}"
                expected_history[history_key] = (account_id, event["event_id"], "outgoing" if outgoing else "incoming",
                                                 abs(int(leg["delta_minor"])), leg["currency"], event["occurred_at"], description)
        elif typ == "AchTransferInitiated":
            aid = payload["source_account_id"] if "source_account_id" in payload else event["account_ids"][0]
            amount = int(payload["amount_minor"])
            currency = payload["currency"]
            expected_version = int(payload["account_version"])
            if aid not in balances or currencies[aid] != currency or expected_version != versions[aid] + 1 or balances[aid] < amount:
                raise ValueError("ACH debit event account/currency/version invariant failed")
            balances[aid] -= amount
            versions[aid] = expected_version
            ref = payload["reference_id"]
            expected_history[f"{ref}:{aid}"] = (aid,event["event_id"],"outgoing",amount,currency,event["occurred_at"],"ACH transfer pending settlement")
        elif typ == "AchTransferFailed":
            aid = event["account_ids"][0]
            amount = int(payload["amount_minor"])
            currency = payload["currency"]
            expected_version = int(payload["version"])
            if aid not in balances or currencies[aid] != currency or expected_version != versions[aid] + 1:
                raise ValueError("ACH refund event account/currency/version invariant failed")
            balances[aid] += amount
            versions[aid] = expected_version
            ref = payload["reference_id"]
            expected_history[f"{ref}:refund:{aid}"] = (aid,event["event_id"],"incoming",amount,currency,event["occurred_at"],"ACH failed; refund credited")
    cursor = conn.cursor()
    conn.execute("BEGIN IMMEDIATE")
    try:
        cursor = conn.cursor()
        from services import decrypt_val
        cursor.execute("CREATE TEMP TABLE stage4_rebuilt(account_id TEXT PRIMARY KEY,balance_minor INTEGER NOT NULL,version INTEGER NOT NULL,currency TEXT NOT NULL)")
        cursor.executemany("INSERT INTO stage4_rebuilt VALUES(?,?,?,?)", [(k,v,versions[k],currencies[k]) for k,v in balances.items()])
        for aid, balance, version, currency in cursor.execute("SELECT account_id,balance_minor,version,currency FROM stage4_rebuilt").fetchall():
            row = cursor.execute("SELECT balance,currency FROM accounts WHERE id=?", (aid,)).fetchone()
            from services import decrypt_val
            if row is None or row[1] != currency or Decimal(decrypt_val(row[0])) != Decimal(balance) / 100:
                raise ValueError("Rebuilt projection differs from committed account state")
            from services import encrypt_val
            cursor.execute("UPDATE accounts SET balance_minor=?,version=? WHERE id=?", (encrypt_val(str(balance)), version, aid))
        cursor.execute("DROP TABLE stage4_rebuilt")
        cursor.execute("CREATE TEMP TABLE stage4_history_rebuilt(history_id TEXT PRIMARY KEY,account_id TEXT,event_id TEXT,direction TEXT,amount_minor INTEGER,currency TEXT,occurred_at TEXT,description TEXT)")
        cursor.executemany("INSERT INTO stage4_history_rebuilt VALUES(?,?,?,?,?,?,?,?)",
                           [(key, *value) for key, value in expected_history.items()])
        actual_history = {}
        for row in cursor.execute("SELECT history_id,account_id,event_id,direction,amount_minor,currency,occurred_at,description FROM history_projection").fetchall():
            actual_history[row[0]] = (row[1], row[2], row[3], int(decrypt_val(row[4])), row[5], row[6], row[7])
        if actual_history != expected_history:
            raise ValueError("Rebuilt history projection differs from committed event history")
        cursor.execute("DROP TABLE stage4_history_rebuilt")
        event_hash = _event_stream_hash(conn)
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute("INSERT OR REPLACE INTO projection_checkpoints VALUES('accounts',?,?,?)",
                       (events[-1]["sequence"] if events else 0, event_hash, now))
        conn.commit()
        return len(events)
    except Exception:
        conn.rollback()
        raise


def projection_status(conn):
    row = conn.execute("SELECT event_sequence,event_hash,updated_at FROM projection_checkpoints WHERE projection_name='accounts'").fetchone()
    latest = conn.execute("SELECT COALESCE(MAX(sequence),0) FROM domain_events").fetchone()[0]
    return {"latest_event_sequence": latest, "checkpoint_sequence": row[0] if row else 0,
            "checkpoint_hash": row[1] if row else None, "event_stream_hash": _event_stream_hash(conn),
            "checkpoint_updated_at": row[2] if row else None}


def _event_stream_hash(conn):
    raw_conn = getattr(conn, "_conn", conn)
    rows = raw_conn.execute("SELECT sequence,event_id,payload_json FROM domain_events ORDER BY sequence").fetchall()
    return hashlib.sha256("".join(f"{row[0]}:{row[1]}:{row[2]}\n" for row in rows).encode()).hexdigest()
