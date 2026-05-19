"""FinLLM API v2 — Phase 2.5 FastAPI gateway.

Tüm client'lar (Telegram, Web, Mobile) bu API'yi tüketir.

Run:
    cd backend
    uvicorn finllm.api.main:app --reload --port 8000

Endpoints (v2):
    GET  /v2/health
    GET  /v2/signals/latest                  — son run sinyalleri
    GET  /v2/signals/by-ticker/{ticker}      — tek ticker son sinyal
    GET  /v2/signals/runs                    — run history
    GET  /v2/signals/run/{run_id}            — specific run detail
    GET  /v2/portfolio                        — tüm market portföyleri
    GET  /v2/portfolio/{market}               — market spesifik
    GET  /v2/history/outcomes                — closed/open outcomes
    GET  /v2/history/calibration             — Platt model status
    GET  /v2/watchlist/{user_id}             — user watchlist
    POST /v2/watchlist/{user_id}/add         — ticker ekle
    POST /v2/watchlist/{user_id}/remove      — ticker çıkar
    POST /v2/trigger/run                     — admin: pipeline tetikle (Bearer auth)
    POST /v2/trigger/update-outcomes         — admin: outcome+calibrator update
    WS   /v2/ws/live                          — live signal stream

Legacy (v1, eski server.py'den):
    GET  /health
    GET  /signals/latest
    POST /signals/generate
    GET  /portfolio
    POST /portfolio/refresh
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from finllm.api.routes import (
    history,
    portfolio,
    signals,
    signals_db,
    trigger,
    watchlist,
    ws_live,
)
from finllm.config.settings import settings

app = FastAPI(
    title="FinLLM API v2",
    version="2.0.0",
    description=(
        "Cross-market AI swing-trading signals for BIST + NASDAQ.\n\n"
        "**⚠️ Bu sistem yatırım tavsiyesi vermez** — analyst-grade taslak üretir, "
        "kullanıcı kendi kararını verir."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3007",
        "https://*.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/v2/health")
def health() -> dict:
    """Health check + sistem bilgisi."""
    return {
        "status": "ok",
        "version": "v2.0.0",
        "env": settings.env,
        "features": {
            "claude": bool(settings.anthropic_api_key),
            "finnhub": bool(settings.finnhub_api_key),
            "telegram": bool(settings.telegram_bot_token),
        },
    }


@app.get("/")
def root() -> dict:
    return {
        "name": "FinLLM API",
        "version": "v2",
        "docs": "/docs",
        "health": "/v2/health",
        "endpoints": [
            "/v2/signals/latest",
            "/v2/portfolio",
            "/v2/history/outcomes",
            "/v2/watchlist/{user_id}",
            "/v2/ws/live (WebSocket)",
        ],
    }


# Routers
app.include_router(signals.router)
app.include_router(signals_db.router)
app.include_router(portfolio.router)
app.include_router(history.router)
app.include_router(watchlist.router)
app.include_router(trigger.router)
app.include_router(ws_live.router)


# ---- Legacy v1 endpoints ----
# Mevcut dashboard'ın bozulmaması için eski server.py'nin endpoint'leri burada da
# çalışsın. Lazy import — eski FinLLM.Signal modeline bağımlı.
try:
    from finllm.api import server as legacy_server  # noqa: F401

    # Sadece v1 endpoint'leri ekle, çift /health çakışmasını önle
    for route in legacy_server.app.routes:
        if hasattr(route, "path") and route.path not in (r.path for r in app.routes):
            app.routes.append(route)
except Exception as e:
    import logging

    logging.warning(f"Legacy v1 endpoints yüklenemedi: {e}")
