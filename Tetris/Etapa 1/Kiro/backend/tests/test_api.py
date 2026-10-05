"""API contract tests using FastAPI's TestClient."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import store
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_store():
    store.reset()
    yield
    store.reset()


def test_create_game_returns_playing_state():
    resp = client.post("/api/games")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "playing"
    assert isinstance(data["id"], str) and data["id"]
    assert data["active_piece"] is not None


def test_created_board_is_20_by_10():
    data = client.post("/api/games").json()
    assert len(data["board"]) == 20
    assert all(len(row) == 10 for row in data["board"])


def test_read_game():
    game_id = client.post("/api/games").json()["id"]
    resp = client.get(f"/api/games/{game_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == game_id


def test_read_unknown_game_404():
    resp = client.get("/api/games/does-not-exist")
    assert resp.status_code == 404


def test_tick_advances_state():
    game_id = client.post("/api/games").json()["id"]
    before = client.get(f"/api/games/{game_id}").json()["active_piece"]["origin"]
    after = client.post(f"/api/games/{game_id}/tick").json()["active_piece"]["origin"]
    assert after[0] == before[0] + 1


def test_move_left_endpoint():
    game_id = client.post("/api/games").json()["id"]
    before = client.get(f"/api/games/{game_id}").json()["active_piece"]["origin"]
    after = client.post(f"/api/games/{game_id}/move", json={"direction": "left"}).json()
    assert after["active_piece"]["origin"][1] == before[1] - 1


def test_move_invalid_direction_422():
    game_id = client.post("/api/games").json()["id"]
    resp = client.post(f"/api/games/{game_id}/move", json={"direction": "up"})
    assert resp.status_code == 422


def test_move_missing_direction_422():
    game_id = client.post("/api/games").json()["id"]
    resp = client.post(f"/api/games/{game_id}/move", json={})
    assert resp.status_code == 422


def test_move_unknown_game_404():
    resp = client.post("/api/games/nope/move", json={"direction": "left"})
    assert resp.status_code == 404


def test_tick_unknown_game_404():
    resp = client.post("/api/games/nope/tick")
    assert resp.status_code == 404


def test_state_payload_shape():
    data = client.post("/api/games").json()
    assert set(data.keys()) == {"id", "status", "board", "active_piece"}
    ap = data["active_piece"]
    assert set(ap.keys()) == {"type", "origin", "cells"}
    assert ap["type"] in ["I", "O", "T", "S", "Z", "J", "L"]
    assert len(ap["origin"]) == 2
    assert len(ap["cells"]) == 4


def test_restart_creates_fresh_game():
    first = client.post("/api/games").json()["id"]
    second = client.post("/api/games").json()["id"]
    assert first != second
    data = client.get(f"/api/games/{second}").json()
    assert data["status"] == "playing"
    assert all(cell == 0 for row in data["board"] for cell in row) or data["active_piece"] is not None
