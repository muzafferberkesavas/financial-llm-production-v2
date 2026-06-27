"""Decision panel orchestrator — the funnel's final assembly (Faz C wiring).

Ties the whole stack into one flow: score every candidate (technical + risk/reward
+ macro), rank by medium-term priority, then run the bull/bear debate ONLY on the
top-N so LLM cost stays bounded. Returns ranked candidates + debate verdicts.

Side-effect-free over already-fetched data (data fetching lives in the caller),
so it's reusable by both the live pipeline and the demo, and testable offline.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from finllm.data.finnhub_fundamentals import FinnhubSignals
from finllm.llm.debate import DebateResult
from finllm.llm.macro_sector import MacroSectorAnalysis
from finllm.markets.base import FundamentalSnapshot
from finllm.portfolio.sector_gate import normalize_sector
from finllm.signals.ranking import (
    CandidateScore,
    build_debate_block,
    rank_candidates,
    score_candidate,
)
from finllm.utils.logging import logger


@dataclass(slots=True)
class CandidateInput:
    symbol: str
    setup_score: float
    snap: FundamentalSnapshot | None = None
    finnhub: FinnhubSignals | None = None
    rr: object = None    # precomputed RiskRewardScore (e.g. BIST-relative); overrides
    news: list = field(default_factory=list)  # extra context (KAP/Turkish news)
    momentum: float | None = None  # 12-1m price momentum (factor for the debate)


@dataclass(slots=True)
class PanelDecision:
    candidate: CandidateScore
    debate: DebateResult | None = None


@dataclass(slots=True)
class PanelResult:
    ranked: list[CandidateScore] = field(default_factory=list)
    decisions: list[PanelDecision] = field(default_factory=list)
    total_cost_usd: float = 0.0

    def actionable(self) -> list[PanelDecision]:
        """Top-N decisions the judge said to buy."""
        return [d for d in self.decisions
                if d.debate and d.debate.action in ("AL", "GUCLU_AL") and d.debate.position_size_pct > 0]


def _appetite(macro: MacroSectorAnalysis | None, sector: str | None) -> float:
    if macro is None or not sector:
        return 0.5
    return macro.appetite_for(normalize_sector(sector), default=0.5)


def run_decision_panel(
    inputs: list[CandidateInput],
    *,
    macro: MacroSectorAnalysis | None = None,
    top_n: int = 5,
    run_debate: bool = True,
    debate_client=None,
) -> PanelResult:
    """Score + rank all candidates, then debate the top-N.

    macro: the day's MacroSectorAnalysis (sector appetites). None → neutral.
    debate_client: a DebateClient; required if run_debate and top_n > 0.
    """
    scored: list[tuple[CandidateScore, CandidateInput]] = []
    for inp in inputs:
        sector = inp.snap.sector if inp.snap else None
        appetite = _appetite(macro, sector)
        cs = score_candidate(
            inp.symbol, inp.setup_score, inp.snap,
            finnhub=inp.finnhub, sector_appetite=appetite, rr=inp.rr,
        )
        scored.append((cs, inp))

    ranked = rank_candidates([cs for cs, _ in scored])
    by_symbol = {cs.symbol: inp for cs, inp in scored}

    result = PanelResult(ranked=ranked)
    if not run_debate or top_n <= 0:
        # Debate yok (ör. --no-debate, $0 anahtarsız mod): yine de top-N adayı
        # debate=None ile karar olarak ekle. Böylece export/serileştirme teknik
        # sıralamayı "IZLE" sinyali olarak UI'a yazabilir (LLM çağrısı olmadan).
        if top_n > 0:
            result.decisions = [PanelDecision(candidate=cs) for cs in ranked[:top_n]]
        return result
    if debate_client is None:
        raise ValueError("run_debate=True requires a debate_client")

    for cs in ranked[:top_n]:
        inp = by_symbol[cs.symbol]
        block = build_debate_block(
            cs.symbol, cs.setup_score, inp.snap,
            finnhub=inp.finnhub, sector_appetite=cs.macro_appetite, news=inp.news,
            momentum=inp.momentum,
        )
        d = debate_client.debate(cs.symbol, block)
        result.total_cost_usd += d.cost_usd
        result.decisions.append(PanelDecision(candidate=cs, debate=d))

    logger.info(
        f"[PANEL] {len(ranked)} ranked, {len(result.decisions)} debated, "
        f"{len(result.actionable())} actionable, cost=${result.total_cost_usd:.4f}"
    )
    return result


__all__ = ["CandidateInput", "PanelDecision", "PanelResult", "run_decision_panel"]
