"""Repository — Pipeline ↔ DB arasında veri akışı.

Stage 5 dual-write: hem JSON dosyaya hem DB'ye yazar. JSON Phase 3'te
backward-compat için (mobile app cache, eski dashboard, manual inspection).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select

from finllm.pipeline.context import ExtendedSignal, PipelineContext
from finllm.storage.engine import session_scope
from finllm.storage.models import Outcome, Run, Signal, SignalScenario, Watchlist
from finllm.utils.logging import logger


def save_run(ctx: PipelineContext) -> int | None:
    """Pipeline run summary + tüm sinyalleri DB'ye yaz. Returns Run.id."""
    try:
        with session_scope() as sess:
            run = Run(
                run_id=ctx.run_id,
                market=ctx.adapter.name,
                mode=ctx.mode,
                started_at=ctx.started_at,
                total_capital=ctx.total_capital,
                max_positions=ctx.max_positions,
                max_position_pct=ctx.max_position_pct,
                cash_buffer_pct=ctx.cash_buffer_pct,
                min_expected_return_pct=ctx.min_expected_return_pct,
                vix=ctx.regime.vix if ctx.regime else None,
                benchmark_change_5d=ctx.regime.benchmark_change_5d if ctx.regime else None,
                trade_enabled=ctx.regime.trade_enabled if ctx.regime else True,
                halt_reason=ctx.regime.halt_reason if ctx.regime else None,
                fear_level=ctx.regime.fear_level if ctx.regime else "calm",
                universe_size=len(ctx.ingested),
                passed_hard_filter=sum(1 for c in ctx.candidates if c.passed_hard_filter),
                stage3_queue_size=len(ctx.stage3_queue),
                signals_generated=len(ctx.signals),
                actionable_signals=len(ctx.actionable_signals),
                total_duration_sec=sum(ctx.stage_durations_sec.values()),
                total_cost_usd=ctx.total_cost_usd,
                stage_durations=dict(ctx.stage_durations_sec),
            )
            sess.add(run)
            sess.flush()  # run.id elde et

            for sig in ctx.signals:
                db_sig = _signal_to_orm(sig, run.id)
                sess.add(db_sig)
                sess.flush()
                for sc in sig.scenarios:
                    sess.add(
                        SignalScenario(
                            signal_id=db_sig.id,
                            label=sc.label,
                            target_price=sc.target_price,
                            probability=sc.probability,
                            expected_return_pct=sc.expected_return_pct,
                        )
                    )

                # Actionable sinyallere outcome record (lifecycle tracking)
                if sig.is_actionable:
                    sess.add(
                        Outcome(
                            signal_id=db_sig.id,
                            run_id=ctx.run_id,
                            ticker=sig.ticker.symbol,
                            market=ctx.adapter.name,
                            generated_at=sig.generated_at,
                            signal_label=sig.signal,
                            confidence=sig.confidence,
                            expected_return_pct=sig.expected_return_pct,
                            time_horizon_days=sig.time_horizon_days,
                            status="open",
                        )
                    )

            run_id_db = run.id
        logger.info(f"[DB] saved run {ctx.run_id} (id={run_id_db}, {len(ctx.signals)} signals)")
        return run_id_db
    except Exception as e:
        logger.exception(f"[DB] save_run failed: {e}")
        return None


def _signal_to_orm(sig: ExtendedSignal, run_db_id: int) -> Signal:
    return Signal(
        run_db_id=run_db_id,
        ticker=sig.ticker.symbol,
        name=sig.ticker.name,
        sector=sig.ticker.sector,
        market=sig.ticker.market,
        generated_at=sig.generated_at,
        run_id=sig.run_id,
        signal=sig.signal,
        confidence=sig.confidence,
        calibrated_probability=sig.calibrated_probability,
        entry_zone_low=sig.entry_zone_low,
        entry_zone_high=sig.entry_zone_high,
        stop_loss=sig.stop_loss,
        expected_return_pct=sig.expected_return_pct,
        time_horizon_days=sig.time_horizon_days,
        allocation_weight=sig.allocation_weight,
        allocation_cash=sig.allocation_cash,
        confluence_score=sig.confluence_score,
        market_regime=sig.market_regime,
        weekly_trend=sig.weekly_trend,
        confirmation_count=sig.confirmation_count,
        backtest_30d_return_pct=sig.backtest_30d_return_pct,
        backtest_gate_passed=sig.backtest_gate_passed,
        is_actionable=sig.is_actionable,
        rationale={
            "trend": sig.rationale_trend,
            "formation": sig.rationale_formation,
            "volume": sig.rationale_volume,
            "news": sig.rationale_news,
            "fibonacci": sig.rationale_fibonacci,
            "risks": sig.rationale_risks,
            "full": sig.rationale_full,
        },
        warning_flags=list(sig.warning_flags),
        unsourced_flag=sig.unsourced_flag,
        llm_model=sig.llm_model,
        llm_cost_usd=sig.llm_cost_usd,
        confluence_detail=None,  # Run önemli değilse ileride doldur
        fundamental_detail=None,
    )


def latest_run(market: str | None = None) -> Run | None:
    """En son run."""
    with session_scope() as sess:
        q = select(Run).order_by(Run.started_at.desc())
        if market:
            q = q.where(Run.market == market)
        return sess.execute(q.limit(1)).scalar_one_or_none()


def signals_for_run(run_id: str) -> list[Signal]:
    """Bir run'a ait tüm sinyaller."""
    with session_scope() as sess:
        q = select(Signal).where(Signal.run_id == run_id)
        return list(sess.execute(q).scalars())


def latest_signals(
    market: str | None = None, actionable_only: bool = False, limit: int = 50
) -> list[Signal]:
    """En son run'un sinyalleri."""
    with session_scope() as sess:
        run = latest_run(market)
        if run is None:
            return []
        q = select(Signal).where(Signal.run_db_id == run.id)
        if actionable_only:
            q = q.where(Signal.is_actionable.is_(True))
        return list(sess.execute(q.order_by(Signal.confidence.desc()).limit(limit)).scalars())


def signal_by_ticker(ticker: str, lookback: int = 10) -> Signal | None:
    """Bir ticker için son N run içinden ilk eşleşmeyi al."""
    with session_scope() as sess:
        q = (
            select(Signal)
            .where(Signal.ticker == ticker.upper())
            .order_by(Signal.generated_at.desc())
            .limit(lookback)
        )
        results = list(sess.execute(q).scalars())
        return results[0] if results else None


def recent_runs(market: str | None = None, limit: int = 30) -> list[Run]:
    with session_scope() as sess:
        q = select(Run).order_by(Run.started_at.desc()).limit(limit)
        if market:
            q = q.where(Run.market == market)
        return list(sess.execute(q).scalars())


def add_to_watchlist(user_id: str, ticker: str, market: str = "nasdaq") -> list[str]:
    with session_scope() as sess:
        existing = sess.execute(
            select(Watchlist).where(
                Watchlist.user_id == user_id, Watchlist.ticker == ticker.upper()
            )
        ).scalar_one_or_none()
        if not existing:
            sess.add(Watchlist(user_id=user_id, ticker=ticker.upper(), market=market))
        # Tüm watchlist döner
        rows = sess.execute(
            select(Watchlist.ticker).where(Watchlist.user_id == user_id)
        ).scalars()
        return list(rows)


def remove_from_watchlist(user_id: str, ticker: str) -> list[str]:
    with session_scope() as sess:
        sess.execute(
            select(Watchlist)
            .where(Watchlist.user_id == user_id, Watchlist.ticker == ticker.upper())
        ).scalars()
        # delete
        from sqlalchemy import delete as sa_delete

        sess.execute(
            sa_delete(Watchlist).where(
                Watchlist.user_id == user_id, Watchlist.ticker == ticker.upper()
            )
        )
        rows = sess.execute(
            select(Watchlist.ticker).where(Watchlist.user_id == user_id)
        ).scalars()
        return list(rows)


def get_watchlist(user_id: str) -> list[str]:
    with session_scope() as sess:
        rows = sess.execute(
            select(Watchlist.ticker).where(Watchlist.user_id == user_id)
        ).scalars()
        return list(rows)


__all__ = [
    "add_to_watchlist",
    "get_watchlist",
    "latest_run",
    "latest_signals",
    "recent_runs",
    "remove_from_watchlist",
    "save_run",
    "signal_by_ticker",
    "signals_for_run",
]
