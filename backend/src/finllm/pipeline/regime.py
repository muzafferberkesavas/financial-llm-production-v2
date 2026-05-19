"""Regime kill-switch — pipeline başında VIX/SPY check.

Phase 1: basit eşikler
Phase 2: regime-aware threshold ayarı (RANGE'de daha geniş stop, vs.)
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta

from finllm.data.prices import fetch_prices
from finllm.markets.base import RegimeContext
from finllm.pipeline.context import PipelineContext
from finllm.utils.logging import logger


VIX_TICKER = "^VIX"
SPY_TICKER = "SPY"


def _fetch_vix() -> float | None:
    try:
        start = (datetime.utcnow() - timedelta(days=10)).strftime("%Y-%m-%d")
        df = fetch_prices(VIX_TICKER, start=start)
        if df.empty:
            return None
        return float(df["close"].iloc[-1])
    except Exception as e:
        logger.warning(f"[REGIME] VIX fetch hatası: {e}")
        return None


def _check_benchmark(symbol: str) -> tuple[float | None, bool | None]:
    """Benchmark 5g % değişim + 200D MA üstünde mi."""
    try:
        start = (datetime.utcnow() - timedelta(days=300)).strftime("%Y-%m-%d")
        df = fetch_prices(symbol, start=start)
        if df.empty or len(df) < 200:
            return None, None
        latest = float(df["close"].iloc[-1])
        five_d_ago = float(df["close"].iloc[-6]) if len(df) >= 6 else latest
        change_5d = (latest - five_d_ago) / five_d_ago * 100
        ma200 = float(df["close"].tail(200).mean())
        return change_5d, latest > ma200
    except Exception as e:
        logger.warning(f"[REGIME] Benchmark {symbol} hatası: {e}")
        return None, None


def run_regime_check(ctx: PipelineContext) -> PipelineContext:
    """Pipeline başında piyasa rejimi check. Trade engelliyse halt_reason ile işaretler."""
    started = time.perf_counter()
    benchmark_symbol = ctx.adapter.benchmark_symbol
    market = ctx.adapter.name

    # VIX (NASDAQ için doğrudan, BIST için proxy olarak da kullanılır)
    vix = _fetch_vix()
    change_5d, above_200d = _check_benchmark(
        benchmark_symbol.replace(".IS", "")  # XU100 için suffix sorunu
        if market == "bist"
        else benchmark_symbol
    )

    regime = RegimeContext(
        market=market,
        vix=vix,
        benchmark_change_5d=change_5d,
        benchmark_above_200d_ma=above_200d,
    )

    # Fear level
    if vix is not None:
        if vix >= 35:
            regime.fear_level = "extreme"
        elif vix >= 25:
            regime.fear_level = "elevated"
        else:
            regime.fear_level = "calm"

    # Kill-switch kuralları
    if vix is not None and vix >= 35:
        regime.block(f"VIX {vix:.1f} >= 35 (extreme fear)")
    elif change_5d is not None and change_5d <= -5.0:
        regime.block(f"benchmark 5d change {change_5d:.1f}% (panic selling)")
    elif above_200d is False:
        # Below 200D MA — bearish regime, daha düşük position size (block etmiyoruz)
        logger.warning(
            f"[REGIME] {market}: benchmark below 200D MA — confidence cap %50"
        )

    ctx.regime = regime
    duration = time.perf_counter() - started
    ctx.log_stage("regime_check", duration)

    if regime.trade_enabled:
        vix_str = f"{vix:.1f}" if vix is not None else "N/A"
        chg_str = f"{change_5d:+.1f}%" if change_5d is not None else "N/A"
        logger.info(
            f"[REGIME] {market}: trade OK | VIX={vix_str} | "
            f"5d_change={chg_str} | "
            f"above_200D={above_200d} | fear={regime.fear_level} ({duration:.1f}s)"
        )
    else:
        logger.warning(
            f"[REGIME] {market}: TRADE HALTED — {regime.halt_reason} ({duration:.1f}s)"
        )

    return ctx
