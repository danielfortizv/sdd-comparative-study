import random
from typing import List, Dict, Literal, Tuple
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
    active_piece: ActivePiece

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
    active_piece = get_spawned_piece(shape)
    board = [[0] * BOARD_COLS for _ in range(BOARD_ROWS)]
    
    # Check for immediate collision at spawn
    status = "playing"
    if not is_valid_position(board, active_piece.cells):
        status = "game_over"
        
    return GameState(
        id=game_id,
        status=status,
        board=board,
        active_piece=active_piece
    )

def move_piece(state: GameState, direction: Literal["left", "right", "down"]) -> GameState:
    """Executes a move in the specified direction with authoritative validation."""
    if state.status == "game_over":
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
            return GameState(id=state.id, status=state.status, board=state.board, active_piece=new_piece)
        else:
            return state

    elif direction == "down":
        if is_valid_position(state.board, new_cells):
            new_origin = Cell(row=state.active_piece.origin.row + dr, col=state.active_piece.origin.col + dc)
            new_piece = ActivePiece(shape=state.active_piece.shape, origin=new_origin, cells=new_cells)
            return GameState(id=state.id, status=state.status, board=state.board, active_piece=new_piece)
        else:
            # Downward collision! Lock the piece immediately.
            locked_board = bake_piece_into_board(state.board, state.active_piece)
            cleared_board, _ = clear_completed_lines(locked_board)
            
            # Spawn a new piece
            next_shape = get_random_shape()
            next_piece = get_spawned_piece(next_shape)
            
            status = "playing"
            if not is_valid_position(cleared_board, next_piece.cells):
                status = "game_over"
                
            return GameState(id=state.id, status=status, board=cleared_board, active_piece=next_piece)

def tick_game(state: GameState) -> GameState:
    """Advances the game by one gravity tick, same logic as manual soft drop."""
    return move_piece(state, "down")
