#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

echo "[deploy] Bringing stack down (if running)..."
docker compose down || true

echo "[deploy] Building and starting services..."
docker compose up -d --build

echo "[deploy] Current service status:"
docker compose ps
