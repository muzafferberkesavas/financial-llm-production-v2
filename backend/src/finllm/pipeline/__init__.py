"""Funnel pipeline — Stage 0 → 5 cross-market orkestratör.

Tek giriş: `finllm.pipeline.run_pipeline(market, mode)`

Akış:
    Stage 0 ingest → 1 hard-filter → 1B setup → 1C indicators
    → 2 cheap LLM → 3 deep LLM → 4 meta-judge → 4.5 backtest gate
    → 5 writer + alert fanout
"""
from finllm.pipeline.context import (
    BUY_SIGNALS,
    SELL_SIGNALS,
    SIGNAL_TO_DIRECTION,
    Candidate,
    ExtendedSignal,
    IngestedData,
    PipelineContext,
    PipelineMode,
    PriceScenario,
    SignalType,
)

# orchestrator burada import EDİLMEZ — circular import'tan kaçınmak için.
# Kullanıcı: `from finllm.pipeline.orchestrator import run_pipeline`

__all__ = [
    "BUY_SIGNALS",
    "Candidate",
    "ExtendedSignal",
    "IngestedData",
    "PipelineContext",
    "PipelineMode",
    "PriceScenario",
    "SELL_SIGNALS",
    "SIGNAL_TO_DIRECTION",
    "SignalType",
]
