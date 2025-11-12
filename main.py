from typing import Set, Dict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
import json
import os
from datetime import datetime
import pytz
from collections import defaultdict
from uuid import uuid4

# --- DB (SQLite, SQLAlchemy sync) ---
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Index
from sqlalchemy.orm import declarative_base, sessionmaker

DB_URL = "sqlite:///./chat.db"
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    room = Column(String(128), index=True)
    msg_type = Column(String(32))                 # chat/system/assign/users 등
    sender = Column(String(128))
    text = Column(Text)
    timestamp = Column(DateTime)                  # KST naive로 저장(표시 용)
    msg_id = Column(String(64), index=True)       # 클라 중복 전송 대비용(optional)
    image_data = Column(Text, nullable=True)      # Base64 인코딩된 이미지 데이터(image 타입용)

Index("idx_room_timestamp", Message.room, Message.timestamp)

def init_db():
    Base.metadata.create_all(bind=engine)

def save_message(room: str, msg: dict):
    """필요 필드만 저장."""
    with SessionLocal() as db:
        db.add(Message(
            room=room,
            msg_type=msg.get("type", "chat"),
            sender=msg.get("sender"),
            text=msg.get("text"),
            timestamp=_to_kst_dt(msg.get("timestamp")),
            msg_id=msg.get("msgId"),
            image_data=msg.get("imageData"),
        ))
        db.commit()

def load_recent_messages(room: str, limit: int = 50):
    with SessionLocal() as db:
        rows = db.query(Message)\
                 .filter(Message.room == room)\
                 .order_by(Message.timestamp.desc())\
                 .limit(limit).all()
        data = []
        for r in reversed(rows):
            msg_dict = {
                "type": r.msg_type,
                "sender": r.sender,
                "text": r.text,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                "room": room,
                "msgId": r.msg_id,
            }
            if r.image_data:
                msg_dict["imageData"] = r.image_data
            data.append(msg_dict)
        return data

def _to_kst_dt(ts_str: str | None):
    kst = pytz.timezone("Asia/Seoul")
    if ts_str:
        try:
            # ISO 문자열이면 파싱 시도
            return datetime.fromisoformat(ts_str.replace("Z", "+00:00")).astimezone(kst).replace(tzinfo=None)
        except:
            pass
    return datetime.now(kst).replace(tzinfo=None)

# --- App ---
app = FastAPI(title="Mini Chat (rooms + history)")
init_db()

# 메모리 상태
rooms: Dict[str, Set[WebSocket]] = defaultdict(set)        # room -> set(ws)
user_by_ws: Dict[WebSocket, str] = {}                      # ws -> name
room_by_ws: Dict[WebSocket, str] = {}                      # ws -> room
users_in_room: Dict[str, Set[str]] = defaultdict(set)      # room -> set(name)

def kst_iso_now():
    kst = pytz.timezone('Asia/Seoul')
    return datetime.now(kst).isoformat()

async def broadcast_room(room: str, message: dict):
    # timestamp 자동 추가
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
        # 정리
        await _cleanup_ws(ws)

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    # 쿼리 파싱
    name = ws.query_params.get("name", "익명")
    room = ws.query_params.get("room", "lobby")

    await ws.accept()

    # 방 단위 닉 중복 처리
    assigned = name
    if assigned in users_in_room[room]:
        idx = 1
        while f"{name}_{idx}" in users_in_room[room]:
            idx += 1
        assigned = f"{name}_{idx}"
        try:
            await ws.send_text(json.dumps({"type": "assign", "name": assigned, "room": room}, ensure_ascii=False))
        except Exception:
            pass

    # 입장 처리
    rooms[room].add(ws)
    room_by_ws[ws] = room
    user_by_ws[ws] = assigned
    users_in_room[room].add(assigned)

    # 1) 최근 히스토리 전송
    history = load_recent_messages(room, limit=50)
    try:
        await ws.send_text(json.dumps({"type": "history", "room": room, "messages": history}, ensure_ascii=False))
    except Exception:
        pass

    # 2) 현재 방 사용자 목록 브로드캐스트
    await broadcast_room(room, {"type": "users", "users": sorted(list(users_in_room[room]))})

    # 3) 입장 시스템 메시지(브로드캐스트 + 저장)
    join_msg = {"type": "system", "text": f"🟢 {assigned} 님이 '{room}' 방에 입장했습니다.", "sender": "system", "room": room}
    await broadcast_room(room, join_msg)
    save_message(room, {**join_msg, "timestamp": kst_iso_now()})

    try:
        while True:
            text = await ws.receive_text()

            # 클라가 순수 텍스트만 보내도 되고, JSON을 보내도 됨.
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

            sender = user_by_ws.get(ws, "익명")
            room = room_by_ws.get(ws, "lobby")

            message = {
                "type": msg_type,
                "text": msg_text,
                "sender": sender,
                "timestamp": kst_iso_now(),
                "room": room,
                "msgId": msg_id,
            }
            
            # image 타입일 경우 imageData 추가
            if image_data:
                message["imageData"] = image_data

            # 같은 방에만 브로드캐스트
            await broadcast_room(room, message)

            # 히스토리 저장 (chat/system/image 등 모두 저장)
            save_message(room, message)

    except WebSocketDisconnect:
        await _cleanup_ws(ws)
    except Exception:
        await _cleanup_ws(ws)
        # 오류 시스템 메시지 (방에 남아있는 사람들에게만)
        room = room_by_ws.get(ws)
        name = user_by_ws.get(ws, "익명")
        if room:
            err_msg = {"type": "system", "text": f"⚠️ {name} 연결 오류로 종료", "sender": "system", "room": room}
            await broadcast_room(room, err_msg)
            save_message(room, {**err_msg, "timestamp": kst_iso_now()})

async def _cleanup_ws(ws: WebSocket):
    room = room_by_ws.pop(ws, None)
    name = user_by_ws.pop(ws, None)
    if room:
        rooms[room].discard(ws)
        if name:
            users_in_room[room].discard(name)
            # 사용자 목록 업데이트
            await broadcast_room(room, {"type": "users", "users": sorted(list(users_in_room[room]))})
            # 퇴장 메시지 저장/전파
            leave_msg = {"type": "system", "text": f"🔴 {name} 님이 '{room}' 방에서 퇴장했습니다.", "sender": "system", "room": room}
            await broadcast_room(room, leave_msg)
            save_message(room, {**leave_msg, "timestamp": kst_iso_now()})

# 정적 파일 제공 (프런트)
dist_dir = os.path.join("frontend", "dist")
if os.path.isdir(dist_dir):
    app.mount("/", StaticFiles(directory=dist_dir, html=True), name="static")
else:
    # 개발 중이라면 주석 처리하고 /docs로만 테스트 가능
    raise RuntimeError("Frontend dist directory not found. Please run 'npm run build' in the frontend directory.")
