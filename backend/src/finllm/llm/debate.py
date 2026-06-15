"""Faz C — multi-agent bull/bear debate + judge (ARCHITECTURE.md §1 K3).

Two structured calls per stock (cost-aware panel design):
  1. Adversary  → strongest bull case + strongest bear case, each data-anchored.
  2. Judge      → final action + confidence + position size + key risks, weighing
                  the disagreement.

Model: Sonnet 4.6 (agentic financial reasoning ≈/> Opus at ~1/5 cost). Reuses
claude.py cost-tracking + prompt caching + tool-calling. Run only on the top-N
ranked candidates (signals/ranking) so cost stays bounded.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from anthropic import APIError

from finllm.llm.claude import (
    PRICING,
    _BaseClaudeClient,
    _calculate_cost,
    _extract_tool_input,
)
from finllm.skills import load_skill
from finllm.utils.logging import logger

DEBATE_TOOL = {
    "name": "produce_debate",
    "description": "Output the strongest bull and bear cases, each anchored to the data.",
    "input_schema": {
        "type": "object",
        "required": ["bull_points", "bear_points"],
        "properties": {
            "bull_points": {
                "type": "array", "minItems": 1, "maxItems": 4,
                "items": {
                    "type": "object", "required": ["claim", "evidence"],
                    "properties": {
                        "claim": {"type": "string", "maxLength": 160},
                        "evidence": {"type": "string", "maxLength": 200,
                                     "description": "Specific figure/signal from the data block"},
                    },
                },
            },
            "bear_points": {
                "type": "array", "minItems": 1, "maxItems": 4,
                "items": {
                    "type": "object", "required": ["claim", "evidence"],
                    "properties": {
                        "claim": {"type": "string", "maxLength": 160},
                        "evidence": {"type": "string", "maxLength": 200},
                    },
                },
            },
        },
    },
}

VERDICT_TOOL = {
    "name": "produce_verdict",
    "description": "Final medium-term decision weighing the bull and bear cases.",
    "input_schema": {
        "type": "object",
        "required": ["action", "confidence", "position_size_pct", "rationale"],
        "properties": {
            "action": {"type": "string",
                       "enum": ["GUCLU_AL", "AL", "IZLE", "TUT", "KISMI_SAT", "SAT"]},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "position_size_pct": {"type": "number", "minimum": 0, "maximum": 100,
                                  "description": "% of portfolio; 0 = no trade"},
            "time_horizon_days": {"type": ["integer", "null"], "minimum": 1, "maximum": 180},
            "key_risks": {"type": "array", "maxItems": 5, "items": {"type": "string", "maxLength": 160}},
            "rationale": {"type": "string", "maxLength": 800,
                          "description": "Name the decisive bull AND bear points"},
        },
    },
}


@dataclass(slots=True)
class DebatePoint:
    claim: str
    evidence: str


@dataclass(slots=True)
class DebateResult:
    symbol: str
    bull_points: list[DebatePoint] = field(default_factory=list)
    bear_points: list[DebatePoint] = field(default_factory=list)
    action: str = "TUT"
    confidence: float = 0.0
    position_size_pct: float = 0.0
    time_horizon_days: int | None = None
    key_risks: list[str] = field(default_factory=list)
    rationale: str = ""
    model: str = ""
    cost_usd: float = 0.0

    def as_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "action": self.action,
            "confidence": round(self.confidence, 2),
            "position_size_pct": round(self.position_size_pct, 1),
            "time_horizon_days": self.time_horizon_days,
            "bull": [p.claim for p in self.bull_points],
            "bear": [p.claim for p in self.bear_points],
            "key_risks": self.key_risks,
            "rationale": self.rationale,
            "cost_usd": round(self.cost_usd, 5),
        }


class DebateClient(_BaseClaudeClient):
    """Tiered 2-call bull/bear debate + judge per stock (Faz D model tiering).

    The adversary just extracts/anchors bull+bear points from the data → a cheap
    model (Haiku) suffices. The judge must WEIGH the disagreement and calibrate →
    a stronger reasoner (Sonnet). This is the research's cheap-analyst/strong-judge
    pattern; it cuts per-stock cost vs all-Sonnet while protecting the decision.
    """

    ADVERSARY_MODEL = "claude-haiku-4-5-20251001"
    JUDGE_MODEL = "claude-sonnet-4-6"

    def __init__(
        self,
        api_key: str | None = None,
        adversary_model: str | None = None,
        judge_model: str | None = None,
    ):
        super().__init__(api_key=api_key)
        self.adversary_model = adversary_model or self.ADVERSARY_MODEL
        self.judge_model = judge_model or self.JUDGE_MODEL
        self.name = self.judge_model
        self._adversary_skill = load_skill("debate-adversary")
        self._judge_skill = load_skill("debate-judge")

    def _system(self, skill: str) -> list[dict]:
        return [{"type": "text", "text": skill, "cache_control": {"type": "ephemeral"}}]

    def debate(self, symbol: str, data_block: str) -> DebateResult:
        result = DebateResult(symbol=symbol, model=self.name)

        # 1) adversary — bull + bear (cheap model)
        try:
            resp = self._call(
                model=self.adversary_model, system=self._system(self._adversary_skill),
                user_content=f"DATA BLOCK for {symbol}:\n\n{data_block}\n\nProduce the debate via the tool.",
                tools=[DEBATE_TOOL], tool_choice={"type": "tool", "name": "produce_debate"},
                max_tokens=1200,
            )
        except APIError as e:
            logger.error(f"[DEBATE] {symbol} adversary error: {e}")
            result.rationale = f"adversary API error: {e}"
            return result
        d = _extract_tool_input(resp, "produce_debate") or {}
        result.bull_points = [DebatePoint(p.get("claim", ""), p.get("evidence", "")) for p in d.get("bull_points", [])]
        result.bear_points = [DebatePoint(p.get("claim", ""), p.get("evidence", "")) for p in d.get("bear_points", [])]
        result.cost_usd += _calculate_cost(self.adversary_model, resp.usage)

        # 2) judge — verdict
        bull_txt = "\n".join(f"+ {p.claim} ({p.evidence})" for p in result.bull_points)
        bear_txt = "\n".join(f"- {p.claim} ({p.evidence})" for p in result.bear_points)
        judge_input = (
            f"DATA BLOCK for {symbol}:\n\n{data_block}\n\n"
            f"BULL CASE:\n{bull_txt}\n\nBEAR CASE:\n{bear_txt}\n\n"
            "Render the final medium-term verdict via the tool."
        )
        try:
            resp2 = self._call(
                model=self.judge_model, system=self._system(self._judge_skill),
                user_content=judge_input,
                tools=[VERDICT_TOOL], tool_choice={"type": "tool", "name": "produce_verdict"},
                max_tokens=1000,
            )
        except APIError as e:
            logger.error(f"[DEBATE] {symbol} judge error: {e}")
            result.rationale = f"judge API error: {e}"
            return result
        v = _extract_tool_input(resp2, "produce_verdict") or {}
        result.action = v.get("action", "TUT")
        result.confidence = float(v.get("confidence", 0.0))
        result.position_size_pct = float(v.get("position_size_pct", 0.0))
        result.time_horizon_days = v.get("time_horizon_days")
        result.key_risks = v.get("key_risks", [])
        result.rationale = v.get("rationale", "")
        result.cost_usd += _calculate_cost(self.name, resp2.usage)

        logger.info(
            f"[DEBATE] {symbol}: {result.action} conf={result.confidence:.2f} "
            f"size={result.position_size_pct:.1f}% cost=${result.cost_usd:.4f}"
        )
        return result


__all__ = ["DebateClient", "DebateResult", "DebatePoint"]
