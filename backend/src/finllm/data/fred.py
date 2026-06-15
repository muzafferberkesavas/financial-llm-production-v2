"""FRED (St. Louis Fed) macro reader — fills the [INFLATION][EMPLOYMENT][RATES]
slots the price-only assembler can't (Faz B.1 enrichment).

Free API. Crucially supports point-in-time queries (`as_of`) via FRED's
`observation_end`, so the same reader feeds both the live layer and a
look-ahead-safe historical backtest (Faz B.3).

Series:
  CPIAUCSL  CPI (all urban, SA, index) → YoY
  PCEPILFE  Core PCE price index → YoY
  UNRATE    Unemployment rate (%)
  PAYEMS    Nonfarm payrolls (thousands) → MoM change = NFP
  FEDFUNDS  Effective fed funds rate (%, monthly)
  DGS10/DGS2  10y / 2y treasury yields (%, daily)
"""
from __future__ import annotations

from datetime import date

import httpx

from finllm.config.settings import settings
from finllm.utils.logging import logger

_BASE = "https://api.stlouisfed.org/fred/series/observations"


def _obs(series_id: str, as_of: str | None = None, limit: int = 14) -> list[tuple[str, float]]:
    """Latest `limit` observations (newest first). Skips FRED's '.' (missing)."""
    key = settings.fred_api_key
    if not key:
        return []
    params = {
        "series_id": series_id,
        "api_key": key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": str(limit),
    }
    if as_of:
        params["observation_end"] = as_of
    try:
        r = httpx.get(_BASE, params=params, timeout=15.0)
        r.raise_for_status()
        out = []
        for o in r.json().get("observations", []):
            v = o.get("value", ".")
            if v not in (".", "", None):
                out.append((o["date"], float(v)))
        return out
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[FRED] {series_id} fetch failed: {e}")
        return []


def _yoy(obs: list[tuple[str, float]]) -> float | None:
    """Year-over-year % from a monthly index series (newest first, need 13 pts)."""
    if len(obs) < 13:
        return None
    return (obs[0][1] / obs[12][1] - 1) * 100


def is_available() -> bool:
    return bool(settings.fred_api_key)


def fred_macro_block(as_of: str | None = None) -> str | None:
    """Formatted [RATES]/[INFLATION]/[EMPLOYMENT] block, or None if no key.
    `as_of` (YYYY-MM-DD) makes it point-in-time for historical backtests."""
    if not is_available():
        return None

    cpi = _obs("CPIAUCSL", as_of, 14)
    pce = _obs("PCEPILFE", as_of, 14)
    unrate = _obs("UNRATE", as_of, 2)
    payems = _obs("PAYEMS", as_of, 2)
    fedfunds = _obs("FEDFUNDS", as_of, 2)
    dgs10 = _obs("DGS10", as_of, 5)
    dgs2 = _obs("DGS2", as_of, 5)

    rates = []
    if fedfunds:
        rates.append(f"Fed funds {fedfunds[0][1]:.2f}% (as of {fedfunds[0][0]})")
    if dgs10 and dgs2:
        spread = dgs10[0][1] - dgs2[0][1]
        shape = "inverted" if spread < 0 else "normal"
        rates.append(f"10Y {dgs10[0][1]:.2f}% / 2Y {dgs2[0][1]:.2f}% → 2s10s {spread:+.2f}% ({shape})")
    elif dgs10:
        rates.append(f"10Y {dgs10[0][1]:.2f}%")

    inflation = []
    cpi_yoy = _yoy(cpi)
    if cpi_yoy is not None:
        inflation.append(f"CPI {cpi_yoy:+.1f}% YoY (as of {cpi[0][0]})")
    pce_yoy = _yoy(pce)
    if pce_yoy is not None:
        inflation.append(f"Core PCE {pce_yoy:+.1f}% YoY (as of {pce[0][0]})")

    employment = []
    if unrate:
        trend = ""
        if len(unrate) >= 2:
            trend = " (rising)" if unrate[0][1] > unrate[1][1] else " (falling/flat)"
        employment.append(f"Unemployment {unrate[0][1]:.1f}%{trend} (as of {unrate[0][0]})")
    if len(payems) >= 2:
        nfp_change = (payems[0][1] - payems[1][1])  # thousands
        employment.append(f"NFP MoM {nfp_change:+,.0f}k (as of {payems[0][0]})")

    blocks = []
    if rates:
        blocks.append("[RATES — FRED]\n" + "\n".join(rates))
    if inflation:
        blocks.append("[INFLATION — FRED]\n" + "\n".join(inflation))
    if employment:
        blocks.append("[EMPLOYMENT — FRED]\n" + "\n".join(employment))
    return "\n\n".join(blocks) if blocks else None


__all__ = ["fred_macro_block", "is_available"]
