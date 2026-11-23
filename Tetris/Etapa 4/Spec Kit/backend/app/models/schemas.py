from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Optional, Any

class CreateGameRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid"  # Strictly reject unexpected parameters inside POST request body
    )

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
    score: int = Field(0, ge=0, description="Current game score")
    total_lines: int = Field(0, ge=0, description="Cumulative cleared line count")
    level: int = Field(1, ge=1, description="Current level")
    gravity_interval_ms: int = Field(500, ge=100, le=500, description="Progressive gravity interval in milliseconds")
    next_piece: str = Field(..., description="Type of the queued next piece")
    hold_piece: Optional[str] = Field(None, description="Type of the held piece")
    can_hold: bool = Field(True, description="Whether the player can use Hold in this turn")
    is_persisted: bool = Field(False, exclude=True, description="In-memory flag to prevent duplicate persistence/mutations")
    active_piece_generation: int = Field(0, ge=0, alias="activePieceGeneration")
    last_processed_seq_num: int = Field(0, ge=0, alias="lastProcessedSeqNum")
    last_action_seat: Optional[str] = Field(None, alias="lastActionSeat")
    last_action_seq: Optional[int] = Field(None, alias="lastActionSeq")
    last_action_observable_change: Optional[bool] = Field(None, alias="lastActionObservableChange")
    player_id: Optional[str] = Field(None, alias="playerId")

    model_config = ConfigDict(
        populate_by_name=True
    )

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

    @field_validator('next_piece')
    @classmethod
    def validate_next_piece(cls, v: str) -> str:
        if v not in {"I", "O", "T", "S", "Z", "J", "L"}:
            raise ValueError("next_piece must be one of 'I', 'O', 'T', 'S', 'Z', 'J', 'L'")
        return v

    @field_validator('hold_piece')
    @classmethod
    def validate_hold_piece(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in {"I", "O", "T", "S", "Z", "J", "L"}:
            raise ValueError("hold_piece must be one of 'I', 'O', 'T', 'S', 'Z', 'J', 'L'")
        return v

class MoveRequest(BaseModel):
    direction: str = Field(..., description="Direction of manual movement: 'left', 'right', 'down', 'cw', 'ccw'")

    model_config = ConfigDict(
        extra="forbid"  # Strictly reject unexpected parameters inside POST request body
    )

    @field_validator('direction')
    @classmethod
    def validate_direction(cls, v: str) -> str:
        if v not in {"left", "right", "down", "cw", "ccw"}:
            raise ValueError("Direction must be one of 'left', 'right', 'down', 'cw', 'ccw'")
        return v

class HighScoreEntrySchema(BaseModel):
    game_id: str = Field(..., description="UUID of the completed game session")
    score: int = Field(..., ge=0, description="The final game score")
    total_lines: int = Field(..., ge=0, description="Number of lines cleared")
    level: int = Field(..., ge=1, description="Final level reached")
    completed_at: str = Field(..., description="UTC completion timestamp in ISO-8601 format")

class LeaderboardResponseSchema(BaseModel):
    scores: List[HighScoreEntrySchema]

class WSActionPayload(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True
    )
    seq_num: int = Field(..., ge=1, le=9007199254740991)
    generation: int = Field(..., ge=0, le=9007199254740991)
    action_type: str = Field(...)

    @field_validator('seq_num', 'generation')
    @classmethod
    def validate_ints_no_bool(cls, v: Any) -> int:
        if isinstance(v, bool):
            raise ValueError("Boolean values are not allowed for integer fields")
        return v

    @field_validator('action_type')
    @classmethod
    def validate_action_type(cls, v: str) -> str:
        if v not in {"left", "right", "down", "cw", "ccw", "hold"}:
            raise ValueError("action_type must be one of 'left', 'right', 'down', 'cw', 'ccw', 'hold'")
        return v

class WSActionMessage(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True
    )
    v: int = Field(..., ge=1, le=1)
    event: str = Field(..., pattern="^action$")
    payload: WSActionPayload

    @field_validator('v')
    @classmethod
    def validate_v_no_bool(cls, v: Any) -> int:
        if isinstance(v, bool):
            raise ValueError("Boolean values are not allowed for version field")
        return v

