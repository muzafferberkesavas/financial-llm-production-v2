"""Portfolio domain modelleri."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Side = Literal["BUY", "SELL"]
PositionStatus = Literal["open", "closed"]
OrderStatus = Literal["pending", "executed", "cancelled"]

ExitReason = Literal[
    "TARGET_HIT",
    "STOP_HIT",
    "MAX_HOLDING",
    "SIGNAL_FLIP",
    "NEGATIVE_NEWS",
    "MANUAL",
]


class Position(BaseModel):
    id: int | None = None
    symbol: str
    entry_price: float
    entry_date: datetime
    target_price: float | None = None
    stop_loss: float | None = None
    max_holding_days: int = 15
    weight_pct: float                # 0-100
    capital_usd: float
    entry_confidence: float | None = None
    entry_rationale: str | None = None

    exit_price: float | None = None
    exit_date: datetime | None = None
    exit_reason: ExitReason | None = None
    pnl_pct: float | None = None
    pnl_usd: float | None = None

    status: PositionStatus = "open"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Order(BaseModel):
    id: int | None = None
    symbol: str
    side: Side
    status: OrderStatus = "pending"
    suggested_price: float
    target_price: float | None = None
    stop_loss: float | None = None
    weight_pct: float | None = None
    capital_usd: float | None = None
    rationale: str | None = None
    reason_code: ExitReason | None = None
    related_position_id: int | None = None
    executed_price: float | None = None
    executed_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PortfolioSnapshot(BaseModel):
    initial_capital_usd: float
    deployed_capital_usd: float
    open_positions: list[Position]
    pending_orders: list[Order]
    realized_pnl_usd: float
    open_pnl_usd: float           # marka-piyasaya görelik
    total_value_usd: float        # cash + open positions @ mark
    n_open: int
    n_pending: int
