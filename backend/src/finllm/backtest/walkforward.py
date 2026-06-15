"""Walk-forward validation — run the strategy over many rolling windows.

A single backtest window is the classic overfitting trap (research arXiv:2603.27539,
arXiv:2411.08899): one good period proves nothing. This harness slices [start, end]
into overlapping rolling windows, runs the real StrategyBacktestEngine on each, and
reports the *distribution* of PF / Sharpe / return so we can see whether the edge is
consistent or a single-window fluke.

Each window is an independent run (own warmup, own regime gate, own cost model), so
the only thing shared is the universe and parameters.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import datetime

import pandas as pd
from loguru import logger

from finllm.backtest.costs import CostModel
from finllm.backtest.engine import BacktestConfig
from finllm.backtest.metrics import PerformanceMetrics
from finllm.backtest.reports import build_metrics
from finllm.backtest.strategy_engine import StrategyBacktestEngine


@dataclass
class WindowResult:
    start: datetime
    end: datetime
    metrics: PerformanceMetrics
    n_symbols: int
    commission_usd: float


def generate_windows(
    start: datetime,
    end: datetime,
    window_months: int,
    step_months: int,
) -> list[tuple[datetime, datetime]]:
    """Rolling [w_start, w_end] windows of ``window_months`` length, stepped by
    ``step_months``. Only full-length windows that fit inside [start, end]."""
    windows: list[tuple[datetime, datetime]] = []
    cur = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    while True:
        w_end = cur + pd.DateOffset(months=window_months) - pd.DateOffset(days=1)
        if w_end > end_ts:
            break
        windows.append((cur.to_pydatetime(), w_end.to_pydatetime()))
        cur = cur + pd.DateOffset(months=step_months)
    return windows


def run_walk_forward(
    universe: list[str],
    start: datetime,
    end: datetime,
    *,
    costs: CostModel,
    window_months: int = 12,
    step_months: int = 3,
    min_setup_score: float = 0.5,
    use_regime: bool = True,
) -> list[WindowResult]:
    windows = generate_windows(start, end, window_months, step_months)
    if not windows:
        raise ValueError(
            f"no full {window_months}-month window fits in {start.date()}..{end.date()}"
        )
    logger.info(
        f"Walk-forward: {len(windows)} windows "
        f"({window_months}mo length, {step_months}mo step)"
    )
    results: list[WindowResult] = []
    for i, (w_start, w_end) in enumerate(windows, 1):
        logger.info(f"--- window {i}/{len(windows)}: {w_start.date()} → {w_end.date()} ---")
        config = BacktestConfig(
            universe=universe, start=w_start, end=w_end, costs=costs
        )
        engine = StrategyBacktestEngine(
            config, min_setup_score=min_setup_score, use_regime=use_regime
        )
        try:
            res = engine.run()
        except Exception as e:  # noqa: BLE001
            logger.warning(f"window {i} failed — {e}; skipping")
            continue
        metrics = build_metrics(res)
        results.append(
            WindowResult(
                start=w_start,
                end=w_end,
                metrics=metrics,
                n_symbols=len(res.prices),
                commission_usd=res.ledger.total_commission_usd,
            )
        )
    return results


# ---------- aggregation ----------

def _stat(values: list[float]) -> dict[str, float]:
    if not values:
        return {"mean": 0.0, "median": 0.0, "min": 0.0, "max": 0.0, "std": 0.0}
    return {
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
        "std": statistics.pstdev(values) if len(values) > 1 else 0.0,
    }


def summarize(results: list[WindowResult]) -> dict:
    """Distribution stats + consistency ratios across windows."""
    n = len(results)
    pf = [r.metrics.profit_factor for r in results if r.metrics.profit_factor != float("inf")]
    sharpe = [r.metrics.sharpe for r in results]
    ret = [r.metrics.total_return_pct for r in results]
    dd = [r.metrics.max_drawdown_pct for r in results]

    return {
        "n_windows": n,
        "profit_factor": _stat(pf),
        "sharpe": _stat(sharpe),
        "total_return_pct": _stat(ret),
        "max_drawdown_pct": _stat(dd),
        # Consistency — what fraction of windows clears each bar
        "pct_pf_gt_1": sum(1 for r in results if r.metrics.profit_factor > 1.0) / n if n else 0.0,
        "pct_sharpe_gt_0": sum(1 for r in results if r.metrics.sharpe > 0) / n if n else 0.0,
        "pct_positive_return": sum(1 for r in results if r.metrics.total_return_pct > 0) / n if n else 0.0,
    }
