from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String, create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import POSTGRES_URL

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


def init_user_db():
    Base.metadata.create_all(bind=engine)
    reset_all_user_states()


def reset_all_user_states():
    """서버 시작 시 모든 사용자를 오프라인으로 초기화"""
    try:
        with SessionLocal() as db:
            db.query(ChatUser).update({ChatUser.is_active: False})
            db.commit()
    except SQLAlchemyError as exc:
        print(f"[PostgreSQL] Failed to reset user states: {exc}")


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

