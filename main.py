from typing import Dict, Set

import json
import os
from collections import defaultdict
from datetime import datetime
from uuid import uuid4

import pytz
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.errors import PyMongoError
from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String, create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import declarative_base, sessionmaker

# --- Databases (MongoDB for messages, PostgreSQL for users) ---
MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongo:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "chatapp")
MONGO_COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME", "messages")

POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql+psycopg://postgres:postgres@postgres:5432/chatapp")

engine = create_engine(POSTGRES_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ChatUser(Base):
    __tablename__ = "chat_users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    room = Column(String(128), nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True, nullable=False)

    __table_args__ = (
        Index("idx_users_room_name", "room", "name", unique=True),
        Index("idx_users_active_room", "is_active", "room"),
    )


mongo_client: MongoClient | None = None
message_collection: Collection | None = None

try:
    mongo_client = MongoClient(MONGO_URL)
    mongo_db = mongo_client[MONGO_DB_NAME]
    message_collection = mongo_db[MONGO_COLLECTION_NAME]
except PyMongoError as exc:
    print(f"[MongoDB] Connection failed: {exc}")


def init_user_db():
    Base.metadata.create_all(bind=engine)
    reset_all_user_states()


def reset_all_user_states():
    """서버 시작 시 모든 이용자를 오프라인으로 초기화."""
    try:
        with SessionLocal() as db:
            db.query(ChatUser).update({ChatUser.is_active: False})
            db.commit()
    except SQLAlchemyError as exc:
        print(f"[PostgreSQL] Failed to reset user states: {exc}")


def ensure_message_indexes():
    if message_collection is None:
        return
    try:
        message_collection.create_index([("room", ASCENDING), ("timestamp", DESCENDING)])
        message_collection.create_index("msg_id")
    except PyMongoError as exc:
        print(f"[MongoDB] Failed to create indexes: {exc}")


def record_user_join(room: str, name: str):
    now = datetime.utcnow()
    try:
        with SessionLocal() as db:
            user = (
                db.query(ChatUser)
                .filter(ChatUser.room == room, ChatUser.name == name)
                .one_or_none()
            )
            if not user:
                user = ChatUser(room=room, name=name, joined_at=now)
            user.last_seen = now
            user.is_active = True
            db.add(user)
            db.commit()
    except SQLAlchemyError as exc:
        print(f"[PostgreSQL] Failed to record join for {name}@{room}: {exc}")


def record_user_leave(room: str, name: str):
    now = datetime.utcnow()
    try:
        with SessionLocal() as db:
            user = (
                db.query(ChatUser)
                .filter(ChatUser.room == room, ChatUser.name == name)
                .one_or_none()
            )
            if not user:
                user = ChatUser(room=room, name=name, joined_at=now)
            user.last_seen = now
            user.is_active = False
            db.add(user)
            db.commit()
    except SQLAlchemyError as exc:
        print(f"[PostgreSQL] Failed to record leave for {name}@{room}: {exc}")


def save_message(room: str, msg: dict):
    """MongoDB에 메시지 저장."""
    if message_collection is None:
        return
    doc = {
        "room": room,
        "msg_type": msg.get("type", "chat"),
        "sender": msg.get("sender"),
        "text": msg.get("text"),
        "timestamp": _to_kst_dt(msg.get("timestamp")),
        "msg_id": msg.get("msgId"),
        "image_data": msg.get("imageData"),
    }
    try:
        message_collection.insert_one(doc)
    except PyMongoError as exc:
        print(f"[MongoDB] Failed to save message: {exc}")


def load_recent_messages(room: str, limit: int = 50):
    if message_collection is None:
        return []
    try:
        rows = list(
            message_collection.find({"room": room}).sort("timestamp", DESCENDING).limit(limit)
        )
    except PyMongoError as exc:
        print(f"[MongoDB] Failed to load history for {room}: {exc}")
        return []

    data = []
    for r in reversed(rows):
        timestamp = r.get("timestamp")
        msg_dict = {
            "type": r.get("msg_type", "chat"),
            "sender": r.get("sender"),
            "text": r.get("text"),
            "timestamp": timestamp.isoformat() if isinstance(timestamp, datetime) else timestamp,
            "room": room,
            "msgId": r.get("msg_id"),
        }
        image_data = r.get("image_data")
        if image_data:
            msg_dict["imageData"] = image_data
        data.append(msg_dict)
    return data


def _to_kst_dt(ts_str: str | None):
    kst = pytz.timezone("Asia/Seoul")
    if ts_str:
        try:
            return (
                datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                .astimezone(kst)
                .replace(tzinfo=None)
            )
        except Exception:
            pass
    return datetime.now(kst).replace(tzinfo=None)


# --- App ---
app = FastAPI(title="Mini Chat (rooms + history)")
init_user_db()
ensure_message_indexes()

# 메모리 상태
rooms: Dict[str, Set[WebSocket]] = defaultdict(set)
user_by_ws: Dict[WebSocket, str] = {}
room_by_ws: Dict[WebSocket, str] = {}
users_in_room: Dict[str, Set[str]] = defaultdict(set)


def kst_iso_now():
    kst = pytz.timezone("Asia/Seoul")
    return datetime.now(kst).isoformat()


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


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    name = ws.query_params.get("name", "이용자")
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
        "text": f"{assigned} 님이 '{room}' 룸에 입장하셨습니다.",
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

            sender = user_by_ws.get(ws, "이용자")
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
        name = user_by_ws.get(ws, "이용자")
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
                "text": f"{name} 님이 '{room}' 룸에서 나갔습니다.",
                "sender": "system",
                "room": room,
            }
            await broadcast_room(room, leave_msg)
            save_message(room, {**leave_msg, "timestamp": kst_iso_now()})


dist_dir = os.path.join("frontend", "dist")
if os.path.isdir(dist_dir):
    app.mount("/", StaticFiles(directory=dist_dir, html=True), name="static")
else:
    raise RuntimeError(
        "Frontend dist directory not found. Please run 'npm run build' in the frontend directory."
    )
