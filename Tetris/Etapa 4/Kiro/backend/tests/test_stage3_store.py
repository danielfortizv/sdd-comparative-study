"""Stage 3 unit tests for the SQLite High_Score_Store.

Covers startup/schema/durability (tasks 1.5) and tie-break ordering plus the
ten-row cap (task 1.6). Each test uses an isolated temp DB path.
"""

from __future__ import annotations

import os
import sqlite3

import pytest

from app.persistence.store import HighScoreRecord, HighScoreStore, StorageError


def _rec(game_id, score, completed_at, total_lines=0, level=1):
    return HighScoreRecord(
        game_id=game_id,
        score=score,
        total_lines=total_lines,
        level=level,
        completed_at=completed_at,
    )


def test_initialize_creates_missing_parent_and_schema(tmp_path):
    db = tmp_path / "nested" / "dir" / "hs.sqlite3"
    store = HighScoreStore(str(db))
    store.initialize()

    assert db.parent.exists()
    assert db.exists()
    # Schema exists and is queryable.
    assert store.top_ten() == []


def test_initialize_is_idempotent_and_keeps_rows(tmp_path):
    db = tmp_path / "hs.sqlite3"
    store = HighScoreStore(str(db))
    store.initialize()
    assert store.finalize(_rec("g1", 100, "2026-01-01T00:00:00+00:00")) is True

    # Re-initialize: existing rows are left intact (CREATE TABLE IF NOT EXISTS).
    store.initialize()
    rows = store.top_ten()
    assert len(rows) == 1
    assert rows[0].game_id == "g1"


def test_unique_game_id_rejects_duplicate(tmp_path):
    db = tmp_path / "hs.sqlite3"
    store = HighScoreStore(str(db))
    store.initialize()

    assert store.finalize(_rec("g1", 100, "2026-01-01T00:00:00+00:00")) is True
    # Second write for the same game_id is an idempotent duplicate (False), not
    # an error, and does not overwrite the original record.
    assert store.finalize(_rec("g1", 999, "2026-02-02T00:00:00+00:00", total_lines=9, level=5)) is False

    rows = store.top_ten()
    assert len(rows) == 1
    assert rows[0].score == 100
    assert rows[0].completed_at == "2026-01-01T00:00:00+00:00"


def test_new_store_instance_reads_persisted_rows(tmp_path):
    db = tmp_path / "hs.sqlite3"
    first = HighScoreStore(str(db))
    first.initialize()
    first.finalize(_rec("g1", 100, "2026-01-01T00:00:00+00:00"))

    # A freshly constructed store opening the same file reads prior rows
    # without reinitializing or clearing them.
    second = HighScoreStore(str(db))
    second.initialize()
    rows = second.top_ten()
    assert [r.game_id for r in rows] == ["g1"]


def test_from_env_default_and_override(tmp_path, monkeypatch):
    monkeypatch.delenv("TETRIS_DB_PATH", raising=False)
    assert HighScoreStore.from_env().db_path.endswith("high-scores.sqlite3")

    monkeypatch.setenv("TETRIS_DB_PATH", str(tmp_path / "custom.sqlite3"))
    assert HighScoreStore.from_env().db_path == str(tmp_path / "custom.sqlite3")

    # Empty / whitespace falls back to the default.
    monkeypatch.setenv("TETRIS_DB_PATH", "   ")
    assert HighScoreStore.from_env().db_path.endswith("high-scores.sqlite3")


def test_tie_break_ordering_and_ten_cap(tmp_path):
    db = tmp_path / "hs.sqlite3"
    store = HighScoreStore(str(db))
    store.initialize()

    # Equal scores: order by completed_at ASC, then game_id ASC.
    store.finalize(_rec("b", 500, "2026-01-01T00:00:02+00:00"))
    store.finalize(_rec("a", 500, "2026-01-01T00:00:01+00:00"))
    store.finalize(_rec("c", 500, "2026-01-01T00:00:02+00:00"))  # same time as b, id after b
    store.finalize(_rec("z", 900, "2026-01-01T00:00:05+00:00"))  # highest score first

    rows = store.top_ten()
    assert [r.game_id for r in rows] == ["z", "a", "b", "c"]

    # Cap at ten.
    for i in range(20):
        store.finalize(_rec(f"cap{i:02d}", 10, f"2026-03-01T00:00:{i:02d}+00:00"))
    assert len(store.top_ten()) == 10


def test_top_ten_raises_storage_error_on_broken_db(tmp_path):
    db = tmp_path / "hs.sqlite3"
    store = HighScoreStore(str(db))
    store.initialize()
    # Corrupt the file so sqlite fails on read.
    db.write_bytes(b"not a database")
    with pytest.raises(StorageError):
        store.top_ten()
