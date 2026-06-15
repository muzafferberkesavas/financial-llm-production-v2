"""Event-driven daily backtest engine.

For each trading day in [start, end]:
  1. Slice price + feature frames to data available up to today (no look-ahead).
  2. Evaluate exits on open positions (intraday target/stop checks + time-based).
  3. Generate technical signals for every universe symbol on today's bar.
  4. Run the production position sizer to pick weights.
  5. Open new positions from available cash.
  6. Record an equity snapshot.

Look-ahead guard: features are pre-computed on the full dataset once but only
*sliced* (never recomputed) per day. All indicators used here are causal — they
reference close[t] and prior bars only, never close[t+k].
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

import pandas as pd
from loguru import logger

from finllm.backtest.ledger import BacktestLedger
from finllm.backtest.signals import DEFAULT_HOLDING_MAX, technical_signal
from finllm.data.prices import fetch_prices
from finllm.portfolio.exits import evaluate_exit
from finllm.portfolio.models import ExitReason
from finllm.portfolio.sizing import compute_weights, select_buy_candidates

WARMUP_DAYS = 400          # ~1.5 trading years — enough for SMA200 + indicator stabilization
MIN_FEATURE_ROWS = 200     # don't trade a symbol until we have this much history
MIN_NEW_POSITION_PCT = 2.0 # don't open a position smaller than this % of equity (avoid dust)


@dataclass
class BacktestConfig:
    universe: list[str]
    start: datetime
    end: datetime
    initial_capital: float = 10_000.0

    def __post_init__(self) -> None:
        if self.end <= self.start:
            raise ValueError("end must be after start")
        if not self.universe:
            raise ValueError("universe is empty")


@dataclass
class BacktestResult:
    config: BacktestConfig
    ledger: BacktestLedger
    prices: dict[str, pd.DataFrame] = field(default_factory=dict)


class BacktestEngine:
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.ledger = BacktestLedger(initial_capital=config.initial_capital)
        self.prices: dict[str, pd.DataFrame] = {}
        self.features: dict[str, pd.DataFrame] = {}

    # ---------- setup ----------

    def _load_data(self) -> None:
        # Lazy import: the generic technical-blend backtest needs pandas-ta, but
        # the strategy backtest (which overrides _load_data) does not — keeping
        # this import here lets the strategy path run without pandas-ta.
        from finllm.features.technical import add_technical_features

        warmup_start = (self.config.start - timedelta(days=WARMUP_DAYS)).strftime("%Y-%m-%d")
        end_str = self.config.end.strftime("%Y-%m-%d")

        for sym in self.config.universe:
            try:
                p = fetch_prices(sym, start=warmup_start, end=end_str, use_cache=True)
            except Exception as e:
                logger.warning(f"{sym}: price fetch failed — {e}")
                continue
            if p.empty or len(p) < MIN_FEATURE_ROWS:
                logger.warning(f"{sym}: insufficient history ({len(p)} rows) — skipping")
                continue
            self.prices[sym] = p
            self.features[sym] = add_technical_features(p)
        logger.info(f"Loaded {len(self.prices)}/{len(self.config.universe)} symbols")

    def _trading_days(self) -> pd.DatetimeIndex:
        """Union of all symbols' trading days within [start, end]."""
        all_dates: set[pd.Timestamp] = set()
        for df in self.prices.values():
            in_window = df.index[(df.index >= self.config.start) & (df.index <= self.config.end)]
            all_dates.update(in_window)
        return pd.DatetimeIndex(sorted(all_dates))

    # ---------- per-day operations ----------

    def _today_close(self, sym: str, date: pd.Timestamp) -> float | None:
        df = self.prices[sym]
        window = df.loc[df.index <= date]
        if window.empty:
            return None
        return float(window["close"].iloc[-1])

    def _today_bar(self, sym: str, date: pd.Timestamp) -> pd.Series | None:
        df = self.prices[sym]
        if date not in df.index:
            return None
        return df.loc[date]

    def _check_exits(self, date: pd.Timestamp) -> None:
        """Apply intraday target/stop checks then time-based exits."""
        positions = self.ledger.as_position_models()
        for sym, pos in positions.items():
            bar = self._today_bar(sym, date)
            if bar is None:
                continue
            high = float(bar["high"])
            low = float(bar["low"])
            close = float(bar["close"])

            exit_reason: ExitReason | None = None
            exit_price: float | None = None

            # Conservative: if both stop and target hit same day, assume stop first.
            if pos.stop_loss is not None and low <= pos.stop_loss:
                exit_reason = "STOP_HIT"
                exit_price = pos.stop_loss
            elif pos.target_price is not None and high >= pos.target_price:
                exit_reason = "TARGET_HIT"
                exit_price = pos.target_price
            else:
                # Time-based / signal-flip — checked at close
                decision = evaluate_exit(pos, close, new_signal=None, now=date.to_pydatetime())
                if decision.should_exit:
                    exit_reason = decision.reason
                    exit_price = close

            if exit_reason is not None and exit_price is not None:
                self.ledger.close_position(sym, exit_price, date.to_pydatetime(), exit_reason)

    def _generate_signals(self, date: pd.Timestamp) -> list:
        signals = []
        for sym, feats in self.features.items():
            window = feats.loc[feats.index <= date]
            if len(window) < MIN_FEATURE_ROWS:
                continue
            sig = technical_signal(sym, window, now=date.to_pydatetime())
            if sig is not None:
                signals.append(sig)
        return signals

    def _open_new_positions(self, date: pd.Timestamp, signals: list) -> None:
        held = self.ledger.held_symbols()
        candidates = select_buy_candidates(signals, exclude_symbols=held)
        weighted = compute_weights(candidates)
        if not weighted:
            return

        today_prices = {sig.symbol: self._today_close(sig.symbol, date) for sig, _ in weighted}
        total_value = self.ledger.total_value({s: p for s, p in today_prices.items() if p is not None})
        min_capital = total_value * MIN_NEW_POSITION_PCT / 100

        for signal, weight_pct in weighted:
            entry_price = today_prices.get(signal.symbol)
            if entry_price is None or entry_price <= 0:
                continue
            target_capital = total_value * weight_pct / 100
            actual_capital = min(target_capital, self.ledger.cash)
            if actual_capital < min_capital:
                continue
            self.ledger.open_position(
                signal=signal,
                entry_price=entry_price,
                entry_date=date.to_pydatetime(),
                capital_usd=actual_capital,
                max_holding_days=signal.holdingDays.max or DEFAULT_HOLDING_MAX,
            )

    def _record_snapshot(self, date: pd.Timestamp) -> None:
        prices = {s: self._today_close(s, date) for s in self.ledger.held_symbols()}
        self.ledger.record_snapshot(date.to_pydatetime(), {s: p for s, p in prices.items() if p is not None})

    # ---------- main loop ----------

    def run(self) -> BacktestResult:
        self._load_data()
        if not self.prices:
            raise RuntimeError("no usable symbol data — aborting")

        days = self._trading_days()
        logger.info(f"Simulating {len(days)} trading days: {days[0].date()} → {days[-1].date()}")

        for i, date in enumerate(days):
            self._check_exits(date)
            signals = self._generate_signals(date)
            self._open_new_positions(date, signals)
            self._record_snapshot(date)
            if (i + 1) % 50 == 0:
                eq = self.ledger.equity_curve[-1].total
                logger.info(
                    f"  day {i+1}/{len(days)} ({date.date()}): "
                    f"equity ${eq:,.0f}, open={self.ledger.equity_curve[-1].n_open}, "
                    f"closed_trades={len(self.ledger.closed_trades)}"
                )

        # Close any positions still open at end (mark to last close)
        last_date = days[-1]
        for sym in list(self.ledger.held_symbols()):
            close = self._today_close(sym, last_date)
            if close is not None:
                self.ledger.close_position(sym, close, last_date.to_pydatetime(), "MAX_HOLDING")

        return BacktestResult(config=self.config, ledger=self.ledger, prices=self.prices)
