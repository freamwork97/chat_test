import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from chat_app.config import FRONTEND_DIST
from chat_app.database import init_user_db
from chat_app.message_store import ensure_message_indexes
from chat_app.websocket_handlers import router as websocket_router

app = FastAPI(title="Mini Chat (rooms + history)")

# Initialize persistence layers before serving traffic
init_user_db()
ensure_message_indexes()

# Routes & websockets
app.include_router(websocket_router)

if os.path.isdir(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="static")
else:
    raise RuntimeError(
        "Frontend dist directory not found. Please run 'npm run build' in the frontend directory."
    )

