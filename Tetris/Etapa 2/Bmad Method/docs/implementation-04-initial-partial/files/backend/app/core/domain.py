import random
from typing import List, Dict, Literal, Tuple, Optional
from pydantic import BaseModel, Field

# Board settings
BOARD_COLS = 10
BOARD_ROWS = 20

# Standard Tetromino shape templates
SHAPE_TEMPLATES = {
    "I": {
        "origin": {"row": 0, "col": 3},
        "cells": [{"row": 0, "col": 3}, {"row": 0, "col": 4}, {"row": 0, "col": 5}, {"row": 0, "col": 6}]
    },
    "J": {
        "origin": {"row": 0, "col": 3},
        "cells": [{"row": 0, "col": 3}, {"row": 1, "col": 3}, {"row": 1, "col": 4}, {"row": 1, "col": 5}]
    },
    "L": {
        "origin": {"row": 0, "col": 3},
        "cells": [{"row": 0, "col": 5}, {"row": 1, "col": 3}, {"row": 1, "col": 4}, {"row": 1, "col": 5}]
    },
    "O": {
        "origin": {"row": 0, "col": 4},
        "cells": [{"row": 0, "col": 4}, {"row": 0, "col": 5}, {"row": 1, "col": 4}, {"row": 1, "col": 5}]
    },
    "S": {
        "origin": {"row": 0, "col": 3},
        "cells": [{"row": 0, "col": 4}, {"row": 0, "col": 5}, {"row": 1, "col": 3}, {"row": 1, "col": 4}]
    },
    "T": {
        "origin": {"row": 0, "col": 3},
        "cells": [{"row": 0, "col": 4}, {"row": 1, "col": 3}, {"row": 1, "col": 4}, {"row": 1, "col": 5}]
    },
    "Z": {
        "origin": {"row": 0, "col": 3},
        "cells": [{"row": 0, "col": 3}, {"row": 0, "col": 4}, {"row": 1, "col": 4}, {"row": 1, "col": 5}]
    }
}

SHAPE_INDICES = {
    "I": 1, "J": 2, "L": 3, "O": 4, "S": 5, "T": 6, "Z": 7
}

class Cell(BaseModel):
    row: int
    col: int

class ActivePiece(BaseModel):
    shape: Literal["I", "J", "L", "O", "S", "T", "Z"]
    origin: Cell
    cells: List[Cell]

class GameState(BaseModel):
    id: str
    status: Literal["playing", "game_over"]
    board: List[List[int]] = Field(default_factory=lambda: [[0] * BOARD_COLS for _ in range(BOARD_ROWS)])
    active_piece: Optional[ActivePiece] = None
    score: int = 0
    total_lines: int = 0
    level: int = 1
    gravity_interval_ms: int = 500
    next_piece: str
    hold_piece: Optional[str] = None
    can_hold: bool = True

def get_random_shape() -> str:
    """Selects a random Tetromino shape."""
    return random.choice(list(SHAPE_TEMPLATES.keys()))

def get_spawned_piece(shape: str) -> ActivePiece:
    """Returns a new active piece of the given shape at spawn coordinates."""
    template = SHAPE_TEMPLATES[shape]
    return ActivePiece(
        shape=shape,
        origin=Cell(row=template["origin"]["row"], col=template["origin"]["col"]),
        cells=[Cell(row=c["row"], col=c["col"]) for c in template["cells"]]
    )

def is_valid_position(board: List[List[int]], cells: List[Cell]) -> bool:
    """Validates if the piece's cells are within bounds and do not overlap with settled blocks."""
    for cell in cells:
        if cell.col < 0 or cell.col >= BOARD_COLS:
            return False
        if cell.row < 0 or cell.row >= BOARD_ROWS:
            return False
        if board[cell.row][cell.col] > 0:
            return False
    return True

def bake_piece_into_board(board: List[List[int]], piece: ActivePiece) -> List[List[int]]:
    """Bakes the active piece blocks into the board grid as settled blocks."""
    new_board = [row[:] for row in board]
    color_index = SHAPE_INDICES[piece.shape]
    for cell in piece.cells:
        if 0 <= cell.row < BOARD_ROWS and 0 <= cell.col < BOARD_COLS:
            new_board[cell.row][cell.col] = color_index
    return new_board

def clear_completed_lines(board: List[List[int]]) -> Tuple[List[List[int]], int]:
    """Clears completed rows and shifts upper rows down. Returns the new board and lines cleared."""
    new_board = [row for row in board if any(cell == 0 for cell in row)]
    cleared_count = BOARD_ROWS - len(new_board)
    for _ in range(cleared_count):
        new_board.insert(0, [0] * BOARD_COLS)
    return new_board, cleared_count

def create_new_game(game_id: str) -> GameState:
    """Initializes a new game state."""
    shape = get_random_shape()
    next_shape = get_random_shape()
    active_piece = get_spawned_piece(shape)
    board = [[0] * BOARD_COLS for _ in range(BOARD_ROWS)]
    
    # Check for immediate collision at spawn
    status = "playing"
    if not is_valid_position(board, active_piece.cells):
        status = "game_over"
        active_piece = None
        
    return GameState(
        id=game_id,
        status=status,
        board=board,
        active_piece=active_piece,
        score=0,
        total_lines=0,
        level=1,
        gravity_interval_ms=500,
        next_piece=next_shape,
        hold_piece=None,
        can_hold=True
    )

def move_piece(state: GameState, direction: Literal["left", "right", "down"]) -> GameState:
    """Executes a move in the specified direction with authoritative validation."""
    if state.status == "game_over" or state.active_piece is None:
        return state

    # Compute prospective new cells and origin
    dr, dc = 0, 0
    if direction == "left":
        dc = -1
    elif direction == "right":
        dc = 1
    elif direction == "down":
        dr = 1

    new_cells = [Cell(row=c.row + dr, col=c.col + dc) for c in state.active_piece.cells]
    
    if direction in ("left", "right"):
        if is_valid_position(state.board, new_cells):
            new_origin = Cell(row=state.active_piece.origin.row + dr, col=state.active_piece.origin.col + dc)
            new_piece = ActivePiece(shape=state.active_piece.shape, origin=new_origin, cells=new_cells)
            return GameState(
                id=state.id,
                status=state.status,
                board=state.board,
                active_piece=new_piece,
                score=state.score,
                total_lines=state.total_lines,
                level=state.level,
                gravity_interval_ms=state.gravity_interval_ms,
                next_piece=state.next_piece,
                hold_piece=state.hold_piece,
                can_hold=state.can_hold
            )
        else:
            return state

    elif direction == "down":
        if is_valid_position(state.board, new_cells):
            new_origin = Cell(row=state.active_piece.origin.row + dr, col=state.active_piece.origin.col + dc)
            new_piece = ActivePiece(shape=state.active_piece.shape, origin=new_origin, cells=new_cells)
            return GameState(
                id=state.id,
                status=state.status,
                board=state.board,
                active_piece=new_piece,
                score=state.score,
                total_lines=state.total_lines,
                level=state.level,
                gravity_interval_ms=state.gravity_interval_ms,
                next_piece=state.next_piece,
                hold_piece=state.hold_piece,
                can_hold=state.can_hold
            )
        else:
            # Downward collision! Lock the piece immediately.
            locked_board = bake_piece_into_board(state.board, state.active_piece)
            cleared_board, cleared_count = clear_completed_lines(locked_board)
            
            # Score / Level / Gravity calculation
            pre_lock_level = state.level
            
            # Points for lock:
            points_map = {0: 0, 1: 100, 2: 300, 3: 500, 4: 800}
            awarded = points_map.get(cleared_count, 0) * pre_lock_level
            
            new_score = state.score + awarded
            new_total_lines = state.total_lines + cleared_count
            new_level = 1 + (new_total_lines // 10)
            new_gravity_interval_ms = max(100, 500 - 50 * (new_level - 1))
            
            # Spawn a new piece using current next_piece
            spawn_shape = state.next_piece
            next_piece_active = get_spawned_piece(spawn_shape)
            
            # Draw a new random next_piece
            new_next_piece = get_random_shape() # 1 draw
            
            status = "playing"
            active = next_piece_active
            if not is_valid_position(cleared_board, next_piece_active.cells):
                status = "game_over"
                active = None
                
            return GameState(
                id=state.id,
                status=status,
                board=cleared_board,
                active_piece=active,
                score=new_score,
                total_lines=new_total_lines,
                level=new_level,
                gravity_interval_ms=new_gravity_interval_ms,
                next_piece=new_next_piece,
                hold_piece=state.hold_piece,
                can_hold=True # Hold cooldown resets on lock
            )

def hold_game(state: GameState) -> GameState:
    """Performs a hold swap if legal."""
    if state.status == "game_over" or state.active_piece is None:
        return state
    
    if not state.can_hold:
        return state
    
    # We can hold! We transition.
    current_shape = state.active_piece.shape
    
    if state.hold_piece is None:
        # First hold: consumes next_piece preview
        new_hold = current_shape
        spawn_shape = state.next_piece
        new_next = get_random_shape() # Draw exactly 1 new random shape
        
        spawned = get_spawned_piece(spawn_shape)
        
        status = "playing"
        active = spawned
        if not is_valid_position(state.board, spawned.cells):
            status = "game_over"
            active = None
            
        return GameState(
            id=state.id,
            status=status,
            board=state.board,
            active_piece=active,
            score=state.score,
            total_lines=state.total_lines,
            level=state.level,
            gravity_interval_ms=state.gravity_interval_ms,
            next_piece=new_next,
            hold_piece=new_hold,
            can_hold=False
        )
    else:
        # Occupied hold swap: swaps with hold_piece, next_piece is unchanged (0 draws)
        new_hold = current_shape
        spawn_shape = state.hold_piece
        
        spawned = get_spawned_piece(spawn_shape)
        
        status = "playing"
        active = spawned
        if not is_valid_position(state.board, spawned.cells):
            status = "game_over"
            active = None
            
        return GameState(
            id=state.id,
            status=status,
            board=state.board,
            active_piece=active,
            score=state.score,
            total_lines=state.total_lines,
            level=state.level,
            gravity_interval_ms=state.gravity_interval_ms,
            next_piece=state.next_piece,
            hold_piece=new_hold,
            can_hold=False
        )

def tick_game(state: GameState) -> GameState:
    """Advances the game by one gravity tick, same logic as manual soft drop."""
    return move_piece(state, "down")
