"""LLM clients + prompt building.

Phase 1: MockLLM (deterministic).
Phase 2: ClaudeScreenClient (Haiku), ClaudeDeepClient (Opus).
"""
from finllm.llm.base import (
    DeepAnalysis,
    LLMClient,
    PriceScenarioOutput,
    ScreenVerdict,
)
from finllm.llm.claude import ClaudeDeepClient, ClaudeScreenClient
from finllm.llm.data_block_builder import build_data_block
from finllm.llm.mock import MockLLM

__all__ = [
    "ClaudeDeepClient",
    "ClaudeScreenClient",
    "DeepAnalysis",
    "LLMClient",
    "MockLLM",
    "PriceScenarioOutput",
    "ScreenVerdict",
    "build_data_block",
]
