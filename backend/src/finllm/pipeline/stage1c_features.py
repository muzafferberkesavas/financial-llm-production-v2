"""Stage 1C — Indicators + derived + confluence → Candidate.indicators.

Akış:
    1. features/technical.py ile ~50 ham gösterge hesapla (pandas-ta)
    2. indicators/derived.py ile OBV div, BB squeeze, weekly trend ekle
    3. indicators/confluence.py ile 8-bileşenli skor
    4. detect_market_regime → Candidate.regime
    5. confluence_to_signal_suggestion → ranking için kullanılır

Phase 1'de pricesonly hard filter geçenlerde hesaplanır (cost optimization);
Phase 2'de full universe için (cross-sectional ranking).
"""
from __future__ import annotations

import time

import numpy as np
import pandas as pd

from finllm.features.technical import add_technical_features
from finllm.indicators import (
    compute_bb_squeeze,
    compute_confluence,
    compute_obv_divergence,
    compute_swing_levels,
    compute_weekly_trend,
    detect_market_regime,
)
from finllm.indicators.fundamentals import compute_fundamental_score
from finllm.pipeline.context import Candidate, PipelineContext
from finllm.utils.logging import logger


def _fib_zone_from_prices(prices: pd.DataFrame, window: int = 250) -> str | None:
    """Basit Fibonacci zone label — son N gün swing high/low'a göre.

    Lib.zip'in FibonacciCalculator'ı ATR×2 swing detection kullanıyor;
    burada minimal versiyon — full port Phase 2'de.
    """
    if len(prices) < 30:
        return None
    window_data = prices.tail(window)
    swing_high = float(window_data["high"].max())
    swing_low = float(window_data["low"].min())
    diff = swing_high - swing_low
    if diff <= 0:
        return None

    close = float(prices["close"].iloc[-1])
    if close > swing_high:
        return "ABOVE_HIGH(breakout)"

    # Yükseliş retracement varsayımı (low → high)
    retracement = (swing_high - close) / diff
    if retracement < 0:
        return "ABOVE_HIGH(breakout)"
    if retracement <= 0.236:
        return "0%-23.6%(strong_zone)"
    if retracement <= 0.382:
        return "23.6%-38.2%(healthy_pullback)"
    if retracement <= 0.5:
        return "38.2%-50%(deep_pullback)"
    if retracement <= 0.618:
        return "50%-61.8%(critical_support)"
    if retracement <= 1.0:
        return "61.8%-100%(danger_zone)"
    return "BELOW_LOW(trend_broken)"


def _timeframe_alignment(daily_rsi: float | None, weekly_trend: str | None) -> str:
    """Günlük RSI yönü ile haftalık trend'i karşılaştır."""
    if daily_rsi is None or weekly_trend is None:
        return "UNKNOWN"
    daily_dir = "BULLISH" if daily_rsi > 50 else "BEARISH"
    if daily_dir == "BULLISH" and weekly_trend in ("UPTREND", "EARLY_RECOVERY"):
        return "ALIGNED"
    if daily_dir == "BEARISH" and weekly_trend in ("DOWNTREND", "EARLY_WEAKNESS"):
        return "ALIGNED"
    if weekly_trend == "SIDEWAYS":
        return "PARTIALLY_ALIGNED"
    return "CONFLICTING"


def _enrich_candidate(cand: Candidate) -> None:
    """Tek bir candidate için tüm indikatör+derived+confluence hesaplaması."""
    prices = cand.ingested.prices
    if len(prices) < 50:
        return

    # 1. Pandas-ta tüm göstergeler
    try:
        enriched = add_technical_features(prices)
    except Exception as e:
        logger.warning(f"[STAGE 1C] {cand.ticker} technical features hatası: {e}")
        return

    last = enriched.iloc[-1]
    prev = enriched.iloc[-2] if len(enriched) >= 2 else last

    # Son barın değerlerini dict'e kopyala (NaN'leri None'a çevir)
    def _val(x):
        try:
            v = float(x)
            return v if not (np.isnan(v) or np.isinf(v)) else None
        except (TypeError, ValueError):
            return None

    indicator_keys = [
        "rsi_14", "rsi_7", "macd", "macd_signal", "macd_hist",
        "stoch_k", "stoch_d", "cci_20", "willr_14", "roc_10",
        "bb_lower", "bb_mid", "bb_upper", "bb_pct", "bb_width",
        "atr_14", "atr_pct", "donch_pct",
        "vol_sma_20", "vol_ratio", "obv", "mfi_14", "cmf_20", "price_vs_vwap",
        "adx_14", "di_plus", "di_minus", "aroon_up", "aroon_down", "aroon_osc",
        "ichi_signal", "supertrend_dir",
        "sma_10", "sma_20", "sma_50", "sma_200", "ema_12", "ema_26",
        "price_vs_sma20", "price_vs_sma50", "price_vs_sma200", "sma50_vs_sma200",
        "ret_1d", "ret_5d", "ret_20d", "vol_20d", "vol_60d",
    ]
    for k in indicator_keys:
        if k in enriched.columns:
            cand.indicators[k] = _val(last.get(k))

    # 2. Derived: OBV divergence
    if "obv" in enriched.columns:
        obv_info = compute_obv_divergence(prices, enriched["obv"], lookback=5)
        cand.indicators["obv_trend"] = obv_info["trend"]
        cand.indicators["obv_divergence"] = obv_info["divergence"]
        cand.indicators["obv_divergence_type"] = obv_info["type"]
        cand.indicators["obv_ma20"] = obv_info["obv_ma20"]
        obv_above_ma20 = (
            obv_info["obv_ma20"] is not None
            and cand.indicators.get("obv") is not None
            and cand.indicators["obv"] > obv_info["obv_ma20"]
        )
    else:
        obv_info = {"trend": None, "type": None}
        obv_above_ma20 = None

    # 3. Derived: BB squeeze
    if all(k in enriched.columns for k in ("bb_upper", "bb_lower", "bb_mid")):
        squeeze_info = compute_bb_squeeze(
            enriched["bb_upper"], enriched["bb_lower"], enriched["bb_mid"]
        )
        cand.indicators["bb_squeeze"] = squeeze_info["squeeze"]
        cand.indicators["bb_width_trend"] = squeeze_info["trend"]
    else:
        squeeze_info = {"squeeze": None, "trend": None}

    # 4. Derived: Weekly trend
    weekly_info = compute_weekly_trend(prices)
    cand.indicators["weekly_sma20"] = weekly_info["sma20"]
    cand.indicators["weekly_sma50"] = weekly_info["sma50"]
    cand.indicators["weekly_rsi"] = weekly_info["rsi"]
    cand.indicators["weekly_trend"] = weekly_info["trend"]

    # 5. Swing levels
    swing = compute_swing_levels(prices, window=20)
    cand.indicators["swing_high_20"] = swing["swing_high"]
    cand.indicators["swing_low_20"] = swing["swing_low"]

    # 6. Market regime
    cand.regime = detect_market_regime(cand.indicators)

    # 7. Fibonacci zone (basit versiyon)
    cand.indicators["fib_zone"] = _fib_zone_from_prices(prices)

    # 8. Timeframe alignment
    alignment = _timeframe_alignment(
        cand.indicators.get("rsi_14"), weekly_info["trend"]
    )
    cand.indicators["timeframe_alignment"] = alignment

    # 9. Confluence score (8-bileşenli)
    prev_macd_hist = _val(prev.get("macd_hist")) if "macd_hist" in enriched.columns else None
    confluence = compute_confluence(
        indicators=cand.indicators,
        timeframe_alignment=alignment,
        obv_trend=obv_info["trend"],
        obv_above_ma20=obv_above_ma20,
        obv_divergence_type=obv_info["type"],
        bb_squeeze=squeeze_info["squeeze"],
        fib_zone=cand.indicators["fib_zone"],
        prev_macd_hist=prev_macd_hist,
    )
    cand.confluence_score = confluence.total()
    cand.confluence_detail = confluence.as_dict()

    # 10. Fundamental scoring (Phase 3.1)
    fund_snap = cand.ingested.fundamentals
    if fund_snap is not None:
        fund_score = compute_fundamental_score(fund_snap)
        cand.fundamental_score = fund_score.total
        cand.fundamental_detail = fund_score.as_dict()


def run_stage1c(ctx: PipelineContext) -> PipelineContext:
    """Stage 1C entry: hard filter'ı geçenlere indikatör hesabı + confluence."""
    started = time.perf_counter()
    active = ctx.active_candidates

    for cand in active:
        try:
            _enrich_candidate(cand)
        except Exception as e:
            logger.warning(f"[STAGE 1C] {cand.ticker} enrich hatası: {e}")

    duration = time.perf_counter() - started
    ctx.log_stage("stage1c_features", duration)

    # Top 10 by confluence
    by_conf = sorted(active, key=lambda c: c.confluence_score, reverse=True)
    logger.info(
        f"[STAGE 1C] {ctx.market}: {len(active)} hisse indikatör+confluence hesaplandı "
        f"({duration:.2f}s)"
    )
    if by_conf:
        top10 = by_conf[:10]
        logger.info(
            f"[STAGE 1C] top by confluence: "
            + ", ".join(
                f"{c.ticker.symbol}({c.confluence_score}|{c.regime})"
                for c in top10
            )
        )

    return ctx
