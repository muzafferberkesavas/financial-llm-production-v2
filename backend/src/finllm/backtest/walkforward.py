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
    regime: str = "SIDEWAYS"  # BULL | BEAR | SIDEWAYS (from benchmark over the window)


def classify_regime(benchmark_return_pct: float, window_months: int) -> str:
    """Label a window by its benchmark (buy-and-hold universe) return, annualized.

    Bull/bear are the regimes where the research warns a strategy can look great
    or terrible purely from market beta — labelling them lets us check whether the
    edge survives a *bear* (the real robustness question)."""
    annualized = benchmark_return_pct * (12.0 / window_months) if window_months else benchmark_return_pct
    if annualized >= 10.0:
        return "BULL"
    if annualized <= -10.0:
        return "BEAR"
    return "SIDEWAYS"


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
                regime=classify_regime(metrics.benchmark_return_pct, window_months),
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
    """Distribution stats + consistency ratios + per-regime breakdown."""
    n = len(results)
    pf = [r.metrics.profit_factor for r in results if r.metrics.profit_factor != float("inf")]
    sharpe = [r.metrics.sharpe for r in results]
    ret = [r.metrics.total_return_pct for r in results]
    dd = [r.metrics.max_drawdown_pct for r in results]

    by_regime: dict[str, dict] = {}
    for regime in ("BULL", "SIDEWAYS", "BEAR"):
        rs = [r for r in results if r.regime == regime]
        if not rs:
            continue
        by_regime[regime] = {
            "n": len(rs),
            "profit_factor": _stat(
                [r.metrics.profit_factor for r in rs if r.metrics.profit_factor != float("inf")]
            ),
            "return_pct": _stat([r.metrics.total_return_pct for r in rs]),
        }

    return {
        "n_windows": n,
        "profit_factor": _stat(pf),
        "sharpe": _stat(sharpe),
        "total_return_pct": _stat(ret),
        "max_drawdown_pct": _stat(dd),
        "by_regime": by_regime,
        # Consistency — what fraction of windows clears each bar
        "pct_pf_gt_1": sum(1 for r in results if r.metrics.profit_factor > 1.0) / n if n else 0.0,
        "pct_sharpe_gt_0": sum(1 for r in results if r.metrics.sharpe > 0) / n if n else 0.0,
        "pct_positive_return": sum(1 for r in results if r.metrics.total_return_pct > 0) / n if n else 0.0,
    }


# ---------- robustness gate standard ----------

@dataclass
class RobustnessStandard:
    """The bar a strategy must clear in walk-forward before any LLM signal is
    trusted in production. This is the verifier gate from ARCHITECTURE.md §1 (K4):
    it directly targets the five evaluation failures (arXiv:2603.27539) — costs are
    already on, windows are multiple, and these thresholds enforce regime-robustness
    rather than single-window luck.

    Defaults are deliberately strict; tune as the strategy improves.
    """

    min_median_pf: float = 1.20          # typical window must have a real edge
    min_pct_pf_gt_1: float = 0.70        # ≥70% of windows profitable (not a coin-flip)
    max_worst_drawdown_pct: float = -30.0  # no window worse than this
    min_trades_per_window: int = 20      # enough samples per window to mean anything
    min_bear_pf: float = 0.90            # must not bleed badly in a bear regime


@dataclass
class GateCheck:
    name: str
    passed: bool
    detail: str


@dataclass
class GateReport:
    passed: bool
    checks: list[GateCheck]


def evaluate_gate(
    results: list[WindowResult],
    summary: dict,
    standard: RobustnessStandard | None = None,
) -> GateReport:
    std = standard or RobustnessStandard()
    checks: list[GateCheck] = []

    median_pf = summary["profit_factor"]["median"]
    checks.append(GateCheck(
        "median PF", median_pf >= std.min_median_pf,
        f"{median_pf:.2f} (need ≥ {std.min_median_pf:.2f})",
    ))

    pct = summary["pct_pf_gt_1"]
    checks.append(GateCheck(
        "% windows PF>1", pct >= std.min_pct_pf_gt_1,
        f"{pct*100:.0f}% (need ≥ {std.min_pct_pf_gt_1*100:.0f}%)",
    ))

    worst_dd = summary["max_drawdown_pct"]["min"]
    checks.append(GateCheck(
        "worst drawdown", worst_dd >= std.max_worst_drawdown_pct,
        f"{worst_dd:.1f}% (need ≥ {std.max_worst_drawdown_pct:.0f}%)",
    ))

    min_trades = min((r.metrics.n_trades for r in results), default=0)
    checks.append(GateCheck(
        "min trades/window", min_trades >= std.min_trades_per_window,
        f"{min_trades} (need ≥ {std.min_trades_per_window})",
    ))

    bear = summary.get("by_regime", {}).get("BEAR")
    if bear is not None:
        bear_pf = bear["profit_factor"]["mean"]
        checks.append(GateCheck(
            "bear-regime PF", bear_pf >= std.min_bear_pf,
            f"{bear_pf:.2f} (need ≥ {std.min_bear_pf:.2f})",
        ))
    else:
        checks.append(GateCheck(
            "bear-regime PF", False,
            "no BEAR window in range — robustness UNPROVEN (add a bear period)",
        ))

    return GateReport(passed=all(c.passed for c in checks), checks=checks)
