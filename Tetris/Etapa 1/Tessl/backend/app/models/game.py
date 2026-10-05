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
    active_piece: Optional[ActivePieceModel]
    status: GameStatus
