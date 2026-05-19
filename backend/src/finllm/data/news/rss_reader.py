"""RSS news reader — BIST (lib.zip 5 kaynak port) + NASDAQ ek kaynaklar.

Untrusted RSS feed → NewsItem listesi. xml ile parse, cleanup_text ile sanitize.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

import httpx
from defusedxml import ElementTree as DefusedET

from finllm.config.settings import settings
from finllm.data.news.base import NewsCategory, NewsItem, NewsLanguage, cleanup_text
from finllm.utils.logging import logger


@dataclass(frozen=True)
class _RssSource:
    name: str
    url: str
    language: NewsLanguage
    category: NewsCategory
    is_atom: bool = False
    market: Literal["bist", "nasdaq", "global"] = "global"


# Lib.zip port (BIST) + ek NASDAQ kaynakları
DEFAULT_SOURCES: list[_RssSource] = [
    # ---- BIST / TR ----
    _RssSource(
        name="BigPara",
        url="https://bigpara.hurriyet.com.tr/rss/",
        language="tr",
        category="STOCK",
        market="bist",
    ),
    _RssSource(
        name="Bloomberg HT",
        url="https://www.bloomberght.com/rss",
        language="tr",
        category="MACRO",
        market="bist",
    ),
    _RssSource(
        name="Investing.com Turkey",
        url="https://tr.investing.com/rss/news.rss",
        language="tr",
        category="MACRO",
        market="bist",
    ),
    _RssSource(
        name="ParaAnaliz",
        url="https://www.paraanaliz.com/feed/",
        language="tr",
        category="MACRO",
        market="bist",
    ),
    _RssSource(
        name="NTV Ekonomi",
        url="https://www.ntv.com.tr/ekonomi.rss",
        language="tr",
        category="MACRO",
        market="bist",
        is_atom=True,
    ),
    # ---- NASDAQ / US ----
    _RssSource(
        name="MarketWatch Top Stories",
        url="https://feeds.content.dowjones.io/public/rss/mw_topstories",
        language="en",
        category="MACRO",
        market="nasdaq",
    ),
    _RssSource(
        name="Seeking Alpha Market Currents",
        url="https://seekingalpha.com/market_currents.xml",
        language="en",
        category="STOCK",
        market="nasdaq",
    ),
    _RssSource(
        name="CNBC Top News",
        url="https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
        language="en",
        category="MACRO",
        market="nasdaq",
    ),
]


# ---- Date parsing helpers ----
_MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


def _parse_rfc822(s: str) -> datetime | None:
    """RFC 822: 'Mon, 19 May 2026 09:30:00 +0300'."""
    if not s:
        return None
    try:
        # Strip day-of-week prefix if exists
        s = s.split(",", 1)[1].strip() if "," in s else s.strip()
        parts = s.split()
        if len(parts) < 4:
            return None
        day = int(parts[0])
        month = _MONTHS.get(parts[1])
        year = int(parts[2])
        if not month:
            return None
        time_parts = parts[3].split(":")
        h = int(time_parts[0])
        m = int(time_parts[1]) if len(time_parts) > 1 else 0
        sec = int(time_parts[2]) if len(time_parts) > 2 else 0
        return datetime(year, month, day, h, m, sec)
    except (ValueError, KeyError, IndexError):
        return None


def _parse_date(s: str | None) -> datetime | None:
    """ISO 8601 ya da RFC 822 dene."""
    if not s:
        return None
    s = s.strip()
    # ISO 8601 (Atom)
    try:
        # Remove timezone for naive comparison
        cleaned = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        return dt.replace(tzinfo=None)
    except (ValueError, AttributeError):
        pass
    return _parse_rfc822(s)


class RssReader:
    """RSS 2.0 + Atom parser, untrusted → NewsItem list."""

    market: Literal["bist", "nasdaq", "global"]

    def __init__(
        self,
        market: Literal["bist", "nasdaq", "global"] = "global",
        sources: list[_RssSource] | None = None,
        client: httpx.Client | None = None,
    ):
        self.market = market
        self.name = f"rss-{market}"
        # Sources: market'a göre filtrele (verilmedi ise default)
        if sources is None:
            sources = [s for s in DEFAULT_SOURCES if s.market in (market, "global")]
        self.sources = sources
        self._client = client or httpx.Client(
            timeout=httpx.Timeout(connect=10.0, read=15.0, write=10.0, pool=15.0),
            headers={"User-Agent": "Mozilla/5.0 (compatible; FinLLM/1.0)"},
            follow_redirects=True,
        )

    def is_available(self) -> bool:
        return bool(self.sources)

    def fetch(
        self,
        ticker: str | None = None,
        max_age_hours: int = 24,
        limit: int = 30,
    ) -> list[NewsItem]:
        """Tüm kaynaklardan haber çek, son N saatle sınırla, sırala."""
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        items: list[NewsItem] = []

        for source in self.sources:
            try:
                xml_text = self._client.get(source.url).text
                parsed = self._parse_feed(xml_text, source)
                items.extend(p for p in parsed if p.pub_date.replace(tzinfo=None) >= cutoff)
            except Exception as e:
                logger.warning(f"[RSS] {source.name} ({source.url}): {e}")

        items.sort(key=lambda n: n.pub_date, reverse=True)

        # Ticker filtre (varsa) — basit substring match (ileride NER iyileştirilebilir)
        if ticker:
            t_upper = ticker.upper()
            items = [
                n for n in items
                if t_upper in n.title.upper() or t_upper in (n.description or "").upper()
            ]

        return items[:limit]

    # ---- internal parsing ----
    def _parse_feed(self, xml_text: str, source: _RssSource) -> list[NewsItem]:
        try:
            # defusedxml ile XXE saldırılarına karşı güvenli parse
            root = DefusedET.fromstring(xml_text)
        except Exception as e:
            logger.warning(f"[RSS] {source.name} parse fail: {e}")
            return []

        if source.is_atom:
            return self._parse_atom(root, source)
        return self._parse_rss2(root, source)

    def _parse_rss2(self, root, source: _RssSource) -> list[NewsItem]:
        items: list[NewsItem] = []
        # RSS 2.0: rss/channel/item
        for item in root.iter("item"):
            title_el = item.find("title")
            if title_el is None or not title_el.text:
                continue
            title = cleanup_text(title_el.text, max_len=300)
            if not title:
                continue

            desc_el = item.find("description")
            desc = cleanup_text(desc_el.text if desc_el is not None else "", max_len=500)

            link_el = item.find("link")
            url = (link_el.text or "").strip() if link_el is not None else ""

            pubdate_el = item.find("pubDate")
            pub_date = _parse_date(pubdate_el.text if pubdate_el is not None else None) or datetime.utcnow()

            items.append(
                NewsItem(
                    title=title,
                    description=desc,
                    pub_date=pub_date,
                    source=source.name,
                    language=source.language,
                    category=source.category,
                    url=url,
                )
            )
        return items

    def _parse_atom(self, root, source: _RssSource) -> list[NewsItem]:
        items: list[NewsItem] = []
        # Atom: feed/entry with namespace
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        # Some feeds don't declare namespace consistently — try both
        entries = root.findall(".//atom:entry", ns) or [
            e for e in root.iter() if e.tag.endswith("entry")
        ]
        for entry in entries:
            title_el = entry.find("atom:title", ns) or next(
                (e for e in entry if e.tag.endswith("title")), None
            )
            if title_el is None or not (title_el.text or "").strip():
                continue
            title = cleanup_text(title_el.text, max_len=300)
            if not title:
                continue

            summary_el = entry.find("atom:summary", ns) or next(
                (e for e in entry if e.tag.endswith("summary") or e.tag.endswith("content")), None
            )
            desc = cleanup_text(
                summary_el.text if summary_el is not None else "", max_len=500
            )

            link_el = entry.find("atom:link", ns) or next(
                (e for e in entry if e.tag.endswith("link")), None
            )
            url = ""
            if link_el is not None:
                url = link_el.attrib.get("href") or (link_el.text or "").strip()

            date_el = entry.find("atom:published", ns) or entry.find("atom:updated", ns)
            if date_el is None:
                date_el = next(
                    (e for e in entry if e.tag.endswith("published") or e.tag.endswith("updated")),
                    None,
                )
            pub_date = (
                _parse_date(date_el.text if date_el is not None else None)
                or datetime.utcnow()
            )

            items.append(
                NewsItem(
                    title=title,
                    description=desc,
                    pub_date=pub_date,
                    source=source.name,
                    language=source.language,
                    category=source.category,
                    url=url,
                )
            )
        return items
