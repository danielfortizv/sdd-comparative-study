"""SQLite-backed account store owned by the identity service (Stage 4 R1.2).

This is the identity service's private store. No other service reads or writes
this database. It holds Customer accounts with a one-way hashed credential;
plain-text passwords are never stored. Password hashing mirrors the Stage 3
policy (bcrypt with a SHA-256 pre-hash for inputs over bcrypt's 72-byte limit).
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path

import bcrypt

_DEFAULT_DB = Path(__file__).resolve().parent.parent / "identity.db"


def _db_path() -> Path:
    return Path(os.environ.get("IDENTITY_DB_PATH", str(_DEFAULT_DB)))


def _to_secret(password: str) -> bytes:
    raw = password.encode("utf-8")
    if len(raw) > 72:
        return hashlib.sha256(raw).hexdigest().encode("ascii")
    return raw


def hash_password(password: str) -> str:
    """Return a bcrypt hash of ``password`` (never the plain text)."""
    return bcrypt.hashpw(_to_secret(password), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    """Return whether ``password`` matches the stored bcrypt hash."""
    try:
        return bcrypt.checkpw(_to_secret(password), password_hash.encode("ascii"))
    except ValueError:
        return False


@dataclass(frozen=True)
class Account:
    """A stored account; ``password_hash`` is one-way and never returned to clients."""

    id: str
    identifier: str
    password_hash: str
    is_moderator: bool


class AccountStore:
    """Private SQLite store for identity accounts."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path if path is not None else _db_path()
        self._lock = threading.Lock()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _init_schema(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS accounts (
                    id TEXT PRIMARY KEY,
                    identifier TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    is_moderator INTEGER NOT NULL DEFAULT 0
                )
                """
            )

    def _row_to_account(self, row: sqlite3.Row) -> Account:
        return Account(
            id=row["id"],
            identifier=row["identifier"],
            password_hash=row["password_hash"],
            is_moderator=bool(row["is_moderator"]),
        )

    def get_by_identifier(self, identifier: str) -> Account | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM accounts WHERE identifier = ?", (identifier,)
            ).fetchone()
            return self._row_to_account(row) if row is not None else None

    def get_by_id(self, account_id: str) -> Account | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM accounts WHERE id = ?", (account_id,)
            ).fetchone()
            return self._row_to_account(row) if row is not None else None

    def create_account(self, identifier: str, password_hash: str) -> Account:
        """Create a customer account. Raises ValueError if the identifier exists."""
        account = Account(
            id=str(uuid.uuid4()),
            identifier=identifier,
            password_hash=password_hash,
            is_moderator=False,
        )
        return self._insert(account)

    def add_account(self, account: Account) -> Account:
        """Store a pre-built account (used to seed the moderator)."""
        return self._insert(account)

    def _insert(self, account: Account) -> Account:
        with self._lock, self._connect() as conn:
            try:
                conn.execute(
                    "INSERT INTO accounts (id, identifier, password_hash, is_moderator)"
                    " VALUES (?, ?, ?, ?)",
                    (
                        account.id,
                        account.identifier,
                        account.password_hash,
                        1 if account.is_moderator else 0,
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise ValueError(
                    f"An account already exists for identifier: {account.identifier}"
                ) from error
        return account

    def clear(self) -> None:
        """Remove all accounts (test support)."""
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM accounts")
