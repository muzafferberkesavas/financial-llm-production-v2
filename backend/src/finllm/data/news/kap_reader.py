"""KAP reader — Borsa İstanbul resmi açıklamalar (Public Disclosure Platform).

KAP'ın yapısal JSON API'si yok; kap.org.tr/tr/api/disclosures public endpoint
mevcut ama undocumented + sık değişiyor. Bu Phase 2.2 implementasyonu:

1. Endpoint: https://www.kap.org.tr/tr/api/disclosures?subjectId=0&sequenceId=0
2. POST/GET hibrit — uygulamada GET deniyoruz, fail ise stub
3. Response: JSON list of disclosure objects
4. Stub fallback: KAP'ın home page'ini parse etmeye girmeyiz, Phase 3'te
   ya pykap kütüphanesi ya da resmi anlaşmalı erişim

Phase 2'de KAP'tan veri gelmezse → boş liste döner (Stage 3 hâlâ çalışır).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal

import httpx

from finllm.data.news.base import CorporateDisclosure, NewsItem, cleanup_text
from finllm.utils.logging import logger


_KAP_BASE = "https://www.kap.org.tr"
_KAP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; FinLLM/1.0)",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "tr,en;q=0.9",
}

# Yüksek-öncelikli açıklama türleri (KAP'ın "konuKodu" eşlemesi)
_HIGH_PRIORITY_TYPES = {
    "ozel_durum",          # Material event
    "finansal_rapor",      # Financial statement
    "kar_payi",             # Dividend
    "geri_alim",            # Share buyback
    "yk_karari",            # Board decision
    "birlesme_devralma",    # M&A
}


def _normalize_priority(disclosure_type: str) -> Literal["HIGH", "MEDIUM", "LOW"]:
    """KAP açıklama tipinden öncelik üret."""
    t = disclosure_type.lower()
    if any(k in t for k in ["özel", "ozel", "finansal", "kar payı", "kar payi", "geri al"]):
        return "HIGH"
    if any(k in t for k in ["genel kurul", "rating", "kredi", "sözleşme", "sozlesme"]):
        return "MEDIUM"
    return "LOW"


class KapReader:
    """KAP açıklamaları okur.

    Phase 3.5: KAP public REST API'si yok (Next.js page-only).
    Quick fail + fallback — pipeline'ı yavaşlatmasın.
    Phase 4+'ta Selenium/Playwright ile gerçek render-scraping yapılabilir.
    """

    market: Literal["bist"] = "bist"
    name = "kap"

    def __init__(self):
        self._client = httpx.Client(
            timeout=httpx.Timeout(connect=3.0, read=5.0, write=3.0, pool=5.0),
            headers=_KAP_HEADERS,
            follow_redirects=True,
        )
        self._available = True
        self._probe_done = False

    def is_available(self) -> bool:
        """Hızlı probe — yavaşlamamak için 1 kere check edilir."""
        if self._probe_done:
            return self._available
        self._probe_done = True
        try:
            resp = self._client.get(f"{_KAP_BASE}/tr", follow_redirects=True)
            self._available = resp.status_code < 500
        except Exception:
            self._available = False
        if not self._available:
            logger.debug("[KAP] unavailable (Phase 4'te Selenium scraper denenecek)")
        return self._available

    def fetch_disclosures(
        self,
        tickers: list[str] | None = None,
        max_age_hours: int = 24,
        limit: int = 20,
    ) -> list[CorporateDisclosure]:
        """KAP'tan son açıklamaları çek. Ticker listesi varsa onlarla filtre."""
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)

        # KAP'ın public undocumented endpoint'i:
        # https://www.kap.org.tr/tr/api/disclosures
        # Bu endpoint zaman zaman değişiyor — fail-safe yaz
        try:
            resp = self._client.get(f"{_KAP_BASE}/tr/api/disclosures")
            if resp.status_code != 200:
                logger.warning(f"[KAP] HTTP {resp.status_code} — KAP API erişilemez")
                self._available = False
                return []
            raw_list = resp.json()
            if not isinstance(raw_list, list):
                logger.warning(f"[KAP] beklenmeyen response tipi: {type(raw_list)}")
                return []
        except Exception as e:
            logger.warning(f"[KAP] API hatası (Phase 3'te resmi erişim): {e}")
            self._available = False
            return []

        out: list[CorporateDisclosure] = []
        ticker_set = {t.upper() for t in tickers} if tickers else None

        for raw in raw_list[: limit * 3]:  # eleme öncesi havuz
            try:
                disclosure_ticker = (raw.get("stockCode") or "").upper().strip()
                if ticker_set and disclosure_ticker not in ticker_set:
                    continue

                title = cleanup_text(raw.get("disclosureClass") or raw.get("subject", ""))
                if not title:
                    continue

                # Tarih parse
                date_str = raw.get("publishDate") or raw.get("kapPublishedDate")
                if not date_str:
                    continue
                try:
                    # KAP format: "2026-05-19 14:30:00" veya ISO
                    pub_date = datetime.fromisoformat(date_str.replace(" ", "T"))
                except ValueError:
                    continue

                if pub_date.replace(tzinfo=None) < cutoff:
                    continue

                disclosure_type = raw.get("disclosureClass", "")
                priority = _normalize_priority(disclosure_type)

                out.append(
                    CorporateDisclosure(
                        ticker=disclosure_ticker,
                        publish_date=pub_date.replace(tzinfo=None),
                        title=title,
                        disclosure_type=disclosure_type,
                        priority=priority,
                        summary=cleanup_text(raw.get("summary", ""), max_len=400),
                        url=(
                            f"{_KAP_BASE}/tr/Bildirim/"
                            f"{raw.get('disclosureIndex', '')}"
                            if raw.get("disclosureIndex")
                            else ""
                        ),
                        source="KAP",
                    )
                )
            except Exception as e:
                logger.debug(f"[KAP] disclosure parse hatası: {e}")

        out.sort(key=lambda d: d.publish_date, reverse=True)
        return out[:limit]

    def fetch(
        self,
        ticker: str | None = None,
        max_age_hours: int = 24,
        limit: int = 10,
    ) -> list[NewsItem]:
        """NewsReader protocol — disclosure → NewsItem."""
        tickers = [ticker] if ticker else None
        disclosures = self.fetch_disclosures(tickers=tickers, max_age_hours=max_age_hours, limit=limit)
        return [
            NewsItem(
                title=f"[KAP/{d.disclosure_type}] {d.title}",
                description=d.summary,
                pub_date=d.publish_date,
                source=d.source,
                language="tr",
                category="REGULATORY",
                url=d.url,
                ticker=d.ticker,
            )
            for d in disclosures
        ]
