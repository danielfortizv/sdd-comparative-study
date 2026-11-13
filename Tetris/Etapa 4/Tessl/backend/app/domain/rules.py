from typing import List, Optional, Tuple, Literal, Callable
from app.models.game import GameStateModel, ActivePieceModel
from app.domain.pieces import get_relative_cells, get_random_piece_type

def is_legal_position(board: List[List[Optional[str]]], relative_cells: List[Tuple[int, int]], origin: Tuple[int, int]) -> bool:
    for r, c in relative_cells:
        abs_row = origin[0] + r
        abs_col = origin[1] + c
        if abs_row < 0 or abs_row >= 20 or abs_col < 0 or abs_col >= 10:
            return False
        if board[abs_row][abs_col] is not None:
            return False
    return True

def lock_piece(board: List[List[Optional[str]]], active_piece_type: str, absolute_cells: List[Tuple[int, int]]) -> None:
    for r, c in absolute_cells:
        if 0 <= r < 20 and 0 <= c < 10:
            board[r][c] = active_piece_type

def clear_lines(board: List[List[Optional[str]]]) -> List[List[Optional[str]]]:
    # Completed rows: rows where all 10 columns are filled with non-null settled blocks
    new_board = [row for row in board if any(cell is None for cell in row)]
    cleared_count = len(board) - len(new_board)
    # Insert empty rows at the top to maintain the 20-row height
    for _ in range(cleared_count):
        new_board.insert(0, [None] * 10)
    return new_board

def get_score_for_lines(cleared: int, level: int) -> int:
    if cleared == 1:
        return 100 * level
    elif cleared == 2:
        return 300 * level
    elif cleared == 3:
        return 500 * level
    elif cleared == 4:
        return 800 * level
    return 0

def tick_game(state: GameStateModel, piece_supplier: Optional[Callable[[], str]] = None) -> GameStateModel:
    if state.status == "game_over":
        return state

    if state.active_piece is None:
        return state

    active = state.active_piece
    relative_cells = get_relative_cells(active.type, active.orientation)

    # Try moving down
    next_origin = (active.origin[0] + 1, active.origin[1])
    if is_legal_position(state.board, relative_cells, next_origin):
        active.origin = next_origin
        active.cells = [(next_origin[0] + r, next_origin[1] + c) for r, c in relative_cells]
        state.board_revision += 1
    else:
        # Trigger locking sequence
        lock_piece(state.board, active.type, active.cells)

        # Count completed lines
        n_cleared = sum(1 for row in state.board if all(cell is not None for cell in row))

        # Calculate score points based on pre-lock level
        pre_lock_level = state.level
        points = get_score_for_lines(n_cleared, pre_lock_level)
        state.score += points

        # Clear lines
        state.board = clear_lines(state.board)

        # Update total lines, level, and gravity interval
        state.total_lines += n_cleared
        state.level = 1 + (state.total_lines // 10)
        state.gravity_interval_ms = max(100, 500 - 50 * (state.level - 1))

        # Check Row-Zero Locking:
        # If locked piece contains cells in row 0, set status "game_over" immediately.
        # Do NOT spawn a new piece, do NOT consume next_piece, set active_piece = None.
        is_locked_at_row_zero = any(r == 0 for r, c in active.cells) or active.origin[0] == 0

        if is_locked_at_row_zero:
            state.status = "game_over"
            state.active_piece = None
        else:
            # Spawn a new random piece from next_piece
            new_type = state.next_piece
            new_rel = get_relative_cells(new_type, 0)
            spawn_origin = (0, 3)

            # Draw a new random piece for state.next_piece
            if piece_supplier:
                state.next_piece = piece_supplier()
            else:
                state.next_piece = get_random_piece_type()
            state.can_hold = True

            if is_legal_position(state.board, new_rel, spawn_origin):
                state.active_piece = ActivePieceModel(
                    type=new_type,
                    origin=spawn_origin,
                    cells=[(spawn_origin[0] + r, spawn_origin[1] + c) for r, c in new_rel],
                    orientation=0
                )
            else:
                state.status = "game_over"
                state.active_piece = None
        
        state.board_revision += 1

    return state

def move_game(state: GameStateModel, direction: Literal['left', 'right', 'down'], piece_supplier: Optional[Callable[[], str]] = None) -> GameStateModel:
    if state.status == "game_over":
        return state

    if state.active_piece is None:
        return state

    active = state.active_piece
    relative_cells = get_relative_cells(active.type, active.orientation)

    if direction == "left":
        next_origin = (active.origin[0], active.origin[1] - 1)
        if is_legal_position(state.board, relative_cells, next_origin):
            active.origin = next_origin
            active.cells = [(next_origin[0] + r, next_origin[1] + c) for r, c in relative_cells]
            state.board_revision += 1
    elif direction == "right":
        next_origin = (active.origin[0], active.origin[1] + 1)
        if is_legal_position(state.board, relative_cells, next_origin):
            active.origin = next_origin
            active.cells = [(next_origin[0] + r, next_origin[1] + c) for r, c in relative_cells]
            state.board_revision += 1
    elif direction == "down":
        return tick_game(state, piece_supplier)

    return state

def hold_game(state: GameStateModel, piece_supplier: Optional[Callable[[], str]] = None) -> GameStateModel:
    if state.status == "game_over" or not state.can_hold:
        return state

    if state.active_piece is None:
        return state

    current_type = state.active_piece.type

    if state.hold_piece is None:
        # First Hold
        state.hold_piece = current_type
        new_type = state.next_piece
        # Draw a new random piece for state.next_piece
        if piece_supplier:
            state.next_piece = piece_supplier()
        else:
            state.next_piece = get_random_piece_type()
    else:
        # Swap Hold
        new_type = state.hold_piece
        state.hold_piece = current_type

    state.can_hold = False

    # Spawn new piece at (0, 3) with orientation 0
    new_rel = get_relative_cells(new_type, 0)
    spawn_origin = (0, 3)
    if is_legal_position(state.board, new_rel, spawn_origin):
        state.active_piece = ActivePieceModel(
            type=new_type,
            origin=spawn_origin,
            cells=[(spawn_origin[0] + r, spawn_origin[1] + c) for r, c in new_rel],
            orientation=0
        )
    else:
        state.status = "game_over"
        state.active_piece = None

    state.board_revision += 1
    return state

def rotate_game(state: GameStateModel, direction: Literal['cw', 'ccw']) -> GameStateModel:
    if state.status == "game_over":
        return state

    if state.active_piece is None:
        return state

    active = state.active_piece

    # 'O' piece is a strict no-op
    if active.type == 'O':
        return state

    # Cyclic orientations
    if direction == 'cw':
        target_orientation = (active.orientation + 1) % 4
    elif direction == 'ccw':
        target_orientation = (active.orientation - 1) % 4
    else:
        return state

    target_relative_cells = get_relative_cells(active.type, target_orientation)

    # Try horizontal kick offsets: 0, -1, +1, -2, +2
    for dc in [0, -1, +1, -2, +2]:
        next_origin = (active.origin[0], active.origin[1] + dc)
        if is_legal_position(state.board, target_relative_cells, next_origin):
            active.orientation = target_orientation
            active.origin = next_origin
            active.cells = [(next_origin[0] + r, next_origin[1] + c) for r, c in target_relative_cells]
            state.board_revision += 1
            return state

    # If no offset is valid, rotation is rejected: state remains completely unchanged
    return state
