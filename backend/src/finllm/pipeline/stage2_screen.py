"""Stage 2 — Cheap LLM screen: 'strong/potential/skip' etiketi.

Stage 1C'den gelen candidate'lara her birine kısa prompt gönderir.
Output: strong + best-of-potential top N → Stage 3'e geçer.

Phase 1: MockLLM
Phase 2: Claude Haiku 4.5 (~$0.001/screen)
"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from finllm.llm import build_data_block
from finllm.llm.base import LLMClient
from finllm.pipeline.context import Candidate, PipelineContext
from finllm.utils.logging import logger


def _screen_one(client: LLMClient, cand: Candidate, agenda=None) -> Candidate:
    data_block = build_data_block(cand, market_agenda=agenda)
    verdict = client.screen(data_block)
    cand.screen_verdict = verdict.verdict
    cand.screen_rationale = verdict.rationale
    return cand


def run_stage2(
    ctx: PipelineContext,
    client: LLMClient,
    max_pass_to_stage3: int = 15,
    max_workers: int = 8,
) -> PipelineContext:
    """Stage 2 entry: aktif candidate'ları paralel screen et."""
    started = time.perf_counter()
    active = ctx.active_candidates

    if not active:
        logger.warning("[STAGE 2] Aktif candidate yok, skip")
        ctx.log_stage("stage2_screen", time.perf_counter() - started)
        return ctx

    logger.info(f"[STAGE 2] {ctx.market}: {len(active)} candidate screen ({client.name})")

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_screen_one, client, c, ctx.market_agenda) for c in active]
        for fut in as_completed(futures):
            try:
                fut.result()
            except Exception as e:
                logger.warning(f"[STAGE 2] Screen hatası: {e}")

    # Sırala: strong > potential > skip; tie'da confluence score
    verdict_rank = {"strong": 3, "potential": 2, "skip": 1, "pending": 0}
    active.sort(
        key=lambda c: (verdict_rank.get(c.screen_verdict, 0), c.confluence_score),
        reverse=True,
    )

    # Top N'i geçir
    advancing = [c for c in active if c.screen_verdict in ("strong", "potential")][
        :max_pass_to_stage3
    ]
    advancing_set = {c.ticker.symbol for c in advancing}

    # Geçemeyenlerin passed_hard_filter'ını korumak istiyoruz ama
    # Stage 3 sadece bu listede olanlarla çalışsın diye ek bir flag eklemiyoruz —
    # context'in actionable filtering'i sonraki stage'lerde uygulanır.
    # Şimdilik active sıralamayı yansıtır; ctx.candidates da güncellendi.

    by_verdict = {
        "strong": sum(1 for c in active if c.screen_verdict == "strong"),
        "potential": sum(1 for c in active if c.screen_verdict == "potential"),
        "skip": sum(1 for c in active if c.screen_verdict == "skip"),
    }

    duration = time.perf_counter() - started
    ctx.log_stage("stage2_screen", duration)
    logger.info(
        f"[STAGE 2] verdicts: strong={by_verdict['strong']}, "
        f"potential={by_verdict['potential']}, skip={by_verdict['skip']} "
        f"({duration:.2f}s)"
    )
    logger.info(
        f"[STAGE 2] → Stage 3'e geçecek: "
        f"{len(advancing)} ({', '.join(advancing_set)})"
    )

    # Stage 3'ün hangi candidate'ları işleyeceğini context'e yaz
    ctx.signals = []  # reset for Stage 3
    ctx.stage3_queue = advancing

    return ctx
