import pytest
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


def test_scoring_rules_isolated():
    def get_points(lines, level):
        table = {1: 100, 2: 300, 3: 500, 4: 800}
        return table.get(lines, 0) * level

    assert get_points(1, 1) == 100
    assert get_points(2, 1) == 300
    assert get_points(3, 1) == 500
    assert get_points(4, 1) == 800

    assert get_points(1, 3) == 300
    assert get_points(2, 3) == 900
    assert get_points(3, 3) == 1500
    assert get_points(4, 3) == 2400


def test_level_boundary_calculation():
    def calc_level(lines):
        return 1 + lines // 10

    assert calc_level(0) == 1
    assert calc_level(5) == 1
    assert calc_level(9) == 1
    assert calc_level(10) == 2
    assert calc_level(19) == 2
    assert calc_level(20) == 3


def test_pre_lock_level_scoring():
    active_sessions.clear()
    session = create_session()
    session.level = 1
    session.total_lines = 9
    session.score = 0
    
    session.board[19] = [0] + [2] * 9
    session.active_piece = TetrominoSchema(
        type="I",
        cells=[[18, 0], [18, 1], [18, 2], [19, 0]],
        origin=[18, 0]
    )
    active_sessions[session.id] = session

    updated = tick_session(session.id)
    assert updated.total_lines == 10
    assert updated.level == 2
    assert updated.score == 100


def test_progressive_gravity_calculations():
    def calc_gravity(level):
        return max(100, 500 - 50 * (level - 1))

    assert calc_gravity(1) == 500
    assert calc_gravity(2) == 450
    assert calc_gravity(5) == 300
    assert calc_gravity(9) == 100
    assert calc_gravity(10) == 100


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
