"""Independent Stage 1 acceptance smoke test for the isolated BMAD rerun."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "Bmad Method" / "backend"))

from app.core.domain import (  # noqa: E402
    ActivePiece,
    BOARD_COLS,
    BOARD_ROWS,
    Cell,
    GameState,
    clear_completed_lines,
    get_spawned_piece,
    is_valid_position,
    tick_game,
)
from app.main import app, sessions  # noqa: E402


def verify_domain() -> None:
    board = [[0] * BOARD_COLS for _ in range(BOARD_ROWS)]
    assert not is_valid_position(board, [Cell(row=0, col=-1)])
    assert not is_valid_position(board, [Cell(row=0, col=10)])
    assert not is_valid_position(board, [Cell(row=20, col=0)])
    board[8][5] = 1
    assert not is_valid_position(board, [Cell(row=8, col=5)])

    for count in range(1, 5):
        filled = [[0] * BOARD_COLS for _ in range(BOARD_ROWS)]
        filled[BOARD_ROWS - count :] = [[1] * BOARD_COLS for _ in range(count)]
        filled[BOARD_ROWS - count - 1][2] = 7
        cleared, actual = clear_completed_lines(filled)
        assert actual == count
        assert len(cleared) == BOARD_ROWS
        assert cleared[-1][2] == 7

    top_filled = [[0] * BOARD_COLS for _ in range(BOARD_ROWS)]
    top_filled[0] = [1] * BOARD_COLS
    top_cleared, top_count = clear_completed_lines(top_filled)
    assert top_count == 1
    assert all(cell == 0 for row in top_cleared for cell in row)

    piece = get_spawned_piece("O")
    piece = ActivePiece(
        shape="O",
        origin=Cell(row=18, col=4),
        cells=[Cell(row=18, col=4), Cell(row=18, col=5), Cell(row=19, col=4), Cell(row=19, col=5)],
    )
    lock_state = GameState(id="lock", status="playing", board=[[0] * BOARD_COLS for _ in range(BOARD_ROWS)], active_piece=piece)
    after_lock = tick_game(lock_state)
    assert after_lock.board[19][4] == 4 and after_lock.board[19][5] == 4
    assert after_lock.active_piece.cells != piece.cells

    blocked = [[0] * BOARD_COLS for _ in range(BOARD_ROWS)]
    for cell in get_spawned_piece("O").cells:
        blocked[cell.row][cell.col] = 1
    blocked_state = GameState(id="blocked", status="playing", board=blocked, active_piece=piece)
    assert tick_game(blocked_state).status == "game_over"


def verify_api() -> None:
    sessions.clear()
    with TestClient(app) as client:
        created = client.post("/api/games")
        assert created.status_code == 201
        state = created.json()
        game_id = state["id"]
        assert len(state["board"]) == 20
        assert all(len(row) == 10 for row in state["board"])
        assert len(state["active_piece"]["cells"]) == 4
        assert state["status"] == "playing"
        assert client.get(f"/api/games/{game_id}").status_code == 200
        assert client.post(f"/api/games/{game_id}/move", json={"direction": "left"}).status_code == 200
        assert client.post(f"/api/games/{game_id}/move", json={"direction": "rotate"}).status_code == 422
        assert client.post(f"/api/games/{game_id}/tick").status_code == 200
        assert client.get("/api/games/missing").status_code == 404
        restarted = client.post("/api/games")
        assert restarted.status_code == 201
        assert restarted.json()["id"] != game_id
        assert all(cell == 0 for row in restarted.json()["board"] for cell in row)
    sessions.clear()


if __name__ == "__main__":
    verify_domain()
    verify_api()
    print("Independent acceptance smoke test passed: grid, seven-shape state, borders/stack, lock, 1-4 line clears, game over, routes and restart.")
