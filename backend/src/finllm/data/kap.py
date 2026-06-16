"""KAP (Kamuyu Aydınlatma Platformu) — official BIST disclosures + financials.

KAP has no stable REST API; the maintained `pykap` library scrapes it. This wraps
pykap to surface per-stock OFFICIAL disclosures (material events, dividends, board
decisions) and the list of filed financial-report periods — the authoritative
Turkish source the user wanted. Day-cached per ticker (scraping is slow) and
degrades to [] on any failure so the panel never blocks on KAP.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from finllm.utils.logging import logger

_CACHE = Path("backend/data/cache/kap")
# Disclosure categories worth surfacing as 'news' (KAP type codes via pykap).
# KDP=özel durum, DEG=değişiklik, UNV=uyarı, FAR=finansal rapor, SYI=sermaye/yatırım.
_NEWS_TYPES = ("KDP", "DEG", "UNV", "FAR", "SYI")


@dataclass(slots=True)
class KapInfo:
    ticker: str
    disclosures: list[str] = field(default_factory=list)   # recent disclosure titles
    financial_periods: list[str] = field(default_factory=list)  # filed report periods

    def as_dict(self) -> dict:
        return {"ticker": self.ticker, "disclosures": self.disclosures,
                "financial_periods": self.financial_periods}


def _cache_path(ticker: str) -> Path:
    return _CACHE / f"{ticker}_{datetime.utcnow():%Y%m%d}.json"


def fetch_kap(ticker: str, use_cache: bool = True, max_disclosures: int = 8) -> KapInfo:
    """Official KAP disclosures + financial-report periods for one BIST stock."""
    raw = ticker.replace(".IS", "").upper()
    cache = _cache_path(raw)
    if use_cache and cache.exists():
        try:
            d = json.loads(cache.read_text())
            return KapInfo(raw, d.get("disclosures", []), d.get("financial_periods", []))
        except Exception:  # noqa: BLE001
            pass

    info = KapInfo(ticker=raw)
    try:
        import pykap

        c = pykap.BISTCompany(raw)
        seen: set[str] = set()
        for dtype in _NEWS_TYPES:
            try:
                for d in (c.get_disclosures(dtype) or []):
                    title = (d.get("title") or "").strip()
                    if title and title not in seen:
                        seen.add(title)
                        info.disclosures.append(title)
            except Exception:  # noqa: BLE001
                continue
            if len(info.disclosures) >= max_disclosures:
                break
        info.disclosures = info.disclosures[:max_disclosures]
        try:
            fr = c.get_financial_reports()
            if isinstance(fr, dict):
                info.financial_periods = list(fr.keys())
        except Exception:  # noqa: BLE001
            pass
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[KAP] {raw} failed: {e}")
        return info

    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(info.as_dict(), ensure_ascii=False))
    except Exception:  # noqa: BLE001
        pass
    return info


__all__ = ["KapInfo", "fetch_kap"]
