"""Minimal, dependency-light API serving the decision-panel export to the dashboard.

The full v2 app (api/main.py) pulls in DB-backed routes (sqlalchemy/duckdb). The
dashboard only needs the file-based latest signals + portfolio, so this standalone
app serves exactly that from DATA_DIR/out/signals_<market>_*.json (written by
api/panel_serialize.write_signals_file / `run_decision_panel.py --export`).

Run:
    uvicorn finllm.api.panel_server:app --port 8000
Then point the dashboard at it: BACKEND_API_URL=http://localhost:8000
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from finllm.config.settings import DATA_DIR

app = FastAPI(title="FinLLM Panel API", version="1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

_OUT = DATA_DIR / "out"


def _latest(market: str | None) -> dict:
    pattern = f"signals_{market}_*.json" if market else "signals_*.json"
    files = sorted(_OUT.glob(pattern), reverse=True)
    if not files:
        raise HTTPException(404, "No panel signals yet — run scripts/run_decision_panel.py --export")
    return json.loads(files[0].read_text())


@app.get("/health")
def health() -> dict:
    n = len(list(_OUT.glob("signals_*.json"))) if _OUT.exists() else 0
    return {"status": "ok", "signal_files": n}


@app.get("/signals/latest")
@app.get("/v2/signals/latest")
def latest(market: str | None = None) -> dict:
    return _latest(market)


@app.get("/portfolio")
@app.get("/v2/portfolio")
def portfolio(market: str | None = None) -> dict:
    """Derive the portfolio view from the latest signals' allocations."""
    data = _latest(market)
    positions = [
        {"ticker": s["ticker"], "sector": s.get("sector", ""),
         "weight_pct": s["allocation_weight"], "action": s["signal"],
         "confidence": s["confidence"], "cash": s["allocation_cash"]}
        for s in data["signals"] if s.get("is_actionable")
    ]
    return {
        "market": data["summary"]["market"],
        "cash_pct": data["summary"].get("cash_buffer_pct", 100.0),
        "positions": positions,
        "run_id": data["summary"]["run_id"],
    }


__all__ = ["app"]
