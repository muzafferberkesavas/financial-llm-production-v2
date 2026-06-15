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
from finllm.pipeline.stage1_filter import _compute_ema
from finllm.utils.logging import logger


VIX_TICKER = "^VIX"
SPY_TICKER = "SPY"
REGIME_LONG_SMA = 200  # classic 200-day bull/bear filter (backtest-validated, Faz A.4)


def _benchmark_uptrend(df) -> bool | None:
    """Mirror of backtest qqq_uptrend: close > EMA21 > EMA50 AND close > SMA200.

    This is the 200-DMA bull/bear regime filter that passed the robustness gate
    (ARCHITECTURE.md §4 Faz A.4) — keeping the live pipeline out of bear regimes
    where the strategy's edge inverts. Returns None if not enough history."""
    if df is None or df.empty or len(df) < REGIME_LONG_SMA:
        return None
    closes = df["close"]
    close = float(closes.iloc[-1])
    ema21 = _compute_ema(closes, 21)
    ema50 = _compute_ema(closes, 50)
    if ema21 is None or ema50 is None:
        return None
    close_20_ago = float(closes.iloc[-21]) if len(closes) >= 21 else close
    sma200 = float(closes.tail(REGIME_LONG_SMA).mean())
    return close > ema21 and ema21 > ema50 and close > close_20_ago and close > sma200


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


def _check_benchmark(symbol: str) -> tuple[float | None, bool | None, bool | None]:
    """Benchmark 5g % değişim + 200D MA üstünde mi + uptrend mi (EMA stack + SMA200)."""
    try:
        start = (datetime.utcnow() - timedelta(days=400)).strftime("%Y-%m-%d")
        df = fetch_prices(symbol, start=start)
        if df.empty or len(df) < REGIME_LONG_SMA:
            return None, None, None
        latest = float(df["close"].iloc[-1])
        five_d_ago = float(df["close"].iloc[-6]) if len(df) >= 6 else latest
        change_5d = (latest - five_d_ago) / five_d_ago * 100
        ma200 = float(df["close"].tail(REGIME_LONG_SMA).mean())
        return change_5d, latest > ma200, _benchmark_uptrend(df)
    except Exception as e:
        logger.warning(f"[REGIME] Benchmark {symbol} hatası: {e}")
        return None, None, None


def run_regime_check(ctx: PipelineContext) -> PipelineContext:
    """Pipeline başında piyasa rejimi check. Trade engelliyse halt_reason ile işaretler."""
    started = time.perf_counter()
    benchmark_symbol = ctx.adapter.benchmark_symbol
    market = ctx.adapter.name

    # VIX (NASDAQ için doğrudan, BIST için proxy olarak da kullanılır)
    vix = _fetch_vix()
    change_5d, above_200d, uptrend = _check_benchmark(
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
    elif uptrend is False:
        # Benchmark not in uptrend (below SMA200 / EMA stack broken) — bear regime
        # where the edge inverts. Backtest-validated: block NEW entries (Faz A.4).
        regime.block("benchmark not in uptrend (below 200D MA / EMA stack) — bear regime")
    elif uptrend is None and above_200d is False:
        # Couldn't confirm uptrend but clearly below 200D MA — stay safe, block.
        regime.block("benchmark below 200D MA (uptrend unconfirmed) — bear regime")

    ctx.regime = regime
    duration = time.perf_counter() - started
    ctx.log_stage("regime_check", duration)

    if regime.trade_enabled:
        vix_str = f"{vix:.1f}" if vix is not None else "N/A"
        chg_str = f"{change_5d:+.1f}%" if change_5d is not None else "N/A"
        logger.info(
            f"[REGIME] {market}: trade OK | VIX={vix_str} | "
            f"5d_change={chg_str} | "
            f"above_200D={above_200d} | uptrend={uptrend} | "
            f"fear={regime.fear_level} ({duration:.1f}s)"
        )
    else:
        logger.warning(
            f"[REGIME] {market}: TRADE HALTED — {regime.halt_reason} ({duration:.1f}s)"
        )

    return ctx
