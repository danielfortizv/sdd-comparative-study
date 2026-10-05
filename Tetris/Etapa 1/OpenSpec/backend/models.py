from pydantic import BaseModel, Field
from typing import List, Optional

class ActivePiece(BaseModel):
    type: str
    cells: List[List[int]] = Field(description="Absolute board coordinates of active piece cells [[row, col], ...]")
    origin: List[int] = Field(description="Active piece coordinate origin [row, col]")

class GameState(BaseModel):
    id: str
    board: List[List[Optional[str]]] = Field(description="20x10 grid with null for empty and block type string for settled blocks")
    active_piece: Optional[ActivePiece] = None
    status: str = Field(description="Game status: 'playing' or 'game_over'")

class MoveRequest(BaseModel):
    direction: str = Field(description="Move direction: 'left', 'right', or 'down'")
