"""Support/Resistance, Fibonacci S/R, volume profile yardimcilari."""
from __future__ import annotations

import numpy as np
import pandas as pd


def compute_fibonacci_sr(
    prices: pd.DataFrame,
    lookbacks: list[int] | None = None,
) -> tuple[list[float], list[float]]:
    """Fibonacci destek ve direnc seviyeleri.

    Returns:
        (supports, resistances) — siralanmis float listeleri.
    """
    if lookbacks is None:
        lookbacks = [20, 50]
    if prices is None or prices.empty or len(prices) < 20:
        return [], []

    supports = []
    resistances = []
    close = float(prices["close"].iloc[-1])

    for lb in lookbacks:
        window = prices.tail(lb)
        high = float(window["high"].max())
        low = float(window["low"].min())
        diff = high - low
        if diff <= 0:
            continue

        fib_levels = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
        for fib in fib_levels:
            level = high - diff * fib
            if level < close:
                supports.append(level)
            elif level > close:
                resistances.append(level)

    supports = sorted(set(supports), reverse=True)  # en yakin ustte
    resistances = sorted(set(resistances))           # en yakin ustte
    return supports, resistances


def find_nearest_support(close: float, supports: list[float]) -> tuple[float | None, float | None]:
    """En yakin destek + mesafe (pct)."""
    if not supports:
        return None, None
    nearest = supports[0]  # already sorted desc, first is nearest
    dist_pct = (close - nearest) / close if close > 0 else None
    return nearest, dist_pct


def find_nearest_resistance(close: float, resistances: list[float]) -> tuple[float | None, float | None]:
    """En yakin direnc + mesafe (pct)."""
    if not resistances:
        return None, None
    nearest = resistances[0]  # already sorted asc, first is nearest
    dist_pct = (nearest - close) / close if close > 0 else None
    return nearest, dist_pct


def count_support_touches(
    prices: pd.DataFrame,
    level: float,
    window: int = 60,
    tol_pct: float = 1.5,
) -> int:
    """Fiyatin belirli bir seviyeye kac kez temas ettigi."""
    if prices is None or prices.empty:
        return 0
    lows = prices["low"].tail(window).values
    tol = level * tol_pct / 100
    touches = np.sum(np.abs(lows - level) <= tol)
    return int(touches)


def compute_volume_profile_simple(
    prices: pd.DataFrame,
    window: int = 30,
) -> tuple[float | None, float | None, float | None]:
    """Basit volume profile: POC, VA_HIGH, VA_LOW.

    Returns:
        (poc, va_high, va_low) veya (None, None, None).
    """
    if prices is None or prices.empty or len(prices) < window:
        return None, None, None

    recent = prices.tail(window)
    closes = recent["close"].values
    volumes = recent["volume"].values

    if len(closes) < 5:
        return None, None, None

    # Fiyat araligini 20 bins'e bol
    price_min = float(np.min(closes))
    price_max = float(np.max(closes))
    if price_max <= price_min:
        return None, None, None

    n_bins = 20
    bins = np.linspace(price_min, price_max, n_bins + 1)
    bin_indices = np.digitize(closes, bins) - 1
    bin_indices = np.clip(bin_indices, 0, n_bins - 1)

    vol_profile = np.zeros(n_bins)
    for i, bi in enumerate(bin_indices):
        vol_profile[bi] += volumes[i]

    poc_bin = int(np.argmax(vol_profile))
    poc = float((bins[poc_bin] + bins[poc_bin + 1]) / 2)

    # Value area = %70 toplam hacim (POC'den disa dogru)
    total_vol = vol_profile.sum()
    if total_vol == 0:
        return poc, None, None

    va_vol = vol_profile[poc_bin]
    low_idx = poc_bin
    high_idx = poc_bin
    while va_vol < total_vol * 0.70:
        expand_low = low_idx > 0
        expand_high = high_idx < n_bins - 1
        if not expand_low and not expand_high:
            break
        low_val = vol_profile[low_idx - 1] if expand_low else 0
        high_val = vol_profile[high_idx + 1] if expand_high else 0
        if low_val >= high_val and expand_low:
            low_idx -= 1
            va_vol += vol_profile[low_idx]
        elif expand_high:
            high_idx += 1
            va_vol += vol_profile[high_idx]
        else:
            low_idx -= 1
            va_vol += vol_profile[low_idx]

    va_low = float(bins[low_idx])
    va_high = float(bins[high_idx + 1])
    return poc, va_high, va_low


def detect_pivot_lows(prices: pd.DataFrame, lookback: int = 5) -> list[float]:
    """Pivot low listesi (son 60 gun)."""
    if prices is None or prices.empty or len(prices) < lookback * 2 + 1:
        return []

    lows = prices["low"].tail(60).values
    pivots = []
    for i in range(lookback, len(lows) - lookback):
        if all(lows[i] <= lows[i - j] for j in range(1, lookback + 1)) and \
           all(lows[i] <= lows[i + j] for j in range(1, lookback + 1)):
            pivots.append(float(lows[i]))
    return pivots


def is_higher_low_sequence(pivot_lows: list[float]) -> int:
    """Ardisik higher low sayisi."""
    if len(pivot_lows) < 2:
        return 0
    count = 0
    for i in range(1, len(pivot_lows)):
        if pivot_lows[i] > pivot_lows[i - 1]:
            count += 1
        else:
            count = 0
    return count


def breakout_age(prices: pd.DataFrame, donch_upper_20: float | None) -> tuple[int, bool]:
    """Son Donchian kiriliminin yasi (gun) + hacim teyiti.

    Returns:
        (age_days, vol_confirmed)
    """
    if prices is None or prices.empty or donch_upper_20 is None:
        return -1, False

    closes = prices["close"].values
    volumes = prices["volume"].values
    vol_sma = float(np.mean(volumes[-20:])) if len(volumes) >= 20 else 0

    for i in range(len(closes) - 1, max(len(closes) - 60, -1), -1):
        if closes[i] >= donch_upper_20:
            age = len(closes) - 1 - i
            vol_confirmed = volumes[i] > vol_sma * 1.3 if vol_sma > 0 else False
            return age, bool(vol_confirmed)

    return -1, False
