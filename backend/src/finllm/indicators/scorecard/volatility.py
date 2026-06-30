"""VOLATILITE kategorisi — 4 kriter, ~16 puan.

c24+c54 birlesti -> c24m swing_range_fitness.
"""
from __future__ import annotations

from finllm.indicators.scorecard._helpers import _g
from finllm.indicators.scorecard._registry import criterion
from finllm.indicators.scorecard._types import ScoringContext


@criterion("bb_position", "VOLATILITE", 4)
def c21_bb_position(ctx: ScoringContext) -> tuple[int, str]:
    v = _g(ctx.ind, "bb_pct")
    if v is None:
        return 0, "N/A"
    if 0.3 <= v <= 0.7:
        s = 4
    elif 0.05 <= v < 0.3:
        s = 3
    elif 0.7 < v <= 0.9:
        s = 2
    elif v < 0.05:
        s = 2
    else:
        s = 0
    return s, f"%B={v:.2f} -> {s}/4"


@criterion("bb_squeeze", "VOLATILITE", 5)
def c22_bb_squeeze(ctx: ScoringContext) -> tuple[int, str]:
    sq = ctx.ind.get("bb_squeeze")
    wt = ctx.ind.get("bb_width_trend")
    if sq is None and wt is None:
        return 0, "N/A"
    if sq:
        s = 5
    elif wt == "NARROWING":
        s = 3
    elif wt == "WIDENING":
        s = 2
    elif wt == "STABLE":
        s = 1
    else:
        s = 1
    return s, f"squeeze={sq} trend={wt} -> {s}/5"


@criterion("volatility_ratio", "VOLATILITE", 4)
def c23_vol_ratio_20_60(ctx: ScoringContext) -> tuple[int, str]:
    v20 = _g(ctx.ind, "vol_20d")
    v60 = _g(ctx.ind, "vol_60d")
    if v20 is None or v60 is None or v60 == 0:
        return 0, "N/A"
    if v20 < v60 * 0.8:
        s = 4
    elif v20 < v60:
        s = 3
    elif v20 > v60 * 1.3:
        s = 1
    else:
        s = 2
    return s, f"20d={v20:.3f} 60d={v60:.3f} -> {s}/4"


@criterion("swing_range_fitness", "VOLATILITE", 3)
def c24m_swing_range_fitness(ctx: ScoringContext) -> tuple[int, str]:
    """ATR% + ADR% birlesmis swing uygunlugu."""
    atr_pct = _g(ctx.ind, "atr_pct")
    adr = _g(ctx.ind, "adr_pct")

    if atr_pct is None and adr is None:
        return 0, "N/A"

    atr_p = None
    if atr_pct is not None:
        atr_p = atr_pct * 100 if atr_pct < 1 else atr_pct

    score_parts = 0
    count = 0

    if atr_p is not None:
        count += 1
        if 2 <= atr_p <= 5:
            score_parts += 3
        elif 1 <= atr_p < 2 or 5 < atr_p <= 8:
            score_parts += 2
        elif atr_p > 8:
            score_parts += 0
        else:
            score_parts += 1

    if adr is not None:
        count += 1
        if 2.5 <= adr <= 6.0:
            score_parts += 3
        elif 2.0 <= adr < 2.5 or 6.0 < adr <= 8.0:
            score_parts += 2
        elif 1.5 <= adr < 2.0:
            score_parts += 1
        else:
            score_parts += 0

    s = min(round(score_parts / count) if count > 0 else 0, 3)
    parts = []
    if atr_p is not None:
        parts.append(f"ATR={atr_p:.1f}%")
    if adr is not None:
        parts.append(f"ADR={adr:.2f}%")
    return s, f"{' '.join(parts)} -> {s}/3"
