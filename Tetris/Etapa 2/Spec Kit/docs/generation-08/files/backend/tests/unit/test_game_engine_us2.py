import pytest
from app.services.game_engine import clear_lines_in_board

def test_clear_lines_single_row():
    # Setup board with row 19 completely filled (non-zero) except empty above
    board = [[0] * 10 for _ in range(19)]
    board.append([3] * 10)  # Filled with purple blocks
    
    # Place a single block at row 18, col 5
    board[18][5] = 1
    
    cleared = clear_lines_in_board(board)
    assert cleared == 1
    # Check that row 19 is now the shifted row 18 (with the block at col 5)
    assert board[19][5] == 1
    # Check that other cells in row 19 are empty (since row 18 was mostly empty)
    assert board[19][4] == 0
    # Check that row 0 is completely empty
    assert board[0] == [0] * 10

def test_clear_lines_multiple_rows():
    board = [[0] * 10 for _ in range(18)]
    board.append([2] * 10)  # Row 18 filled
    board.append([2] * 10)  # Row 19 filled
    
    # Place block at row 17, col 1
    board[17][1] = 4
    
    cleared = clear_lines_in_board(board)
    assert cleared == 2
    # Row 19 should now be what row 17 was
    assert board[19][1] == 4
    # Top two rows (0 and 1) should be empty
    assert board[0] == [0] * 10
    assert board[1] == [0] * 10


from app.services.game_engine import (
    hold_session_piece,
    create_session,
    tick_session,
    active_sessions
)
from app.models.schemas import TetrominoSchema

def test_hold_first_time():
    active_sessions.clear()
    session = create_session()
    
    assert session.hold_piece is None
    assert session.can_hold is True
    
    initial_active_type = session.active_piece.type
    initial_next_type = session.next_piece
    
    updated = hold_session_piece(session.id)
    
    assert updated.hold_piece == initial_active_type
    assert updated.active_piece.type == initial_next_type
    assert updated.next_piece in {"I", "O", "T", "S", "Z", "J", "L"}
    assert updated.can_hold is False

def test_hold_swap():
    active_sessions.clear()
    session = create_session()
    session.hold_piece = "T"
    session.can_hold = True
    
    initial_active_type = session.active_piece.type
    initial_next_type = session.next_piece
    
    updated = hold_session_piece(session.id)
    
    assert updated.active_piece.type == "T"
    assert updated.hold_piece == initial_active_type
    assert updated.next_piece == initial_next_type
    assert updated.can_hold is False

def test_hold_immutable_actions():
    active_sessions.clear()
    session = create_session()
    
    # 1. Rejected Holds when can_hold is False
    session.can_hold = False
    session.hold_piece = "I"
    active_type = session.active_piece.type
    updated = hold_session_piece(session.id)
    assert updated.hold_piece == "I"
    assert updated.active_piece.type == active_type
    assert updated.can_hold is False
    
    # 2. Repeated state reads and holds after game over do not mutate state
    session.status = "game_over"
    session.can_hold = True
    session.hold_piece = None
    updated = hold_session_piece(session.id)
    assert updated.hold_piece is None

def test_hold_obstructed_spawn():
    active_sessions.clear()
    session = create_session()
    session.hold_piece = "I"
    session.can_hold = True
    
    for col in range(10):
        session.board[0][col] = 1
        
    updated = hold_session_piece(session.id)
    assert updated.status == "game_over"
    assert updated.active_piece is None

def test_hold_reset_on_lock():
    active_sessions.clear()
    session = create_session()
    session.can_hold = False
    
    session.active_piece = TetrominoSchema(
        type="O",
        cells=[[18, 4], [18, 5], [19, 4], [19, 5]],
        origin=[18, 4]
    )
    active_sessions[session.id] = session
    
    updated = tick_session(session.id)
    assert updated.can_hold is True
