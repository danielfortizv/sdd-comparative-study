import os
import json
import logging
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException

from app.services.duel_manager import DuelRoomManager

logger = logging.getLogger("tetris.ws_duel")
router = APIRouter()

# Parse allowed origins from environment (same as main.py)
raw_origins = os.environ.get("TETRIS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
ALLOWED_ORIGINS = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]

# DuelRoomManager global singleton for the single-worker backend
duel_manager = DuelRoomManager()

@router.websocket("/api/duel/ws")
async def websocket_duel_endpoint(
    websocket: WebSocket,
    room_id: Optional[str] = Query(None)
):
    # 1. Authoritative Handshake Origin Validation (CSWSH Prevention)
    origin = websocket.headers.get("origin")
    if not origin:
        logger.warning("Connection rejected: Origin header is missing.")
        raise HTTPException(status_code=403, detail="Forbidden: Origin header required")

    origin_normalized = origin.rstrip("/")
    if "*" not in ALLOWED_ORIGINS and origin_normalized not in [o.rstrip("/") for o in ALLOWED_ORIGINS]:
        logger.warning(f"Connection rejected: Origin '{origin}' not authorized.")
        raise HTTPException(status_code=403, detail="Forbidden: Origin not authorized")

    # 2. Room Assignment and Seat Allocation Gating
    joined = False
    assigned_room_id = None
    assigned_seat = None
    try:
        try:
            if not room_id:
                room_id = await duel_manager.create_room()
            else:
                # Check room availability and state BEFORE accepting the upgrade
                async with duel_manager.lock:
                    if room_id not in duel_manager.rooms:
                        await websocket.accept()
                        await websocket.close(code=4004, reason="Room Invalid/Finished")
                        return
                    
                    room = duel_manager.rooms[room_id]
                    if room["status"] == "finished":
                        await websocket.accept()
                        await websocket.close(code=4004, reason="Room Invalid/Finished")
                        return
                    if room["seat_1"] is not None and room["seat_2"] is not None:
                        await websocket.accept()
                        await websocket.close(code=4001, reason="Room Full")
                        return

            # Upgrade connection
            await websocket.accept()

            # Join player into the allocated room seat
            assigned_room_id, assigned_seat = await duel_manager.join_room(room_id, websocket)
            joined = True

        except ValueError as e:
            err_msg = str(e)
            if "full" in err_msg.lower():
                await websocket.close(code=4001, reason="Room Full")
            else:
                await websocket.close(code=4004, reason="Room Invalid/Finished")
            return
        except Exception as e:
            logger.exception("Failed during WebSocket room assignment")
            await websocket.close(code=4000, reason="Handshake Failure")
            return

        # 3. Emit Room Join Confirmation
        joined_payload = {
            "v": 1,
            "event": "joined",
            "payload": {
                "room_id": assigned_room_id,
                "assigned_seat": assigned_seat
            }
        }
        await websocket.send_json(joined_payload)

        # Broadcast initial room state
        await duel_manager.broadcast_state(assigned_room_id)

        # 4. Bidirectional Message Reception Loop
        try:
            while True:
                # Enforce 1 KB payload length restriction (strict UTF-8 byte limit)
                raw_data = await websocket.receive_text()
                raw_bytes = raw_data.encode('utf-8')
                if len(raw_bytes) > 1024:
                    logger.warning(f"Incoming payload exceeded 1KB limit: {len(raw_bytes)} bytes. Closing connection.")
                    await websocket.close(code=4000, reason="Payload limit exceeded")
                    break

                try:
                    data = json.loads(raw_data)
                    # Ensure incoming data is a JSON object, not a list or primitive
                    if not isinstance(data, dict):
                        await websocket.send_json({
                            "v": 1,
                            "event": "error",
                            "payload": {"code": 400, "message": "Payload must be a JSON object"}
                        })
                        continue
                except json.JSONDecodeError:
                    await websocket.send_json({
                        "v": 1,
                        "event": "error",
                        "payload": {"code": 400, "message": "Malformed JSON"}
                    })
                    continue

                # Validate WebSocket Schema via Pydantic WSActionMessage
                from app.models.schemas import WSActionMessage
                try:
                    parsed_msg = WSActionMessage.model_validate(data)
                except Exception as e:
                    await websocket.send_json({
                        "v": 1,
                        "event": "error",
                        "payload": {"code": 400, "message": f"Validation failed: {str(e)}"}
                    })
                    continue

                payload = parsed_msg.payload
                seq_num = payload.seq_num
                generation = payload.generation
                action_type = payload.action_type

                # Authoritatively process action targeting player's own seat
                err = await duel_manager.process_action(
                    room_id=assigned_room_id,
                    seat=assigned_seat,
                    seq_num=seq_num,
                    generation=generation,
                    action_type=action_type
                )

                if err:
                    await websocket.send_json({
                        "v": 1,
                        "event": "error",
                        "payload": err["error"]
                    })

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for room {assigned_room_id}, seat {assigned_seat}")
        except Exception as e:
            logger.exception("Error in WebSocket communication loop")

    finally:
        if joined and assigned_room_id and assigned_seat:
            await duel_manager.handle_disconnect(assigned_room_id, assigned_seat)
