"""Forensic trade-level analysis of a backtest run — WHY do losses lose and why are
small wins small? Joins each trade with its setup quality (from entry_confidence),
its 12-1m momentum at entry (recomputed), and its sector, then slices P&L every way.

Usage: python scripts/analyze_trades.py <trades.csv>
"""
from __future__ import annotations

import json
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from finllm.config.settings import DATA_DIR
from finllm.data.prices import fetch_prices
from finllm.indicators.momentum import momentum_12_1


def _sectors() -> dict:
    p = DATA_DIR / "universes" / "sp500.json"
    return {r["symbol"]: r["sector"] for r in json.loads(p.read_text())} if p.exists() else {}


def _band(x, edges, labels):
    for e, l in zip(edges, labels):
        if x <= e:
            return l
    return labels[-1]


def main() -> None:
    csv = sys.argv[1]
    df = pd.read_csv(csv)
    df["entry_date"] = pd.to_datetime(df["entry_date"])
    df["win"] = df["pnl_pct"] > 0
    # entry_confidence = 0.60 + 0.40*setup  →  setup = (conf-0.60)/0.40
    df["setup"] = ((df["entry_confidence"] - 0.60) / 0.40).clip(0, 1).round(2)
    sec = _sectors()
    df["sector"] = df["symbol"].map(lambda s: sec.get(s, "?"))

    # recompute 12-1m momentum at each trade's entry (causal, from cache)
    moms = {}
    for sym in df["symbol"].unique():
        try:
            p = fetch_prices(sym, start="2018-06-01", use_cache=True)
            moms[sym] = p
        except Exception:
            moms[sym] = None

    def mom_at(row):
        p = moms.get(row["symbol"])
        if p is None:
            return np.nan
        w = p.loc[p.index <= row["entry_date"]]
        m = momentum_12_1(w)
        return m if m is not None else np.nan
    df["mom"] = df.apply(mom_at, axis=1)

    n = len(df)
    pnl = df["pnl_pct"] * 100
    print(f"=== {n} trades | WR {df['win'].mean()*100:.1f}% | avg {pnl.mean():+.2f}% | "
          f"total P&L ${df['pnl_usd'].sum():,.0f} ===\n")

    print("--- P&L distribution (pnl_pct buckets) ---")
    edges = [-100, -8, -4, -1, 0, 1, 4, 8, 100]
    lbls = ["<-8%", "-8..-4", "-4..-1", "-1..0", "0..1", "1..4", "4..8", ">8%"]
    df["bucket"] = pnl.apply(lambda x: _band(x, edges[1:], lbls))
    b = df.groupby("bucket").agg(n=("pnl_pct", "size"), tot_usd=("pnl_usd", "sum")).reindex(lbls).fillna(0)
    for k, r in b.iterrows():
        print(f"  {k:>8}: {int(r['n']):3d} trades  ${r['tot_usd']:+8,.0f}")

    print("\n--- EXIT REASON: where P&L is made/lost ---")
    g = df.groupby("exit_reason").agg(n=("pnl_pct", "size"), wr=("win", "mean"),
        avg=("pnl_pct", "mean"), tot=("pnl_usd", "sum"), dur=("days_held", "mean"))
    for k, r in g.sort_values("tot").iterrows():
        print(f"  {k:>12}: {int(r['n']):3d}  WR {r['wr']*100:4.0f}%  avg {r['avg']*100:+5.2f}%  "
              f"${r['tot']:+8,.0f}  {r['dur']:.1f}d")

    print("\n--- WINNERS vs LOSERS: what separates them ---")
    w, l = df[df.win], df[~df.win]
    print(f"  winners: {len(w)}  avg +{w['pnl_pct'].mean()*100:.2f}%  setup {w['setup'].mean():.2f}  "
          f"mom {w['mom'].mean()*100:+.0f}%  held {w['days_held'].mean():.1f}d")
    print(f"  losers : {len(l)}  avg {l['pnl_pct'].mean()*100:.2f}%  setup {l['setup'].mean():.2f}  "
          f"mom {l['mom'].mean()*100:+.0f}%  held {l['days_held'].mean():.1f}d")
    print(f"  >> win/loss avg ratio: {abs(w['pnl_pct'].mean()/l['pnl_pct'].mean()):.2f}  "
          f"(need > {len(l)/len(w):.2f} to be profitable)")

    print("\n--- SETUP QUALITY decile → WR / avg P&L (does better setup = better trade?) ---")
    df["setup_b"] = pd.cut(df["setup"], [0, .3, .5, .7, .85, 1.01], labels=["0-.3", ".3-.5", ".5-.7", ".7-.85", ".85-1"])
    for k, r in df.groupby("setup_b").agg(n=("win", "size"), wr=("win", "mean"), avg=("pnl_pct", "mean")).iterrows():
        if r["n"] > 0:
            print(f"  setup {k:>7}: {int(r['n']):3d}  WR {r['wr']*100:4.0f}%  avg {r['avg']*100:+5.2f}%")

    print("\n--- MOMENTUM quintile → WR / avg P&L (does entry momentum help?) ---")
    df["mom_b"] = pd.qcut(df["mom"].rank(method="first"), 5, labels=["Q1-low", "Q2", "Q3", "Q4", "Q5-high"])
    for k, r in df.groupby("mom_b").agg(n=("win", "size"), wr=("win", "mean"), avg=("pnl_pct", "mean"), m=("mom", "mean")).iterrows():
        print(f"  {k:>8} (mom {r['m']*100:+4.0f}%): {int(r['n']):3d}  WR {r['wr']*100:4.0f}%  avg {r['avg']*100:+5.2f}%")

    print("\n--- HOLDING days → WR / avg P&L (early/late exit effect) ---")
    df["hb"] = pd.cut(df["days_held"], [-1, 0, 2, 5, 8, 100], labels=["0d", "1-2d", "3-5d", "6-8d", "9-10d"])
    for k, r in df.groupby("hb").agg(n=("win", "size"), wr=("win", "mean"), avg=("pnl_pct", "mean")).iterrows():
        if r["n"] > 0:
            print(f"  held {k:>6}: {int(r['n']):3d}  WR {r['wr']*100:4.0f}%  avg {r['avg']*100:+5.2f}%")

    print("\n--- SECTOR → net P&L (selection: which sectors bleed?) ---")
    s = df.groupby("sector").agg(n=("win", "size"), wr=("win", "mean"), tot=("pnl_usd", "sum"))
    for k, r in s.sort_values("tot").iterrows():
        print(f"  {k:>24}: {int(r['n']):3d}  WR {r['wr']*100:4.0f}%  ${r['tot']:+8,.0f}")

    print("\n--- TOP 8 WINNERS ---")
    for _, t in df.nlargest(8, "pnl_pct").iterrows():
        print(f"  {t['symbol']:6} {t['pnl_pct']*100:+6.1f}%  {t['exit_reason']:11} {t['days_held']:2.0f}d  setup {t['setup']:.2f}  mom {t['mom']*100:+.0f}%")
    print("--- TOP 8 LOSERS ---")
    for _, t in df.nsmallest(8, "pnl_pct").iterrows():
        print(f"  {t['symbol']:6} {t['pnl_pct']*100:+6.1f}%  {t['exit_reason']:11} {t['days_held']:2.0f}d  setup {t['setup']:.2f}  mom {t['mom']*100:+.0f}%")


if __name__ == "__main__":
    main()
