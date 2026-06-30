"""Scorecard veri yapilari."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from finllm.markets.base import FundamentalSnapshot
from finllm.pipeline.context import Candidate


@dataclass(slots=True)
class CriterionResult:
    name: str
    category: str
    score: int
    max_score: int
    data_available: bool
    detail: str


@dataclass(slots=True)
class CategoryScore:
    name: str
    score: int
    max_score: int
    criteria: list[CriterionResult]


@dataclass(slots=True)
class MasterScore:
    total: int
    max_possible: int
    pct: float
    label: str
    categories: dict[str, CategoryScore]
    criteria: list[CriterionResult]

    def summary_line(self) -> str:
        """Compact one-liner for data_block."""
        cat_parts = " ".join(
            f"{k.lower()}={v.score}/{v.max_score}"
            for k, v in self.categories.items()
        )
        return f"{self.total}/{self.max_possible} ({self.pct:.0f}%) [{self.label}] | {cat_parts}"


@dataclass(slots=True)
class ScoringContext:
    """Tum kriter fonksiyonlarina gecirilen birlesik context."""
    ind: dict[str, Any]
    snap: FundamentalSnapshot | None
    prices: pd.DataFrame | None
    quarterly: object | None
    pctiles: dict[str, float] | None
    universe_dollar_vols: dict[str, float] | None
    ticker_symbol: str
    cand: Candidate
