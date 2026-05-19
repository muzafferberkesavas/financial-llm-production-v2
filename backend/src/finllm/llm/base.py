"""LLM client protokolü — Stage 2 (cheap screen) ve Stage 3 (deep analysis).

Pipeline kodu LLM provider'ından bağımsız kalır. Phase 1'de MockLLM,
Phase 2'de Anthropic SDK (Claude) ve Google SDK (Gemini) eklenecek.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol, runtime_checkable


# ---- Stage 2 — Cheap screen verdict ----
@dataclass(slots=True)
class ScreenVerdict:
    """Stage 2'nin Stage 3'e gönderilecek hisseleri seçmek için verdiği etiket."""

    ticker: str
    verdict: Literal["strong", "potential", "skip"]
    rationale: str   # 1-2 cümle, kısa
    cost_usd: float = 0.0


# ---- Stage 3 — Deep analysis ----
@dataclass(slots=True)
class PriceScenarioOutput:
    label: Literal["base", "bull", "bear"]
    target_price: float
    probability: float
    expected_return_pct: float


@dataclass(slots=True)
class DeepAnalysis:
    """Stage 3 LLM çıktısı — ExtendedSignal'a dönüştürülecek tüm veri."""

    ticker: str

    # Core decision
    signal: Literal["GUCLU_AL", "AL", "IZLE", "TUT", "KISMI_SAT", "SAT", "ACIL_SAT"]
    confidence: float

    # Price targets
    entry_zone_low: float | None = None
    entry_zone_high: float | None = None
    stop_loss: float | None = None
    scenarios: list[PriceScenarioOutput] = field(default_factory=list)
    expected_return_pct: float | None = None
    time_horizon_days: int | None = None

    # Rationale (analyst-grade structured output)
    rationale_trend: str = ""
    rationale_formation: str = ""
    rationale_volume: str = ""
    rationale_news: str = ""
    rationale_fibonacci: str = ""
    rationale_risks: list[str] = field(default_factory=list)
    rationale_full: str = ""

    # Quality
    warning_flags: list[str] = field(default_factory=list)
    unsourced_flag: bool = False

    # Audit
    model: str = ""
    cost_usd: float = 0.0


@runtime_checkable
class LLMClient(Protocol):
    """Stage 2 ve Stage 3 LLM çağrıları için ortak arayüz."""

    name: str          # "claude-opus-4-7" | "claude-haiku-4-5" | "gemini-3-pro" | "mock"
    cost_per_1k_input: float
    cost_per_1k_output: float

    def screen(self, data_block: str) -> ScreenVerdict:
        """Stage 2 — Tek hisse için strong/potential/skip kararı.

        Args:
            data_block: PromptBuilder'ın çıktısı, bir hisse için tüm metrikler.

        Returns:
            ScreenVerdict.
        """
        ...

    def deep_analyze(self, data_block: str) -> DeepAnalysis:
        """Stage 3 — Tek hisse için tam multi-layer analiz + scenarios.

        Args:
            data_block: PromptBuilder'ın çıktısı, lib.zip formatında.

        Returns:
            DeepAnalysis with signal, confidence, scenarios, rationale.
        """
        ...


__all__ = [
    "DeepAnalysis",
    "LLMClient",
    "PriceScenarioOutput",
    "ScreenVerdict",
]
