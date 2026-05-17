"""Haber çekme — Finnhub birincil, NewsAPI yedek."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from finllm.config.settings import settings
from finllm.utils.logging import logger


@dataclass
class NewsItem:
    symbol: str
    headline: str
    summary: str
    url: str
    source: str
    published_at: datetime

    @property
    def text(self) -> str:
        return f"{self.headline}. {self.summary}".strip()


class FinnhubClient:
    BASE = "https://finnhub.io/api/v1"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.finnhub_api_key
        if not self.api_key:
            raise RuntimeError("FINNHUB_API_KEY missing — set it in .env")
        self.client = httpx.Client(timeout=15.0)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8))
    def company_news(
        self,
        symbol: str,
        days_back: int = 7,
    ) -> list[NewsItem]:
        to_date = datetime.utcnow().date()
        from_date = to_date - timedelta(days=days_back)
        resp = self.client.get(
            f"{self.BASE}/company-news",
            params={
                "symbol": symbol,
                "from": from_date.isoformat(),
                "to": to_date.isoformat(),
                "token": self.api_key,
            },
        )
        resp.raise_for_status()
        items = []
        for raw in resp.json():
            try:
                items.append(
                    NewsItem(
                        symbol=symbol,
                        headline=raw.get("headline", ""),
                        summary=raw.get("summary", ""),
                        url=raw.get("url", ""),
                        source=raw.get("source", ""),
                        published_at=datetime.utcfromtimestamp(raw["datetime"]),
                    )
                )
            except (KeyError, ValueError, TypeError) as e:
                logger.debug(f"Bad news row skipped: {e}")
        return items


def fetch_news(symbol: str, days_back: int = 7) -> list[NewsItem]:
    client = FinnhubClient()
    items = client.company_news(symbol, days_back=days_back)
    logger.info(f"{symbol}: {len(items)} haber çekildi (son {days_back} gün)")
    return items
