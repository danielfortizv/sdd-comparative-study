import uuid
import secrets
from typing import Dict, List, Optional
from app.models.schemas import GameSessionSchema, TetrominoSchema

# In-memory store for active game sessions, mapping UUID string -> GameSessionSchema
active_sessions: Dict[str, GameSessionSchema] = {}

TETROMINO_TEMPLATES = {
    "I": {"cells": [[0, 3], [0, 4], [0, 5], [0, 6]], "origin": [0, 4], "color": 1},
    "O": {"cells": [[0, 4], [0, 5], [1, 4], [1, 5]], "origin": [0, 4], "color": 2},
    "T": {"cells": [[0, 4], [1, 3], [1, 4], [1, 5]], "origin": [1, 4], "color": 3},
    "S": {"cells": [[0, 4], [0, 5], [1, 3], [1, 4]], "origin": [1, 4], "color": 4},
    "Z": {"cells": [[0, 3], [0, 4], [1, 4], [1, 5]], "origin": [1, 4], "color": 5},
    "J": {"cells": [[0, 3], [1, 3], [1, 4], [1, 5]], "origin": [1, 4], "color": 6},
    "L": {"cells": [[0, 5], [1, 3], [1, 4], [1, 5]], "origin": [1, 4], "color": 7},
}

def has_collision(board: List[List[int]], cells: List[List[int]]) -> bool:
    for row, col in cells:
        if not (0 <= row <= 19) or not (0 <= col <= 9):
            return True
        if board[row][col] != 0:
            return True
    return False

def create_session() -> GameSessionSchema:
    session_id = str(uuid.uuid4())
    board = [[0] * 10 for _ in range(20)]
    
    # Choose random piece type with equal probability (14.28%)
    piece_type = secrets.choice(["I", "O", "T", "S", "Z", "J", "L"])
    template = TETROMINO_TEMPLATES[piece_type]
    active_piece = TetrominoSchema(
        type=piece_type,
        cells=template["cells"],
        origin=template["origin"]
    )
    
    next_piece = secrets.choice(["I", "O", "T", "S", "Z", "J", "L"])
    
    session = GameSessionSchema(
        id=session_id,
        board=board,
        active_piece=active_piece,
        status="playing",
        score=0,
        total_lines=0,
        level=1,
        gravity_interval_ms=500,
        next_piece=next_piece,
        hold_piece=None,
        can_hold=True
    )
    active_sessions[session_id] = session
    return session

def move_session_piece(session_id: str, direction: str) -> GameSessionSchema:
    session = active_sessions.get(session_id)
    if not session or session.status == "game_over":
        return session

    active = session.active_piece
    if not active:
        return session

    cells = active.cells
    origin = active.origin

    if direction == "left":
        proposed_cells = [[r, c - 1] for r, c in cells]
        proposed_origin = [origin[0], origin[1] - 1]
    elif direction == "right":
        proposed_cells = [[r, c + 1] for r, c in cells]
        proposed_origin = [origin[0], origin[1] + 1]
    elif direction == "down":
        proposed_cells = [[r + 1, c] for r, c in cells]
        proposed_origin = [origin[0] + 1, origin[1]]
    else:
        return session

    # Check collision
    if not has_collision(session.board, proposed_cells):
        active.cells = proposed_cells
        active.origin = proposed_origin

    return session

def clear_lines_in_board(board: List[List[int]]) -> int:
    # Filter out completed rows (rows where all cells are non-zero)
    new_board = [row for row in board if any(cell == 0 for cell in row)]
    cleared_count = len(board) - len(new_board)
    
    # Prepend empty rows at the top
    for _ in range(cleared_count):
        new_board.insert(0, [0] * 10)
        
    # Mutate the original board in place
    for r in range(20):
        board[r] = new_board[r]
        
    return cleared_count

def tick_session(session_id: str) -> GameSessionSchema:
    session = active_sessions.get(session_id)
    if not session or session.status == "game_over":
        return session

    active = session.active_piece
    if not active:
        return session

    cells = active.cells
    origin = active.origin

    # Shift down by 1 row
    proposed_cells = [[r + 1, c] for r, c in cells]
    proposed_origin = [origin[0] + 1, origin[1]]

    if not has_collision(session.board, proposed_cells):
        # Move piece down
        active.cells = proposed_cells
        active.origin = proposed_origin
    else:
        # Collision detected: Lock the piece!
        color_id = TETROMINO_TEMPLATES[active.type]["color"]
        for r, c in cells:
            if 0 <= r <= 19 and 0 <= c <= 9:
                session.board[r][c] = color_id

        # Scan and clear horizontal lines (User Story 2)
        cleared_lines = clear_lines_in_board(session.board)

        # 1. Update score using the level prior to line clearing:
        level_before = session.level
        score_award = {1: 100, 2: 300, 3: 500, 4: 800}.get(cleared_lines, 0) * level_before
        session.score += score_award

        # 2. Update total lines
        session.total_lines += cleared_lines

        # 3. Recalculate level: 1 + floor(total_lines / 10)
        session.level = 1 + session.total_lines // 10

        # 4. Compute gravity_interval_ms: max(100, 500 - 50 * (level - 1))
        session.gravity_interval_ms = max(100, 500 - 50 * (session.level - 1))

        # 5. Reset can_hold
        session.can_hold = True

        # Spawn next piece from next_piece queue
        piece_type = session.next_piece
        template = TETROMINO_TEMPLATES[piece_type]
        new_piece = TetrominoSchema(
            type=piece_type,
            cells=template["cells"],
            origin=template["origin"]
        )
        
        # Populate new secure next_piece randomly
        session.next_piece = secrets.choice(["I", "O", "T", "S", "Z", "J", "L"])

        # Check for immediate spawn overlap (User Story 3)
        if has_collision(session.board, template["cells"]):
            session.status = "game_over"
            session.active_piece = None
        else:
            session.active_piece = new_piece

    return session

def hold_session_piece(session_id: str) -> GameSessionSchema:
    session = active_sessions.get(session_id)
    if not session or session.status == "game_over":
        return session

    if not session.can_hold:
        return session

    active = session.active_piece
    if not active:
        return session

    # Determine held piece to spawn and the new hold piece
    if session.hold_piece is None:
        # First time hold: store current active, spawn next_piece, generate new next_piece preview
        session.hold_piece = active.type
        spawn_type = session.next_piece
        session.next_piece = secrets.choice(["I", "O", "T", "S", "Z", "J", "L"])
    else:
        # Swap: old hold piece becomes active, current active is stored in hold
        old_hold = session.hold_piece
        session.hold_piece = active.type
        spawn_type = old_hold

    # Set up spawn
    template = TETROMINO_TEMPLATES[spawn_type]
    new_piece = TetrominoSchema(
        type=spawn_type,
        cells=template["cells"],
        origin=template["origin"]
    )

    # Check for immediate spawn overlap
    if has_collision(session.board, template["cells"]):
        session.status = "game_over"
        session.active_piece = None
    else:
        session.active_piece = new_piece

    session.can_hold = False
    return session
