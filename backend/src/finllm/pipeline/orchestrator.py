"""Pipeline orchestrator — Stage 0 → 5 zinciri tek fonksiyonda.

Kullanım:
    from finllm.pipeline.orchestrator import run_pipeline

    ctx = run_pipeline(
        market="nasdaq",
        mode="pre_market",
        capital=10_000,
    )
"""
from __future__ import annotations

import uuid
from pathlib import Path

from typing import Literal

from finllm.llm import ClaudeDeepClient, MockLLM
from finllm.llm.base import LLMClient

LLMBackend = Literal["mock", "claude", "claude-deep-only"]
from finllm.markets import get_adapter
from finllm.markets.base import MarketName
from finllm.pipeline.context import PipelineContext, PipelineMode
from finllm.pipeline.regime import run_regime_check
from finllm.pipeline.stage0_ingest import run_stage0
from finllm.pipeline.stage0b_agenda import run_stage0b
from finllm.pipeline.stage1_filter import run_stage1
from finllm.pipeline.stage1b_setup import run_stage1b
from finllm.pipeline.stage1c_features import run_stage1c
from finllm.pipeline.stage3_deep import run_stage3
from finllm.pipeline.stage4_5_backtest_gate import run_stage4_5
from finllm.pipeline.stage4_judge import run_stage4
from finllm.pipeline.stage5_writer import run_stage5
from finllm.utils.logging import logger


def _resolve_deep_llm(
    backend: LLMBackend,
    deep_llm: LLMClient | None,
) -> LLMClient:
    """LLM backend seçimi — explicit param > backend flag > mock default."""
    if deep_llm is not None:
        return deep_llm

    if backend == "mock":
        return MockLLM(role="deep")
    if backend in ("claude", "claude-deep-only"):
        return ClaudeDeepClient()
    raise ValueError(f"Unknown LLM backend: {backend}")


def run_pipeline(
    market: MarketName,
    mode: PipelineMode = "pre_market",
    capital: float = 10_000.0,
    *,
    llm_backend: LLMBackend = "mock",
    deep_llm: LLMClient | None = None,
    output_dir: Path | None = None,
    lookback_days: int = 400,
    max_pass_to_stage3: int = 12,
    min_setup_score: float = 0.3,
    skip_backtest_gate: bool = False,
    skip_news_agenda: bool = False,
) -> PipelineContext:
    """Tüm funnel'ı uçtan uca çalıştır.

    Args:
        market: "bist" | "nasdaq"
        mode: "pre_market" | "intraday" | "end_of_day"
        capital: Allocator'a verilecek toplam sermaye (adapter.currency)
        deep_llm: Stage 3 LLM (default MockLLM)
        output_dir: JSON output klasörü (default backend/out/)
        lookback_days: Stage 0 fiyat geçmişi
        max_pass_to_stage3: Stage 1C master_score → Stage 3 quota
        min_setup_score: Stage 1B setup eşiği
        skip_backtest_gate: True ise Stage 4.5 atlanır (hızlı test için)

    Returns:
        PipelineContext (signals + summary).
    """
    adapter = get_adapter(market)
    run_id = f"{market}-{mode}-{uuid.uuid4().hex[:8]}"

    ctx = PipelineContext(
        adapter=adapter,
        mode=mode,
        run_id=run_id,
        total_capital=capital,
    )

    logger.info("=" * 70)
    logger.info(f"PIPELINE RUN: {run_id} | market={market} mode={mode} capital={capital}")
    logger.info("=" * 70)

    # Stage -1: Regime check (kill-switch)
    run_regime_check(ctx)
    if ctx.regime and not ctx.regime.trade_enabled:
        logger.warning(f"[PIPELINE] Trade halted: {ctx.regime.halt_reason}")
        # Yine de ingest+filter çalıştır ama sinyal üretmiyoruz
        run_stage0(ctx, lookback_days=lookback_days)
        return ctx

    # Stages 0-5
    deep_llm = _resolve_deep_llm(llm_backend, deep_llm)
    logger.info(f"[PIPELINE] LLM: deep={deep_llm.name}")

    run_stage0(ctx, lookback_days=lookback_days)

    # Stage 0b — news + agenda (Phase 2.2)
    if not skip_news_agenda and llm_backend != "mock":
        # Real Claude lazım translator için; mock backend'de skip
        run_stage0b(ctx)
    elif not skip_news_agenda and llm_backend == "mock":
        logger.info("[PIPELINE] Stage 0b skipped (mock backend, no Claude available)")

    run_stage1(ctx)
    run_stage1b(ctx, min_setup_score=min_setup_score)
    run_stage1c(ctx, max_pass_to_stage3=max_pass_to_stage3)
    run_stage3(ctx, client=deep_llm)
    run_stage4(ctx)
    if not skip_backtest_gate:
        run_stage4_5(ctx)
    else:
        # backtest skipped, hepsi geçer farzedilir
        for s in ctx.signals:
            s.backtest_gate_passed = s.signal in ("AL", "GUCLU_AL")

    run_stage5(ctx, output_dir=output_dir)

    # Summary
    total_dur = sum(ctx.stage_durations_sec.values())
    logger.info("=" * 70)
    logger.info(
        f"PIPELINE COMPLETE: {len(ctx.actionable_signals)} actionable signals "
        f"({len(ctx.signals)} total) in {total_dur:.1f}s | cost ${ctx.total_cost_usd:.4f}"
    )
    logger.info("=" * 70)

    return ctx
