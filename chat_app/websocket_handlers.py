from __future__ import annotations

import json
from collections import defaultdict
from typing import Dict, Set
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .database import record_user_join, record_user_leave
from .message_store import load_recent_messages, save_message
from .time_utils import kst_iso_now

router = APIRouter()

# 메모리 상태
rooms: Dict[str, Set[WebSocket]] = defaultdict(set)
user_by_ws: Dict[WebSocket, str] = {}
room_by_ws: Dict[WebSocket, str] = {}
users_in_room: Dict[str, Set[str]] = defaultdict(set)


async def broadcast_room(room: str, message: dict):
    if "timestamp" not in message:
        message["timestamp"] = kst_iso_now()
    message.setdefault("room", room)
    data = json.dumps(message, ensure_ascii=False)

    dead = []
    for ws in list(rooms[room]):
        try:
            await ws.send_text(data)
        except Exception:
            dead.append(ws)
    for ws in dead:
        await _cleanup_ws(ws)


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    name = ws.query_params.get("name", "사용자")
    room = ws.query_params.get("room", "lobby")

    await ws.accept()

    assigned = name
    if assigned in users_in_room[room]:
        idx = 1
        while f"{name}_{idx}" in users_in_room[room]:
            idx += 1
        assigned = f"{name}_{idx}"
        try:
            await ws.send_text(
                json.dumps({"type": "assign", "name": assigned, "room": room}, ensure_ascii=False)
            )
        except Exception:
            pass

    rooms[room].add(ws)
    room_by_ws[ws] = room
    user_by_ws[ws] = assigned
    users_in_room[room].add(assigned)
    record_user_join(room, assigned)

    history = load_recent_messages(room, limit=50)
    try:
        await ws.send_text(
            json.dumps({"type": "history", "room": room, "messages": history}, ensure_ascii=False)
        )
    except Exception:
        pass

    await broadcast_room(room, {"type": "users", "users": sorted(list(users_in_room[room]))})

    join_msg = {
        "type": "system",
        "text": f"{assigned} 님이 '{room}' 룸에 입장하셨습니다",
        "sender": "system",
        "room": room,
    }
    await broadcast_room(room, join_msg)
    save_message(room, {**join_msg, "timestamp": kst_iso_now()})

    try:
        while True:
            text = await ws.receive_text()

            try:
                payload = json.loads(text)
                msg_type = payload.get("type", "chat")
                msg_text = payload.get("text", "")
                image_data = payload.get("imageData")
                msg_id = payload.get("msgId") or str(uuid4())
            except json.JSONDecodeError:
                msg_type = "chat"
                msg_text = text
                image_data = None
                msg_id = str(uuid4())

            sender = user_by_ws.get(ws, "사용자")
            room = room_by_ws.get(ws, "lobby")

            message = {
                "type": msg_type,
                "text": msg_text,
                "sender": sender,
                "timestamp": kst_iso_now(),
                "room": room,
                "msgId": msg_id,
            }

            if image_data:
                message["imageData"] = image_data

            await broadcast_room(room, message)
            save_message(room, message)

    except WebSocketDisconnect:
        await _cleanup_ws(ws)
    except Exception:
        await _cleanup_ws(ws)
        room = room_by_ws.get(ws)
        name = user_by_ws.get(ws, "사용자")
        if room:
            err_msg = {
                "type": "system",
                "text": f"{name} 연결이 끊어졌습니다",
                "sender": "system",
                "room": room,
            }
            await broadcast_room(room, err_msg)
            save_message(room, {**err_msg, "timestamp": kst_iso_now()})


async def _cleanup_ws(ws: WebSocket):
    room = room_by_ws.pop(ws, None)
    name = user_by_ws.pop(ws, None)
    if room:
        rooms[room].discard(ws)
        if name:
            users_in_room[room].discard(name)
            record_user_leave(room, name)
            await broadcast_room(room, {"type": "users", "users": sorted(list(users_in_room[room]))})
            leave_msg = {
                "type": "system",
                "text": f"{name} 님이 '{room}' 룸에서 나갔습니다",
                "sender": "system",
                "room": room,
            }
            await broadcast_room(room, leave_msg)
            save_message(room, {**leave_msg, "timestamp": kst_iso_now()})

