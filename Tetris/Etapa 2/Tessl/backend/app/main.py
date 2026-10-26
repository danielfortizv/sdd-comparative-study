from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel

from app.core.config import settings
from app.controllers import games

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

class WelcomeResponseModel(BaseModel):
    message: str

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(games.router)

@app.get("/", response_model=WelcomeResponseModel)
def read_root():
    return WelcomeResponseModel(message="Welcome to Tetris Study API - Stage 1 Option A")
