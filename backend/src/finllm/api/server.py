"""FastAPI — dashboard'un çağıracağı backend.

Çalıştır:
    cd backend && uvicorn finllm.api.server:app --reload --port 8000
"""
from __future__ import annotations

import json
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from finllm.config.settings import settings
from finllm.portfolio import repository as repo
from finllm.portfolio.manager import daily_refresh, get_snapshot
from finllm.portfolio.models import PortfolioSnapshot
from finllm.signals.generator import generate_signal
from finllm.signals.schema import Signal
from finllm.utils.logging import logger

app = FastAPI(title="FinLLM API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3007"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SIGNALS_CACHE = settings.processed_dir / "latest_signals.json"


@app.on_event("startup")
def _init():
    repo.ensure_schema()


@app.get("/health")
def health():
    return {"ok": True, "env": settings.env}


# ---------- Signals ----------

@app.get("/signals/latest")
def latest_signals():
    if not SIGNALS_CACHE.exists():
        return {"signals": [], "message": "Henüz sinyal yok. POST /portfolio/refresh çağır."}
    with SIGNALS_CACHE.open() as f:
        return json.load(f)


@app.post("/signals/generate")
def generate_one(symbol: str) -> Signal:
    try:
        return generate_signal(symbol.upper())
    except Exception as e:
        logger.exception("Signal generation failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ---------- Portfolio ----------

@app.get("/portfolio", response_model=PortfolioSnapshot)
def portfolio():
    return get_snapshot()


@app.get("/portfolio/orders/pending")
def get_pending_orders():
    return {"orders": [o.model_dump() for o in repo.pending_orders()]}


@app.get("/portfolio/positions/open")
def get_open_positions():
    return {"positions": [p.model_dump() for p in repo.open_positions()]}


@app.get("/portfolio/positions/all")
def get_all_positions(limit: int = 100):
    return {"positions": [p.model_dump() for p in repo.all_positions(limit=limit)]}


@app.get("/portfolio/stats")
def get_stats():
    return repo.portfolio_stats()


@app.post("/portfolio/orders/{order_id}/execute")
def execute_order(order_id: int, executed_price: float):
    """Kullanıcı emri broker'da uyguladıktan sonra burada işaretler."""
    try:
        pending = {o.id: o for o in repo.pending_orders()}
        if order_id not in pending:
            raise HTTPException(404, f"Pending order {order_id} bulunamadı")
        order = pending[order_id]
        if order.side == "BUY":
            position_id = repo.execute_buy_order(order_id, executed_price)
            return {"ok": True, "position_id": position_id}
        else:
            repo.execute_sell_order(order_id, executed_price)
            return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Execute order failed")
        raise HTTPException(500, str(e)) from e


@app.post("/portfolio/orders/{order_id}/cancel")
def cancel_order(order_id: int):
    from finllm.storage.db import connection
    with connection() as c:
        r = c.execute(
            "UPDATE orders SET status='cancelled' WHERE id=? AND status='pending' RETURNING id",
            [order_id],
        ).fetchone()
    if not r:
        raise HTTPException(404, "Pending order bulunamadı")
    return {"ok": True}


@app.post("/portfolio/refresh")
def refresh(
    mode: Literal["pre_open", "post_close", "manual"] = "manual",
    universe: str = "core",
):
    """Tam günlük refresh: sinyal üret + exit değerlendir + yeni emirler."""
    try:
        report = daily_refresh(mode=mode, universe=universe)
        return {
            "mode": report.mode,
            "signals_generated": report.signals_generated,
            "positions_evaluated": report.positions_evaluated,
            "sell_orders_created": report.sell_orders_created,
            "buy_orders_created": report.buy_orders_created,
            "errors": report.errors,
        }
    except Exception as e:
        logger.exception("Refresh failed")
        raise HTTPException(500, str(e)) from e
