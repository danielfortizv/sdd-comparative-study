from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import router as api_router

# Swagger-compliant API Metadata description
tags_metadata = [
    {
        "name": "games",
        "description": "Operations to manage and play single-player Tetris active game sessions.",
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
    contact={
        "name": "Gemini CLI Developer",
    },
    license_info={
        "name": "MIT",
    },
)

# Setup CORS middleware
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API endpoints router (mapped with 'games' tag)
app.include_router(api_router, tags=["games"])

@app.get("/", tags=["health"])
def read_root():
    """
    Health check endpoint verifying backend API server status.
    """
    return {"status": "ok", "message": "Tetris Core API is active"}
