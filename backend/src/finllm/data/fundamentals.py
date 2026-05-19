"""Fundamental data fetcher — yfinance.Ticker.info (kapsamlı, yavaş).

`yf.Ticker(sym).info` ~80 alan döner ama yavaş (~1-3s/call).
Bu yüzden parquet cache: aynı gün içinde tekrar çekilmesin.

Phase 3.1: NASDAQ tam, BIST kısıtlı (yfinance BIST için bazı alanları döndürmüyor).
Phase 3.5'te BIST için ek scraper (İş Yatırım/Mynet) opsiyon.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf
from tenacity import retry, stop_after_attempt, wait_exponential

from finllm.config.settings import settings
from finllm.markets.base import FundamentalSnapshot, Ticker
from finllm.utils.logging import logger


_CACHE_TTL_HOURS = 12  # Bilançolar gün içinde değişmez


def _cache_path(yahoo_symbol: str) -> Path:
    safe_name = yahoo_symbol.replace("=", "_").replace(".", "_")
    return settings.cache_dir / f"fundamentals_{safe_name}.json"


def _is_cache_fresh(path: Path) -> bool:
    if not path.exists():
        return False
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    return (datetime.utcnow() - mtime) < timedelta(hours=_CACHE_TTL_HOURS)


def _load_cache(path: Path) -> dict | None:
    if not _is_cache_fresh(path):
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _save_cache(path: Path, data: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, default=str, indent=2))
    except Exception as e:
        logger.debug(f"[FUND] cache write fail: {e}")


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=8))
def _fetch_info_raw(yahoo_symbol: str) -> dict[str, Any]:
    """yfinance.Ticker.info — TÜM mevcut alanları çek."""
    try:
        yt = yf.Ticker(yahoo_symbol)
        info = yt.info  # comprehensive (slow)
        if not info or len(info) < 5:
            return {}
        return dict(info)
    except Exception as e:
        logger.warning(f"[FUND] {yahoo_symbol} info fail: {e}")
        return {}


def _fetch_earnings_date(yahoo_symbol: str) -> datetime | None:
    """En yakın bilanço açıklama tarihi."""
    try:
        yt = yf.Ticker(yahoo_symbol)
        dates: pd.DataFrame | None = yt.earnings_dates
        if dates is None or dates.empty:
            return None
        future = dates[dates.index > pd.Timestamp.utcnow()]
        if future.empty:
            return None
        return future.index.min().to_pydatetime()
    except Exception as e:
        logger.debug(f"[FUND] {yahoo_symbol} earnings_dates fail: {e}")
        return None


def _to_float(v: Any) -> float | None:
    """yfinance bazen string/None döner; güvenli convert."""
    if v is None:
        return None
    try:
        if isinstance(v, str):
            return None  # string olarak gelen değerleri trust etme
        f = float(v)
        # yfinance bazen 0 yerine inf veya nan dönüyor
        if f != f or abs(f) == float("inf"):
            return None
        return f
    except (TypeError, ValueError):
        return None


def fetch_fundamentals(
    ticker: Ticker,
    yahoo_symbol: str,
    use_cache: bool = True,
) -> FundamentalSnapshot | None:
    """Tek ticker için kapsamlı fundamentals + parquet cache.

    Args:
        ticker: pipeline Ticker
        yahoo_symbol: Yahoo Finance formatı (örn 'AAPL', 'THYAO.IS', 'GC=F')
        use_cache: aynı gün tekrar fetch'i atla

    Returns: FundamentalSnapshot. None = data alınamadı.
    """
    cache = _cache_path(yahoo_symbol)
    info: dict[str, Any] = {}

    if use_cache:
        cached = _load_cache(cache)
        if cached is not None:
            info = cached.get("info", {})
            logger.debug(f"[FUND] {yahoo_symbol} cache hit")

    if not info:
        info = _fetch_info_raw(yahoo_symbol)
        if not info:
            return None
        _save_cache(cache, {"info": info, "fetched_at": datetime.utcnow().isoformat()})

    earnings_date = _fetch_earnings_date(yahoo_symbol)

    snap = FundamentalSnapshot(
        ticker=ticker,
        # Market data
        market_cap=_to_float(info.get("marketCap")),
        shares_outstanding=_to_float(info.get("sharesOutstanding")),
        float_shares=_to_float(info.get("floatShares")),
        short_ratio=_to_float(info.get("shortRatio")),
        avg_volume_10d=_to_float(info.get("averageVolume10days") or info.get("averageDailyVolume10Day")),
        avg_volume_20d=_to_float(info.get("averageVolume")),
        # Valuation
        pe_ratio=_to_float(info.get("trailingPE")),
        forward_pe=_to_float(info.get("forwardPE")),
        pb_ratio=_to_float(info.get("priceToBook")),
        ps_ratio=_to_float(info.get("priceToSalesTrailing12Months")),
        ev_to_ebitda=_to_float(info.get("enterpriseToEbitda")),
        ev_to_revenue=_to_float(info.get("enterpriseToRevenue")),
        peg_ratio=_to_float(info.get("trailingPegRatio") or info.get("pegRatio")),
        # Profitability
        profit_margin=_to_float(info.get("profitMargins")),
        gross_margin=_to_float(info.get("grossMargins")),
        operating_margin=_to_float(info.get("operatingMargins")),
        roe=_to_float(info.get("returnOnEquity")),
        roa=_to_float(info.get("returnOnAssets")),
        # Growth
        revenue_growth_yoy=_to_float(info.get("revenueGrowth")),
        earnings_growth_yoy=_to_float(info.get("earningsGrowth")),
        revenue_growth_quarterly=_to_float(info.get("revenueQuarterlyGrowth")),
        earnings_growth_quarterly=_to_float(info.get("earningsQuarterlyGrowth")),
        # Balance
        debt_to_equity=_to_float(info.get("debtToEquity")),
        current_ratio=_to_float(info.get("currentRatio")),
        quick_ratio=_to_float(info.get("quickRatio")),
        total_cash=_to_float(info.get("totalCash")),
        total_debt=_to_float(info.get("totalDebt")),
        free_cash_flow=_to_float(info.get("freeCashflow")),
        book_value=_to_float(info.get("bookValue")),
        # Dividend
        dividend_yield=_to_float(info.get("dividendYield")),
        payout_ratio=_to_float(info.get("payoutRatio")),
        five_year_avg_dividend_yield=_to_float(info.get("fiveYearAvgDividendYield")),
        # Earnings calendar
        earnings_date=earnings_date,
        # Meta
        sector=info.get("sector"),
        industry=info.get("industry"),
        country=info.get("country"),
    )
    return snap


__all__ = ["fetch_fundamentals"]
