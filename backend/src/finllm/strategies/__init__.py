"""Strategy ensemble — birden çok setup detector + regime-based selector."""
from finllm.strategies.base import Regime, StrategySetup, TradingStrategy
from finllm.strategies.earnings_drift import PostEarningsDriftStrategy
from finllm.strategies.pullback import PullbackToEMAStrategy
from finllm.strategies.sector_rotation import SectorRotationStrategy


def all_strategies() -> list[TradingStrategy]:
    """Tüm aktif strategy'leri döner."""
    return [
        PullbackToEMAStrategy(),
        PostEarningsDriftStrategy(),
        SectorRotationStrategy(),
    ]


def strategies_for_regime(regime: str) -> list[TradingStrategy]:
    """Verilen regime'de aktif olacak strategy'ler."""
    return [s for s in all_strategies() if regime in s.applicable_regimes]


__all__ = [
    "PostEarningsDriftStrategy",
    "PullbackToEMAStrategy",
    "Regime",
    "SectorRotationStrategy",
    "StrategySetup",
    "TradingStrategy",
    "all_strategies",
    "strategies_for_regime",
]
