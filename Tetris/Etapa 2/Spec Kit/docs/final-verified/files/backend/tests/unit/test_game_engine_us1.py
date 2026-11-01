import pytest
from unittest.mock import patch
from app.services.game_engine import (
    create_session,
    has_collision,
    move_session_piece,
    tick_session,
    active_sessions
)
from app.models.schemas import GameSessionSchema, TetrominoSchema

def test_has_collision_boundaries():
    # Board is empty (all 0s)
    board = [[0] * 10 for _ in range(20)]
    
    # Inside boundaries (should be False)
    assert not has_collision(board, [[0, 4], [0, 5], [1, 4], [1, 5]])
    
    # Boundary collisions (should be True)
    assert has_collision(board, [[-1, 4]])  # Out of bounds top
    assert has_collision(board, [[20, 4]])  # Out of bounds bottom
    assert has_collision(board, [[10, -1]]) # Out of bounds left
    assert has_collision(board, [[10, 10]]) # Out of bounds right

def test_has_collision_settled_blocks():
    board = [[0] * 10 for _ in range(20)]
    board[15][5] = 2  # Place a block at row 15, col 5
    
    # Collides with settled block
    assert has_collision(board, [[15, 5]])
    # Adjacent does not collide
    assert not has_collision(board, [[15, 4]])

def test_create_session():
    active_sessions.clear()
    session = create_session()
    
    assert session.id in active_sessions
    assert len(session.board) == 20
    assert all(len(row) == 10 for row in session.board)
    assert session.status == "playing"
    assert session.active_piece is not None
    assert session.active_piece.type in {"I", "O", "T", "S", "Z", "J", "L"}
    assert len(session.active_piece.cells) == 4

def test_move_left_right():
    active_sessions.clear()
    session = create_session()
    # Force a known piece and position (e.g. O piece at row 0, col 4)
    session.active_piece = TetrominoSchema(
        type="O",
        cells=[[0, 4], [0, 5], [1, 4], [1, 5]],
        origin=[0, 4]
    )
    active_sessions[session.id] = session
    
    # Move left
    updated = move_session_piece(session.id, "left")
    assert updated.active_piece.origin == [0, 3]
    assert updated.active_piece.cells == [[0, 3], [0, 4], [1, 3], [1, 4]]
    
    # Move right
    updated = move_session_piece(session.id, "right")
    assert updated.active_piece.origin == [0, 4]
    
    # Force adjacent left boundary and test collision revert
    session.active_piece = TetrominoSchema(
        type="O",
        cells=[[0, 0], [0, 1], [1, 0], [1, 1]],
        origin=[0, 0]
    )
    updated = move_session_piece(session.id, "left")
    # Should not move left beyond column 0
    assert updated.active_piece.origin == [0, 0]

def test_manual_down_does_not_lock():
    active_sessions.clear()
    session = create_session()
    # Position piece resting on bottom (row 18 and 19 for O piece)
    session.active_piece = TetrominoSchema(
        type="O",
        cells=[[18, 4], [18, 5], [19, 4], [19, 5]],
        origin=[18, 4]
    )
    active_sessions[session.id] = session
    
    # Move down manual (should not lock on contact with bottom, just keep same coordinates)
    updated = move_session_piece(session.id, "down")
    assert updated.active_piece is not None
    assert updated.active_piece.origin == [18, 4]
    assert updated.status == "playing"

def test_tick_falling_and_lock():
    active_sessions.clear()
    session = create_session()
    session.active_piece = TetrominoSchema(
        type="O",
        cells=[[0, 4], [0, 5], [1, 4], [1, 5]],
        origin=[0, 4]
    )
    active_sessions[session.id] = session
    
    # Tick down once (no collision)
    updated = tick_session(session.id)
    assert updated.active_piece.origin == [1, 4]
    assert updated.active_piece.cells == [[1, 4], [1, 5], [2, 4], [2, 5]]
    
    # Position piece resting on bottom (O piece row 18 and 19)
    session.active_piece = TetrominoSchema(
        type="O",
        cells=[[18, 4], [18, 5], [19, 4], [19, 5]],
        origin=[18, 4]
    )
    active_sessions[session.id] = session
    
    # Gravity tick (should trigger locking and spawn a new piece)
    updated = tick_session(session.id)
    # Check that O piece is locked on board with value 2 (the color index for O is 2 in data-model.md)
    assert updated.board[18][4] == 2
    assert updated.board[18][5] == 2
    assert updated.board[19][4] == 2
    assert updated.board[19][5] == 2
    
    # A new active piece should be spawned at top
    assert updated.active_piece is not None
    assert updated.active_piece.cells != [[18, 4], [18, 5], [19, 4], [19, 5]]

def test_scoring_rules_production():
    # 1. 0 Cleared Rows
    active_sessions.clear()
    session = create_session()
    session.level = 1
    session.score = 0
    session.total_lines = 0
    # Place I piece so it locks at row 19, columns 3, 4, 5, 6
    session.active_piece = TetrominoSchema(
        type="I",
        cells=[[19, 3], [19, 4], [19, 5], [19, 6]],
        origin=[19, 4]
    )
    # Keep row 19 completely empty so no lines clear
    session.board[19] = [0] * 10
    active_sessions[session.id] = session
    
    updated = tick_session(session.id)
    assert updated.score == 0
    assert updated.total_lines == 0
    assert updated.level == 1
    assert updated.gravity_interval_ms == 500

    # 2. 1 Cleared Row (using real horizontal I template and matching board gaps)
    active_sessions.clear()
    session = create_session()
    session.level = 1
    session.score = 0
    session.total_lines = 0
    session.active_piece = TetrominoSchema(
        type="I",
        cells=[[19, 3], [19, 4], [19, 5], [19, 6]],
        origin=[19, 4]
    )
    session.board[19] = [1, 1, 1, 0, 0, 0, 0, 1, 1, 1]
    active_sessions[session.id] = session

    updated = tick_session(session.id)
    assert updated.score == 100
    assert updated.total_lines == 1
    assert updated.level == 1
    assert updated.gravity_interval_ms == 500

    # 3. 2 Cleared Rows (using real O template)
    active_sessions.clear()
    session = create_session()
    session.level = 1
    session.score = 0
    session.total_lines = 0
    session.active_piece = TetrominoSchema(
        type="O",
        cells=[[18, 4], [18, 5], [19, 4], [19, 5]],
        origin=[18, 4]
    )
    session.board[18] = [1, 1, 1, 1, 0, 0, 1, 1, 1, 1]
    session.board[19] = [1, 1, 1, 1, 0, 0, 1, 1, 1, 1]
    active_sessions[session.id] = session

    updated = tick_session(session.id)
    assert updated.score == 300
    assert updated.total_lines == 2
    assert updated.level == 1
    assert updated.gravity_interval_ms == 500

    # 4. 3 and 4 Cleared Rows (using isolated domain fixtures/mocked row clears)
    # 3 Rows cleared at Level 2
    active_sessions.clear()
    session = create_session()
    session.level = 2
    session.score = 0
    session.total_lines = 10
    session.active_piece = TetrominoSchema(
        type="I",
        cells=[[19, 3], [19, 4], [19, 5], [19, 6]],
        origin=[19, 4]
    )
    active_sessions[session.id] = session
    with patch("app.services.game_engine.clear_lines_in_board", return_value=3):
        updated = tick_session(session.id)
    assert updated.score == 1000  # 500 * level_before (2) = 1000
    assert updated.total_lines == 13
    assert updated.level == 2

    # 4 Rows cleared at Level 3
    active_sessions.clear()
    session = create_session()
    session.level = 3
    session.score = 0
    session.total_lines = 20
    session.active_piece = TetrominoSchema(
        type="I",
        cells=[[19, 3], [19, 4], [19, 5], [19, 6]],
        origin=[19, 4]
    )
    active_sessions[session.id] = session
    with patch("app.services.game_engine.clear_lines_in_board", return_value=4):
        updated = tick_session(session.id)
    assert updated.score == 2400  # 800 * level_before (3) = 2400
    assert updated.total_lines == 24
    assert updated.level == 3

def test_level_transitions_and_gravity_floor_production():
    # 9-to-10 line crossing (from Level 1 to Level 2)
    active_sessions.clear()
    session = create_session()
    session.level = 1
    session.total_lines = 9
    session.score = 1000
    session.active_piece = TetrominoSchema(
        type="I",
        cells=[[19, 3], [19, 4], [19, 5], [19, 6]],
        origin=[19, 4]
    )
    session.board[19] = [1, 1, 1, 0, 0, 0, 0, 1, 1, 1]
    active_sessions[session.id] = session

    updated = tick_session(session.id)
    assert updated.total_lines == 10
    assert updated.level == 2
    assert updated.score == 1100  # 1000 + 100 * level_before (1) = 1100
    assert updated.gravity_interval_ms == 450

    # 9-to-11 line crossing (from Level 1 to Level 2 via a double clear)
    active_sessions.clear()
    session = create_session()
    session.level = 1
    session.total_lines = 9
    session.score = 1000
    session.active_piece = TetrominoSchema(
        type="O",
        cells=[[18, 4], [18, 5], [19, 4], [19, 5]],
        origin=[18, 4]
    )
    session.board[18] = [1, 1, 1, 1, 0, 0, 1, 1, 1, 1]
    session.board[19] = [1, 1, 1, 1, 0, 0, 1, 1, 1, 1]
    active_sessions[session.id] = session

    updated = tick_session(session.id)
    assert updated.total_lines == 11
    assert updated.level == 2
    assert updated.score == 1300  # 1000 + 300 * level_before (1) = 1300
    assert updated.gravity_interval_ms == 450

    # Gravity reaching and staying at 100 ms
    # Level 9 (reaches 100ms)
    active_sessions.clear()
    session = create_session()
    session.level = 8
    session.total_lines = 79
    session.score = 0
    session.active_piece = TetrominoSchema(
        type="I",
        cells=[[19, 3], [19, 4], [19, 5], [19, 6]],
        origin=[19, 4]
    )
    session.board[19] = [1, 1, 1, 0, 0, 0, 0, 1, 1, 1]
    active_sessions[session.id] = session

    updated = tick_session(session.id)
    assert updated.level == 9
    assert updated.gravity_interval_ms == 100

    # Level 10 (stays at 100ms floor)
    active_sessions.clear()
    session = create_session()
    session.level = 9
    session.total_lines = 89
    session.score = 0
    session.active_piece = TetrominoSchema(
        type="I",
        cells=[[19, 3], [19, 4], [19, 5], [19, 6]],
        origin=[19, 4]
    )
    session.board[19] = [1, 1, 1, 0, 0, 0, 0, 1, 1, 1]
    active_sessions[session.id] = session

    updated = tick_session(session.id)
    assert updated.level == 10
    assert updated.gravity_interval_ms == 100

def test_no_points_on_soft_drop_production():
    active_sessions.clear()
    session = create_session()
    session.score = 100
    session.active_piece = TetrominoSchema(
        type="O",
        cells=[[0, 4], [0, 5], [1, 4], [1, 5]],
        origin=[0, 4]
    )
    active_sessions[session.id] = session

    updated = move_session_piece(session.id, "down")
    assert updated.score == 100

def test_next_piece_queue_generation():
    active_sessions.clear()
    session = create_session()
    
    assert session.next_piece in {"I", "O", "T", "S", "Z", "J", "L"}
    initial_next = session.next_piece
    
    session.active_piece = TetrominoSchema(
        type="O",
        cells=[[18, 4], [18, 5], [19, 4], [19, 5]],
        origin=[18, 4]
    )
    active_sessions[session.id] = session
    
    updated = tick_session(session.id)
    assert updated.active_piece.type == initial_next
    assert updated.next_piece in {"I", "O", "T", "S", "Z", "J", "L"}
