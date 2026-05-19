"""SEC EDGAR reader — 8-K (material events), 10-Q (quarterly) filings.

Public Atom feed:
    https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=XXX
        &type=8-K&dateb=&owner=include&count=10&output=atom

Hız sınırı: SEC 10 req/sec limit — User-Agent zorunlu (kurum + email).

Ticker → CIK eşlemesi için company_tickers.json kullanıyoruz:
    https://www.sec.gov/files/company_tickers.json  (~10K mapping)
"""
from __future__ import annotations

from datetime import datetime, timedelta
from functools import lru_cache
from typing import Literal

import httpx
from defusedxml import ElementTree as DefusedET

from finllm.data.news.base import CorporateDisclosure, NewsItem, cleanup_text
from finllm.utils.logging import logger


_SEC_HEADERS = {
    "User-Agent": "FinLLM Research savasmuzafferberke@gmail.com",
    "Accept": "application/json",
}

_CIK_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
_EDGAR_URL = "https://www.sec.gov/cgi-bin/browse-edgar"


@lru_cache(maxsize=1)
def _load_cik_map(client: httpx.Client | None = None) -> dict[str, str]:
    """Ticker → CIK (zero-padded 10 digit) eşlemesi. lru_cached."""
    try:
        c = client or httpx.Client(timeout=15.0, headers=_SEC_HEADERS)
        resp = c.get(_CIK_MAP_URL)
        resp.raise_for_status()
        data = resp.json()
        # {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}, ...}
        out: dict[str, str] = {}
        for entry in data.values():
            ticker = entry.get("ticker", "").upper()
            cik = entry.get("cik_str")
            if ticker and cik is not None:
                out[ticker] = f"{int(cik):010d}"
        return out
    except Exception as e:
        logger.warning(f"[SEC] CIK map yüklenemedi: {e}")
        return {}


class SecEdgarReader:
    """SEC EDGAR Atom feed → CorporateDisclosure list.

    8-K = material event (M&A, executive change, earnings result, etc.)
    10-Q = quarterly report
    """

    market: Literal["nasdaq"] = "nasdaq"
    name = "sec-edgar"

    def __init__(self, filing_types: list[str] | None = None):
        self.filing_types = filing_types or ["8-K", "10-Q"]
        self._client = httpx.Client(timeout=15.0, headers=_SEC_HEADERS, follow_redirects=True)

    def is_available(self) -> bool:
        return bool(_load_cik_map(self._client))

    def _fetch_filings(self, cik: str, filing_type: str, count: int = 10) -> list[dict]:
        """Atom feed'i çek + parse → list of {title, date, url}."""
        try:
            resp = self._client.get(
                _EDGAR_URL,
                params={
                    "action": "getcompany",
                    "CIK": cik,
                    "type": filing_type,
                    "dateb": "",
                    "owner": "include",
                    "count": str(count),
                    "output": "atom",
                },
            )
            resp.raise_for_status()
            root = DefusedET.fromstring(resp.text)
        except Exception as e:
            logger.warning(f"[SEC] CIK={cik} {filing_type} fetch fail: {e}")
            return []

        # Atom feed: namespace-agnostic iteration (tag.split('}')[-1] gives local name).
        # SEC root has xmlns="http://www.w3.org/2005/Atom" so children are namespaced.
        entries = [e for e in root.iter() if e.tag.split("}")[-1] == "entry"]

        out = []
        for entry in entries:
            title_text = updated_text = link_url = None

            for child in entry:
                local = child.tag.split("}")[-1]
                if local == "title" and not title_text:
                    title_text = (child.text or "").strip()
                elif local == "updated" and not updated_text:
                    updated_text = (child.text or "").strip()
                elif local == "link" and not link_url:
                    link_url = child.attrib.get("href") or (child.text or "")

            if not title_text or not updated_text:
                continue

            try:
                # Format: 2026-04-30T16:30:41-04:00
                date = datetime.fromisoformat(updated_text).replace(tzinfo=None)
            except (ValueError, AttributeError):
                continue

            out.append(
                {
                    "title": cleanup_text(title_text, max_len=200),
                    "date": date,
                    "url": link_url or "",
                    "type": filing_type,
                }
            )
        return out

    def fetch_disclosures(
        self,
        ticker: str,
        max_age_hours: int = 24,
        limit: int = 10,
    ) -> list[CorporateDisclosure]:
        """8-K + 10-Q filings döner. CorporateDisclosure schema."""
        cik_map = _load_cik_map(self._client)
        cik = cik_map.get(ticker.upper())
        if not cik:
            logger.debug(f"[SEC] {ticker} CIK bulunamadı")
            return []

        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        all_filings: list[CorporateDisclosure] = []

        for filing_type in self.filing_types:
            raws = self._fetch_filings(cik, filing_type, count=5)
            for raw in raws:
                if raw["date"] < cutoff:
                    continue
                priority = "HIGH" if filing_type == "8-K" else "MEDIUM"
                all_filings.append(
                    CorporateDisclosure(
                        ticker=ticker.upper(),
                        publish_date=raw["date"],
                        title=raw["title"],
                        disclosure_type=filing_type,
                        priority=priority,
                        url=raw["url"],
                        source="SEC EDGAR",
                    )
                )

        all_filings.sort(key=lambda d: d.publish_date, reverse=True)
        return all_filings[:limit]

    def fetch(
        self,
        ticker: str | None = None,
        max_age_hours: int = 24,
        limit: int = 10,
    ) -> list[NewsItem]:
        """NewsReader protocol implementasyonu — disclosures'ı NewsItem'a dönüştür."""
        if not ticker:
            return []
        disclosures = self.fetch_disclosures(ticker, max_age_hours, limit)
        return [
            NewsItem(
                title=f"[{d.disclosure_type}] {d.title}",
                description=d.summary,
                pub_date=d.publish_date,
                source=d.source,
                language="en",
                category="REGULATORY",
                url=d.url,
                ticker=d.ticker,
            )
            for d in disclosures
        ]
