"""Deterministic technical-only signal generator for backtesting.

Mirrors the scoring logic in `signals/generator.py::_technical_snapshot`
so backtests use the same rule-based score that ships into production
prompts. No LLM, no news API — pure functions over a feature frame.

Targets/stops derived from ATR (2:1 reward:risk).
"""
from __future__ import annotations

import math
from datetime import datetime

import pandas as pd

from finllm.signals.schema import FactorScore, HoldingDays, Signal, SignalFactors

# Same thresholds the production sizer uses (sizing.py)
BUY_SCORE_THRESHOLD = 0.25
SELL_SCORE_THRESHOLD = -0.25

# ATR multiples for target/stop. 2:1 R:R is the swing-trade default.
ATR_STOP_MULT = 2.0
ATR_TARGET_MULT = 4.0

DEFAULT_HOLDING_MIN = 3
DEFAULT_HOLDING_MAX = 15


def _safe(row: pd.Series, key: str) -> float | None:
    v = row.get(key)
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(f):
        return None
    return f


def score_technical(feats_row: pd.Series) -> float:
    """Rule-based score in [-1, 1] from the last feature row.

    Mirrors signals/generator.py::_technical_snapshot. Keep in sync if you
    change weights there — backtest results become meaningless otherwise.
    """
    score = 0.0
    weights = 0

    rsi = _safe(feats_row, "rsi_14")
    if rsi is not None:
        score += (50 - rsi) / 50
        weights += 1

    macd_hist = _safe(feats_row, "macd_hist")
    if macd_hist is not None:
        score += 1.0 if macd_hist > 0 else -1.0
        weights += 1

    pvs50 = _safe(feats_row, "price_vs_sma50")
    if pvs50 is not None:
        score += min(max(pvs50 * 5, -1), 1)
        weights += 1

    adx = _safe(feats_row, "adx_14")
    di_plus = _safe(feats_row, "di_plus")
    di_minus = _safe(feats_row, "di_minus")
    if adx is not None and di_plus is not None and di_minus is not None:
        trend = (di_plus - di_minus) / 100
        strength = min(adx / 50, 1.0)
        score += trend * strength
        weights += 1

    out = score / max(weights, 1)
    return max(-1.0, min(1.0, out))


def technical_signal(
    symbol: str,
    feats: pd.DataFrame,
    now: datetime,
) -> Signal | None:
    """Build a Signal from a feature frame ending at `now`.

    Returns None if there's no usable row (e.g. all-NaN early in history).
    """
    if feats.empty:
        return None

    row = feats.iloc[-1]
    close = _safe(row, "close")
    atr = _safe(row, "atr_14")
    if close is None or atr is None or atr <= 0:
        return None

    tech_score = score_technical(row)

    if tech_score >= BUY_SCORE_THRESHOLD:
        direction = "BUY"
    elif tech_score <= SELL_SCORE_THRESHOLD:
        direction = "SELL"
    else:
        direction = "HOLD"

    # Confidence: magnitude of tech_score mapped to [0.5, 1.0] so BUY signals
    # above threshold start at 0.5 confidence. Below 0.6 they're filtered by
    # the sizer's MIN_CONFIDENCE — that's intentional, weak signals stay out.
    confidence = 0.5 + 0.5 * min(abs(tech_score), 1.0)

    if direction == "BUY":
        stop = close - ATR_STOP_MULT * atr
        target = close + ATR_TARGET_MULT * atr
    elif direction == "SELL":
        stop = close + ATR_STOP_MULT * atr
        target = close - ATR_TARGET_MULT * atr
    else:
        stop = None
        target = None

    expected_return = None
    if target is not None and close > 0:
        expected_return = (target - close) / close

    return Signal(
        symbol=symbol,
        direction=direction,
        confidence=confidence,
        holdingDays=HoldingDays(min=DEFAULT_HOLDING_MIN, max=DEFAULT_HOLDING_MAX),
        entryPrice=close,
        targetPrice=target,
        stopLoss=stop,
        expectedReturn=expected_return,
        rationale=f"Technical score {tech_score:+.2f}",
        riskFactors=[],
        signals=SignalFactors(
            technical=FactorScore(score=tech_score, notes=""),
            sentiment=FactorScore(score=0.0, notes="backtest: no news"),
        ),
        generatedAt=now,
    )
