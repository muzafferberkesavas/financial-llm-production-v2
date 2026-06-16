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


def _series(name: str, ticker: str, as_of: str | None = None) -> pd.DataFrame | None:
    end = as_of or datetime.utcnow().strftime("%Y-%m-%d")
    start = (datetime.strptime(end, "%Y-%m-%d") - timedelta(days=400)).strftime("%Y-%m-%d")
    try:
        df = fetch_prices(ticker, start=start, end=end, use_cache=True)
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

        # DEFAULT_SOURCES are tagged "bist"/"nasdaq" (none "global") — use the
        # market's own feeds (US: MarketWatch/CNBC/Seeking Alpha) for macro headlines.
        rss_market = "nasdaq" if market not in ("bist", "nasdaq") else market
        items = RssReader(market=rss_market).fetch(max_age_hours=48, limit=limit)
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
    as_of: str | None = None,
) -> str:
    """Assemble a MACRO CONTEXT block from free sources. Degrades gracefully:
    any failed source is omitted (the LLM flags thin context).

    `as_of` (YYYY-MM-DD) makes the whole block point-in-time for historical
    backtests — prices are sliced to that date, FRED queried as-of, and live RSS
    news (which has no history) is skipped automatically.

    For `market="bist"` the context is built from TURKISH drivers (TCMB policy
    rate / CPI / USD-TRY + BIST index regime), not the Fed — the right drivers for
    BIST's domestic sectors.
    """
    if market == "bist":
        return _build_bist_context(news_limit, with_news, as_of)

    frames = {name: _series(name, tk, as_of) for name, tk in MACRO_TICKERS.items()}

    regime, rates_yf, commodities, usd = [], [], [], []
    for name, df in frames.items():
        if df is None:
            continue
        line = _describe(name, df)
        if name in ("VIX", "S&P500", "Nasdaq100"):
            regime.append(line)
        elif name in ("US10Y", "US13W"):
            rates_yf.append(line)
        elif name in ("Gold", "Oil_WTI"):
            commodities.append(line)
        elif name == "USD_DXY":
            usd.append(line)

    blocks: list[str] = []

    # Rates / inflation / employment: prefer FRED (real prints, point-in-time);
    # fall back to yfinance yields + a thin-context flag when no FRED key.
    from finllm.data.fred import fred_macro_block

    fred = fred_macro_block(as_of=as_of)
    if fred:
        blocks.append(fred)
    else:
        blocks.append(
            "[RATES] (CPI/PCE/NFP/Fed decision unavailable — no FRED key, flag as thin)\n"
            + ("\n".join(rates_yf) if rates_yf else "n/a")
        )

    blocks.append("[MARKET REGIME]\n" + ("\n".join(regime) if regime else "n/a"))
    blocks.append("[COMMODITIES]\n" + ("\n".join(commodities) if commodities else "n/a"))
    blocks.append("[USD]\n" + ("\n".join(usd) if usd else "n/a"))

    # Live RSS news has no history → only include for the live (as_of=None) path.
    if with_news and as_of is None:
        heads = _headlines(market, news_limit)
        blocks.append("[HEADLINES] (last 48h)\n" + ("\n".join(heads) if heads else "n/a"))

    stamp = as_of or datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    return f"[AS OF] {stamp}\n\n" + "\n\n".join(blocks)


def _build_bist_context(news_limit: int, with_news: bool, as_of: str | None) -> str:
    """BIST macro context — Turkish drivers (TCMB + XU100/USD-TRY + gold + news)."""
    blocks: list[str] = []

    from finllm.data.tcmb import tcmb_macro_block

    tcmb = tcmb_macro_block() if as_of is None else None  # EVDS as-of not wired yet
    blocks.append(tcmb if tcmb else "[TÜRK MAKRO] (TCMB anahtarı/verisi yok — thin)")

    regime = []
    for name, tk in (("BIST XU100", "XU100.IS"), ("USD/TRY", "USDTRY=X")):
        df = _series(name, tk, as_of)
        if df is not None:
            regime.append(_describe(name, df))
    blocks.append("[PİYASA REJİMİ]\n" + ("\n".join(regime) if regime else "n/a"))

    gold = _series("Gold", "GC=F", as_of)
    if gold is not None:
        blocks.append("[EMTİA]\n" + _describe("Altın (USD/ons)", gold))

    if with_news and as_of is None:
        heads = _headlines("bist", news_limit)
        blocks.append("[HABERLER] (son 48s)\n" + ("\n".join(heads) if heads else "n/a"))

    stamp = as_of or datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    return f"[AS OF] {stamp} · BIST\n\n" + "\n\n".join(blocks)


__all__ = ["build_macro_context", "MACRO_TICKERS"]
