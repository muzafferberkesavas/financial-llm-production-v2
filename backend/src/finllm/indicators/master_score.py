"""Backward compatibility shim — tum logic scorecard/ paketine tasindi.

Yeni import: from finllm.indicators.scorecard import compute_master_score, MasterScore
"""
from finllm.indicators.scorecard import (  # noqa: F401
    CategoryScore,
    CriterionResult,
    MasterScore,
    compute_master_score,
)

__all__ = [
    "CriterionResult",
    "CategoryScore",
    "MasterScore",
    "compute_master_score",
]
