from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, Set
from uuid import uuid4

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)

from .config import UPLOAD_DIR
from .database import record_user_join, record_user_leave
from .message_store import load_recent_messages, save_message
from .time_utils import kst_iso_now

router = APIRouter()

# In-memory room tracking
rooms: Dict[str, Set[WebSocket]] = defaultdict(set)
user_by_ws: Dict[WebSocket, str] = {}
room_by_ws: Dict[WebSocket, str] = {}
users_in_room: Dict[str, Set[str]] = defaultdict(set)

# File upload constraints
MAX_UPLOAD_BYTES = 500 * 1024 * 1024  # 500MB
ALLOWED_COMPRESSED_EXTS = {".zip", ".tar", ".gz", ".tgz", ".bz2", ".7z", ".rar"}
UPLOAD_PATH = Path(UPLOAD_DIR)
UPLOAD_PATH.mkdir(parents=True, exist_ok=True)


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


async def _save_upload_file(upload: UploadFile) -> tuple[str, int]:
    """Save uploaded file to disk while enforcing size limits."""
    safe_name = Path(upload.filename or "file").name
    stored_name = f"{uuid4().hex}_{safe_name}"
    dest_path = UPLOAD_PATH / stored_name

    total_bytes = 0
    chunk_size = 1024 * 1024  # 1MB chunks
    with dest_path.open("wb") as out:
        while True:
            chunk = await upload.read(chunk_size)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > MAX_UPLOAD_BYTES:
                out.close()
                dest_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413, detail="File exceeds the 500MB upload limit."
                )
            out.write(chunk)

    await upload.close()
    return stored_name, total_bytes


@router.post("/upload-file")
async def upload_file(
    file: UploadFile = File(...),
    room: str = Form(...),
    sender: str = Form(...),
    text: str = Form(""),
):
    if not room or not sender:
        raise HTTPException(status_code=400, detail="room and sender are required.")

    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_COMPRESSED_EXTS:
        raise HTTPException(
            status_code=400,
            detail="Only compressed files are allowed (.zip, .tar, .gz, .tgz, .bz2, .7z, .rar).",
        )

    stored_name, total_bytes = await _save_upload_file(file)
    file_url = f"/uploads/{stored_name}"

    message = {
        "type": "file",
        "text": text or "",
        "sender": sender,
        "timestamp": kst_iso_now(),
        "room": room,
        "msgId": str(uuid4()),
        "fileName": file.filename or stored_name,
        "fileUrl": file_url,
        "fileSize": total_bytes,
    }

    await broadcast_room(room, message)
    save_message(room, message)

    return {"status": "ok", "fileUrl": file_url, "fileSize": total_bytes, "msgId": message["msgId"]}


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    name = ws.query_params.get("name", "user")
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
        "text": f"{assigned} joined '{room}' room.",
        "sender": "system",
        "room": room,
    }
    await broadcast_room(room, join_msg)
    save_message(room, {**join_msg, "timestamp": kst_iso_now()})

    try:
        while True:
            text_data = await ws.receive_text()

            try:
                payload = json.loads(text_data)
                msg_type = payload.get("type", "chat")
                msg_text = payload.get("text", "")
                image_data = payload.get("imageData")
                msg_id = payload.get("msgId") or str(uuid4())
            except json.JSONDecodeError:
                msg_type = "chat"
                msg_text = text_data
                image_data = None
                msg_id = str(uuid4())

            sender = user_by_ws.get(ws, "user")
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
        name = user_by_ws.get(ws, "user")
        if room:
            err_msg = {
                "type": "system",
                "text": f"{name} disconnected unexpectedly.",
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
                "text": f"{name} left '{room}' room.",
                "sender": "system",
                "room": room,
            }
            await broadcast_room(room, leave_msg)
            save_message(room, {**leave_msg, "timestamp": kst_iso_now()})
