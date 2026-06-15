"""Macro context assembler — builds the MACRO CONTEXT block for the macro→sector
layer (Faz B.1) from FREE sources: yfinance market/rate/commodity tickers + RSS
headlines. No paid API key required.

What it can NOT get without FRED: point-in-time CPI/PCE and NFP/unemployment
prints. Those slots are emitted as "(unavailable)" so the LLM correctly flags
thin context rather than inventing numbers. Add a FRED reader later to fill them.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from finllm.data.prices import fetch_prices
from finllm.utils.logging import logger

# Free macro tickers (yfinance). Yields are CBOE indices quoted as the rate.
MACRO_TICKERS = {
    "VIX": "^VIX",
    "S&P500": "SPY",
    "Nasdaq100": "QQQ",
    "US10Y": "^TNX",
    "US13W": "^IRX",
    "USD_DXY": "DX-Y.NYB",
    "Gold": "GC=F",
    "Oil_WTI": "CL=F",
}
INDEX_KEYS = {"S&P500", "Nasdaq100"}  # ones where 200-DMA position is meaningful


def _series(name: str, ticker: str) -> pd.DataFrame | None:
    start = (datetime.utcnow() - timedelta(days=400)).strftime("%Y-%m-%d")
    try:
        df = fetch_prices(ticker, start=start, use_cache=True)
        return df if not df.empty else None
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[MACRO] {name} ({ticker}) fetch failed: {e}")
        return None


def _pct(a: float, b: float) -> float:
    return (a / b - 1) * 100 if b else 0.0


def _describe(name: str, df: pd.DataFrame) -> str:
    closes = df["close"].dropna()
    if len(closes) < 2:
        return f"{name}: n/a"
    last = float(closes.iloc[-1])
    chg5 = _pct(last, float(closes.iloc[-6])) if len(closes) >= 6 else 0.0
    chg20 = _pct(last, float(closes.iloc[-21])) if len(closes) >= 21 else 0.0
    parts = [f"{name} {last:,.2f} (5d {chg5:+.1f}%, 20d {chg20:+.1f}%)"]
    if name in INDEX_KEYS and len(closes) >= 200:
        sma200 = float(closes.tail(200).mean())
        pos = "ABOVE" if last > sma200 else "BELOW"
        parts.append(f"{pos} 200-DMA")
    return " — ".join(parts)


def _headlines(market: str, limit: int) -> list[str]:
    try:
        from finllm.data.news.rss_reader import RssReader

        items = RssReader(market="global").fetch(max_age_hours=48, limit=limit)
        out = []
        for n in items[:limit]:
            when = n.pub_date.strftime("%m-%d") if getattr(n, "pub_date", None) else ""
            out.append(f"- [{when}] {n.title.strip()} ({n.source})")
        return out
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[MACRO] headlines fetch failed: {e}")
        return []


def build_macro_context(
    market: str = "nasdaq",
    news_limit: int = 12,
    with_news: bool = True,
) -> str:
    """Assemble a MACRO CONTEXT block from free live data. Degrades gracefully:
    any failed source is simply omitted (the LLM flags thin context)."""
    frames = {name: _series(name, tk) for name, tk in MACRO_TICKERS.items()}

    regime, rates, commodities, usd = [], [], [], []
    for name, df in frames.items():
        if df is None:
            continue
        line = _describe(name, df)
        if name in ("VIX", "S&P500", "Nasdaq100"):
            regime.append(line)
        elif name in ("US10Y", "US13W"):
            rates.append(line)
        elif name in ("Gold", "Oil_WTI"):
            commodities.append(line)
        elif name == "USD_DXY":
            usd.append(line)

    blocks: list[str] = []
    blocks.append(
        "[RATES] (point-in-time Fed decision/CPI/PCE/NFP unavailable without FRED — flag as thin)\n"
        + ("\n".join(rates) if rates else "n/a")
    )
    blocks.append("[MARKET REGIME]\n" + ("\n".join(regime) if regime else "n/a"))
    blocks.append("[COMMODITIES]\n" + ("\n".join(commodities) if commodities else "n/a"))
    blocks.append("[USD]\n" + ("\n".join(usd) if usd else "n/a"))

    if with_news:
        heads = _headlines(market, news_limit)
        blocks.append("[HEADLINES] (last 48h)\n" + ("\n".join(heads) if heads else "n/a"))

    stamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    return f"[AS OF] {stamp}\n\n" + "\n\n".join(blocks)


__all__ = ["build_macro_context", "MACRO_TICKERS"]
