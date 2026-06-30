"""RISK kategorisi — 3 kriter, ~11 puan.

c44 basic R:R -> c76 Fibonacci S/R bazli R:R ile degistirildi.
c47 neg_div_penalty cikarildi (volume'den zaten cikti).
"""
from __future__ import annotations

from finllm.indicators.scorecard._helpers import _g
from finllm.indicators.scorecard._registry import criterion
from finllm.indicators.scorecard._sr_helpers import find_nearest_resistance, find_nearest_support
from finllm.indicators.scorecard._types import ScoringContext


@criterion("earnings_proximity", "RISK", 3)
def c45_earnings_proximity(ctx: ScoringContext) -> tuple[int, str]:
    snap = ctx.snap
    if snap is None or snap.days_to_earnings is None:
        return 2, "N/A (neutral)"
    dte = snap.days_to_earnings
    if dte > 30:
        s = 3
    elif dte > 15:
        s = 2
    elif dte > 5:
        s = 1
    else:
        s = 0
    return s, f"{dte}d -> {s}/3"


@criterion("volatility_fitness", "RISK", 3)
def c46_vol_fitness(ctx: ScoringContext) -> tuple[int, str]:
    vol20 = _g(ctx.ind, "vol_20d")
    atr_pct = _g(ctx.ind, "atr_pct")
    if vol20 is None or atr_pct is None:
        return 0, "N/A"
    atr_p = atr_pct * 100 if atr_pct < 1 else atr_pct
    if 0.15 <= vol20 <= 0.40 and 1.5 <= atr_p <= 5:
        s = 3
    elif 0.10 <= vol20 <= 0.50 and 1 <= atr_p <= 7:
        s = 2
    else:
        s = 0
    return s, f"vol20={vol20:.3f} atr={atr_p:.1f}% -> {s}/3"


@criterion("rr_sr_based", "RISK", 5)
def c76_rr_sr_based(ctx: ScoringContext) -> tuple[int, str]:
    """Fibonacci S/R bazli risk:reward orani."""
    close = _g(ctx.ind, "close")
    supports = ctx.ind.get("fib_supports")
    resistances = ctx.ind.get("fib_resistances")

    if close is None:
        return 0, "N/A"

    # Fallback to swing levels if no Fibonacci data
    if not supports or not resistances:
        sh = _g(ctx.ind, "swing_high_20")
        sl = _g(ctx.ind, "swing_low_20")
        if sh is None or sl is None:
            return 0, "N/A"
        upside = sh - close
        downside = close - sl
        if downside <= 0:
            s = 5
            return s, f"at/below support R:R=inf -> {s}/5"
        rr = upside / downside
    else:
        _, sup_dist = find_nearest_support(close, supports)
        _, res_dist = find_nearest_resistance(close, resistances)
        if sup_dist is None or res_dist is None or sup_dist == 0:
            return 0, "N/A"
        rr = res_dist / sup_dist  # upside potential / downside risk

    if rr > 4:
        s = 5
    elif rr > 3:
        s = 4
    elif rr > 2:
        s = 3
    elif rr > 1.5:
        s = 2
    elif rr > 1:
        s = 1
    else:
        s = 0
    return s, f"R:R={rr:.1f} -> {s}/5"
