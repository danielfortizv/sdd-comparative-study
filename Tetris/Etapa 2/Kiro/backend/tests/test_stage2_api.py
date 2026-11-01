"""Stage 2 Hold mechanics and API contract tests (Req 1,6,8,10,11,12)."""

from __future__ import annotations

import random

import pytest
from fastapi.testclient import TestClient

from app import store
from app.domain.models import COLS, ActivePiece, Game, empty_board
from app.main import app
from app.rules import engine, pieces

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_store():
    store.reset()
    yield
    store.reset()


def craft_game(seed: int = 1) -> Game:
    rng = random.Random(seed)
    game = Game(
        id="test",
        status="playing",
        board=empty_board(),
        active=None,
        rng=rng,
        seed=seed,
        bag=[],
    )
    game.next_type = engine._draw_preview(game)
    return game


# --- New game initial counters (Req 1) ---

def test_new_game_initial_counters():
    data = client.post("/api/games").json()
    assert data["score"] == 0
    assert data["total_lines"] == 0
    assert data["level"] == 1
    assert data["gravity_interval_ms"] == 500
    assert data["hold_piece"] is None
    assert data["can_hold"] is True
    assert data["next_piece"] in ["I", "O", "T", "S", "Z", "J", "L"]


# --- Expanded response contract (Req 6, 12) ---

def test_state_payload_includes_stage2_fields():
    data = client.post("/api/games").json()
    assert set(data.keys()) == {
        "id", "status", "board", "active_piece",
        "score", "total_lines", "level", "gravity_interval_ms",
        "next_piece", "hold_piece", "can_hold",
    }


def test_create_returns_http_200():
    assert client.post("/api/games").status_code == 200


def test_board_remains_integer_coded():
    data = client.post("/api/games").json()
    assert all(isinstance(cell, int) for row in data["board"] for cell in row)


def test_active_piece_key_and_spawn_origin():
    data = client.post("/api/games").json()
    assert data["active_piece"] is not None
    assert data["active_piece"]["origin"] == [0, 3]


def test_next_piece_types_valid():
    data = client.post("/api/games").json()
    assert data["next_piece"] in ["I", "O", "T", "S", "Z", "J", "L"]
    assert data["can_hold"] in (True, False)


# --- State read purity (Req 6.5, 10.3) ---

def test_repeated_get_does_not_change_state():
    game_id = client.post("/api/games").json()["id"]
    first = client.get(f"/api/games/{game_id}").json()
    for _ in range(5):
        again = client.get(f"/api/games/{game_id}").json()
        assert again == first


# --- Hold endpoint: empty slot (Req 8.1) ---

def test_hold_empty_slot_moves_active_to_hold():
    created = client.post("/api/games").json()
    game_id = created["id"]
    active_type = created["active_piece"]["type"]
    next_type = created["next_piece"]
    after = client.post(f"/api/games/{game_id}/hold").json()
    assert after["hold_piece"] == active_type
    assert after["active_piece"]["type"] == next_type
    assert after["active_piece"]["origin"] == [0, 3]
    assert after["can_hold"] is False


# --- Hold endpoint: rejection when can_hold false (Req 8.4) ---

def test_hold_rejected_when_can_hold_false():
    game_id = client.post("/api/games").json()["id"]
    first = client.post(f"/api/games/{game_id}/hold").json()  # uses the hold
    assert first["can_hold"] is False
    second = client.post(f"/api/games/{game_id}/hold").json()  # rejected
    assert second == first


# --- Hold endpoint response shape (Req 8.8) ---

def test_hold_response_shape_matches_other_endpoints():
    game_id = client.post("/api/games").json()["id"]
    data = client.post(f"/api/games/{game_id}/hold").json()
    assert set(data.keys()) == {
        "id", "status", "board", "active_piece",
        "score", "total_lines", "level", "gravity_interval_ms",
        "next_piece", "hold_piece", "can_hold",
    }


# --- Hold endpoint: unknown id 404 (Req 8.6) ---

def test_hold_unknown_game_404():
    assert client.post("/api/games/nope/hold").status_code == 404


# --- Occupied-slot swap at engine level (Req 8.2, 7.3) ---

def test_hold_occupied_slot_swaps_without_consuming_preview():
    game = craft_game()
    game.active = ActivePiece("O", (0, 3), engine._absolute_cells("O", (0, 3)))
    engine.hold(game)                 # empty slot: hold O, bring in preview
    assert game.hold_type == "O"
    held_before = game.hold_type
    active_before = game.active.type
    next_before = game.next_type
    game.can_hold = True              # new active piece is holdable
    engine.hold(game)                 # occupied: swap, no preview draw
    assert game.active.type == held_before
    assert game.hold_type == active_before
    assert game.next_type == next_before
    assert game.can_hold is False


# --- can_hold re-enabled after a lock (Req 8.5) ---

def test_can_hold_re_enabled_after_lock():
    game = craft_game()
    game.active = ActivePiece("O", (18, 4), [(18, 4), (18, 5), (19, 4), (19, 5)])
    game.can_hold = False
    engine.lock(game)
    assert game.can_hold is True


# --- Incoming piece blocked at spawn origin -> game over (Req 8.3) ---

def test_hold_incoming_spawn_collision_ends_game():
    game = craft_game()
    # Occupy the spawn region so any incoming piece at (0,3) is obstructed.
    for col in range(COLS):
        game.board[0][col] = "I"
        game.board[1][col] = "I"
    # Active piece sits lower, outside the filled top region.
    game.active = ActivePiece("O", (5, 3), engine._absolute_cells("O", (5, 3)))
    game.hold_type = None
    game.can_hold = True
    engine.hold(game)
    assert game.status == "game_over"
    assert game.active is None


# --- No-op after game over (Req 8.7, 10.1) ---

def test_hold_noop_after_game_over():
    game = craft_game()
    game.status = "game_over"
    game.active = None
    before = (game.status, game.hold_type, game.next_type)
    engine.hold(game)
    after = (game.status, game.hold_type, game.next_type)
    assert after == before


# --- Scoring/leveling via the tick endpoint path (Req 12.3) ---

def test_tick_applies_scoring_on_clear():
    # Install a crafted game directly in the store with one row from complete.
    game = craft_game(seed=3)
    game.total_lines = 9
    game.level = 1
    for col in range(COLS):
        if col not in (4, 5):
            game.board[19][col] = "I"
    game.active = ActivePiece("O", (18, 4), [(18, 4), (18, 5), (19, 4), (19, 5)])
    store._games[game.id] = game
    # Tick down until it locks and clears the completed row.
    data = None
    for _ in range(5):
        data = client.post(f"/api/games/{game.id}/tick").json()
        if data["total_lines"] >= 10:
            break
    assert data["score"] == 100
    assert data["total_lines"] == 10
    assert data["level"] == 2
    assert data["gravity_interval_ms"] == 450
