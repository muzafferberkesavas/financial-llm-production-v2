"""In-memory state tracker for a backtest run.

Holds cash, open positions, closed trades, and the daily equity curve.
No DuckDB writes — pure memory so we can run hundreds of backtests fast.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from finllm.portfolio.models import ExitReason, Position
from finllm.signals.schema import Signal


@dataclass
class ClosedTrade:
    symbol: str
    entry_date: datetime
    exit_date: datetime
    entry_price: float
    exit_price: float
    shares: float
    capital_usd: float          # capital deployed at entry
    pnl_usd: float
    pnl_pct: float
    exit_reason: ExitReason
    days_held: int
    entry_confidence: float


@dataclass
class EquityPoint:
    date: datetime
    cash: float
    open_value: float           # mark-to-market value of open positions
    total: float                # cash + open_value
    n_open: int


class BacktestLedger:
    """Tracks portfolio state through a backtest. All amounts in USD."""

    def __init__(self, initial_capital: float):
        self.initial_capital: float = initial_capital
        self.cash: float = initial_capital
        self.open_positions: dict[str, _OpenPosition] = {}     # symbol → position
        self.closed_trades: list[ClosedTrade] = []
        self.equity_curve: list[EquityPoint] = []

    # ---------- queries ----------

    def held_symbols(self) -> set[str]:
        return set(self.open_positions.keys())

    def mark_to_market(self, prices: dict[str, float]) -> float:
        """Value of open positions at the provided prices (skip symbols missing)."""
        total = 0.0
        for sym, pos in self.open_positions.items():
            px = prices.get(sym)
            if px is None:
                # fall back to entry price — no surprise mark
                px = pos.entry_price
            total += pos.shares * px
        return total

    def total_value(self, prices: dict[str, float]) -> float:
        return self.cash + self.mark_to_market(prices)

    # ---------- mutations ----------

    def open_position(
        self,
        signal: Signal,
        entry_price: float,
        entry_date: datetime,
        capital_usd: float,
        max_holding_days: int,
    ) -> None:
        if capital_usd <= 0 or entry_price <= 0:
            return
        if capital_usd > self.cash + 1e-6:
            # never overdraw
            capital_usd = self.cash
        shares = capital_usd / entry_price
        self.cash -= capital_usd
        self.open_positions[signal.symbol] = _OpenPosition(
            symbol=signal.symbol,
            entry_price=entry_price,
            entry_date=entry_date,
            shares=shares,
            capital_usd=capital_usd,
            target_price=signal.targetPrice,
            stop_loss=signal.stopLoss,
            max_holding_days=max_holding_days,
            entry_confidence=signal.confidence,
        )

    def close_position(
        self,
        symbol: str,
        exit_price: float,
        exit_date: datetime,
        reason: ExitReason,
    ) -> ClosedTrade | None:
        pos = self.open_positions.pop(symbol, None)
        if pos is None:
            return None
        proceeds = pos.shares * exit_price
        self.cash += proceeds
        pnl_usd = proceeds - pos.capital_usd
        pnl_pct = pnl_usd / pos.capital_usd if pos.capital_usd > 0 else 0.0
        trade = ClosedTrade(
            symbol=pos.symbol,
            entry_date=pos.entry_date,
            exit_date=exit_date,
            entry_price=pos.entry_price,
            exit_price=exit_price,
            shares=pos.shares,
            capital_usd=pos.capital_usd,
            pnl_usd=pnl_usd,
            pnl_pct=pnl_pct,
            exit_reason=reason,
            days_held=max(0, (exit_date - pos.entry_date).days),
            entry_confidence=pos.entry_confidence,
        )
        self.closed_trades.append(trade)
        return trade

    def record_snapshot(self, date: datetime, prices: dict[str, float]) -> None:
        open_value = self.mark_to_market(prices)
        self.equity_curve.append(
            EquityPoint(
                date=date,
                cash=self.cash,
                open_value=open_value,
                total=self.cash + open_value,
                n_open=len(self.open_positions),
            )
        )

    # ---------- adapter so portfolio.evaluate_exit() can be reused ----------

    def as_position_models(self) -> dict[str, Position]:
        """Wrap open positions in the Pydantic Position model so we can call
        the production evaluate_exit() without reimplementing exit rules."""
        out: dict[str, Position] = {}
        for sym, p in self.open_positions.items():
            out[sym] = Position(
                symbol=p.symbol,
                entry_price=p.entry_price,
                entry_date=p.entry_date,
                target_price=p.target_price,
                stop_loss=p.stop_loss,
                max_holding_days=p.max_holding_days,
                weight_pct=0.0,
                capital_usd=p.capital_usd,
                entry_confidence=p.entry_confidence,
            )
        return out


@dataclass
class _OpenPosition:
    symbol: str
    entry_price: float
    entry_date: datetime
    shares: float
    capital_usd: float
    target_price: float | None
    stop_loss: float | None
    max_holding_days: int
    entry_confidence: float
