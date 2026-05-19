"""Stage 4.5 — Backtest gate: son N gün paper-trade simülasyonu.

Her ExtendedSignal için strateji-kuralı son N günde nasıl performans gösterdi?
Hit-rate ve avg return eşiklerini geçemezse → FAIL flag.

Phase 1: basit walk-forward simülasyon.
Phase 2: backtest/engine.py'yi tam entegre et (transaction cost dahil).

Strateji kuralı (basitleştirilmiş Phase 1):
  - Entry: close > EMA21 AND close > EMA50 AND green day
  - Exit: stop_loss (entry × 0.95) veya target (entry × 1.10) veya time_stop (20 gün)
"""
from __future__ import annotations

import time

import pandas as pd

from finllm.markets.base import TransactionCostModel
from finllm.pipeline.context import ExtendedSignal, PipelineContext
from finllm.utils.logging import logger


def _simulate_strategy(
    prices: pd.DataFrame,
    cost_model: TransactionCostModel,
    lookback_days: int = 30,
    stop_pct: float = 0.05,
    target_pct: float = 0.10,
    max_hold_days: int = 20,
) -> dict:
    """Paper trade simülasyonu: son N gün içinde EMA21 yukarı kırış sinyallerini test et.

    Returns: {trades, hit_rate, avg_return_pct, total_return_pct}
    """
    if len(prices) < lookback_days + 50:
        return {"trades": 0, "hit_rate": 0.0, "avg_return_pct": 0.0, "total_return_pct": 0.0}

    closes = prices["close"]
    ema21 = closes.ewm(span=21, adjust=False).mean()
    ema50 = closes.ewm(span=50, adjust=False).mean()

    test_window = prices.tail(lookback_days + max_hold_days)
    trades: list[dict] = []
    in_position = False
    entry_idx = 0
    entry_price = 0.0

    for i in range(len(test_window) - 1):
        idx = len(prices) - len(test_window) + i
        if idx < 50:
            continue

        c = float(closes.iloc[idx])
        prev_c = float(closes.iloc[idx - 1])
        e21 = float(ema21.iloc[idx])
        e50 = float(ema50.iloc[idx])

        if not in_position:
            # Entry: close > both EMAs + green
            if c > e21 and c > e50 and c > prev_c:
                in_position = True
                entry_idx = idx
                entry_price = c
        else:
            held = idx - entry_idx
            stop_price = entry_price * (1.0 - stop_pct)
            target_price = entry_price * (1.0 + target_pct)

            exit_reason = None
            exit_price = c
            if c <= stop_price:
                exit_reason = "stop"
            elif c >= target_price:
                exit_reason = "target"
            elif held >= max_hold_days:
                exit_reason = "time"

            if exit_reason:
                # Apply transaction cost
                atr_proxy = abs(c - prev_c)
                tc_pct = cost_model.round_trip_cost_pct(entry_price, atr_proxy) / 100
                gross_return = (exit_price / entry_price) - 1.0
                net_return = gross_return - tc_pct
                trades.append({
                    "entry": entry_price,
                    "exit": exit_price,
                    "return_pct": net_return * 100,
                    "exit_reason": exit_reason,
                    "days_held": held,
                })
                in_position = False

    if not trades:
        return {"trades": 0, "hit_rate": 0.0, "avg_return_pct": 0.0, "total_return_pct": 0.0}

    winners = [t for t in trades if t["return_pct"] > 0]
    avg_return = sum(t["return_pct"] for t in trades) / len(trades)
    total_return = sum(t["return_pct"] for t in trades)
    return {
        "trades": len(trades),
        "hit_rate": len(winners) / len(trades),
        "avg_return_pct": avg_return,
        "total_return_pct": total_return,
    }


def run_stage4_5(
    ctx: PipelineContext,
    min_hit_rate: float = 0.4,
    min_avg_return: float = 0.0,
    require_at_least_n_trades: int = 1,
) -> PipelineContext:
    """Stage 4.5 entry: her sinyal için son 30g paper-trade simülasyonu."""
    started = time.perf_counter()
    cost_model = ctx.adapter.transaction_cost

    passed = 0
    failed = 0
    no_trades = 0

    for sig in ctx.signals:
        # AL/GUCLU_AL dışındakileri pas geç
        if sig.signal not in ("AL", "GUCLU_AL"):
            sig.backtest_gate_passed = False
            continue

        # Prices'i ingested data'dan al
        matching = next(
            (d for d in ctx.ingested if d.ticker.symbol == sig.ticker.symbol), None
        )
        if matching is None or not matching.has_price_data:
            sig.warning_flags.append("BACKTEST_NO_DATA")
            sig.backtest_gate_passed = False
            failed += 1
            continue

        result = _simulate_strategy(
            matching.prices,
            cost_model,
            lookback_days=30,
        )
        sig.backtest_30d_return_pct = result["avg_return_pct"]

        if result["trades"] < require_at_least_n_trades:
            sig.warning_flags.append(f"BACKTEST_INSUFFICIENT_TRADES({result['trades']})")
            # Strateji yetersiz veri için fail etmiyor, sadece flag
            sig.backtest_gate_passed = True
            no_trades += 1
            continue

        if (
            result["hit_rate"] >= min_hit_rate
            and result["avg_return_pct"] >= min_avg_return
        ):
            sig.backtest_gate_passed = True
            passed += 1
        else:
            sig.backtest_gate_passed = False
            sig.warning_flags.append(
                f"BACKTEST_FAIL(hit={result['hit_rate']:.0%},"
                f"avg={result['avg_return_pct']:.1f}%)"
            )
            failed += 1

    duration = time.perf_counter() - started
    ctx.log_stage("stage4_5_backtest", duration)
    logger.info(
        f"[STAGE 4.5] backtest gate: passed={passed}, failed={failed}, "
        f"no_trades={no_trades} ({duration:.2f}s)"
    )
    return ctx
