"""FastAPI application entry point.

Wires the game router and enables CORS so the local frontend can call the API
during development. All state is in memory; there is no database or auth.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.games import router as games_router

app = FastAPI(title="Tetris Stage 1 (Option A)")

# Allow the local Vite dev server to call the API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(games_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Simple liveness check."""

    return {"status": "ok"}
