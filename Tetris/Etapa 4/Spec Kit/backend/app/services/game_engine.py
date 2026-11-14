import uuid
import secrets
import threading
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from app.models.schemas import GameSessionSchema, TetrominoSchema

# Configure logger
logger = logging.getLogger("tetris.engine")

# In-memory store for active game sessions, mapping UUID string -> GameSessionSchema
active_sessions: Dict[str, GameSessionSchema] = {}

# Global thread-safety lock to serialize all state mutations (tick, move, hold, create)
state_lock = threading.Lock()

TROMINO_TYPES = ["I", "O", "T", "S", "Z", "J", "L"]

TETROMINO_TEMPLATES = {
    "I": {"cells": [[0, 3], [0, 4], [0, 5], [0, 6]], "origin": [0, 4], "color": 1},
    "O": {"cells": [[0, 4], [0, 5], [1, 4], [1, 5]], "origin": [0, 4], "color": 2},
    "T": {"cells": [[0, 4], [1, 3], [1, 4], [1, 5]], "origin": [1, 4], "color": 3},
    "S": {"cells": [[0, 4], [0, 5], [1, 3], [1, 4]], "origin": [1, 4], "color": 4},
    "Z": {"cells": [[0, 3], [0, 4], [1, 4], [1, 5]], "origin": [1, 4], "color": 5},
    "J": {"cells": [[0, 3], [1, 3], [1, 4], [1, 5]], "origin": [1, 4], "color": 6},
    "L": {"cells": [[0, 5], [1, 3], [1, 4], [1, 5]], "origin": [1, 4], "color": 7},
}

ROTATION_ORIENTATIONS = {
    "I": {
        0: [[0, -1], [0, 0], [0, 1], [0, 2]],
        1: [[-1, 0], [0, 0], [1, 0], [2, 0]],
        2: [[0, -2], [0, -1], [0, 0], [0, 1]],
        3: [[-2, 0], [-1, 0], [0, 0], [1, 0]],
    },
    "O": {
        0: [[0, 0], [0, 1], [1, 0], [1, 1]],
        1: [[0, 0], [0, 1], [1, 0], [1, 1]],
        2: [[0, 0], [0, 1], [1, 0], [1, 1]],
        3: [[0, 0], [0, 1], [1, 0], [1, 1]],
    },
    "T": {
        0: [[-1, 0], [0, -1], [0, 0], [0, 1]],
        1: [[-1, 0], [0, 0], [0, 1], [1, 0]],
        2: [[0, -1], [0, 0], [0, 1], [1, 0]],
        3: [[-1, 0], [0, -1], [0, 0], [1, 0]],
    },
    "S": {
        0: [[-1, 0], [-1, 1], [0, -1], [0, 0]],
        1: [[-1, 0], [0, 0], [0, 1], [1, 1]],
        2: [[0, 0], [0, 1], [1, -1], [1, 0]],
        3: [[-1, -1], [0, -1], [0, 0], [1, 0]],
    },
    "Z": {
        0: [[-1, -1], [-1, 0], [0, 0], [0, 1]],
        1: [[-1, 1], [0, 0], [0, 1], [1, 0]],
        2: [[0, -1], [0, 0], [1, 0], [1, 1]],
        3: [[-1, 0], [0, -1], [0, 0], [1, -1]],
    },
    "J": {
        0: [[-1, -1], [0, -1], [0, 0], [0, 1]],
        1: [[-1, 0], [-1, 1], [0, 0], [1, 0]],
        2: [[0, -1], [0, 0], [0, 1], [1, 1]],
        3: [[-1, 0], [0, 0], [1, -1], [1, 0]],
    },
    "L": {
        0: [[-1, 1], [0, -1], [0, 0], [0, 1]],
        1: [[-1, 0], [0, 0], [1, 0], [1, 1]],
        2: [[0, -1], [0, 0], [0, 1], [1, -1]],
        3: [[-1, -1], [-1, 0], [0, 0], [1, 0]],
    }
}

def find_current_orientation(piece_type: str, cells: List[List[int]], origin: List[int]) -> int:
    if piece_type == "O":
        return 0
    current_offsets = sorted([[r - origin[0], c - origin[1]] for r, c in cells])
    for o_idx in range(4):
        o_offsets = sorted(ROTATION_ORIENTATIONS[piece_type][o_idx])
        if current_offsets == o_offsets:
            return o_idx
    return 0  # fallback to spawn orientation

def has_collision(board: List[List[int]], cells: List[List[int]]) -> bool:
    for row, col in cells:
        if not (0 <= row <= 19) or not (0 <= col <= 9):
            return True
        if board[row][col] != 0:
            return True
    return False

def finalize_game_over(session: GameSessionSchema) -> None:
    """
    Saves completed game metrics (once per UUID) to SQLite.
    Marks is_persisted = True on successful insert.
    """
    if session.status != "game_over":
        return
    if session.is_persisted:
        return

    completed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    logger.info(f"Attempting finalization database write for session {session.id} (score={session.score})")
    
    from app.services.database import insert_high_score
    # This might raise an exception, which will be propagated up, leaving is_persisted = False
    success = insert_high_score(
        game_id=session.id,
        score=session.score,
        total_lines=session.total_lines,
        level=session.level,
        completed_at=completed_at
    )
    if success:
        session.is_persisted = True
        logger.info(f"Session {session.id} successfully persisted to SQLite.")

def create_session() -> GameSessionSchema:
    with state_lock:
        session_id = str(uuid.uuid4())
        board = [[0] * 10 for _ in range(20)]
        
        # Choose random piece type with equal probability (14.28%)
        piece_type = secrets.choice(TROMINO_TYPES)
        template = TETROMINO_TEMPLATES[piece_type]
        active_piece = TetrominoSchema(
            type=piece_type,
            cells=template["cells"],
            origin=template["origin"]
        )
        
        next_piece = secrets.choice(TROMINO_TYPES)
        
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
            can_hold=True,
            is_persisted=False
        )
        active_sessions[session_id] = session
        return session

def get_session_snapshot(session_id: str) -> Optional[GameSessionSchema]:
    """
    Thread-safe non-mutating state snapshot retrieval.
    Obtains the lock briefly to create a deep copy of the active session.
    """
    with state_lock:
        session = active_sessions.get(session_id)
        if not session:
            return None
        return session.model_copy(deep=True)

def move_session_piece(session_id: str, direction: str) -> Optional[GameSessionSchema]:
    with state_lock:
        session = active_sessions.get(session_id)
        if not session:
            return None

        # Mutating retry logic on terminal sessions
        if session.status == "game_over":
            if not session.is_persisted:
                finalize_game_over(session)
            return session

        active = session.active_piece
        if not active:
            return session

        cells = active.cells
        origin = active.origin

        if direction == "left":
            proposed_cells = [[r, c - 1] for r, c in cells]
            proposed_origin = [origin[0], origin[1] - 1]
            if not has_collision(session.board, proposed_cells):
                active.cells = proposed_cells
                active.origin = proposed_origin
        elif direction == "right":
            proposed_cells = [[r, c + 1] for r, c in cells]
            proposed_origin = [origin[0], origin[1] + 1]
            if not has_collision(session.board, proposed_cells):
                active.cells = proposed_cells
                active.origin = proposed_origin
        elif direction == "down":
            proposed_cells = [[r + 1, c] for r, c in cells]
            proposed_origin = [origin[0] + 1, origin[1]]
            if not has_collision(session.board, proposed_cells):
                active.cells = proposed_cells
                active.origin = proposed_origin
        elif direction in ("cw", "ccw"):
            if active.type == "O":
                return session

            current_o = find_current_orientation(active.type, cells, origin)
            if direction == "cw":
                new_o = (current_o + 1) % 4
            else:
                new_o = (current_o - 1) % 4

            new_offsets = ROTATION_ORIENTATIONS[active.type][new_o]

            # Try horizontal offsets: 0, -1, +1, -2, +2
            for dx in (0, -1, 1, -2, 2):
                proposed_cells = [[origin[0] + offset_r, origin[1] + offset_c + dx] for offset_r, offset_c in new_offsets]
                proposed_origin = [origin[0], origin[1] + dx]

                if not has_collision(session.board, proposed_cells):
                    active.cells = proposed_cells
                    active.origin = proposed_origin
                    break

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

def lock_piece_and_spawn_next(session: GameSessionSchema, active: TetrominoSchema) -> None:
    """
    Locks the current active piece to the board, clears completed lines,
    updates scoring/level state, and spawns the next tetromino.
    Triggers game finalization if immediate spawn overlap occurs.
    """
    # Collision detected: Lock the piece!
    color_id = TETROMINO_TEMPLATES[active.type]["color"]
    for r, c in active.cells:
        if 0 <= r <= 19 and 0 <= c <= 9:
            session.board[r][c] = color_id

    # Scan and clear horizontal lines
    cleared_lines = clear_lines_in_board(session.board)

    # Update score, lines, level, and progressive gravity
    level_before = session.level
    score_award = {1: 100, 2: 300, 3: 500, 4: 800}.get(cleared_lines, 0) * level_before
    session.score += score_award
    session.total_lines += cleared_lines
    session.level = 1 + session.total_lines // 10
    session.gravity_interval_ms = max(100, 500 - 50 * (session.level - 1))
    session.can_hold = True

    # Spawn next piece from preview queue
    piece_type = session.next_piece
    template = TETROMINO_TEMPLATES[piece_type]
    new_piece = TetrominoSchema(
        type=piece_type,
        cells=template["cells"],
        origin=template["origin"]
    )
    session.next_piece = secrets.choice(TROMINO_TYPES)

    # Check for immediate spawn overlap (Game Over)
    if has_collision(session.board, template["cells"]):
        session.status = "game_over"
        session.active_piece = None
        finalize_game_over(session)
    else:
        session.active_piece = new_piece

def tick_session(session_id: str) -> Optional[GameSessionSchema]:
    with state_lock:
        session = active_sessions.get(session_id)
        if not session:
            return None

        # Mutating retry logic on terminal sessions
        if session.status == "game_over":
            if not session.is_persisted:
                finalize_game_over(session)
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
            lock_piece_and_spawn_next(session, active)

        return session

def hold_session_piece(session_id: str) -> Optional[GameSessionSchema]:
    with state_lock:
        session = active_sessions.get(session_id)
        if not session:
            return None

        # Mutating retry logic on terminal sessions
        if session.status == "game_over":
            if not session.is_persisted:
                finalize_game_over(session)
            return session

        if not session.can_hold:
            return session

        active = session.active_piece
        if not active:
            return session

        # Determine held piece to spawn and the new hold piece
        if session.hold_piece is None:
            # First time hold: store current active, spawn next_piece, preview next
            session.hold_piece = active.type
            spawn_type = session.next_piece
            session.next_piece = secrets.choice(TROMINO_TYPES)
        else:
            # Swap: old hold piece becomes active, current active becomes held
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

        # Check for immediate spawn overlap (Obstructed Hold Game Over)
        if has_collision(session.board, template["cells"]):
            session.status = "game_over"
            session.active_piece = None
            finalize_game_over(session)
        else:
            session.active_piece = new_piece

        session.can_hold = False
        return session
