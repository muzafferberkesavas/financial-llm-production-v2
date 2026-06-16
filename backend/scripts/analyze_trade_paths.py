"""Intra-trade path forensics (MFE/MAE) — was a losing/small trade ever IN PROFIT,
or did it bleed from the start? Did we exit too early or too late? Selection vs exit.

For each trade computes, from the OHLC between entry and exit:
  MFE = max favorable excursion (best unrealized gain reached)
  MAE = max adverse excursion (worst unrealized loss reached)
  mfe_day = which day in the trade the peak happened
And from the 10 bars AFTER exit:
  post_max / post_min = how far price ran up / down after we got out
    (STOP: did it bounce back → we were stopped on noise; MAXHOLD: did it hit target
     later → we should have waited).

Usage: python scripts/analyze_trade_paths.py <trades.csv>
"""
from __future__ import annotations

import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
from loguru import logger

logger.remove()
from finllm.data.prices import fetch_prices


def main() -> None:
    df = pd.read_csv(sys.argv[1])
    df["entry_date"] = pd.to_datetime(df["entry_date"])
    df["exit_date"] = pd.to_datetime(df["exit_date"])

    cache: dict = {}
    rows = []
    for _, t in df.iterrows():
        sym = t["symbol"]
        if sym not in cache:
            try:
                cache[sym] = fetch_prices(sym, start="2021-06-01", use_cache=True)
            except Exception:
                cache[sym] = None
        p = cache[sym]
        if p is None:
            continue
        entry, xprice = t["entry_price"], t["exit_price"]
        path = p.loc[t["entry_date"]:t["exit_date"]]
        if path.empty:
            continue
        mfe = (path["high"].max() - entry) / entry * 100
        mae = (path["low"].min() - entry) / entry * 100
        mfe_day = int(np.argmax(path["high"].values))
        after = p.loc[p.index > t["exit_date"]].head(10)
        post_max = (after["high"].max() - xprice) / xprice * 100 if len(after) else np.nan
        post_min = (after["low"].min() - xprice) / xprice * 100 if len(after) else np.nan
        rows.append(dict(reason=t["exit_reason"], pnl=t["pnl_pct"] * 100, days=t["days_held"],
                         mfe=mfe, mae=mae, mfe_day=mfe_day, post_max=post_max, post_min=post_min))
    r = pd.DataFrame(rows)

    def block(name, sub):
        print(f"\n=== {name}  (n={len(sub)}, avg pnl {sub['pnl'].mean():+.2f}%) ===")
        print(f"  MFE (best gain reached): avg {sub['mfe'].mean():+.2f}%  median {sub['mfe'].median():+.2f}%")
        print(f"  MAE (worst dip reached): avg {sub['mae'].mean():+.2f}%  median {sub['mae'].median():+.2f}%")
        print(f"  peak reached on day: avg {sub['mfe_day'].mean():.1f} (of {sub['days'].mean():.1f} held)")

    stop = r[r.reason == "STOP_HIT"]
    mh = r[r.reason == "MAX_HOLDING"]
    tgt = r[r.reason == "TARGET_HIT"]

    print("############ LOSERS / SMALL: were they ever in profit? ############")
    block("STOP_HIT", stop)
    # of stopped trades, how many were meaningfully green first?
    green_first = stop[stop.mfe >= 2]
    bled = stop[stop.mfe < 1]
    print(f"  >> {len(green_first)}/{len(stop)} ({len(green_first)/len(stop)*100:.0f}%) reached ≥+2% BEFORE stopping "
          f"(gave back a real gain → EXIT problem)")
    print(f"  >> {len(bled)}/{len(stop)} ({len(bled)/len(stop)*100:.0f}%) never cleared +1% (bled from entry → SELECTION problem)")
    print(f"  >> after the stop, price's next-10-bar move: avg high {stop['post_max'].mean():+.2f}% / low {stop['post_min'].mean():+.2f}%")
    print(f"     (if avg high is large positive → we were stopped on noise, exit too tight/early)")

    block("MAX_HOLDING", mh)
    mh_small = mh[mh.pnl < 2]
    near_tgt = mh_small[mh_small.mfe >= 5]
    print(f"  >> {len(mh_small)} max-hold trades closed < +2%; of those {len(near_tgt)} ({len(near_tgt)/max(1,len(mh_small))*100:.0f}%) "
          f"had reached ≥+5% MFE first (target was in reach → we gave it back / target too far)")
    print(f"  >> after max-hold exit, next-10-bar move: avg high {mh['post_max'].mean():+.2f}% / low {mh['post_min'].mean():+.2f}%")
    print(f"     (if avg high large → exiting at day-cap left money on the table, should hold longer)")

    print("\n############ WINNERS: how clean were they? ############")
    block("TARGET_HIT", tgt)
    deep_dip = tgt[tgt.mae <= -3]
    print(f"  >> {len(deep_dip)}/{len(tgt)} ({len(deep_dip)/max(1,len(tgt))*100:.0f}%) dipped ≤-3% BEFORE hitting target "
          f"(winners that first scared us — a tighter stop would have killed them)")
    win_mh = mh[mh.pnl > 0]
    block("MAX_HOLDING winners", win_mh)
    print(f"  >> after these winning max-holds, next-10-bar high avg {win_mh['post_max'].mean():+.2f}% "
          f"(if large → trend kept running, we exited a winner too early)")


if __name__ == "__main__":
    main()
