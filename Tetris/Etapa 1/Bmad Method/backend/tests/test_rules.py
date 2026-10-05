import pytest
from app.rules import ROWS, COLS, SHAPES, SPAWN_ORIGIN, get_piece_cells
from app.models import Position, GameState

def test_api_create_game_and_board_size(client):
    """AC-1: Verify that starting a game instantiates a 20-row by 10-column board."""
    response = client.post("/api/games")
    assert response.status_code == 201
    
    data = response.json()
    assert "game_id" in data
    assert data["status"] == "playing"
    
    # Check board size
    board = data["board"]
    assert len(board) == ROWS
    for row in board:
        assert len(row) == COLS
        assert all(cell is None for cell in row)

def test_api_piece_spawning(client):
    """AC-2: Verify spawning of one of seven standard tetrominoes in initial orientation."""
    # Spawn deterministic first piece "I"
    response = client.post("/api/games?test_piece=I")
    assert response.status_code == 201
    
    data = response.json()
    active_piece = data["active_piece"]
    assert active_piece is not None
    assert active_piece["type"] == "I"
    
    # Initial origin of "I" is (0, 4)
    assert active_piece["origin"]["row"] == 0
    assert active_piece["origin"]["col"] == 4
    
    # Shape coords of "I" offsets: (0,-1), (0,0), (0,1), (0,2) => cols 3, 4, 5, 6
    cells = active_piece["cells"]
    assert len(cells) == 4
    expected_cells = [{"row": 0, "col": 3}, {"row": 0, "col": 4}, {"row": 0, "col": 5}, {"row": 0, "col": 6}]
    assert cells == expected_cells

def test_api_legal_movement(client):
    """AC-3 & AC-4: Verify legal movement left, right, and soft drop (down)."""
    # Start game with "O"
    res_start = client.post("/api/games?test_piece=O")
    game_id = res_start.json()["game_id"]
    
    # Shift Left
    res_left = client.post(f"/api/games/{game_id}/move", json={"direction": "left"})
    assert res_left.status_code == 200
    piece_left = res_left.json()["active_piece"]
    assert piece_left["origin"]["row"] == 0
    assert piece_left["origin"]["col"] == 3
    
    # Shift Right
    res_right = client.post(f"/api/games/{game_id}/move", json={"direction": "right"})
    assert res_right.status_code == 200
    piece_right = res_right.json()["active_piece"]
    assert piece_right["origin"]["row"] == 0
    assert piece_right["origin"]["col"] == 4
    
    # Soft Drop (Down)
    res_down = client.post(f"/api/games/{game_id}/move", json={"direction": "down"})
    assert res_down.status_code == 200
    piece_down = res_down.json()["active_piece"]
    assert piece_down["origin"]["row"] == 1
    assert piece_down["origin"]["col"] == 4

def test_api_collisions_side_and_bottom(client):
    """AC-4 & AC-5: Verify collision constraints. Off-grid movements must be ignored."""
    # Spawn "O" piece: origin (0, 4), offsets [(0,0), (0,1), (1,0), (1,1)]
    # Absolute cols: 4, 5. Max cols is 9.
    res_start = client.post("/api/games?test_piece=O")
    game_id = res_start.json()["game_id"]
    
    # Move left multiple times to hit wall at col 0
    # Left bound of "O" piece is offset 0, so origin col can go down to 0 (cols 0, 1)
    for _ in range(6):
        res_left = client.post(f"/api/games/{game_id}/move", json={"direction": "left"})
    
    # Current origin should be col 0
    data_left = res_left.json()
    assert data_left["active_piece"]["origin"]["col"] == 0
    
    # Move left again (should be ignored due to collision)
    res_left_collision = client.post(f"/api/games/{game_id}/move", json={"direction": "left"})
    assert res_left_collision.json()["active_piece"]["origin"]["col"] == 0
    
    # Move right multiple times to hit wall at col 9
    # Right bound of "O" piece is offset +1, so origin col can go up to 8 (cols 8, 9)
    for _ in range(10):
        res_right = client.post(f"/api/games/{game_id}/move", json={"direction": "right"})
        
    data_right = res_right.json()
    assert data_right["active_piece"]["origin"]["col"] == 8
    
    # Move right again (should be ignored due to collision)
    res_right_collision = client.post(f"/api/games/{game_id}/move", json={"direction": "right"})
    assert res_right_collision.json()["active_piece"]["origin"]["col"] == 8

def test_api_locking_and_subsequent_spawn(client):
    """AC-5, AC-6 & AC-7: Verify piece locking and subsequent spawning."""
    # Start game with "O"
    res_start = client.post("/api/games?test_piece=O")
    data = res_start.json()
    game_id = data["game_id"]
    
    # Move piece to the bottom: row 18 (O piece height is 2 rows, occupies 18 and 19)
    # Origin starts at row 0. Needs 18 down moves.
    for _ in range(18):
        res_down = client.post(f"/api/games/{game_id}/move", json={"direction": "down"})
        
    data_bottom = res_down.json()
    assert data_bottom["active_piece"]["origin"]["row"] == 18
    
    # A subsequent tick triggers locking because the piece cannot go down to row 19 (which would exceed row 19 limits for second row of O)
    res_tick = client.post(f"/api/games/{game_id}/tick?test_next_piece=I")
    data_tick = res_tick.json()
    
    # The active piece should now be "I" at spawning origin
    assert data_tick["active_piece"]["type"] == "I"
    assert data_tick["active_piece"]["origin"]["row"] == 0
    
    # The bottom cells (18, 4), (18, 5), (19, 4), (19, 5) must be occupied on the board
    board = data_tick["board"]
    assert board[18][4] == "O"
    assert board[18][5] == "O"
    assert board[19][4] == "O"
    assert board[19][5] == "O"

def test_api_line_clearing(client):
    """AC-6 & AC-7: Verify clearing of complete horizontal lines and shifting rows down."""
    # Start game with "I" (original offsets: (0,-1), (0,0), (0,1), (0,2))
    # Coordinates from origin (0, 4) are cols: 3, 4, 5, 6
    res_start = client.post("/api/games?test_piece=I")
    data = res_start.json()
    game_id = data["game_id"]
    
    # Mock pre-settled cells at the bottom row (row 19) to complete it
    # We will complete row 19. "I" at row 19 will occupy cols 3, 4, 5, 6.
    # Therefore, we pre-settle cols 0, 1, 2, and 7, 8, 9 with "O" blocks.
    # Let's write them directly into our mock state
    from app.main import games
    state = games[game_id]
    state.board[19][0] = "O"
    state.board[19][1] = "O"
    state.board[19][2] = "O"
    state.board[19][7] = "O"
    state.board[19][8] = "O"
    state.board[19][9] = "O"
    
    # Settle some "Z" blocks on row 18 to verify they drop down
    state.board[18][0] = "Z"
    state.board[18][1] = "Z"
    
    # Shift "I" piece to bottom row 19
    for _ in range(19):
        client.post(f"/api/games/{game_id}/move", json={"direction": "down"})
        
    # Trigger tick to lock "I" into row 19 (filling cols 3, 4, 5, 6 and making row 19 completely full)
    res_tick = client.post(f"/api/games/{game_id}/tick?test_next_piece=O")
    data_cleared = res_tick.json()
    
    # Check that row 19 was cleared
    # The pre-existing "Z" blocks from row 18 should have fallen to row 19!
    board = data_cleared["board"]
    assert board[19][0] == "Z"
    assert board[19][1] == "Z"
    assert board[19][2] is None
    assert board[19][3] is None
    assert board[19][4] is None
    assert board[19][5] is None
    assert board[19][6] is None
    assert board[19][7] is None
    assert board[19][8] is None
    assert board[19][9] is None
    
    # Row 18 should be empty now
    assert all(cell is None for cell in board[18])

def test_api_game_over(client):
    """AC-8: Verify that game over state triggers when spawn cells are pre-occupied."""
    res_start = client.post("/api/games?test_piece=O")
    data = res_start.json()
    game_id = data["game_id"]
    
    # Mock pre-occupied block at SPAWN_ORIGIN col 4, row 0
    from app.main import games
    state = games[game_id]
    state.board[0][4] = "O"
    
    # Push piece down and lock it to trigger next spawn
    for _ in range(19):
        client.post(f"/api/games/{game_id}/move", json={"direction": "down"})
    
    # Settle current piece, spawning next "O" piece which immediately collides with state.board[0][4] = "O"
    res_tick = client.post(f"/api/games/{game_id}/tick?test_next_piece=O")
    data_tick = res_tick.json()
    
    # Status must be game_over, active piece is null
    assert data_tick["status"] == "game_over"
    assert data_tick["active_piece"] is None
