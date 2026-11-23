from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from pydantic import BaseModel

from app.core.config import settings
from app.core.db import init_db, DatabaseError
from app.controllers import games

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the database and schemas on startup
    init_db()
    yield

class WelcomeResponseModel(BaseModel):
    message: str

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan
)

# RESTRICTIVE CORS Policy configuration: Configurable origins, no wildcard allowed with credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global database error interceptor to return clean 503 and hide trace/paths/schemas
@app.exception_handler(DatabaseError)
def database_error_handler(request: Request, exc: DatabaseError):
    return JSONResponse(
        status_code=503,
        content={"detail": "High scores database is temporarily unavailable."}
    )

app.include_router(games.router)
app.include_router(games.high_scores_router)

@app.get("/", response_model=WelcomeResponseModel)
def read_root():
    return WelcomeResponseModel(message="Welcome to Tetris Study API - Stage 1 Option A")
