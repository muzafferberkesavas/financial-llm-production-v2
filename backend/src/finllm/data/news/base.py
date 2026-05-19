"""News domain — NewsItem, MarketAgenda, NewsReader protocol.

Anthropic 3-tier untrusted isolation:
  Tier 1 (READER): NewsReader → NewsItem (schema-validated JSON, NO LLM)
  Tier 2 (TRANSLATOR): Claude Haiku → MarketAgenda (English summary)
  Tier 3 (ANALYST): Claude Opus deep — sees only MarketAgenda.formatted_agenda

Reader katmanı asla LLM'e ham HTML/XML feed göndermez. Strict regex/parsing
ile NewsItem'a dönüştürür. Bu prompt injection savunmasının temeli.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal, Protocol, runtime_checkable

# Whitelist: NewsItem field'larında izin verilen karakterler (untrusted'a karşı)
SAFE_TEXT_PATTERN = r"^[A-Za-z0-9 .,%$£€₺()_/:\-\&\'\"!?]*$"

NewsCategory = Literal[
    "MACRO",          # Fed, TCMB, CPI, GDP, FX
    "SECTOR",         # banking, energy, tech, retail
    "STOCK",          # company-specific (earnings, M&A, dividend)
    "GEOPOLITICAL",   # trade war, sanctions, conflicts
    "REGULATORY",     # SEC, KAP, SPK, FDA
    "GENERAL",        # uncategorized
]

NewsLanguage = Literal["tr", "en"]


@dataclass(slots=True)
class NewsItem:
    """Tek bir haber — untrusted kaynaktan sanitize edilerek üretildi.

    Reader'lar bu schema'ya uyan output döner; metin alanları regex cleanup'tan
    geçer (HTML/script tag, kontrol karakteri ele alınır).
    """

    title: str
    pub_date: datetime
    source: str                          # "BigPara", "SEC EDGAR", "Finnhub" vs.
    language: NewsLanguage               # "tr" | "en"
    category: NewsCategory = "GENERAL"
    description: str = ""
    url: str = ""
    ticker: str = ""                     # ilgili ticker (varsa)

    @property
    def age_hours(self) -> float:
        return (datetime.utcnow() - self.pub_date.replace(tzinfo=None)).total_seconds() / 3600

    @property
    def age_label(self) -> str:
        age = self.age_hours
        if age < 1:
            return f"{int(age * 60)}m ago"
        if age < 24:
            return f"{int(age)}h ago"
        return f"{int(age / 24)}d ago"


@dataclass(slots=True)
class CorporateDisclosure:
    """KAP / SEC resmi açıklaması — daha yüksek güvenilirlik tag.

    KAP: kap.org.tr'den çekilen şirket açıklamaları
    SEC: EDGAR 8-K (material events), 10-Q (quarterly), Form 4 (insider)
    """

    ticker: str
    publish_date: datetime
    title: str
    disclosure_type: str                 # "MATERIAL_EVENT" | "8-K" | "10-Q" | "Form 4" etc.
    priority: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"
    summary: str = ""
    url: str = ""
    source: str = ""                     # "KAP" | "SEC EDGAR"


@dataclass(slots=True)
class MarketAgenda:
    """Translator çıktısı — Stage 3'e gönderilen tek özet.

    Lib.zip'in `news_translation_service.dart` ile uyumlu format:
    1. [MACRO] Fed held rates at 4.25%-4.50% (neutral) [today]
    2. [STOCK:AAPL] Services revenue beat expectations +8% YoY (positive) [today]
    3. [SECTOR:BANKING] Major banks ... (negative) [yesterday]
    """

    formatted_agenda: str                # Numbered list (numbered_list[1-10])
    fetched_at: datetime = field(default_factory=datetime.utcnow)
    news_count: int = 0
    disclosure_count: int = 0
    sources: list[str] = field(default_factory=list)

    @property
    def is_stale(self, max_age_minutes: int = 60) -> bool:
        return (datetime.utcnow() - self.fetched_at).total_seconds() / 60 >= max_age_minutes

    @property
    def is_empty(self) -> bool:
        return not self.formatted_agenda.strip()


@runtime_checkable
class NewsReader(Protocol):
    """Untrusted external source → schema-validated NewsItem list.

    Implementer'lar SAFE_TEXT_PATTERN ile metni temizler, asla LLM'e ham
    feed göndermez.
    """

    name: str
    market: Literal["bist", "nasdaq", "global"]

    def fetch(
        self,
        ticker: str | None = None,
        max_age_hours: int = 24,
        limit: int = 30,
    ) -> list[NewsItem]:
        """Belirli ticker (varsa) için ya da genel piyasa haberi çek."""
        ...

    def is_available(self) -> bool:
        """Reader hazır mı (API key var mı, network OK mi)?"""
        ...


def cleanup_text(text: str | None, max_len: int = 500) -> str:
    """HTML tag, kontrol karakteri, fazla whitespace temizle. Max len cap."""
    import re

    if not text:
        return ""
    # HTML tags
    text = re.sub(r"<[^>]*>", "", text)
    # HTML entities (basit set)
    text = (
        text.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
        .replace("&nbsp;", " ")
    )
    # Control characters
    text = re.sub(r"[\x00-\x1f\x7f]+", " ", text)
    # Multiple whitespace
    text = re.sub(r"\s+", " ", text).strip()
    # Cap
    if len(text) > max_len:
        text = text[: max_len - 3] + "..."
    return text


__all__ = [
    "CorporateDisclosure",
    "MarketAgenda",
    "NewsCategory",
    "NewsItem",
    "NewsLanguage",
    "NewsReader",
    "SAFE_TEXT_PATTERN",
    "cleanup_text",
]
