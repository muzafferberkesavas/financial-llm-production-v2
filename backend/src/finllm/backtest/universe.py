"""Symbol universes for backtesting."""
from __future__ import annotations

import json
from functools import lru_cache

from finllm.config.settings import DATA_DIR


@lru_cache(maxsize=2)
def _load_universe_json(name: str) -> list[dict]:
    """Load a saved universe (sp500.json / bist100.json — fetch_*_universe.py).
    Empty list if not fetched yet — caller falls back to a named universe."""
    path = DATA_DIR / "universes" / f"{name}.json"
    if not path.exists():
        return []
    return json.loads(path.read_text())


def _load_sp500() -> list[dict]:
    return _load_universe_json("sp500")


def sector_map(name: str) -> dict[str, str]:
    """symbol → sector for a named universe (macro→sector overlay in the backtest)."""
    key = name.lower().strip()
    if key == "broad":
        return dict(BROAD_UNIVERSE)
    if key == "sp500":
        return {r["symbol"]: r["sector"] for r in _load_sp500()}
    if key in ("bist", "bist100"):
        return {r["symbol"]: r["sector"] for r in _load_universe_json("bist100")}
    return {}

# Dow 30 — same universe FinGPT-forecaster was trained on, good baseline.
DOW30 = [
    "AAPL", "AMGN", "AMZN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS",
    "GS", "HD", "HON", "IBM", "INTC", "JNJ", "JPM", "KO", "MCD", "MMM",
    "MRK", "MSFT", "NKE", "NVDA", "PG", "TRV", "UNH", "V", "VZ", "WMT",
]

# Mega-cap tech subset — fast smoke tests
MEGA_TECH = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]

# Broad multi-sector universe (≈60 liquid large-caps across all 11 GICS sectors +
# a precious-metals miner) — the FAIR test for the macro→sector / fundamental
# overlays, which have little room on the tech-heavy nasdaq list. Sector labels
# match the macro layer canon (macro_sector.SECTORS) so build the sector_map
# directly from this dict.
BROAD_UNIVERSE: dict[str, str] = {
    # Technology
    "AAPL": "Technology", "MSFT": "Technology", "NVDA": "Technology", "AVGO": "Technology",
    "AMD": "Technology", "CRM": "Technology", "ORCL": "Technology", "ADBE": "Technology",
    # Communication Services
    "GOOGL": "Communication Services", "META": "Communication Services", "NFLX": "Communication Services",
    "DIS": "Communication Services", "VZ": "Communication Services", "T": "Communication Services",
    # Consumer Discretionary
    "AMZN": "Consumer Discretionary", "TSLA": "Consumer Discretionary", "HD": "Consumer Discretionary",
    "NKE": "Consumer Discretionary", "MCD": "Consumer Discretionary", "SBUX": "Consumer Discretionary",
    # Consumer Staples
    "PG": "Consumer Staples", "KO": "Consumer Staples", "PEP": "Consumer Staples",
    "COST": "Consumer Staples", "WMT": "Consumer Staples", "MO": "Consumer Staples",
    # Financials
    "JPM": "Financials", "BAC": "Financials", "GS": "Financials", "MS": "Financials",
    "WFC": "Financials", "V": "Financials", "MA": "Financials",
    # Health Care
    "JNJ": "Health Care", "UNH": "Health Care", "LLY": "Health Care", "PFE": "Health Care",
    "MRK": "Health Care", "ABBV": "Health Care",
    # Industrials
    "CAT": "Industrials", "BA": "Industrials", "GE": "Industrials", "HON": "Industrials",
    "UPS": "Industrials", "RTX": "Industrials",
    # Energy
    "XOM": "Energy", "CVX": "Energy", "COP": "Energy", "SLB": "Energy", "EOG": "Energy",
    # Materials
    "LIN": "Materials", "FCX": "Materials", "APD": "Materials", "SHW": "Materials",
    # Utilities
    "NEE": "Utilities", "DUK": "Utilities", "SO": "Utilities", "AEP": "Utilities",
    # Real Estate
    "AMT": "Real Estate", "PLD": "Real Estate", "O": "Real Estate", "SPG": "Real Estate",
    # Precious Metals
    "NEM": "Precious Metals",
}


def _nasdaq_symbols(which: str) -> list[str]:
    """Pull the production NASDAQ universe so the backtest trades the same
    names the live funnel scans. Imported lazily to avoid a hard dependency
    when only the legacy named universes are used."""
    from finllm.markets.universes.nasdaq import (
        NASDAQ_ALL,
        NASDAQ_CORE,
        NASDAQ_TEST,
    )

    table = {"nasdaq": NASDAQ_ALL, "nasdaq_core": NASDAQ_CORE, "nasdaq_test": NASDAQ_TEST}
    return [t.symbol for t in table[which]]


# Named universes that are computed lazily (function → symbol list).
_LAZY: dict[str, str] = {
    "nasdaq": "nasdaq",
    "nasdaq_core": "nasdaq_core",
    "nasdaq_test": "nasdaq_test",
}

UNIVERSES: dict[str, list[str]] = {
    "dow30": DOW30,
    "mega_tech": MEGA_TECH,
}


def resolve(name_or_list: str) -> list[str]:
    """Accept a named universe (`dow30`, `nasdaq`) or a comma-separated list (`AAPL,MSFT`)."""
    key = name_or_list.lower().strip()
    if key == "broad":
        return list(BROAD_UNIVERSE.keys())
    if key == "sp500":
        syms = [r["symbol"] for r in _load_sp500()]
        if not syms:
            raise ValueError("sp500 universe not fetched — run scripts/fetch_sp500_universe.py")
        return syms
    if key in ("bist", "bist100"):
        from finllm.markets.universes.bist_100 import BIST_100_TICKERS
        return [f"{t.symbol}.IS" for t in BIST_100_TICKERS]
    if key in _LAZY:
        return _nasdaq_symbols(_LAZY[key])
    if key in UNIVERSES:
        return UNIVERSES[key]
    return [s.strip().upper() for s in name_or_list.split(",") if s.strip()]
