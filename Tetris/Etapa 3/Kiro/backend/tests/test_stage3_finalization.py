"""Stage 3 unit tests for the finalization service.

Covers the happy path and zero-score finalization (task 3.2) and finalize-once
idempotency plus UNIQUE/concurrency dedup (task 3.3). The tests assume the
caller holds the service lock (as the controller does); they call the service
functions directly under that contract.
"""

from __future__ import annotations

import threading

import pytest

from app.domain.models import COLS, Game, empty_board
from app.rules import engine
from app.persistence.store import HighScoreRecord, HighScoreStore, StorageError
from app.service import finalization


def _store(tmp_path):
    s = HighScoreStore(str(tmp_path / "hs.sqlite3"))
    s.initialize()
    return s


def _force_game_over(game: Game) -> None:
    """Drive a real game to game_over by obstructing the spawn region.

    Fills the spawn cells (rows 0-1, columns 3-6) so any spawn at the canonical
    origin is obstructed, while leaving other columns empty so NO row is
    complete (avoiding a line clear). Then runs the real engine spawn, which
    transitions the game to game_over through the production code path.
    """

    for r in range(2):
        for c in range(3, 7):
            game.board[r][c] = "I"
    engine.spawn(game)


def test_finalize_happy_path_writes_one_record(tmp_path):
    store = _store(tmp_path)
    game = engine.new_game("g-happy", seed=1)
    with finalization._LOCK:
        finalization.run_mutation(game, _force_game_over, store)

    assert game.status == "game_over"
    assert game.finalized is True
    assert game.pending_finalization is False
    rows = store.top_ten()
    assert len(rows) == 1
    r = rows[0]
    assert r.game_id == "g-happy"
    assert r.score == game.score
    assert r.total_lines == game.total_lines
    assert r.level == game.level
    assert r.completed_at == game.completed_at
    # completed_at is a UTC ISO-8601 string.
    assert r.completed_at.endswith("+00:00")


def test_zero_score_still_finalized(tmp_path):
    store = _store(tmp_path)
    game = engine.new_game("g-zero", seed=2)
    # Do not clear any line, so score stays 0.
    with finalization._LOCK:
        finalization.run_mutation(game, _force_game_over, store)
    assert game.score == 0
    rows = store.top_ten()
    assert len(rows) == 1
    assert rows[0].score == 0


def test_repeated_terminal_mutations_keep_one_record(tmp_path):
    store = _store(tmp_path)
    game = engine.new_game("g-rep", seed=3)
    with finalization._LOCK:
        finalization.run_mutation(game, _force_game_over, store)
        first_completed = game.completed_at
        # Repeated mutating requests on the terminal game: no-op engine calls,
        # already finalized -> no duplicate, unchanged fields.
        finalization.run_mutation(game, engine.tick, store)
        finalization.run_mutation(game, lambda g: engine.move(g, "left"), store)
    rows = store.top_ten()
    assert len(rows) == 1
    assert rows[0].completed_at == first_completed
    assert game.completed_at == first_completed


def test_still_playing_game_not_recorded(tmp_path):
    store = _store(tmp_path)
    game = engine.new_game("g-play", seed=4)
    with finalization._LOCK:
        finalization.run_mutation(game, engine.tick, store)
    assert game.status == "playing"
    assert store.top_ten() == []


def test_concurrent_finalization_one_record(tmp_path):
    store = _store(tmp_path)
    game = engine.new_game("g-conc", seed=5)
    # Pre-drive to terminal and capture the record once (under the lock).
    with finalization._LOCK:
        # Capture the terminal state and record but simulate the write failing
        # the first time is not needed here; instead test that two threads both
        # entering finalization resolve to one row via the gate + UNIQUE.
        _force_game_over(game)

    errors = []

    def worker():
        try:
            with finalization._LOCK:
                finalization._finalize_if_needed(game, store)
        except Exception as exc:  # pragma: no cover - defensive
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    assert len(store.top_ten()) == 1


def test_non_duplicate_storage_failure_surfaces(tmp_path):
    """A non-game_id storage failure is not swallowed as a duplicate."""

    game = engine.new_game("g-fail", seed=6)

    class FailingStore:
        def finalize(self, record):
            raise StorageError("high-score storage is unavailable")

    failing_store = FailingStore()
    finalization._LOCK.acquire()
    try:
        # Non-throwing setup is performed OUTSIDE pytest.raises so the exception
        # block wraps only the single intended throwing invocation (Sonar S5778).
        _force_game_over(game)
        with pytest.raises(StorageError):
            finalization._finalize_if_needed(game, failing_store)
    finally:
        finalization._LOCK.release()

    assert game.finalized is False
    assert game.pending_finalization is True
    assert game.finalization_record is not None

