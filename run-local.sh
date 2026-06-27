#!/usr/bin/env bash
# Tüm sistemi lokalde başlatır: backend (8000) + dashboard (3000) + frontend-vue (5173).
# Kullanım:  ./run-local.sh        (Ctrl-C hepsini durdurur)
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PY="backend/.venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "HATA: backend/.venv yok. Önce kurulum:"
  echo "  cd backend && python3.11 -m venv .venv && .venv/bin/python -m pip install -e ."
  exit 1
fi

PIDS=()
cleanup() { echo; echo "Kapatılıyor…"; for p in "${PIDS[@]:-}"; do kill "$p" 2>/dev/null || true; done; }
trap cleanup INT TERM EXIT

# 1) BIST sinyalleri yoksa $0 (anahtarsız) seed üret ki UI boş açılmasın
if ! ls backend/data/out/signals_bist_*.json >/dev/null 2>&1; then
  echo "▶ İlk BIST seed üretiliyor ($0, anahtarsız)…"
  "$PY" backend/scripts/run_decision_panel.py --market bist \
    --symbols THYAO.IS,GARAN.IS,AKBNK.IS,EREGL.IS,BIMAS.IS,ASELS.IS,KCHOL.IS,SISE.IS \
    --no-debate --no-macro --top-n 8 --export || echo "  (seed atlandı — internet?)"
fi

echo "▶ backend   : http://localhost:8000   (Swagger: /docs)"
"$PY" backend/scripts/run_api.py --port 8000 & PIDS+=($!)

echo "▶ dashboard : http://localhost:3000   (Next.js — port doluysa 3001'e kayar)"
( cd dashboard && npm run dev ) & PIDS+=($!)

echo "▶ frontend  : http://localhost:5173   (Vue panel)"
( cd frontend-vue && npm run dev ) & PIDS+=($!)

echo
echo "Hepsi başlatıldı. Durdurmak için Ctrl-C."
wait
