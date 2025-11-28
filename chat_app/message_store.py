from __future__ import annotations

from datetime import datetime

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from .config import MONGO_COLLECTION_NAME, MONGO_DB_NAME, MONGO_URL
from .time_utils import as_kst_naive, kst_iso_now

mongo_client: MongoClient | None = None
message_collection: Collection | None = None

try:
    mongo_client = MongoClient(MONGO_URL)
    mongo_db = mongo_client[MONGO_DB_NAME]
    message_collection = mongo_db[MONGO_COLLECTION_NAME]
except PyMongoError as exc:
    print(f"[MongoDB] Connection failed: {exc}")


def ensure_message_indexes():
    if message_collection is None:
        return
    try:
        message_collection.create_index([("room", ASCENDING), ("timestamp", DESCENDING)])
        message_collection.create_index("msg_id")
    except PyMongoError as exc:
        print(f"[MongoDB] Failed to create indexes: {exc}")


def save_message(room: str, msg: dict):
    """MongoDB에 메시지 저장"""
    if message_collection is None:
        return
    doc = {
        "room": room,
        "msg_type": msg.get("type", "chat"),
        "sender": msg.get("sender"),
        "text": msg.get("text"),
        "timestamp": as_kst_naive(msg.get("timestamp")),
        "msg_id": msg.get("msgId"),
        "image_data": msg.get("imageData"),
        "file_name": msg.get("fileName"),
        "file_url": msg.get("fileUrl"),
        "file_size": msg.get("fileSize"),
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
        if r.get("msg_type") == "file":
            msg_dict["fileName"] = r.get("file_name")
            msg_dict["fileUrl"] = r.get("file_url")
            msg_dict["fileSize"] = r.get("file_size") or 0
        if "timestamp" not in msg_dict:
            msg_dict["timestamp"] = kst_iso_now()
        data.append(msg_dict)
    return data
