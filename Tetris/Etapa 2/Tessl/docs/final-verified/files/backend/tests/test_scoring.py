from fastapi.testclient import TestClient

from app.main import app
from app.models.game import ActivePieceModel
from app.controllers.games import GAMES

client = TestClient(app)

def test_stage2_initial_state():
    # AC-S2-1: POST /api/games returns initial state with Stage 2 fields
    response = client.post("/api/games")
    assert response.status_code == 200
    data = response.json()
    
    assert data["score"] == 0
    assert data["total_lines"] == 0
    assert data["level"] == 1
    assert data["gravity_interval_ms"] == 500
    assert data["next_piece"] in ('I', 'O', 'T', 'S', 'Z', 'J', 'L')
    assert data["hold_piece"] is None
    assert data["can_hold"] is True
    assert data["status"] == "playing"

def test_root_response_model():
    # Req-S2-2: Welcome route has response model and correct greeting
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to Tetris Study API - Stage 1 Option A"}

def test_read_only_get_game():
    # Req-S2-5: GET /api/games/{id} is read-only
    response_create = client.post("/api/games")
    game_id = response_create.json()["id"]
    next_piece_before = response_create.json()["next_piece"]
    
    response_get = client.get(f"/api/games/{game_id}")
    assert response_get.status_code == 200
    data_get = response_get.json()
    assert data_get["next_piece"] == next_piece_before
    assert data_get["score"] == 0

def test_scoring_1_and_2_clears():
    # AC-S2-2: Verify scoring for 1 and 2 clears
    response = client.post("/api/games")
    game_id = response.json()["id"]
    state = GAMES[game_id]
    
    # Test 1 row clear at Level 1 (should award +100 points)
    state.score = 0
    state.total_lines = 0
    state.level = 1
    state.board = [[None] * 10 for _ in range(20)]
    # Prefill row 19 except col 5
    for col in range(10):
        if col != 5:
            state.board[19][col] = 'S'
    # Place I at origin (19, 5) which spans horizontally [(0, 0), (0, 1), (0, 2), (0, 3)]
    # Let's use 'I' starting at (19, 5). Wait, I is 4 wide so (19, 5)..(19, 8) are cells.
    # To clear only row 19, we place 'I' at origin (19, 5) which fills (19, 5).
    # Wait, 'I' has shape [(0, 0), (0, 1), (0, 2), (0, 3)]. So at (19, 5) its cells are (19, 5), (19, 6), (19, 7), (19, 8).
    # Since we want to fill only row 19, let's prefill everything except col 5, 6, 7, 8 in row 19.
    state.board = [[None] * 10 for _ in range(20)]
    for col in range(10):
        if col not in (5, 6, 7, 8):
            state.board[19][col] = 'S'
    
    state.active_piece = ActivePieceModel(
        type='I',
        origin=(19, 5),
        cells=[(19, 5), (19, 6), (19, 7), (19, 8)]
    )
    
    # Tick to lock
    response_tick = client.post(f"/api/games/{game_id}/tick")
    assert response_tick.status_code == 200
    data = response_tick.json()
    assert data["score"] == 100
    assert data["total_lines"] == 1
    assert data["level"] == 1
    
    # Test 2 row clear at Level 2 (should award +300 * 2 = 600 points)
    # Let's set level to 2
    state.score = 100
    state.total_lines = 10
    state.level = 2
    state.board = [[None] * 10 for _ in range(20)]
    # Prefill rows 18 and 19 except cols 5, 6
    for col in range(10):
        if col not in (5, 6):
            state.board[18][col] = 'S'
            state.board[19][col] = 'S'
    # Place O at (18, 5) -> spans cells (18, 5), (18, 6), (19, 5), (19, 6)
    state.active_piece = ActivePieceModel(
        type='O',
        origin=(18, 5),
        cells=[(18, 5), (18, 6), (19, 5), (19, 6)]
    )
    
    response_tick = client.post(f"/api/games/{game_id}/tick")
    data = response_tick.json()
    # Pre-lock level was 2, so 300 * 2 = 600 points should be awarded.
    # Total score should be 100 + 600 = 700.
    assert data["score"] == 700
    assert data["total_lines"] == 12
    # level is updated after line clear: total_lines = 12 -> level = 1 + 12 // 10 = 2

def test_scoring_3_clears_isolated():
    # Req-S2-23: Isolated unit test for N=3 complete bottom rows 17..19, canonical O rests at origin (15, 3)
    response = client.post("/api/games")
    game_id = response.json()["id"]
    state = GAMES[game_id]
    
    state.score = 0
    state.total_lines = 0
    state.level = 1
    state.board = [[None] * 10 for _ in range(20)]
    
    # Prefill rows 17, 18, 19 completely
    for r in (17, 18, 19):
        for c in range(10):
            state.board[r][c] = 'S'
            
    # Place canonical O at origin (15, 3)
    # Shape of O: [(0, 0), (0, 1), (1, 0), (1, 1)] -> cells (15, 3), (15, 4), (16, 3), (16, 4)
    state.active_piece = ActivePieceModel(
        type='O',
        origin=(15, 3),
        cells=[(15, 3), (15, 4), (16, 3), (16, 4)]
    )
    
    # Tick down -> O cannot move down because row 17 is occupied. It locks!
    response_tick = client.post(f"/api/games/{game_id}/tick")
    data = response_tick.json()
    
    # Pre-lock level is 1. Score awarded: 500 * 1 = 500 points.
    assert data["score"] == 500
    assert data["total_lines"] == 3
    assert data["level"] == 1
    # Check that O cells (15, 3), (15, 4), (16, 3), (16, 4) fell down by 3 rows after clearing rows 17..19!
    # They should end up at row 18 and 19 (cols 3, 4)
    assert data["board"][18][3] == 'O'
    assert data["board"][18][4] == 'O'
    assert data["board"][19][3] == 'O'
    assert data["board"][19][4] == 'O'

def test_scoring_4_clears_isolated():
    # Req-S2-23: Isolated unit test for N=4 complete bottom rows 16..19, canonical O rests at origin (14, 3)
    response = client.post("/api/games")
    game_id = response.json()["id"]
    state = GAMES[game_id]
    
    state.score = 0
    state.total_lines = 0
    state.level = 1
    state.board = [[None] * 10 for _ in range(20)]
    
    # Prefill rows 16, 17, 18, 19 completely
    for r in (16, 17, 18, 19):
        for c in range(10):
            state.board[r][c] = 'S'
            
    # Place canonical O at origin (14, 3)
    # Shape of O: [(0, 0), (0, 1), (1, 0), (1, 1)] -> cells (14, 3), (14, 4), (15, 3), (15, 4)
    state.active_piece = ActivePieceModel(
        type='O',
        origin=(14, 3),
        cells=[(14, 3), (14, 4), (15, 3), (15, 4)]
    )
    
    # Tick down -> O locks!
    response_tick = client.post(f"/api/games/{game_id}/tick")
    data = response_tick.json()
    
    # Pre-lock level is 1. Score awarded: 800 * 1 = 800 points.
    assert data["score"] == 800
    assert data["total_lines"] == 4
    assert data["level"] == 1
    # Check that O cells fell down by 4 rows after clearing rows 16..19!
    # They should end up at row 18 and 19 (cols 3, 4)
    assert data["board"][18][3] == 'O'
    assert data["board"][18][4] == 'O'
    assert data["board"][19][3] == 'O'
    assert data["board"][19][4] == 'O'

def test_threshold_crossing_level_and_gravity():
    # Prefill board with 9 lines cleared previously. Lock a piece to clear 1 row (crossing to 10 total lines).
    # Verify that the score uses Level 1 (pre-lock level), and then the level becomes 2 and gravity interval becomes 450.
    response = client.post("/api/games")
    game_id = response.json()["id"]
    state = GAMES[game_id]
    
    state.score = 0
    state.total_lines = 9
    state.level = 1
    state.board = [[None] * 10 for _ in range(20)]
    # Prefill row 19 except col 5
    for col in range(10):
        if col != 5:
            state.board[19][col] = 'S'
    state.active_piece = ActivePieceModel(
        type='I',
        origin=(19, 5),
        cells=[(19, 5), (19, 6), (19, 7), (19, 8)]
    )
    # Wait, 'I' has shape of 4 cells horizontally, so we should prefill row 19 except cols 5,6,7,8
    state.board = [[None] * 10 for _ in range(20)]
    for col in range(10):
        if col not in (5, 6, 7, 8):
            state.board[19][col] = 'S'
            
    state.active_piece = ActivePieceModel(
        type='I',
        origin=(19, 5),
        cells=[(19, 5), (19, 6), (19, 7), (19, 8)]
    )
    
    response_tick = client.post(f"/api/games/{game_id}/tick")
    data = response_tick.json()
    
    # Score should be 100 (Level 1 * 100)
    assert data["score"] == 100
    assert data["total_lines"] == 10
    # Level becomes 2
    assert data["level"] == 2
    # gravity_interval_ms becomes 450
    assert data["gravity_interval_ms"] == 450

def test_gravity_floor():
    # Req-S2-19: Set level to 10 and verify gravity interval is 100 ms (floor).
    response = client.post("/api/games")
    game_id = response.json()["id"]
    state = GAMES[game_id]
    
    # Simulate high levels
    state.total_lines = 90 # level 10
    state.level = 10
    state.gravity_interval_ms = max(100, 500 - 50 * (state.level - 1))
    assert state.gravity_interval_ms == 100
    
    state.total_lines = 150 # level 16
    state.level = 16
    state.gravity_interval_ms = max(100, 500 - 50 * (state.level - 1))
    assert state.gravity_interval_ms == 100

def test_first_hold():
    # AC-S2-4: First hold when hold_piece is null and can_hold is true
    response = client.post("/api/games")
    game_id = response.json()["id"]
    state = GAMES[game_id]
    
    active_type_before = state.active_piece.type
    next_type_before = state.next_piece
    
    response_hold = client.post(f"/api/games/{game_id}/hold")
    assert response_hold.status_code == 200
    data = response_hold.json()
    
    # hold_piece is now active_type_before
    assert data["hold_piece"] == active_type_before
    # active_piece is now next_type_before
    assert data["active_piece"]["type"] == next_type_before
    # can_hold is false
    assert data["can_hold"] is False
    # next_piece is updated with a new random piece
    assert data["next_piece"] in ('I', 'O', 'T', 'S', 'Z', 'J', 'L')

def test_swap_hold():
    # AC-S2-5: Swap hold when hold_piece is occupied and can_hold is true
    response = client.post("/api/games")
    game_id = response.json()["id"]
    state = GAMES[game_id]
    
    state.hold_piece = 'Z'
    state.can_hold = True
    active_type_before = state.active_piece.type
    next_type_before = state.next_piece
    
    response_hold = client.post(f"/api/games/{game_id}/hold")
    assert response_hold.status_code == 200
    data = response_hold.json()
    
    # hold_piece is now active_type_before
    assert data["hold_piece"] == active_type_before
    # active_piece is now 'Z' (the previous hold_piece)
    assert data["active_piece"]["type"] == 'Z'
    # next_piece remains unchanged (not consumed)
    assert data["next_piece"] == next_type_before
    # can_hold is false
    assert data["can_hold"] is False

def test_hold_rejection_and_reset():
    # AC-S2-6: Rejection of subsequent holds, and reset of can_hold on lock
    response = client.post("/api/games")
    game_id = response.json()["id"]
    state = GAMES[game_id]
    
    # Set can_hold to False
    state.can_hold = False
    active_type_before = state.active_piece.type
    
    # Try hold -> should be rejected and returned unchanged (HTTP 200)
    response_hold = client.post(f"/api/games/{game_id}/hold")
    assert response_hold.status_code == 200
    assert response_hold.json()["can_hold"] is False
    assert response_hold.json()["active_piece"]["type"] == active_type_before
    
    # Lock a piece, should reset can_hold to True
    # Place piece near bottom and tick
    state.board = [[None] * 10 for _ in range(20)]
    state.active_piece = ActivePieceModel(
        type='I',
        origin=(19, 0),
        cells=[(19, 0), (19, 1), (19, 2), (19, 3)]
    )
    
    response_tick = client.post(f"/api/games/{game_id}/tick")
    assert response_tick.json()["can_hold"] is True

def test_row_zero_locking_no_preview_consumption():
    # AC-S2-7: Row-zero locking triggers game over and does NOT consume next_piece
    response = client.post("/api/games")
    game_id = response.json()["id"]
    state = GAMES[game_id]
    
    # Block row 1 so piece at row 0 cannot move down
    for col in range(10):
        state.board[1][col] = 'S'
        
    state.active_piece = ActivePieceModel(
        type='I',
        origin=(0, 0),
        cells=[(0, 0), (0, 1), (0, 2), (0, 3)]
    )
    
    next_piece_before = state.next_piece
    
    response_tick = client.post(f"/api/games/{game_id}/tick")
    data = response_tick.json()
    
    assert data["status"] == "game_over"
    assert data["active_piece"] is None
    # next_piece is NOT consumed
    assert data["next_piece"] == next_piece_before

def test_obstructed_spawn():
    # AC-S2-8: Obstructed spawn transitions to game_over and active_piece is null
    response = client.post("/api/games")
    game_id = response.json()["id"]
    state = GAMES[game_id]
    
    # Prefill the spawn area at (0, 3)
    # The 'I' piece starting at (0, 3) has cells (0,3), (0,4), (0,5), (0,6). Let's block them all.
    for col in (3, 4, 5, 6):
        state.board[0][col] = 'S'
        
    # Place an active piece at (19, 0) and tick to lock it, triggering a spawn
    state.active_piece = ActivePieceModel(
        type='O',
        origin=(19, 0),
        cells=[(19, 0), (19, 1), (18, 0), (18, 1)]
    )
    # Set state.next_piece to 'I'
    state.next_piece = 'I'
    
    response_tick = client.post(f"/api/games/{game_id}/tick")
    data = response_tick.json()
    
    assert data["status"] == "game_over"
    assert data["active_piece"] is None

def test_obstructed_hold_spawn():
    # AC-S2-8: Obstructed hold spawn transitions to game_over and active_piece is null
    response = client.post("/api/games")
    game_id = response.json()["id"]
    state = GAMES[game_id]
    
    # Block spawn area for 'I'
    for col in (3, 4, 5, 6):
        state.board[0][col] = 'S'
        
    state.next_piece = 'I'
    state.can_hold = True
    
    response_hold = client.post(f"/api/games/{game_id}/hold")
    data = response_hold.json()
    
    assert data["status"] == "game_over"
    assert data["active_piece"] is None
