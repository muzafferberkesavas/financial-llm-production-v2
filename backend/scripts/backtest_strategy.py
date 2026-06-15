"""CLI: backtest the REAL EMA-pullback + volume-breakout swing strategy.

Runs the live Stage 1 hard filter + Stage 1B setup detection over history,
gated by a QQQ uptrend regime filter. Unlike scripts/backtest.py (a generic
technical blend), this measures the user's actual strategy.

Examples:
    python scripts/backtest_strategy.py --universe nasdaq --start 2022-01-01 --end 2024-12-31
    python scripts/backtest_strategy.py --universe nasdaq --min-setup-score 0.6
    python scripts/backtest_strategy.py --universe nasdaq --no-regime   # ablation
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from loguru import logger

from finllm.backtest.engine import BacktestConfig
from finllm.backtest.reports import build_metrics, console, render_console, save_run
from finllm.backtest.strategy_engine import StrategyBacktestEngine
from finllm.backtest.universe import resolve
from finllm.config.settings import settings


def parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d")


def main() -> None:
    ap = argparse.ArgumentParser(description="EMA-pullback + volume-breakout strategy backtest")
    ap.add_argument("--universe", default="nasdaq", help="Named universe or comma-separated tickers")
    ap.add_argument("--start", type=parse_date, default=parse_date("2022-01-01"))
    ap.add_argument("--end", type=parse_date, default=parse_date("2024-12-31"))
    ap.add_argument(
        "--initial-capital",
        type=float,
        default=float(getattr(settings, "portfolio_initial_capital_usd", 10_000)),
    )
    ap.add_argument(
        "--min-setup-score",
        type=float,
        default=0.5,
        help="Minimum Stage 1B setup score to take a trade (0..1)",
    )
    ap.add_argument(
        "--no-regime",
        action="store_true",
        help="Disable the QQQ uptrend gate (ablation: measure raw setup edge)",
    )
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=Path("backend/data/backtest_runs"),
    )
    args = ap.parse_args()

    symbols = resolve(args.universe)
    if not symbols:
        raise SystemExit(f"empty universe: {args.universe}")

    logger.info(f"Universe ({len(symbols)}): {', '.join(symbols)}")
    logger.info(
        f"min_setup_score={args.min_setup_score}  "
        f"regime_gate={'OFF' if args.no_regime else 'QQQ uptrend'}"
    )

    config = BacktestConfig(
        universe=symbols,
        start=args.start,
        end=args.end,
        initial_capital=args.initial_capital,
    )
    engine = StrategyBacktestEngine(
        config,
        min_setup_score=args.min_setup_score,
        use_regime=not args.no_regime,
    )
    result = engine.run()

    metrics = build_metrics(result)
    console.print()
    render_console(result, metrics)

    run_dir = save_run(result, metrics, args.out_dir)
    console.print(f"\n[green]Saved run to:[/green] {run_dir}")


if __name__ == "__main__":
    main()
