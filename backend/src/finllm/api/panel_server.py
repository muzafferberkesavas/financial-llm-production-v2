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


@app.get("/v2/commodities")
@app.get("/commodities")
def commodities() -> dict:
    """Live gold (USD + gram-TRY), silver, USD/TRY — fetched fresh ($0, no LLM)."""
    from finllm.data.commodities import fetch_commodities

    return fetch_commodities().as_dict()


@app.get("/signals/latest")
@app.get("/v2/signals/latest")
def latest(market: str | None = None) -> dict:
    return _latest(market)


@app.get("/portfolio")
@app.get("/v2/portfolio")
@app.get("/v2/portfolio/{market}")
def portfolio(market: str | None = None) -> dict:
    """PortfolioResponse derived from the latest signals' allocations."""
    data = _latest(market)
    summary = data["summary"]
    capital = summary.get("total_capital", 10_000.0)
    positions = [
        {
            "ticker": s["ticker"], "name": s.get("name", ""), "sector": s.get("sector", ""),
            "signal": s["signal"], "confidence": s["confidence"],
            "calibrated_probability": s.get("calibrated_probability"),
            "allocation_weight": s["allocation_weight"], "allocation_cash": s["allocation_cash"],
            "expected_return_pct": s.get("expected_return_pct"),
            "time_horizon_days": s.get("time_horizon_days"),
            "entry_zone_low": s.get("entry_zone_low"), "entry_zone_high": s.get("entry_zone_high"),
            "stop_loss": s.get("stop_loss"),
        }
        for s in data["signals"] if s.get("is_actionable")
    ]
    allocated_total = round(sum(p["allocation_cash"] for p in positions), 2)
    return {
        "market": summary["market"],
        "run_id": summary["run_id"],
        "as_of": summary.get("started_at", ""),
        "total_capital": capital,
        "cash_buffer_pct": summary.get("cash_buffer_pct", 100.0),
        "allocated_count": len(positions),
        "allocated_total": allocated_total,
        "cash_remaining": round(capital - allocated_total, 2),
        "positions": positions,
    }


__all__ = ["app"]
