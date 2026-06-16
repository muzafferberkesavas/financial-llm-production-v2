"""LLM meta-labeling test — can an LLM, seeing ONLY entry-time data, filter our
momentum-selected trades into keep/pass and improve WR / PF / cut average loss?

Leakage-safe: the context is built from price action UP TO entry_date only
(technicals, momentum, RSI, extension) — NO fundamentals/analyst (those are
present-day snapshots and would leak the future). This tests the pure question:
can the LLM read entry-time setup quality and suppress false positives?

Compares the full sampled set vs the subset the LLM said AL (buy):
  if LLM-AL has higher WR + lower avg-loss → meta-labeling works (lit: -46.5% loss).

Usage: python scripts/meta_label_llm_test.py <trades.csv> [n_sample]
COST: ~$0.003/trade (one Sonnet call) → ~$0.40 for 120. Prints running cost.
"""
from __future__ import annotations

import json
import random
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
from loguru import logger

logger.remove()
import anthropic

from finllm.config.settings import settings
from finllm.data.prices import fetch_prices
from finllm.indicators.momentum import momentum_12_1
from finllm.pipeline.stage1_filter import _compute_adr_pct, _compute_ema

MODEL = "claude-sonnet-4-6"
PRICE_IN, PRICE_OUT = 3.0 / 1e6, 15.0 / 1e6  # Sonnet $/token

SYS = (
    "You are a swing-trade RISK FILTER. A momentum strategy already picked this stock; "
    "your only job is to decide whether to ACT on it or PASS. The trade plan: enter now, "
    "hold ~5-8 trading days, take a fast profit, cut losers quickly. Goal is HIGH HIT-RATE "
    "and SMALL losses — when in doubt, PASS. Judge ONLY from the entry-time technicals given "
    "(no other knowledge). Output via the verdict tool: AL (act, high chance of a clean "
    "1-week gain) or PAS (skip, choppy/extended/weak), plus confidence 0-1."
)
TOOL = [{
    "name": "verdict",
    "description": "Keep or pass on this swing trade.",
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["AL", "PAS"]},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "reason": {"type": "string"},
        },
        "required": ["action", "confidence"],
    },
}]


def _rsi(c: pd.Series, n: int = 14) -> float:
    d = c.diff().dropna()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean().iloc[-1]
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean().iloc[-1]
    return 100.0 if dn == 0 else 100 - 100 / (1 + up / dn)


def context(w: pd.DataFrame, setup: float, sector: str) -> str:
    c = w["close"]
    last = float(c.iloc[-1])
    e21, e50 = _compute_ema(c, 21), _compute_ema(c, 50)
    mom = momentum_12_1(w)
    lines = [
        f"sector: {sector}",
        f"setup score: {setup:.2f} (0-1, entry-timing quality)",
        f"12-1m momentum: {mom*100:+.0f}%" if mom is not None else "12-1m momentum: n/a",
        f"5-day return: {(last/float(c.iloc[-6])-1)*100:+.1f}%",
        f"20-day return: {(last/float(c.iloc[-21])-1)*100:+.1f}%",
        f"RSI(14): {_rsi(c):.0f}",
        f"price vs EMA21: {(last/e21-1)*100:+.1f}%" if e21 else "",
        f"price vs EMA50: {(last/e50-1)*100:+.1f}%" if e50 else "",
        f"ADR (daily range): {_compute_adr_pct(w,20):.1f}%",
        f"distance below 60d high: {(last/float(w['high'].iloc[-60:].max())-1)*100:+.1f}%",
        f"entry-day move: {(last/float(c.iloc[-2])-1)*100:+.1f}%",
    ]
    return "\n".join(x for x in lines if x)


def main() -> None:
    csv = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 120
    from finllm.config.settings import DATA_DIR
    p = DATA_DIR / "universes" / "sp500.json"
    sectors = {r["symbol"]: r["sector"] for r in json.loads(p.read_text())} if p.exists() else {}

    df = pd.read_csv(csv)
    df["entry_date"] = pd.to_datetime(df["entry_date"])
    df["setup"] = ((df["entry_confidence"] - 0.60) / 0.40).clip(0, 1)
    random.seed(42)
    idx = list(df.index)
    random.shuffle(idx)
    sample = df.loc[idx[:n]].copy()

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    cache: dict = {}
    cost = 0.0
    recs = []
    for i, (_, t) in enumerate(sample.iterrows()):
        sym = t["symbol"]
        if sym not in cache:
            try:
                cache[sym] = fetch_prices(sym, start="2018-06-01", use_cache=True)
            except Exception:
                cache[sym] = None
        pr = cache[sym]
        if pr is None:
            continue
        w = pr.loc[pr.index <= t["entry_date"]]
        if len(w) < 60:
            continue
        ctx = context(w, t["setup"], sectors.get(sym, "?"))
        try:
            resp = client.messages.create(
                model=MODEL, max_tokens=250, system=SYS, tools=TOOL,
                tool_choice={"type": "tool", "name": "verdict"},
                messages=[{"role": "user", "content": f"[{sym}] entry-time data:\n{ctx}"}],
            )
            cost += resp.usage.input_tokens * PRICE_IN + resp.usage.output_tokens * PRICE_OUT
            tu = next(b for b in resp.content if b.type == "tool_use")
            act = tu.input["action"]
        except Exception as e:
            print(f"  {sym}: LLM err {str(e)[:50]}", flush=True)
            continue
        recs.append({"sym": sym, "llm": act, "pnl": t["pnl_pct"] * 100, "win": t["pnl_pct"] > 0})
        if (i + 1) % 20 == 0:
            print(f"  ...{i+1}/{n}  cost ${cost:.2f}", flush=True)

    r = pd.DataFrame(recs)

    def stats(name, sub):
        if len(sub) == 0:
            print(f"{name:>16}: (empty)")
            return
        wr = sub["win"].mean() * 100
        wins, losses = sub[sub.win], sub[~sub.win]
        pf = (wins["pnl"].sum() / abs(losses["pnl"].sum())) if len(losses) and losses["pnl"].sum() != 0 else float("inf")
        al = losses["pnl"].mean() if len(losses) else 0
        print(f"{name:>16}: n={len(sub):3d}  WR {wr:4.1f}%  PF {pf:4.2f}  avg-loss {al:+5.2f}%  avg-pnl {sub['pnl'].mean():+5.2f}%")

    print(f"\n===== LLM META-LABEL RESULT (n={len(r)}, cost ${cost:.2f}) =====")
    stats("ALL trades", r)
    stats("LLM said AL", r[r.llm == "AL"])
    stats("LLM said PAS", r[r.llm == "PAS"])
    kept = (r.llm == "AL").mean() * 100
    print(f"\nLLM kept {kept:.0f}% of trades.")
    al, allr = r[r.llm == "AL"], r
    if len(al):
        print(f">> WR change: {allr['win'].mean()*100:.1f}% → {al['win'].mean()*100:.1f}%  "
              f"({(al['win'].mean()-allr['win'].mean())*100:+.1f}pp)")
        la, lo = allr[~allr.win]["pnl"].mean(), al[~al.win]["pnl"].mean() if (~al.win).any() else 0
        print(f">> avg-loss change: {la:+.2f}% → {lo:+.2f}%  (target: less negative = better downside control)")


if __name__ == "__main__":
    main()
