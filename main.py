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
# 연결된 사용자 이름 목록
connected_users: Set[str] = set()

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
    # 먼저 accept한 뒤 닉네임 중복 검사
    await ws.accept()

    # 닉네임 중복 시 자동으로 유니크한 suffix를 붙여 할당
    assigned_name = name
    if assigned_name in connected_users:
        idx = 1
        while f"{name}_{idx}" in connected_users:
            idx += 1
        assigned_name = f"{name}_{idx}"
        # 클라이언트에게 할당된 닉네임을 알림
        try:
            await ws.send_text(json.dumps({"type": "assign", "name": assigned_name}, ensure_ascii=False))
        except Exception:
            pass

    # 연결/사용자 목록에 추가
    active_connections.add(ws)
    connected_users.add(assigned_name)

    # 사용자 목록 업데이트 브로드캐스트
    await broadcast({"type": "users", "users": list(connected_users)})
    # 입장 알림 (할당된 닉네임 사용)
    await broadcast({"type": "system", "text": f"🟢 {assigned_name} 님이 입장했습니다.", "sender": "system"})

    try:
        while True:
            text = await ws.receive_text()
            await broadcast({"type": "chat", "text": text, "sender": assigned_name})
    except WebSocketDisconnect:
        active_connections.discard(ws)
        connected_users.discard(assigned_name)
        # 사용자 목록 업데이트 브로드캐스트
        await broadcast({"type": "users", "users": list(connected_users)})
        # 퇴장 알림 (할당된 닉네임 사용)
        await broadcast({"type": "system", "text": f"🔴 {assigned_name} 님이 퇴장했습니다.", "sender": "system"})
    except Exception:
        active_connections.discard(ws)
        connected_users.discard(assigned_name)
        # 사용자 목록 업데이트 브로드캐스트
        await broadcast({"type": "users", "users": list(connected_users)})
        # 오류 알림 (할당된 닉네임 사용)
        await broadcast({"type": "system", "text": f"⚠️ {assigned_name} 연결 오류로 종료", "sender": "system"})

# 정적 파일 제공 (프런트)
dist_dir = os.path.join("frontend", "dist")
if os.path.isdir(dist_dir):
    app.mount("/", StaticFiles(directory=dist_dir, html=True), name="static")
else:
    raise RuntimeError("Frontend dist directory not found. Please run 'npm run build' in the frontend directory.")
