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

from finllm.backtest.costs import PRESETS
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
        "--regime-long-period",
        type=int,
        default=200,
        help="QQQ long-term SMA bull/bear filter period (0 = disable, classic 200)",
    )
    ap.add_argument(
        "--rank-momentum",
        type=float,
        default=0.5,
        help="Blend cross-sectional 12-1m momentum percentile into slot selection (0..1, 0=off)",
    )
    ap.add_argument("--mom-lookback", type=int, default=252,
                    help="Selection-momentum lookback in bars (252=12mo; 20=short, more discriminative)")
    ap.add_argument("--mom-skip", type=int, default=21,
                    help="Selection-momentum skip in bars (21=skip last month; 0=no skip)")
    ap.add_argument("--target-mult", type=float, default=4.0,
                    help="ATR target multiple (exit geometry; lower = closer profit target)")
    ap.add_argument("--stop-mult", type=float, default=2.5,
                    help="ATR stop multiple (lower = tighter stop; 2.5 default after whipsaw analysis)")
    ap.add_argument("--holding-max", type=int, default=20,
                    help="Max holding days (swing thesis ≈ 5-8; default 20 = ~1 month)")
    ap.add_argument("--min-52wh-prox", type=float, default=-1.0,
                    help="Require entry within this fraction of the 52wk high (-0.15=within 15%%; -1=off)")
    ap.add_argument("--trail-mult", type=float, default=0.0,
                    help="Chandelier trailing-stop ATR multiple (0=off; let winners run, lock gains)")
    ap.add_argument("--be-activate", type=float, default=0.0,
                    help="Arm trail + breakeven floor only after peak gain ≥ this (e.g. 0.03=+3%%)")
    ap.add_argument("--max-positions", type=int, default=7,
                    help="Max concurrent positions (lower = more concentrated = higher return/risk)")
    ap.add_argument("--sizing", choices=["equal", "conviction", "inverse_atr"], default="conviction",
                    help="Position sizing: equal-weight / momentum-conviction-tilted / equal-risk")
    ap.add_argument("--risk-pct", type=float, default=0.02, help="Per-trade equity risk for inverse_atr")
    ap.add_argument("--max-pos-pct", type=float, default=0.35, help="Cap any single position at this fraction")
    ap.add_argument(
        "--costs",
        choices=sorted(PRESETS),
        default="midas-us",
        help="Transaction-cost preset (default: midas-us = $1.5/trade + 5bps slippage)",
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
        f"regime_gate={'OFF' if args.no_regime else 'QQQ uptrend'}  "
        f"costs={args.costs}"
    )

    config = BacktestConfig(
        universe=symbols,
        start=args.start,
        end=args.end,
        initial_capital=args.initial_capital,
        costs=PRESETS[args.costs],
    )
    engine = StrategyBacktestEngine(
        config,
        min_setup_score=args.min_setup_score,
        use_regime=not args.no_regime,
        regime_long_period=args.regime_long_period or None,
        rank_momentum_weight=args.rank_momentum,
        mom_lookback=args.mom_lookback,
        mom_skip=args.mom_skip,
        target_mult=args.target_mult,
        stop_mult=args.stop_mult,
        holding_max=args.holding_max,
        min_52wh_prox=args.min_52wh_prox,
        trail_mult=args.trail_mult,
        be_activate=args.be_activate,
        max_positions=args.max_positions,
        sizing_mode=args.sizing,
        risk_pct=args.risk_pct,
        max_pos_pct=args.max_pos_pct,
    )
    result = engine.run()

    metrics = build_metrics(result)
    console.print()
    render_console(result, metrics)

    run_dir = save_run(result, metrics, args.out_dir)
    console.print(f"\n[green]Saved run to:[/green] {run_dir}")


if __name__ == "__main__":
    main()
