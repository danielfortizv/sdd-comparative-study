import random
from typing import List, Optional, Tuple, Dict, Literal
from app.models import GameState, ActivePiece, Position

# Grid settings
ROWS = 20
COLS = 10

# Tetromino shapes defined as offsets (row_offset, col_offset) from the spawn origin
# Using standard initial orientations where all cells are row >= 0
SHAPES: Dict[str, List[Tuple[int, int]]] = {
    "I": [(0, -1), (0, 0), (0, 1), (0, 2)],
    "O": [(0, 0), (0, 1), (1, 0), (1, 1)],
    "T": [(0, -1), (0, 0), (0, 1), (1, 0)],
    "S": [(0, 0), (0, 1), (1, -1), (1, 0)],
    "Z": [(0, -1), (0, 0), (1, 0), (1, 1)],
    "J": [(0, -1), (0, 0), (0, 1), (1, 1)],
    "L": [(0, -1), (0, 0), (0, 1), (1, -1)]
}

# The default spawn origin for all pieces
SPAWN_ORIGIN = (0, 4)

def get_piece_cells(piece_type: str, origin_row: int, origin_col: int) -> List[Position]:
    """Calculate absolute coordinates for all cells of a piece from its origin."""
    offsets = SHAPES.get(piece_type, [])
    return [
        Position(row=origin_row + r_off, col=origin_col + c_off)
        for r_off, c_off in offsets
    ]

def init_new_game(game_id: str, fixed_first_piece: Optional[str] = None) -> GameState:
    """Initialize a brand new game board and spawn the first piece."""
    board = [[None for _ in range(COLS)] for _ in range(ROWS)]
    
    # Spawn first piece
    piece_type = fixed_first_piece or random.choice(list(SHAPES.keys()))
    spawn_row, spawn_col = SPAWN_ORIGIN
    cells = get_piece_cells(piece_type, spawn_row, spawn_col)
    
    active_piece = ActivePiece(
        type=piece_type,
        origin=Position(row=spawn_row, col=spawn_col),
        cells=cells
    )
    
    # Check if spawned piece immediately collides (though highly unlikely for brand new game)
    status: Literal["playing", "game_over"] = "playing"
    for cell in cells:
        if cell.row >= ROWS or cell.col < 0 or cell.col >= COLS or board[cell.row][cell.col] is not None:
            status = "game_over"
            
    return GameState(
        game_id=game_id,
        board=board,
        active_piece=active_piece,
        status=status
    )

def is_valid_position(board: List[List[Optional[str]]], cells: List[Position]) -> bool:
    """Verify if the piece can be placed at the target coordinates without collisions."""
    for cell in cells:
        # Check boundary collision
        if cell.row < 0 or cell.row >= ROWS:
            return False
        if cell.col < 0 or cell.col >= COLS:
            return False
        # Check settled block collision
        if board[cell.row][cell.col] is not None:
            return False
    return True

def move_piece(state: GameState, direction: str) -> GameState:
    """Move the active piece by 1 unit in the specified direction if valid."""
    if state.status == "game_over" or state.active_piece is None:
        return state
        
    origin = state.active_piece.origin
    piece_type = state.active_piece.type
    
    # Calculate proposed origin
    if direction == "left":
        new_origin = Position(row=origin.row, col=origin.col - 1)
    elif direction == "right":
        new_origin = Position(row=origin.row, col=origin.col + 1)
    elif direction == "down":
        new_origin = Position(row=origin.row + 1, col=origin.col)
    else:
        return state
        
    # Calculate target cells
    proposed_cells = get_piece_cells(piece_type, new_origin.row, new_origin.col)
    
    # Verify and apply
    if is_valid_position(state.board, proposed_cells):
        state.active_piece.origin = new_origin
        state.active_piece.cells = proposed_cells
        
    return state

def process_gravity_tick(state: GameState, fixed_next_piece: Optional[str] = None) -> GameState:
    """Advance the game state by one gravity tick."""
    if state.status == "game_over" or state.active_piece is None:
        return state
        
    origin = state.active_piece.origin
    piece_type = state.active_piece.type
    
    # Attempt to move the piece down by 1 row
    next_origin = Position(row=origin.row + 1, col=origin.col)
    proposed_cells = get_piece_cells(piece_type, next_origin.row, next_origin.col)
    
    if is_valid_position(state.board, proposed_cells):
        # Piece can move down, so update its position
        state.active_piece.origin = next_origin
        state.active_piece.cells = proposed_cells
    else:
        # Piece cannot move down, lock it in place!
        for cell in state.active_piece.cells:
            if 0 <= cell.row < ROWS and 0 <= cell.col < COLS:
                state.board[cell.row][cell.col] = piece_type
                
        # Clear any completed rows
        state.board = clear_lines(state.board)
        
        # Spawn subsequent tetromino
        next_type = fixed_next_piece or random.choice(list(SHAPES.keys()))
        spawn_row, spawn_col = SPAWN_ORIGIN
        new_cells = get_piece_cells(next_type, spawn_row, spawn_col)
        
        state.active_piece = ActivePiece(
            type=next_type,
            origin=Position(row=spawn_row, col=spawn_col),
            cells=new_cells
        )
        
        # Check game-over condition: does the new piece overlap with existing blocks?
        if not is_valid_position(state.board, new_cells):
            state.status = "game_over"
            state.active_piece = None  # Clear active piece on game-over
            
    return state

def clear_lines(board: List[List[Optional[str]]]) -> List[List[Optional[str]]]:
    """Find and clear fully locked horizontal rows, shifting above rows down."""
    new_board = [row for row in board if any(cell is None for cell in row)]
    cleared_count = ROWS - len(new_board)
    
    # Prepend new empty rows at the top
    for _ in range(cleared_count):
        new_board.insert(0, [None for _ in range(COLS)])
        
    return new_board
