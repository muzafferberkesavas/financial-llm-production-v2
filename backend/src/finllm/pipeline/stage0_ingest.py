"""Stage 0 — Ingest: adapter üzerinden universe için ham veri topla.

Output: list[IngestedData] (PipelineContext.ingested'a yazılır).

Paralellik: ThreadPoolExecutor (yfinance I/O-bound).
Hata toleransı: bir ticker fail ederse skip, log; pipeline durmaz.
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path

from finllm.data.quarterly_financials import fetch_quarterly
from finllm.markets.base import Ticker
from finllm.pipeline.context import IngestedData, PipelineContext
from finllm.utils.logging import logger

_DEFAULT_CACHE_DIR = Path.home() / ".finllm" / "cache"


def _fetch_one(adapter, ticker: Ticker, lookback_days: int, cache_dir: Path, skip_news: bool = False) -> IngestedData:
    """Tek ticker için fiyat + fundamentals + quarterly + (stub) news."""
    errors: list[str] = []
    start = (datetime.utcnow() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

    # Prices
    try:
        prices = adapter.fetch_prices(ticker, start=start)
    except Exception as e:
        errors.append(f"prices: {e}")
        prices = adapter.fetch_prices.__self__.__class__  # placeholder, empty DF below
        import pandas as pd
        prices = pd.DataFrame()

    # Fundamentals
    fundamentals = None
    try:
        fundamentals = adapter.fetch_fundamentals(ticker)
    except Exception as e:
        errors.append(f"fundamentals: {e}")

    # Quarterly financials (yfinance, free, cached 45 days)
    quarterly = None
    try:
        yahoo_sym = adapter.format_yahoo_symbol(ticker)
        quarterly = fetch_quarterly(yahoo_sym, cache_dir)
    except Exception as e:
        errors.append(f"quarterly: {e}")

    # News (KAP/RSS — skip_news=True ise atla, timeout'lardan kaçınır)
    news: list[dict] = []
    if not skip_news:
        try:
            news = adapter.fetch_news(ticker, hours=24)
        except Exception as e:
            errors.append(f"news: {e}")

    return IngestedData(
        ticker=ticker,
        prices=prices,
        fundamentals=fundamentals,
        news=news,
        quarterly=quarterly,
        fetch_errors=errors,
    )


def run_stage0(
    ctx: PipelineContext,
    lookback_days: int = 365,
    max_workers: int = 8,
    cache_dir: Path | None = None,
    skip_news: bool = False,
) -> PipelineContext:
    """Stage 0 entry: adapter'ın evrenini paralel olarak indirir."""
    started = time.perf_counter()
    universe = ctx.adapter.get_universe()
    logger.info(f"[STAGE 0] {ctx.market}: {len(universe)} ticker ingest başlıyor")

    if cache_dir is None:
        cache_dir = _DEFAULT_CACHE_DIR

    results: list[IngestedData] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_fetch_one, ctx.adapter, t, lookback_days, cache_dir, skip_news): t
            for t in universe
        }
        for fut in as_completed(futures):
            ticker = futures[fut]
            try:
                data = fut.result()
                results.append(data)
                if data.fetch_errors:
                    logger.debug(f"[STAGE 0] {ticker} hata: {data.fetch_errors}")
            except Exception as e:
                logger.warning(f"[STAGE 0] {ticker} fetch exception: {e}")

    # Eksik fiyat dataset'i olanları logla
    valid = [d for d in results if d.has_price_data]
    rejected_count = len(results) - len(valid)
    if rejected_count > 0:
        logger.info(f"[STAGE 0] {rejected_count} ticker yetersiz veri (skip)")

    ctx.ingested = results
    duration = time.perf_counter() - started
    ctx.log_stage("stage0_ingest", duration)
    logger.info(
        f"[STAGE 0] tamam: {len(valid)}/{len(universe)} ticker veri OK ({duration:.1f}s)"
    )
    return ctx
