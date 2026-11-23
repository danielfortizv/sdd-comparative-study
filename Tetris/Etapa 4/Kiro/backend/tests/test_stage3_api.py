"""Stage 3 API integration tests.

Covers failure/recovery/GET-purity (task 4.3), the exact leaderboard contract
and read-side 503 (task 5.3), injection-like input rejection (task 5.4), and
CORS/startup wiring (task 6.2). Tests drive the production app through
FastAPI's TestClient and inject stores via the shared accessor.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api import deps
from app import store as game_store
from app.domain.models import COLS
from app.persistence.store import HighScoreStore, StorageError
from app.rules import engine

client = TestClient(app)

STORAGE_MESSAGE_FORBIDDEN = ("/", "\\", "sqlite", "SELECT", "INSERT", "Traceback", "Error", "Exception")


def _obstruct_and_make_terminal(game):
    """Obstruct the spawn region (no line clear) so the next spawn ends the game."""

    for r in range(2):
        for c in range(3, 7):
            game.board[r][c] = "I"


def _new_game_id():
    resp = client.post("/api/games")
    assert resp.status_code == 200
    return resp.json()["id"]


class _FailOnceStore:
    """Store that raises StorageError on the first finalize, then delegates."""

    def __init__(self, real):
        self._real = real
        self.calls = 0
        self.attempted = []

    def finalize(self, record):
        self.calls += 1
        self.attempted.append(record)
        if self.calls == 1:
            raise StorageError("high-score storage is unavailable")
        return self._real.finalize(record)

    def top_ten(self):
        return self._real.top_ten()

    def initialize(self):
        return self._real.initialize()


class _AlwaysFailStore:
    def finalize(self, record):
        raise StorageError("high-score storage is unavailable")

    def top_ten(self):
        raise StorageError("high-score storage is unavailable")

    def initialize(self):
        return None


def _drive_terminal_via_api(game_id):
    """Fill the spawn region on the in-memory game, then tick to end it."""

    game = game_store.get(game_id)
    _obstruct_and_make_terminal(game)
    return client.post(f"/api/games/{game_id}/tick")


# --- Task 4.3: failure, recovery, GET purity (frozen snapshot) ---

def test_failure_then_recovery_same_record(tmp_path):
    real = HighScoreStore(str(tmp_path / "hs.sqlite3"))
    real.initialize()
    fail_once = _FailOnceStore(real)
    deps.set_high_score_store(fail_once)

    gid = _new_game_id()
    # First terminal attempt fails -> controlled 503.
    resp = _drive_terminal_via_api(gid)
    assert resp.status_code == 503
    assert resp.headers["content-type"].startswith("application/json")
    body = resp.json()
    assert "detail" in body
    msg = body["detail"]
    assert "storage" in msg.lower()
    for forbidden in STORAGE_MESSAGE_FORBIDDEN:
        assert forbidden not in msg

    # Game stays terminal and pending.
    game = game_store.get(gid)
    assert game.status == "game_over"
    assert game.pending_finalization is True
    assert game.finalized is False
    captured = game.finalization_record
    assert captured is not None

    # A GET during the pending window never retries, never writes, never
    # changes pending status.
    get_resp = client.get(f"/api/games/{gid}")
    assert get_resp.status_code == 200
    assert game.pending_finalization is True
    assert fail_once.calls == 1  # GET did not attempt another write
    assert real.top_ten() == []

    # A later mutating request retries and succeeds.
    retry = client.post(f"/api/games/{gid}/tick")
    assert retry.status_code == 200
    assert game.finalized is True
    assert game.pending_finalization is False

    # Exactly one record, and it is byte-for-byte the SAME captured record:
    # completed_at was NOT regenerated at retry time.
    rows = real.top_ten()
    assert len(rows) == 1
    assert fail_once.attempted[0] == fail_once.attempted[1]
    assert rows[0].completed_at == captured.completed_at
    assert rows[0].game_id == captured.game_id
    assert rows[0].score == captured.score


# --- Task 5.3: exact leaderboard contract and read-side 503 ---

def test_leaderboard_empty_contract(tmp_path):
    real = HighScoreStore(str(tmp_path / "hs.sqlite3"))
    real.initialize()
    deps.set_high_score_store(real)
    resp = client.get("/api/high-scores")
    assert resp.status_code == 200
    assert resp.json() == {"scores": []}


def test_leaderboard_entry_has_exactly_five_fields(tmp_path):
    from app.persistence.store import HighScoreRecord

    real = HighScoreStore(str(tmp_path / "hs.sqlite3"))
    real.initialize()
    real.finalize(HighScoreRecord("g1", 100, 3, 2, "2026-01-01T00:00:00+00:00"))
    deps.set_high_score_store(real)
    resp = client.get("/api/high-scores")
    assert resp.status_code == 200
    scores = resp.json()["scores"]
    assert len(scores) == 1
    assert set(scores[0].keys()) == {"game_id", "score", "total_lines", "level", "completed_at"}


def test_leaderboard_read_503(tmp_path):
    deps.set_high_score_store(_AlwaysFailStore())
    resp = client.get("/api/high-scores")
    assert resp.status_code == 503
    assert resp.headers["content-type"].startswith("application/json")
    msg = resp.json()["detail"]
    assert "storage" in msg.lower()
    for forbidden in STORAGE_MESSAGE_FORBIDDEN:
        assert forbidden not in msg


# --- Task 5.4: injection-like input rejection ---

def test_create_rejects_extra_body_fields(tmp_path):
    deps.set_high_score_store(HighScoreStore(str(tmp_path / "hs.sqlite3")))
    deps.get_high_score_store().initialize()
    resp = client.post("/api/games", json={"score": 9999, "game_id": "forged"})
    assert resp.status_code == 422


def test_bodyless_create_still_200(tmp_path):
    deps.set_high_score_store(HighScoreStore(str(tmp_path / "hs.sqlite3")))
    deps.get_high_score_store().initialize()
    resp = client.post("/api/games")
    assert resp.status_code == 200


def test_move_rejects_extra_fields_and_bad_direction(tmp_path):
    deps.set_high_score_store(HighScoreStore(str(tmp_path / "hs.sqlite3")))
    deps.get_high_score_store().initialize()
    gid = _new_game_id()
    assert client.post(f"/api/games/{gid}/move", json={"direction": "left", "score": 1}).status_code == 422
    assert client.post(f"/api/games/{gid}/move", json={"direction": "up"}).status_code == 422
    assert client.post(f"/api/games/{gid}/move", json={"direction": "left"}).status_code == 200


def test_unknown_game_404(tmp_path):
    deps.set_high_score_store(HighScoreStore(str(tmp_path / "hs.sqlite3")))
    deps.get_high_score_store().initialize()
    assert client.post("/api/games/does-not-exist/tick").status_code == 404
    assert client.get("/api/games/does-not-exist").status_code == 404


# --- Task 6.2: CORS policy and startup init ---

def test_cors_configurable_no_wildcard_with_credentials(monkeypatch):
    from app.main import _resolve_allowed_origins

    monkeypatch.setenv("TETRIS_ALLOWED_ORIGINS", "https://a.example,https://b.example")
    origins = _resolve_allowed_origins()
    assert origins == ["https://a.example", "https://b.example"]
    assert "*" not in origins


def test_startup_lifespan_initializes_store(tmp_path, monkeypatch):
    monkeypatch.setenv("TETRIS_DB_PATH", str(tmp_path / "hs.sqlite3"))
    deps.reset_high_score_store()
    with TestClient(app) as c:
        resp = c.get("/api/high-scores")
        assert resp.status_code == 200
        assert resp.json() == {"scores": []}


# --- Round 04: CORS wildcard-with-credentials fail-closed (Req 10.3-10.7) ---

def test_cors_default_is_restrictive_local_dev(monkeypatch):
    """Unset TETRIS_ALLOWED_ORIGINS -> restrictive local-dev default, no wildcard."""

    from app.main import _resolve_allowed_origins

    monkeypatch.delenv("TETRIS_ALLOWED_ORIGINS", raising=False)
    origins = _resolve_allowed_origins()
    assert origins == ["http://localhost:5173", "http://127.0.0.1:5173"]
    assert "*" not in origins


def test_cors_empty_value_falls_back_to_default(monkeypatch):
    from app.main import _resolve_allowed_origins

    monkeypatch.setenv("TETRIS_ALLOWED_ORIGINS", "   ")
    origins = _resolve_allowed_origins()
    assert origins == ["http://localhost:5173", "http://127.0.0.1:5173"]
    assert "*" not in origins


def test_cors_explicit_allow_list_is_preserved(monkeypatch):
    """A valid explicit allow-list still works and keeps credentials usable."""

    from app.main import _resolve_allowed_origins

    monkeypatch.setenv("TETRIS_ALLOWED_ORIGINS", " https://a.example , https://b.example ")
    origins = _resolve_allowed_origins()
    assert origins == ["https://a.example", "https://b.example"]
    assert "*" not in origins


def test_cors_pure_wildcard_is_rejected(monkeypatch):
    """A lone '*' with credentials enabled is rejected (fail closed)."""

    from app.main import _resolve_allowed_origins, CORSConfigurationError

    monkeypatch.setenv("TETRIS_ALLOWED_ORIGINS", "*")
    with pytest.raises(CORSConfigurationError):
        _resolve_allowed_origins()


def test_cors_mixed_list_with_wildcard_is_rejected(monkeypatch):
    """A mixed list containing '*' with credentials is rejected (fail closed)."""

    from app.main import _resolve_allowed_origins, CORSConfigurationError

    monkeypatch.setenv("TETRIS_ALLOWED_ORIGINS", "https://app.example,*")
    with pytest.raises(CORSConfigurationError):
        _resolve_allowed_origins()


def test_cors_middleware_never_reflects_arbitrary_origin_with_credentials(monkeypatch):
    """A credentialed app built from the resolved allow-list never grants '*'.

    Builds an isolated FastAPI app that applies the SAME CORS policy shape as
    production (credentials enabled, origins from _resolve_allowed_origins) so
    the live behavior is exercised without mutating the shared app module. An
    arbitrary (untrusted) origin must not receive a credentialed grant and the
    allowed origin must be echoed exactly (never '*').
    """

    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    from app.main import _resolve_allowed_origins

    monkeypatch.setenv("TETRIS_ALLOWED_ORIGINS", "https://allowed.example")
    probe = FastAPI()
    probe.add_middleware(
        CORSMiddleware,
        allow_origins=_resolve_allowed_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @probe.get("/api/high-scores")
    def _hs() -> dict:
        return {"scores": []}

    c = TestClient(probe)

    # Untrusted origin: no credentialed CORS grant, never '*'.
    resp = c.options(
        "/api/high-scores",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"},
    )
    acao = resp.headers.get("access-control-allow-origin")
    assert acao != "*"
    assert acao != "https://evil.example"

    # Allowed origin: echoed exactly with credentials.
    resp2 = c.options(
        "/api/high-scores",
        headers={"Origin": "https://allowed.example", "Access-Control-Request-Method": "GET"},
    )
    assert resp2.headers.get("access-control-allow-origin") == "https://allowed.example"
    assert resp2.headers.get("access-control-allow-credentials") == "true"
