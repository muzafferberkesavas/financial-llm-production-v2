"""Macro→Sector appetite layer — the general-to-specific funnel's top tier.

Reads a macro/geopolitical context block and returns a risk stance plus a 0..1
appetite score per equity sector (ARCHITECTURE.md §1 K2, validated by the ICLR
2025 top-down sector-allocation pattern). Downstream, these appetites gate stock
signals (filter / confidence-weight / veto).

Model: Sonnet 4.6 — research shows it matches/beats Opus on agentic financial
reasoning at ~1/5 the cost, the right tier for this multi-step macro synthesis.
Reuses claude.py's cost-tracking, prompt-caching and structured-output plumbing.
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

# GICS 11 + a precious-metals (gold) cross-asset leg (user trades gold too).
SECTORS = [
    "Technology",
    "Communication Services",
    "Consumer Discretionary",
    "Consumer Staples",
    "Financials",
    "Health Care",
    "Industrials",
    "Energy",
    "Materials",
    "Utilities",
    "Real Estate",
    "Precious Metals",
]

MACRO_SECTOR_TOOL = {
    "name": "produce_sector_appetite",
    "description": "Output the top-down risk stance and per-sector appetite scores.",
    "input_schema": {
        "type": "object",
        "required": ["overall_stance", "macro_summary", "sectors"],
        "properties": {
            "overall_stance": {
                "type": "string",
                "enum": ["risk_on", "neutral", "risk_off"],
            },
            "macro_summary": {
                "type": "string",
                "description": "2-3 sentences: the regime and the dominant drivers. Flag thin context.",
                "maxLength": 600,
            },
            "sectors": {
                "type": "array",
                "minItems": 1,
                "maxItems": len(SECTORS),
                "items": {
                    "type": "object",
                    "required": ["sector", "appetite", "rationale"],
                    "properties": {
                        "sector": {"type": "string", "enum": SECTORS},
                        "appetite": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 1.0,
                            "description": "0.5 neutral; >0.5 tailwind; <0.5 headwind.",
                        },
                        "rationale": {
                            "type": "string",
                            "description": "1 sentence naming the specific macro driver.",
                            "maxLength": 240,
                        },
                    },
                },
            },
        },
    },
}


@dataclass(slots=True)
class SectorAppetite:
    sector: str
    appetite: float       # 0..1, 0.5 = neutral
    rationale: str


@dataclass(slots=True)
class MacroSectorAnalysis:
    overall_stance: str   # risk_on | neutral | risk_off
    macro_summary: str
    sectors: list[SectorAppetite] = field(default_factory=list)
    model: str = ""
    cost_usd: float = 0.0

    def appetite_for(self, sector: str, default: float = 0.5) -> float:
        for s in self.sectors:
            if s.sector.lower() == sector.lower():
                return s.appetite
        return default


class MacroSectorClient(_BaseClaudeClient):
    """Sonnet 4.6 — macro context → sector appetite scores."""

    name = "claude-sonnet-4-6"

    def __init__(self, api_key: str | None = None, model: str | None = None):
        super().__init__(api_key=api_key)
        if model:
            self.name = model
        self._system_skill = load_skill("macro-sector-analyst")
        self.cost_per_1k_input = PRICING[self.name]["input"] / 1000
        self.cost_per_1k_output = PRICING[self.name]["output"] / 1000

    def analyze(self, macro_context: str) -> MacroSectorAnalysis:
        system = [
            {
                "type": "text",
                "text": self._system_skill,
                "cache_control": {"type": "ephemeral"},  # skill cached → cheap reruns
            }
        ]
        user_content = (
            "MACRO CONTEXT:\n\n"
            f"{macro_context}\n\n"
            "Produce the risk stance and per-sector appetite scores via the tool."
        )
        try:
            response = self._call(
                model=self.name,
                system=system,
                user_content=user_content,
                tools=[MACRO_SECTOR_TOOL],
                tool_choice={"type": "tool", "name": "produce_sector_appetite"},
                max_tokens=1500,
            )
        except APIError as e:
            logger.error(f"[MACRO-SECTOR] API hatası: {e}")
            return MacroSectorAnalysis(
                overall_stance="neutral",
                macro_summary=f"API error: {e}",
                model=self.name,
                cost_usd=0.0,
            )

        parsed = _extract_tool_input(response, "produce_sector_appetite") or {}
        cost = _calculate_cost(self.name, response.usage)
        sectors = [
            SectorAppetite(
                sector=s.get("sector", "?"),
                appetite=float(s.get("appetite", 0.5)),
                rationale=s.get("rationale", ""),
            )
            for s in parsed.get("sectors", [])
            if "sector" in s
        ]
        logger.info(
            f"[MACRO-SECTOR] stance={parsed.get('overall_stance')} "
            f"sectors={len(sectors)} "
            f"tokens(in/out/cache_r)={response.usage.input_tokens}/"
            f"{response.usage.output_tokens}/"
            f"{getattr(response.usage, 'cache_read_input_tokens', 0)} "
            f"cost=${cost:.5f}"
        )
        return MacroSectorAnalysis(
            overall_stance=parsed.get("overall_stance", "neutral"),
            macro_summary=parsed.get("macro_summary", ""),
            sectors=sectors,
            model=self.name,
            cost_usd=cost,
        )


__all__ = ["MacroSectorClient", "MacroSectorAnalysis", "SectorAppetite", "SECTORS"]
