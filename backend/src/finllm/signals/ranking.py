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


def _fmt(v, pct=False, suffix=""):
    if v is None:
        return "n/a"
    return f"{v*100:.1f}%" if pct else f"{v:.2f}{suffix}"


def build_debate_block(
    symbol: str,
    setup_score: float,
    snap: FundamentalSnapshot | None = None,
    *,
    finnhub: FinnhubSignals | None = None,
    sector_appetite: float = 0.5,
    rr: RiskRewardScore | None = None,
) -> str:
    """Assemble the per-stock DATA BLOCK fed to the Faz C debate — all signals in
    one text view so bull/bear arguments can anchor to specific figures."""
    rr = rr or score_risk_reward(snap, None, sector_appetite, finnhub)
    lines = [f"[{symbol}] medium-term long candidate", ""]
    lines.append(f"[TECHNICAL] setup score {setup_score:.2f} (0-1; entry-timing quality)")

    if snap is not None:
        lines += [
            "[FUNDAMENTALS]",
            f"  sector {snap.sector or 'n/a'} | P/E {_fmt(snap.pe_ratio)} (fwd {_fmt(snap.forward_pe)}) | "
            f"PEG {_fmt(snap.peg_ratio)} | P/B {_fmt(snap.pb_ratio)}",
            f"  ROE {_fmt(snap.roe, pct=True)} | profit margin {_fmt(snap.profit_margin, pct=True)} | "
            f"rev growth {_fmt(snap.revenue_growth_yoy, pct=True)} | earnings growth {_fmt(snap.earnings_growth_yoy, pct=True)}",
            f"  D/E {_fmt(snap.debt_to_equity)} | current ratio {_fmt(snap.current_ratio)} | "
            f"FCF {'positive' if (snap.free_cash_flow or 0) > 0 else 'NEGATIVE' if snap.free_cash_flow is not None else 'n/a'}",
        ]
    else:
        lines.append("[FUNDAMENTALS] n/a")

    if finnhub is not None:
        lines.append(
            f"[EARNINGS/ANALYST] earnings {finnhub.earnings_momentum} "
            f"(streak {finnhub.beat_streak}Q, avg surprise {_fmt(finnhub.avg_surprise_pct, suffix='%')}) | "
            f"analyst {finnhub.analyst_label} ({_fmt(finnhub.analyst_score)}, n={finnhub.n_analysts})"
        )

    lines.append(f"[MACRO] sector appetite {sector_appetite:.2f} (0.5 neutral; >0.5 tailwind)")
    lines.append(
        f"[RISK/REWARD] reward {rr.reward:.0f} | risk {rr.risk:.0f} | quality {rr.quality_flag} | "
        f"composite {rr.composite:.0f}/100"
        + (f" | drivers: {'; '.join(rr.notes)}" if rr.notes else "")
    )
    return "\n".join(lines)


__all__ = [
    "CandidateScore", "score_candidate", "rank_candidates",
    "build_debate_block", "W_RISK_REWARD", "W_TECHNICAL",
]
