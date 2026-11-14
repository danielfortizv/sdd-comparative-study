"""FastAPI application entry point (Stage 3, Option A).

Wires the game and leaderboard routers, initializes the High_Score_Store on
startup via the lifespan handler, and applies a restrictive, configurable CORS
policy. All game state is in memory (single worker); only completed-game
high-score summaries are persisted. No authentication, no player names.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import deps
from .api.games import router as games_router
from .api.high_scores import router as high_scores_router
from .persistence.store import HighScoreStore

# Default allowed origins for local development (Vite dev server).
_DEFAULT_ALLOWED_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"


class CORSConfigurationError(ValueError):
    """Raised when the configured CORS allow-list is invalid for credentials.

    Credentials are always enabled, so a wildcard origin (``*``) — on its own
    or mixed into a list of concrete origins — is an invalid, insecure
    configuration. Resolving it raises this error at startup (fail closed)
    instead of handing ``*`` to the CORS middleware, which would otherwise
    reflect an arbitrary ``Origin`` with ``Access-Control-Allow-Credentials:
    true`` and grant a credentialed response to any site.
    """


def _resolve_allowed_origins() -> list[str]:
    """Resolve the configurable, restrictive CORS allow-list.

    Reads ``TETRIS_ALLOWED_ORIGINS`` (comma-separated); an unset or empty value
    falls back to the restrictive local-dev origins. Because credentials are
    enabled, a resolved list that contains a literal ``*`` — including a mixed
    list such as ``"https://app.example,*"`` — is rejected with
    :class:`CORSConfigurationError` (fail closed) rather than returned. Only
    concrete explicit origins are ever returned, so a credentialed response can
    never be granted to an arbitrary origin (Req 10.3-10.7).
    """

    raw = os.environ.get("TETRIS_ALLOWED_ORIGINS")
    if raw is None or raw.strip() == "":
        raw = _DEFAULT_ALLOWED_ORIGINS
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    if any(origin == "*" for origin in origins):
        raise CORSConfigurationError(
            "A wildcard '*' origin cannot be combined with credentialed CORS. "
            "Set TETRIS_ALLOWED_ORIGINS to an explicit list of concrete origins."
        )
    return origins


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the High_Score_Store once on startup."""

    store = HighScoreStore.from_env()
    store.initialize()
    deps.set_high_score_store(store)
    yield


app = FastAPI(title="Tetris Stage 3 (Option A)", lifespan=lifespan)

# Restrictive, configurable CORS. Credentials are allowed only with an explicit
# origin allow-list, never with a wildcard origin (Req 10.3, 10.4).
app.add_middleware(
    CORSMiddleware,
    allow_origins=_resolve_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(games_router)
app.include_router(high_scores_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Simple liveness check."""

    return {"status": "ok"}
