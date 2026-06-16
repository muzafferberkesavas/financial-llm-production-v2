"""Fetch the current S&P 500 constituents (symbol + GICS sector) from Wikipedia
and write them to backend/data/universes/sp500.json for the backtest universe.

Production-scale universe: ~500 liquid US large-caps across all 11 GICS sectors,
vs the hand-curated ~62-name NASDAQ_ALL. Refreshable (re-run to update).

CAVEAT — survivorship bias: this is the CURRENT index membership, so a backtest
over it tacitly excludes names that were dropped/delisted before today. Fine for
relative comparison and development; flag it in any headline number. PIT (point-in-
time) membership would need a paid/historical source.

Sector labels are mapped to the macro layer's canon (macro_sector.SECTORS) so the
macro→sector overlay lines up.
"""
from __future__ import annotations

import io
import json
from pathlib import Path

import httpx
import pandas as pd

from finllm.config.settings import DATA_DIR

WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 finllm-research/1.0"

# Wikipedia GICS sector → macro layer canon (macro_sector.SECTORS).
SECTOR_MAP = {
    "Information Technology": "Technology",
    "Communication Services": "Communication Services",
    "Consumer Discretionary": "Consumer Discretionary",
    "Consumer Staples": "Consumer Staples",
    "Financials": "Financials",
    "Health Care": "Health Care",
    "Industrials": "Industrials",
    "Energy": "Energy",
    "Materials": "Materials",
    "Utilities": "Utilities",
    "Real Estate": "Real Estate",
}


def fetch_sp500() -> list[dict]:
    html = httpx.get(WIKI_URL, headers={"User-Agent": UA}, timeout=30.0, follow_redirects=True).text
    df = pd.read_html(io.StringIO(html))[0]
    out: list[dict] = []
    for _, row in df.iterrows():
        sym = str(row["Symbol"]).strip().upper().replace(".", "-")  # BRK.B → BRK-B (yahoo)
        sector = SECTOR_MAP.get(str(row["GICS Sector"]).strip(), str(row["GICS Sector"]).strip())
        name = str(row["Security"]).strip()
        out.append({"symbol": sym, "name": name, "sector": sector})
    return out


def main() -> None:
    rows = fetch_sp500()
    out_dir = DATA_DIR / "universes"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "sp500.json"
    path.write_text(json.dumps(rows, indent=2))
    from collections import Counter
    sectors = Counter(r["sector"] for r in rows)
    print(f"Wrote {len(rows)} S&P 500 names → {path}")
    for s, n in sectors.most_common():
        print(f"  {s:28s} {n}")


if __name__ == "__main__":
    main()
