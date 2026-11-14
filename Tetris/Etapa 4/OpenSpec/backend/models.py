from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from typing import List, Optional

class ActivePiece(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: str
    cells: List[List[int]] = Field(description="Absolute board coordinates of active piece cells [[row, col], ...]")
    origin: List[int] = Field(description="Active piece coordinate origin [row, col]")
    orientation: int = Field(default=0, description="Active piece orientation (0-3)")

class GameState(BaseModel):
    model_config = ConfigDict(extra="forbid")
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
    orientation: int = Field(default=0, description="Active piece orientation (0-3)")

class MoveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    direction: str = Field(description="Move direction: 'left', 'right', 'down', 'clockwise', or 'counterclockwise'")

class GameCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

class HighScoreEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    game_id: str
    score: int
    total_lines: int
    level: int
    completed_at: str

class HighScoresResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scores: List[HighScoreEntry]

# --- Milestone 3: Real-Time Duel WebSocket Models ---

from typing import Literal, Any
import datetime
import hashlib

def get_piece_at_index(index: int, seed: int) -> str:
    piece_types = ["I", "O", "T", "J", "L", "S", "Z"]
    h = hashlib.sha256(f"{seed}-{index}".encode("utf-8")).hexdigest()
    val = int(h[:8], 16)
    return piece_types[val % 7]

class ActionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    action: Literal["move_left", "move_right", "rotate_clockwise", "rotate_counterclockwise", "soft_drop", "hard_drop", "hold"]
    seq: int = Field(ge=0, description="Sequence number of player action")
    room_id: str = Field(max_length=64, pattern=r"^[a-zA-Z0-9_\-]+$")
    player_id: str = Field(max_length=64, pattern=r"^[a-zA-Z0-9_\-]+$")
    generation: int = Field(ge=0, description="Board spawn generation")

    @field_validator("seq", "generation", mode="before")
    @classmethod
    def validate_strict_int(cls, v: Any) -> int:
        if type(v) is not int or v is True or v is False:
            raise ValueError("Must be a strict non-negative integer")
        if v < 0:
            raise ValueError("Must be a strict non-negative integer")
        return v

class StartPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    room_id: str = Field(max_length=64, pattern=r"^[a-zA-Z0-9_\-]+$")
    player1_id: str = Field(max_length=64, pattern=r"^[a-zA-Z0-9_\-]+$")
    player2_id: str = Field(max_length=64, pattern=r"^[a-zA-Z0-9_\-]+$")

class DuelBoardStatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    room_id: str = Field(max_length=64, pattern=r"^[a-zA-Z0-9_\-]+$")
    seat: Literal[1, 2] = Field(description="Seat index (1 or 2)")
    player_id: str = Field(max_length=64, pattern=r"^[a-zA-Z0-9_\-]+$")
    board: List[List[Optional[str]]] = Field(description="20x10 grid")
    active_piece: Optional[ActivePiece] = None
    status: Literal["playing", "game_over"]
    score: int
    total_lines: int
    level: int
    gravity_interval_ms: int
    next_piece: str
    hold_piece: Optional[str] = None
    can_hold: bool
    revision: int = Field(description="Monotonic state revision")
    generation: int = Field(default=0, description="Board spawn generation")
    last_processed_seq: int = Field(description="Last processed client sequence")

class OutcomePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    room_id: str = Field(max_length=64, pattern=r"^[a-zA-Z0-9_\-]+$")
    winner_id: Optional[str] = Field(default=None, max_length=64, pattern=r"^[a-zA-Z0-9_\-]+$")
    loser_id: Optional[str] = Field(default=None, max_length=64, pattern=r"^[a-zA-Z0-9_\-]+$")
    is_draw: bool
    reason: Literal["top_out", "forfeit"]

class ErrorPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    message: str

class WSMessageEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    v: Literal[1] = Field(default=1, description="Protocol version, must be 1")
    type: Literal["action", "heartbeat", "start", "state", "outcome", "error"] = Field(description="Message type")
    timestamp: str = Field(description="ISO-8601 timestamp string")
    seq: int = Field(description="Sequence number")
    payload: Any = Field(description="Message payload")

    @field_validator("v", mode="before")
    @classmethod
    def validate_v(cls, v: Any) -> int:
        if type(v) is not int or v is True or v is False:
            raise ValueError("v must be strict integer 1")
        if v != 1:
            raise ValueError("v must be strict integer 1")
        return v

    @field_validator("seq")
    @classmethod
    def validate_seq(cls, v: Any) -> int:
        if type(v) is not int or v < -1:
            raise ValueError("seq must be a strict non-negative integer or -1")
        return v

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        try:
            datetime.datetime.fromisoformat(v.replace("Z", "+00:00"))
        except Exception:
            raise ValueError("timestamp must be a valid ISO-8601 string")
        return v

    @model_validator(mode="after")
    def validate_payload_type(self) -> 'WSMessageEnvelope':
        t = self.type
        p = self.payload
        try:
            if t == "action":
                if isinstance(p, dict):
                    self.payload = ActionPayload(**p)
                elif not isinstance(p, ActionPayload):
                    raise ValueError("payload must be ActionPayload for type 'action'")
            elif t == "heartbeat":
                if p is not None and not isinstance(p, dict):
                    raise ValueError("payload must be None or dict for type 'heartbeat'")
            elif t == "start":
                if isinstance(p, dict):
                    self.payload = StartPayload(**p)
                elif not isinstance(p, StartPayload):
                    raise ValueError("payload must be StartPayload for type 'start'")
            elif t == "state":
                if isinstance(p, dict):
                    self.payload = DuelBoardStatePayload(**p)
                elif not isinstance(p, DuelBoardStatePayload):
                    raise ValueError("payload must be DuelBoardStatePayload for type 'state'")
            elif t == "outcome":
                if isinstance(p, dict):
                    self.payload = OutcomePayload(**p)
                elif not isinstance(p, OutcomePayload):
                    raise ValueError("payload must be OutcomePayload for type 'outcome'")
            elif t == "error":
                if isinstance(p, dict):
                    self.payload = ErrorPayload(**p)
                elif not isinstance(p, ErrorPayload):
                    raise ValueError("payload must be ErrorPayload for type 'error'")
        except Exception as e:
            raise ValueError(f"Payload validation failed for type '{t}': {str(e)}")
        return self

    @model_validator(mode="after")
    def validate_outer_payload_seq(self) -> 'WSMessageEnvelope':
        if self.type == "action" and isinstance(self.payload, ActionPayload):
            if self.seq != self.payload.seq:
                raise ValueError("Outer seq and payload seq must be identical")
        return self

    @model_validator(mode="after")
    def validate_size(self) -> 'WSMessageEnvelope':
        try:
            json_str = self.model_dump_json()
            if len(json_str.encode('utf-8')) > 4096:
                raise ValueError("Frame size exceeds 4096-byte limit")
        except Exception as e:
            if "Frame size exceeds" in str(e):
                raise
        return self
