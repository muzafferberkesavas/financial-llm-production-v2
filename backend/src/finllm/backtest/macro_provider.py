"""Macro providers for the backtest's sector gate (Faz B.3).

A provider maps an as-of date → that period's MacroSectorAnalysis. Two factories:
  • make_llm_macro_provider — real Sonnet calls on point-in-time macro context
    (FRED + prices, no news for history). Monthly-cached by the engine, so a
    3-year run is ~36 calls. THIS COSTS MONEY.
  • make_mock_macro_provider — deterministic, free; for wiring/integration tests.
"""
from __future__ import annotations

from typing import Callable

from finllm.llm.macro_sector import MacroSectorAnalysis, SectorAppetite

MacroProvider = Callable[[str], "MacroSectorAnalysis | None"]


def make_llm_macro_provider(model: str | None = None):
    """Real provider — builds point-in-time macro context and calls Sonnet.
    Each unique month triggers one API call (the engine caches by month)."""
    from finllm.data.macro import build_macro_context
    from finllm.llm.macro_sector import MacroSectorClient

    client = MacroSectorClient(model=model)

    def provider(as_of: str) -> MacroSectorAnalysis | None:
        ctx = build_macro_context(as_of=as_of, with_news=False)
        return client.analyze(ctx)

    return provider


def make_mock_macro_provider(
    energy_appetite: float = 0.2,
    tech_appetite: float = 0.8,
    stance: str = "risk_on",
):
    """Free deterministic provider for integration tests — Energy cold, Tech hot."""
    def provider(as_of: str) -> MacroSectorAnalysis | None:
        return MacroSectorAnalysis(
            overall_stance=stance,
            macro_summary=f"mock @ {as_of}",
            sectors=[
                SectorAppetite("Technology", tech_appetite, "mock"),
                SectorAppetite("Energy", energy_appetite, "mock"),
            ],
            model="mock",
            cost_usd=0.0,
        )

    return provider


__all__ = ["make_llm_macro_provider", "make_mock_macro_provider", "MacroProvider"]
