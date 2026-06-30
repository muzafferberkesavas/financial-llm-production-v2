"""TREND kategorisi — 9 kriter, ~46 puan."""
from __future__ import annotations

from finllm.indicators.scorecard._helpers import _g
from finllm.indicators.scorecard._registry import criterion
from finllm.indicators.scorecard._types import ScoringContext


@criterion("weekly_trend_direction", "TREND", 6)
def c01_weekly_trend(ctx: ScoringContext) -> tuple[int, str]:
    wt = ctx.ind.get("weekly_trend")
    if wt is None:
        return 0, "N/A"
    mapping = {"UPTREND": 6, "EARLY_RECOVERY": 4, "SIDEWAYS": 2, "EARLY_WEAKNESS": 0, "DOWNTREND": 0}
    s = mapping.get(wt, 0)
    return s, f"{wt} -> {s}/6"


@criterion("price_vs_sma200", "TREND", 5)
def c02_price_vs_sma200(ctx: ScoringContext) -> tuple[int, str]:
    v = _g(ctx.ind, "price_vs_sma200")
    if v is None:
        return 0, "N/A"
    if v > 0.10:
        s = 5
    elif v > 0.03:
        s = 4
    elif v > 0:
        s = 3
    elif v > -0.05:
        s = 1
    else:
        s = 0
    return s, f"{v:+.3f} -> {s}/5"


@criterion("sma50_vs_sma200", "TREND", 4)
def c03_golden_cross(ctx: ScoringContext) -> tuple[int, str]:
    v = _g(ctx.ind, "sma50_vs_sma200")
    if v is None:
        return 0, "N/A"
    if v > 0.05:
        s = 4
    elif v > 0:
        s = 3
    elif v > -0.02:
        s = 2
    else:
        s = 0
    return s, f"{v:+.3f} -> {s}/4"


@criterion("adx_trend_strength", "TREND", 5)
def c04_adx(ctx: ScoringContext) -> tuple[int, str]:
    v = _g(ctx.ind, "adx_14")
    if v is None:
        return 0, "N/A"
    if v >= 35:
        s = 5
    elif v >= 25:
        s = 4
    elif v >= 20:
        s = 2
    else:
        s = 0
    return s, f"{v:.1f} -> {s}/5"


@criterion("supertrend_direction", "TREND", 3)
def c05_supertrend(ctx: ScoringContext) -> tuple[int, str]:
    v = _g(ctx.ind, "supertrend_dir")
    if v is None:
        return 0, "N/A"
    s = 3 if v == 1 else 0
    return s, f"{v} -> {s}/3"


@criterion("ichimoku_cloud", "TREND", 5)
def c06_ichimoku(ctx: ScoringContext) -> tuple[int, str]:
    v = _g(ctx.ind, "ichi_signal")
    if v is None:
        return 0, "N/A"
    if v == 1:
        s = 5
    elif v == 0:
        s = 2
    else:
        s = 0
    return s, f"{v} -> {s}/5"


@criterion("aroon_oscillator", "TREND", 4)
def c07_aroon(ctx: ScoringContext) -> tuple[int, str]:
    v = _g(ctx.ind, "aroon_osc")
    if v is None:
        return 0, "N/A"
    if v > 60:
        s = 4
    elif v > 30:
        s = 3
    elif v > 0:
        s = 2
    else:
        s = 0
    return s, f"{v:.0f} -> {s}/4"


@criterion("close_vs_ema21", "TREND", 4)
def c52_close_vs_ema21(ctx: ScoringContext) -> tuple[int, str]:
    close = _g(ctx.ind, "close")
    ema21 = _g(ctx.ind, "ema21")
    if close is None or ema21 is None or ema21 == 0:
        return 0, "N/A"
    pct = (close - ema21) / ema21 * 100
    if pct > 3.0:
        s = 4
    elif pct > 1.0:
        s = 3
    elif pct > 0:
        s = 2
    elif pct > -2.0:
        s = 1
    else:
        s = 0
    return s, f"{pct:+.2f}% -> {s}/4"


@criterion("close_vs_ema50", "TREND", 4)
def c53_close_vs_ema50(ctx: ScoringContext) -> tuple[int, str]:
    close = _g(ctx.ind, "close")
    ema50 = _g(ctx.ind, "ema50")
    if close is None or ema50 is None or ema50 == 0:
        return 0, "N/A"
    pct = (close - ema50) / ema50 * 100
    if pct > 5.0:
        s = 4
    elif pct > 2.0:
        s = 3
    elif pct > 0:
        s = 2
    elif pct > -3.0:
        s = 1
    else:
        s = 0
    return s, f"{pct:+.2f}% -> {s}/4"
