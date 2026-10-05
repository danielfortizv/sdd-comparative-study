import uuid
import random
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
    piece_type = random.choice(["I", "O", "T", "S", "Z", "J", "L"])
    template = TETROMINO_TEMPLATES[piece_type]
    active_piece = TetrominoSchema(
        type=piece_type,
        cells=template["cells"],
        origin=template["origin"]
    )
    
    session = GameSessionSchema(
        id=session_id,
        board=board,
        active_piece=active_piece,
        status="playing"
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
        clear_lines_in_board(session.board)

        # Spawn next piece
        piece_type = random.choice(["I", "O", "T", "S", "Z", "J", "L"])
        template = TETROMINO_TEMPLATES[piece_type]
        new_piece = TetrominoSchema(
            type=piece_type,
            cells=template["cells"],
            origin=template["origin"]
        )

        # Check for immediate spawn overlap (User Story 3)
        if has_collision(session.board, template["cells"]):
            session.status = "game_over"
            session.active_piece = None
        else:
            session.active_piece = new_piece

    return session
