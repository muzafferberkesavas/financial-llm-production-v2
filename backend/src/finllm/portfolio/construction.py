"""Portfolio construction — turn per-name debate verdicts into one coherent,
risk-limited portfolio (the funnel's capital-allocation step).

Takes the judge's per-name position sizes (llm/debate) and applies portfolio-level
risk discipline the per-stock judge can't see:
  • max positions (concentration)
  • single-name cap
  • per-sector cap (avoid loading one theme)
  • total-exposure cap (keep cash; never lever)
Respects the judge's risk-sizing as the base — only ever scales DOWN — so a cautious
set of verdicts stays cautious (cash is a valid position).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from finllm.pipeline.decision_panel import PanelDecision
from finllm.portfolio.sector_gate import build_sector_map


@dataclass(slots=True)
class PortfolioConfig:
    max_positions: int = 7
    max_total_exposure_pct: float = 95.0   # always keep ≥5% cash
    max_sector_pct: float = 40.0           # one sector can't dominate
    max_position_pct: float = 25.0         # single-name cap
    min_position_pct: float = 2.0          # drop dust


@dataclass(slots=True)
class PortfolioPosition:
    symbol: str
    sector: str
    weight_pct: float
    action: str
    confidence: float


@dataclass(slots=True)
class Portfolio:
    positions: list[PortfolioPosition] = field(default_factory=list)
    cash_pct: float = 100.0
    total_exposure_pct: float = 0.0
    sector_exposure: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "positions": [
                {"symbol": p.symbol, "sector": p.sector, "weight_pct": round(p.weight_pct, 1),
                 "action": p.action, "confidence": round(p.confidence, 2)}
                for p in self.positions
            ],
            "cash_pct": round(self.cash_pct, 1),
            "total_exposure_pct": round(self.total_exposure_pct, 1),
            "sector_exposure": {k: round(v, 1) for k, v in self.sector_exposure.items()},
            "notes": self.notes,
        }


def construct_portfolio(
    decisions: list[PanelDecision],
    config: PortfolioConfig | None = None,
    sector_map: dict[str, str] | None = None,
) -> Portfolio:
    config = config or PortfolioConfig()
    sector_map = sector_map if sector_map is not None else build_sector_map()
    notes: list[str] = []

    # 1) actionable buys only, best confidence first
    actionable = [
        d for d in decisions
        if d.debate and d.debate.action in ("AL", "GUCLU_AL") and d.debate.position_size_pct > 0
    ]
    actionable.sort(key=lambda d: d.debate.confidence, reverse=True)
    if len(actionable) > config.max_positions:
        notes.append(f"capped to {config.max_positions} positions (had {len(actionable)})")
        actionable = actionable[: config.max_positions]

    # 2) base weights = judge size, clamped to single-name cap
    rows: list[PortfolioPosition] = []
    for d in actionable:
        sym = d.candidate.symbol
        w = min(d.debate.position_size_pct, config.max_position_pct)
        rows.append(PortfolioPosition(
            symbol=sym, sector=sector_map.get(sym, "Unknown"),
            weight_pct=w, action=d.debate.action, confidence=d.debate.confidence,
        ))

    # 3) per-sector cap — scale down a sector's names proportionally if over
    sector_tot: dict[str, float] = {}
    for p in rows:
        sector_tot[p.sector] = sector_tot.get(p.sector, 0.0) + p.weight_pct
    for sec, tot in sector_tot.items():
        if tot > config.max_sector_pct:
            scale = config.max_sector_pct / tot
            for p in rows:
                if p.sector == sec:
                    p.weight_pct *= scale
            notes.append(f"{sec} scaled to {config.max_sector_pct:.0f}% cap (was {tot:.0f}%)")

    # 4) total-exposure cap — scale everything down if over
    total = sum(p.weight_pct for p in rows)
    if total > config.max_total_exposure_pct:
        scale = config.max_total_exposure_pct / total
        for p in rows:
            p.weight_pct *= scale
        notes.append(f"total exposure scaled to {config.max_total_exposure_pct:.0f}% (was {total:.0f}%)")

    # 5) drop dust, finalize
    rows = [p for p in rows if p.weight_pct >= config.min_position_pct]
    total = sum(p.weight_pct for p in rows)
    sector_exp: dict[str, float] = {}
    for p in rows:
        sector_exp[p.sector] = sector_exp.get(p.sector, 0.0) + p.weight_pct

    return Portfolio(
        positions=rows,
        cash_pct=max(0.0, 100.0 - total),
        total_exposure_pct=total,
        sector_exposure=sector_exp,
        notes=notes,
    )


__all__ = ["PortfolioConfig", "PortfolioPosition", "Portfolio", "construct_portfolio"]
