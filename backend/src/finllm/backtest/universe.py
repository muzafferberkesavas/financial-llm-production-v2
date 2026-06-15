"""Symbol universes for backtesting."""
from __future__ import annotations

# Dow 30 — same universe FinGPT-forecaster was trained on, good baseline.
DOW30 = [
    "AAPL", "AMGN", "AMZN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS",
    "GS", "HD", "HON", "IBM", "INTC", "JNJ", "JPM", "KO", "MCD", "MMM",
    "MRK", "MSFT", "NKE", "NVDA", "PG", "TRV", "UNH", "V", "VZ", "WMT",
]

# Mega-cap tech subset — fast smoke tests
MEGA_TECH = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]


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
    if key in _LAZY:
        return _nasdaq_symbols(_LAZY[key])
    if key in UNIVERSES:
        return UNIVERSES[key]
    return [s.strip().upper() for s in name_or_list.split(",") if s.strip()]
