"""DEGER kategorisi — 6 kriter, ~21 puan.

c58 ev_sales eklendi.
c34 PEG: negatif EPS -> otomatik 0.
"""
from __future__ import annotations

from finllm.indicators.scorecard._helpers import _quintile_score
from finllm.indicators.scorecard._registry import criterion
from finllm.indicators.scorecard._types import ScoringContext


@criterion("pe_ratio_relative", "DEGER", 4)
def c30_pe(ctx: ScoringContext) -> tuple[int, str]:
    snap = ctx.snap
    if snap is None or snap.pe_ratio is None or snap.pe_ratio <= 0:
        return 0, "N/A"
    if ctx.pctiles:
        s = _quintile_score(ctx.pctiles.get("pe", 0.5), (4, 3, 2, 1, 0))
        return s, f"PE={snap.pe_ratio:.1f} pct={ctx.pctiles.get('pe', 0.5):.2f} -> {s}/4"
    if snap.pe_ratio < 8:
        s = 4
    elif snap.pe_ratio < 15:
        s = 3
    elif snap.pe_ratio < 25:
        s = 2
    else:
        s = 0
    return s, f"PE={snap.pe_ratio:.1f} (abs) -> {s}/4"


@criterion("pb_ratio_relative", "DEGER", 3)
def c31_pb(ctx: ScoringContext) -> tuple[int, str]:
    snap = ctx.snap
    if snap is None or snap.pb_ratio is None or snap.pb_ratio <= 0:
        return 0, "N/A"
    if ctx.pctiles:
        s = _quintile_score(ctx.pctiles.get("pb", 0.5), (3, 2, 1, 0, 0))
        return s, f"PB={snap.pb_ratio:.1f} pct={ctx.pctiles.get('pb', 0.5):.2f} -> {s}/3"
    if snap.pb_ratio < 1.5:
        s = 3
    elif snap.pb_ratio < 3:
        s = 2
    else:
        s = 0
    return s, f"PB={snap.pb_ratio:.1f} (abs) -> {s}/3"


@criterion("ev_ebitda_relative", "DEGER", 4)
def c32_ev_ebitda(ctx: ScoringContext) -> tuple[int, str]:
    snap = ctx.snap
    if snap is None or snap.ev_to_ebitda is None or snap.ev_to_ebitda <= 0:
        return 0, "N/A"
    if ctx.pctiles:
        s = _quintile_score(ctx.pctiles.get("ev_ebitda", 0.5), (4, 3, 2, 1, 0))
        return s, f"EV/EBITDA={snap.ev_to_ebitda:.1f} pct={ctx.pctiles.get('ev_ebitda', 0.5):.2f} -> {s}/4"
    if snap.ev_to_ebitda < 6:
        s = 4
    elif snap.ev_to_ebitda < 10:
        s = 3
    elif snap.ev_to_ebitda < 15:
        s = 2
    else:
        s = 0
    return s, f"EV/EBITDA={snap.ev_to_ebitda:.1f} (abs) -> {s}/4"


@criterion("forward_pe_vs_trailing", "DEGER", 4)
def c33_forward_vs_trailing(ctx: ScoringContext) -> tuple[int, str]:
    snap = ctx.snap
    if snap is None or snap.forward_pe is None or snap.pe_ratio is None or snap.pe_ratio <= 0:
        return 0, "N/A"
    ratio = snap.forward_pe / snap.pe_ratio
    if ratio < 0.85:
        s = 4
    elif ratio < 1.0:
        s = 3
    elif ratio == 1.0:
        s = 1
    else:
        s = 0
    return s, f"fwd/trail={ratio:.2f} -> {s}/4"


@criterion("peg_ratio", "DEGER", 3)
def c34_peg(ctx: ScoringContext) -> tuple[int, str]:
    snap = ctx.snap
    if snap is None or snap.peg_ratio is None:
        return 0, "N/A"
    if snap.peg_ratio <= 0:
        return 0, f"PEG={snap.peg_ratio:.2f} (neg EPS) -> 0/3"
    if snap.peg_ratio < 1.0:
        s = 3
    elif snap.peg_ratio < 1.5:
        s = 2
    elif snap.peg_ratio < 2.0:
        s = 1
    else:
        s = 0
    return s, f"PEG={snap.peg_ratio:.2f} -> {s}/3"


@criterion("ev_sales_relative", "DEGER", 3)
def c58_ev_sales(ctx: ScoringContext) -> tuple[int, str]:
    """EV/Revenue percentile."""
    snap = ctx.snap
    if snap is None or snap.ev_to_revenue is None or snap.ev_to_revenue <= 0:
        return 0, "N/A"
    if ctx.pctiles:
        s = _quintile_score(ctx.pctiles.get("ev_revenue", 0.5), (3, 2, 1, 0, 0))
        return s, f"EV/S={snap.ev_to_revenue:.1f} pct={ctx.pctiles.get('ev_revenue', 0.5):.2f} -> {s}/3"
    if snap.ev_to_revenue < 1:
        s = 3
    elif snap.ev_to_revenue < 3:
        s = 2
    elif snap.ev_to_revenue < 5:
        s = 1
    else:
        s = 0
    return s, f"EV/S={snap.ev_to_revenue:.1f} (abs) -> {s}/3"
