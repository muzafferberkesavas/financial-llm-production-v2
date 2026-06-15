"""Sector gate — apply the macro→sector appetite layer to individual stock
signals (Faz B.2). This is where the general-to-specific funnel connects: the
top-down sector view (macro_sector.MacroSectorAnalysis) reshapes bottom-up stock
confidence before sizing.

Three configurable policies (the open design question, now made explicit):
  • weight  — scale confidence by sector appetite (default; soft, keeps optionality)
  • filter  — drop entries in sectors below an appetite floor (hard, fewer trades)
  • veto    — filter + block ALL new entries when the overall stance is risk_off
  • off     — passthrough (ablation / A-B baseline)

Designed to be cheap and side-effect free so it can run in both the live pipeline
and the backtest (where the lift is measured).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from finllm.llm.macro_sector import MacroSectorAnalysis

# Universe Ticker.sector names → macro layer SECTORS names (macro_sector.SECTORS).
_SECTOR_ALIASES = {
    "Financial": "Financials",
    "Healthcare": "Health Care",
    "Consumer Defensive": "Consumer Staples",
}

GateMode = Literal["weight", "filter", "veto", "off"]


def normalize_sector(name: str) -> str:
    """Map a universe sector label to the macro layer's canonical sector name."""
    return _SECTOR_ALIASES.get(name, name)


def build_sector_map() -> dict[str, str]:
    """symbol → canonical macro sector, from the NASDAQ universe (has .sector)."""
    from finllm.markets.universes.nasdaq import NASDAQ_ALL

    return {t.symbol: normalize_sector(t.sector) for t in NASDAQ_ALL}


@dataclass(slots=True)
class SectorGateConfig:
    mode: GateMode = "weight"
    weight_strength: float = 1.0     # [0,1]: 1.0 → appetite swings confidence ±50%
    filter_threshold: float = 0.40   # filter/veto: drop entries below this appetite
    risk_off_blocks: bool = True     # veto mode: risk_off stance blocks all new entries
    min_confidence: float = 0.0      # floor after weighting


@dataclass(slots=True)
class GateOutcome:
    keep: bool                 # may this signal open a new position?
    adjusted_confidence: float
    appetite: float
    reason: str


def weight_factor(appetite: float, strength: float) -> float:
    """appetite 0.5 → ×1.0; 1.0 → ×(1+0.5·strength); 0.0 → ×(1-0.5·strength)."""
    return 1.0 + (appetite - 0.5) * strength


def apply_sector_gate(
    confidence: float,
    sector: str,
    analysis: MacroSectorAnalysis | None,
    config: SectorGateConfig | None = None,
) -> GateOutcome:
    """Apply the macro→sector view to one stock signal's confidence / eligibility."""
    config = config or SectorGateConfig()
    if config.mode == "off" or analysis is None:
        return GateOutcome(True, confidence, 0.5, "gate off")

    macro_sector = normalize_sector(sector)
    appetite = analysis.appetite_for(macro_sector, default=0.5)

    if config.mode == "veto" and config.risk_off_blocks and analysis.overall_stance == "risk_off":
        return GateOutcome(False, confidence, appetite, "risk_off stance vetoes new entries")

    if config.mode in ("filter", "veto") and appetite < config.filter_threshold:
        return GateOutcome(
            False, confidence, appetite,
            f"{macro_sector} appetite {appetite:.2f} < {config.filter_threshold:.2f}",
        )

    if config.mode in ("filter", "veto"):
        return GateOutcome(True, confidence, appetite, f"{macro_sector} appetite {appetite:.2f} — pass")

    # weight (default)
    factor = weight_factor(appetite, config.weight_strength)
    adj = max(config.min_confidence, min(1.0, confidence * factor))
    return GateOutcome(
        True, adj, appetite,
        f"{macro_sector} appetite {appetite:.2f} → conf ×{factor:.2f}",
    )


__all__ = [
    "SectorGateConfig",
    "GateOutcome",
    "GateMode",
    "apply_sector_gate",
    "weight_factor",
    "normalize_sector",
    "build_sector_map",
]
