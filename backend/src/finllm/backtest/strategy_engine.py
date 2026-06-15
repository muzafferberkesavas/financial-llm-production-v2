"""Strategy backtest engine — runs the real EMA-pullback + volume-breakout
swing strategy over history.

Reuses BacktestEngine's event loop, ledger, no-look-ahead slicing, exit logic,
and snapshots. It only swaps two things:

  1. Signal generation → `strategy_signal()` (Stage 1 filter + Stage 1B setup),
     run on the RAW price frame instead of the generic feature-blend signal.
  2. A QQQ trend-regime gate: on a day where QQQ is not in an uptrend, no new
     positions are opened (open positions are still managed/exited normally).

Sizing here is fixed-fractional (equity / MAX_POSITIONS) rather than the live
confidence-weighted sizer. The point of this backtest is to isolate the edge
of the setup itself, so every qualifying setup gets a comparable slug of
capital and thin days aren't zeroed out by the live MIN_POSITIONS=3 rule.
"""
from __future__ import annotations

from datetime import timedelta

import pandas as pd
from loguru import logger

from finllm.backtest.engine import (
    MIN_FEATURE_ROWS,
    WARMUP_DAYS,
    BacktestConfig,
    BacktestEngine,
)
from typing import Callable

from finllm.backtest.strategy_signals import (
    qqq_uptrend,
    strategy_signal,
)
from finllm.data.prices import fetch_prices
from finllm.llm.macro_sector import MacroSectorAnalysis
from finllm.markets import get_adapter
from finllm.portfolio.sector_gate import (
    SectorGateConfig,
    apply_sector_gate,
    build_sector_map,
)

REGIME_SYMBOL = "QQQ"
MAX_POSITIONS = 7

# A macro provider maps an as-of date (YYYY-MM-DD) to that period's sector view.
# Injected so the engine never imports the LLM client directly — gate-off passes
# None, the real run passes an LLM-backed (monthly-cached) provider, tests pass a
# cheap mock. Returns None when no view is available (→ gate is a no-op that day).
MacroProvider = Callable[[str], "MacroSectorAnalysis | None"]


class StrategyBacktestEngine(BacktestEngine):
    def __init__(
        self,
        config: BacktestConfig,
        min_setup_score: float = 0.5,
        use_regime: bool = True,
        regime_long_period: int | None = 200,
        sector_gate: SectorGateConfig | None = None,
        macro_provider: MacroProvider | None = None,
    ):
        super().__init__(config)
        self.min_setup_score = min_setup_score
        self.use_regime = use_regime
        self.regime_long_period = regime_long_period
        self.thresholds = get_adapter("nasdaq").thresholds
        self.regime_prices: pd.DataFrame | None = None
        self._regime_cache: dict[pd.Timestamp, bool] = {}

        # Macro→sector gate (Faz B.3). Active only when both a config and a
        # provider are supplied; macro views are cached per calendar month so a
        # 3-year backtest costs ~36 LLM calls, not one per trading day.
        self.sector_gate = sector_gate
        self.macro_provider = macro_provider
        self.sector_map: dict[str, str] = build_sector_map() if sector_gate else {}
        self._macro_cache: dict[str, MacroSectorAnalysis | None] = {}

    # ---------- data ----------

    def _load_data(self) -> None:
        # Strategy signals work on the RAW price frame (Stage 1 filter + Stage 1B
        # setup compute their own EMAs/ADR/ATR), so we skip add_technical_features
        # entirely — that also keeps this path free of the pandas-ta dependency.
        warmup_start = (self.config.start - timedelta(days=WARMUP_DAYS)).strftime("%Y-%m-%d")
        end_str = self.config.end.strftime("%Y-%m-%d")
        for sym in self.config.universe:
            try:
                p = fetch_prices(sym, start=warmup_start, end=end_str, use_cache=True)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"{sym}: price fetch failed — {e}")
                continue
            if p.empty or len(p) < MIN_FEATURE_ROWS:
                logger.warning(f"{sym}: insufficient history ({len(p)} rows) — skipping")
                continue
            self.prices[sym] = p
        logger.info(f"Loaded {len(self.prices)}/{len(self.config.universe)} symbols")

        if not self.use_regime:
            return
        warmup_start = (self.config.start - timedelta(days=WARMUP_DAYS)).strftime("%Y-%m-%d")
        end_str = self.config.end.strftime("%Y-%m-%d")
        try:
            qqq = fetch_prices(REGIME_SYMBOL, start=warmup_start, end=end_str, use_cache=True)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"QQQ regime fetch failed ({e}) — running WITHOUT regime gate")
            self.use_regime = False
            return
        if qqq.empty:
            logger.warning("QQQ regime data empty — running WITHOUT regime gate")
            self.use_regime = False
            return
        self.regime_prices = qqq

    # ---------- regime gate ----------

    def _regime_ok(self, date: pd.Timestamp) -> bool:
        if not self.use_regime or self.regime_prices is None:
            return True
        cached = self._regime_cache.get(date)
        if cached is not None:
            return cached
        window = self.regime_prices.loc[self.regime_prices.index <= date]
        ok = (
            qqq_uptrend(window, long_sma_period=self.regime_long_period)
            if not window.empty
            else False
        )
        self._regime_cache[date] = ok
        return ok

    # ---------- signal generation (override) ----------

    def _generate_signals(self, date: pd.Timestamp) -> list:
        if not self._regime_ok(date):
            return []  # QQQ not in uptrend → no new entries today
        signals = []
        for sym, p in self.prices.items():
            window = p.loc[p.index <= date]
            if len(window) < MIN_FEATURE_ROWS:
                continue
            sig = strategy_signal(
                sym, window, date.to_pydatetime(), self.thresholds, self.min_setup_score
            )
            if sig is not None:
                signals.append(sig)
        return signals

    # ---------- sizing (override: fixed fractional, no MIN_POSITIONS gate) ----------

    def _plan_entries(self, date: pd.Timestamp, signals: list) -> list[tuple]:
        """Equal-weight slug per qualifying setup, ranked by setup score.

        Decided at close[t]; the base engine fills the plan at open[t+1] with
        slippage + commission applied. Only the selection/sizing differs from the
        generic engine — execution is shared.
        """
        held = self.ledger.held_symbols()
        open_slots = MAX_POSITIONS - len(held)
        if open_slots <= 0 or not signals:
            return []

        # Rank new candidates by setup score (technical factor), best first.
        fresh = [s for s in signals if s.symbol not in held]
        fresh.sort(key=lambda s: s.signals.technical.score, reverse=True)
        fresh = fresh[:open_slots]
        if not fresh:
            return []

        prices_today = {s.symbol: self._today_close(s.symbol, date) for s in fresh}
        total_value = self.ledger.total_value(
            {s: p for s, p in prices_today.items() if p is not None}
        )
        target_capital = total_value / MAX_POSITIONS  # equal-weight slug

        if self.sector_gate is None:
            return [(signal, target_capital) for signal in fresh]

        # Apply the macro→sector gate: filter/veto drops entries, weight scales the
        # slug by the appetite factor. None analysis → gate is a no-op.
        analysis = self._macro_for(date)
        plans: list[tuple] = []
        for signal in fresh:
            sector = self.sector_map.get(signal.symbol, "")
            g = apply_sector_gate(signal.confidence, sector, analysis, self.sector_gate)
            if not g.keep:
                continue
            cap = target_capital
            if self.sector_gate.mode == "weight" and signal.confidence > 0:
                cap = target_capital * (g.adjusted_confidence / signal.confidence)
            plans.append((signal, cap))
        return plans

    # ---------- macro view (monthly-cached) ----------

    def _macro_for(self, date: pd.Timestamp) -> MacroSectorAnalysis | None:
        if self.macro_provider is None:
            return None
        key = date.strftime("%Y-%m")
        if key not in self._macro_cache:
            self._macro_cache[key] = self.macro_provider(date.strftime("%Y-%m-%d"))
        return self._macro_cache[key]
