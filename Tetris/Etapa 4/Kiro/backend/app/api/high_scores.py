"""Leaderboard controller: GET /api/high-scores (Stage 3, Option A)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..persistence.store import StorageError
from .deps import get_high_score_store
from .errors import STORAGE_UNAVAILABLE_MESSAGE
from .schemas import HighScoreEntryOut, HighScoresOut

router = APIRouter(prefix="/api/high-scores", tags=["high-scores"])


@router.get(
    "",
    responses={503: {"description": "High-score storage is temporarily unavailable."}},
)
def read_high_scores() -> HighScoresOut:
    """Return the top-ten leaderboard.

    Reads at most ten records ordered by score DESC, completed_at ASC, game_id
    ASC. The read creates no record and mutates no game state (Req 3.4, 5.x). A
    storage failure surfaces as a controlled JSON 503 (Req 7.1).
    """

    store = get_high_score_store()
    try:
        records = store.top_ten()
    except StorageError:
        raise HTTPException(status_code=503, detail=STORAGE_UNAVAILABLE_MESSAGE)

    return HighScoresOut(
        scores=[
            HighScoreEntryOut(
                game_id=r.game_id,
                score=r.score,
                total_lines=r.total_lines,
                level=r.level,
                completed_at=r.completed_at,
            )
            for r in records
        ]
    )
