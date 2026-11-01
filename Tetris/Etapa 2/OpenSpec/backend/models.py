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
    score: int = Field(default=0, description="Current game score")
    total_lines: int = Field(default=0, description="Total rows cleared")
    level: int = Field(default=1, description="Current game level")
    gravity_interval_ms: int = Field(default=500, description="Dynamic gravity interval in milliseconds")
    next_piece: str = Field(description="Next piece type string")
    hold_piece: Optional[str] = Field(default=None, description="Held piece type string")
    can_hold: bool = Field(default=True, description="Whether hold action is currently available")

class MoveRequest(BaseModel):
    direction: str = Field(description="Move direction: 'left', 'right', or 'down'")
