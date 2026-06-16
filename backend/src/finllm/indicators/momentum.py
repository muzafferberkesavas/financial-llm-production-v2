"""12-1 month price momentum (signal research #4 — a disciplined real factor).

Momentum is among the most replicated equity factors (the research notes it is
real, just decaying). The canonical construction is the 12-1 month return: the
return from ~12 months ago to ~1 month ago, SKIPPING the most recent month to
avoid short-term reversal. Cross-sectional — compared across the candidate set.

Returns a raw 12-1m return; the panel ranks it cross-sectionally so it adds a
genuine factor without an absolute threshold (avoids overfitting a magnitude).
"""
from __future__ import annotations

import pandas as pd

LOOKBACK = 252      # ~12 trading months
SKIP = 21           # skip most recent ~1 month (reversal)


def momentum_12_1(prices: pd.DataFrame) -> float | None:
    """12-1 month return from a daily OHLCV frame, or None if too short."""
    if prices is None or prices.empty or len(prices) < LOOKBACK + 1:
        return None
    closes = prices["close"].dropna()
    if len(closes) < LOOKBACK + 1:
        return None
    start = float(closes.iloc[-LOOKBACK])      # ~12m ago
    end = float(closes.iloc[-SKIP - 1])        # ~1m ago (skip last month)
    if start <= 0:
        return None
    return end / start - 1.0


__all__ = ["momentum_12_1", "LOOKBACK", "SKIP"]
