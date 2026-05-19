"""Render backtest results to console (Rich) and disk (JSON + CSV)."""
from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import pandas as pd
from rich.console import Console
from rich.table import Table

from finllm.backtest.engine import BacktestResult
from finllm.backtest.metrics import PerformanceMetrics, compute, equal_weight_benchmark

console = Console()


def render_console(result: BacktestResult, metrics: PerformanceMetrics) -> None:
    cfg = result.config

    header = Table.grid(padding=(0, 2))
    header.add_column(style="cyan", justify="right")
    header.add_column(style="white")
    header.add_row("Universe:", f"{len(cfg.universe)} symbols")
    header.add_row("Period:", f"{cfg.start.date()} → {cfg.end.date()}")
    header.add_row("Initial capital:", f"${cfg.initial_capital:,.0f}")
    console.print(header)
    console.print()

    perf = Table(title="Performance", show_header=True, header_style="bold cyan")
    perf.add_column("Metric")
    perf.add_column("Value", justify="right")
    perf.add_row("Total return", f"{metrics.total_return_pct:+.2f}%")
    perf.add_row("CAGR", f"{metrics.cagr_pct:+.2f}%")
    perf.add_row("Final equity", f"${metrics.final_equity:,.2f}")
    perf.add_row("Benchmark (buy & hold)", f"{metrics.benchmark_return_pct:+.2f}%")
    perf.add_row("Alpha vs benchmark", f"{metrics.alpha_pct:+.2f}%")
    console.print(perf)

    risk = Table(title="Risk", show_header=True, header_style="bold cyan")
    risk.add_column("Metric")
    risk.add_column("Value", justify="right")
    risk.add_row("Sharpe (ann.)", f"{metrics.sharpe:.2f}")
    risk.add_row("Sortino (ann.)", f"{metrics.sortino:.2f}")
    risk.add_row("Max drawdown", f"{metrics.max_drawdown_pct:.2f}%")
    risk.add_row("Longest underwater", f"{metrics.max_drawdown_days} days")
    console.print(risk)

    trades = Table(title="Trades", show_header=True, header_style="bold cyan")
    trades.add_column("Metric")
    trades.add_column("Value", justify="right")
    trades.add_row("Total trades", str(metrics.n_trades))
    trades.add_row("Wins / losses", f"{metrics.n_wins} / {metrics.n_losses}")
    trades.add_row("Win rate", f"{metrics.win_rate * 100:.1f}%")
    trades.add_row("Avg win", f"{metrics.avg_win_pct:+.2f}%")
    trades.add_row("Avg loss", f"{metrics.avg_loss_pct:+.2f}%")
    pf = "∞" if metrics.profit_factor == float("inf") else f"{metrics.profit_factor:.2f}"
    trades.add_row("Profit factor", pf)
    trades.add_row("Avg duration", f"{metrics.avg_trade_duration_days:.1f} days")
    console.print(trades)

    # Exit reason breakdown
    exits = Counter(t.exit_reason for t in result.ledger.closed_trades)
    if exits:
        exit_t = Table(title="Exit reasons", show_header=True, header_style="bold cyan")
        exit_t.add_column("Reason")
        exit_t.add_column("Count", justify="right")
        exit_t.add_column("% of trades", justify="right")
        total = sum(exits.values())
        for reason, count in exits.most_common():
            exit_t.add_row(reason, str(count), f"{count / total * 100:.1f}%")
        console.print(exit_t)


def save_run(result: BacktestResult, metrics: PerformanceMetrics, out_dir: Path) -> Path:
    """Write metrics.json, trades.csv, equity.csv to a timestamped folder."""
    out_dir.mkdir(parents=True, exist_ok=True)
    run_dir = out_dir / datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)

    # metrics + config
    config_dump = {
        "universe": result.config.universe,
        "start": result.config.start.isoformat(),
        "end": result.config.end.isoformat(),
        "initial_capital": result.config.initial_capital,
    }
    (run_dir / "metrics.json").write_text(
        json.dumps({"config": config_dump, "metrics": metrics.to_dict()}, indent=2)
    )

    # trades CSV
    trade_rows = []
    for t in result.ledger.closed_trades:
        row = asdict(t)
        row["entry_date"] = t.entry_date.isoformat()
        row["exit_date"] = t.exit_date.isoformat()
        trade_rows.append(row)
    if trade_rows:
        with (run_dir / "trades.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(trade_rows[0].keys()))
            w.writeheader()
            w.writerows(trade_rows)

    # equity curve CSV
    with (run_dir / "equity.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "cash", "open_value", "total", "n_open"])
        for p in result.ledger.equity_curve:
            w.writerow([p.date.isoformat(), p.cash, p.open_value, p.total, p.n_open])

    return run_dir


def build_metrics(result: BacktestResult) -> PerformanceMetrics:
    bench = equal_weight_benchmark(
        result.prices,
        start=pd.Timestamp(result.config.start),
        end=pd.Timestamp(result.config.end),
    )
    return compute(result.ledger.equity_curve, result.ledger.closed_trades, benchmark_return_pct=bench)
