import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.services.game_engine import (
    create_session,
    tick_session,
    move_session_piece,
    hold_session_piece,
    active_sessions
)
from app.models.schemas import TetrominoSchema

client = TestClient(app)

def test_qa02_random_draw_counts():
    active_sessions.clear()
    
    # Patch secrets.choice with a Mock to track calls precisely
    # We provide a side_effect returning standard piece types
    mock_choices = ["O", "I", "T", "S", "Z", "J", "L"] * 5
    with patch("app.services.game_engine.secrets.choice", side_effect=mock_choices) as mock_choice:
        # 1. New Game -> exactly 2 draws (one active, one next)
        session = create_session()
        assert mock_choice.call_count == 2
        
        # Reset call count tracker
        mock_choice.reset_mock()
        
        # 2. Normal Piece Lock -> exactly 1 draw (for the new next_piece)
        # Position piece resting on bottom (O piece row 18 and 19)
        session.active_piece = TetrominoSchema(
            type="O",
            cells=[[18, 4], [18, 5], [19, 4], [19, 5]],
            origin=[18, 4]
        )
        updated = tick_session(session.id)
        assert mock_choice.call_count == 1
        
        # Reset call count tracker
        mock_choice.reset_mock()
        
        # 3. Empty Hold -> exactly 1 draw (to replenish next_piece)
        updated.hold_piece = None
        updated.can_hold = True
        updated = hold_session_piece(session.id)
        assert mock_choice.call_count == 1
        
        # Reset call count tracker
        mock_choice.reset_mock()
        
        # 4. Occupied Swap Hold -> exactly 0 draws
        updated.can_hold = True
        updated.hold_piece = "T"
        updated = hold_session_piece(session.id)
        assert mock_choice.call_count == 0
        
        # Reset call count tracker
        mock_choice.reset_mock()
        
        # 5. Repeated state reads (GET) via actual route -> exactly 0 draws
        # Retrieving or looking at the state does not consume or draw pieces
        for _ in range(3):
            response = client.get(f"/api/games/{session.id}")
            assert response.status_code == 200
        assert mock_choice.call_count == 0
        
        # 6. Rejected hold (can_hold is False) -> exactly 0 draws
        updated.can_hold = False
        updated = hold_session_piece(session.id)
        assert mock_choice.call_count == 0
        
        # Reset call count tracker
        mock_choice.reset_mock()
        
        # 7. All actions after Game Over -> exactly 0 draws
        updated.status = "game_over"
        updated.can_hold = True
        
        # Try to tick after game over
        _ = tick_session(session.id)
        assert mock_choice.call_count == 0
        
        # Try to move left after game over
        _ = move_session_piece(session.id, "left")
        assert mock_choice.call_count == 0
        
        # Try to hold after game over
        _ = hold_session_piece(session.id)
        assert mock_choice.call_count == 0

def test_qa03_immutable_deep_state_snapshots():
    active_sessions.clear()
    session = create_session()
    
    # Freeze expected full JSON snapshot ONCE BEFORE the three-GET loop
    expected_snapshot = session.model_dump(mode='json', by_alias=True)
    
    with patch("app.services.game_engine.secrets.choice") as mock_choice:
        # 1. Repeated GET state reads via actual route: Deep serialized snapshots are identical, including activePiece and board
        for _ in range(3):
            response = client.get(f"/api/games/{session.id}")
            assert response.status_code == 200
            assert response.json() == expected_snapshot
            assert session.model_dump(mode='json', by_alias=True) == expected_snapshot
        
        # Keep zero-draw route spy
        assert mock_choice.call_count == 0
    
    # 2. Rejected Holds (when can_hold is False): Deep serialized state remains identical
    session.can_hold = False
    session.hold_piece = "T"
    pre_hold_snapshot = session.model_dump()
    updated = hold_session_piece(session.id)
    assert updated.model_dump() == pre_hold_snapshot
    
    # 3. Game Over isolation: All move/tick/hold operations are strictly no-ops
    session.status = "game_over"
    session.active_piece = TetrominoSchema(
        type="O",
        cells=[[0, 4], [0, 5], [1, 4], [1, 5]],
        origin=[0, 4]
    )
    post_game_over_snapshot = session.model_dump()
    
    # Tick after game over should leave state identical
    assert tick_session(session.id).model_dump() == post_game_over_snapshot
    
    # Move left after game over should leave state identical
    assert move_session_piece(session.id, "left").model_dump() == post_game_over_snapshot
    
    # Move right after game over should leave state identical
    assert move_session_piece(session.id, "right").model_dump() == post_game_over_snapshot
    
    # Move down after game over should leave state identical
    assert move_session_piece(session.id, "down").model_dump() == post_game_over_snapshot
    
    # Hold after game over should leave state identical
    assert hold_session_piece(session.id).model_dump() == post_game_over_snapshot

def test_qa04_restart_dirty_cleanup():
    active_sessions.clear()
    session = create_session()
    
    # Dirty every Stage 2 counter, hold field, and board cell
    session.board = [[5] * 10 for _ in range(20)]
    session.score = 9999
    session.total_lines = 45
    session.level = 5
    session.gravity_interval_ms = 300
    session.hold_piece = "O"
    session.can_hold = False
    session.status = "game_over"
    active_sessions[session.id] = session
    
    # Trigger restart (creates a new session)
    new_session = create_session()
    
    # Verify all Stage 2 defaults are restored and the board is fully empty
    assert new_session.id != session.id
    assert new_session.status == "playing"
    assert new_session.score == 0
    assert new_session.total_lines == 0
    assert new_session.level == 1
    assert new_session.gravity_interval_ms == 500
    assert new_session.hold_piece is None
    assert new_session.can_hold is True
    
    # Board is fully empty (all 0s)
    assert len(new_session.board) == 20
    assert all(row == [0] * 10 for row in new_session.board)
    
    # Valid active and next pieces
    assert new_session.active_piece is not None
    assert new_session.active_piece.type in {"I", "O", "T", "S", "Z", "J", "L"}
    assert new_session.next_piece in {"I", "O", "T", "S", "Z", "J", "L"}
