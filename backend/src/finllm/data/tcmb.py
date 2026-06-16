"""TCMB EVDS — Turkish macro for the BIST leg (Faz E).

US macro appetites only partially transfer to BIST (the domestic-driven sectors —
banks, retail — follow TCMB policy rate, TRY, and Turkish CPI, not the Fed). EVDS
(Elektronik Veri Dağıtım Sistemi) is the Turkish central bank's free data API; this
reader pulls the policy rate, CPI YoY, and USD/TRY so the macro→sector layer can
reason about BIST with the right drivers.

Free API key required (register at evds2.tcmb.gov.tr → Profilim → API Anahtarı),
set TCMB_API_KEY in .env. Series codes are EVDS-specific and may need tuning once a
key is available; each is fetched independently and degrades to None on failure.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import httpx

from finllm.config.settings import settings
from finllm.utils.logging import logger

_BASE = "https://evds2.tcmb.gov.tr/service/evds"

# EVDS series codes (frequency in comment). Adjust if EVDS renames them.
SERIES = {
    "policy_rate": "TP.APIFON4",        # 1-week repo (policy) rate, %
    "cpi_index": "TP.FG.J0",            # CPI index (TÜFE), monthly → YoY computed
    "usdtry": "TP.DK.USD.A.YTL",        # USD buying rate, daily
}


def is_available() -> bool:
    return bool(settings.tcmb_api_key)


def _fetch(series: str, months: int = 18) -> list[tuple[str, float]]:
    key = settings.tcmb_api_key
    if not key:
        return []
    end = datetime.utcnow()
    start = end - timedelta(days=months * 31)
    params = {
        "series": series,
        "startDate": start.strftime("%d-%m-%Y"),
        "endDate": end.strftime("%d-%m-%Y"),
        "type": "json",
    }
    try:
        r = httpx.get(_BASE, params=params, headers={"key": key}, timeout=20)
        r.raise_for_status()
        col = series.replace(".", "_")
        out = []
        for row in r.json().get("items", []):
            v = row.get(col)
            if v not in (None, "", "null"):
                try:
                    out.append((row.get("Tarih", ""), float(v)))
                except ValueError:
                    pass
        return out
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[TCMB] {series} failed: {e}")
        return []


def tcmb_macro_block() -> str | None:
    """Formatted [TÜRK MAKRO — TCMB] block, or None if no key/data."""
    if not is_available():
        return None
    rate = _fetch(SERIES["policy_rate"], 6)
    cpi = _fetch(SERIES["cpi_index"], 18)
    usd = _fetch(SERIES["usdtry"], 3)

    lines = []
    if rate:
        lines.append(f"Politika faizi (1H repo): {rate[-1][1]:.2f}% (son: {rate[-1][0]})")
    if len(cpi) >= 13:
        yoy = (cpi[-1][1] / cpi[-13][1] - 1) * 100
        lines.append(f"TÜFE: {yoy:+.1f}% YoY (son: {cpi[-1][0]})")
    if usd:
        chg = ((usd[-1][1] / usd[0][1] - 1) * 100) if len(usd) > 1 and usd[0][1] else 0.0
        lines.append(f"USD/TRY: {usd[-1][1]:.2f} (3a {chg:+.1f}%)")
    return "[TÜRK MAKRO — TCMB]\n" + "\n".join(lines) if lines else None


__all__ = ["tcmb_macro_block", "is_available", "SERIES"]
