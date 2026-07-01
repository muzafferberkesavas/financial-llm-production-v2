"""Stage 0b — Market agenda fetch + translate.

Stage 0 (price ingest) sonrası, Stage 1 öncesi:
  1. Watchlist tickerlarına özel haber çek (Finnhub for NASDAQ, KAP for BIST)
  2. Genel market RSS haberlerini çek
  3. SEC EDGAR / KAP corporate disclosures
  4. NewsTranslator (Claude Haiku) ile İngilizce MARKET AGENDA üret
  5. PipelineContext.market_agenda'ya yaz

LLM cost per run: ~$0.005 (Haiku, ~3-4K input tokens).
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from finllm.data.news import (
    FinnhubReader,
    KapReader,
    NewsTranslator,
    RssReader,
    SecEdgarReader,
)
from finllm.data.news.base import CorporateDisclosure, NewsItem
from finllm.data.news.kap_translator import translate_disclosure
from finllm.pipeline.context import PipelineContext
from finllm.utils.logging import logger


def _fetch_market_news(market: str, max_age_hours: int) -> list[NewsItem]:
    """Market-wide RSS news (ticker-agnostic)."""
    try:
        rss = RssReader(market=market)
        return rss.fetch(max_age_hours=max_age_hours, limit=20)
    except Exception as e:
        logger.warning(f"[STAGE 0B] RSS market news ({market}): {e}")
        return []


def _fetch_ticker_news_nasdaq(symbol: str) -> list[NewsItem]:
    """Bir NASDAQ ticker için Finnhub haber."""
    try:
        fn = FinnhubReader()
        if not fn.is_available():
            return []
        return fn.fetch(ticker=symbol, max_age_hours=48, limit=5)
    except Exception as e:
        logger.debug(f"[STAGE 0B] Finnhub {symbol}: {e}")
        return []


def _fetch_ticker_sec(symbol: str) -> list[CorporateDisclosure]:
    """SEC EDGAR 8-K + 10-Q filings, son 30 gün."""
    try:
        sec = SecEdgarReader()
        return sec.fetch_disclosures(symbol, max_age_hours=24 * 30, limit=3)
    except Exception as e:
        logger.debug(f"[STAGE 0B] SEC {symbol}: {e}")
        return []


def _fetch_kap_disclosures(tickers: list[str]) -> list[CorporateDisclosure]:
    """KAP — toplu hisse listesi için."""
    try:
        kap = KapReader()
        if not kap.is_available():
            return []
        return kap.fetch_disclosures(tickers=tickers, max_age_hours=24, limit=20)
    except Exception as e:
        logger.warning(f"[STAGE 0B] KAP: {e}")
        return []


def run_stage0b(
    ctx: PipelineContext,
    watchlist_limit: int = 10,
    max_workers: int = 6,
) -> PipelineContext:
    """Stage 0b entry: news fetch + translate → ctx.market_agenda."""
    started = time.perf_counter()
    market = ctx.adapter.name

    # Stage 0'da ingest edilen ticker'lardan watchlist çıkar
    watchlist_symbols = [
        d.ticker.symbol for d in ctx.ingested if d.has_price_data
    ][:watchlist_limit]

    if not watchlist_symbols:
        logger.warning("[STAGE 0B] no tickers to fetch news for, skip")
        ctx.log_stage("stage0b_agenda", time.perf_counter() - started)
        return ctx

    logger.info(
        f"[STAGE 0B] {market}: watchlist {len(watchlist_symbols)} ticker, "
        f"market news + agenda çekiliyor"
    )

    # 1. Market-wide RSS (paralel ile uzun süre engellememeli)
    all_news: list[NewsItem] = []
    all_disclosures: list[CorporateDisclosure] = []

    # 2. Watchlist ticker-spesifik (paralel)
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        # RSS market news
        rss_future = pool.submit(_fetch_market_news, market, 24)

        # Ticker bazlı
        if market == "nasdaq":
            ticker_news_futures = {
                pool.submit(_fetch_ticker_news_nasdaq, sym): sym
                for sym in watchlist_symbols
            }
            sec_futures = {
                pool.submit(_fetch_ticker_sec, sym): sym for sym in watchlist_symbols
            }

            for fut in as_completed(ticker_news_futures):
                try:
                    all_news.extend(fut.result())
                except Exception:
                    pass
            for fut in as_completed(sec_futures):
                try:
                    all_disclosures.extend(fut.result())
                except Exception:
                    pass

        elif market == "bist":
            # KAP toplu
            kap_future = pool.submit(_fetch_kap_disclosures, watchlist_symbols)
            try:
                all_disclosures.extend(kap_future.result(timeout=10))
            except Exception:
                pass

        try:
            all_news.extend(rss_future.result(timeout=20))
        except Exception:
            pass

    logger.info(
        f"[STAGE 0B] fetched: {len(all_news)} news items, "
        f"{len(all_disclosures)} corporate disclosures"
    )

    # 3. Separate per-ticker vs macro disclosures
    per_ticker: dict[str, list[CorporateDisclosure]] = {}
    macro_disclosures: list[CorporateDisclosure] = []

    for disc in all_disclosures:
        ticker_key = disc.ticker.upper().strip() if disc.ticker else ""
        if ticker_key:
            per_ticker.setdefault(ticker_key, []).append(disc)
        else:
            macro_disclosures.append(disc)

    # Store per-ticker KAP disclosures (rule-based translation, no LLM cost)
    ctx.kap_per_ticker = per_ticker
    if per_ticker:
        total_per = sum(len(v) for v in per_ticker.values())
        logger.info(
            f"[STAGE 0B] per-ticker KAP: {total_per} disclosures "
            f"across {len(per_ticker)} tickers (rule-based TR→EN)"
        )

    if not all_news and not macro_disclosures:
        logger.warning("[STAGE 0B] no news/macro disclosures, skipping translator")
        ctx.market_agenda = None
        ctx.log_stage("stage0b_agenda", time.perf_counter() - started)
        return ctx

    # 4. Claude Haiku ile MARKET AGENDA üret (only macro/market-wide content)
    try:
        translator = NewsTranslator()
        agenda = translator.translate(
            news=all_news,
            disclosures=macro_disclosures,
            watchlist=watchlist_symbols,
            use_cache=True,
        )
        ctx.market_agenda = agenda
        ctx.total_cost_usd += 0.005  # tahmini Haiku translator maliyeti
        logger.info(
            f"[STAGE 0B] MARKET AGENDA hazır: "
            f"{len(agenda.formatted_agenda.splitlines())} items, "
            f"sources={agenda.sources}"
        )
    except Exception as e:
        logger.warning(f"[STAGE 0B] translator hatası: {e}")
        ctx.market_agenda = None

    duration = time.perf_counter() - started
    ctx.log_stage("stage0b_agenda", duration)
    logger.info(f"[STAGE 0B] tamam ({duration:.2f}s)")
    return ctx
