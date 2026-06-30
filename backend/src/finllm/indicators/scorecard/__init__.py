"""Master Scorecard v2 — 67 kriterli moduler mimari.

Public API:
    from finllm.indicators.scorecard import compute_master_score, MasterScore
"""
from __future__ import annotations

from finllm.indicators.scorecard._helpers import (
    _compute_universe_percentiles,
    _label,
)
from finllm.indicators.scorecard._registry import (
    CATEGORY_ORDER,
    get_all_criteria,
)
from finllm.indicators.scorecard._types import (
    CategoryScore,
    CriterionResult,
    MasterScore,
    ScoringContext,
)

# Side-effect imports: @criterion decorator'lari calistirir
from finllm.indicators.scorecard import trend          # noqa: F401
from finllm.indicators.scorecard import momentum       # noqa: F401
from finllm.indicators.scorecard import volume         # noqa: F401
from finllm.indicators.scorecard import volatility     # noqa: F401
from finllm.indicators.scorecard import price_structure  # noqa: F401
from finllm.indicators.scorecard import valuation      # noqa: F401
from finllm.indicators.scorecard import quality        # noqa: F401
from finllm.indicators.scorecard import growth         # noqa: F401
from finllm.indicators.scorecard import risk           # noqa: F401
from finllm.indicators.scorecard import multi_timeframe  # noqa: F401

from finllm.markets.base import FundamentalSnapshot
from finllm.pipeline.context import Candidate


def compute_master_score(
    cand: Candidate,
    universe_fundamentals: dict[str, FundamentalSnapshot] | None = None,
    universe_dollar_volumes: dict[str, float] | None = None,
) -> MasterScore:
    """67-kriterli master scorecard hesapla.

    Args:
        cand: Stage 1C sonrasi Candidate (indicators dolu)
        universe_fundamentals: tum aktif adaylarin fundamentals'i (cross-section icin)
        universe_dollar_volumes: ticker -> close*vol_sma_20 (cross-section icin)
    """
    ind = cand.indicators
    snap = cand.ingested.fundamentals
    prices = cand.ingested.prices
    quarterly = getattr(cand.ingested, "quarterly", None)

    # Compute universe percentiles for this ticker
    pctiles: dict[str, float] | None = None
    if universe_fundamentals and cand.ticker.symbol in universe_fundamentals:
        all_pctiles = _compute_universe_percentiles(universe_fundamentals)
        pctiles = all_pctiles.get(cand.ticker.symbol)

    # Add close to indicators if not present
    if "close" not in ind and prices is not None and not prices.empty:
        ind["close"] = float(prices["close"].iloc[-1])

    # Build context
    ctx = ScoringContext(
        ind=ind,
        snap=snap,
        prices=prices,
        quarterly=quarterly,
        pctiles=pctiles,
        universe_dollar_vols=universe_dollar_volumes,
        ticker_symbol=cand.ticker.symbol,
        cand=cand,
    )

    # Run all 67 criteria
    all_criteria: list[CriterionResult] = []
    for cdef in get_all_criteria():
        try:
            score, detail = cdef.fn(ctx)
            data_avail = detail != "N/A" and not detail.startswith("N/A")
            cr = CriterionResult(
                name=cdef.name,
                category=cdef.category,
                score=min(score, cdef.max_score),
                max_score=cdef.max_score,
                data_available=data_avail,
                detail=detail,
            )
        except Exception:
            cr = CriterionResult(
                name=cdef.name,
                category=cdef.category,
                score=0,
                max_score=cdef.max_score,
                data_available=False,
                detail="error",
            )
        all_criteria.append(cr)

    # Group by category
    cat_map: dict[str, list[CriterionResult]] = {cat: [] for cat in CATEGORY_ORDER}
    for cr in all_criteria:
        cat_map[cr.category].append(cr)

    categories: dict[str, CategoryScore] = {}
    total = 0
    max_possible = 0
    for cat_name in CATEGORY_ORDER:
        criteria = cat_map[cat_name]
        cat_score = sum(c.score for c in criteria)
        cat_max = sum(c.max_score for c in criteria)
        categories[cat_name] = CategoryScore(
            name=cat_name, score=cat_score, max_score=cat_max, criteria=criteria,
        )
        total += cat_score
        max_possible += cat_max

    pct = (total / max_possible * 100) if max_possible > 0 else 0.0

    return MasterScore(
        total=total,
        max_possible=max_possible,
        pct=pct,
        label=_label(pct),
        categories=categories,
        criteria=all_criteria,
    )


__all__ = [
    "CriterionResult",
    "CategoryScore",
    "MasterScore",
    "ScoringContext",
    "compute_master_score",
]
