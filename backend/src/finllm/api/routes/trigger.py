"""/v2/trigger — admin endpoint, run_pipeline'ı çalıştırır.

Auth: Bearer token zorunlu.
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from finllm.api.auth import require_bearer
from finllm.utils.logging import logger

router = APIRouter(prefix="/v2/trigger", tags=["trigger"])


class TriggerRequest(BaseModel):
    market: Literal["bist", "nasdaq"]
    mode: Literal["pre_market", "intraday", "end_of_day"] = "pre_market"
    capital: float = 10_000.0
    llm_backend: Literal["mock", "claude", "claude-screen-only", "claude-deep-only"] = "mock"
    max_pass_to_stage3: int = 12
    skip_backtest: bool = False
    skip_news: bool = False


def _run_pipeline_bg(req: TriggerRequest) -> None:
    """Background task — long-running pipeline run."""
    from finllm.pipeline.orchestrator import run_pipeline

    try:
        ctx = run_pipeline(
            market=req.market,
            mode=req.mode,
            capital=req.capital,
            llm_backend=req.llm_backend,
            max_pass_to_stage3=req.max_pass_to_stage3,
            skip_backtest_gate=req.skip_backtest,
            skip_news_agenda=req.skip_news,
        )
        logger.info(
            f"[API-TRIGGER] {req.market}/{req.mode} done: "
            f"{len(ctx.actionable_signals)} actionable, ${ctx.total_cost_usd:.2f} cost"
        )
    except Exception as e:
        logger.exception(f"[API-TRIGGER] {req.market} failed: {e}")


@router.post("/run")
def trigger_run(
    req: TriggerRequest,
    background_tasks: BackgroundTasks,
    _: str = Depends(require_bearer),
) -> dict:
    """Pipeline'ı arka planda başlat. Pre-flight cevap döner."""
    background_tasks.add_task(_run_pipeline_bg, req)
    return {
        "queued": True,
        "market": req.market,
        "mode": req.mode,
        "llm_backend": req.llm_backend,
        "estimated_duration_sec": 30 if req.llm_backend == "mock" else 90,
        "message": "Pipeline started in background. Check /v2/signals/latest in ~1-2 min.",
    }


@router.post("/update-outcomes")
def trigger_outcome_update(
    background_tasks: BackgroundTasks,
    _: str = Depends(require_bearer),
) -> dict:
    """Cron equivalent — outcome update + Platt retrain."""

    def _bg():
        from finllm.calibration import (
            OutcomeTracker,
            train_calibrator,
            update_realized_outcomes,
        )

        try:
            stats = update_realized_outcomes()
            calibrator = train_calibrator(OutcomeTracker())
            logger.info(
                f"[API-TRIGGER] outcome update: {stats}, "
                f"calibrator trained={calibrator.is_trained}, n={calibrator.n_train}"
            )
        except Exception as e:
            logger.exception(f"[API-TRIGGER] outcome update failed: {e}")

    background_tasks.add_task(_bg)
    return {"queued": True, "message": "Outcome update + calibrator retrain running"}
