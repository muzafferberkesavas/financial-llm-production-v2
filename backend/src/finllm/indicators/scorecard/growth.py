"""BUYUME kategorisi — 6 kriter, ~20 puan.

c61 gross_margin_stability ve c64 operating_leverage eklendi.
"""
from __future__ import annotations

from finllm.indicators.scorecard._helpers import _quintile_score
from finllm.indicators.scorecard._registry import criterion
from finllm.indicators.scorecard._types import ScoringContext


@criterion("revenue_growth_relative", "BUYUME", 4)
def c40_rev_growth(ctx: ScoringContext) -> tuple[int, str]:
    snap = ctx.snap
    if snap is None or snap.revenue_growth_yoy is None:
        return 0, "N/A"
    if ctx.pctiles:
        s = _quintile_score(ctx.pctiles.get("rev_growth", 0.5), (4, 3, 2, 1, 0))
        return s, f"rev_g={snap.revenue_growth_yoy:.2%} pct={ctx.pctiles.get('rev_growth', 0.5):.2f} -> {s}/4"
    if snap.revenue_growth_yoy > 0.30:
        s = 4
    elif snap.revenue_growth_yoy > 0.15:
        s = 3
    elif snap.revenue_growth_yoy > 0.05:
        s = 2
    elif snap.revenue_growth_yoy > 0:
        s = 1
    else:
        s = 0
    return s, f"rev_g={snap.revenue_growth_yoy:.2%} (abs) -> {s}/4"


@criterion("earnings_growth_relative", "BUYUME", 4)
def c41_earn_growth(ctx: ScoringContext) -> tuple[int, str]:
    snap = ctx.snap
    if snap is None or snap.earnings_growth_yoy is None:
        return 0, "N/A"
    if ctx.pctiles:
        s = _quintile_score(ctx.pctiles.get("earn_growth", 0.5), (4, 3, 2, 1, 0))
        return s, f"earn_g={snap.earnings_growth_yoy:.2%} pct={ctx.pctiles.get('earn_growth', 0.5):.2f} -> {s}/4"
    if snap.earnings_growth_yoy > 0.30:
        s = 4
    elif snap.earnings_growth_yoy > 0.15:
        s = 3
    elif snap.earnings_growth_yoy > 0.05:
        s = 2
    elif snap.earnings_growth_yoy > 0:
        s = 1
    else:
        s = 0
    return s, f"earn_g={snap.earnings_growth_yoy:.2%} (abs) -> {s}/4"


@criterion("revenue_acceleration", "BUYUME", 3)
def c42_rev_acceleration(ctx: ScoringContext) -> tuple[int, str]:
    snap = ctx.snap
    if snap is None or snap.revenue_growth_quarterly is None or snap.revenue_growth_yoy is None:
        return 0, "N/A"
    if snap.revenue_growth_quarterly > snap.revenue_growth_yoy:
        s = 3
    elif abs(snap.revenue_growth_quarterly - snap.revenue_growth_yoy) < 0.02:
        s = 2
    else:
        s = 0
    return s, f"q={snap.revenue_growth_quarterly:.2%} y={snap.revenue_growth_yoy:.2%} -> {s}/3"


@criterion("earnings_surprise", "BUYUME", 3)
def c43_earnings_surprise(ctx: ScoringContext) -> tuple[int, str]:
    snap = ctx.snap
    if snap is None or snap.last_earnings_surprise_pct is None:
        return 0, "N/A"
    pct = snap.last_earnings_surprise_pct
    if pct > 5:
        s = 3
    elif pct > 2:
        s = 2
    elif pct > 0:
        s = 1
    else:
        s = 0
    return s, f"{pct:+.1f}% -> {s}/3"


@criterion("gross_margin_stability", "BUYUME", 3)
def c61_gross_margin_stability(ctx: ScoringContext) -> tuple[int, str]:
    """Ceyreklik brut marj standart sapmasi (dusuk = stabil = iyi)."""
    q = ctx.quarterly
    if q is None:
        return 0, "N/A"
    gm_std = getattr(q, "gross_margin_std", None)
    if gm_std is None:
        return 0, "N/A"
    if gm_std < 0.02:
        s = 3
    elif gm_std < 0.05:
        s = 2
    elif gm_std < 0.10:
        s = 1
    else:
        s = 0
    return s, f"gm_std={gm_std:.3f} -> {s}/3"


@criterion("operating_leverage", "BUYUME", 3)
def c64_operating_leverage(ctx: ScoringContext) -> tuple[int, str]:
    """earnings_growth / revenue_growth — isletme kaldirac etkisi."""
    snap = ctx.snap
    if snap is None or snap.earnings_growth_yoy is None or snap.revenue_growth_yoy is None:
        return 0, "N/A"
    if snap.revenue_growth_yoy == 0 or snap.revenue_growth_yoy < -0.5:
        return 0, "N/A (no rev growth)"
    leverage = snap.earnings_growth_yoy / snap.revenue_growth_yoy
    if leverage > 2.0 and snap.earnings_growth_yoy > 0:
        s = 3  # strong positive operating leverage
    elif leverage > 1.0 and snap.earnings_growth_yoy > 0:
        s = 2
    elif leverage > 0 and snap.earnings_growth_yoy > 0:
        s = 1
    else:
        s = 0
    return s, f"leverage={leverage:.2f} -> {s}/3"
