"""Finnhub reader — NASDAQ company news + general market.

Wraps the existing FinnhubClient (legacy) with NewsItem schema.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal

from finllm.config.settings import settings
from finllm.data.news._legacy_finnhub import FinnhubClient
from finllm.data.news.base import NewsItem, cleanup_text
from finllm.utils.logging import logger


class FinnhubReader:
    """NASDAQ ticker bazlı haber + market-wide news."""

    market: Literal["nasdaq"] = "nasdaq"
    name = "finnhub"

    def __init__(self):
        if settings.finnhub_api_key:
            try:
                self._client = FinnhubClient(api_key=settings.finnhub_api_key)
            except Exception as e:
                logger.warning(f"[FINNHUB] init failed: {e}")
                self._client = None
        else:
            self._client = None

    def is_available(self) -> bool:
        return self._client is not None

    def fetch(
        self,
        ticker: str | None = None,
        max_age_hours: int = 24,
        limit: int = 30,
    ) -> list[NewsItem]:
        if not self.is_available():
            return []
        if not ticker:
            # Finnhub'ın general market news endpoint'i ileride eklenir
            return []

        days_back = max(1, (max_age_hours + 23) // 24)
        try:
            legacy_items = self._client.company_news(ticker, days_back=days_back)
        except Exception as e:
            logger.warning(f"[FINNHUB] {ticker} hatası: {e}")
            return []

        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        items: list[NewsItem] = []

        for li in legacy_items:
            if li.published_at < cutoff:
                continue
            title = cleanup_text(li.headline, max_len=300)
            desc = cleanup_text(li.summary, max_len=500)
            if not title:
                continue
            items.append(
                NewsItem(
                    title=title,
                    description=desc,
                    pub_date=li.published_at,
                    source=f"Finnhub({li.source})" if li.source else "Finnhub",
                    language="en",
                    category="STOCK",
                    url=li.url,
                    ticker=ticker.upper(),
                )
            )

        items.sort(key=lambda n: n.pub_date, reverse=True)
        return items[:limit]
