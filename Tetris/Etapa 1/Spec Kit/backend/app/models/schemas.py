from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

class TetrominoSchema(BaseModel):
    type: str = Field(..., description="One of 'I', 'O', 'T', 'S', 'Z', 'J', 'L'")
    cells: List[List[int]] = Field(..., description="Exactly 4 coordinate pairs: [[row, col], ...]")
    origin: List[int] = Field(..., description="Pivot coordinate: [row, col]")

    @field_validator('type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in {"I", "O", "T", "S", "Z", "J", "L"}:
            raise ValueError("Type must be one of 'I', 'O', 'T', 'S', 'Z', 'J', 'L'")
        return v

    @field_validator('cells')
    @classmethod
    def validate_cells(cls, v: List[List[int]]) -> List[List[int]]:
        if len(v) != 4:
            raise ValueError("Cells must contain exactly 4 coordinate pairs")
        for cell in v:
            if len(cell) != 2:
                raise ValueError("Each cell coordinate must be of length 2")
            row, col = cell[0], cell[1]
            if not (0 <= row <= 19) or not (0 <= col <= 9):
                raise ValueError(f"Cell coordinates must be bounded: row [0, 19], col [0, 9]. Got row={row}, col={col}")
        return v

    @field_validator('origin')
    @classmethod
    def validate_origin(cls, v: List[int]) -> List[int]:
        if len(v) != 2:
            raise ValueError("Origin must be a coordinate pair of length 2")
        row, col = v[0], v[1]
        if not (0 <= row <= 19) or not (0 <= col <= 9):
            raise ValueError(f"Origin coordinates must be bounded: row [0, 19], col [0, 9]. Got row={row}, col={col}")
        return v

class GameSessionSchema(BaseModel):
    id: str = Field(..., description="Unique UUID string representing the game session")
    board: List[List[int]] = Field(..., description="20x10 grid. 0 = empty cell; 1-7 = settled piece colors")
    active_piece: Optional[TetrominoSchema] = Field(None, alias="activePiece")
    status: str = Field(..., description="Session status: 'playing' or 'game_over'")

    class Config:
        populate_by_name = True

    @field_validator('board')
    @classmethod
    def validate_board(cls, v: List[List[int]]) -> List[List[int]]:
        if len(v) != 20:
            raise ValueError("Board must have exactly 20 rows")
        for row_idx, row in enumerate(v):
            if len(row) != 10:
                raise ValueError(f"Row {row_idx} must have exactly 10 columns")
            for col_idx, cell in enumerate(row):
                if not (0 <= cell <= 7):
                    raise ValueError(f"Cell value must be between 0 and 7. Got {cell} at row {row_idx}, col {col_idx}")
        return v

    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in {"playing", "game_over"}:
            raise ValueError("Status must be 'playing' or 'game_over'")
        return v

class MoveRequest(BaseModel):
    direction: str = Field(..., description="Direction of manual movement: 'left', 'right', 'down'")

    @field_validator('direction')
    @classmethod
    def validate_direction(cls, v: str) -> str:
        if v not in {"left", "right", "down"}:
            raise ValueError("Direction must be one of 'left', 'right', 'down'")
        return v
