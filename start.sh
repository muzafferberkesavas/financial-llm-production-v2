#!/usr/bin/env bash
# Backend (8000) + Frontend-Vue (5173) ayni anda baslatir.
# Kullanim:  bash start.sh   veya   ./start.sh
# Durdurmak: Ctrl-C
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PIDS=()
cleanup() { echo; echo "Kapatiliyor..."; for p in "${PIDS[@]:-}"; do kill "$p" 2>/dev/null || true; done; exit 0; }
trap cleanup INT TERM EXIT

echo "============================================"
echo "  FinLLM Lokal Gelistirme Ortami"
echo "============================================"
echo ""

# Backend
echo "[1/2] Backend baslatiliyor (port 8001)..."
(cd backend && .venv/Scripts/python.exe scripts/run_api.py --port 8001 --reload) &
PIDS+=($!)

# Frontend-Vue
echo "[2/2] Frontend baslatiliyor (port 5173)..."
(cd frontend-vue && npm run dev) &
PIDS+=($!)

echo ""
echo "  Backend  : http://localhost:8001  (Swagger: /docs)"
echo "  Frontend : http://localhost:5173"
echo ""
echo "Durdurmak icin Ctrl-C"
wait
