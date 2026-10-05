from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from .models import GameState, MoveRequest
from .engine import SessionManager

app = FastAPI(title="Stateless Tetris API", version="1.0.0")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = SessionManager()

@app.post("/api/games", response_model=GameState, status_code=status.HTTP_201_CREATED)
def create_game():
    session = manager.create_session()
    return session.to_state()

@app.get("/api/games/{game_id}", response_model=GameState)
def get_game(game_id: str):
    session = manager.get_session(game_id)
    if not session:
        raise HTTPException(status_code=404, detail="Game session not found")
    return session.to_state()

@app.post("/api/games/{game_id}/move", response_model=GameState)
def move_game(game_id: str, request: MoveRequest):
    session = manager.get_session(game_id)
    if not session:
        raise HTTPException(status_code=404, detail="Game session not found")
    
    # Reject invalid directions gracefully or process left/right/down
    if request.direction not in ("left", "right", "down"):
        raise HTTPException(status_code=400, detail="Invalid direction. Must be 'left', 'right', or 'down'.")
    
    session.move(request.direction)
    return session.to_state()

@app.post("/api/games/{game_id}/tick", response_model=GameState)
def tick_game(game_id: str):
    session = manager.get_session(game_id)
    if not session:
        raise HTTPException(status_code=404, detail="Game session not found")
    
    session.step_down()
    return session.to_state()
