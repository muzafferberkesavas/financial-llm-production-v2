"""What separates WINNERS from LOSERS — at entry time only (no look-ahead).

For every trade, recompute the features that were KNOWABLE the moment we entered
(price action up to entry_date), then rank features by how strongly they separate
winners from losers (Cohen's d) and show win-rate by quintile so we can see which
ones are monotonic — i.e. which to ADD to the selection layer.

Usage: python scripts/discriminate_trades.py <trades.csv>
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
from finllm.indicators.momentum import momentum_12_1
from finllm.pipeline.stage1_filter import _compute_adr_pct, _compute_ema


def _rsi(closes: pd.Series, n: int = 14) -> float:
    d = closes.diff().dropna()
    if len(d) < n:
        return np.nan
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean().iloc[-1]
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean().iloc[-1]
    if dn == 0:
        return 100.0
    rs = up / dn
    return 100 - 100 / (1 + rs)


def _atr_pct(w: pd.DataFrame, n: int = 14) -> float:
    h, l, c = w["high"], w["low"], w["close"]
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / n, adjust=False).mean().iloc[-1]
    return float(atr / c.iloc[-1]) if c.iloc[-1] else np.nan


def feats_at_entry(w: pd.DataFrame) -> dict:
    c = w["close"]
    if len(c) < 60:
        return {}
    ema21 = _compute_ema(c, 21)
    ema50 = _compute_ema(c, 50)
    last = float(c.iloc[-1])
    ema21_series = c.ewm(span=21, adjust=False).mean()
    return {
        "mom_12_1": momentum_12_1(w),
        "ret_5d": last / float(c.iloc[-6]) - 1,
        "ret_20d": last / float(c.iloc[-21]) - 1,
        "adr_pct": _compute_adr_pct(w, 20),
        "atr_pct": _atr_pct(w),
        "ext_ema21": last / ema21 - 1 if ema21 else np.nan,   # extension above EMA21
        "ext_ema50": last / ema50 - 1 if ema50 else np.nan,
        "rsi14": _rsi(c),
        "entry_day_ret": last / float(c.iloc[-2]) - 1,         # green-day strength
        "days_above_ema21": float((c.iloc[-20:] > ema21_series.iloc[-20:]).sum()),
        "vol_surge": float(w["volume"].iloc[-1] / w["volume"].iloc[-20:].mean()),
        "dist_60d_high": last / float(w["high"].iloc[-60:].max()) - 1,  # 0 = at high
        "gap": last / float(c.iloc[-2]) - 1,
    }


def main() -> None:
    df = pd.read_csv(sys.argv[1])
    df["entry_date"] = pd.to_datetime(df["entry_date"])
    df["win"] = df["pnl_pct"] > 0
    df["setup"] = ((df["entry_confidence"] - 0.60) / 0.40).clip(0, 1)

    cache: dict = {}
    rows = []
    for _, t in df.iterrows():
        sym = t["symbol"]
        if sym not in cache:
            try:
                cache[sym] = fetch_prices(sym, start="2018-06-01", use_cache=True)
            except Exception:
                cache[sym] = None
        p = cache[sym]
        if p is None:
            continue
        w = p.loc[p.index <= t["entry_date"]]
        f = feats_at_entry(w)
        if not f:
            continue
        f["setup"] = t["setup"]
        f["win"] = bool(t["win"])
        f["pnl"] = t["pnl_pct"] * 100
        rows.append(f)
    r = pd.DataFrame(rows)
    feat_cols = [c for c in r.columns if c not in ("win", "pnl")]

    print(f"=== {len(r)} trades | {r['win'].sum()} win / {(~r['win']).sum()} loss ===\n")
    print("DISCRIMINATION POWER (entry-time features), ranked by |Cohen's d|:")
    print(f"{'feature':>16} | {'win avg':>9} | {'loss avg':>9} | {'sep(d)':>7} | win-rate by quintile (low→high)")
    out = []
    for col in feat_cols:
        wv = r[r.win][col].dropna()
        lv = r[~r.win][col].dropna()
        if len(wv) < 5 or len(lv) < 5:
            continue
        pooled = np.sqrt((wv.var() + lv.var()) / 2) or 1e-9
        d = (wv.mean() - lv.mean()) / pooled
        # win-rate by quintile of this feature
        try:
            r["_q"] = pd.qcut(r[col].rank(method="first"), 5, labels=False)
            wr = r.groupby("_q")["win"].mean().reindex(range(5)).values
            wr_s = " ".join(f"{x*100:3.0f}" if not np.isnan(x) else " - " for x in wr)
        except Exception:
            wr_s = "n/a"
        out.append((abs(d), col, wv.mean(), lv.mean(), d, wr_s))
    for ad, col, wm, lm, d, wr_s in sorted(out, reverse=True):
        print(f"{col:>16} | {wm:9.3f} | {lm:9.3f} | {d:+7.2f} | {wr_s}")
    print("\n(sep(d): |d|>0.2 small, >0.5 medium, >0.8 large separation)")
    print("quintile win-rate MONOTONIC up/down = usable filter; flat = useless for selection")


if __name__ == "__main__":
    main()
