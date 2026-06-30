"""COKLU_ZAMAN kategorisi — 7 kriter, ~26 puan.

c74 sr_touch_count, c75 volume_profile_pos, c77 consolidation_duration,
c78 higher_low_sequence, c79 breakout_age eklendi.
"""
from __future__ import annotations

from finllm.indicators.scorecard._helpers import _g
from finllm.indicators.scorecard._registry import criterion
from finllm.indicators.scorecard._sr_helpers import (
    count_support_touches,
    is_higher_low_sequence,
)
from finllm.indicators.scorecard._types import ScoringContext


@criterion("timeframe_alignment", "COKLU_ZAMAN", 5)
def c48_tf_alignment(ctx: ScoringContext) -> tuple[int, str]:
    v = ctx.ind.get("timeframe_alignment")
    if v is None:
        return 1, "UNKNOWN -> 1/5"
    mapping = {"ALIGNED": 5, "PARTIALLY_ALIGNED": 2, "CONFLICTING": 0, "UNKNOWN": 1}
    s = mapping.get(v, 1)
    return s, f"{v} -> {s}/5"


@criterion("ema_order", "COKLU_ZAMAN", 4)
def c49_ema_order(ctx: ScoringContext) -> tuple[int, str]:
    ema12 = _g(ctx.ind, "ema_12")
    ema26 = _g(ctx.ind, "ema_26")
    sma50 = _g(ctx.ind, "sma_50")
    sma200 = _g(ctx.ind, "sma_200")
    vals = [ema12, ema26, sma50, sma200]
    if any(v is None for v in vals):
        return 0, "N/A"
    in_order = 0
    if ema12 > ema26:
        in_order += 1
    if ema26 > sma50:
        in_order += 1
    if sma50 > sma200:
        in_order += 1
    if in_order == 3:
        s = 4
    elif in_order == 2:
        s = 3
    elif in_order == 1:
        s = 2
    else:
        s = 0
    return s, f"{in_order}/3 in order -> {s}/4"


@criterion("di_spread", "COKLU_ZAMAN", 3)
def c50_di_spread(ctx: ScoringContext) -> tuple[int, str]:
    di_p = _g(ctx.ind, "di_plus")
    di_m = _g(ctx.ind, "di_minus")
    if di_p is None or di_m is None:
        return 0, "N/A"
    diff = di_p - di_m
    if diff > 15:
        s = 3
    elif diff > 5:
        s = 2
    elif diff > 0:
        s = 1
    else:
        s = 0
    return s, f"DI+={di_p:.0f} DI-={di_m:.0f} diff={diff:.0f} -> {s}/3"


@criterion("sr_touch_count", "COKLU_ZAMAN", 3)
def c74_sr_touch_count(ctx: ScoringContext) -> tuple[int, str]:
    """Destek test sayisi (60 gun)."""
    supports = ctx.ind.get("fib_supports")
    if not supports or ctx.prices is None:
        return 0, "N/A"
    # En yakin destek icin touch sayisi
    nearest_support = supports[0]
    touches = count_support_touches(ctx.prices, nearest_support, window=60, tol_pct=1.5)
    if touches >= 3:
        s = 3  # coklu test = guclu destek
    elif touches >= 2:
        s = 2
    elif touches >= 1:
        s = 1
    else:
        s = 0
    return s, f"{touches} touches @ {nearest_support:.2f} -> {s}/3"


@criterion("volume_profile_pos", "COKLU_ZAMAN", 4)
def c75_volume_profile_pos(ctx: ScoringContext) -> tuple[int, str]:
    """Fiyat vs value area."""
    close = _g(ctx.ind, "close")
    vpoc = _g(ctx.ind, "vpoc")
    va_high = _g(ctx.ind, "va_high")
    va_low = _g(ctx.ind, "va_low")
    if close is None or vpoc is None or va_high is None or va_low is None:
        return 0, "N/A"
    if close > va_high:
        s = 4  # value area ustunde — guclu
    elif close >= vpoc:
        s = 3  # POC ustunde
    elif close >= va_low:
        s = 2  # value area icinde
    else:
        s = 0  # value area altinda
    return s, f"close={close:.1f} poc={vpoc:.1f} va=[{va_low:.1f},{va_high:.1f}] -> {s}/4"


@criterion("consolidation_duration", "COKLU_ZAMAN", 4)
def c77_consolidation_duration(ctx: ScoringContext) -> tuple[int, str]:
    """20d range / 60d range — dusuk oran = sikilma, breakout potansiyeli."""
    if ctx.prices is None or len(ctx.prices) < 60:
        return 0, "N/A"
    highs = ctx.prices["high"].values
    lows = ctx.prices["low"].values

    range_20 = float(highs[-20:].max() - lows[-20:].min())
    range_60 = float(highs[-60:].max() - lows[-60:].min())

    if range_60 == 0:
        return 0, "N/A"

    ratio = range_20 / range_60
    if ratio < 0.3:
        s = 4  # tight consolidation — breakout yakın
    elif ratio < 0.5:
        s = 3
    elif ratio < 0.7:
        s = 2
    else:
        s = 0  # geniş range, konsolidasyon yok
    return s, f"20d/60d={ratio:.2f} -> {s}/4"


@criterion("higher_low_sequence", "COKLU_ZAMAN", 4)
def c78_higher_low_sequence(ctx: ScoringContext) -> tuple[int, str]:
    """Ardisik higher low (Dow Theory)."""
    pivot_lows = ctx.ind.get("pivot_lows")
    if not pivot_lows or len(pivot_lows) < 2:
        return 0, "N/A"
    count = is_higher_low_sequence(pivot_lows)
    if count >= 3:
        s = 4
    elif count >= 2:
        s = 3
    elif count >= 1:
        s = 2
    else:
        s = 0
    return s, f"{count} higher lows -> {s}/4"


@criterion("breakout_age", "COKLU_ZAMAN", 3)
def c79_breakout_age(ctx: ScoringContext) -> tuple[int, str]:
    """Son Donchian kirilimi yasi."""
    age = _g(ctx.ind, "breakout_age_days")
    vol_confirmed = ctx.ind.get("breakout_vol_confirmed", False)
    if age is None or age < 0:
        return 0, "N/A"
    if age <= 3 and vol_confirmed:
        s = 3  # taze kirilim + hacim teyidi
    elif age <= 3:
        s = 2  # taze ama teyitsiz
    elif age <= 7:
        s = 1  # bir hafta icerisinde
    else:
        s = 0
    vol_tag = " +vol" if vol_confirmed else ""
    return s, f"age={age}d{vol_tag} -> {s}/3"
