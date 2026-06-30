"""FIYAT_YAPISI kategorisi — 8 kriter, ~38 puan.

c56 candlestick max 4->3 degisti, hacim teyidi zorunlu.
c72 support_proximity ve c73 resistance_distance eklendi.
"""
from __future__ import annotations

from finllm.indicators.scorecard._helpers import _g, _pct_from_52w_high
from finllm.indicators.scorecard._registry import criterion
from finllm.indicators.scorecard._sr_helpers import find_nearest_resistance, find_nearest_support
from finllm.indicators.scorecard._types import ScoringContext


@criterion("fibonacci_zone", "FIYAT_YAPISI", 5)
def c25_fib_zone(ctx: ScoringContext) -> tuple[int, str]:
    fz = ctx.ind.get("fib_zone")
    if fz is None:
        return 0, "N/A"
    fz_str = str(fz)
    if "healthy_pullback" in fz_str:
        s = 5
    elif "strong_zone" in fz_str:
        s = 4
    elif "critical_support" in fz_str:
        s = 4
    elif "breakout" in fz_str.lower():
        s = 3
    elif "deep_pullback" in fz_str:
        s = 2
    elif "danger" in fz_str or "broken" in fz_str:
        s = 0
    else:
        s = 2
    return s, f"{fz} -> {s}/5"


@criterion("price_vs_vwap", "FIYAT_YAPISI", 4)
def c26_price_vs_vwap(ctx: ScoringContext) -> tuple[int, str]:
    v = _g(ctx.ind, "price_vs_vwap")
    if v is None:
        return 0, "N/A"
    if 0 < v < 0.05:
        s = 4
    elif v >= 0.05:
        s = 3
    elif -0.02 <= v <= 0:
        s = 2
    else:
        s = 0
    return s, f"{v:+.3f} -> {s}/4"


@criterion("donchian_position", "FIYAT_YAPISI", 5)
def c27_donchian(ctx: ScoringContext) -> tuple[int, str]:
    v = _g(ctx.ind, "donch_pct")
    if v is None:
        return 0, "N/A"
    if 0.6 <= v <= 0.9:
        s = 5
    elif 0.4 <= v < 0.6:
        s = 3
    elif v > 0.95:
        s = 2
    elif v < 0.3:
        s = 0
    else:
        s = 2
    return s, f"{v:.2f} -> {s}/5"


@criterion("52w_high_proximity", "FIYAT_YAPISI", 5)
def c28_52w_high(ctx: ScoringContext) -> tuple[int, str]:
    pct = _pct_from_52w_high(ctx.prices) if ctx.prices is not None else None
    if pct is None:
        return 0, "N/A"
    pct100 = pct * 100
    if pct100 < 5:
        s = 5
    elif pct100 < 10:
        s = 4
    elif pct100 < 20:
        s = 3
    elif pct100 < 30:
        s = 1
    else:
        s = 0
    return s, f"{pct100:.1f}% below -> {s}/5"


@criterion("swing_position", "FIYAT_YAPISI", 3)
def c29_swing_position(ctx: ScoringContext) -> tuple[int, str]:
    sh = _g(ctx.ind, "swing_high_20")
    sl = _g(ctx.ind, "swing_low_20")
    close = _g(ctx.ind, "close")
    if sh is None or sl is None or close is None or sh <= sl:
        return 0, "N/A"
    if close > sh:
        s = 3
    elif close > sh * 0.98:
        s = 2
    elif close > (sh + sl) / 2:
        s = 1
    else:
        s = 0
    return s, f"close={close:.1f} sh={sh:.1f} sl={sl:.1f} -> {s}/3"


@criterion("setup_pattern", "FIYAT_YAPISI", 5)
def c55_setup_pattern(ctx: ScoringContext) -> tuple[int, str]:
    setup = getattr(ctx.cand, "setup_type", "none")
    conf = getattr(ctx.cand, "setup_confidence", 0.0)
    if setup == "none" or conf <= 0:
        return 0, "none"
    if conf >= 0.7:
        s = 5
    elif conf >= 0.5:
        s = 4
    elif conf >= 0.3:
        s = 3
    else:
        s = 1
    return s, f"{setup}({conf:.2f}) -> {s}/5"


@criterion("candlestick_signal", "FIYAT_YAPISI", 3)
def c56_candlestick_signal(ctx: ScoringContext) -> tuple[int, str]:
    """Max 3 puan, hacim teyidi zorunlu."""
    engulf = _g(ctx.ind, "pattern_bull_engulf")
    hammer = _g(ctx.ind, "pattern_hammer")
    vol_ratio = _g(ctx.ind, "vol_ratio")
    has_pattern = (engulf is not None and engulf > 0) or (hammer is not None and hammer > 0)
    if not has_pattern:
        return 0, "no pattern"
    high_vol = vol_ratio is not None and vol_ratio >= 1.2
    if has_pattern and high_vol:
        s = 3
    else:
        s = 0  # hacim teyidi olmadan puan yok
    parts = []
    if engulf and engulf > 0:
        parts.append("engulf")
    if hammer and hammer > 0:
        parts.append("hammer")
    vol_tag = f" vol={vol_ratio:.1f}x" if vol_ratio else ""
    return s, f"{'+'.join(parts)}{vol_tag} -> {s}/3"


@criterion("support_proximity", "FIYAT_YAPISI", 5)
def c72_support_proximity(ctx: ScoringContext) -> tuple[int, str]:
    """Fibonacci destege mesafe."""
    close = _g(ctx.ind, "close")
    supports = ctx.ind.get("fib_supports")
    if close is None or not supports:
        return 0, "N/A"
    _, dist_pct = find_nearest_support(close, supports)
    if dist_pct is None:
        return 0, "N/A"
    dist = dist_pct * 100
    if dist < 2:
        s = 5  # destek cok yakin — guvenli giris
    elif dist < 5:
        s = 4
    elif dist < 10:
        s = 3
    elif dist < 15:
        s = 1
    else:
        s = 0
    return s, f"{dist:.1f}% above support -> {s}/5"


@criterion("resistance_distance", "FIYAT_YAPISI", 4)
def c73_resistance_distance(ctx: ScoringContext) -> tuple[int, str]:
    """Fibonacci dirence mesafe."""
    close = _g(ctx.ind, "close")
    resistances = ctx.ind.get("fib_resistances")
    if close is None or not resistances:
        return 0, "N/A"
    _, dist_pct = find_nearest_resistance(close, resistances)
    if dist_pct is None:
        return 0, "N/A"
    dist = dist_pct * 100
    if dist > 15:
        s = 4  # direnc uzak — bol alan var
    elif dist > 10:
        s = 3
    elif dist > 5:
        s = 2
    elif dist > 2:
        s = 1
    else:
        s = 0  # direnc cok yakin
    return s, f"{dist:.1f}% below resistance -> {s}/4"
