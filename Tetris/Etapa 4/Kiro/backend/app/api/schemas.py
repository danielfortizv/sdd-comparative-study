"""Request and response schemas plus domain-to-JSON serialization."""

from __future__ import annotations

from typing import List, Literal, Optional, Tuple

from pydantic import BaseModel, ConfigDict

from ..domain.models import Game, PieceType

# Stable integer codes for board serialization (0 = empty).
TYPE_CODES: dict[PieceType, int] = {
    "I": 1,
    "O": 2,
    "T": 3,
    "S": 4,
    "Z": 5,
    "J": 6,
    "L": 7,
}


class CreateGameRequest(BaseModel):
    """Body for the create-game endpoint.

    Has no fields; ``extra="forbid"`` rejects any client-supplied score
    metadata or arbitrary game id if a body is sent. A bodyless request remains
    valid and still creates a game (Req 6.2, 6.4).
    """

    model_config = ConfigDict(extra="forbid")


class MoveRequest(BaseModel):
    """Body for the move endpoint.

    ``extra="forbid"`` rejects any field beyond ``direction``; an invalid or
    missing ``direction`` yields HTTP 422 (Req 6.3, 6.6).
    """

    model_config = ConfigDict(extra="forbid")

    direction: Literal["left", "right", "down"]


class RotateRequest(BaseModel):
    """Body for the rotate endpoint.

    Mirrors ``MoveRequest`` hardening: ``extra="forbid"`` rejects any field
    beyond ``direction`` (Req 1.6), and ``direction`` is constrained to the two
    documented, case-sensitive values. Any other string, a missing field, or a
    non-string value (bool/number/array/object/null) fails validation and yields
    HTTP 422 (Req 1.5, 1.6).
    """

    model_config = ConfigDict(extra="forbid")

    direction: Literal["cw", "ccw"]


class ActivePieceOut(BaseModel):
    """Serialized active piece."""

    type: PieceType
    origin: Tuple[int, int]
    cells: List[Tuple[int, int]]


class GameStateOut(BaseModel):
    """Serialized game state returned by every endpoint."""

    id: str
    status: str
    board: List[List[int]]
    active_piece: Optional[ActivePieceOut] = None
    # --- Stage 2 fields ---
    score: int
    total_lines: int
    level: int
    gravity_interval_ms: int
    next_piece: PieceType
    hold_piece: Optional[PieceType] = None
    can_hold: bool


class HighScoreEntryOut(BaseModel):
    """One leaderboard entry with exactly the five recorded fields (Req 5.4)."""

    game_id: str
    score: int
    total_lines: int
    level: int
    completed_at: str


class HighScoresOut(BaseModel):
    """Leaderboard response: an object with a ``scores`` array (Req 5.1)."""

    scores: List[HighScoreEntryOut]


def serialize(game: Game) -> GameStateOut:
    """Convert a domain Game into its JSON-friendly response model."""

    board = [[TYPE_CODES[cell] if cell is not None else 0 for cell in row] for row in game.board]

    active_piece: Optional[ActivePieceOut] = None
    if game.active is not None:
        active_piece = ActivePieceOut(
            type=game.active.type,
            origin=game.active.origin,
            cells=game.active.cells,
        )

    return GameStateOut(
        id=game.id,
        status=game.status,
        board=board,
        active_piece=active_piece,
        score=game.score,
        total_lines=game.total_lines,
        level=game.level,
        gravity_interval_ms=game.gravity_interval_ms,
        next_piece=game.next_type,
        hold_piece=game.hold_type,
        can_hold=game.can_hold,
    )
