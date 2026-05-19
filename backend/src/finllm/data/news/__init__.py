"""News module — untrusted external sources → schema-validated NewsItem.

Phase 2.2: 4 reader (RSS, Finnhub, SEC, KAP) + translator (Claude Haiku → English agenda).

Backward-compat: signals/generator.py'nin `from finllm.data.news import fetch_news`
import'u çalışmaya devam ediyor (_legacy_finnhub.py modülü).
"""
from finllm.data.news._legacy_finnhub import (
    FinnhubClient,
    NewsItem as LegacyNewsItem,
    fetch_news,
)
from finllm.data.news.base import (
    CorporateDisclosure,
    MarketAgenda,
    NewsCategory,
    NewsItem,
    NewsLanguage,
    NewsReader,
    cleanup_text,
)
from finllm.data.news.finnhub_reader import FinnhubReader
from finllm.data.news.kap_reader import KapReader
from finllm.data.news.rss_reader import DEFAULT_SOURCES, RssReader
from finllm.data.news.sec_reader import SecEdgarReader
from finllm.data.news.translator import NewsTranslator

__all__ = [
    "CorporateDisclosure",
    "DEFAULT_SOURCES",
    "FinnhubClient",
    "FinnhubReader",
    "KapReader",
    "LegacyNewsItem",
    "MarketAgenda",
    "NewsCategory",
    "NewsItem",
    "NewsLanguage",
    "NewsReader",
    "NewsTranslator",
    "RssReader",
    "SecEdgarReader",
    "cleanup_text",
    "fetch_news",
]
