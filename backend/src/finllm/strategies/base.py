"""Strategy abstraction — birden çok setup detector'ı paralel çalıştırır.

Mevcut Stage 1B = single strategy (pullback_ema + bull_flag + breakout in tek dosya).
Phase 3.6: her strategy ayrı modül + regime-based weighting.

Strategy contract:
  - name: unique str
  - applicable_regimes: hangi regime'lerde çalıştırılır
  - detect(prices, indicators) → SetupSignal | None

Pipeline:
  Stage 1 (hard filter) → list[Candidate]
  Stage 1B (strategies) → her strategy candidate'lara aday üretir
  Stage 1C → indicators + confluence
  ...
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

import pandas as pd

Regime = Literal[
    "TREND",
    "STRONG_TREND",
    "RANGE",
    "RANGE_SQUEEZE",
    "VOLATILE",
    "TRANSITIONAL",
    "UNKNOWN",
]


@dataclass(slots=True)
class StrategySetup:
    """Bir strategy'nin candidate üzerinde bulduğu setup."""

    strategy: str                       # "pullback_ema", "earnings_drift", "sector_rotation"
    setup_score: float                  # 0-1, kaliteyi yansıtır
    metadata: dict[str, Any] = field(default_factory=dict)
    rationale: str = ""                 # kısa açıklama


@runtime_checkable
class TradingStrategy(Protocol):
    """Stage 1B'de çağrılan algoritmik setup detector."""

    name: str
    applicable_regimes: tuple[Regime, ...]

    def detect(
        self,
        prices: pd.DataFrame,
        indicators: dict[str, float | None],
    ) -> StrategySetup | None:
        """Setup tespit edersen StrategySetup döndür, yoksa None."""
        ...
