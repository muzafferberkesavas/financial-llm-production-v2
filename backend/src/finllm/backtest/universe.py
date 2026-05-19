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

UNIVERSES: dict[str, list[str]] = {
    "dow30": DOW30,
    "mega_tech": MEGA_TECH,
}


def resolve(name_or_list: str) -> list[str]:
    """Accept either a named universe (`dow30`) or a comma-separated list (`AAPL,MSFT`)."""
    key = name_or_list.lower().strip()
    if key in UNIVERSES:
        return UNIVERSES[key]
    return [s.strip().upper() for s in name_or_list.split(",") if s.strip()]
