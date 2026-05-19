"""Stage 3 — Deep LLM: tam multi-layer analiz, ExtendedSignal üretimi.

Phase 1: MockLLM
Phase 2: Claude Opus 4.7 (~$0.20/analysis, ~$3/run for 15 stocks)

Stage 2'den gelen advancing candidate'lara DeepAnalysis çağrısı.
Çıktıyı ExtendedSignal'a serialize eder.
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from finllm.llm import build_data_block
from finllm.llm.base import LLMClient
from finllm.pipeline.context import (
    Candidate,
    ExtendedSignal,
    PipelineContext,
    PriceScenario,
)
from finllm.utils.logging import logger


def _deep_one(client: LLMClient, cand: Candidate, agenda=None) -> ExtendedSignal:
    """Tek candidate için deep analysis → ExtendedSignal."""
    data_block = build_data_block(cand, market_agenda=agenda)
    analysis = client.deep_analyze(data_block)

    # PriceScenarioOutput → PriceScenario (pipeline tip)
    scenarios = [
        PriceScenario(
            label=s.label,
            target_price=s.target_price,
            probability=s.probability,
            expected_return_pct=s.expected_return_pct,
        )
        for s in analysis.scenarios
    ]

    return ExtendedSignal(
        ticker=cand.ticker,
        signal=analysis.signal,
        confidence=analysis.confidence,
        entry_zone_low=analysis.entry_zone_low,
        entry_zone_high=analysis.entry_zone_high,
        stop_loss=analysis.stop_loss,
        scenarios=scenarios,
        expected_return_pct=analysis.expected_return_pct,
        time_horizon_days=analysis.time_horizon_days,
        rationale_trend=analysis.rationale_trend,
        rationale_formation=analysis.rationale_formation,
        rationale_volume=analysis.rationale_volume,
        rationale_news=analysis.rationale_news,
        rationale_fibonacci=analysis.rationale_fibonacci,
        rationale_risks=analysis.rationale_risks,
        rationale_full=analysis.rationale_full,
        warning_flags=analysis.warning_flags,
        unsourced_flag=analysis.unsourced_flag,
        confluence_score=cand.confluence_score,
        market_regime=cand.regime,
        weekly_trend=cand.indicators.get("weekly_trend", "UNKNOWN"),
        llm_model=analysis.model,
        llm_cost_usd=analysis.cost_usd,
    )


def run_stage3(
    ctx: PipelineContext,
    client: LLMClient,
    max_workers: int = 4,
) -> PipelineContext:
    """Stage 3 entry: Stage 2'den gelen kuyrukla deep analysis."""
    started = time.perf_counter()
    queue: list[Candidate] = ctx.stage3_queue

    if not queue:
        logger.warning("[STAGE 3] Stage 2'den queue gelmedi, skip")
        ctx.log_stage("stage3_deep", time.perf_counter() - started)
        return ctx

    logger.info(f"[STAGE 3] {ctx.market}: {len(queue)} hisse deep analysis ({client.name})")

    signals: list[ExtendedSignal] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_deep_one, client, c, ctx.market_agenda): c for c in queue}
        for fut in as_completed(futures):
            cand = futures[fut]
            try:
                sig = fut.result()
                sig.run_id = ctx.run_id
                signals.append(sig)
                ctx.total_cost_usd += sig.llm_cost_usd
            except Exception as e:
                logger.warning(f"[STAGE 3] {cand.ticker} deep analysis hatası: {e}")

    # Sort by confidence (en yüksek önce)
    signals.sort(key=lambda s: s.confidence, reverse=True)
    ctx.signals = signals

    by_signal = {}
    for s in signals:
        by_signal[s.signal] = by_signal.get(s.signal, 0) + 1

    duration = time.perf_counter() - started
    ctx.log_stage("stage3_deep", duration)
    logger.info(
        f"[STAGE 3] tamam: {len(signals)} signal | "
        f"distribution: {by_signal} | "
        f"cost: ${ctx.total_cost_usd:.4f} ({duration:.2f}s)"
    )
    if signals:
        top3 = signals[:3]
        for s in top3:
            exp_str = f"exp_ret={s.expected_return_pct:+.1f}%" if s.expected_return_pct else "exp_ret=-"
            logger.info(
                f"[STAGE 3] {s.ticker.symbol:<8} {s.signal:<10} conf={s.confidence:.2f} "
                f"{exp_str} horizon={s.time_horizon_days}d"
            )
    return ctx
