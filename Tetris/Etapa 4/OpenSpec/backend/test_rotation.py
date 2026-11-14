import pytest
from backend.engine import TetrisEngine, GameSession, TETROMINOES, TETROMINO_ORIENTATIONS
from backend.models import ActivePiece

def test_four_turn_closure_and_inverses():
    """Verify unobstructed clockwise/counterclockwise turns, closure, and mathematical inverses."""
    board = TetrisEngine.create_empty_board()
    
    # Test for all standard pieces (except O, which is tested separately)
    for piece_type in ["I", "T", "J", "L", "S", "Z"]:
        # Spawn piece
        active_piece, _ = TetrisEngine.spawn_piece(board, force_piece_type=piece_type)
        initial_cells = sorted(active_piece.cells)
        initial_orientation = active_piece.orientation
        assert initial_orientation == 0
        
        # Rotate CW 4 times
        p = active_piece
        for _ in range(4):
            p, success = TetrisEngine.rotate_piece(board, p, "clockwise")
            assert success
            
        assert p.orientation == 0
        assert sorted(p.cells) == initial_cells
        
        # Rotate CCW 4 times
        p = active_piece
        for _ in range(4):
            p, success = TetrisEngine.rotate_piece(board, p, "counterclockwise")
            assert success
            
        assert p.orientation == 0
        assert sorted(p.cells) == initial_cells
        
        # CW then CCW should return to initial state
        p_cw, success_cw = TetrisEngine.rotate_piece(board, active_piece, "clockwise")
        assert success_cw
        assert p_cw.orientation == 1
        
        p_ccw, success_ccw = TetrisEngine.rotate_piece(board, p_cw, "counterclockwise")
        assert success_ccw
        assert p_ccw.orientation == 0
        assert sorted(p_ccw.cells) == initial_cells


def test_o_piece_no_op():
    """Verify that O tetromino rotation is a full no-op (orientation, cells, origin remain unchanged)."""
    board = TetrisEngine.create_empty_board()
    active_piece, _ = TetrisEngine.spawn_piece(board, force_piece_type="O")
    initial_cells = sorted(active_piece.cells)
    initial_origin = active_piece.origin
    initial_orientation = active_piece.orientation
    
    # Rotate CW
    p, success = TetrisEngine.rotate_piece(board, active_piece, "clockwise")
    assert success
    assert p.orientation == initial_orientation
    assert p.origin == initial_origin
    assert sorted(p.cells) == initial_cells
    
    # Rotate CCW
    p2, success2 = TetrisEngine.rotate_piece(board, active_piece, "counterclockwise")
    assert success2
    assert p2.orientation == initial_orientation
    assert p2.origin == initial_origin
    assert sorted(p2.cells) == initial_cells


def test_i_piece_orientations():
    """Verify that "I" shape rotated coordinates match exact designs."""
    board = TetrisEngine.create_empty_board()
    # Spawns at origin [0, 3]
    active_piece, _ = TetrisEngine.spawn_piece(board, force_piece_type="I")
    
    # Orientation 0: [[1, 0], [1, 1], [1, 2], [1, 3]] -> shifted by [0, 3]
    # => [[1, 3], [1, 4], [1, 5], [1, 6]]
    assert sorted(active_piece.cells) == [[1, 3], [1, 4], [1, 5], [1, 6]]
    assert active_piece.orientation == 0
    
    # Orientation 1
    p1, success = TetrisEngine.rotate_piece(board, active_piece, "clockwise")
    assert success
    assert p1.orientation == 1
    # Local coords for 1: [[0, 2], [1, 2], [2, 2], [3, 2]] -> shifted by [0, 3]
    # => [[0, 5], [1, 5], [2, 5], [3, 5]]
    assert sorted(p1.cells) == [[0, 5], [1, 5], [2, 5], [3, 5]]


def test_spawn_and_hold_reset_orientation():
    """Verify spawning or hold swaps reset active piece orientation to 0."""
    session = GameSession("test-reset-session")
    session.next_piece = "T"  # Pin non-O geometry fixture to prevent O piece no-op flakiness
    # Force active piece to T to avoid O no-op flakiness
    from backend.models import ActivePiece
    session.active_piece = ActivePiece(type="T", cells=[[1, 1], [2, 0], [2, 1], [2, 2]], origin=[0, 3], orientation=0)
    
    # Rotate CW to orientation 1
    success = session.move("clockwise")
    assert success
    assert session.active_piece.orientation == 1
    
    # Hold Swap
    success_hold = session.hold()
    assert success_hold
    # New active piece should have orientation 0
    assert session.active_piece.orientation == 0
    
    # Reset can hold so we can hold swap back
    session.can_hold = True
    success_hold_back = session.hold()
    assert success_hold_back
    # Held piece retrieved should reset orientation to 0
    assert session.active_piece.orientation == 0


def test_movement_after_rotation_preserves_orientation_and_cells():
    """Verify movement after rotation preserves orientation and translated rotated cells."""
    board = TetrisEngine.create_empty_board()
    active_piece, _ = TetrisEngine.spawn_piece(board, force_piece_type="T")
    
    # Rotate CW (orientation 1)
    p_rot, success_rot = TetrisEngine.rotate_piece(board, active_piece, "clockwise")
    assert success_rot
    assert p_rot.orientation == 1
    
    # Move left
    p_move, success_move = TetrisEngine.move_piece(board, p_rot, "left")
    assert success_move
    assert p_move.orientation == 1
    assert p_move.origin == [p_rot.origin[0], p_rot.origin[1] - 1]
    
    # Check cells are shifted left by 1 column
    expected_cells = [[r, c - 1] for r, c in p_rot.cells]
    assert sorted(p_move.cells) == sorted(expected_cells)


def test_wall_kicks_and_priority():
    """Verify horizontal wall-kicks in priority order 0, -1, +1, -2, +2."""
    # Let's test a piece colliding with the left boundary (col < 0)
    board = TetrisEngine.create_empty_board()
    
    # Create a T piece manually with origin at [5, -1] (or just move it there)
    # T local blocks at orientation 1: [[1, 1], [2, 1], [2, 2], [3, 1]]
    # If origin is [5, -1], cells are: [[6, 0], [7, 0], [7, 1], [8, 0]]
    # If we rotate it from orientation 0 (origin [5, -1], cells: [[6, 0], [7, -1], [7, 0], [7, 1]])
    # Wait, let's test using TetrisEngine.rotate_piece directly with custom ActivePiece!
    active_piece = ActivePiece(
        type="T",
        origin=[5, -1],
        cells=[[6, 0], [7, -1], [7, 0], [7, 1]], # Left cell is at column -1 (collides!)
        orientation=0
    )
    
    # Rotate CW to orientation 1 (local coords: [[1, 1], [2, 1], [2, 2], [3, 1]])
    # For col_offset = 0 (origin [5, -1]): cells: [[6, 0], [7, 0], [7, 1], [8, 0]] - valid!
    # Let's see: col_offset = 0 is valid. So it doesn't need to kick, offset 0 is applied.
    p, success = TetrisEngine.rotate_piece(board, active_piece, "clockwise")
    assert success
    assert p.origin == [5, -1]
    
    # Let's create a collision on col_offset = 0, but valid for +1 offset
    # Let's lock a block at [7, 0] (which collides with col_offset=0, but offset +1 shift piece to right)
    board[7][0] = "I"
    active_piece2 = ActivePiece(
        type="T",
        origin=[5, -1],
        cells=[[6, 0], [7, -1], [7, 0], [7, 1]],
        orientation=0
    )
    # Rotate CW to orientation 1.
    # col_offset = 0: origin [5, -1], cells: [[6, 0], [7, 0], [7, 1], [8, 0]] -> Collides with locked block at [7, 0]!
    # col_offset = -1: origin [5, -2], cells: [[6, -1], [7, -1], [7, 0], [8, -1]] -> Collides with wall!
    # col_offset = +1: origin [5, 0], cells: [[6, 1], [7, 1], [7, 2], [8, 1]] -> Valid! (all columns >= 0 and no locked block collision)
    # Priority order tries: 0 (collide), -1 (collide), +1 (valid!)
    p2, success2 = TetrisEngine.rotate_piece(board, active_piece2, "clockwise")
    assert success2
    assert p2.origin == [5, 0] # Kicked right by 1 column!
    assert p2.orientation == 1


def test_floor_limits_and_full_rejection():
    """Verify floor limits and full rejection when no offsets fit (no vertical kicks)."""
    board = TetrisEngine.create_empty_board()
    
    # Put a T piece near the bottom floor.
    # T local blocks at orientation 1: [[1, 1], [2, 1], [2, 2], [3, 1]]
    # If origin is [17, 3], orientation 0: cells are within [17, 3]+[[1, 1], [2, 0], [2, 1], [2, 2]] = [[18, 4], [19, 3], [19, 4], [19, 5]] (fits!)
    # Rotating CW to orientation 1: cells would have row index 17 + 3 = 20 (row 20 is out of bounds/floor!)
    # Since there are no vertical offsets, trying col_offsets 0, -1, +1, -2, +2 will always keep row 20, which collides with floor.
    # Therefore, rotation must be completely rejected and state preserved.
    active_piece = ActivePiece(
        type="T",
        origin=[17, 3],
        cells=[[18, 4], [19, 3], [19, 4], [19, 5]],
        orientation=0
    )
    
    p, success = TetrisEngine.rotate_piece(board, active_piece, "clockwise")
    assert not success
    assert p.orientation == 0
    assert p.origin == [17, 3]
    assert p.cells == active_piece.cells


def test_game_over_terminal_no_op():
    """Verify rotation is a terminal no-op on game-over."""
    session = GameSession("test-game-over-session")
    session.status = "game_over"
    
    # Try rotating
    success = session.move("clockwise")
    assert not success
