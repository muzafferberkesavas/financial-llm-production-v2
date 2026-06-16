"""Stock-specific BIST news (Faz E).

BIST RSS headlines reference companies by NAME (Akbank, Türk Hava Yolları) not
ticker (AKBNK, THYAO), so ticker-symbol filtering misses everything. This matches
the universe's company name against the RSS feed to surface per-stock Turkish news
— the working path for BIST news (KAP has no stable public API).
"""
from __future__ import annotations

import re

from finllm.data.news.base import NewsItem
from finllm.data.news.rss_reader import RssReader

# Common Turkish suffixes to strip so "Akbank T.A.Ş." → key "Akbank".
_STOP = {"holding", "grubu", "anonim", "şirketi", "sanayi", "ticaret", "ve",
         "a.ş.", "t.a.ş.", "gyo", "yatırım", "hayat", "emeklilik"}


def _name_keys(name: str) -> list[str]:
    """Distinctive uppercase search keys from a company name."""
    if not name:
        return []
    words = re.split(r"\s+", name.strip())
    keys = [name.upper()]                       # full name
    sig = [w for w in words if w.lower() not in _STOP and len(w) > 2]
    if sig:
        keys.append(sig[0].upper())             # first distinctive word (Akbank, Aselsan)
        if len(sig) >= 2:
            keys.append(f"{sig[0]} {sig[1]}".upper())
    return list(dict.fromkeys(keys))


def _name_for(ticker: str) -> str | None:
    from finllm.markets.universes.bist_100 import BIST_100_TICKERS
    raw = ticker.replace(".IS", "").upper()
    for t in BIST_100_TICKERS:
        if t.symbol.upper() == raw:
            return t.name
    return None


def fetch_bist_stock_news(
    ticker: str, max_age_hours: int = 96, limit: int = 5, _feed: list[NewsItem] | None = None
) -> list[NewsItem]:
    """Recent Turkish news for one BIST stock, matched by company name + ticker."""
    name = _name_for(ticker)
    keys = [ticker.replace(".IS", "").upper(), *(_name_keys(name) if name else [])]
    feed = _feed if _feed is not None else RssReader(market="bist").fetch(max_age_hours=max_age_hours, limit=120)
    hits = [n for n in feed if any(k in n.title.upper() for k in keys)]
    return hits[:limit]


__all__ = ["fetch_bist_stock_news"]
