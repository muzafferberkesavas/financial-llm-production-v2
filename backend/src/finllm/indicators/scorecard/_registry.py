"""Criterion decorator registry."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from finllm.indicators.scorecard._types import ScoringContext


@dataclass(slots=True)
class CriterionDef:
    name: str
    category: str
    max_score: int
    fn: Callable[[ScoringContext], tuple[int, str]]


_REGISTRY: list[CriterionDef] = []


def criterion(name: str, category: str, max_score: int):
    """Decorator: kriter fonksiyonunu global registry'ye ekler."""
    def decorator(fn: Callable[[ScoringContext], tuple[int, str]]):
        _REGISTRY.append(CriterionDef(
            name=name, category=category, max_score=max_score, fn=fn,
        ))
        return fn
    return decorator


def get_all_criteria() -> list[CriterionDef]:
    return list(_REGISTRY)


CATEGORY_ORDER = [
    "TREND", "MOMENTUM", "HACIM", "VOLATILITE", "FIYAT_YAPISI",
    "DEGER", "KALITE", "BUYUME", "RISK", "COKLU_ZAMAN",
]
