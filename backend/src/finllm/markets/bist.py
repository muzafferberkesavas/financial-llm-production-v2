"""BistAdapter — BIST-100 + Altın/Gümüş için MarketAdapter implementasyonu.

Özellikler:
- .IS suffix Yahoo için
- T+1 settlement
- USD/oz emtia → TRY/gram dönüşümü (USDTRY paritesi ile)
- BIST trading hours: 09:50-18:10 Europe/Istanbul
- Komisyon ~0.15% + BSMV 5% (broker fee'nin %5'i)
- KAP haber kaynağı (Phase 2'de implement edilecek, şu an stub)
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
from finllm.markets.universes import (
    BIST_ALL,
    BIST_FX_TICKER,
    TROY_OUNCE_TO_GRAM,
)
from finllm.utils.logging import logger


class BistAdapter(MarketAdapter):
    """Borsa İstanbul adapter — TL bazlı, .IS suffix'li, T+1 settlement."""

    name = "bist"
    currency = "TRY"
    timezone = ZoneInfo("Europe/Istanbul")

    # BIST seans: 09:50-18:10 (öğle arası genişledi 2021'den beri)
    open_time = time(9, 50)
    close_time = time(18, 10)
    settlement_days = 1  # T+1

    benchmark_symbol = "XU100.IS"

    # Eşikler — lib.zip + memory/trading_strategy.md uyumlu
    thresholds = FilterThresholds(
        min_price=5.0,                     # 5 TL minimum (penny stock'ları ele)
        min_market_cap=1_000_000_000,       # 1 milyar TRY (BIST mid-cap ve üstü)
        min_avg_volume_10d=100_000,         # 100K shares/gün
        min_daily_dollar_volume=10_000_000, # 10M TRY günlük likidite
        min_adr_pct=2.0,                    # Average Daily Range >= 2%
        require_close_above_ema21=True,
        require_close_above_ema50=True,
        require_green_day=True,
    )

    transaction_cost = TransactionCostModel(
        commission_per_share=0.0,          # BIST percentage-based
        commission_pct=0.00075,             # 0.075% broker (Garanti, Yapı Kredi ortalaması)
        tax_pct=0.00005,                    # BSMV ~0.005% (komisyonun %5'i, fiyatın değil)
        slippage_atr_mult=0.05,
        half_spread_pct=0.05,               # BIST orta-büyük cap'lerde dar spread
    )

    def get_universe(self) -> list[Ticker]:
        return BIST_ALL

    def format_yahoo_symbol(self, ticker: Ticker) -> str:
        """BIST hisseleri için .IS suffix; emtia için raw."""
        if ticker.is_commodity:
            return ticker.symbol  # GC=F, SI=F → Yahoo raw
        if "." in ticker.symbol or "=" in ticker.symbol:
            return ticker.symbol  # Zaten formatlanmış
        return f"{ticker.symbol}.IS"

    def fetch_prices(
        self,
        ticker: Ticker,
        start: str | datetime | None = None,
        end: str | datetime | None = None,
        interval: str = "1d",
    ) -> pd.DataFrame:
        """OHLCV fetch + emtia için TRY/gram dönüşümü."""
        yahoo_symbol = self.format_yahoo_symbol(ticker)
        prices = yahoo_fetch(yahoo_symbol, start=start, end=end, interval=interval)

        if prices.empty:
            logger.warning(f"[BIST] {ticker} için fiyat alınamadı")
            return prices

        # Emtia ise USD/oz → TRY/gram çevir
        if ticker.is_commodity:
            prices = self._convert_commodity_to_try_gram(prices, start=start, end=end)

        return prices

    def _convert_commodity_to_try_gram(
        self, usd_prices: pd.DataFrame, start, end
    ) -> pd.DataFrame:
        """USD/ons fiyatı TRY/gram'a çevir, day-by-day USDTRY ile.

        Niye day-by-day: ons/USD ile USDTRY paralel değişir; tek bir kurla
        çarpmak son 6 ay TL devalüasyonunda yanlış backtest verir.
        """
        try:
            usdtry = yahoo_fetch(BIST_FX_TICKER, start=start, end=end, interval="1d")
        except Exception as e:
            logger.warning(f"[BIST] USDTRY alınamadı, USD fiyat döndürülüyor: {e}")
            return usd_prices

        if usdtry.empty:
            return usd_prices

        # Tarihe göre eşle, eksik günler son kuru kullansın
        usdtry_close = usdtry["close"].reindex(usd_prices.index, method="ffill")
        factor = usdtry_close / TROY_OUNCE_TO_GRAM

        out = usd_prices.copy()
        for col in ("open", "high", "low", "close"):
            if col in out.columns:
                out[col] = out[col] * factor
        # volume kalsın (ons cinsinden, semantic olarak doğru)
        return out

    def fetch_fundamentals(self, ticker: Ticker) -> FundamentalSnapshot | None:
        """BIST fundamentals — Phase 3.1: yfinance.info (BIST için kısıtlı veri seti).

        BIST hisselerinde yfinance bazı alanları (PEG, growth) döndürmüyor.
        Phase 3.5'te KAP/İşYatırım scraper ile zenginleştirilecek.
        """
        if ticker.is_commodity:
            return FundamentalSnapshot(ticker=ticker)

        from finllm.data.fundamentals import fetch_fundamentals as _ff

        try:
            return _ff(ticker, self.format_yahoo_symbol(ticker), use_cache=True)
        except Exception as e:
            logger.warning(f"[BIST] {ticker} fundamentals hatası: {e}")
            return None

    def fetch_news(self, ticker: Ticker | None = None, hours: int = 24) -> list[dict]:
        """KAP (resmi açıklamalar) + RSS (5 BIST kaynak).

        KAP Phase 2'de timeout veriyor olabilir — graceful fail.
        """
        from finllm.data.news import KapReader, RssReader

        all_news: list[dict] = []

        # KAP — ticker-specific veya genel
        try:
            kap = KapReader()
            if kap.is_available():
                items = kap.fetch(
                    ticker=ticker.symbol if ticker else None,
                    max_age_hours=hours,
                    limit=10,
                )
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
            logger.warning(f"[BIST] KAP: {e}")

        # RSS — ticker yoksa market-wide
        if not ticker:
            try:
                rss = RssReader(market="bist")
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
                logger.warning(f"[BIST] RSS: {e}")

        return all_news

    def is_market_open(self, dt: datetime | None = None) -> bool:
        now = (dt or datetime.now(tz=self.timezone)).astimezone(self.timezone)
        # Hafta sonu kapalı
        if now.weekday() >= 5:
            return False
        # Saat aralığı
        t = now.time()
        return self.open_time <= t <= self.close_time

    def is_commodity(self, ticker: Ticker) -> bool:
        return ticker.is_commodity

    def convert_commodity_price(
        self, raw_price: float, currency_rate: float | None = None
    ) -> float:
        """USD/ons → TRY/gram. Kur verilmezse 1.0 (test için).

        Production'da fetch_prices içindeki day-by-day çevirim kullanılır;
        bu metot tek-fiyat point-in-time çevirimi için.
        """
        rate = currency_rate or 1.0
        return raw_price * rate / TROY_OUNCE_TO_GRAM
