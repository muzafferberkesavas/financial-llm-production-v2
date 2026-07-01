"""POST /v2/analyze/bist — BIST analiz pipeline'i.

Tam pipeline calistirir (stage 0-5), top 5 hisseyi Opus'a gonderir,
senaryo ve sinyal uretir. Sonuclari JSON dosyaya kaydeder.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel

from finllm.config.settings import DATA_DIR, settings
from finllm.utils.logging import logger

router = APIRouter(prefix="/v2/analyze", tags=["analyze"])

_ANALYSIS_DIR = DATA_DIR / "analysis"


class AnalyzeRequest(BaseModel):
    capital: float = 100_000.0
    llm_backend: str = "claude"
    max_top: int = 5
    skip_backtest: bool = True
    skip_news: bool = True


def _signal_to_dict(sig) -> dict:
    """ExtendedSignal -> JSON-serializable dict."""
    return {
        "ticker": sig.ticker.symbol,
        "name": sig.ticker.name,
        "sector": sig.ticker.sector,
        "market": sig.ticker.market,
        "generated_at": sig.generated_at.isoformat(),
        "run_id": sig.run_id,
        "signal": sig.signal,
        "confidence": sig.confidence,
        "entry_zone_low": sig.entry_zone_low,
        "entry_zone_high": sig.entry_zone_high,
        "stop_loss": sig.stop_loss,
        "expected_return_pct": sig.expected_return_pct,
        "time_horizon_days": sig.time_horizon_days,
        "scenarios": [
            {
                "label": s.label,
                "target_price": s.target_price,
                "probability": s.probability,
                "expected_return_pct": s.expected_return_pct,
            }
            for s in sig.scenarios
        ],
        "allocation_weight": sig.allocation_weight,
        "allocation_cash": sig.allocation_cash,
        "confluence_score": sig.confluence_score,
        "market_regime": sig.market_regime,
        "weekly_trend": sig.weekly_trend,
        "master_score_pct": sig.master_score_pct,
        "confirmation_count": sig.confirmation_count,
        "backtest_gate_passed": sig.backtest_gate_passed,
        "is_actionable": sig.is_actionable,
        "rationale": {
            "trend": sig.rationale_trend,
            "formation": sig.rationale_formation,
            "volume": sig.rationale_volume,
            "news": sig.rationale_news,
            "fibonacci": sig.rationale_fibonacci,
            "risks": sig.rationale_risks,
            "full": sig.rationale_full,
        },
        "warning_flags": sig.warning_flags,
        "llm_model": sig.llm_model,
        "llm_cost_usd": sig.llm_cost_usd,
    }


def _save_analysis(result: dict) -> Path:
    """Analiz sonucunu dosyaya kaydet."""
    _ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    fpath = _ANALYSIS_DIR / f"bist_analysis_{ts}.json"
    fpath.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return fpath


@router.post("/bist")
def run_bist_analysis(req: AnalyzeRequest) -> dict:
    """BIST pipeline'i calistir, top N hisseyi Opus ile analiz et."""
    from finllm.pipeline.orchestrator import run_pipeline

    started = time.perf_counter()

    ctx = run_pipeline(
        market="bist",
        mode="end_of_day",
        capital=req.capital,
        llm_backend=req.llm_backend,
        max_pass_to_stage3=req.max_top,
        skip_backtest_gate=req.skip_backtest,
        skip_news_agenda=req.skip_news,
    )

    duration = time.perf_counter() - started

    signals = [_signal_to_dict(s) for s in ctx.signals]
    buy_signals = [s for s in signals if s["signal"] in ("GUCLU_AL", "AL")]

    result = {
        "status": "completed",
        "run_id": ctx.run_id,
        "market": "bist",
        "duration_sec": round(duration, 1),
        "total_cost_usd": round(ctx.total_cost_usd, 4),
        "universe_size": len(ctx.ingested),
        "passed_filter": sum(1 for c in ctx.candidates if c.passed_hard_filter),
        "analyzed_count": len(ctx.stage3_queue),
        "signals": signals,
        "buy_signals": buy_signals,
        "portfolio_additions": [
            {
                "ticker": s["ticker"],
                "signal": s["signal"],
                "confidence": s["confidence"],
                "entry_zone_low": s["entry_zone_low"],
                "entry_zone_high": s["entry_zone_high"],
                "stop_loss": s["stop_loss"],
                "scenarios": s["scenarios"],
                "allocation_weight": s["allocation_weight"],
                "allocation_cash": s["allocation_cash"],
            }
            for s in buy_signals
        ],
        "stage_durations": ctx.stage_durations_sec,
    }

    fpath = _save_analysis(result)
    logger.info(f"[ANALYZE] BIST analysis saved: {fpath}")

    return result


@router.get("/latest")
def get_latest_analysis(
    market: str = Query("bist", pattern="^(bist|nasdaq)$"),
) -> dict:
    """Son analiz sonuclarini getir."""
    _ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    pattern = f"{market}_analysis_*.json"
    files = sorted(_ANALYSIS_DIR.glob(pattern), reverse=True)
    if not files:
        return {"status": "no_analysis", "signals": [], "buy_signals": []}

    return json.loads(files[0].read_text(encoding="utf-8"))
