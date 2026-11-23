import pytest
from pydantic import ValidationError
from backend.models import (
    ActionPayload,
    StartPayload,
    DuelBoardStatePayload,
    OutcomePayload,
    ErrorPayload,
    WSMessageEnvelope
)

def test_action_payload_strict_int_validation():
    # Test strict int validation for seq and generation in ActionPayload
    with pytest.raises(ValidationError) as excinfo:
        ActionPayload(action="move_left", seq="not-an-int", room_id="room1", player_id="player1", generation=0)
    assert "Must be a strict non-negative integer" in str(excinfo.value)

    with pytest.raises(ValidationError) as excinfo:
        ActionPayload(action="move_left", seq=True, room_id="room1", player_id="player1", generation=0)
    assert "Must be a strict non-negative integer" in str(excinfo.value)

    with pytest.raises(ValidationError) as excinfo:
        ActionPayload(action="move_left", seq=-10, room_id="room1", player_id="player1", generation=0)
    assert "Must be a strict non-negative integer" in str(excinfo.value)


def test_ws_message_envelope_v_validation():
    # Test validation of protocol version 'v'
    with pytest.raises(ValidationError) as excinfo:
        WSMessageEnvelope(v="not-an-int", type="heartbeat", timestamp="2026-11-05T00:00:00Z", seq=1, payload=None)
    assert "v must be strict integer 1" in str(excinfo.value) or "Input should be" in str(excinfo.value)

    with pytest.raises(ValidationError) as excinfo:
        WSMessageEnvelope(v=True, type="heartbeat", timestamp="2026-11-05T00:00:00Z", seq=1, payload=None)
    assert "v must be strict integer 1" in str(excinfo.value)

    with pytest.raises(ValidationError) as excinfo:
        WSMessageEnvelope(v=2, type="heartbeat", timestamp="2026-11-05T00:00:00Z", seq=1, payload=None)
    assert "v must be strict integer 1" in str(excinfo.value)


def test_ws_message_envelope_seq_validation():
    # Test validation of outer seq
    with pytest.raises(ValidationError) as excinfo:
        WSMessageEnvelope(v=1, type="heartbeat", timestamp="2026-11-05T00:00:00Z", seq="not-an-int", payload=None)
    assert "Input should be a valid integer" in str(excinfo.value)

    with pytest.raises(ValidationError) as excinfo:
        WSMessageEnvelope(v=1, type="heartbeat", timestamp="2026-11-05T00:00:00Z", seq=-5, payload=None)
    assert "seq must be a strict non-negative integer or -1" in str(excinfo.value)


def test_ws_message_envelope_timestamp_validation():
    # Test validation of timestamp ISO format
    with pytest.raises(ValidationError) as excinfo:
        WSMessageEnvelope(v=1, type="heartbeat", timestamp="invalid-timestamp", seq=1, payload=None)
    assert "timestamp must be a valid ISO-8601 string" in str(excinfo.value)


def test_ws_message_envelope_payload_validation():
    timestamp = "2026-11-05T00:00:00Z"

    # 1. Action type with non-ActionPayload payload
    with pytest.raises(ValidationError) as excinfo:
        WSMessageEnvelope(v=1, type="action", timestamp=timestamp, seq=1, payload="not-a-payload")
    assert "Payload validation failed" in str(excinfo.value)

    # 2. Heartbeat type with non-None/non-dict payload
    with pytest.raises(ValidationError) as excinfo:
        WSMessageEnvelope(v=1, type="heartbeat", timestamp=timestamp, seq=1, payload="not-none-or-dict")
    assert "Payload validation failed" in str(excinfo.value)

    # 3. Start type with non-StartPayload payload
    with pytest.raises(ValidationError) as excinfo:
        WSMessageEnvelope(v=1, type="start", timestamp=timestamp, seq=1, payload="not-a-start-payload")
    assert "Payload validation failed" in str(excinfo.value)

    # 4. State type with non-DuelBoardStatePayload payload
    with pytest.raises(ValidationError) as excinfo:
        WSMessageEnvelope(v=1, type="state", timestamp=timestamp, seq=1, payload="not-a-state-payload")
    assert "Payload validation failed" in str(excinfo.value)

    # 5. Outcome type with non-OutcomePayload payload
    with pytest.raises(ValidationError) as excinfo:
        WSMessageEnvelope(v=1, type="outcome", timestamp=timestamp, seq=1, payload="not-an-outcome-payload")
    assert "Payload validation failed" in str(excinfo.value)

    # 6. Error type with non-ErrorPayload payload
    with pytest.raises(ValidationError) as excinfo:
        WSMessageEnvelope(v=1, type="error", timestamp=timestamp, seq=1, payload="not-an-error-payload")
    assert "Payload validation failed" in str(excinfo.value)


def test_ws_message_envelope_valid_dict_payloads():
    timestamp = "2026-11-05T00:00:00Z"

    # Cover action path
    action_dict = {
        "action": "move_left",
        "seq": 1,
        "room_id": "room-123",
        "player_id": "player-abc",
        "generation": 0
    }
    msg_action = WSMessageEnvelope(v=1, type="action", timestamp=timestamp, seq=1, payload=action_dict)
    assert isinstance(msg_action.payload, ActionPayload)

    # Cover start path
    start_dict = {
        "room_id": "room-123",
        "player1_id": "player-1",
        "player2_id": "player-2"
    }
    msg_start = WSMessageEnvelope(v=1, type="start", timestamp=timestamp, seq=1, payload=start_dict)
    assert isinstance(msg_start.payload, StartPayload)

    # Cover state path
    state_dict = {
        "room_id": "room-123",
        "seat": 1,
        "player_id": "player-1",
        "board": [[None] * 10 for _ in range(20)],
        "active_piece": {
            "type": "I",
            "cells": [[0, 1], [1, 1], [2, 1], [3, 1]],
            "origin": [1, 1],
            "orientation": 0
        },
        "status": "playing",
        "score": 100,
        "total_lines": 0,
        "level": 1,
        "gravity_interval_ms": 1000,
        "next_piece": "O",
        "hold_piece": None,
        "can_hold": True,
        "revision": 1,
        "generation": 0,
        "last_processed_seq": 0
    }
    msg_state = WSMessageEnvelope(v=1, type="state", timestamp=timestamp, seq=1, payload=state_dict)
    assert isinstance(msg_state.payload, DuelBoardStatePayload)

    # Cover outcome path
    outcome_dict = {
        "room_id": "room-123",
        "winner_id": "player-1",
        "loser_id": "player-2",
        "is_draw": False,
        "reason": "top_out"
    }
    msg_outcome = WSMessageEnvelope(v=1, type="outcome", timestamp=timestamp, seq=1, payload=outcome_dict)
    assert isinstance(msg_outcome.payload, OutcomePayload)

    # Cover error path
    error_dict = {
        "message": "Some error occurred"
    }
    msg_error = WSMessageEnvelope(v=1, type="error", timestamp=timestamp, seq=1, payload=error_dict)
    assert isinstance(msg_error.payload, ErrorPayload)


def test_ws_message_envelope_seq_mismatch():
    timestamp = "2026-11-05T00:00:00Z"
    action_payload = ActionPayload(
        action="move_left",
        seq=5,
        room_id="room1",
        player_id="player1",
        generation=0
    )
    with pytest.raises(ValidationError) as excinfo:
        WSMessageEnvelope(v=1, type="action", timestamp=timestamp, seq=10, payload=action_payload)
    assert "Outer seq and payload seq must be identical" in str(excinfo.value)


def test_ws_message_envelope_size_exceeded():
    timestamp = "2026-11-05T00:00:00Z"
    # Create an extremely large message to exceed 4096 bytes
    large_message = "A" * 5000
    error_payload = ErrorPayload(message=large_message)
    with pytest.raises(ValidationError) as excinfo:
        WSMessageEnvelope(v=1, type="error", timestamp=timestamp, seq=1, payload=error_payload)
    assert "Frame size exceeds 4096-byte limit" in str(excinfo.value)
