"""Unified candidate ranker — the funnel's decision-fusion step.

Combines the three layers built so far into ONE rankable medium-term priority so
expensive downstream analysis (and capital) goes to the best risk/reward names:

  technical setup (0-1)  — entry timing quality (Stage 1B)
  risk/reward composite  — fundamentals + Finnhub earnings/analyst + macro→sector
                           appetite (indicators/risk_reward)

priority = 0.65·risk_reward + 0.35·(setup·100)

Medium-term focus → fundamentals/macro (risk_reward) carry most weight; the
technical setup times the entry. Pure function; feed it whatever data is on hand
(missing fundamentals → risk_reward defaults to 50, so technical still ranks).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from finllm.data.finnhub_fundamentals import FinnhubSignals
from finllm.indicators.fundamentals import FundamentalScore
from finllm.indicators.risk_reward import RiskRewardScore, score_risk_reward
from finllm.markets.base import FundamentalSnapshot

W_RISK_REWARD = 0.65
W_TECHNICAL = 0.35


@dataclass(slots=True)
class CandidateScore:
    symbol: str
    setup_score: float          # 0-1 technical
    risk_reward: float          # 0-100 composite
    macro_appetite: float       # 0-1
    quality_flag: str
    priority: float             # 0-100 final rankable
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "setup": round(self.setup_score, 3),
            "risk_reward": round(self.risk_reward, 1),
            "macro_appetite": round(self.macro_appetite, 2),
            "quality": self.quality_flag,
            "priority": round(self.priority, 1),
            "notes": self.notes,
        }


def score_candidate(
    symbol: str,
    setup_score: float,
    snap: FundamentalSnapshot | None = None,
    *,
    fund_score: FundamentalScore | None = None,
    finnhub: FinnhubSignals | None = None,
    sector_appetite: float = 0.5,
    rr: RiskRewardScore | None = None,
) -> CandidateScore:
    """Fuse technical setup + risk/reward into a medium-term priority for one name."""
    rr = rr or score_risk_reward(snap, fund_score, sector_appetite, finnhub)
    setup = max(0.0, min(1.0, setup_score))
    priority = W_RISK_REWARD * rr.composite + W_TECHNICAL * (setup * 100.0)
    priority = max(0.0, min(100.0, priority))
    return CandidateScore(
        symbol=symbol,
        setup_score=setup,
        risk_reward=rr.composite,
        macro_appetite=sector_appetite,
        quality_flag=rr.quality_flag,
        priority=priority,
        notes=rr.notes,
    )


def rank_candidates(candidates: list[CandidateScore]) -> list[CandidateScore]:
    """Highest priority first."""
    return sorted(candidates, key=lambda c: c.priority, reverse=True)


__all__ = ["CandidateScore", "score_candidate", "rank_candidates", "W_RISK_REWARD", "W_TECHNICAL"]
