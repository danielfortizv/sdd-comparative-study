"""Stage 4 (Option A) M1 rotation API integration tests.

These are REAL HTTP route/payload tests for ``POST /api/games/{id}/rotate``.
Every case drives the production FastAPI app through ``TestClient`` (never the
pure engine directly) and reuses the inherited create-game flow and the shared
store accessor, mirroring the Stage 3 integration tests
(``tests/test_stage3_api.py``) and the shared isolation fixture
(``tests/conftest.py``, autouse ``_isolated_state``).

The rotate endpoint returns the eleven-key ``GameStateOut`` shape on success
(Req 1.3, 1.4), 422 for a malformed body (Req 1.6, 9.7), 404 for an unknown id
(Req 1.7), and is a state-preserving no-op on a ``game_over`` game (Req 1.8) or
a game with no active piece (Req 1.9). A rotation on a playing game must not
finalize it or touch the inherited leaderboard (Req 1.8, 9.6).
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app import store as game_store
from app.persistence.store import HighScoreStore
from app.api import deps

client = TestClient(app)

# The exact eleven-key GameStateOut contract shared by every game endpoint.
ELEVEN_KEYS = {
    "id",
    "status",
    "board",
    "active_piece",
    "score",
    "total_lines",
    "level",
    "gravity_interval_ms",
    "next_piece",
    "hold_piece",
    "can_hold",
}

# Fields that are authoritative game state: a rejected/no-op/422/404 rotate must
# never change any of these.
AUTHORITATIVE_FIELDS = (
    "status",
    "board",
    "active_piece",
    "score",
    "total_lines",
    "level",
    "gravity_interval_ms",
    "next_piece",
    "hold_piece",
    "can_hold",
)


def _use_real_store(tmp_path):
    """Install a real, initialized high-score store for a test and return it.

    The autouse ``_isolated_state`` fixture already points ``TETRIS_DB_PATH`` at
    a fresh temp file and resets the store accessor; this makes the store
    explicit so leaderboard assertions read a known, empty baseline.
    """

    store = HighScoreStore(str(tmp_path / "hs.sqlite3"))
    store.initialize()
    deps.set_high_score_store(store)
    return store


def _new_game_id():
    resp = client.post("/api/games")
    assert resp.status_code == 200
    return resp.json()["id"]


def _get_state(game_id):
    resp = client.get(f"/api/games/{game_id}")
    assert resp.status_code == 200
    return resp.json()


def _drive_to_game_over(game_id):
    """Obstruct the spawn region on the in-memory game, then tick to terminal.

    Mirrors the Stage 3 integration approach: fill the spawn cells (rows 0-1,
    columns 3-6) so the next spawn is obstructed but no row is complete, then
    tick through the production path until the game reports ``game_over``.
    """

    game = game_store.get(game_id)
    for r in range(2):
        for c in range(3, 7):
            game.board[r][c] = "I"
    resp = client.post(f"/api/games/{game_id}/tick")
    # The tick that spawns into the obstructed region ends the game.
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "game_over"
    return body


# --- Req 1.3, 1.4: accepted rotation -> HTTP 200 and exact eleven-key shape ---

def test_accepted_rotation_returns_200_and_exact_eleven_key_shape(tmp_path):
    _use_real_store(tmp_path)
    gid = _new_game_id()

    cw = client.post(f"/api/games/{gid}/rotate", json={"direction": "cw"})
    assert cw.status_code == 200
    body = cw.json()
    assert set(body.keys()) == ELEVEN_KEYS
    assert body["id"] == gid
    assert body["status"] == "playing"

    ccw = client.post(f"/api/games/{gid}/rotate", json={"direction": "ccw"})
    assert ccw.status_code == 200
    ccw_body = ccw.json()
    assert set(ccw_body.keys()) == ELEVEN_KEYS
    assert ccw_body["status"] == "playing"


# --- Req 1.8: rotation on a game_over game is a state-preserving no-op ---

def test_rotation_on_game_over_is_noop_200(tmp_path):
    _use_real_store(tmp_path)
    gid = _new_game_id()

    before = _drive_to_game_over(gid)
    assert before["status"] == "game_over"
    # A terminal game has no active piece (covers Req 1.9 via the public API).
    assert before["active_piece"] is None

    # Match the inherited terminal convention: mutating routes no-op with 200.
    for direction in ("cw", "ccw"):
        resp = client.post(f"/api/games/{gid}/rotate", json={"direction": direction})
        assert resp.status_code == 200
        after = resp.json()
        assert set(after.keys()) == ELEVEN_KEYS
        assert after["status"] == "game_over"
        for field in AUTHORITATIVE_FIELDS:
            assert after[field] == before[field], f"rotate changed {field} on game_over"


# --- Req 1.9: no active piece -> rotation leaves state unchanged ---

def test_rotation_with_no_active_piece_is_noop(tmp_path):
    """Via the public API, ``active_piece`` is only null once the game is
    terminal, so this is exercised through the game_over path: with
    ``active_piece`` absent a rotate changes no authoritative field."""

    _use_real_store(tmp_path)
    gid = _new_game_id()
    before = _drive_to_game_over(gid)
    assert before["active_piece"] is None

    resp = client.post(f"/api/games/{gid}/rotate", json={"direction": "cw"})
    assert resp.status_code == 200
    after = resp.json()
    assert after["active_piece"] is None
    for field in AUTHORITATIVE_FIELDS:
        assert after[field] == before[field]


# --- Req 1.6, 9.7: malformed bodies -> HTTP 422, state unchanged ---

MALFORMED_BODIES = [
    ("missing_direction", {}),
    ("extra_field", {"direction": "cw", "foo": 1}),
    ("bool_direction", {"direction": True}),
    ("int_direction", {"direction": 1}),
    ("float_direction", {"direction": 1.0}),
    ("wrong_string_up", {"direction": "up"}),
    ("uppercase_cw", {"direction": "CW"}),
    ("list_direction", {"direction": ["cw"]}),
    ("object_direction", {"direction": {"x": 1}}),
    ("null_direction", {"direction": None}),
]


def test_malformed_rotate_bodies_return_422_and_do_not_change_state(tmp_path):
    _use_real_store(tmp_path)
    gid = _new_game_id()
    before = _get_state(gid)

    for name, payload in MALFORMED_BODIES:
        resp = client.post(f"/api/games/{gid}/rotate", json=payload)
        assert resp.status_code == 422, f"{name}: expected 422, got {resp.status_code}"
        after = _get_state(gid)
        for field in AUTHORITATIVE_FIELDS:
            assert after[field] == before[field], f"{name}: rotate changed {field}"


# --- Req 1.7: unknown game id -> HTTP 404 ---

def test_rotate_unknown_game_id_returns_404(tmp_path):
    _use_real_store(tmp_path)
    resp = client.post("/api/games/does-not-exist/rotate", json={"direction": "cw"})
    assert resp.status_code == 404


# --- Req 1.8, 9.6: rotating a playing game never finalizes / touches leaderboard ---

def test_rotation_on_playing_game_does_not_finalize_or_touch_leaderboard(tmp_path):
    _use_real_store(tmp_path)
    gid = _new_game_id()

    # Baseline: a fresh, playing game has written no high-score entry.
    hs_before = client.get("/api/high-scores")
    assert hs_before.status_code == 200
    assert len(hs_before.json()["scores"]) == 0

    before = _get_state(gid)
    assert before["status"] == "playing"

    resp = client.post(f"/api/games/{gid}/rotate", json={"direction": "cw"})
    assert resp.status_code == 200
    after = resp.json()

    # The game is still playing and was not finalized.
    assert after["status"] == "playing"
    # Rotation advances neither the queue nor Hold, and never changes the score.
    assert after["next_piece"] == before["next_piece"]
    assert after["hold_piece"] == before["hold_piece"]
    assert after["can_hold"] == before["can_hold"]
    assert after["score"] == before["score"]
    assert after["total_lines"] == before["total_lines"]
    assert after["level"] == before["level"]

    # No high-score entry was created by rotating a playing game.
    hs_after = client.get("/api/high-scores")
    assert hs_after.status_code == 200
    assert len(hs_after.json()["scores"]) == 0
