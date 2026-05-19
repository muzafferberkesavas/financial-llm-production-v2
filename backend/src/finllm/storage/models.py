"""SQLAlchemy 2.0 declarative models — Postgres production + DuckDB local dev.

Schema:
  runs              — pipeline run history
  signals           — ExtendedSignal records
  signal_scenarios  — base/bull/bear scenarios per signal
  outcomes          — calibration için realized outcomes
  fundamentals      — cached fundamental snapshots
  watchlists        — user_id → tickers mapping

Auto-detect: DATABASE_URL postgresql://... ise psycopg, duckdb:///... ise duckdb-engine.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Run(Base):
    """Bir pipeline run'unun summary kaydı."""

    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    market: Mapped[str] = mapped_column(String(16), index=True)  # bist | nasdaq
    mode: Mapped[str] = mapped_column(String(32))  # pre_market | intraday | end_of_day
    started_at: Mapped[datetime] = mapped_column(DateTime, index=True)

    total_capital: Mapped[float] = mapped_column(Float)
    max_positions: Mapped[int] = mapped_column(Integer)
    max_position_pct: Mapped[float] = mapped_column(Float)
    cash_buffer_pct: Mapped[float] = mapped_column(Float)
    min_expected_return_pct: Mapped[float] = mapped_column(Float)

    # Regime
    vix: Mapped[float | None] = mapped_column(Float, nullable=True)
    benchmark_change_5d: Mapped[float | None] = mapped_column(Float, nullable=True)
    trade_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    halt_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    fear_level: Mapped[str] = mapped_column(String(16), default="calm")

    # Stats
    universe_size: Mapped[int] = mapped_column(Integer)
    passed_hard_filter: Mapped[int] = mapped_column(Integer)
    stage3_queue_size: Mapped[int] = mapped_column(Integer, default=0)
    signals_generated: Mapped[int] = mapped_column(Integer)
    actionable_signals: Mapped[int] = mapped_column(Integer)
    total_duration_sec: Mapped[float] = mapped_column(Float)
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)

    # Stage timings (JSON)
    stage_durations: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    signals: Mapped[list["Signal"]] = relationship(
        "Signal", back_populates="run", cascade="all, delete-orphan"
    )


class Signal(Base):
    """Bir hisse için tek pipeline çıktısı (ExtendedSignal)."""

    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_db_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)

    ticker: Mapped[str] = mapped_column(String(16), index=True)
    name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(64), nullable=True)
    market: Mapped[str] = mapped_column(String(16), index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    run_id: Mapped[str] = mapped_column(String(64))  # denormalize for easy join

    # Core decision
    signal: Mapped[str] = mapped_column(String(16))  # GUCLU_AL | AL | ...
    confidence: Mapped[float] = mapped_column(Float)
    calibrated_probability: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Pricing
    entry_zone_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    entry_zone_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    stop_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_return_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    time_horizon_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Allocation
    allocation_weight: Mapped[float] = mapped_column(Float, default=0.0)
    allocation_cash: Mapped[float] = mapped_column(Float, default=0.0)

    # Scores
    confluence_score: Mapped[int] = mapped_column(Integer, default=0)
    fundamental_score: Mapped[int] = mapped_column(Integer, default=0)
    market_regime: Mapped[str] = mapped_column(String(32), default="")
    weekly_trend: Mapped[str] = mapped_column(String(32), default="", nullable=True)
    confirmation_count: Mapped[int] = mapped_column(Integer, default=0)

    # Backtest gate
    backtest_30d_return_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    backtest_gate_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_actionable: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # Rationale (JSON)
    rationale: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    warning_flags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    unsourced_flag: Mapped[bool] = mapped_column(Boolean, default=False)

    # Audit
    llm_model: Mapped[str] = mapped_column(String(64), default="")
    llm_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)

    # Scenarios (separate table)
    scenarios: Mapped[list["SignalScenario"]] = relationship(
        "SignalScenario", back_populates="signal", cascade="all, delete-orphan"
    )

    # Confluence/fundamental detail
    confluence_detail: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    fundamental_detail: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    run: Mapped["Run"] = relationship("Run", back_populates="signals")

    __table_args__ = (
        Index("ix_signals_ticker_generated", "ticker", "generated_at"),
        Index("ix_signals_market_actionable", "market", "is_actionable"),
    )


class SignalScenario(Base):
    """Bir signal'a ait base/bull/bear senaryo."""

    __tablename__ = "signal_scenarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    signal_id: Mapped[int] = mapped_column(ForeignKey("signals.id"), index=True)
    label: Mapped[str] = mapped_column(String(8))  # base | bull | bear
    target_price: Mapped[float] = mapped_column(Float)
    probability: Mapped[float] = mapped_column(Float)
    expected_return_pct: Mapped[float] = mapped_column(Float)

    signal: Mapped["Signal"] = relationship("Signal", back_populates="scenarios")


class Outcome(Base):
    """Realized outcome — calibration training set."""

    __tablename__ = "outcomes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    signal_id: Mapped[int | None] = mapped_column(ForeignKey("signals.id"), nullable=True, index=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    ticker: Mapped[str] = mapped_column(String(16), index=True)
    market: Mapped[str] = mapped_column(String(16), index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime)
    signal_label: Mapped[str] = mapped_column(String(16))
    confidence: Mapped[float] = mapped_column(Float)
    expected_return_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    time_horizon_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Realized
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    realized_return_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    realized_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    days_held: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exit_reason: Mapped[str] = mapped_column(String(64), default="")


class FundamentalCache(Base):
    """yfinance.info cache — 12 saatlik TTL ile fetch redundancy'yi azaltır."""

    __tablename__ = "fundamental_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(16), index=True)
    market: Mapped[str] = mapped_column(String(16), index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    pe_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    pb_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    ev_to_ebitda: Mapped[float | None] = mapped_column(Float, nullable=True)
    profit_margin: Mapped[float | None] = mapped_column(Float, nullable=True)
    roe: Mapped[float | None] = mapped_column(Float, nullable=True)
    revenue_growth_yoy: Mapped[float | None] = mapped_column(Float, nullable=True)
    debt_to_equity: Mapped[float | None] = mapped_column(Float, nullable=True)
    market_cap: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (Index("ix_fund_ticker_market", "ticker", "market"),)


class Watchlist(Base):
    """User watchlist — Phase 3'te Postgres'te kalıcı."""

    __tablename__ = "watchlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    ticker: Mapped[str] = mapped_column(String(16))
    market: Mapped[str] = mapped_column(String(16), default="nasdaq")
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("ix_watchlist_user_ticker", "user_id", "ticker", unique=True),)


__all__ = [
    "Base",
    "FundamentalCache",
    "Outcome",
    "Run",
    "Signal",
    "SignalScenario",
    "Watchlist",
]
