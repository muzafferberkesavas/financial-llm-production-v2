"""CLI: walk-forward validation of the EMA-pullback + volume-breakout strategy.

Runs the real strategy over rolling windows and reports the distribution of
PF / Sharpe / return — the overfitting check a single backtest can't give.

Examples:
    python scripts/walkforward.py --universe nasdaq --window-months 12 --step-months 3
    python scripts/walkforward.py --universe nasdaq --costs midas-us --min-setup-score 0.65
"""
from __future__ import annotations

import argparse
from datetime import datetime

from loguru import logger
from rich.console import Console
from rich.table import Table

from finllm.backtest.costs import PRESETS
from finllm.backtest.universe import resolve
from finllm.backtest.walkforward import run_walk_forward, summarize

console = Console()


def parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d")


def _pf(v: float) -> str:
    return "∞" if v == float("inf") else f"{v:.2f}"


def render(results, summary) -> None:
    t = Table(title="Walk-forward windows", show_header=True, header_style="bold cyan")
    t.add_column("#", justify="right")
    t.add_column("Window")
    t.add_column("Syms", justify="right")
    t.add_column("Return", justify="right")
    t.add_column("Sharpe", justify="right")
    t.add_column("PF", justify="right")
    t.add_column("MaxDD", justify="right")
    t.add_column("Trades", justify="right")
    for i, r in enumerate(results, 1):
        m = r.metrics
        pf_style = "green" if m.profit_factor > 1.0 else "red"
        t.add_row(
            str(i),
            f"{r.start.date()} → {r.end.date()}",
            str(r.n_symbols),
            f"{m.total_return_pct:+.1f}%",
            f"{m.sharpe:.2f}",
            f"[{pf_style}]{_pf(m.profit_factor)}[/{pf_style}]",
            f"{m.max_drawdown_pct:.1f}%",
            str(m.n_trades),
        )
    console.print(t)

    s = summary
    summ = Table(title="Distribution across windows", show_header=True, header_style="bold magenta")
    summ.add_column("Metric")
    summ.add_column("Mean", justify="right")
    summ.add_column("Median", justify="right")
    summ.add_column("Min", justify="right")
    summ.add_column("Max", justify="right")
    summ.add_column("Std", justify="right")
    for label, key in [("Profit factor", "profit_factor"), ("Sharpe", "sharpe"),
                       ("Return %", "total_return_pct"), ("Max DD %", "max_drawdown_pct")]:
        d = s[key]
        summ.add_row(label, f"{d['mean']:.2f}", f"{d['median']:.2f}",
                     f"{d['min']:.2f}", f"{d['max']:.2f}", f"{d['std']:.2f}")
    console.print(summ)

    cons = Table(title="Consistency", show_header=True, header_style="bold yellow")
    cons.add_column("Check")
    cons.add_column("Windows passing", justify="right")
    cons.add_row("PF > 1.0", f"{s['pct_pf_gt_1']*100:.0f}%")
    cons.add_row("Sharpe > 0", f"{s['pct_sharpe_gt_0']*100:.0f}%")
    cons.add_row("Positive return", f"{s['pct_positive_return']*100:.0f}%")
    console.print(cons)


def main() -> None:
    ap = argparse.ArgumentParser(description="Walk-forward strategy validation")
    ap.add_argument("--universe", default="nasdaq")
    ap.add_argument("--start", type=parse_date, default=parse_date("2021-01-01"))
    ap.add_argument("--end", type=parse_date, default=parse_date("2024-12-31"))
    ap.add_argument("--window-months", type=int, default=12)
    ap.add_argument("--step-months", type=int, default=3)
    ap.add_argument("--min-setup-score", type=float, default=0.5)
    ap.add_argument("--no-regime", action="store_true")
    ap.add_argument("--costs", choices=sorted(PRESETS), default="midas-us")
    args = ap.parse_args()

    symbols = resolve(args.universe)
    if not symbols:
        raise SystemExit(f"empty universe: {args.universe}")
    logger.info(f"Universe ({len(symbols)}): {', '.join(symbols)}")

    results = run_walk_forward(
        symbols,
        args.start,
        args.end,
        costs=PRESETS[args.costs],
        window_months=args.window_months,
        step_months=args.step_months,
        min_setup_score=args.min_setup_score,
        use_regime=not args.no_regime,
    )
    if not results:
        raise SystemExit("no windows produced results")

    summary = summarize(results)
    console.print()
    render(results, summary)


if __name__ == "__main__":
    main()
