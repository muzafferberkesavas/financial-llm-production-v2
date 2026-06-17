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
from finllm.portfolio.models import ExitReason
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
        mom_lookback: int = 252,
        mom_skip: int = 21,
        target_mult: float = 4.0,
        stop_mult: float = 2.5,
        holding_max: int = 20,
        min_52wh_prox: float = -1.0,
        trail_mult: float = 0.0,
        be_activate: float = 0.0,
        max_positions: int = MAX_POSITIONS,
        sizing_mode: str = "equal",   # equal | conviction | inverse_atr
        risk_pct: float = 0.02,       # per-trade equity risk for inverse_atr
        max_pos_pct: float = 0.35,    # cap any single position at this fraction
        vol_target: float = 0.0,      # annualized target vol for exposure scaling (0=off)
        vol_lookback: int = 20,       # bars of realized vol to estimate the regime
        sector_map: dict[str, str] | None = None,
        market: str = "nasdaq",
    ):
        super().__init__(config)
        self.min_setup_score = min_setup_score
        self.target_mult = target_mult
        self.stop_mult = stop_mult
        self.holding_max = holding_max
        self.min_52wh_prox = min_52wh_prox
        self.max_positions = max(1, max_positions)
        self.sizing_mode = sizing_mode
        self.risk_pct = risk_pct
        self.max_pos_pct = max_pos_pct
        # Portfolio inverse-vol scaling (Barroso & Santa-Clara): when the market's
        # realized vol spikes above target, cut total exposure (hold cash); when calm,
        # deploy fully. Lifts Sharpe and cuts crashes without touching stock selection.
        self.vol_target = vol_target
        self.vol_lookback = vol_lookback
        # Chandelier trailing stop: once a position runs up, ratchet the stop to
        # (highest-high-since-entry − trail_mult·ATR). 0 = off (fixed stop only).
        self.trail_mult = max(0.0, trail_mult)
        # Profit-activated breakeven: the trail engages ONLY after peak gain reaches
        # be_activate (e.g. 0.03 = +3%), and then never lets the stop fall below the
        # entry price. This fixes the two biggest leaks the path analysis found:
        # MAX_HOLDING giving back gains (+5% MFE → +1% close) and STOP whipsaw
        # (stopped on noise, then +6.7% bounce). Unlike a from-entry chandelier
        # (which cut winners on noise), this only arms once the trade is truly green.
        self.be_activate = max(0.0, be_activate)
        self.use_regime = use_regime
        self.regime_long_period = regime_long_period
        # Cross-sectional 12-1m momentum blended into the slot-selection ranking
        # (signal research #4 — a replicated factor). 0 = setup-only baseline. The
        # point: across a 500-name universe, setup score alone picks the wrong 7;
        # a proven cross-sectional factor should improve which names win the slots.
        self.rank_momentum_weight = max(0.0, min(1.0, rank_momentum_weight))
        # Lookback/skip for the selection-momentum. Default 252/21 = 12-1m, but trade
        # forensics showed 12-1m barely separates winners from losers (Cohen's d 0.09)
        # while SHORT momentum (~20d) does (d 0.53). Tunable so we can rank on the
        # signal that actually discriminates.
        self.mom_lookback = mom_lookback
        self.mom_skip = mom_skip
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

    def _vol_scalar(self, date: pd.Timestamp) -> float:
        """Exposure multiplier in [0,1] = target_vol / market_realized_vol, capped at 1
        (no leverage). High realized vol → smaller positions / more cash."""
        if self.vol_target <= 0 or self.regime_prices is None:
            return 1.0
        window = self.regime_prices.loc[self.regime_prices.index <= date]
        if len(window) < self.vol_lookback + 1:
            return 1.0
        rets = window["close"].pct_change().dropna().iloc[-self.vol_lookback:]
        realized = float(rets.std() * (252 ** 0.5))
        if realized <= 0:
            return 1.0
        return max(0.0, min(1.0, self.vol_target / realized))

    # ---------- exits (override: add chandelier trailing stop) ----------

    def _check_exits(self, date: pd.Timestamp) -> None:
        if self.trail_mult <= 0:
            return super()._check_exits(date)
        from finllm.backtest.strategy_signals import _atr
        from finllm.portfolio.exits import evaluate_exit

        for sym, pos in self.ledger.as_position_models().items():
            bar = self._today_bar(sym, date)
            if bar is None:
                continue
            high, low, close = float(bar["high"]), float(bar["low"]), float(bar["close"])

            # Ratchet the stop up via chandelier (never below the original stop).
            eff_stop = pos.stop_loss
            p = self.prices.get(sym)
            if p is not None:
                window = p.loc[(p.index >= pos.entry_date) & (p.index <= date)]
                atr = _atr(p.loc[p.index <= date])
                if not window.empty and atr:
                    hh = float(window["high"].max())
                    peak_gain = (hh - pos.entry_price) / pos.entry_price
                    # If be_activate is set, arm the trail only once peak gain clears
                    # it, and floor the stop at breakeven (entry). Otherwise trail
                    # from entry (legacy behavior).
                    if self.be_activate <= 0 or peak_gain >= self.be_activate:
                        trail = hh - self.trail_mult * atr
                        floor = pos.entry_price if self.be_activate > 0 else None
                        cand = max(trail, floor) if floor is not None else trail
                        if eff_stop is None or cand > eff_stop:
                            eff_stop = cand

            exit_reason: ExitReason | None = None
            exit_price: float | None = None
            if eff_stop is not None and low <= eff_stop:
                exit_reason = "STOP_HIT"
                exit_price = eff_stop
            elif pos.target_price is not None and high >= pos.target_price:
                exit_reason = "TARGET_HIT"
                exit_price = pos.target_price
            else:
                decision = evaluate_exit(pos, close, new_signal=None, now=date.to_pydatetime())
                if decision.should_exit:
                    exit_reason = decision.reason
                    exit_price = close

            if exit_reason is not None and exit_price is not None:
                self.ledger.close_position(sym, exit_price, date.to_pydatetime(), exit_reason)

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
                sym, window, date.to_pydatetime(), self.thresholds, self.min_setup_score,
                target_mult=self.target_mult, stop_mult=self.stop_mult,
                holding_max=self.holding_max, min_52wh_prox=self.min_52wh_prox,
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
        open_slots = self.max_positions - len(held)
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
        cap_ceiling = total_value * self.max_pos_pct
        vol_scalar = self._vol_scalar(date)  # ≤1: shrink exposure in high-vol regimes

        def _slug(signal) -> float:
            """Capital for one position under the active sizing mode (capped)."""
            equal = total_value / self.max_positions * vol_scalar
            if self.sizing_mode == "inverse_atr":
                # Equal-RISK: each trade risks risk_pct of equity at its stop. A
                # tight-ATR name gets more capital, a wide-ATR name less.
                entry, stop = signal.entryPrice, signal.stopLoss
                if entry and stop and entry > stop:
                    stop_frac = (entry - stop) / entry
                    return min(cap_ceiling, total_value * self.risk_pct * vol_scalar / stop_frac)
                return min(cap_ceiling, equal)
            if self.sizing_mode == "conviction":
                # Tilt toward higher-momentum names: 0.6×–1.6× the equal slug by the
                # candidate's cross-sectional momentum percentile.
                ser = self._mom_series(signal.symbol) if self.rank_momentum_weight > 0 else None
                pct = 0.5
                if ser is not None:
                    hits = ser.loc[ser.index <= date]
                    if not hits.empty and pd.notna(hits.iloc[-1]):
                        vals = sorted(v for s2 in fresh
                                      for v in [self._mom_at(s2.symbol, date)] if v is not None)
                        v = float(hits.iloc[-1])
                        pct = (sum(1 for x in vals if x <= v) / len(vals)) if vals else 0.5
                return min(cap_ceiling, equal * (0.6 + pct))
            return equal  # equal-weight

        if self.sector_gate is None:
            return [(signal, _slug(signal)) for signal in fresh]
        target_capital = total_value / self.max_positions

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
            p = self.prices.get(sym)
            if p is None:
                return None
            c = p["close"]
            # mom[t] = close[t-skip] / close[t-(lookback-1)] - 1
            s = c.shift(self.mom_skip) / c.shift(max(1, self.mom_lookback - 1)) - 1.0
            self._mom_cache[sym] = s
        return s

    def _mom_at(self, sym: str, date: pd.Timestamp) -> float | None:
        ser = self._mom_series(sym)
        if ser is None:
            return None
        hits = ser.loc[ser.index <= date]
        if hits.empty or pd.isna(hits.iloc[-1]):
            return None
        return float(hits.iloc[-1])

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
