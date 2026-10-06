from app.core.domain import (
    create_new_game,
    move_piece,
    tick_game,
    is_valid_position,
    clear_completed_lines,
    get_spawned_piece,
    Cell,
    BOARD_COLS,
    BOARD_ROWS
)

def test_board_creation():
    state = create_new_game("test-uuid")
    assert state.id == "test-uuid"
    assert state.status == "playing"
    assert len(state.board) == BOARD_ROWS
    assert all(len(row) == BOARD_COLS for row in state.board)
    assert all(cell == 0 for row in state.board for cell in row)
    assert state.active_piece.shape in ["I", "J", "L", "O", "S", "T", "Z"]

def test_spawning_centered_coordinates():
    # Verify that spawning coordinates are centered around column 3-6 at rows 0-1
    for shape in ["I", "J", "L", "O", "S", "T", "Z"]:
        piece = get_spawned_piece(shape)
        assert all(0 <= cell.row <= 1 for cell in piece.cells)
        assert all(3 <= cell.col <= 6 for cell in piece.cells)

def test_collision_detection_borders():
    board = [[0] * BOARD_COLS for _ in range(BOARD_ROWS)]
    
    # Left border collision
    left_piece_cells = [Cell(row=0, col=-1), Cell(row=0, col=0)]
    assert not is_valid_position(board, left_piece_cells)
    
    # Right border collision
    right_piece_cells = [Cell(row=0, col=10), Cell(row=0, col=9)]
    assert not is_valid_position(board, right_piece_cells)
    
    # Bottom border collision
    bottom_piece_cells = [Cell(row=20, col=5)]
    assert not is_valid_position(board, bottom_piece_cells)
    
    # Valid position in bounds
    valid_cells = [Cell(row=0, col=5), Cell(row=1, col=5)]
    assert is_valid_position(board, valid_cells)

def test_collision_detection_settled_blocks():
    board = [[0] * BOARD_COLS for _ in range(BOARD_ROWS)]
    board[5][5] = 1  # settled block
    
    overlapping_cells = [Cell(row=5, col=5)]
    non_overlapping_cells = [Cell(row=4, col=5)]
    
    assert not is_valid_position(board, overlapping_cells)
    assert is_valid_position(board, non_overlapping_cells)

def test_legal_movements():
    # Setup standard game and check shifting Left, Right, Down updates cells correctly
    state = create_new_game("test")
    # Force coordinates to a safe middle zone
    state.active_piece.cells = [Cell(row=5, col=3), Cell(row=5, col=4), Cell(row=5, col=5), Cell(row=5, col=6)]
    state.active_piece.origin = Cell(row=5, col=3)
    
    # Left Shift
    left_state = move_piece(state, "left")
    assert all(c.col == original - 1 for c, original in zip(left_state.active_piece.cells, [3, 4, 5, 6]))
    assert left_state.active_piece.origin.col == 2
    
    # Right Shift
    right_state = move_piece(state, "right")
    assert all(c.col == original + 1 for c, original in zip(right_state.active_piece.cells, [3, 4, 5, 6]))
    assert right_state.active_piece.origin.col == 4
    
    # Down Shift
    down_state = move_piece(state, "down")
    assert all(c.row == 6 for c in down_state.active_piece.cells)
    assert down_state.active_piece.origin.row == 6

def test_movements_blocked():
    state = create_new_game("test")
    # Blocked by left boundary
    state.active_piece.cells = [Cell(row=5, col=0)]
    blocked_left = move_piece(state, "left")
    assert blocked_left.active_piece.cells[0].col == 0
    
    # Blocked by right boundary
    state.active_piece.cells = [Cell(row=5, col=BOARD_COLS-1)]
    blocked_right = move_piece(state, "right")
    assert blocked_right.active_piece.cells[0].col == BOARD_COLS-1
    
    # Blocked by settled block (stack collision)
    state.board[5][2] = 1
    state.active_piece.cells = [Cell(row=5, col=3)]
    blocked_stack = move_piece(state, "left")
    assert blocked_stack.active_piece.cells[0].col == 3

def test_immediate_lock_and_spawn():
    # Force piece to the bottom row, and move down
    state = create_new_game("test")
    state.active_piece.cells = [Cell(row=19, col=5)]
    state.active_piece.shape = "I"
    
    locked_state = move_piece(state, "down")
    # Verify piece is baked into board at bottom row
    assert locked_state.board[19][5] == 1  # Index of I shape is 1
    # Verify a new random active piece spawned at the top
    assert locked_state.active_piece is not None
    assert all(0 <= cell.row <= 1 for cell in locked_state.active_piece.cells)

def test_line_clears_1_to_4_rows():
    # 1 Line Clear
    board1 = [[0] * BOARD_COLS for _ in range(BOARD_ROWS)]
    board1[19] = [1] * BOARD_COLS
    res1, cleared1 = clear_completed_lines(board1)
    assert cleared1 == 1
    assert all(cell == 0 for row in res1 for cell in row)
    
    # 2 Line Clear
    board2 = [[0] * BOARD_COLS for _ in range(BOARD_ROWS)]
    board2[18] = [1] * BOARD_COLS
    board2[19] = [1] * BOARD_COLS
    res2, cleared2 = clear_completed_lines(board2)
    assert cleared2 == 2
    assert all(cell == 0 for row in res2 for cell in row)
    
    # 3 Line Clear
    board3 = [[0] * BOARD_COLS for _ in range(BOARD_ROWS)]
    board3[17] = [1] * BOARD_COLS
    board3[18] = [1] * BOARD_COLS
    board3[19] = [1] * BOARD_COLS
    res3, cleared3 = clear_completed_lines(board3)
    assert cleared3 == 3
    assert all(cell == 0 for row in res3 for cell in row)
    
    # 4 Line Clear (Tetris!)
    board4 = [[0] * BOARD_COLS for _ in range(BOARD_ROWS)]
    board4[16] = [1] * BOARD_COLS
    board4[17] = [1] * BOARD_COLS
    board4[18] = [1] * BOARD_COLS
    board4[19] = [1] * BOARD_COLS
    res4, cleared4 = clear_completed_lines(board4)
    assert cleared4 == 4
    assert all(cell == 0 for row in res4 for cell in row)

def test_spawning_collision_game_over():
    # Make spawning coordinates (cols 3-6, row 0-1) dirty with non-zero settled blocks,
    # but keep them as partial rows (not full rows) so they are NOT cleared during tick locking.
    board = [[0] * BOARD_COLS for _ in range(BOARD_ROWS)]
    board[0][3] = 1
    board[0][4] = 0  # partial row
    board[1][3] = 1
    board[1][4] = 0  # partial row
    
    active_piece = get_spawned_piece("I")
    # Force active piece to bottom row for locking
    active_piece.cells = [Cell(row=19, col=5)]
    
    from app.core.domain import GameState
    state = GameState(id="test", status="playing", board=board, active_piece=active_piece)
    
    # Tick down -> locks piece at bottom -> spawns next piece -> hits row 0/1 dirty cell -> game_over
    next_state = tick_game(state)
    assert next_state.status == "game_over"
