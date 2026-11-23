import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.game import GameStateModel, ActivePieceModel
from app.controllers.games import GAMES
from app.domain.pieces import get_relative_cells, ORIENTATIONS
from app.domain.rules import rotate_game

client = TestClient(app)

def test_four_cycles_open_space():
    # Cover ALL 7 pieces / four orientations / both directions / four unobstructed cycles
    pieces = ['I', 'O', 'T', 'S', 'Z', 'J', 'L']
    board = [[None] * 10 for _ in range(20)]
    
    for pt in pieces:
        # Starting in Orientation 0
        state = GameStateModel(
            id="test-cycle",
            board=board,
            active_piece=ActivePieceModel(
                type=pt,
                origin=(5, 3),
                cells=[(5 + r, 3 + c) for r, c in get_relative_cells(pt, 0)],
                orientation=0
            ),
            status="playing",
            next_piece="I"
        )
        
        # Test Clockwise Cycle (0 -> 1 -> 2 -> 3 -> 0)
        # Verify exact relative coordinates sorted lexicographically
        for i in range(1, 5):
            state = rotate_game(state, 'cw')
            if pt == 'O':
                assert state.active_piece.orientation == 0
            else:
                expected_orientation = i % 4
                assert state.active_piece.orientation == expected_orientation
                
                expected_rel = sorted(get_relative_cells(pt, expected_orientation))
                actual_rel = sorted([(r - state.active_piece.origin[0], c - state.active_piece.origin[1]) 
                                     for r, c in state.active_piece.cells])
                assert actual_rel == expected_rel

        # Test Counterclockwise Cycle (0 -> 3 -> 2 -> 1 -> 0)
        state.active_piece.orientation = 0
        state.active_piece.cells = [(5 + r, 3 + c) for r, c in get_relative_cells(pt, 0)]
        
        for i in range(1, 5):
            state = rotate_game(state, 'ccw')
            if pt == 'O':
                assert state.active_piece.orientation == 0
            else:
                expected_orientation = (4 - i) % 4
                assert state.active_piece.orientation == expected_orientation
                
                expected_rel = sorted(get_relative_cells(pt, expected_orientation))
                actual_rel = sorted([(r - state.active_piece.origin[0], c - state.active_piece.origin[1]) 
                                     for r, c in state.active_piece.cells])
                assert actual_rel == expected_rel

def test_o_piece_no_op_isolation():
    # O piece is a strict no-op: no orientation change, no coordinate change, no kick check
    board = [[None] * 10 for _ in range(20)]
    state = GameStateModel(
        id="test-o",
        board=board,
        active_piece=ActivePieceModel(
            type='O',
            origin=(5, 3),
            cells=[(5, 3), (5, 4), (6, 3), (6, 4)],
            orientation=0
        ),
        status="playing",
        next_piece="I"
    )
    
    # Try CW
    state = rotate_game(state, 'cw')
    assert state.active_piece.orientation == 0
    assert state.active_piece.origin == (5, 3)
    assert sorted(state.active_piece.cells) == [(5, 3), (5, 4), (6, 3), (6, 4)]
    
    # Try CCW
    state = rotate_game(state, 'ccw')
    assert state.active_piece.orientation == 0
    assert state.active_piece.origin == (5, 3)
    assert sorted(state.active_piece.cells) == [(5, 3), (5, 4), (6, 3), (6, 4)]

def test_right_wall_kick_i_piece():
    # Given 'I' piece at (0, 7) attempting CW rotation:
    # Kick 0 (dc = 0): col exceeds bound 9 (failed)
    # Kick 1 (dc = -1): inside bounds (succeeds)
    board = [[None] * 10 for _ in range(20)]
    state = GameStateModel(
        id="test-right-kick",
        board=board,
        active_piece=ActivePieceModel(
            type='I',
            origin=(0, 7),
            cells=[(0 + r, 7 + c) for r, c in get_relative_cells('I', 0)],
            orientation=0
        ),
        status="playing",
        next_piece="O"
    )
    
    state = rotate_game(state, 'cw')
    assert state.active_piece.orientation == 1
    # Shifted left by 1 (col 7 -> 6)
    assert state.active_piece.origin == (0, 6)
    expected_cells = [(0 + r, 6 + c) for r, c in get_relative_cells('I', 1)]
    assert sorted(state.active_piece.cells) == sorted(expected_cells)

def test_left_wall_kick_i_piece():
    # Given 'I' piece at orientation 3, at (0, -1) attempting CW rotation to orientation 0:
    # Kick 0 (dc = 0): col 0 is -1 (failed)
    # Kick 1 (dc = -1): col 0 is -2 (failed)
    # Kick 2 (dc = +1): col 0 is 0 (succeeds!)
    board = [[None] * 10 for _ in range(20)]
    state = GameStateModel(
        id="test-left-kick",
        board=board,
        active_piece=ActivePieceModel(
            type='I',
            origin=(0, -1),
            cells=[(0 + r, -1 + c) for r, c in get_relative_cells('I', 3)],
            orientation=3
        ),
        status="playing",
        next_piece="O"
    )
    
    state = rotate_game(state, 'cw')
    assert state.active_piece.orientation == 0
    # Shifted right by 1 (col -1 -> 0)
    assert state.active_piece.origin == (0, 0)
    expected_cells = [(0 + r, 0 + c) for r, c in get_relative_cells('I', 0)]
    assert sorted(state.active_piece.cells) == sorted(expected_cells)

def test_floor_collision_full_rejection():
    # Given 'I' piece at row = 18 attempting CW rotation:
    # Relative cells at orientation 1 have block at row 3 (relative). Abs row = 18 + 3 = 21 > 19 (illegal)
    # No horizontal kick can fix a vertical floor collision.
    board = [[None] * 10 for _ in range(20)]
    state = GameStateModel(
        id="test-floor-reject",
        board=board,
        active_piece=ActivePieceModel(
            type='I',
            origin=(18, 3),
            cells=[(18 + r, 3 + c) for r, c in get_relative_cells('I', 0)],
            orientation=0
        ),
        status="playing",
        next_piece="O",
        score=100,
        total_lines=5
    )
    
    state = rotate_game(state, 'cw')
    # Fully rejected: active piece orientation, origin, cells, score, lines remain completely unchanged
    assert state.active_piece.orientation == 0
    assert state.active_piece.origin == (18, 3)
    assert state.score == 100
    assert state.total_lines == 5

def test_locked_cells_full_rejection():
    # Piece is surrounded by locked cells so all kicks are blocked
    board = [[None] * 10 for _ in range(20)]
    # Lock everything in rows 5 to 8 except the exact initial cells of I piece at orientation 0
    for r in range(5, 9):
        for c in range(10):
            if not (r == 5 and 3 <= c <= 6):
                board[r][c] = 'X'
        
    state = GameStateModel(
        id="test-obstacle-reject",
        board=board,
        active_piece=ActivePieceModel(
            type='I',
            origin=(5, 3),
            cells=[(5 + r, 3 + c) for r, c in get_relative_cells('I', 0)],
            orientation=0
        ),
        status="playing",
        next_piece="O"
    )
    
    state = rotate_game(state, 'cw')
    assert state.active_piece.orientation == 0
    assert state.active_piece.origin == (5, 3)

def test_spawn_and_hold_orientation_reset():
    response = client.post("/api/games")
    assert response.status_code == 200
    data = response.json()
    game_id = data["id"]
    
    # Explicitly mock active piece to be an 'I' piece to ensure rotation modifies orientation
    GAMES[game_id].active_piece = ActivePieceModel(
        type='I',
        origin=(0, 3),
        cells=[(0 + r, 3 + c) for r, c in get_relative_cells('I', 0)],
        orientation=0
    )
    
    # 1. Rotate active piece CW to orientation 1
    response = client.post(f"/api/games/{game_id}/rotate", json={"direction": "cw"})
    assert response.status_code == 200
    assert response.json()["active_piece"]["orientation"] == 1
    
    # 2. Hold active piece (should store it)
    response = client.post(f"/api/games/{game_id}/hold")
    assert response.status_code == 200
    data_hold = response.json()
    # Held piece is stored, and a new piece is spawned in its spawn orientation (0)
    assert data_hold["active_piece"]["orientation"] == 0
    
    # Explicitly force newly spawned piece to be 'I' so we can rotate it deterministically
    GAMES[game_id].active_piece = ActivePieceModel(
        type='I',
        origin=(0, 3),
        cells=[(0 + r, 3 + c) for r, c in get_relative_cells('I', 0)],
        orientation=0
    )
    
    # 3. Rotate new piece CCW to orientation 3
    response = client.post(f"/api/games/{game_id}/rotate", json={"direction": "ccw"})
    assert response.status_code == 200
    assert response.json()["active_piece"]["orientation"] == 3
    
    # 4. Trigger holding again (to retrieve the originally held piece)
    # Wait, can_hold is set to false after one hold, so we need to mock can_hold = True
    GAMES[game_id].can_hold = True
    response = client.post(f"/api/games/{game_id}/hold")
    assert response.status_code == 200
    # Retrieved held piece from hold container enters play at orientation 0
    assert response.json()["active_piece"]["orientation"] == 0

def test_terminal_game_rotation_handling():
    # If the game is in game_over state, rotation endpoint returns game_over state without modification
    response = client.post("/api/games")
    game_id = response.json()["id"]
    state = GAMES[game_id]
    state.status = "game_over"
    
    response = client.post(f"/api/games/{game_id}/rotate", json={"direction": "cw"})
    assert response.status_code == 200
    assert response.json()["status"] == "game_over"

def test_invalid_requests_and_direction_payload():
    # Invalid direction values or extra payload fields
    response = client.post("/api/games")
    game_id = response.json()["id"]
    
    # Invalid direction
    response = client.post(f"/api/games/{game_id}/rotate", json={"direction": "invalid"})
    assert response.status_code == 422
    
    # Extra parameter
    response = client.post(f"/api/games/{game_id}/rotate", json={"direction": "cw", "extra_param": "forbidden"})
    assert response.status_code == 422
