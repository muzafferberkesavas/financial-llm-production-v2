"""Performance metrics over a list of closed trades and an equity curve."""
from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from finllm.backtest.ledger import ClosedTrade, EquityPoint

TRADING_DAYS_PER_YEAR = 252


@dataclass
class PerformanceMetrics:
    # Returns
    total_return_pct: float
    cagr_pct: float
    final_equity: float
    initial_equity: float

    # Trade stats
    n_trades: int
    n_wins: int
    n_losses: int
    win_rate: float
    avg_win_pct: float
    avg_loss_pct: float
    profit_factor: float          # gross wins / abs(gross losses)
    avg_trade_duration_days: float

    # Risk
    sharpe: float                  # annualized, rf=0
    sortino: float                 # annualized, rf=0
    max_drawdown_pct: float
    max_drawdown_days: int

    # Benchmark comparison (buy-and-hold equal-weight)
    benchmark_return_pct: float
    alpha_pct: float               # strategy - benchmark

    def to_dict(self) -> dict:
        return {
            "total_return_pct": round(self.total_return_pct, 2),
            "cagr_pct": round(self.cagr_pct, 2),
            "final_equity": round(self.final_equity, 2),
            "initial_equity": round(self.initial_equity, 2),
            "n_trades": self.n_trades,
            "n_wins": self.n_wins,
            "n_losses": self.n_losses,
            "win_rate": round(self.win_rate, 4),
            "avg_win_pct": round(self.avg_win_pct, 2),
            "avg_loss_pct": round(self.avg_loss_pct, 2),
            "profit_factor": round(self.profit_factor, 2),
            "avg_trade_duration_days": round(self.avg_trade_duration_days, 1),
            "sharpe": round(self.sharpe, 2),
            "sortino": round(self.sortino, 2),
            "max_drawdown_pct": round(self.max_drawdown_pct, 2),
            "max_drawdown_days": self.max_drawdown_days,
            "benchmark_return_pct": round(self.benchmark_return_pct, 2),
            "alpha_pct": round(self.alpha_pct, 2),
        }


def compute(
    equity: list[EquityPoint],
    trades: list[ClosedTrade],
    benchmark_return_pct: float,
) -> PerformanceMetrics:
    if not equity:
        raise ValueError("empty equity curve")

    initial = equity[0].total
    final = equity[-1].total
    total_return = (final / initial - 1) * 100 if initial > 0 else 0.0

    # CAGR
    days = (equity[-1].date - equity[0].date).days
    years = days / 365.25 if days > 0 else 0.0
    cagr = ((final / initial) ** (1 / years) - 1) * 100 if years > 0 and initial > 0 else 0.0

    # Trade stats
    n = len(trades)
    wins = [t for t in trades if t.pnl_usd > 0]
    losses = [t for t in trades if t.pnl_usd <= 0]
    win_rate = len(wins) / n if n > 0 else 0.0
    avg_win = sum(t.pnl_pct for t in wins) / len(wins) * 100 if wins else 0.0
    avg_loss = sum(t.pnl_pct for t in losses) / len(losses) * 100 if losses else 0.0
    gross_win = sum(t.pnl_usd for t in wins)
    gross_loss = sum(t.pnl_usd for t in losses)
    profit_factor = gross_win / abs(gross_loss) if gross_loss < 0 else float("inf") if gross_win > 0 else 0.0
    avg_duration = sum(t.days_held for t in trades) / n if n > 0 else 0.0

    # Risk metrics from equity curve
    df = pd.DataFrame(
        [{"date": p.date, "total": p.total} for p in equity]
    ).set_index("date")
    daily_ret = df["total"].pct_change().dropna()
    sharpe = _annualized_sharpe(daily_ret)
    sortino = _annualized_sortino(daily_ret)
    dd_pct, dd_days = _max_drawdown(df["total"])

    return PerformanceMetrics(
        total_return_pct=total_return,
        cagr_pct=cagr,
        final_equity=final,
        initial_equity=initial,
        n_trades=n,
        n_wins=len(wins),
        n_losses=len(losses),
        win_rate=win_rate,
        avg_win_pct=avg_win,
        avg_loss_pct=avg_loss,
        profit_factor=profit_factor,
        avg_trade_duration_days=avg_duration,
        sharpe=sharpe,
        sortino=sortino,
        max_drawdown_pct=dd_pct,
        max_drawdown_days=dd_days,
        benchmark_return_pct=benchmark_return_pct,
        alpha_pct=total_return - benchmark_return_pct,
    )


def _annualized_sharpe(daily_ret: pd.Series) -> float:
    if len(daily_ret) < 2:
        return 0.0
    sd = daily_ret.std()
    if sd == 0 or math.isnan(sd):
        return 0.0
    return float(daily_ret.mean() / sd * math.sqrt(TRADING_DAYS_PER_YEAR))


def _annualized_sortino(daily_ret: pd.Series) -> float:
    if len(daily_ret) < 2:
        return 0.0
    downside = daily_ret[daily_ret < 0]
    if len(downside) == 0:
        return float("inf")
    dd_std = downside.std()
    if dd_std == 0 or math.isnan(dd_std):
        return 0.0
    return float(daily_ret.mean() / dd_std * math.sqrt(TRADING_DAYS_PER_YEAR))


def _max_drawdown(equity: pd.Series) -> tuple[float, int]:
    """Returns (max drawdown % as negative number, longest underwater streak in days)."""
    if equity.empty:
        return 0.0, 0
    running_max = equity.cummax()
    drawdown = (equity / running_max - 1) * 100
    max_dd = float(drawdown.min())

    # Longest streak under water (equity below prior peak)
    underwater = equity < running_max
    longest = current = 0
    for u in underwater:
        if u:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return max_dd, longest


def equal_weight_benchmark(
    prices: dict[str, pd.DataFrame],
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> float:
    """Buy-and-hold equal-weight across the universe, return total % over period."""
    rets = []
    for sym, df in prices.items():
        window = df.loc[(df.index >= start) & (df.index <= end)]
        if len(window) < 2:
            continue
        first = float(window["close"].iloc[0])
        last = float(window["close"].iloc[-1])
        if first > 0:
            rets.append((last / first - 1) * 100)
    return sum(rets) / len(rets) if rets else 0.0


def equal_weight_benchmark_curve(
    prices: dict[str, pd.DataFrame],
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.Series:
    """Daily equal-weight buy-and-hold index over [start, end], normalized to 1.0
    at the window's first bar. Used to measure intra-window market stress."""
    cols: dict[str, pd.Series] = {}
    for sym, df in prices.items():
        w = df.loc[(df.index >= start) & (df.index <= end), "close"]
        if len(w) < 2 or float(w.iloc[0]) <= 0:
            continue
        cols[sym] = w / float(w.iloc[0])
    if not cols:
        return pd.Series(dtype=float)
    return pd.DataFrame(cols).ffill().mean(axis=1)


def series_max_drawdown_pct(s: pd.Series) -> float:
    """Max peak-to-trough drawdown of a price/equity series, as a negative %."""
    if s is None or s.empty:
        return 0.0
    running_max = s.cummax()
    drawdown = (s / running_max - 1) * 100
    return float(drawdown.min())
