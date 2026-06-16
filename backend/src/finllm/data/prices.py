"""OHLCV veri çekme — yfinance birincil kaynak, parquet cache."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import yfinance as yf
from tenacity import retry, stop_after_attempt, wait_exponential

from finllm.config.settings import settings
from finllm.utils.logging import logger


def _cache_path(symbol: str, interval: str) -> Path:
    return settings.cache_dir / f"prices_{symbol}_{interval}.parquet"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _download(symbol: str, start: str, end: str | None, interval: str) -> pd.DataFrame:
    # timeout caps yfinance's own socket wait so a single hung symbol can't stall a
    # 500-name backtest indefinitely — it fails fast, retries, then skips. Without
    # it one flaky name blocks the whole universe load (observed: 30-min hangs).
    df = yf.download(
        symbol,
        start=start,
        end=end,
        interval=interval,
        progress=False,
        auto_adjust=True,
        actions=False,
        timeout=20,
    )
    if df.empty:
        raise ValueError(f"No data returned for {symbol}")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [c.lower() for c in df.columns]
    df.index.name = "date"
    return df


def fetch_prices(
    symbol: str,
    start: str = "2018-01-01",
    end: str | None = None,
    interval: str = "1d",
    use_cache: bool = True,
) -> pd.DataFrame:
    cache_file = _cache_path(symbol, interval)
    end = end or datetime.utcnow().strftime("%Y-%m-%d")

    if use_cache and cache_file.exists():
        cached = pd.read_parquet(cache_file)
        first_date = cached.index.min().strftime("%Y-%m-%d")
        last_date = cached.index.max().strftime("%Y-%m-%d")
        needs_backfill = start < first_date
        needs_forward = last_date < end
        if not needs_backfill and not needs_forward:
            return cached.loc[start:end]

        pieces = [cached]
        if needs_backfill:
            logger.info(f"{symbol}: cache backfill {start} → {first_date}")
            pieces.insert(0, _download(symbol, start, first_date, interval))
        if needs_forward:
            logger.info(f"{symbol}: cache forward {last_date} → {end}")
            pieces.append(_download(symbol, last_date, end, interval))
        merged = pd.concat(pieces)
        merged = merged[~merged.index.duplicated(keep="last")].sort_index()
        merged.to_parquet(cache_file)
        return merged.loc[start:end]

    logger.info(f"{symbol}: full download {start} → {end}")
    df = _download(symbol, start, end, interval)
    df.to_parquet(cache_file)
    return df


def fetch_universe(
    symbols: list[str],
    start: str = "2018-01-01",
    end: str | None = None,
    interval: str = "1d",
) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        try:
            out[sym] = fetch_prices(sym, start=start, end=end, interval=interval)
        except Exception as e:
            logger.warning(f"{sym} skipped: {e}")
    return out
