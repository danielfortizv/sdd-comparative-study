"""Read-only, transaction-bound validation before the approved legacy cutover."""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Iterable

import account_model
import audit
import banking


_ISSUE_ORDER = (
    "transaction_required",
    "preflight_time_invalid",
    "source_schema_unreconcilable",
    "account_state_ambiguous",
    "source_balance_unreconcilable",
    "source_configuration_unreconcilable",
    "pending_ach",
    "pending_mfa",
    "active_recurring_schedule",
    "paused_recurring_schedule",
    "legacy_history_unreconcilable",
    "current_day_usage_unverifiable",
    "current_day_limit_usage_nonzero",
    "preexisting_domain_events",
    "audit_chain_unverifiable",
)


@dataclass(frozen=True)
class PreflightIssue:
    code: str
    record_ids: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {"code": self.code, "record_ids": list(self.record_ids)}


@dataclass(frozen=True)
class MigrationPreflightResult:
    eligible: bool
    checked_at_utc: str | None
    issues: tuple[PreflightIssue, ...]

    def as_dict(self) -> dict:
        return {
            "eligible": self.eligible,
            "checked_at_utc": self.checked_at_utc,
            "issues": [issue.as_dict() for issue in self.issues],
        }


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}


def _safe_decimal(value, *, positive: bool = False) -> Decimal | None:
    if not isinstance(value, str) or not re.fullmatch(r"\d+(?:\.\d{1,2})?", value):
        return None
    try:
        parsed = Decimal(value)
    except InvalidOperation:
        return None
    if not parsed.is_finite() or (positive and parsed <= 0):
        return None
    return parsed


def _valid_timestamp(value) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _result(issues: dict[str, set[str]], checked_at_utc: str | None) -> MigrationPreflightResult:
    ordered = tuple(
        PreflightIssue(code, tuple(sorted(issues.get(code, set()))))
        for code in _ISSUE_ORDER
        if code in issues
    )
    return MigrationPreflightResult(not ordered, checked_at_utc, ordered)


def _add(issues: dict[str, set[str]], code: str, records: Iterable[str] = ()) -> None:
    issues.setdefault(code, set()).update(str(record) for record in records if record is not None)


def _tables(conn: sqlite3.Connection) -> set[str]:
    return {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _validate_accounts(conn: sqlite3.Connection, issues: dict[str, set[str]]) -> set[str]:
    expected = account_model.LEGACY_PUBLIC_REFERENCES
    if not {"accounts"}.issubset(_tables(conn)):
        _add(issues, "source_schema_unreconcilable", ("accounts",))
        return set()
    required = {"id", "name", "balance", "currency", "public_reference", "migration_state"}
    if not required.issubset(_columns(conn, "accounts")):
        _add(issues, "account_state_ambiguous", ("accounts",))
        return set()
    rows = conn.execute(
        "SELECT id,name,balance,currency,public_reference,migration_state FROM accounts ORDER BY id"
    ).fetchall()
    ids = {row["id"] for row in rows}
    for unknown in sorted(ids - set(expected), key=str):
        _add(issues, "account_state_ambiguous", (unknown,))
    for missing in sorted(set(expected) - ids):
        _add(issues, "account_state_ambiguous", (missing,))
    for row in rows:
        account_id = row["id"]
        if account_id not in expected:
            continue
        if (
            row["public_reference"] != expected[account_id]
            or row["currency"] is not None
            or row["migration_state"] != "legacy_unmigrated"
        ):
            _add(issues, "account_state_ambiguous", (account_id,))
        balance = _safe_decimal(row["balance"])
        if balance is None:
            _add(issues, "source_balance_unreconcilable", (account_id,))
        for reference in (account_id, expected[account_id]):
            try:
                resolved = account_model.resolve_account_reference(conn, reference)
            except account_model.AccountModelError:
                resolved = None
            if resolved is None or resolved["id"] != account_id:
                _add(issues, "account_state_ambiguous", (account_id, reference))
    return ids


def _validate_limits(conn: sqlite3.Connection, issues: dict[str, set[str]]) -> None:
    if "transfer_limits" not in _tables(conn):
        _add(issues, "source_configuration_unreconcilable", ("transfer_limits",))
        return
    rows = conn.execute("SELECT user_id,per_transfer,daily FROM transfer_limits ORDER BY user_id").fetchall()
    if not rows:
        _add(issues, "source_configuration_unreconcilable", ("transfer_limits",))
        return
    for row in rows:
        user_id = row["user_id"]
        if (
            not isinstance(user_id, str)
            or not user_id
            or _safe_decimal(row["per_transfer"], positive=True) is None
            or _safe_decimal(row["daily"], positive=True) is None
        ):
            _add(issues, "source_configuration_unreconcilable", (user_id or "transfer_limits",))


def _validate_history(conn: sqlite3.Connection, account_ids: set[str], issues: dict[str, set[str]]) -> None:
    tables = _tables(conn)
    if not {"transactions", "ach_transfers", "recurring_schedules"}.issubset(tables):
        _add(issues, "source_schema_unreconcilable", ("legacy_operations",))
        return

    transaction_columns = _columns(conn, "transactions")
    needed_transactions = {"id", "source_account_id", "destination_account_id", "amount", "timestamp", "status"}
    if not needed_transactions.issubset(transaction_columns):
        _add(issues, "source_schema_unreconcilable", ("transactions",))
    else:
        for row in conn.execute(
            "SELECT id,source_account_id,destination_account_id,amount,timestamp,status FROM transactions ORDER BY id"
        ):
            record_id = row["id"]
            status = str(row["status"]).lower()
            if status in {"pending", "pending_mfa", "awaiting_mfa"}:
                _add(issues, "pending_mfa" if status != "pending" else "legacy_history_unreconcilable", (record_id,))
                continue
            if status not in {"completed", "failed", "expired", "cancelled", "canceled"}:
                _add(issues, "legacy_history_unreconcilable", (record_id,))
                continue
            if (
                row["source_account_id"] not in account_ids
                or row["destination_account_id"] not in account_ids
                or _safe_decimal(row["amount"], positive=True) is None
                or not _valid_timestamp(row["timestamp"])
            ):
                _add(issues, "legacy_history_unreconcilable", (record_id,))

    ach_columns = _columns(conn, "ach_transfers")
    needed_ach = {"id", "source_account_id", "amount", "status", "created_at", "accepted_at", "refund_applied"}
    if not needed_ach.issubset(ach_columns):
        _add(issues, "source_schema_unreconcilable", ("ach_transfers",))
    else:
        for row in conn.execute(
            "SELECT id,source_account_id,amount,status,created_at,accepted_at,refund_applied FROM ach_transfers ORDER BY id"
        ):
            record_id = row["id"]
            status = str(row["status"]).lower()
            if status == "pending":
                _add(issues, "pending_ach", (record_id,))
            elif status == "pending_mfa":
                _add(issues, "pending_mfa", (record_id,))
            elif status not in {"settled", "failed", "cancelled", "canceled", "expired"}:
                _add(issues, "legacy_history_unreconcilable", (record_id,))
            if (
                row["source_account_id"] not in account_ids
                or _safe_decimal(row["amount"], positive=True) is None
                or not _valid_timestamp(row["created_at"])
                or (status in {"settled", "failed"} and not _valid_timestamp(row["accepted_at"]))
                or (status == "failed" and row["refund_applied"] != 1)
                or (status == "settled" and row["refund_applied"] != 0)
            ):
                _add(issues, "legacy_history_unreconcilable", (record_id,))

    schedule_columns = _columns(conn, "recurring_schedules")
    needed_schedules = {"id", "transfer_type", "source_account_id", "destination_account_id", "amount", "status"}
    if not needed_schedules.issubset(schedule_columns):
        _add(issues, "source_schema_unreconcilable", ("recurring_schedules",))
    else:
        for row in conn.execute(
            "SELECT id,transfer_type,source_account_id,destination_account_id,amount,status FROM recurring_schedules ORDER BY id"
        ):
            record_id = row["id"]
            status = str(row["status"]).lower()
            if status == "active":
                _add(issues, "active_recurring_schedule", (record_id,))
            elif status == "paused":
                _add(issues, "paused_recurring_schedule", (record_id,))
            elif status == "pending_mfa":
                _add(issues, "pending_mfa", (record_id,))
            elif status not in {"cancelled", "canceled", "expired", "completed"}:
                _add(issues, "legacy_history_unreconcilable", (record_id,))
            if (
                row["transfer_type"] not in {"internal", "ach"}
                or row["source_account_id"] not in account_ids
                or (row["transfer_type"] == "internal" and row["destination_account_id"] not in account_ids)
                or _safe_decimal(row["amount"], positive=True) is None
            ):
                _add(issues, "legacy_history_unreconcilable", (record_id,))


def preflight_migration(conn: sqlite3.Connection, checked_at: datetime) -> MigrationPreflightResult:
    """Read and validate the legacy cutover state without changing any records.

    The caller must start a SQLite `BEGIN IMMEDIATE` transaction and retain it
    through the later cutover writes. This keeps the preflight view stable and
    avoids a time-of-check/time-of-use gap. The function never commits or writes.
    """
    issues: dict[str, set[str]] = {}
    if not conn.in_transaction:
        _add(issues, "transaction_required")
        return _result(issues, None)
    if not isinstance(checked_at, datetime) or checked_at.tzinfo is None or checked_at.utcoffset() is None:
        _add(issues, "preflight_time_invalid")
        return _result(issues, None)
    checked_at_utc = checked_at.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")

    account_ids = _validate_accounts(conn, issues)
    _validate_limits(conn, issues)
    _validate_history(conn, account_ids, issues)

    tables = _tables(conn)
    if "domain_events" not in tables:
        _add(issues, "source_schema_unreconcilable", ("domain_events",))
    else:
        event_count = conn.execute("SELECT COUNT(*) FROM domain_events").fetchone()[0]
        if event_count:
            _add(issues, "preexisting_domain_events", ("domain_events",))

    try:
        usage = banking.daily_usage(conn, checked_at)
        if usage != Decimal("0"):
            _add(issues, "current_day_limit_usage_nonzero")
    except Exception:
        _add(issues, "current_day_usage_unverifiable")

    try:
        verification = audit.verify_connection(conn)
        if not verification.get("valid"):
            _add(issues, "audit_chain_unverifiable")
    except Exception:
        _add(issues, "audit_chain_unverifiable")

    return _result(issues, checked_at_utc)
