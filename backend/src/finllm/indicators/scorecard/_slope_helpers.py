"""Slope / momentum yardimci fonksiyonlari."""
from __future__ import annotations

import numpy as np


def indicator_slope(values, window: int = 5) -> float | None:
    """Son `window` degerin np.polyfit slope'u.

    Args:
        values: array-like (son N deger) veya None
        window: kullanilacak bar sayisi

    Returns:
        Slope (float) veya None.
    """
    if values is None:
        return None
    arr = np.asarray(values, dtype=float)
    arr = arr[~np.isnan(arr)]
    if len(arr) < window:
        return None
    arr = arr[-window:]
    x = np.arange(window, dtype=float)
    try:
        slope, _ = np.polyfit(x, arr, 1)
        return float(slope)
    except (np.linalg.LinAlgError, ValueError):
        return None


def slopes_rising_count(slopes: dict[str, float | None]) -> int:
    """Kac gostergenin slope'u pozitif."""
    return sum(1 for v in slopes.values() if v is not None and v > 0)


def consecutive_growth(values) -> int:
    """Ardisik artis sayisi (sondan geriye)."""
    if values is None:
        return 0
    arr = np.asarray(values, dtype=float)
    arr = arr[~np.isnan(arr)]
    if len(arr) < 2:
        return 0
    count = 0
    for i in range(len(arr) - 1, 0, -1):
        if arr[i] > arr[i - 1]:
            count += 1
        else:
            break
    return count
