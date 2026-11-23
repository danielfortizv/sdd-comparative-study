import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import router as api_router, scores_router
from app.services.database import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database schema and directory on service startup
    init_db()
    yield

# Swagger-compliant API Metadata description
tags_metadata = [
    {
        "name": "games",
        "description": "Operations to manage and play single-player Tetris active game sessions.",
    },
    {
        "name": "leaderboard",
        "description": "Read-only global High Scores leaderboard.",
    }
]

app = FastAPI(
    title="Tetris Authoritative Core API",
    description=(
        "An authoritative, in-memory REST API backend for browser-based single-player Tetris. "
        "Exposes endpoints for game initialization, state retrieval, movement control, and automatic gravity ticking. "
        "Ensures game rules, boundaries, locking, and line-clearing are fully owned and validated on the server."
    ),
    version="1.0.0",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
    contact={
        "name": "Gemini CLI Developer",
    },
    license_info={
        "name": "MIT",
    },
)

# Parse configurable origins from environment variables, fallback to local development URLs
raw_origins = os.environ.get("TETRIS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]

# Restrictive CORS constraint: Disallow wildcard origins when credentials are enabled
allow_credentials = True
if "*" in origins:
    allow_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API endpoints routers
app.include_router(api_router, tags=["games"])
app.include_router(scores_router, tags=["leaderboard"])

@app.get("/", tags=["health"])
def read_root():
    """
    Health check endpoint verifying backend API server status.
    """
    return {"status": "ok", "message": "Tetris Core API is active"}
