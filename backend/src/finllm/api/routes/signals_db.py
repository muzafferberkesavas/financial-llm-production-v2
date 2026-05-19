"""/v2/db/signals — DB-backed sinyal route'ları (Phase 3.2c).

Mevcut /v2/signals (JSON-backed) korunuyor; bu yeni endpoint'ler DB'yi prefer
eder, kullanılabilirlik bittiğinde JSON'a fallback yapar.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from finllm.api.auth import optional_bearer
from finllm.storage.engine import session_scope
from finllm.storage.models import Run, Signal

router = APIRouter(prefix="/v2/db", tags=["signals-db"])


def _signal_to_dict(s: Signal, scenarios: list = None) -> dict[str, Any]:
    return {
        "id": s.id,
        "ticker": s.ticker,
        "name": s.name,
        "sector": s.sector,
        "market": s.market,
        "generated_at": s.generated_at.isoformat(),
        "run_id": s.run_id,
        "signal": s.signal,
        "confidence": s.confidence,
        "calibrated_probability": s.calibrated_probability,
        "entry_zone_low": s.entry_zone_low,
        "entry_zone_high": s.entry_zone_high,
        "stop_loss": s.stop_loss,
        "expected_return_pct": s.expected_return_pct,
        "time_horizon_days": s.time_horizon_days,
        "allocation_weight": s.allocation_weight,
        "allocation_cash": s.allocation_cash,
        "confluence_score": s.confluence_score,
        "fundamental_score": s.fundamental_score,
        "market_regime": s.market_regime,
        "weekly_trend": s.weekly_trend,
        "confirmation_count": s.confirmation_count,
        "backtest_30d_return_pct": s.backtest_30d_return_pct,
        "backtest_gate_passed": s.backtest_gate_passed,
        "is_actionable": s.is_actionable,
        "rationale": s.rationale,
        "warning_flags": s.warning_flags or [],
        "unsourced_flag": s.unsourced_flag,
        "llm_model": s.llm_model,
        "llm_cost_usd": s.llm_cost_usd,
        "scenarios": [
            {
                "label": sc.label,
                "target_price": sc.target_price,
                "probability": sc.probability,
                "expected_return_pct": sc.expected_return_pct,
            }
            for sc in (scenarios or s.scenarios)
        ],
    }


def _run_to_dict(r: Run) -> dict[str, Any]:
    return {
        "run_id": r.run_id,
        "market": r.market,
        "mode": r.mode,
        "started_at": r.started_at.isoformat(),
        "total_capital": r.total_capital,
        "max_positions": r.max_positions,
        "max_position_pct": r.max_position_pct,
        "cash_buffer_pct": r.cash_buffer_pct,
        "min_expected_return_pct": r.min_expected_return_pct,
        "regime": {
            "vix": r.vix,
            "benchmark_change_5d": r.benchmark_change_5d,
            "trade_enabled": r.trade_enabled,
            "halt_reason": r.halt_reason,
            "fear_level": r.fear_level,
        },
        "universe_size": r.universe_size,
        "passed_hard_filter": r.passed_hard_filter,
        "stage3_queue_size": r.stage3_queue_size,
        "signals_generated": r.signals_generated,
        "actionable_signals": r.actionable_signals,
        "total_duration_sec": r.total_duration_sec,
        "total_cost_usd": r.total_cost_usd,
        "stage_durations_sec": r.stage_durations or {},
    }


@router.get("/signals/latest")
def latest_signals_db(
    market: str | None = Query(default=None, regex="^(bist|nasdaq)$"),
    actionable_only: bool = False,
    _=Depends(optional_bearer),
) -> dict[str, Any]:
    """En son run'un sinyalleri — DB-backed."""
    with session_scope() as sess:
        q = select(Run).order_by(Run.started_at.desc())
        if market:
            q = q.where(Run.market == market)
        run = sess.execute(q.limit(1)).scalar_one_or_none()
        if not run:
            raise HTTPException(404, "No runs in DB yet")

        sig_q = select(Signal).where(Signal.run_db_id == run.id)
        if actionable_only:
            sig_q = sig_q.where(Signal.is_actionable.is_(True))
        signals = list(
            sess.execute(sig_q.order_by(Signal.confidence.desc())).scalars()
        )

        return {
            "summary": _run_to_dict(run),
            "signals": [_signal_to_dict(s) for s in signals],
        }


@router.get("/signals/by-ticker/{ticker}")
def signal_by_ticker_db(
    ticker: str,
    lookback: int = Query(default=10, ge=1, le=100),
    _=Depends(optional_bearer),
) -> dict[str, Any]:
    """Belirli ticker için son sinyali bul."""
    with session_scope() as sess:
        q = (
            select(Signal)
            .where(Signal.ticker == ticker.upper())
            .order_by(Signal.generated_at.desc())
            .limit(lookback)
        )
        results = list(sess.execute(q).scalars())
        if not results:
            raise HTTPException(404, f"{ticker} hiç sinyalde yok")
        sig = results[0]
        run = sess.execute(
            select(Run).where(Run.run_id == sig.run_id)
        ).scalar_one_or_none()
        return {
            "summary": _run_to_dict(run) if run else None,
            "signal": _signal_to_dict(sig),
        }


@router.get("/runs")
def list_runs_db(
    market: str | None = Query(default=None, regex="^(bist|nasdaq)$"),
    limit: int = Query(default=30, ge=1, le=200),
    _=Depends(optional_bearer),
) -> dict[str, Any]:
    with session_scope() as sess:
        q = select(Run).order_by(Run.started_at.desc())
        if market:
            q = q.where(Run.market == market)
        runs = list(sess.execute(q.limit(limit)).scalars())
        return {
            "runs": [_run_to_dict(r) for r in runs],
            "count": len(runs),
        }


@router.get("/stats")
def signal_stats(_=Depends(optional_bearer)) -> dict[str, Any]:
    """Genel istatistik — DB sayımları."""
    from sqlalchemy import func

    with session_scope() as sess:
        total_runs = sess.execute(select(func.count(Run.id))).scalar() or 0
        total_signals = sess.execute(select(func.count(Signal.id))).scalar() or 0
        actionable = (
            sess.execute(
                select(func.count(Signal.id)).where(Signal.is_actionable.is_(True))
            ).scalar()
            or 0
        )
        per_market = sess.execute(
            select(Run.market, func.count(Run.id)).group_by(Run.market)
        ).all()
        return {
            "total_runs": total_runs,
            "total_signals": total_signals,
            "actionable_signals": actionable,
            "runs_per_market": {row[0]: row[1] for row in per_market},
        }
