from typing import List, Optional, Tuple, Literal
from pydantic import BaseModel

TetrominoType = Literal['I', 'O', 'T', 'S', 'Z', 'J', 'L']
GameStatus = Literal['playing', 'game_over']

class ActivePieceModel(BaseModel):
    type: TetrominoType
    origin: Tuple[int, int]
    cells: List[Tuple[int, int]]  # Absolute coordinates on the board

class GameStateModel(BaseModel):
    id: str
    board: List[List[Optional[str]]]  # 20 rows of 10 columns
    active_piece: Optional[ActivePieceModel] = None
    status: GameStatus
    score: int = 0
    total_lines: int = 0
    level: int = 1
    gravity_interval_ms: int = 500
    next_piece: TetrominoType
    hold_piece: Optional[TetrominoType] = None
    can_hold: bool = True
