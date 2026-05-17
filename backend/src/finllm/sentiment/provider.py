"""Sentiment provider soyutlaması — lokal FinBERT veya uzak FinGPT'ye geçişi kolaylaştırır.

settings.sentiment_provider:
    "finbert" → lokal FinBERT (ProsusAI/finbert, Mac MPS)
    "fingpt"  → uzak FinGPT-Sentiment endpoint (AWS sunucu)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx

from finllm.config.settings import settings
from finllm.utils.logging import logger


@dataclass
class SentimentResult:
    text: str
    label: str               # positive / negative / neutral (veya FinGPT'nin daha çok sınıfı)
    score: float             # seçilen etiketin güveni
    polarity: float          # ∈ [-1, 1]


class SentimentProvider(Protocol):
    def score_batch(self, texts: list[str]) -> list[SentimentResult]: ...


class FinBERTProvider:
    """Lokal FinBERT (Mac MPS / CPU). Mevcut sentiment/finbert.py'yi sarar."""
    def score_batch(self, texts: list[str]) -> list[SentimentResult]:
        from finllm.sentiment.finbert import score_batch as fb_score
        return [
            SentimentResult(text=r.text, label=r.label, score=r.score, polarity=r.polarity)
            for r in fb_score(texts)
        ]


class FinGPTProvider:
    """Uzak FinGPT-Sentiment endpoint'ine HTTP çağrısı yapar.

    Beklenen endpoint kontratı:
        POST {FINGPT_ENDPOINT}/sentiment
        Body: {"texts": ["...", "..."]}
        Headers: Authorization: Bearer {FINGPT_API_KEY}
        Response: {"results": [{"label": str, "score": float, "polarity": float}, ...]}
    """
    def __init__(self) -> None:
        if not settings.fingpt_endpoint:
            raise RuntimeError("FINGPT_ENDPOINT .env'de tanımlı değil")
        self.url = settings.fingpt_endpoint.rstrip("/") + "/sentiment"
        self.headers = {"Content-Type": "application/json"}
        if settings.fingpt_api_key:
            self.headers["Authorization"] = f"Bearer {settings.fingpt_api_key}"

    def score_batch(self, texts: list[str]) -> list[SentimentResult]:
        if not texts:
            return []
        resp = httpx.post(self.url, headers=self.headers, json={"texts": texts}, timeout=60.0)
        resp.raise_for_status()
        data = resp.json()
        return [
            SentimentResult(
                text=texts[i],
                label=r["label"],
                score=float(r["score"]),
                polarity=float(r["polarity"]),
            )
            for i, r in enumerate(data["results"])
        ]


def get_provider() -> SentimentProvider:
    name = settings.sentiment_provider.lower()
    if name == "finbert":
        return FinBERTProvider()
    if name == "fingpt":
        logger.info(f"FinGPT sentiment endpoint: {settings.fingpt_endpoint}")
        return FinGPTProvider()
    raise ValueError(f"Bilinmeyen SENTIMENT_PROVIDER: {name}")


def aggregate_polarity(results: list[SentimentResult]) -> float:
    if not results:
        return 0.0
    weights = [r.score for r in results]
    weighted = sum(r.polarity * w for r, w in zip(results, weights))
    return weighted / sum(weights)
