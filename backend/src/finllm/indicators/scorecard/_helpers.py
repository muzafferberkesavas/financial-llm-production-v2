"""Ortak yardimci fonksiyonlar."""
from __future__ import annotations

import pandas as pd

from finllm.indicators.relative_score import _pct_ranks
from finllm.indicators.scorecard._types import CriterionResult
from finllm.markets.base import FundamentalSnapshot


def _g(ind: dict, key: str):
    """Get indicator value, return None for missing/non-numeric."""
    v = ind.get(key)
    if v is None:
        return None
    if isinstance(v, str):
        return None
    return v


def _cr(name: str, category: str, score: int, max_score: int, detail: str,
        data_available: bool = True) -> CriterionResult:
    return CriterionResult(
        name=name, category=category,
        score=min(score, max_score), max_score=max_score,
        data_available=data_available, detail=detail,
    )


def _label(pct: float) -> str:
    if pct >= 80:
        return "MUKEMMEL"
    if pct >= 65:
        return "IYI"
    if pct >= 50:
        return "ORTA"
    if pct >= 35:
        return "ZAYIF"
    return "KOTU"


def _quintile_score(pct: float, scores: tuple[int, int, int, int, int]) -> int:
    """Map percentile (0-1, 1=best) to quintile score."""
    if pct >= 0.8:
        return scores[0]
    if pct >= 0.6:
        return scores[1]
    if pct >= 0.4:
        return scores[2]
    if pct >= 0.2:
        return scores[3]
    return scores[4]


def _pct_from_52w_high(prices: pd.DataFrame) -> float | None:
    """Pct below 52-week high. 0.0 = at high, 0.30 = %30 below."""
    if prices is None or prices.empty or len(prices) < 50:
        return None
    high_col = prices["high"].tail(252)
    if high_col.empty:
        return None
    high_52w = float(high_col.max())
    if high_52w <= 0:
        return None
    close = float(prices["close"].iloc[-1])
    return (high_52w - close) / high_52w


def _compute_universe_percentiles(
    universe_fundamentals: dict[str, FundamentalSnapshot],
) -> dict[str, dict[str, float]]:
    """ticker -> {metric_name: percentile (0-1)} for fundamental metrics."""
    if not universe_fundamentals:
        return {}

    def _col(attr, transform=lambda x: x):
        return {
            t: (transform(getattr(s, attr)) if getattr(s, attr) is not None else None)
            for t, s in universe_fundamentals.items()
        }

    pe_pct = _pct_ranks(_col("pe_ratio", lambda v: v if v and v > 0 else None), higher_better=False)
    pb_pct = _pct_ranks(_col("pb_ratio", lambda v: v if v and v > 0 else None), higher_better=False)
    ev_ebitda_pct = _pct_ranks(_col("ev_to_ebitda", lambda v: v if v and v > 0 else None), higher_better=False)
    de_pct = _pct_ranks(_col("debt_to_equity"), higher_better=False)

    roe_pct = _pct_ranks(_col("roe"), higher_better=True)
    margin_pct = _pct_ranks(_col("profit_margin"), higher_better=True)
    rev_growth_pct = _pct_ranks(_col("revenue_growth_yoy"), higher_better=True)
    earn_growth_pct = _pct_ranks(_col("earnings_growth_yoy"), higher_better=True)

    # New: ev_to_revenue percentile (lower is better)
    ev_rev_pct = _pct_ranks(
        _col("ev_to_revenue", lambda v: v if v and v > 0 else None),
        higher_better=False,
    )

    out: dict[str, dict[str, float]] = {}
    for t in universe_fundamentals:
        out[t] = {
            "pe": pe_pct[t],
            "pb": pb_pct[t],
            "ev_ebitda": ev_ebitda_pct[t],
            "roe": roe_pct[t],
            "margin": margin_pct[t],
            "debt_equity": de_pct[t],
            "rev_growth": rev_growth_pct[t],
            "earn_growth": earn_growth_pct[t],
            "ev_revenue": ev_rev_pct[t],
        }
    return out
