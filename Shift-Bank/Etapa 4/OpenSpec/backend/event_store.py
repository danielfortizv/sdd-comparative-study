"""Append-only SQLite primitives for Stage 4 financial domain events.

Callers own the transaction so event appends can later share one atomic commit
with command results, projections, idempotency records, and the audit chain.
Financial amounts are stored as integer minor units with an explicit currency.
"""
from __future__ import annotations

import json
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any


SUPPORTED_CURRENCIES = frozenset({"USD", "EUR", "GBP"})


class EventStoreError(ValueError):
    """A domain event is invalid or cannot be safely persisted."""


def install_schema(conn: sqlite3.Connection) -> None:
    """Install the durable event table and database-enforced append-only guards."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS domain_events (
            event_sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL UNIQUE,
            aggregate_type TEXT NOT NULL CHECK(length(aggregate_type) > 0),
            aggregate_id TEXT NOT NULL CHECK(length(aggregate_id) > 0),
            aggregate_sequence INTEGER NOT NULL CHECK(aggregate_sequence > 0),
            operation_id TEXT NOT NULL CHECK(length(operation_id) > 0),
            event_type TEXT NOT NULL CHECK(length(event_type) > 0),
            currency TEXT,
            amount_minor_units INTEGER,
            payload_json TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            UNIQUE(aggregate_type, aggregate_id, aggregate_sequence),
            CHECK ((currency IS NULL AND amount_minor_units IS NULL)
                OR (currency IN ('USD', 'EUR', 'GBP') AND amount_minor_units IS NOT NULL))
        )"""
    )
    conn.execute(
        """CREATE TRIGGER IF NOT EXISTS domain_events_no_update
        BEFORE UPDATE ON domain_events
        BEGIN SELECT RAISE(ABORT, 'domain events are append-only'); END"""
    )
    conn.execute(
        """CREATE TRIGGER IF NOT EXISTS domain_events_no_delete
        BEFORE DELETE ON domain_events
        BEGIN SELECT RAISE(ABORT, 'domain events are append-only'); END"""
    )


def _contains_float(value: Any) -> bool:
    if isinstance(value, float):
        return True
    if isinstance(value, dict):
        return any(_contains_float(key) or _contains_float(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return any(_contains_float(item) for item in value)
    return False


def append_event(
    conn: sqlite3.Connection,
    *,
    aggregate_type: str,
    aggregate_id: str,
    operation_id: str,
    event_type: str,
    payload: dict[str, Any],
    currency: str | None = None,
    amount_minor_units: int | None = None,
    occurred_at: datetime | None = None,
    event_id: str | None = None,
) -> dict[str, Any]:
    """Append one event to the caller's active transaction.

    Monetary effects use signed integer minor units and one supported currency.
    Non-monetary lifecycle events may leave both amount fields null.
    """
    if not conn.in_transaction:
        raise EventStoreError("Domain event append requires an active transaction")
    for label, value in (
        ("aggregate_type", aggregate_type),
        ("aggregate_id", aggregate_id),
        ("operation_id", operation_id),
        ("event_type", event_type),
    ):
        if not isinstance(value, str) or not value.strip():
            raise EventStoreError(f"{label} must be a non-empty string")
    if (currency is None) != (amount_minor_units is None):
        raise EventStoreError("Currency and amount must either both be provided or both be absent")
    if currency is not None and (
        not isinstance(currency, str) or currency not in SUPPORTED_CURRENCIES
    ):
        raise EventStoreError("Unsupported event currency")
    if amount_minor_units is not None and (
        isinstance(amount_minor_units, bool) or not isinstance(amount_minor_units, int)
    ):
        raise EventStoreError("Event amount must use integer minor units")
    if amount_minor_units is not None and not -(2**63) <= amount_minor_units < 2**63:
        raise EventStoreError("Event amount is outside the supported integer storage range")
    if not isinstance(payload, dict) or _contains_float(payload):
        raise EventStoreError("Event payload must be an object without binary floating-point values")
    try:
        payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError):
        raise EventStoreError("Event payload must contain JSON-compatible values") from None

    row = conn.execute(
        """SELECT COALESCE(MAX(aggregate_sequence), 0) + 1
           FROM domain_events WHERE aggregate_type=? AND aggregate_id=?""",
        (aggregate_type, aggregate_id),
    ).fetchone()
    aggregate_sequence = row[0]
    if occurred_at is None:
        timestamp = datetime.now(timezone.utc)
    elif not isinstance(occurred_at, datetime) or occurred_at.tzinfo is None:
        raise EventStoreError("Event timestamp must be timezone-aware")
    else:
        timestamp = occurred_at.astimezone(timezone.utc)
    occurred_at_text = timestamp.isoformat(timespec="microseconds").replace("+00:00", "Z")
    if event_id is None:
        event_id = "evt_" + uuid.uuid4().hex
    elif not isinstance(event_id, str) or not re.fullmatch(r"evt_[0-9a-f]{32}", event_id):
        raise EventStoreError("event_id must be a canonical event identifier")
    cursor = conn.execute(
        """INSERT INTO domain_events
           (event_id, aggregate_type, aggregate_id, aggregate_sequence, operation_id,
            event_type, currency, amount_minor_units, payload_json, occurred_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            event_id,
            aggregate_type,
            aggregate_id,
            aggregate_sequence,
            operation_id,
            event_type,
            currency,
            amount_minor_units,
            payload_json,
            occurred_at_text,
        ),
    )
    return {
        "event_sequence": cursor.lastrowid,
        "event_id": event_id,
        "aggregate_type": aggregate_type,
        "aggregate_id": aggregate_id,
        "aggregate_sequence": aggregate_sequence,
        "operation_id": operation_id,
        "event_type": event_type,
        "currency": currency,
        "amount_minor_units": amount_minor_units,
        "payload": payload,
        "occurred_at": occurred_at_text,
    }


def list_events(
    conn: sqlite3.Connection,
    *,
    after_sequence: int = 0,
    limit: int = 1000,
) -> list[dict[str, Any]]:
    """Read a stable slice of the global event order."""
    if isinstance(after_sequence, bool) or not isinstance(after_sequence, int) or after_sequence < 0:
        raise EventStoreError("after_sequence must be a non-negative integer")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 10000:
        raise EventStoreError("limit must be between 1 and 10000")
    rows = conn.execute(
        """SELECT event_sequence, event_id, aggregate_type, aggregate_id, aggregate_sequence,
                  operation_id, event_type, currency, amount_minor_units, payload_json, occurred_at
           FROM domain_events WHERE event_sequence > ? ORDER BY event_sequence LIMIT ?""",
        (after_sequence, limit),
    ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["payload"] = json.loads(item.pop("payload_json"))
        result.append(item)
    return result
