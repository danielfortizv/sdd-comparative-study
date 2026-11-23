import pytest
from fastapi.testclient import TestClient
from typing import List, Optional

from app.main import app
from app.models.game import GameStateModel, ActivePieceModel
from app.controllers.games import GAMES
from app.domain.rules import is_legal_position, lock_piece, clear_lines, tick_game, move_game
from app.domain.pieces import get_relative_cells

client = TestClient(app)

def test_grid_dimensions():
    # Req-1: Grid must have 10 columns and 20 rows.
    # Req-2: coordinate (row, col) row ranges from 0 to 19, col ranges from 0 to 9.
    response = client.post("/api/games")
    assert response.status_code == 200
    data = response.json()
    board = data["board"]
    assert len(board) == 20
    for row in board:
        assert len(row) == 10
        for cell in row:
            assert cell is None

def test_spawning_and_coordinate_calculations():
    # Req-7: a new random piece spawns at top.
    # Req-8: default spawn origin is (0, 3).
    response = client.post("/api/games")
    assert response.status_code == 200
    data = response.json()
    active_piece = data["active_piece"]
    assert active_piece is not None
    assert active_piece["origin"] == [0, 3] or active_piece["origin"] == (0, 3)
    
    # Calculate absolute coordinates from pieces.py and verify active_piece cells
    piece_type = active_piece["type"]
    relative_cells = get_relative_cells(piece_type)
    expected_cells = [[0 + r, 3 + c] for r, c in relative_cells]
    # Check cells match expected absolute coordinates
    assert active_piece["cells"] == expected_cells

def test_legal_shifts_and_border_collisions():
    # Create game
    response = client.post("/api/games")
    game_id = response.json()["id"]
    
    # Force state to have piece 'O' (which has shape [(0, 0), (0, 1), (1, 0), (1, 1)])
    # Origin at (0, 3) -> cells: (0, 3), (0, 4), (1, 3), (1, 4)
    state = GAMES[game_id]
    state.active_piece = ActivePieceModel(
        type='O',
        origin=(0, 3),
        cells=[(0, 3), (0, 4), (1, 3), (1, 4)]
    )
    
    # Move left -> success, origin should be (0, 2)
    response = client.post(f"/api/games/{game_id}/move", json={"direction": "left"})
    assert response.status_code == 200
    data = response.json()
    assert data["active_piece"]["origin"] == [0, 2]
    assert data["active_piece"]["cells"] == [[0, 2], [0, 3], [1, 2], [1, 3]]
    
    # Shift multiple times left to hit left boundary (col=0)
    # col=2 -> col=1 -> col=0 -> tries col=-1 (illegal, ignored)
    client.post(f"/api/games/{game_id}/move", json={"direction": "left"}) # to (0, 1)
    client.post(f"/api/games/{game_id}/move", json={"direction": "left"}) # to (0, 0)
    # This next left shift is illegal and should be ignored (keep origin at [0, 0])
    response = client.post(f"/api/games/{game_id}/move", json={"direction": "left"})
    assert response.json()["active_piece"]["origin"] == [0, 0]
    
    # Now shift right to right boundary (col=8 because 'O' has width 2, so rightmost block is col+1, if col=8, rightmost block is 9)
    # col=0 -> 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9 (illegal, because right cell is col+1 which would be 10, illegal)
    for _ in range(8):
        client.post(f"/api/games/{game_id}/move", json={"direction": "right"})
        
    response = client.post(f"/api/games/{game_id}/move", json={"direction": "right"})
    assert response.json()["active_piece"]["origin"] == [0, 8]
    
    # Try one more right (col=9 is illegal)
    response = client.post(f"/api/games/{game_id}/move", json={"direction": "right"})
    assert response.json()["active_piece"]["origin"] == [0, 8]

def test_stack_collisions():
    response = client.post("/api/games")
    game_id = response.json()["id"]
    state = GAMES[game_id]
    
    # Settle a block at (2, 3)
    state.board[2][3] = 'I'
    
    # Put active piece 'I' (shape [(0,0), (0,1), (0,2), (0,3)]) at (1, 3) -> cells (1,3), (1,4), (1,5), (1,6)
    # Downward move would make cells (2,3), (2,4), (2,5), (2,6) -> overlaps with (2,3), which is illegal
    state.active_piece = ActivePieceModel(
        type='I',
        origin=(1, 3),
        cells=[(1, 3), (1, 4), (1, 5), (1, 6)]
    )
    
    # Executing tick should trigger locking instead of moving down
    response = client.post(f"/api/games/{game_id}/tick")
    data = response.json()
    # Active piece at (1,3) should be locked in board, active_piece field is cleared or new piece spawned, board should have 'I' at (1,3)..(1,6)
    assert data["board"][1][3] == 'I'
    assert data["board"][1][4] == 'I'
    assert data["board"][1][5] == 'I'
    assert data["board"][1][6] == 'I'

def test_downward_locking_and_line_clearing():
    response = client.post("/api/games")
    game_id = response.json()["id"]
    state = GAMES[game_id]
    
    # Clear board
    state.board = [[None] * 10 for _ in range(20)]
    
    # Fill row 19 except columns 5 and 6
    for col in range(10):
        if col not in (5, 6):
            state.board[19][col] = 'S'
            
    # Set active piece 'O' at origin (18, 5) -> cells (18, 5), (18, 6), (19, 5), (19, 6)
    state.active_piece = ActivePieceModel(
        type='O',
        origin=(18, 5),
        cells=[(18, 5), (18, 6), (19, 5), (19, 6)]
    )
    
    # Tick down -> since moving down would put cells at row 20 (illegal), it locks at current position (18, 5)
    response = client.post(f"/api/games/{game_id}/tick")
    data = response.json()
    
    # Row 19 is fully filled and should be cleared!
    # Since row 19 is cleared, the cells from row 18 shift down.
    # The piece 'O' had blocks at (18, 5) and (18, 6).
    # After line 19 is cleared, row 18 blocks shift down to row 19.
    # So board[19][5] and board[19][6] should be 'O', while row 18 is completely cleared.
    assert data["board"][19][5] == 'O'
    assert data["board"][19][6] == 'O'
    for col in range(10):
        if col not in (5, 6):
            assert data["board"][19][col] is None  # Since the other blocks were at row 19 and got cleared
    # Row 18 should be empty
    assert all(cell is None for cell in data["board"][18])

def test_multiple_lines_clearing():
    response = client.post("/api/games")
    game_id = response.json()["id"]
    state = GAMES[game_id]
    state.board = [[None] * 10 for _ in range(20)]
    
    # Complete rows 18 and 19 except column 5 and 6
    for col in range(10):
        if col not in (5, 6):
            state.board[18][col] = 'T'
            state.board[19][col] = 'T'
            
    # Set active piece 'O' at (18, 5)
    # cells: (18, 5), (18, 6), (19, 5), (19, 6)
    # Locking this piece completes BOTH rows 18 and 19!
    state.active_piece = ActivePieceModel(
        type='O',
        origin=(18, 5),
        cells=[(18, 5), (18, 6), (19, 5), (19, 6)]
    )
    
    response = client.post(f"/api/games/{game_id}/tick")
    data = response.json()
    
    # Both rows 18 and 19 are cleared.
    # Since both are cleared, row 18 and 19 should be completely empty (all None)
    assert all(cell is None for cell in data["board"][19])
    assert all(cell is None for cell in data["board"][18])

def test_game_over_state_trigger_on_spawn_overlap():
    response = client.post("/api/games")
    game_id = response.json()["id"]
    state = GAMES[game_id]
    state.board = [[None] * 10 for _ in range(20)]
    
    # Fill columns 3,4,5,6 on rows 0 and 1.
    # This guarantees that any random tetromino spawned at (0,3) will overlap with these blocked cells,
    # but since the rows are not completely filled, they won't be cleared by clear_lines.
    for r in (0, 1):
        for c in (3, 4, 5, 6):
            state.board[r][c] = 'Z'
    
    # Put active piece at (19, 3) and make it lock, so a new spawn is triggered
    state.active_piece = ActivePieceModel(
        type='I',
        origin=(19, 3),
        cells=[(19, 3), (19, 4), (19, 5), (19, 6)]
    )
    
    # This move down will trigger locking because (19, 3)..(19, 6) is empty but row 20 is illegal,
    # then line clear (none), then try to spawn a new piece.
    # Since board[0][3] has 'Z', spawning is illegal, transitioning to game_over.
    response = client.post(f"/api/games/{game_id}/tick")
    data = response.json()
    assert data["status"] == "game_over"
    assert data["active_piece"] is None

def test_game_over_state_trigger_on_tick_at_row_zero():
    # Req-26: "The game status MUST transition from 'playing' to 'game_over' if,
    # at the time of a gravity tick, the active piece is already locked at row 0 and cannot move down."
    response = client.post("/api/games")
    game_id = response.json()["id"]
    state = GAMES[game_id]
    state.board = [[None] * 10 for _ in range(20)]
    
    # Settle blocks below row 0, e.g., row 1 is full of blocks so piece at row 0 cannot move down
    for col in range(10):
        state.board[1][col] = 'S'
        
    # Active piece at row 0 (origin (0, 3))
    # 'I' has shape [(0, 0), (0, 1), (0, 2), (0, 3)] -> cells at (0, 3), (0, 4), (0, 5), (0, 6)
    state.active_piece = ActivePieceModel(
        type='I',
        origin=(0, 3),
        cells=[(0, 3), (0, 4), (0, 5), (0, 6)]
    )
    
    # It cannot move down to row 1 because row 1 is filled with 'S'.
    # This should trigger locking at row 0, and since it locks at row 0 and cannot move down, status becomes game_over.
    response = client.post(f"/api/games/{game_id}/tick")
    data = response.json()
    assert data["status"] == "game_over"
    assert data["active_piece"] is None

def test_game_over_ignores_commands():
    # Req-27: While the game is in "game_over" status, any tick or movement commands MUST be ignored,
    # and the API must return the current state with "game_over" status.
    response = client.post("/api/games")
    game_id = response.json()["id"]
    state = GAMES[game_id]
    state.status = "game_over"
    state.active_piece = None
    
    # Try tick
    response = client.post(f"/api/games/{game_id}/tick")
    assert response.json()["status"] == "game_over"
    
    # Try move left
    response = client.post(f"/api/games/{game_id}/move", json={"direction": "left"})
    assert response.json()["status"] == "game_over"
