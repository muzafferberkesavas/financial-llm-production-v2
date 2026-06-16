"""Export the BIST-100 universe (symbol + sector) to data/universes/bist100.json
and prefetch its price history into the cache, mirroring fetch_sp500_universe.py.

The constituent list lives in code (markets/universes/bist_100.py, ported from the
lib.zip app). This script materializes it as JSON — same shape as sp500.json — so
the backtest/universe layer can load both markets uniformly, and warms the yfinance
cache (.IS suffix) so later backtests run offline-fast.
"""
from __future__ import annotations

import json
import time

from finllm.config.settings import DATA_DIR
from finllm.data.prices import fetch_prices
from finllm.markets.universes.bist_100 import BIST_100_TICKERS

# Skip the commodity tickers (GC=F, SI=F) — those are global Yahoo symbols, not BIST.
PREFETCH_START = "2017-06-01"
PREFETCH_END = "2024-12-31"


def main() -> None:
    rows = [
        {"symbol": f"{t.symbol}.IS", "name": t.name, "sector": t.sector}
        for t in BIST_100_TICKERS
        if "=" not in t.symbol  # drop commodity futures
    ]
    out_dir = DATA_DIR / "universes"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "bist100.json"
    path.write_text(json.dumps(rows, indent=2, ensure_ascii=False))
    print(f"Wrote {len(rows)} BIST-100 names → {path}", flush=True)

    ok = skip = 0
    for i, r in enumerate(rows):
        s = r["symbol"]
        t0 = time.time()
        try:
            df = fetch_prices(s, start=PREFETCH_START, end=PREFETCH_END, use_cache=True)
            ok += 1
            if time.time() - t0 > 8:
                print(f"SLOW {s} {time.time()-t0:.0f}s rows={len(df)}", flush=True)
        except Exception as e:  # noqa: BLE001
            skip += 1
            print(f"SKIP {s}: {str(e)[:60]}", flush=True)
        if i % 25 == 0:
            print(f"...{i}/{len(rows)} ok={ok} skip={skip}", flush=True)
    print(f"BIST100DONE ok={ok} skip={skip}", flush=True)


if __name__ == "__main__":
    main()
