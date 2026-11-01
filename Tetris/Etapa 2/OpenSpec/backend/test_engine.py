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


def test_stage2_scoring_and_progression():
    """Verify scoring logic (including 4-row control scenario), levels progression, and gravity timers."""
    session = GameSession("test-stage2-progression")
    
    # Check initial values (REQ-032)
    assert session.score == 0
    assert session.total_lines == 0
    assert session.level == 1
    assert session.gravity_interval_ms == 500
    assert session.hold_piece is None
    assert session.can_hold is True

    # 1. Test 1-row clear scoring at level 1: 100 * 1 = 100 points
    session.level = 1
    session.board = TetrisEngine.create_empty_board()
    for col in range(10):
        session.board[19][col] = "I"
    # Cause a lock
    session.active_piece = ActivePiece(type="I", cells=[[18, 0], [18, 1], [18, 2], [18, 3]], origin=[17, 0])
    session.step_down()  # locks and clears row 19
    assert session.score == 100
    assert session.total_lines == 1
    assert session.level == 1
    assert session.gravity_interval_ms == 500

    # 2. Test 2-row clear scoring at level 2: 300 * 2 = 600 points (+ 100 from previous = 700)
    session.level = 2
    session.total_lines = 9
    session.board = TetrisEngine.create_empty_board()
    for col in range(10):
        session.board[19][col] = "I"
        session.board[18][col] = "I"
    session.active_piece = ActivePiece(type="I", cells=[[17, 0], [17, 1], [17, 2], [17, 3]], origin=[16, 0])
    session.step_down()  # locks and clears rows 19 & 18
    assert session.score == 700  # 100 + 600
    assert session.total_lines == 11
    assert session.level == 2  # 1 + floor(11 / 10) = 2
    assert session.gravity_interval_ms == 450  # 500 - 50 * (2 - 1) = 450

    # 3. Test 3-row clear scoring at level 3: 500 * 3 = 1500 points (+ 700 from previous = 2200)
    session.level = 3
    session.board = TetrisEngine.create_empty_board()
    for col in range(10):
        session.board[19][col] = "I"
        session.board[18][col] = "I"
        session.board[17][col] = "I"
    session.active_piece = ActivePiece(type="I", cells=[[16, 0], [16, 1], [16, 2], [16, 3]], origin=[15, 0])
    session.step_down()  # locks and clears rows 19, 18, 17
    assert session.score == 2200  # 700 + 1500

    # 4. Test 4-row clear scoring (REQ-033, 4-row control scenario) at level 4: 800 * 4 = 3200 points (+ 2200 from previous = 5400)
    session.level = 4
    session.board = TetrisEngine.create_empty_board()
    for col in range(10):
        session.board[19][col] = "I"
        session.board[18][col] = "I"
        session.board[17][col] = "I"
        session.board[16][col] = "I"
    session.active_piece = ActivePiece(type="I", cells=[[15, 0], [15, 1], [15, 2], [15, 3]], origin=[14, 0])
    session.step_down()  # locks and clears rows 19, 18, 17, 16
    assert session.score == 5400  # 2200 + 3200


def test_stage2_level_and_gravity_speed_progression():
    """Verify progressive gravity calculations and maximum speed cap."""
    session = GameSession("test-stage2-gravity")
    
    # Level 1 (0 to 9 lines) -> 500ms
    session.total_lines = 9
    session.board = TetrisEngine.create_empty_board()
    for col in range(10):
        session.board[19][col] = "I"
    session.active_piece = ActivePiece(type="I", cells=[[18, 0], [18, 1], [18, 2], [18, 3]], origin=[17, 0])
    session.step_down()
    assert session.total_lines == 10
    assert session.level == 2
    assert session.gravity_interval_ms == 450

    # Increase lines to level 10 -> interval should be max(100, 500 - 50 * (10 - 1)) = max(100, 500 - 450) = 100ms
    session.total_lines = 99
    session.board = TetrisEngine.create_empty_board()
    for col in range(10):
        session.board[19][col] = "I"
    session.active_piece = ActivePiece(type="I", cells=[[18, 0], [18, 1], [18, 2], [18, 3]], origin=[17, 0])
    session.step_down()
    assert session.total_lines == 100
    assert session.level == 11
    assert session.gravity_interval_ms == 100  # Capped at 100ms


def test_stage2_hold_mechanics():
    """Verify hold operations, swapping, can_hold cooldown and hold-spawn collisions."""
    session = GameSession("test-stage2-hold")
    session.active_piece = ActivePiece(type="T", cells=[[1, 4], [2, 3], [2, 4], [2, 5]], origin=[0, 3])
    session.next_piece = "I"
    session.hold_piece = None
    session.can_hold = True

    # 1. First Hold Execution (REQ-038)
    assert session.hold() is True
    assert session.hold_piece == "T"
    assert session.active_piece.type == "I"
    assert session.can_hold is False

    # 2. Repeated Hold Rejection (REQ-040)
    assert session.hold() is False  # can_hold is False
    assert session.hold_piece == "T"
    assert session.active_piece.type == "I"

    # 3. Restoring can_hold after lock and spawn
    session.board = TetrisEngine.create_empty_board()
    # Move active piece to the bottom and step down to force a lock and spawn next
    session.active_piece = ActivePiece(type="I", cells=[[19, 0], [19, 1], [19, 2], [19, 3]], origin=[18, 0])
    session.step_down()  # Locks piece, spawns next, makes can_hold=True
    assert session.can_hold is True

    # 4. Swapping Hold Execution (REQ-039)
    session.active_piece = ActivePiece(type="O", cells=[[1, 4], [1, 5], [2, 4], [2, 5]], origin=[0, 3])
    assert session.hold() is True
    assert session.hold_piece == "O"
    assert session.active_piece.type == "T"
    assert session.can_hold is False

    # 5. Hold Spawn Collision transitions immediately to game_over (REQ-041)
    session.can_hold = True
    session.board = TetrisEngine.create_empty_board()
    # Place settled block in spawn coordinates [1, 4]
    session.board[1][4] = "I"
    session.active_piece = ActivePiece(type="S", cells=[[1, 4], [1, 5], [2, 3], [2, 4]], origin=[0, 3])
    session.hold_piece = "O"
    
    assert session.hold() is True  # The action still executes, but the spawned piece overlaps, causing game_over
    assert session.status == "game_over"
    assert session.can_hold is False
    assert session.to_state().active_piece is None


def test_stage2_level_boundary_uses_pre_lock_score():
    """S2-08: clearing line ten scores at level one, then raises the level."""
    session = GameSession("level-boundary")
    session.total_lines = 9
    session.level = 1
    session.board = TetrisEngine.create_empty_board()
    session.board[19] = ["I"] * 10
    session.active_piece = ActivePiece(
        type="I", cells=[[18, 0], [18, 1], [18, 2], [18, 3]], origin=[17, 0]
    )

    assert session.step_down() is False
    assert session.score == 100
    assert session.total_lines == 10
    assert session.level == 2
    assert session.gravity_interval_ms == 450


def test_stage2_game_over_actions_leave_state_unchanged():
    """S2-14: game-over sessions reject gravity, movement, and Hold."""
    session = GameSession("game-over-inert")
    session.status = "game_over"
    before = session.to_state().model_dump()

    assert session.step_down() is False
    assert session.move("left") is False
    assert session.move("right") is False
    assert session.move("down") is False
    assert session.hold() is False
    assert session.to_state().model_dump() == before


def test_api_peek_next_piece_does_not_consume():
    """Verify that fetching game state does not consume the next piece queue (REQ-037)."""
    # Create Game
    create_response = client.post("/api/games")
    assert create_response.status_code == 201
    game_data = create_response.json()
    game_id = game_data["id"]
    next_piece = game_data["next_piece"]
    assert next_piece is not None

    # Get Game multiple times (peeking)
    for _ in range(3):
        get_response = client.get(f"/api/games/{game_id}")
        assert get_response.status_code == 200
        assert get_response.json()["next_piece"] == next_piece


def test_api_hold_endpoint_and_restart():
    """Verify API POST /api/games/{id}/hold endpoint and reset behavior (REQ-028)."""
    # Create Game
    create_response = client.post("/api/games")
    game_data = create_response.json()
    game_id = game_data["id"]
    active_type = game_data["active_piece"]["type"]
    next_type = game_data["next_piece"]

    # Call Hold API
    hold_resp = client.post(f"/api/games/{game_id}/hold")
    assert hold_resp.status_code == 200
    hold_data = hold_resp.json()
    assert hold_data["hold_piece"] == active_type
    assert hold_data["active_piece"]["type"] == next_type
    assert hold_data["can_hold"] is False

    # Call Hold API again when not allowed -> should raise HTTP 400
    hold_resp_blocked = client.post(f"/api/games/{game_id}/hold")
    assert hold_resp_blocked.status_code == 400
    assert "Hold action is not allowed" in hold_resp_blocked.json()["detail"]

    # Create new session (restarting/resets) -> check resetting Stage 2 metrics
    restart_resp = client.post("/api/games")
    assert restart_resp.status_code == 201
    restart_data = restart_resp.json()
    assert restart_data["id"] != game_id
    assert restart_data["score"] == 0
    assert restart_data["total_lines"] == 0
    assert restart_data["level"] == 1
    assert restart_data["gravity_interval_ms"] == 500
    assert restart_data["hold_piece"] is None
    assert restart_data["can_hold"] is True
