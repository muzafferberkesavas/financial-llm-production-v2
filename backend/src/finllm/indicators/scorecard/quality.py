"""KALITE kategorisi — 7 kriter, ~25 puan.

c39 binary FCF -> c57 fcf_yield ile degistirildi.
c62 accruals_quality ve c63p analyst_consensus eklendi.
"""
from __future__ import annotations

from finllm.indicators.scorecard._helpers import _quintile_score
from finllm.indicators.scorecard._registry import criterion
from finllm.indicators.scorecard._types import ScoringContext


@criterion("roe_relative", "KALITE", 4)
def c35_roe(ctx: ScoringContext) -> tuple[int, str]:
    snap = ctx.snap
    if snap is None or snap.roe is None:
        return 0, "N/A"
    if ctx.pctiles:
        s = _quintile_score(ctx.pctiles.get("roe", 0.5), (4, 3, 2, 1, 0))
        return s, f"ROE={snap.roe:.2%} pct={ctx.pctiles.get('roe', 0.5):.2f} -> {s}/4"
    if snap.roe > 0.25:
        s = 4
    elif snap.roe > 0.15:
        s = 3
    elif snap.roe > 0.05:
        s = 2
    elif snap.roe > 0:
        s = 1
    else:
        s = 0
    return s, f"ROE={snap.roe:.2%} (abs) -> {s}/4"


@criterion("profit_margin_relative", "KALITE", 4)
def c36_margin(ctx: ScoringContext) -> tuple[int, str]:
    snap = ctx.snap
    if snap is None or snap.profit_margin is None:
        return 0, "N/A"
    if ctx.pctiles:
        s = _quintile_score(ctx.pctiles.get("margin", 0.5), (4, 3, 2, 1, 0))
        return s, f"margin={snap.profit_margin:.2%} pct={ctx.pctiles.get('margin', 0.5):.2f} -> {s}/4"
    if snap.profit_margin > 0.20:
        s = 4
    elif snap.profit_margin > 0.10:
        s = 3
    elif snap.profit_margin > 0.05:
        s = 2
    elif snap.profit_margin > 0:
        s = 1
    else:
        s = 0
    return s, f"margin={snap.profit_margin:.2%} (abs) -> {s}/4"


@criterion("debt_equity_safety", "KALITE", 4)
def c37_debt_equity(ctx: ScoringContext) -> tuple[int, str]:
    snap = ctx.snap
    if snap is None or snap.debt_to_equity is None:
        return 0, "N/A"
    if ctx.pctiles:
        s = _quintile_score(ctx.pctiles.get("debt_equity", 0.5), (4, 3, 2, 1, 0))
        return s, f"D/E={snap.debt_to_equity:.1f} pct={ctx.pctiles.get('debt_equity', 0.5):.2f} -> {s}/4"
    de = snap.debt_to_equity / 100 if snap.debt_to_equity > 5 else snap.debt_to_equity
    if de < 0.3:
        s = 4
    elif de < 0.7:
        s = 3
    elif de < 1.5:
        s = 2
    elif de < 2.5:
        s = 1
    else:
        s = 0
    return s, f"D/E={snap.debt_to_equity:.1f} (abs) -> {s}/4"


@criterion("current_ratio", "KALITE", 3)
def c38_current_ratio(ctx: ScoringContext) -> tuple[int, str]:
    snap = ctx.snap
    if snap is None or snap.current_ratio is None:
        return 0, "N/A"
    if snap.current_ratio > 2.0:
        s = 3
    elif snap.current_ratio > 1.5:
        s = 2
    elif snap.current_ratio > 1.0:
        s = 1
    else:
        s = 0
    return s, f"{snap.current_ratio:.2f} -> {s}/3"


@criterion("fcf_yield", "KALITE", 4)
def c57_fcf_yield(ctx: ScoringContext) -> tuple[int, str]:
    """FCF / market_cap orani."""
    snap = ctx.snap
    if snap is None or snap.free_cash_flow is None or snap.market_cap is None or snap.market_cap <= 0:
        return 0, "N/A"
    fcf_yield = snap.free_cash_flow / snap.market_cap
    if fcf_yield > 0.08:
        s = 4
    elif fcf_yield > 0.05:
        s = 3
    elif fcf_yield > 0.02:
        s = 2
    elif fcf_yield > 0:
        s = 1
    else:
        s = 0
    return s, f"FCF yield={fcf_yield:.2%} -> {s}/4"


@criterion("accruals_quality", "KALITE", 3)
def c62_accruals_quality(ctx: ScoringContext) -> tuple[int, str]:
    """(net_income - OCF) / total_assets — dusuk accrual = kaliteli gelir."""
    snap = ctx.snap
    # Need quarterly data for OCF/total_assets
    q = ctx.quarterly
    if q is None:
        return 0, "N/A"

    net_income = getattr(q, "net_income", None)
    ocf = getattr(q, "operating_cash_flow", None)
    total_assets = getattr(q, "total_assets", None)

    if net_income is None or ocf is None or total_assets is None or total_assets == 0:
        return 0, "N/A"

    accrual_ratio = (net_income - ocf) / total_assets
    if accrual_ratio < -0.05:
        s = 3  # Cash > earnings, very good
    elif accrual_ratio < 0.05:
        s = 2  # reasonable
    elif accrual_ratio < 0.10:
        s = 1
    else:
        s = 0  # high accruals, earnings quality concern
    return s, f"accrual={accrual_ratio:.3f} -> {s}/3"


@criterion("analyst_consensus", "KALITE", 3)
def c63p_analyst_consensus(ctx: ScoringContext) -> tuple[int, str]:
    """Analyst consensus proxy (FundamentalSnapshot'tan)."""
    snap = ctx.snap
    # analyst_score may not exist on all snapshots — use getattr safely
    score = getattr(snap, "analyst_score", None) if snap else None
    if score is None:
        return 0, "N/A"
    # analyst_score: 1=strong_sell, 5=strong_buy
    if score >= 4.0:
        s = 3
    elif score >= 3.5:
        s = 2
    elif score >= 3.0:
        s = 1
    else:
        s = 0
    return s, f"analyst={score:.1f} -> {s}/3"
