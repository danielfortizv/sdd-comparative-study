from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_game_api():
    response = client.post("/api/games")
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["status"] == "playing"
    assert len(data["board"]) == 20
    assert len(data["board"][0]) == 10
    assert "active_piece" in data
    assert data["active_piece"]["shape"] in ["I", "J", "L", "O", "S", "T", "Z"]

def test_get_game_api():
    # Create first
    create_res = client.post("/api/games")
    game_id = create_res.json()["id"]
    
    # Retrieve
    get_res = client.get(f"/api/games/{game_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == game_id
    
    # Non-existent ID
    bad_res = client.get("/api/games/invalid-uuid")
    assert bad_res.status_code == 404
    assert "detail" in bad_res.json()

def test_tick_game_api():
    # Create first
    create_res = client.post("/api/games")
    game_id = create_res.json()["id"]
    
    # Tick
    tick_res = client.post(f"/api/games/{game_id}/tick")
    assert tick_res.status_code == 200
    data = tick_res.json()
    assert data["id"] == game_id
    
    # Bad ID
    bad_res = client.post("/api/games/invalid-uuid/tick")
    assert bad_res.status_code == 404

def test_move_game_api():
    # Create first
    create_res = client.post("/api/games")
    game_id = create_res.json()["id"]
    
    # Move Left
    move_res = client.post(f"/api/games/{game_id}/move", json={"direction": "left"})
    assert move_res.status_code == 200
    
    # Invalid Direction (FastAPI validation error -> 422 Unprocessable Entity)
    bad_dir_res = client.post(f"/api/games/{game_id}/move", json={"direction": "up"})
    assert bad_dir_res.status_code == 422
    
    # Non-existent ID
    bad_res = client.post("/api/games/invalid-uuid/move", json={"direction": "down"})
    assert bad_res.status_code == 404

def test_hold_game_api():
    # Create first
    create_res = client.post("/api/games")
    game_id = create_res.json()["id"]
    
    # Check that initially we have the 7 new fields
    data = create_res.json()
    assert "score" in data
    assert "total_lines" in data
    assert "level" in data
    assert "gravity_interval_ms" in data
    assert "next_piece" in data
    assert "hold_piece" in data
    assert "can_hold" in data
    assert data["can_hold"] is True
    assert data["hold_piece"] is None
    
    # Perform Hold
    hold_res = client.post(f"/api/games/{game_id}/hold")
    assert hold_res.status_code == 200
    hold_data = hold_res.json()
    assert hold_data["hold_piece"] is not None
    assert hold_data["can_hold"] is False
    
    # Try Hold again (rejected because can_hold is False)
    hold_res2 = client.post(f"/api/games/{game_id}/hold")
    assert hold_res2.status_code == 200
    hold_data2 = hold_res2.json()
    assert hold_data2["hold_piece"] == hold_data["hold_piece"]
    assert hold_data2["can_hold"] is False
    
    # Hold non-existent ID
    bad_res = client.post("/api/games/invalid-uuid/hold")
    assert bad_res.status_code == 404
