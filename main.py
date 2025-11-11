from typing import Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import json
import os
from datetime import datetime, timezone
import pytz

app = FastAPI(title="Mini Chat")

# 연결된 클라이언트 관리
active_connections: Set[WebSocket] = set()

async def broadcast(message: dict):
    # timestamp 자동 추가 (없으면) - 한국 시간대로 변환
    if "timestamp" not in message:
        # UTC 현재 시간을 한국 시간대로 변환
        kst = pytz.timezone('Asia/Seoul')
        message["timestamp"] = datetime.now(kst).isoformat()
    
    data = json.dumps(message, ensure_ascii=False)
    # 끊어진 소켓은 제거
    dead = []
    for ws in active_connections:
        try:
            await ws.send_text(data)
        except Exception:
            dead.append(ws)
    for ws in dead:
        active_connections.discard(ws)

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    # 쿼리로 닉네임 받기 (기본값 '익명')
    name = ws.query_params.get("name", "익명")
    await ws.accept()
    active_connections.add(ws)
    await broadcast({"type": "system", "text": f"🟢 {name} 님이 입장했습니다.", "sender": "system"})

    try:
        while True:
            text = await ws.receive_text()
            await broadcast({"type": "chat", "text": text, "sender": name})
    except WebSocketDisconnect:
        active_connections.discard(ws)
        await broadcast({"type": "system", "text": f"🔴 {name} 님이 퇴장했습니다.", "sender": "system"})
    except Exception:
        active_connections.discard(ws)
        await broadcast({"type": "system", "text": f"⚠️ {name} 연결 오류로 종료", "sender": "system"})

# 정적 파일 제공 (프런트)
dist_dir = os.path.join("frontend", "dist")
if os.path.isdir(dist_dir):
    app.mount("/", StaticFiles(directory=dist_dir, html=True), name="static")
else:
    raise RuntimeError("Frontend dist directory not found. Please run 'npm run build' in the frontend directory.")
