"""NasdaqAdapter — NYSE/NASDAQ ABD piyasası için MarketAdapter.

Özellikler:
- Raw ticker (suffix yok)
- T+2 settlement (2024'te SEC T+1'e indirdi — TRACK!)
- USD bazlı
- 09:30-16:00 ET (America/New_York)
- Robinhood/IBKR Lite: komisyonsuz
- Polygon: SEC EDGAR + Finnhub haberi (Phase 2)
"""
from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

import pandas as pd

from finllm.data.prices import fetch_prices as yahoo_fetch
from finllm.markets.base import (
    FilterThresholds,
    FundamentalSnapshot,
    MarketAdapter,
    Ticker,
    TransactionCostModel,
)
from finllm.markets.universes import NASDAQ_ALL
from finllm.utils.logging import logger


class NasdaqAdapter(MarketAdapter):
    """ABD NYSE/NASDAQ adapter — USD bazlı, raw ticker, T+1 (2024'ten beri)."""

    name = "nasdaq"
    currency = "USD"
    timezone = ZoneInfo("America/New_York")

    # NYSE/NASDAQ regular session
    open_time = time(9, 30)
    close_time = time(16, 0)
    settlement_days = 1  # T+1 (SEC kuralı Mayıs 2024'ten itibaren)

    benchmark_symbol = "SPY"

    # Kullanıcının manuel TradingView taraması — birebir port
    thresholds = FilterThresholds(
        min_price=3.0,                      # $3 minimum (penny stock'ları ele)
        min_market_cap=300_000_000,          # $300M (kurumsal flow alanı)
        min_avg_volume_10d=500_000,          # 500K shares/gün
        min_daily_dollar_volume=1_000_000,   # $1M günlük likidite
        min_adr_pct=2.0,
        require_close_above_ema21=True,
        require_close_above_ema50=True,
        require_green_day=True,
    )

    # IBKR Lite / Robinhood komisyonsuz; spread + slippage kalıyor
    transaction_cost = TransactionCostModel(
        commission_per_share=0.0,
        commission_pct=0.0,
        tax_pct=0.0,                         # US tax kullanıcı tarafında (1099-B)
        slippage_atr_mult=0.05,
        half_spread_pct=0.025,               # Mega-cap'te dar (~5bps spread)
    )

    def get_universe(self) -> list[Ticker]:
        return NASDAQ_ALL

    def format_yahoo_symbol(self, ticker: Ticker) -> str:
        """NASDAQ ticker'ları Yahoo'da raw; sadece Berkshire vs. 'BRK-B' formatı korunur."""
        return ticker.symbol

    def fetch_prices(
        self,
        ticker: Ticker,
        start: str | datetime | None = None,
        end: str | datetime | None = None,
        interval: str = "1d",
    ) -> pd.DataFrame:
        yahoo_symbol = self.format_yahoo_symbol(ticker)
        return yahoo_fetch(yahoo_symbol, start=start, end=end, interval=interval)

    def fetch_fundamentals(self, ticker: Ticker) -> FundamentalSnapshot | None:
        """Phase 3.1: yfinance.info kapsamlı (20+ field) + parquet cache."""
        from finllm.data.fundamentals import fetch_fundamentals as _ff

        try:
            return _ff(ticker, self.format_yahoo_symbol(ticker), use_cache=True)
        except Exception as e:
            logger.warning(f"[NASDAQ] {ticker} fundamentals hatası: {e}")
            return None

    def fetch_news(self, ticker: Ticker | None = None, hours: int = 24) -> list[dict]:
        """Finnhub (company news) + SEC EDGAR (8-K, 10-Q) + RSS NASDAQ market news.

        Returns list of dicts compatible with old IngestedData.news; Stage 0
        ayrıca Phase 2.2'de NewsItem objesi ile çalışabiliyor. Geriye uyumluluk
        için bu metod dict döner — `RawNewsBundle` ile birlikte fetch_news_bundle
        çağrılırsa structured objeler alınır.
        """
        from finllm.data.news import FinnhubReader, RssReader, SecEdgarReader

        all_news = []
        # Finnhub: company-specific
        if ticker:
            try:
                fn = FinnhubReader()
                if fn.is_available():
                    items = fn.fetch(ticker=ticker.symbol, max_age_hours=hours, limit=10)
                    all_news.extend(
                        {
                            "title": n.title,
                            "description": n.description,
                            "pub_date": n.pub_date.isoformat(),
                            "source": n.source,
                            "category": n.category,
                            "ticker": n.ticker,
                            "url": n.url,
                        }
                        for n in items
                    )
            except Exception as e:
                logger.warning(f"[NASDAQ] Finnhub {ticker}: {e}")

        # SEC EDGAR: ticker-specific filings (60g geri)
        if ticker:
            try:
                sec = SecEdgarReader()
                items = sec.fetch(ticker=ticker.symbol, max_age_hours=24 * 60, limit=5)
                all_news.extend(
                    {
                        "title": n.title,
                        "description": n.description,
                        "pub_date": n.pub_date.isoformat(),
                        "source": n.source,
                        "category": n.category,
                        "ticker": n.ticker,
                        "url": n.url,
                    }
                    for n in items
                )
            except Exception as e:
                logger.warning(f"[NASDAQ] SEC {ticker}: {e}")

        # RSS: ticker yoksa market-wide news
        if not ticker:
            try:
                rss = RssReader(market="nasdaq")
                items = rss.fetch(max_age_hours=hours, limit=15)
                all_news.extend(
                    {
                        "title": n.title,
                        "description": n.description,
                        "pub_date": n.pub_date.isoformat(),
                        "source": n.source,
                        "category": n.category,
                        "ticker": n.ticker,
                        "url": n.url,
                    }
                    for n in items
                )
            except Exception as e:
                logger.warning(f"[NASDAQ] RSS: {e}")

        return all_news

    def is_market_open(self, dt: datetime | None = None) -> bool:
        now = (dt or datetime.now(tz=self.timezone)).astimezone(self.timezone)
        if now.weekday() >= 5:
            return False
        # TODO: NYSE holiday calendar (pandas_market_calendars) Phase 2
        t = now.time()
        return self.open_time <= t <= self.close_time

    def is_commodity(self, ticker: Ticker) -> bool:
        # NASDAQ tarafında doğrudan emtia yok — ETF'ler (GLD, SLV) hisse gibi işlenir
        return False

    def convert_commodity_price(
        self, raw_price: float, currency_rate: float | None = None
    ) -> float:
        # NASDAQ zaten USD — no-op
        return raw_price
