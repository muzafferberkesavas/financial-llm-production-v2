"""MOMENTUM kategorisi — 9 kriter, ~37 puan.

c14 CCI cikarildi (RSI/Stoch/WillR ile korelasyon).
c66 indicator_momentum ve c67 rsi_trajectory eklendi.
"""
from __future__ import annotations

from finllm.indicators.scorecard._helpers import _g
from finllm.indicators.scorecard._registry import criterion
from finllm.indicators.scorecard._slope_helpers import indicator_slope, slopes_rising_count
from finllm.indicators.scorecard._types import ScoringContext


@criterion("rsi_sweet_spot", "MOMENTUM", 5)
def c08_rsi_sweet(ctx: ScoringContext) -> tuple[int, str]:
    v = _g(ctx.ind, "rsi_14")
    if v is None:
        return 0, "N/A"
    prev_rsi = _g(ctx.ind, "prev_rsi_14")
    rising = prev_rsi is not None and v > prev_rsi
    if 50 <= v <= 65:
        s = 5 if rising else 4
    elif 40 <= v < 50:
        s = 4 if rising else 3
    elif 65 < v <= 70:
        s = 3
    elif 30 <= v < 40:
        s = 4 if rising else 2
    elif v < 30:
        s = 3 if rising else 1
    else:
        s = 0
    arrow = "^" if rising else "v" if prev_rsi and not rising else "?"
    return s, f"{v:.1f} {arrow} -> {s}/5"


@criterion("macd_histogram", "MOMENTUM", 5)
def c09_macd_hist(ctx: ScoringContext) -> tuple[int, str]:
    hist = _g(ctx.ind, "macd_hist")
    if hist is None:
        return 0, "N/A"
    prev_hist = _g(ctx.ind, "prev_macd_hist")
    if hist > 0:
        if prev_hist is not None and prev_hist <= 0:
            s = 5
        elif prev_hist is not None and hist > prev_hist:
            s = 4
        else:
            s = 3
    elif hist < 0:
        if prev_hist is not None and hist > prev_hist:
            s = 2
        else:
            s = 0
    else:
        s = 1
    cross_tag = f" prev={prev_hist:.3f}" if prev_hist is not None else ""
    return s, f"hist={hist:.3f}{cross_tag} -> {s}/5"


@criterion("stochastic", "MOMENTUM", 5)
def c10_stochastic(ctx: ScoringContext) -> tuple[int, str]:
    k = _g(ctx.ind, "stoch_k")
    d = _g(ctx.ind, "stoch_d")
    if k is None:
        return 0, "N/A"
    if d is not None:
        if k > d and 20 <= k <= 80:
            s = 4
        elif k < 20 and k > d:
            s = 5
        elif k > 80:
            s = 1
        elif k < 20:
            s = 0
        else:
            s = 2
    else:
        s = 2
    return s, f"K={k:.0f} D={d if d else '-'} -> {s}/5"


@criterion("roc_10", "MOMENTUM", 4)
def c11_roc(ctx: ScoringContext) -> tuple[int, str]:
    v = _g(ctx.ind, "roc_10")
    if v is None:
        return 0, "N/A"
    prev_roc = _g(ctx.ind, "prev_roc_10")
    accelerating = prev_roc is not None and v > prev_roc
    if 3 <= v <= 10:
        s = 4
    elif 1 <= v < 3:
        s = 4 if accelerating else 3
    elif 10 < v <= 15:
        s = 2
    elif v > 15:
        s = 1
    elif v < 0 and accelerating:
        s = 1
    else:
        s = 0
    accel_tag = " ^accel" if accelerating else ""
    return s, f"{v:.1f}%{accel_tag} -> {s}/4"


@criterion("williams_r", "MOMENTUM", 4)
def c12_williams_r(ctx: ScoringContext) -> tuple[int, str]:
    v = _g(ctx.ind, "willr_14")
    if v is None:
        return 0, "N/A"
    if -50 <= v <= -20:
        s = 4
    elif -80 <= v < -50:
        s = 3
    elif v > -20:
        s = 1
    elif v < -80:
        s = 2
    else:
        s = 0
    return s, f"{v:.0f} -> {s}/4"


@criterion("weekly_rsi", "MOMENTUM", 4)
def c13_weekly_rsi(ctx: ScoringContext) -> tuple[int, str]:
    v = _g(ctx.ind, "weekly_rsi")
    if v is None:
        return 0, "N/A"
    if 50 <= v <= 70:
        s = 4
    elif 40 <= v < 50:
        s = 3
    elif v > 70:
        s = 1
    else:
        s = 0
    return s, f"{v:.1f} -> {s}/4"


@criterion("green_day", "MOMENTUM", 3)
def c51_green_day(ctx: ScoringContext) -> tuple[int, str]:
    close = _g(ctx.ind, "close")
    prev_close = _g(ctx.ind, "prev_close")
    if close is None or prev_close is None or prev_close == 0:
        return 0, "N/A"
    chg_pct = (close - prev_close) / prev_close * 100
    if chg_pct > 2.0:
        s = 3
    elif chg_pct > 0.5:
        s = 2
    elif chg_pct > 0:
        s = 1
    else:
        s = 0
    return s, f"chg={chg_pct:+.2f}% -> {s}/3"


@criterion("indicator_momentum", "MOMENTUM", 4)
def c66_indicator_momentum(ctx: ScoringContext) -> tuple[int, str]:
    """RSI/ADX/MACD 5-bar slope yon sayisi."""
    rsi_vals = ctx.ind.get("rsi_14_series")
    adx_vals = ctx.ind.get("adx_14_series")
    macd_vals = ctx.ind.get("macd_hist_series")

    slopes = {
        "rsi": indicator_slope(rsi_vals, 5),
        "adx": indicator_slope(adx_vals, 5),
        "macd": indicator_slope(macd_vals, 5),
    }

    # Fallback: use single-value slope indicators if series not available
    if slopes["rsi"] is None:
        slopes["rsi"] = _g(ctx.ind, "rsi_slope_5")
    if slopes["adx"] is None:
        slopes["adx"] = _g(ctx.ind, "adx_slope_5")
    if slopes["macd"] is None:
        slopes["macd"] = _g(ctx.ind, "macd_slope_5")

    rising = slopes_rising_count(slopes)
    if rising >= 3:
        s = 4
    elif rising == 2:
        s = 3
    elif rising == 1:
        s = 1
    else:
        s = 0
    return s, f"{rising}/3 rising -> {s}/4"


@criterion("rsi_trajectory", "MOMENTUM", 4)
def c67_rsi_trajectory(ctx: ScoringContext) -> tuple[int, str]:
    """RSI 10-bar slope + bolge."""
    rsi = _g(ctx.ind, "rsi_14")
    rsi_slope = _g(ctx.ind, "rsi_slope_10")
    if rsi is None:
        return 0, "N/A"
    if rsi_slope is None:
        # Fallback: use prev_rsi direction
        prev = _g(ctx.ind, "prev_rsi_14")
        if prev is not None:
            rsi_slope = rsi - prev
        else:
            return 0, "N/A (no slope)"

    rising = rsi_slope > 0
    if 40 <= rsi <= 65 and rising:
        s = 4
    elif 30 <= rsi < 40 and rising:
        s = 3  # recovery
    elif 50 <= rsi <= 70 and not rising:
        s = 2  # still in zone but weakening
    elif rising:
        s = 1
    else:
        s = 0
    arrow = "^" if rising else "v"
    return s, f"RSI={rsi:.1f} slope={rsi_slope:.2f}{arrow} -> {s}/4"
