"""Derived indicators — lib.zip'in `_computeDerivedFields` Python port'u.

OBV divergence, BB squeeze (percentile-based), weekly trend aggregation.
features/technical.py'nin üzerine ek katman — Stage 1C'de Candidate.indicators
sözlüğüne yazılır.
"""
from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd


def compute_obv_divergence(
    prices: pd.DataFrame,
    obv: pd.Series,
    lookback: int = 5,
) -> dict[str, object]:
    """OBV ile fiyat arasında divergence tespit.

    Fiyat ↑ + OBV ↓ = NEGATIVE (bearish warning)
    Fiyat ↓ + OBV ↑ = POSITIVE (bullish warning)
    Aksi → false

    Args:
        prices: OHLCV, lowercase columns
        obv: OBV serisi (technical.py'den)
        lookback: bugün ile lookback gün önce karşılaştır

    Returns:
        {"trend": "RISING"|"FALLING", "divergence": bool,
         "type": "POSITIVE"|"NEGATIVE"|None, "obv_ma20": float|None}
    """
    if len(prices) < lookback + 1 or len(obv) < lookback + 1:
        return {"trend": None, "divergence": False, "type": None, "obv_ma20": None}

    latest_obv = float(obv.iloc[-1]) if not pd.isna(obv.iloc[-1]) else 0.0
    prev_obv = (
        float(obv.iloc[-(lookback + 1)])
        if not pd.isna(obv.iloc[-(lookback + 1)])
        else 0.0
    )

    obv_trend: Literal["RISING", "FALLING"] = "RISING" if latest_obv > prev_obv else "FALLING"

    obv_ma20 = None
    if len(obv) >= 20:
        obv_ma20 = float(obv.tail(20).mean())

    today_close = float(prices["close"].iloc[-1])
    prev_close = float(prices["close"].iloc[-(lookback + 1)])
    price_rising = today_close > prev_close

    obv_rising = latest_obv > prev_obv

    divergence_type: Literal["POSITIVE", "NEGATIVE"] | None = None
    if price_rising and not obv_rising:
        divergence_type = "NEGATIVE"
    elif not price_rising and obv_rising:
        divergence_type = "POSITIVE"

    return {
        "trend": obv_trend,
        "divergence": divergence_type is not None,
        "type": divergence_type,
        "obv_ma20": obv_ma20,
    }


def compute_bb_squeeze(
    bb_upper: pd.Series,
    bb_lower: pd.Series,
    bb_mid: pd.Series,
    percentile_window: int = 20,
    squeeze_threshold: float = 0.2,
) -> dict[str, object]:
    """BB width'in son N gündeki yerini bul; alt %20'deyse SQUEEZE.

    BB Squeeze = volatilite çöktü → patlama yaklaşıyor (genelde).
    """
    if len(bb_upper) < percentile_window:
        return {"width": None, "trend": None, "squeeze": False}

    widths = ((bb_upper - bb_lower) / bb_mid).tail(percentile_window).dropna()
    if len(widths) < 5:
        return {"width": None, "trend": None, "squeeze": False}

    current_width = float(widths.iloc[-1])

    # Trend: son 5 ile şimdi karşılaştır
    prev_width = float(widths.iloc[-6]) if len(widths) > 5 else current_width
    if current_width < prev_width * 0.85:
        trend = "NARROWING"
    elif current_width > prev_width * 1.15:
        trend = "WIDENING"
    else:
        trend = "STABLE"

    sorted_widths = sorted(widths.values)
    p20 = sorted_widths[int(len(sorted_widths) * squeeze_threshold)]
    is_squeeze = current_width <= p20

    return {
        "width": current_width,
        "trend": trend,
        "squeeze": is_squeeze,
    }


def compute_weekly_trend(
    daily_prices: pd.DataFrame,
    min_weeks: int = 50,
) -> dict[str, object]:
    """Daily → weekly aggregate edip haftalık SMA20/50 + trend label.

    lib.zip'in `_computeWeeklyIndicators` Python port'u.
    Trend label LLM'in multi-timeframe (Layer 2) kararı için kullanılır.
    """
    if len(daily_prices) < 60:
        return {"sma20": None, "sma50": None, "rsi": None, "trend": None}

    # Hafta sonu kapanışları al (W-FRI)
    weekly = daily_prices["close"].resample("W-FRI").last().dropna()

    if len(weekly) < min_weeks:
        return {"sma20": None, "sma50": None, "rsi": None, "trend": None}

    sma20 = float(weekly.tail(20).mean())
    sma50 = float(weekly.tail(50).mean())

    # Weekly RSI(14)
    delta = weekly.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.tail(14).mean()
    avg_loss = loss.tail(14).mean()
    if avg_loss == 0:
        rsi = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))

    latest = float(weekly.iloc[-1])
    if latest > sma20 and sma20 > sma50:
        trend = "UPTREND"
    elif latest < sma20 and sma20 < sma50:
        trend = "DOWNTREND"
    elif latest > sma20 and sma20 < sma50:
        trend = "EARLY_RECOVERY"
    elif latest < sma20 and sma20 > sma50:
        trend = "EARLY_WEAKNESS"
    else:
        trend = "SIDEWAYS"

    return {
        "sma20": sma20,
        "sma50": sma50,
        "rsi": float(rsi),
        "trend": trend,
    }


def compute_swing_levels(prices: pd.DataFrame, window: int = 20) -> dict[str, float]:
    """Son N gün swing high/low — basit destek/direnç."""
    if len(prices) < window:
        return {"swing_high": None, "swing_low": None}
    recent = prices.tail(window)
    return {
        "swing_high": float(recent["high"].max()),
        "swing_low": float(recent["low"].min()),
    }


def detect_market_regime(features: dict[str, float | None]) -> str:
    """ADX + BB width trend → market regime.

    lib.zip'in `_marketRegime` Python port'u.
    Stage 3 LLM bu regime'e göre strateji ayarlar.
    """
    adx = features.get("adx_14")
    bb_trend = features.get("bb_width_trend")  # NARROWING/WIDENING/STABLE

    if adx is None:
        return "UNKNOWN"

    if adx >= 25 and bb_trend != "NARROWING":
        if adx >= 40:
            return "STRONG_TREND"
        return "TREND"

    if adx < 20:
        if bb_trend == "NARROWING":
            return "RANGE_SQUEEZE"
        return "RANGE"

    if adx >= 30 and bb_trend == "WIDENING":
        return "VOLATILE"

    return "TRANSITIONAL"
