"""Currency and identity primitives for Stage 4 account records."""
from __future__ import annotations

import sqlite3
from typing import Any


SUPPORTED_CURRENCIES = frozenset({"USD", "EUR", "GBP"})
LEGACY_PUBLIC_REFERENCES = {
    "acc_checking": "CHK-1001",
    "acc_savings": "SAV-2001",
}


class AccountModelError(ValueError):
    """An account identity or currency cannot be resolved safely."""


class AccountCurrencyError(AccountModelError):
    """An account is not yet eligible for supported-currency operations."""


def validate_currency(value: Any) -> str:
    """Return an exact supported currency code or reject it."""
    if not isinstance(value, str) or value not in SUPPORTED_CURRENCIES:
        raise AccountCurrencyError("Account currency must be USD, EUR, or GBP")
    return value


def require_spendable_currency(account: Any) -> str:
    """Fail closed unless an account has completed Stage 4 currency assignment."""
    if account is None or account["migration_state"] != "active":
        raise AccountCurrencyError("Account currency migration is not complete")
    return validate_currency(account["currency"])


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}


def initialize_account_identity(conn: sqlite3.Connection) -> None:
    """Add nullable Stage 4 metadata and stable public aliases without touching money.

    Existing rows remain `legacy_unmigrated` with a NULL supported currency. Their
    balances and transaction references are intentionally left unchanged until
    the separately specified COP migration is implemented and authorized.
    """
    owns_transaction = not conn.in_transaction
    if owns_transaction:
        conn.execute("BEGIN IMMEDIATE")
    try:
        columns = _columns(conn, "accounts")
        if "currency" not in columns:
            conn.execute(
                "ALTER TABLE accounts ADD COLUMN currency TEXT "
                "CHECK(currency IS NULL OR currency IN ('USD','EUR','GBP'))"
            )
        if "public_reference" not in columns:
            conn.execute("ALTER TABLE accounts ADD COLUMN public_reference TEXT")
        if "migration_state" not in columns:
            conn.execute(
                "ALTER TABLE accounts ADD COLUMN migration_state TEXT NOT NULL "
                "DEFAULT 'legacy_unmigrated' "
                "CHECK(migration_state IN ('legacy_unmigrated','active'))"
            )
        if "account_version" not in columns:
            conn.execute(
                "ALTER TABLE accounts ADD COLUMN account_version INTEGER NOT NULL "
                "DEFAULT 0 CHECK(account_version >= 0)"
            )
        conn.execute(
            """CREATE UNIQUE INDEX IF NOT EXISTS idx_accounts_public_reference
               ON accounts(public_reference) WHERE public_reference IS NOT NULL"""
        )

        for internal_id, public_reference in LEGACY_PUBLIC_REFERENCES.items():
            row = conn.execute(
                "SELECT public_reference FROM accounts WHERE id=?", (internal_id,)
            ).fetchone()
            if row is None:
                continue
            current = row["public_reference"]
            if current not in (None, public_reference):
                raise AccountModelError(
                    f"Conflicting public reference for inherited account {internal_id}"
                )
            if current is None:
                conn.execute(
                    "UPDATE accounts SET public_reference=? WHERE id=? AND public_reference IS NULL",
                    (public_reference, internal_id),
                )
        if owns_transaction:
            conn.commit()
    except Exception:
        if owns_transaction and conn.in_transaction:
            conn.rollback()
        raise


def resolve_account_reference(conn: sqlite3.Connection, reference: Any):
    """Resolve a legacy internal ID or public reference to one persisted row."""
    if not isinstance(reference, str) or not reference:
        raise AccountModelError("Account reference is required")
    rows = conn.execute(
        """SELECT id, name, balance, currency, public_reference, migration_state
           FROM accounts WHERE id=? OR public_reference=?""",
        (reference, reference),
    ).fetchall()
    if not rows:
        return None
    if len(rows) != 1:
        raise AccountModelError("Account reference is ambiguous")
    return rows[0]
