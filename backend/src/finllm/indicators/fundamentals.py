"""Fundamental scoring — value + quality + growth → 0-100.

3 alt-skor:
  - VALUE (40 pts): P/E, P/B, EV/EBITDA, PEG (düşük = iyi)
  - QUALITY (30 pts): ROE, profit margin, debt/equity, current ratio
  - GROWTH (30 pts): revenue growth, earnings growth

Sektör benchmarks (yaklaşık, US ortalaması):
  Technology: P/E=25, P/B=5, ROE=22%, profit_margin=18%, rev_growth=15%
  Financial: P/E=12, P/B=1.4, ROE=12%, profit_margin=22%, rev_growth=5%
  Healthcare: P/E=22, P/B=4, ROE=18%, profit_margin=12%, rev_growth=8%
  Consumer Defensive: P/E=20, P/B=4, ROE=20%, profit_margin=8%, rev_growth=5%
  Energy: P/E=10, P/B=1.5, ROE=15%, profit_margin=10%, rev_growth=8%
  Industrials: P/E=18, P/B=3, ROE=15%, profit_margin=10%, rev_growth=6%

Phase 3'te bu benchmark'lar canlı sektör medianı'ndan hesaplanır (cross-sectional).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from finllm.markets.base import FundamentalSnapshot

# Sektör benchmark'ları — Phase 3.1 hardcoded, Phase 3.2'de dynamic
SECTOR_BENCHMARKS: dict[str, dict[str, float]] = {
    "Technology": {
        "pe": 28.0, "pb": 6.0, "ev_ebitda": 22.0,
        "roe": 0.22, "profit_margin": 0.18,
        "revenue_growth": 0.15, "earnings_growth": 0.18,
    },
    "Financial Services": {
        "pe": 12.0, "pb": 1.4, "ev_ebitda": 12.0,
        "roe": 0.12, "profit_margin": 0.22,
        "revenue_growth": 0.05, "earnings_growth": 0.08,
    },
    "Healthcare": {
        "pe": 22.0, "pb": 4.0, "ev_ebitda": 18.0,
        "roe": 0.18, "profit_margin": 0.12,
        "revenue_growth": 0.08, "earnings_growth": 0.10,
    },
    "Consumer Defensive": {
        "pe": 20.0, "pb": 4.0, "ev_ebitda": 15.0,
        "roe": 0.20, "profit_margin": 0.08,
        "revenue_growth": 0.05, "earnings_growth": 0.07,
    },
    "Consumer Cyclical": {
        "pe": 18.0, "pb": 3.5, "ev_ebitda": 14.0,
        "roe": 0.18, "profit_margin": 0.07,
        "revenue_growth": 0.08, "earnings_growth": 0.10,
    },
    "Energy": {
        "pe": 10.0, "pb": 1.5, "ev_ebitda": 8.0,
        "roe": 0.15, "profit_margin": 0.10,
        "revenue_growth": 0.08, "earnings_growth": 0.10,
    },
    "Industrials": {
        "pe": 18.0, "pb": 3.0, "ev_ebitda": 14.0,
        "roe": 0.15, "profit_margin": 0.10,
        "revenue_growth": 0.06, "earnings_growth": 0.08,
    },
    "Communication Services": {
        "pe": 20.0, "pb": 4.0, "ev_ebitda": 12.0,
        "roe": 0.18, "profit_margin": 0.15,
        "revenue_growth": 0.08, "earnings_growth": 0.12,
    },
    "Default": {  # Fallback
        "pe": 18.0, "pb": 3.0, "ev_ebitda": 14.0,
        "roe": 0.15, "profit_margin": 0.12,
        "revenue_growth": 0.07, "earnings_growth": 0.10,
    },
}


@dataclass
class FundamentalScore:
    """Tek hisse fundamental scoring breakdown'u — Stage 1C ile entegre olur."""

    value_score: int = 0       # 0-40
    quality_score: int = 0     # 0-30
    growth_score: int = 0      # 0-30
    total: int = 0             # 0-100
    sector_used: str = "Default"

    # Detailed labels (LLM için)
    pe_label: str = "N/A"           # "cheap" | "fair" | "expensive" | "very_expensive"
    quality_label: str = "N/A"       # "high_quality" | "average" | "low"
    growth_label: str = "N/A"        # "high_growth" | "moderate" | "stagnant" | "declining"
    earnings_warning: bool = False   # Bilanço açıklaması <5 gün içindeyse

    def as_dict(self) -> dict[str, Any]:
        return {
            "value": self.value_score,
            "quality": self.quality_score,
            "growth": self.growth_score,
            "total": self.total,
            "sector": self.sector_used,
            "pe_label": self.pe_label,
            "quality_label": self.quality_label,
            "growth_label": self.growth_label,
            "earnings_warning": self.earnings_warning,
        }


def _get_benchmark(sector: str | None) -> tuple[dict[str, float], str]:
    if not sector:
        return SECTOR_BENCHMARKS["Default"], "Default"
    # Direct match
    if sector in SECTOR_BENCHMARKS:
        return SECTOR_BENCHMARKS[sector], sector
    # Fuzzy match
    for key in SECTOR_BENCHMARKS:
        if key.lower() in sector.lower() or sector.lower() in key.lower():
            return SECTOR_BENCHMARKS[key], key
    return SECTOR_BENCHMARKS["Default"], "Default"


def _score_value(snap: FundamentalSnapshot, bench: dict[str, float]) -> tuple[int, str]:
    """Düşük PE/PB/EV-EBITDA = iyi. Max 40 puan."""
    pts = 0
    labels = []

    pe = snap.pe_ratio
    if pe and pe > 0:
        ratio = pe / bench["pe"]
        if ratio < 0.7:
            pts += 12
            labels.append("cheap")
        elif ratio < 1.0:
            pts += 10
            labels.append("fair")
        elif ratio < 1.5:
            pts += 5
            labels.append("expensive")
        else:
            pts += 0
            labels.append("very_expensive")
    elif pe is not None and pe <= 0:
        # Negative PE = zarar ediyor
        labels.append("unprofitable")

    pb = snap.pb_ratio
    if pb and pb > 0:
        ratio = pb / bench["pb"]
        if ratio < 0.8:
            pts += 8
        elif ratio < 1.2:
            pts += 6
        elif ratio < 2.0:
            pts += 3
        else:
            pts += 0

    ev_ebitda = snap.ev_to_ebitda
    if ev_ebitda and ev_ebitda > 0:
        ratio = ev_ebitda / bench["ev_ebitda"]
        if ratio < 0.7:
            pts += 10
        elif ratio < 1.0:
            pts += 8
        elif ratio < 1.5:
            pts += 4
        else:
            pts += 0

    peg = snap.peg_ratio
    if peg and peg > 0:
        if peg < 1.0:
            pts += 10   # Growth at reasonable price (GARP)
        elif peg < 1.5:
            pts += 7
        elif peg < 2.0:
            pts += 3
        else:
            pts += 0

    label = labels[0] if labels else "no_data"
    return min(pts, 40), label


def _score_quality(snap: FundamentalSnapshot, bench: dict[str, float]) -> tuple[int, str]:
    """High ROE + margin + low debt = iyi. Max 30 puan."""
    pts = 0
    quality_signs = 0

    roe = snap.roe
    if roe is not None:
        ratio = roe / bench["roe"] if bench["roe"] > 0 else 0
        if ratio > 1.5:
            pts += 10
            quality_signs += 1
        elif ratio > 1.0:
            pts += 7
            quality_signs += 1
        elif ratio > 0.6:
            pts += 4
        else:
            pts += 0

    pm = snap.profit_margin
    if pm is not None:
        ratio = pm / bench["profit_margin"] if bench["profit_margin"] > 0 else 0
        if ratio > 1.5:
            pts += 8
            quality_signs += 1
        elif ratio > 1.0:
            pts += 6
            quality_signs += 1
        elif ratio > 0.6:
            pts += 3
        elif pm < 0:
            pts += 0   # Net loss
        else:
            pts += 1

    de = snap.debt_to_equity
    if de is not None:
        # yfinance D/E genellikle 100x ratio veriyor (örn 30 = %30)
        de_pct = de / 100.0 if de > 5 else de
        if de_pct < 0.5:
            pts += 8
            quality_signs += 1
        elif de_pct < 1.0:
            pts += 6
        elif de_pct < 2.0:
            pts += 3
        else:
            pts += 0

    cr = snap.current_ratio
    if cr is not None:
        if cr > 2.0:
            pts += 4
        elif cr > 1.2:
            pts += 3
        elif cr > 1.0:
            pts += 2
        else:
            pts += 0   # Likidite riski

    if quality_signs >= 2:
        label = "high_quality"
    elif quality_signs >= 1:
        label = "average"
    else:
        label = "low"

    return min(pts, 30), label


def _score_growth(snap: FundamentalSnapshot, bench: dict[str, float]) -> tuple[int, str]:
    """Revenue + earnings growth. Max 30 puan."""
    pts = 0
    growth_signs = 0
    is_declining = False

    rg = snap.revenue_growth_yoy
    if rg is not None:
        bench_rg = bench["revenue_growth"]
        if rg > 2 * bench_rg:
            pts += 15
            growth_signs += 1
        elif rg > bench_rg:
            pts += 12
            growth_signs += 1
        elif rg > bench_rg * 0.5:
            pts += 7
        elif rg > 0:
            pts += 3
        else:
            pts += 0
            is_declining = True

    eg = snap.earnings_growth_yoy
    if eg is not None:
        bench_eg = bench["earnings_growth"]
        if eg > 2 * bench_eg:
            pts += 15
            growth_signs += 1
        elif eg > bench_eg:
            pts += 12
            growth_signs += 1
        elif eg > bench_eg * 0.5:
            pts += 7
        elif eg > 0:
            pts += 3
        else:
            pts += 0
            is_declining = True

    if is_declining:
        label = "declining"
    elif growth_signs >= 2:
        label = "high_growth"
    elif growth_signs >= 1:
        label = "moderate"
    else:
        label = "stagnant"

    return min(pts, 30), label


def compute_fundamental_score(snap: FundamentalSnapshot | None) -> FundamentalScore:
    """Bir hisse için tam fundamental skoru."""
    score = FundamentalScore()

    if snap is None:
        return score

    bench, sector_used = _get_benchmark(snap.sector)
    score.sector_used = sector_used

    value_pts, value_label = _score_value(snap, bench)
    score.value_score = value_pts
    score.pe_label = value_label

    quality_pts, quality_label = _score_quality(snap, bench)
    score.quality_score = quality_pts
    score.quality_label = quality_label

    growth_pts, growth_label = _score_growth(snap, bench)
    score.growth_score = growth_pts
    score.growth_label = growth_label

    # Earnings warning — 5 gün içinde bilanço açıklanacaksa
    if snap.days_to_earnings is not None and 0 <= snap.days_to_earnings <= 5:
        score.earnings_warning = True

    score.total = score.value_score + score.quality_score + score.growth_score
    return score


__all__ = [
    "FundamentalScore",
    "SECTOR_BENCHMARKS",
    "compute_fundamental_score",
]
