"""In-memory state tracker for a backtest run.

Holds cash, open positions, closed trades, and the daily equity curve.
No DuckDB writes — pure memory so we can run hundreds of backtests fast.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from finllm.backtest.costs import CostModel
from finllm.portfolio.models import ExitReason, Position
from finllm.signals.schema import Signal


@dataclass
class ClosedTrade:
    symbol: str
    entry_date: datetime
    exit_date: datetime
    entry_price: float          # actual fill price (slippage applied)
    exit_price: float           # actual fill price (slippage applied)
    shares: float
    capital_usd: float          # capital deployed at entry (notional at fill)
    pnl_usd: float              # net of entry + exit commission
    pnl_pct: float
    exit_reason: ExitReason
    days_held: int
    entry_confidence: float
    commission_usd: float = 0.0  # entry + exit commission for this trade


@dataclass
class EquityPoint:
    date: datetime
    cash: float
    open_value: float           # mark-to-market value of open positions
    total: float                # cash + open_value
    n_open: int


class BacktestLedger:
    """Tracks portfolio state through a backtest. All amounts in USD."""

    def __init__(self, initial_capital: float, costs: CostModel | None = None):
        self.initial_capital: float = initial_capital
        self.cash: float = initial_capital
        self.costs: CostModel = costs if costs is not None else CostModel.zero()
        self.open_positions: dict[str, _OpenPosition] = {}     # symbol → position
        self.closed_trades: list[ClosedTrade] = []
        self.equity_curve: list[EquityPoint] = []
        self.total_commission_usd: float = 0.0

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
        """Open a long position.

        ``entry_price`` is the *reference* fill price (e.g. next-bar open);
        slippage is applied here so the position fills slightly worse, and
        commission is deducted from cash on top of the deployed notional.
        """
        if capital_usd <= 0 or entry_price <= 0:
            return
        fill = self.costs.entry_fill_price(entry_price)

        # Deploy `capital_usd` of notional, pay commission on top. If cash can't
        # cover notional + commission, scale the notional down to fit.
        shares = capital_usd / fill
        commission = self.costs.commission(fill, shares)
        if capital_usd + commission > self.cash + 1e-6:
            capital_usd = max(0.0, self.cash - self.costs.flat_fee_usd)
            shares = capital_usd / fill
            commission = self.costs.commission(fill, shares)
            if capital_usd + commission > self.cash + 1e-6:
                # still short (tiny cash) — skip rather than overdraw
                return
        if capital_usd <= 0 or shares <= 0:
            return

        self.cash -= capital_usd + commission
        self.total_commission_usd += commission
        self.open_positions[signal.symbol] = _OpenPosition(
            symbol=signal.symbol,
            entry_price=fill,
            entry_date=entry_date,
            shares=shares,
            capital_usd=capital_usd,
            target_price=signal.targetPrice,
            stop_loss=signal.stopLoss,
            max_holding_days=max_holding_days,
            entry_confidence=signal.confidence,
            entry_commission=commission,
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
        # `exit_price` is the reference exit level (stop/target level or close);
        # slippage makes the realised fill worse, then exit commission is deducted.
        fill = self.costs.exit_fill_price(exit_price)
        exit_commission = self.costs.commission(fill, pos.shares)
        proceeds = pos.shares * fill - exit_commission
        self.cash += proceeds
        self.total_commission_usd += exit_commission
        pnl_usd = proceeds - pos.capital_usd - pos.entry_commission
        pnl_pct = pnl_usd / pos.capital_usd if pos.capital_usd > 0 else 0.0
        trade = ClosedTrade(
            symbol=pos.symbol,
            entry_date=pos.entry_date,
            exit_date=exit_date,
            entry_price=pos.entry_price,
            exit_price=fill,
            shares=pos.shares,
            capital_usd=pos.capital_usd,
            pnl_usd=pnl_usd,
            pnl_pct=pnl_pct,
            exit_reason=reason,
            days_held=max(0, (exit_date - pos.entry_date).days),
            entry_confidence=pos.entry_confidence,
            commission_usd=pos.entry_commission + exit_commission,
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
    entry_commission: float = 0.0
