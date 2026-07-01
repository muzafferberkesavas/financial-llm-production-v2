"""GET /v2/stocks/{ticker} — hisse detay endpoint'i.

Ceyreklik finansallar, KAP bildirimleri ve teknik gostergeler doner.
"""
from __future__ import annotations

import asyncio
import math
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Query

from finllm.config.settings import settings
from finllm.utils.logging import logger

router = APIRouter(prefix="/v2", tags=["stocks"])

_executor = ThreadPoolExecutor(max_workers=3)

# Teknik gostergelerden API'ye sunulacak alt kume
_INDICATOR_KEYS = [
    "rsi_14", "rsi_7", "macd", "macd_signal", "macd_hist",
    "sma_10", "sma_20", "sma_50", "sma_200",
    "ema_12", "ema_26",
    "price_vs_sma20", "price_vs_sma50", "price_vs_sma200",
    "adx_14", "di_plus", "di_minus",
    "atr_14", "atr_pct",
    "bb_pct", "bb_width",
    "vol_ratio", "mfi_14", "cmf_20",
    "stoch_k", "stoch_d",
    "supertrend_dir",
    "cci_20", "willr_14", "roc_10",
    "aroon_osc",
    "vol_20d",
]


def _safe_json(val: Any) -> Any:
    """NaN/Inf -> None for JSON serialization."""
    if val is None:
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return round(f, 6)
    except (TypeError, ValueError):
        return None


def _fetch_quarterly(yahoo_symbol: str) -> dict | None:
    try:
        from finllm.data.quarterly_financials import fetch_quarterly

        result = fetch_quarterly(yahoo_symbol, cache_dir=settings.cache_dir)
        if result is None:
            return None
        return {
            "quarters": [asdict(q) for q in result.quarters],
            "fetched_at": result.fetched_at,
        }
    except Exception as e:
        logger.warning(f"[STOCK_DETAIL] quarterly error {yahoo_symbol}: {e}")
        return None


def _fetch_kap_data(ticker: str) -> dict | None:
    try:
        from finllm.data.kap import fetch_kap

        info = fetch_kap(ticker)
        return info.as_dict()
    except Exception as e:
        logger.warning(f"[STOCK_DETAIL] kap error {ticker}: {e}")
        return None


def _fetch_technicals(yahoo_symbol: str) -> dict | None:
    try:
        from finllm.data.prices import fetch_prices
        from finllm.features.technical import add_technical_features

        df = fetch_prices(yahoo_symbol, start="2023-01-01")
        if df.empty:
            return None
        df = add_technical_features(df)
        last = df.iloc[-1]

        price_info = {
            "close": _safe_json(last.get("close")),
            "change_1d_pct": _safe_json(last.get("ret_1d")),
            "change_5d_pct": _safe_json(last.get("ret_5d")),
            "change_20d_pct": _safe_json(last.get("ret_20d")),
        }
        indicators = {k: _safe_json(last.get(k)) for k in _INDICATOR_KEYS}

        as_of = str(df.index[-1].date()) if hasattr(df.index[-1], "date") else str(df.index[-1])

        return {
            "as_of": as_of,
            "price": price_info,
            "indicators": indicators,
        }
    except Exception as e:
        logger.warning(f"[STOCK_DETAIL] technicals error {yahoo_symbol}: {e}")
        return None


@router.get("/universe/bist")
def list_bist_stocks() -> dict:
    """BIST-100 hisse listesi (sembol, isim, sektor)."""
    from finllm.markets.universes.bist_100 import BIST_100_TICKERS

    return {
        "market": "bist",
        "count": len(BIST_100_TICKERS),
        "stocks": [
            {"symbol": t.symbol, "name": t.name, "sector": t.sector}
            for t in BIST_100_TICKERS
            if not t.is_commodity
        ],
    }


@router.get("/stocks/{ticker}")
async def stock_detail(
    ticker: str,
    market: str = Query("bist", pattern="^(bist|nasdaq)$"),
) -> dict:
    """Hisse detay: ceyreklik finansallar + KAP + teknik gostergeler."""
    yahoo_symbol = f"{ticker}.IS" if market == "bist" else ticker
    loop = asyncio.get_event_loop()

    # Paralel cek — birinin hatasi digerlerini etkilemesin
    quarterly_fut = loop.run_in_executor(_executor, _fetch_quarterly, yahoo_symbol)
    technicals_fut = loop.run_in_executor(_executor, _fetch_technicals, yahoo_symbol)

    kap_fut = loop.run_in_executor(_executor, _fetch_kap_data, ticker) if market == "bist" else None

    quarterly, technicals = await quarterly_fut, await technicals_fut
    kap = (await kap_fut) if kap_fut is not None else None

    return {
        "ticker": ticker,
        "market": market,
        "quarterly_financials": quarterly,
        "kap": kap,
        "technicals": technicals,
    }
