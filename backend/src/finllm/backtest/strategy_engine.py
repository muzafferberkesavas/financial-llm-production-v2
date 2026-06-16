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
# Per-market regime benchmark for the backtest's trend gate (Faz E).
REGIME_BY_MARKET = {"nasdaq": "QQQ", "bist": "XU100.IS"}
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
        fundamental_provider: Callable[[str, str], "float | None"] | None = None,
        fundamental_weight: float = 0.0,
        rank_momentum_weight: float = 0.0,
        sector_map: dict[str, str] | None = None,
        market: str = "nasdaq",
    ):
        super().__init__(config)
        self.min_setup_score = min_setup_score
        self.use_regime = use_regime
        self.regime_long_period = regime_long_period
        # Cross-sectional 12-1m momentum blended into the slot-selection ranking
        # (signal research #4 — a replicated factor). 0 = setup-only baseline. The
        # point: across a 500-name universe, setup score alone picks the wrong 7;
        # a proven cross-sectional factor should improve which names win the slots.
        self.rank_momentum_weight = max(0.0, min(1.0, rank_momentum_weight))
        self._mom_cache: dict[str, pd.Series] = {}
        self.market = market
        self.thresholds = get_adapter(market).thresholds
        self.regime_symbol = REGIME_BY_MARKET.get(market, REGIME_SYMBOL)
        self.regime_prices: pd.DataFrame | None = None
        self._regime_cache: dict[pd.Timestamp, bool] = {}

        # Fundamental ranking overlay (Faz B.3 / full-stack backtest): re-rank the
        # candidates competing for the limited slots by a blend of technical setup
        # and the point-in-time fundamental composite. weight 0 = setup-only baseline.
        self.fundamental_provider = fundamental_provider
        self.fundamental_weight = max(0.0, min(1.0, fundamental_weight))

        # Macro→sector gate (Faz B.3). Active only when both a config and a
        # provider are supplied; macro views are cached per calendar month so a
        # 3-year backtest costs ~36 LLM calls, not one per trading day.
        self.sector_gate = sector_gate
        self.macro_provider = macro_provider
        # sector_map override lets a broader (non-NASDAQ_ALL) universe carry its
        # own symbol→sector mapping for the macro gate.
        if sector_map is not None:
            self.sector_map = sector_map
        else:
            self.sector_map = build_sector_map() if sector_gate else {}
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
            qqq = fetch_prices(self.regime_symbol, start=warmup_start, end=end_str, use_cache=True)
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

        # Rank new candidates for the limited slots. Baseline = setup score; with a
        # fundamental overlay, blend in the point-in-time fundamental composite.
        fresh = [s for s in signals if s.symbol not in held]
        if self.fundamental_weight > 0 and self.fundamental_provider is not None:
            as_of = date.strftime("%Y-%m-%d")
            fw = self.fundamental_weight

            def _combined(s) -> float:
                setup = s.signals.technical.score
                comp = self.fundamental_provider(s.symbol, as_of)
                comp_norm = (comp / 100.0) if comp is not None else 0.5
                return (1.0 - fw) * setup + fw * comp_norm

            fresh.sort(key=_combined, reverse=True)
        elif self.rank_momentum_weight > 0:
            fresh.sort(key=self._setup_momentum_key(fresh, date), reverse=True)
        else:
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

    def _mom_series(self, sym: str) -> pd.Series | None:
        """12-1m momentum for EVERY bar of a symbol, computed once (vectorized) and
        cached. mom[t] = close[t-SKIP] / close[t-(LOOKBACK-1)] - 1, matching
        indicators.momentum.momentum_12_1 (end = skip last month, start ≈ 12m ago).
        Causal: shift() only looks backward, so a date's value uses no future bar."""
        s = self._mom_cache.get(sym)
        if s is None:
            from finllm.indicators.momentum import LOOKBACK, SKIP

            p = self.prices.get(sym)
            if p is None:
                return None
            c = p["close"]
            s = c.shift(SKIP) / c.shift(LOOKBACK - 1) - 1.0
            self._mom_cache[sym] = s
        return s

    def _setup_momentum_key(self, fresh: list, date: pd.Timestamp):
        """Rank key = (1-w)·setup + w·(cross-sectional 12-1m momentum percentile).

        Momentum is ranked as a PERCENTILE *within today's candidate set* (not an
        absolute threshold) so it adds the factor without overfitting a magnitude —
        exactly the disciplined-factor construction the research calls for.
        """
        w = self.rank_momentum_weight
        moms: dict[str, float | None] = {}
        for s in fresh:
            ser = self._mom_series(s.symbol)
            val = None
            if ser is not None:
                hits = ser.loc[ser.index <= date]
                if not hits.empty:
                    v = hits.iloc[-1]
                    val = float(v) if pd.notna(v) else None
            moms[s.symbol] = val
        valid = sorted(v for v in moms.values() if v is not None)

        def _pct(x: float | None) -> float:
            if x is None or not valid:
                return 0.5
            return sum(1 for v in valid if v <= x) / len(valid)

        return lambda s: (1.0 - w) * s.signals.technical.score + w * _pct(moms[s.symbol])

    # ---------- macro view (monthly-cached) ----------

    def _macro_for(self, date: pd.Timestamp) -> MacroSectorAnalysis | None:
        if self.macro_provider is None:
            return None
        key = date.strftime("%Y-%m")
        if key not in self._macro_cache:
            self._macro_cache[key] = self.macro_provider(date.strftime("%Y-%m-%d"))
        return self._macro_cache[key]
