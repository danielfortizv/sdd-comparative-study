from pydantic import BaseModel
from typing import List, Optional, Literal

class Position(BaseModel):
    row: int
    col: int

class ActivePiece(BaseModel):
    type: str
    origin: Position
    cells: List[Position]

class GameState(BaseModel):
    game_id: str
    board: List[List[Optional[str]]]
    active_piece: Optional[ActivePiece]
    status: Literal["playing", "game_over"]

class MoveRequest(BaseModel):
    direction: Literal["left", "right", "down"]
    
class ErrorResponse(BaseModel):
    detail: str
