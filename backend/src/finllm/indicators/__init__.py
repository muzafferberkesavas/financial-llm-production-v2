"""Indicators — features/technical.py'nin üzerinde derived + confluence katmanı.

features.technical → ham göstergeler (~50)
indicators.derived → OBV div, BB squeeze, weekly trend, market regime
indicators.confluence → 8-bileşenli skorlama
"""
from finllm.indicators.confluence import (
    ConfluenceComponents,
    compute_confluence,
    confluence_to_signal_suggestion,
)
from finllm.indicators.derived import (
    compute_bb_squeeze,
    compute_obv_divergence,
    compute_swing_levels,
    compute_weekly_trend,
    detect_market_regime,
)
from finllm.indicators.fundamentals import (
    FundamentalScore,
    SECTOR_BENCHMARKS,
    compute_fundamental_score,
)

__all__ = [
    "ConfluenceComponents",
    "FundamentalScore",
    "SECTOR_BENCHMARKS",
    "compute_bb_squeeze",
    "compute_confluence",
    "compute_fundamental_score",
    "compute_obv_divergence",
    "compute_swing_levels",
    "compute_weekly_trend",
    "confluence_to_signal_suggestion",
    "detect_market_regime",
]
