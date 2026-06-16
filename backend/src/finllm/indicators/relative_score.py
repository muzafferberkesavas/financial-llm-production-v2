"""Universe-relative fundamental scoring (Faz E — honest BIST scoring).

The US-calibrated sector benchmarks (indicators/fundamentals) misrate BIST: Turkish
stocks trade at single-digit P/Es (inflation + risk premium) so they all look
'cheap', and nominal growth is inflation-inflated. The fix is to score each stock
by its PERCENTILE within the universe rather than against an absolute benchmark —
inflation-neutral (all names share it) and market-agnostic.

Produces a 0-100 composite per ticker from value (cheap), quality (ROE/margin),
growth, minus leverage risk — all as cross-sectional percentiles.
"""
from __future__ import annotations

from finllm.markets.base import FundamentalSnapshot


def _pct_ranks(values: dict[str, float | None], higher_better: bool) -> dict[str, float]:
    """Percentile rank (0..1) of each non-None value; None → 0.5 (neutral)."""
    present = {k: v for k, v in values.items() if v is not None}
    out: dict[str, float] = {k: 0.5 for k in values}
    n = len(present)
    if n <= 1:
        return out
    ordered = sorted(present.items(), key=lambda kv: kv[1], reverse=not higher_better)
    # rank 0 = worst → 1 = best
    for i, (k, _) in enumerate(ordered):
        out[k] = i / (n - 1)
    return out


def relative_composites(snaps: dict[str, FundamentalSnapshot]) -> dict[str, dict]:
    """ticker → {value, quality, growth, risk, composite} (cross-sectional)."""
    def col(attr, transform=lambda x: x):
        return {t: (transform(getattr(s, attr)) if getattr(s, attr) is not None else None)
                for t, s in snaps.items()}

    # value: cheaper P/E and P/B is better (lower → higher percentile)
    pe = _pct_ranks(col("pe_ratio", lambda v: v if v and v > 0 else None), higher_better=False)
    pb = _pct_ranks(col("pb_ratio", lambda v: v if v and v > 0 else None), higher_better=False)
    # quality: higher ROE + margin better
    roe = _pct_ranks(col("roe"), higher_better=True)
    margin = _pct_ranks(col("profit_margin"), higher_better=True)
    # growth: higher revenue growth better (inflation-neutral in relative terms)
    growth = _pct_ranks(col("revenue_growth_yoy"), higher_better=True)
    # risk: higher leverage worse (lower percentile = lower risk)
    lev = _pct_ranks(col("debt_to_equity"), higher_better=False)  # low D/E → high pct = good

    out: dict[str, dict] = {}
    for t in snaps:
        value = (pe[t] + pb[t]) / 2 * 100
        quality = (roe[t] + margin[t]) / 2 * 100
        grow = growth[t] * 100
        risk_ok = lev[t] * 100                     # high = low leverage = good
        # composite: reward (value+growth+quality) tempered by leverage safety
        composite = (0.30 * value + 0.25 * grow + 0.30 * quality + 0.15 * risk_ok)
        out[t] = {
            "value": round(value, 1), "quality": round(quality, 1),
            "growth": round(grow, 1), "risk_safety": round(risk_ok, 1),
            "composite": round(composite, 1),
        }
    return out


def to_risk_reward(rel: dict):
    """Convert one relative_composites entry → a RiskRewardScore (for the panel)."""
    from finllm.indicators.risk_reward import RiskRewardScore

    quality = rel["quality"]
    flag = "strong" if quality >= 66 else "ok" if quality >= 33 else "weak"
    reward = 0.4 * rel["value"] + 0.3 * rel["growth"] + 0.3 * rel["quality"]
    return RiskRewardScore(
        reward=round(reward, 1),
        risk=round(100 - rel["risk_safety"], 1),
        quality_flag=flag,
        composite=rel["composite"],
        notes=["BIST-relative (percentile) scoring"],
    )


__all__ = ["relative_composites", "to_risk_reward"]
