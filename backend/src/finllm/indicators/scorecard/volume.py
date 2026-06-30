"""HACIM kategorisi — 8 kriter, ~37 puan.

c47 neg_div_penalty cikarildi (c17 ile ayni veri).
c68 macd_hist_sequence, c69 obv_slope_change, c71 volume_price_divergence eklendi.
"""
from __future__ import annotations

import numpy as np

from finllm.indicators.scorecard._helpers import _g, _quintile_score
from finllm.indicators.scorecard._registry import criterion
from finllm.indicators.scorecard._slope_helpers import consecutive_growth, indicator_slope
from finllm.indicators.scorecard._types import ScoringContext
from finllm.indicators.relative_score import _pct_ranks


@criterion("volume_ratio", "HACIM", 6)
def c15_vol_ratio(ctx: ScoringContext) -> tuple[int, str]:
    v = _g(ctx.ind, "vol_ratio")
    if v is None:
        return 0, "N/A"
    if v >= 2.0:
        s = 6
    elif v >= 1.5:
        s = 5
    elif v >= 1.2:
        s = 3
    elif v >= 0.8:
        s = 1
    else:
        s = 0
    return s, f"{v:.2f}x -> {s}/6"


@criterion("obv_trend", "HACIM", 5)
def c16_obv_trend(ctx: ScoringContext) -> tuple[int, str]:
    trend = ctx.ind.get("obv_trend")
    obv = _g(ctx.ind, "obv")
    obv_ma20 = _g(ctx.ind, "obv_ma20")
    obv_ema10 = _g(ctx.ind, "obv_ema10")
    obv_ema30 = _g(ctx.ind, "obv_ema30")
    if trend is None:
        return 0, "N/A"
    ema_bullish = obv_ema10 is not None and obv_ema30 is not None and obv_ema10 > obv_ema30
    if trend == "RISING":
        if ema_bullish:
            s = 5
        elif obv is not None and obv_ma20 is not None and obv > obv_ma20:
            s = 4
        else:
            s = 3
    else:
        s = 1 if ema_bullish else 0
    ema_tag = " EMA10>30" if ema_bullish else ""
    return s, f"{trend}{ema_tag} -> {s}/5"


@criterion("obv_divergence", "HACIM", 5)
def c17_obv_divergence(ctx: ScoringContext) -> tuple[int, str]:
    div_type = ctx.ind.get("obv_divergence_type")
    trend = ctx.ind.get("obv_trend")
    if div_type is None and trend is None:
        return 2, "N/A (neutral)"
    if div_type == "POSITIVE":
        s = 5
    elif div_type == "NEGATIVE":
        s = 0
    elif div_type is None or div_type == "NONE":
        s = 4 if trend == "RISING" else 2
    else:
        s = 2
    return s, f"div={div_type} trend={trend} -> {s}/5"


@criterion("money_flow_index", "HACIM", 4)
def c18_mfi(ctx: ScoringContext) -> tuple[int, str]:
    v = _g(ctx.ind, "mfi_14")
    if v is None:
        return 0, "N/A"
    if 40 <= v <= 70:
        s = 4
    elif 70 < v <= 80:
        s = 3
    elif 30 <= v < 40:
        s = 2
    elif v > 80:
        s = 0
    else:
        s = 1
    return s, f"{v:.0f} -> {s}/4"


@criterion("chaikin_money_flow", "HACIM", 4)
def c19_cmf(ctx: ScoringContext) -> tuple[int, str]:
    v = _g(ctx.ind, "cmf_20")
    if v is None:
        return 0, "N/A"
    if v > 0.10:
        s = 4
    elif v > 0.05:
        s = 3
    elif v > 0:
        s = 2
    else:
        s = 0
    return s, f"{v:.3f} -> {s}/4"


@criterion("daily_dollar_volume", "HACIM", 4)
def c20_dollar_volume(ctx: ScoringContext) -> tuple[int, str]:
    close = _g(ctx.ind, "close")
    vol_sma = _g(ctx.ind, "vol_sma_20")
    if close is None or vol_sma is None:
        return 0, "N/A"
    dv = close * vol_sma
    if ctx.universe_dollar_vols and len(ctx.universe_dollar_vols) > 1:
        pct = _pct_ranks(ctx.universe_dollar_vols, higher_better=True)
        p = pct.get(ctx.ticker_symbol, 0.5)
    else:
        p = 0.5
    s = _quintile_score(p, (4, 3, 2, 1, 0))
    return s, f"dv={dv:.0f} pct={p:.2f} -> {s}/4"


@criterion("macd_hist_sequence", "HACIM", 3)
def c68_macd_hist_sequence(ctx: ScoringContext) -> tuple[int, str]:
    """Histogram ardisik buyume."""
    hist_vals = ctx.ind.get("macd_hist_values")
    if hist_vals is None:
        return 0, "N/A"
    count = consecutive_growth(hist_vals)
    if count >= 4:
        s = 3
    elif count >= 3:
        s = 2
    elif count >= 2:
        s = 1
    else:
        s = 0
    return s, f"{count} consecutive growth -> {s}/3"


@criterion("obv_slope_change", "HACIM", 3)
def c69_obv_slope_change(ctx: ScoringContext) -> tuple[int, str]:
    """Kisa vs uzun OBV egimi."""
    short_slope = _g(ctx.ind, "obv_slope_5")
    long_slope = _g(ctx.ind, "obv_slope_20")
    if short_slope is None or long_slope is None:
        return 0, "N/A"
    if short_slope > 0 and short_slope > long_slope:
        s = 3  # accelerating accumulation
    elif short_slope > 0:
        s = 2  # positive but decelerating
    elif short_slope < 0 and long_slope > 0:
        s = 1  # short-term dip in long-term uptrend
    else:
        s = 0
    return s, f"short={short_slope:.0f} long={long_slope:.0f} -> {s}/3"


@criterion("volume_price_divergence", "HACIM", 3)
def c71_volume_price_divergence(ctx: ScoringContext) -> tuple[int, str]:
    """Price-volume correlation (son 20 gun)."""
    corr = _g(ctx.ind, "price_vol_corr_20")
    if corr is None:
        return 0, "N/A"
    # Pozitif korelasyon = fiyat yukselirken hacim artiyor (iyi)
    if corr > 0.5:
        s = 3
    elif corr > 0.2:
        s = 2
    elif corr > -0.2:
        s = 1
    else:
        s = 0  # negatif korelasyon — fiyat duserken hacim artiyor
    return s, f"corr={corr:.2f} -> {s}/3"
