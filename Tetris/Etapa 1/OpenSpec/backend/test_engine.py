import pytest
from fastapi.testclient import TestClient
from backend.engine import TetrisEngine, GameSession, SessionManager, TETROMINOES
from backend.models import GameState, ActivePiece, MoveRequest
from backend.main import app

# API test client
client = TestClient(app)

# ==========================================
# PHASE 5.1: UNIT TESTS FOR THE GAME ENGINE
# ==========================================

def test_create_empty_board():
    """REQ-001, REQ-002, REQ-003: Verify empty board layout and representation."""
    board = TetrisEngine.create_empty_board()
    assert len(board) == 20, "Board height must be 20 rows"
    for row in board:
        assert len(row) == 10, "Board width must be 10 columns"
        assert all(cell is None for cell in row), "All cells must be initialized to None"


def test_spawn_piece():
    """REQ-004, REQ-005, REQ-006, REQ-007: Verify piece spawning centering and orientation."""
    board = TetrisEngine.create_empty_board()
    
    # Test for each tetromino type
    for t_type in TETROMINOES.keys():
        active_piece, status = TetrisEngine.spawn_piece(board, force_piece_type=t_type)
        assert active_piece.type == t_type
        assert active_piece.origin == [0, 3], "Spawning origin must be centered at [0, 3]"
        assert status == "playing", "Initially the status must be playing on an empty board"
        
        # Verify default spawning orientation relative to [0, 3] origin
        expected_cells = [[0 + r, 3 + c] for r, c in TETROMINOES[t_type]]
        assert active_piece.cells == expected_cells, "Spawning cells should match shifted local coordinates"


def test_move_piece_success():
    """REQ-008, REQ-009, REQ-010: Verify successful movements (left, right, down)."""
    board = TetrisEngine.create_empty_board()
    # Spawn an O piece (origin [0, 3], cells: [1,4], [1,5], [2,4], [2,5])
    active_piece, _ = TetrisEngine.spawn_piece(board, force_piece_type="O")
    
    # Move left
    left_piece, success_left = TetrisEngine.move_piece(board, active_piece, "left")
    assert success_left
    assert left_piece.origin == [0, 2]
    assert left_piece.cells == [[1, 3], [1, 4], [2, 3], [2, 4]]
    
    # Move right
    right_piece, success_right = TetrisEngine.move_piece(board, active_piece, "right")
    assert success_right
    assert right_piece.origin == [0, 4]
    
    # Move down
    down_piece, success_down = TetrisEngine.move_piece(board, active_piece, "down")
    assert success_down
    assert down_piece.origin == [1, 3]


def test_move_piece_boundary_collisions():
    """REQ-011, REQ-012, REQ-013: Verify that moves hitting boundaries are blocked."""
    board = TetrisEngine.create_empty_board()
    active_piece, _ = TetrisEngine.spawn_piece(board, force_piece_type="O")
    
    # Shift O piece all the way to the left border to trigger collision
    curr = active_piece
    for _ in range(10):
        next_p, success = TetrisEngine.move_piece(board, curr, "left")
        if not success:
            break
        curr = next_p
    
    # Attempting to move left again should fail (origin columns cannot exceed border 0)
    final_left, fail_left = TetrisEngine.move_piece(board, curr, "left")
    assert not fail_left
    assert final_left == curr
    # Verify at least one cell has column index 0
    assert any(c[1] == 0 for r, c in enumerate(curr.cells))

    # Shift O piece all the way to the right border
    curr = active_piece
    for _ in range(10):
        next_p, success = TetrisEngine.move_piece(board, curr, "right")
        if not success:
            break
        curr = next_p
        
    final_right, fail_right = TetrisEngine.move_piece(board, curr, "right")
    assert not fail_right
    assert final_right == curr
    # Verify at least one cell has column index 9
    assert any(c[1] == 9 for r, c in enumerate(curr.cells))

    # Shift O piece all the way to the bottom border
    curr = active_piece
    for _ in range(30):
        next_p, success = TetrisEngine.move_piece(board, curr, "down")
        if not success:
            break
        curr = next_p
        
    final_down, fail_down = TetrisEngine.move_piece(board, curr, "down")
    assert not fail_down
    assert final_down == curr
    # Verify at least one cell has row index 19
    assert any(c[0] == 19 for r, c in enumerate(curr.cells))


def test_move_piece_settled_collisions():
    """REQ-014, REQ-015, REQ-016: Verify collisions against settled blocks."""
    board = TetrisEngine.create_empty_board()
    # Place a settled block in column 2 of row 5
    board[5][2] = "I"
    
    # Test Left Collision: Active block moving left into [5, 2]
    # Create an active piece cell at [5, 3]
    active_piece = ActivePiece(type="I", cells=[[5, 3]], origin=[4, 3])
    _, success = TetrisEngine.move_piece(board, active_piece, "left")
    assert not success, "Should be blocked by settled block on the left"
    
    # Test Right Collision: Active block moving right into [5, 2]
    active_piece = ActivePiece(type="I", cells=[[5, 1]], origin=[4, 1])
    _, success = TetrisEngine.move_piece(board, active_piece, "right")
    assert not success, "Should be blocked by settled block on the right"
    
    # Test Down Collision: Active block moving down into [5, 2]
    active_piece = ActivePiece(type="I", cells=[[4, 2]], origin=[3, 2])
    _, success = TetrisEngine.move_piece(board, active_piece, "down")
    assert not success, "Should be blocked by settled block underneath"


def test_lock_and_integrate_piece():
    """REQ-017, REQ-018, REQ-019: Verify active piece locking and integrating into board state."""
    board = TetrisEngine.create_empty_board()
    active_piece = ActivePiece(type="T", cells=[[19, 3], [19, 4], [19, 5], [18, 4]], origin=[17, 3])
    
    # Lock the piece
    new_board = TetrisEngine.lock_piece(board, active_piece)
    
    # Verify piece cells are settled in the new board matrix
    for r, c in active_piece.cells:
        assert new_board[r][c] == "T"
    assert new_board[0][0] is None


def test_clear_lines_single_and_multiple():
    """REQ-020, REQ-021, REQ-022, REQ-023, REQ-024: Verify line detection, clearing, row shifting and top padding."""
    board = TetrisEngine.create_empty_board()
    
    # Fill row 19 completely with settled blocks (10 columns)
    for col in range(10):
        board[19][col] = "I"
    # Put a partial block in row 18
    board[18][5] = "O"
    
    new_board, cleared = TetrisEngine.clear_lines(board)
    assert cleared == 1
    assert all(cell is None for cell in new_board[0]), "Row 0 must be empty prepend"
    assert new_board[19][5] == "O", "Row 18's O block should have shifted down to row 19"
    assert new_board[19][4] is None, "Other columns in shifted row 19 should remain empty"

    # Test simultaneous clearing of two rows
    double_board = TetrisEngine.create_empty_board()
    for col in range(10):
        double_board[19][col] = "T"
        double_board[18][col] = "O"
    double_board[17][3] = "J"
    
    cleared_board, double_cleared = TetrisEngine.clear_lines(double_board)
    assert double_cleared == 2
    assert cleared_board[19][3] == "J", "The J block from row 17 should drop 2 rows to row 19"
    assert all(cell is None for cell in cleared_board[0])
    assert all(cell is None for cell in cleared_board[1])


def test_game_over_trigger_and_rejection():
    """REQ-025, REQ-026, REQ-027: Verify game-over trigger on overlap on spawn and input rejection."""
    board = TetrisEngine.create_empty_board()
    # Place a settled block right in the horizontal center where pieces spawn
    board[1][4] = "I"
    
    # Spawning a T piece should trigger game over because its local coordinates [[1, 1], [2, 0], [2, 1], [2, 2]]
    # relative to origin [0, 3] contain cell [1, 4] which is blocked.
    _, status = TetrisEngine.spawn_piece(board, force_piece_type="T")
    assert status == "game_over"

    # Test GameSession control rejection on game_over status
    session = GameSession("test-session")
    session.board[1][4] = "I"
    session.status = "game_over"
    
    # Commands should fail / have no effect
    res_move = session.move("left")
    assert not res_move
    res_tick = session.step_down()
    assert not res_tick


def test_session_reset():
    """REQ-028: Verify restart / reset game control."""
    session = GameSession("test-session")
    session.board[19][3] = "I"
    session.status = "game_over"
    
    session.reset()
    assert session.status == "playing"
    assert all(all(cell is None for cell in row) for row in session.board)
    assert session.active_piece is not None


# ==========================================
# PHASE 5.2: API CONTROLLER INTEGRATION TESTS
# ==========================================

def test_api_create_and_get_game():
    """REQ-029, REQ-030: Test POST /api/games and GET /api/games/{id}."""
    # Create Game
    create_response = client.post("/api/games")
    assert create_response.status_code == 201
    game_data = create_response.json()
    assert "id" in game_data
    assert len(game_data["board"]) == 20
    assert len(game_data["board"][0]) == 10
    assert game_data["status"] == "playing"
    assert game_data["active_piece"] is not None
    
    game_id = game_data["id"]
    
    # Get Game
    get_response = client.get(f"/api/games/{game_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == game_id


def test_api_invalid_session():
    """Test standard error response for missing sessions."""
    get_response = client.get("/api/games/non-existent-id")
    assert get_response.status_code == 404
    assert get_response.json()["detail"] == "Game session not found"


def test_api_move_piece():
    """Test POST /api/games/{id}/move endpoint."""
    create_response = client.post("/api/games")
    game_id = create_response.json()["id"]
    
    # Move left
    move_resp = client.post(f"/api/games/{game_id}/move", json={"direction": "left"})
    assert move_resp.status_code == 200
    move_data = move_resp.json()
    assert move_data["status"] == "playing"
    
    # Test invalid direction parameter
    invalid_resp = client.post(f"/api/games/{game_id}/move", json={"direction": "rotate"})
    assert invalid_resp.status_code == 400


def test_api_gravity_tick():
    """Test POST /api/games/{id}/tick endpoint advancing gravity."""
    create_response = client.post("/api/games")
    game_id = create_response.json()["id"]
    
    tick_resp = client.post(f"/api/games/{game_id}/tick")
    assert tick_resp.status_code == 200
    tick_data = tick_resp.json()
    # Confirm it returned the GameState correctly
    assert tick_data["id"] == game_id
