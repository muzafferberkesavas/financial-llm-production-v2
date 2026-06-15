"""Measure the macro→sector gate's LIFT over the backtest (Faz B.3).

Runs the strategy over a full period with the gate OFF and with each requested
gate mode, then compares risk-adjusted metrics. The macro view is disk-cached by
month, so the LLM is called ~once per active month on the FIRST paid run; later
runs (and other modes) are free.

COST: with --mock, $0 (validates the harness). With real LLM, ~$0.02 × active
months (typically ~$0.30-0.60 for 2022-24). The script prints the live-call cost.

Usage:
    python scripts/measure_macro_lift.py --mock                      # free dry run
    python scripts/measure_macro_lift.py --modes off,weight,filter   # real (paid)
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table

from finllm.backtest.engine import BacktestConfig
from finllm.backtest.macro_provider import (
    make_cached_llm_macro_provider,
    make_mock_macro_provider,
)
from finllm.backtest.reports import build_metrics
from finllm.backtest.strategy_engine import StrategyBacktestEngine
from finllm.backtest.universe import resolve
from finllm.portfolio.sector_gate import SectorGateConfig

console = Console()


def parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d")


def run_one(symbols, start, end, gate, provider, min_setup_score):
    cfg = BacktestConfig(universe=symbols, start=start, end=end)
    eng = StrategyBacktestEngine(
        cfg, min_setup_score=min_setup_score, sector_gate=gate, macro_provider=provider
    )
    res = eng.run()
    m = build_metrics(res)
    return m, len(res.ledger.closed_trades), eng._macro_cache


def main() -> None:
    ap = argparse.ArgumentParser(description="Macro→sector gate lift measurement")
    ap.add_argument("--universe", default="nasdaq")
    ap.add_argument("--start", type=parse_date, default=parse_date("2022-01-01"))
    ap.add_argument("--end", type=parse_date, default=parse_date("2024-12-31"))
    ap.add_argument("--min-setup-score", type=float, default=0.5)
    ap.add_argument("--modes", default="off,weight,filter,veto",
                    help="comma list of off,weight,filter,veto")
    ap.add_argument("--mock", action="store_true", help="use free mock macro provider")
    ap.add_argument("--model", default=None, help="LLM model (default Sonnet 4.6)")
    ap.add_argument("--cache", default="backend/data/macro_cache.json")
    args = ap.parse_args()

    symbols = resolve(args.universe)
    modes = [m.strip() for m in args.modes.split(",") if m.strip()]

    stats = None
    if args.mock:
        provider = make_mock_macro_provider()
        console.print("[yellow]MOCK provider — $0 dry run[/yellow]\n")
    else:
        provider, stats = make_cached_llm_macro_provider(args.cache, model=args.model)
        console.print(f"[cyan]Cached LLM provider[/cyan] (cache: {args.cache})\n")

    rows = []
    for mode in modes:
        gate = None if mode == "off" else SectorGateConfig(mode=mode)
        prov = None if mode == "off" else provider
        m, n_trades, mcache = run_one(symbols, args.start, args.end, gate, prov, args.min_setup_score)
        rows.append((mode, m, n_trades))
        console.print(f"  ran [bold]{mode}[/bold]: return {m.total_return_pct:+.1f}%  PF {m.profit_factor:.2f}  trades {n_trades}")

    # Comparison table
    t = Table(title=f"Macro→sector lift — {args.universe} {args.start.date()}..{args.end.date()}",
              show_header=True, header_style="bold cyan")
    t.add_column("Mode")
    t.add_column("Return", justify="right")
    t.add_column("CAGR", justify="right")
    t.add_column("Sharpe", justify="right")
    t.add_column("PF", justify="right")
    t.add_column("MaxDD", justify="right")
    t.add_column("Trades", justify="right")
    base = rows[0][1] if rows else None
    for mode, m, n in rows:
        d_sharpe = f" ({m.sharpe - base.sharpe:+.2f})" if base and mode != rows[0][0] else ""
        t.add_row(
            mode, f"{m.total_return_pct:+.1f}%", f"{m.cagr_pct:+.1f}%",
            f"{m.sharpe:.2f}{d_sharpe}",
            f"{'∞' if m.profit_factor==float('inf') else f'{m.profit_factor:.2f}'}",
            f"{m.max_drawdown_pct:.1f}%", str(n),
        )
    console.print()
    console.print(t)

    if stats is not None:
        console.print(
            f"\n[bold]Macro LLM cost:[/bold] [green]${stats['cost_usd']:.4f}[/green] "
            f"({stats['live_calls']} live calls, {stats['cache_hits']} cache hits)"
        )


if __name__ == "__main__":
    main()
