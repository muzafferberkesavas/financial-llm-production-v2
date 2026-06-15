"""Backtest signal generator that runs the REAL production strategy.

Unlike `backtest/signals.py` — a generic RSI/MACD/ADX blend — this module
exercises the same edge the live funnel trades:

  * Stage 1 hard filter (TradingView clone): price, green day, ADR%, avg
    volume, daily $ volume, close > EMA21 and close > EMA50.
  * Stage 1B setup detection: pullback-to-EMA / bull-flag / breakout, scored
    0..1 by the exact same detectors the live pipeline uses.
  * A QQQ trend-regime gate (applied by the engine, not here): only generate
    new entries while QQQ is in an uptrend, mirroring the user's manual flow.

So a backtest built on this module actually measures the user's strategy.

Look-ahead safety: every function reads only `prices` up to and including the
current bar. No forward bars are referenced.

Market-cap caveat: the live Stage 1 filter also requires market_cap >= $300M.
That snapshot isn't available point-in-time from yfinance, so it is *skipped*
here. The backtest universe is the curated large/mega-cap NASDAQ list, where
the cap floor is effectively always satisfied — skipping it does not loosen
the test in practice.
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd

from finllm.markets.base import FilterThresholds
from finllm.pipeline.stage1_filter import _compute_adr_pct, _compute_ema
from finllm.pipeline.stage1b_setup import _best_setup
from finllm.signals.schema import (
    FactorScore,
    HoldingDays,
    Signal,
    SignalFactors,
)

# Swing exit geometry — 2:1 reward:risk on ATR, <1-month horizon.
ATR_STOP_MULT = 2.0
ATR_TARGET_MULT = 4.0
DEFAULT_HOLDING_MIN = 3
DEFAULT_HOLDING_MAX = 20      # ~1 trading month, matches the "<1 ay" target

# Minimum bars needed to evaluate EMA50 + 20-bar ADR + setup windows.
MIN_BARS = 60


def passes_hard_filter(
    prices: pd.DataFrame,
    thresholds: FilterThresholds,
) -> tuple[bool, dict]:
    """Price-only mirror of Stage 1 (`stage1_filter._check_one`).

    Returns (passed, indicators). market_cap is intentionally omitted (see
    module docstring). Keep the checks here in sync with stage1_filter.py.
    """
    if len(prices) < MIN_BARS:
        return False, {"reason": f"insufficient_history ({len(prices)})"}

    latest = prices.iloc[-1]
    close = float(latest["close"])
    prev_close = float(prices["close"].iloc[-2])

    # 1. Min price
    if close < thresholds.min_price:
        return False, {"reason": "price"}

    # 2. Green day
    if thresholds.require_green_day and close <= prev_close:
        return False, {"reason": "not_green"}

    # 3. Avg volume 10d
    avg_vol_10d = float(prices["volume"].tail(10).mean())
    if avg_vol_10d < thresholds.min_avg_volume_10d:
        return False, {"reason": "avg_vol"}

    # 4. Daily $ volume
    today_vol = float(latest["volume"]) if not pd.isna(latest["volume"]) else 0.0
    daily_dollar = today_vol * close
    if daily_dollar < thresholds.min_daily_dollar_volume:
        return False, {"reason": "daily_dollar"}

    # 5. ADR%
    adr = _compute_adr_pct(prices, period=20)
    if adr < thresholds.min_adr_pct:
        return False, {"reason": "adr"}

    # 6. EMA21 / EMA50 uptrend
    closes = prices["close"]
    ema21 = _compute_ema(closes, 21)
    ema50 = _compute_ema(closes, 50)
    if thresholds.require_close_above_ema21:
        if ema21 is None or close <= ema21:
            return False, {"reason": "ema21"}
    if thresholds.require_close_above_ema50:
        if ema50 is None or close <= ema50:
            return False, {"reason": "ema50"}

    return True, {
        "close": close,
        "ema21": ema21,
        "ema50": ema50,
        "adr_pct": adr,
        "avg_vol_10d": avg_vol_10d,
    }


def _atr(prices: pd.DataFrame, period: int = 14) -> float | None:
    """Wilder ATR on the last bar, computed from raw OHLC (causal)."""
    if len(prices) < period + 1:
        return None
    high = prices["high"]
    low = prices["low"]
    close = prices["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    atr = tr.ewm(alpha=1 / period, adjust=False).mean().iloc[-1]
    val = float(atr)
    return val if val > 0 else None


def strategy_signal(
    symbol: str,
    prices: pd.DataFrame,
    now: datetime,
    thresholds: FilterThresholds,
    min_setup_score: float = 0.5,
) -> Signal | None:
    """Emit a BUY Signal if `prices` (up to `now`) passes Stage 1 and shows a
    Stage 1B setup at or above `min_setup_score`. Otherwise None.

    Confidence maps setup score [min..1.0] → [0.60..1.0] so qualifying setups
    clear the sizer's MIN_CONFIDENCE floor; below-threshold setups never reach
    here. Stop/target are ATR-based (2:1 R:R).
    """
    passed, ind = passes_hard_filter(prices, thresholds)
    if not passed:
        return None

    ema21 = ind["ema21"]
    setup_type, score, meta = _best_setup(prices, ema21)
    if setup_type == "none" or score < min_setup_score:
        return None

    atr = _atr(prices)
    if atr is None:
        return None

    close = ind["close"]
    # score in [min_setup_score, 1.0] → confidence in [0.60, 1.0]
    span = max(1e-9, 1.0 - min_setup_score)
    confidence = 0.60 + 0.40 * min(max((score - min_setup_score) / span, 0.0), 1.0)

    stop = close - ATR_STOP_MULT * atr
    target = close + ATR_TARGET_MULT * atr
    expected_return = (target - close) / close if close > 0 else None

    return Signal(
        symbol=symbol,
        direction="BUY",
        confidence=confidence,
        holdingDays=HoldingDays(min=DEFAULT_HOLDING_MIN, max=DEFAULT_HOLDING_MAX),
        entryPrice=close,
        targetPrice=target,
        stopLoss=stop,
        expectedReturn=expected_return,
        rationale=f"{setup_type} setup score {score:.2f}",
        riskFactors=[],
        signals=SignalFactors(
            technical=FactorScore(score=score, notes=setup_type),
            sentiment=FactorScore(score=0.0, notes="backtest: no news"),
        ),
        generatedAt=now,
    )


# ---------- QQQ trend-regime gate ----------

def qqq_uptrend(qqq_prices: pd.DataFrame) -> bool:
    """True when QQQ is in an uptrend (not sideways/down) on the last bar.

    Definition mirrors the user's manual rule "QQQ yükseliş trendinde mi":
      * close > EMA21  (above short-term trend)
      * EMA21 > EMA50  (stacked, momentum up)
      * close today > close 20 bars ago  (positive medium-term slope)
    All three must hold. Causal — uses only bars up to today.
    """
    if len(qqq_prices) < 50:
        return False
    closes = qqq_prices["close"]
    close = float(closes.iloc[-1])
    ema21 = _compute_ema(closes, 21)
    ema50 = _compute_ema(closes, 50)
    if ema21 is None or ema50 is None:
        return False
    close_20_ago = float(closes.iloc[-21]) if len(closes) >= 21 else close
    return close > ema21 and ema21 > ema50 and close > close_20_ago
