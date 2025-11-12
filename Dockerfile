# ---------- Frontend build ----------
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend

# Install and build React app
COPY frontend/package.json ./ 
COPY frontend/tsconfig*.json ./ 
COPY frontend/vite.config.ts ./ 
COPY frontend/index.html ./ 
COPY frontend/src ./src
RUN npm install && npm run build


# ---------- Backend runtime ----------
FROM python:3.12-slim AS runtime
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Seoul

# ---- 필수 시스템 패키지 설치 ----
# sqlite3 런타임 및 개발 헤더, tzdata 설치
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        tzdata \
        sqlite3 \
        libsqlite3-dev && \
    rm -rf /var/lib/apt/lists/*

# ---- 시간대 설정 ----
RUN ln -snf /usr/share/zoneinfo/Asia/Seoul /etc/localtime && echo Asia/Seoul > /etc/timezone

# ---- Python dependencies ----
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ---- Backend code ----
COPY main.py ./

# ---- Frontend build output ----
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
