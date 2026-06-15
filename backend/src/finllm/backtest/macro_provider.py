"""Macro providers for the backtest's sector gate (Faz B.3).

A provider maps an as-of date → that period's MacroSectorAnalysis. Two factories:
  • make_llm_macro_provider — real Sonnet calls on point-in-time macro context
    (FRED + prices, no news for history). Monthly-cached by the engine, so a
    3-year run is ~36 calls. THIS COSTS MONEY.
  • make_mock_macro_provider — deterministic, free; for wiring/integration tests.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from finllm.llm.macro_sector import MacroSectorAnalysis, SectorAppetite
from finllm.utils.logging import logger

MacroProvider = Callable[[str], "MacroSectorAnalysis | None"]


def _to_dict(a: MacroSectorAnalysis) -> dict:
    return {
        "overall_stance": a.overall_stance,
        "macro_summary": a.macro_summary,
        "sectors": [[s.sector, s.appetite, s.rationale] for s in a.sectors],
        "model": a.model,
        "cost_usd": a.cost_usd,
    }


def _from_dict(d: dict) -> MacroSectorAnalysis:
    return MacroSectorAnalysis(
        overall_stance=d["overall_stance"],
        macro_summary=d.get("macro_summary", ""),
        sectors=[SectorAppetite(s[0], float(s[1]), s[2] if len(s) > 2 else "") for s in d.get("sectors", [])],
        model=d.get("model", ""),
        cost_usd=float(d.get("cost_usd", 0.0)),
    )


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


def make_cached_llm_macro_provider(cache_path: str | Path, model: str | None = None):
    """LLM provider with a DISK cache keyed by month (YYYY-MM). The first run pays
    for each month's macro call; later runs (other gate modes, re-runs) reuse the
    saved JSON for free. Returns (provider, stats) where stats tracks live calls."""
    path = Path(cache_path)
    cache: dict[str, dict] = {}
    if path.exists():
        try:
            cache = json.loads(path.read_text())
        except Exception:  # noqa: BLE001
            cache = {}
    stats = {"live_calls": 0, "cache_hits": 0, "cost_usd": 0.0}
    inner = None  # lazily build the real client only if a live call is needed

    def provider(as_of: str) -> MacroSectorAnalysis | None:
        nonlocal inner
        month = as_of[:7]  # YYYY-MM
        if month in cache:
            stats["cache_hits"] += 1
            return _from_dict(cache[month])
        if inner is None:
            inner = make_llm_macro_provider(model)
        analysis = inner(as_of)
        if analysis is not None:
            cache[month] = _to_dict(analysis)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(cache, indent=2))
            stats["live_calls"] += 1
            stats["cost_usd"] += analysis.cost_usd
            logger.info(f"[MACRO-CACHE] {month} live call (${analysis.cost_usd:.4f})")
        return analysis

    return provider, stats


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


__all__ = [
    "make_llm_macro_provider",
    "make_cached_llm_macro_provider",
    "make_mock_macro_provider",
    "MacroProvider",
]
