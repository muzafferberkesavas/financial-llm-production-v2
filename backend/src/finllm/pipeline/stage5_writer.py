"""Stage 5 — Writer: JSON output + alert fan-out.

Phase 1: JSON dosyaya yaz + telegram stub'a post.
Phase 2: Neon Postgres + aiogram + FCM + WebSocket broadcast.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path

from finllm.alerts import TelegramStub, get_alert_target
from finllm.calibration import OutcomeTracker
from finllm.config.settings import settings
from finllm.pipeline.context import ExtendedSignal, PipelineContext
from finllm.utils.logging import logger

# Phase 3.2: DB dual-write
try:
    from finllm.storage import repository as db_repo
    from finllm.storage.engine import init_schema as init_v2_schema

    _DB_AVAILABLE = True
except Exception as e:
    logger.warning(f"[STAGE 5] DB layer not available: {e}")
    _DB_AVAILABLE = False
    db_repo = None  # type: ignore
    init_v2_schema = None  # type: ignore


def _signal_to_dict(sig: ExtendedSignal) -> dict:
    """ExtendedSignal'i JSON-serializable dict'e çevir."""
    return {
        "ticker": sig.ticker.symbol,
        "name": sig.ticker.name,
        "sector": sig.ticker.sector,
        "market": sig.ticker.market,
        "generated_at": sig.generated_at.isoformat(),
        "session_id": sig.session_id,
        "run_id": sig.run_id,
        "signal": sig.signal,
        "confidence": sig.confidence,
        "calibrated_probability": sig.calibrated_probability,
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
        "backtest_30d_return_pct": sig.backtest_30d_return_pct,
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
        "unsourced_flag": sig.unsourced_flag,
        "llm_model": sig.llm_model,
        "llm_cost_usd": sig.llm_cost_usd,
    }


def _context_to_summary(ctx: PipelineContext) -> dict:
    """Pipeline run summary'sini JSON'a koy."""
    return {
        "run_id": ctx.run_id,
        "market": ctx.market,
        "mode": ctx.mode,
        "started_at": ctx.started_at.isoformat(),
        "total_capital": ctx.total_capital,
        "max_positions": ctx.max_positions,
        "max_position_pct": ctx.max_position_pct,
        "cash_buffer_pct": ctx.cash_buffer_pct,
        "min_expected_return_pct": ctx.min_expected_return_pct,
        "regime": {
            "vix": ctx.regime.vix if ctx.regime else None,
            "benchmark_change_5d": ctx.regime.benchmark_change_5d if ctx.regime else None,
            "trade_enabled": ctx.regime.trade_enabled if ctx.regime else None,
            "halt_reason": ctx.regime.halt_reason if ctx.regime else None,
            "fear_level": ctx.regime.fear_level if ctx.regime else None,
        }
        if ctx.regime
        else None,
        "universe_size": len(ctx.ingested),
        "passed_hard_filter": sum(1 for c in ctx.candidates if c.passed_hard_filter),
        "stage3_queue_size": len(ctx.stage3_queue),
        "signals_generated": len(ctx.signals),
        "actionable_signals": len(ctx.actionable_signals),
        "stage_durations_sec": ctx.stage_durations_sec,
        "total_duration_sec": sum(ctx.stage_durations_sec.values()),
        "total_cost_usd": ctx.total_cost_usd,
    }


def run_stage5(
    ctx: PipelineContext,
    output_dir: Path | None = None,
    telegram: TelegramStub | None = None,
) -> Path:
    """Stage 5 entry: JSON yaz + alert fan-out. Output dosya path'ini döner."""
    started = time.perf_counter()
    output_dir = output_dir or settings.cache_dir.parent / "out"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = ctx.started_at.strftime("%Y%m%d_%H%M")
    fname = f"signals_{ctx.market}_{timestamp}_{ctx.mode}.json"
    fpath = output_dir / fname

    payload = {
        "summary": _context_to_summary(ctx),
        "signals": [_signal_to_dict(s) for s in ctx.signals],
    }

    fpath.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
    logger.info(f"[STAGE 5] wrote {fpath} ({len(ctx.signals)} signals)")

    # Outcome tracker (JSONL) — backward-compat
    try:
        tracker = OutcomeTracker()
        added = tracker.append_many(ctx.signals, market=ctx.market)
        if added > 0:
            logger.info(f"[STAGE 5] outcome tracker (JSONL): {added} signals queued")
    except Exception as e:
        logger.warning(f"[STAGE 5] outcome tracker JSONL error: {e}")

    # Phase 3.2: DB dual-write
    if _DB_AVAILABLE and db_repo is not None:
        try:
            init_v2_schema()  # idempotent
            run_db_id = db_repo.save_run(ctx)
            if run_db_id:
                logger.info(f"[STAGE 5] DB write: run.id={run_db_id}, {len(ctx.signals)} signals persisted")
        except Exception as e:
            logger.warning(f"[STAGE 5] DB write error (JSON still works): {e}")

    # Alert fan-out — Phase 2.3: token varsa gerçek bot, yoksa stub fallback
    if telegram:
        telegram.post_signals(ctx)
    else:
        target = get_alert_target(market=ctx.market)
        target.post_signals(ctx)

    duration = time.perf_counter() - started
    ctx.log_stage("stage5_writer", duration)
    logger.info(f"[STAGE 5] alert fan-out completed ({duration:.2f}s)")
    return fpath
