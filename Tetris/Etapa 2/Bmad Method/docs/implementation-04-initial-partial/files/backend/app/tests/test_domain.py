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
    state = GameState(id="test", status="playing", board=board, active_piece=active_piece, next_piece="I")
    
    # Tick down -> locks piece at bottom -> spawns next piece -> hits row 0/1 dirty cell -> game_over
    next_state = tick_game(state)
    assert next_state.status == "game_over"
    assert next_state.active_piece is None

def test_progression_multipliers():
    # 1 Line clear at Level 1 should score 100 * 1 = 100
    # Level is set to 1 + floor(total_lines / 10).
    # Level 1 to start, line count = 9. Clear 1 line -> lines = 10 -> level becomes 2.
    # Score should use the pre-lock level (1) multiplier, so points = 100 * 1 = 100.
    from app.core.domain import GameState, move_piece
    board = [[0] * BOARD_COLS for _ in range(BOARD_ROWS)]
    board[19] = [1] * BOARD_COLS
    board[19][5] = 0 # keep one column open for active piece to land
    
    active = get_spawned_piece("I")
    active.cells = [Cell(row=19, col=5)]
    
    state = GameState(
        id="test",
        status="playing",
        board=board,
        active_piece=active,
        score=0,
        total_lines=9,
        level=1,
        gravity_interval_ms=500,
        next_piece="O",
        hold_piece=None,
        can_hold=True
    )
    
    next_state = move_piece(state, "down")
    assert next_state.total_lines == 10
    assert next_state.level == 2
    assert next_state.score == 100 # prelock level 1 * 100
    assert next_state.gravity_interval_ms == 450 # 500 - 50 * (2 - 1)

def test_rng_counts(monkeypatch):
    draw_count = 0
    def mock_get_random_shape():
        nonlocal draw_count
        draw_count += 1
        return "O"
    
    monkeypatch.setattr("app.core.domain.get_random_shape", mock_get_random_shape)
    
    # 1. New game creation -> exact 2 draws
    state = create_new_game("test")
    assert draw_count == 2
    
    # 2. State peek (GET equivalent) -> exact 0 draws
    draw_count = 0
    from app.core.domain import GameState
    # Just inspect state
    _ = state.next_piece
    assert draw_count == 0
    
    # 3. First Hold (empty Hold slot) -> exact 1 draw (consumes next_piece, draws 1 new next_piece)
    from app.core.domain import hold_game
    draw_count = 0
    state2 = hold_game(state)
    assert draw_count == 1
    
    # 4. Occupied Hold swap -> exact 0 draws
    draw_count = 0
    state3 = hold_game(state2)
    assert draw_count == 0
    
    # 5. Rejected Hold (cooldown active) -> exact 0 draws
    draw_count = 0
    state4 = hold_game(state3)
    assert draw_count == 0
    
    # 6. Normal lock/spawn -> exact 1 draw
    from app.core.domain import move_piece
    draw_count = 0
    active = get_spawned_piece("O")
    active.cells = [Cell(row=19, col=5)]
    state_to_lock = GameState(
        id="test",
        status="playing",
        board=[[0] * BOARD_COLS for _ in range(BOARD_ROWS)],
        active_piece=active,
        score=0,
        total_lines=0,
        level=1,
        gravity_interval_ms=500,
        next_piece="O",
        hold_piece=None,
        can_hold=True
    )
    locked_state = move_piece(state_to_lock, "down")
    assert draw_count == 1

def test_obstructed_spawn_game_overs():
    # If standard spawn coords are obstructed, game over with active_piece = None
    from app.core.domain import GameState
    board = [[0] * BOARD_COLS for _ in range(BOARD_ROWS)]
    # Fill spawn rows cols 3-6 to block any spawn
    for col in range(3, 7):
        board[0][col] = 1
        board[1][col] = 1
        
    state = create_new_game("test")
    state.board = board
    
    # Trigger a hold swap that spawns a piece at origin, it should immediately be game over with active_piece=None
    from app.core.domain import hold_game
    next_state = hold_game(state)
    assert next_state.status == "game_over"
    assert next_state.active_piece is None

def test_non_rotational_o_piece_clears():
    # N=3 Clears Test
    # Precomplete rows 17, 18, 19 with 1s. Spawning/dropping O piece locks at row 15/16.
    from app.core.domain import GameState, move_piece
    board = [[0] * BOARD_COLS for _ in range(BOARD_ROWS)]
    board[17] = [1] * BOARD_COLS
    board[18] = [1] * BOARD_COLS
    board[19] = [1] * BOARD_COLS
    
    active = get_spawned_piece("O")
    # Place O piece exactly above precompleted rows 17-19
    active.origin = Cell(row=15, col=4)
    active.cells = [Cell(row=15, col=4), Cell(row=15, col=5), Cell(row=16, col=4), Cell(row=16, col=5)]
    
    state = GameState(
        id="test",
        status="playing",
        board=board,
        active_piece=active,
        score=0,
        total_lines=0,
        level=1,
        gravity_interval_ms=500,
        next_piece="I",
        hold_piece=None,
        can_hold=True
    )
    
    next_state = move_piece(state, "down")
    # Verify exactly 3 lines cleared (17, 18, 19)
    assert next_state.total_lines == 3
    assert next_state.score == 500 # 500 * level 1
    
    # N=4 Clears Test
    # Precomplete rows 16, 17, 18, 19.
    board_4 = [[0] * BOARD_COLS for _ in range(BOARD_ROWS)]
    board_4[16] = [1] * BOARD_COLS
    board_4[17] = [1] * BOARD_COLS
    board_4[18] = [1] * BOARD_COLS
    board_4[19] = [1] * BOARD_COLS
    
    active_4 = get_spawned_piece("O")
    active_4.origin = Cell(row=14, col=4)
    active_4.cells = [Cell(row=14, col=4), Cell(row=14, col=5), Cell(row=15, col=4), Cell(row=15, col=5)]
    
    state_4 = GameState(
        id="test-4",
        status="playing",
        board=board_4,
        active_piece=active_4,
        score=0,
        total_lines=0,
        level=1,
        gravity_interval_ms=500,
        next_piece="I",
        hold_piece=None,
        can_hold=True
    )
    
    next_state_4 = move_piece(state_4, "down")
    assert next_state_4.total_lines == 4
    assert next_state_4.score == 800 # 800 * level 1
