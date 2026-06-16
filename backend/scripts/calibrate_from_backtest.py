"""Fit confidence→win-probability calibration from the strategy backtest (#3).

Runs the strategy over history, collects (entry_confidence, win) from closed
trades, fits an isotonic (PAV) calibration, saves it, and prints the reliability
curve so we can see how mis-calibrated the raw confidence is.

    python scripts/calibrate_from_backtest.py --start 2022-01-01 --end 2024-12-31
"""
from __future__ import annotations

import argparse
import collections
from datetime import datetime

from rich.console import Console
from rich.table import Table

from finllm.backtest.engine import BacktestConfig
from finllm.backtest.strategy_engine import StrategyBacktestEngine
from finllm.backtest.universe import resolve
from finllm.calibration.reliability import Reliability, fit_isotonic

console = Console()


def parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--universe", default="nasdaq")
    ap.add_argument("--start", type=parse_date, default=parse_date("2022-01-01"))
    ap.add_argument("--end", type=parse_date, default=parse_date("2024-12-31"))
    ap.add_argument("--min-setup-score", type=float, default=0.5)
    args = ap.parse_args()

    cfg = BacktestConfig(universe=resolve(args.universe), start=args.start, end=args.end)
    res = StrategyBacktestEngine(cfg, min_setup_score=args.min_setup_score).run()
    trades = res.ledger.closed_trades
    pairs = [(t.entry_confidence, 1 if t.pnl_pct > 0 else 0) for t in trades]
    if len(pairs) < 20:
        console.print(f"[red]Too few trades ({len(pairs)}) to calibrate.[/red]")
        return

    rel = Reliability(**fit_isotonic(pairs))
    rel.save()

    # reliability table (raw bins vs calibrated)
    bins = collections.defaultdict(lambda: [0, 0])
    for c, w in pairs:
        b = round(c, 1)
        bins[b][0] += w
        bins[b][1] += 1
    t = Table(title=f"Confidence reliability — {len(pairs)} trades", header_style="bold cyan")
    for col in ("Raw conf", "Trades", "Actual win%", "Calibrated"):
        t.add_column(col, justify="right")
    for b in sorted(bins):
        w, n = bins[b]
        t.add_row(f"{b:.1f}", str(n), f"{w / n:.0%}", f"{rel.calibrate(b):.0%}")
    console.print(t)
    console.print(f"[green]Saved calibration[/green] ({rel.n} samples). "
                  "The panel now maps raw confidence → calibrated win probability.")


if __name__ == "__main__":
    main()
