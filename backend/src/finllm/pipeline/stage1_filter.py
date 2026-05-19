"""Stage 1 — Hard filter: TradingView clone, MarketAdapter eşikleriyle.

Kullanıcının manuel taraması (lib.zip + memory/trading-strategy):
    ✓ close > min_price
    ✓ close > prev_close (yeşil gün)
    ✓ market_cap >= min_market_cap
    ✓ avg_volume_10d > min_avg_volume_10d
    ✓ daily $ volume > min_daily_dollar_volume
    ✓ ADR >= min_adr_pct (Average Daily Range %)
    ✓ close > EMA21 ve close > EMA50 (uptrend)

Output: Candidate listesi (passed_hard_filter ile işaretlenmiş).
Bu stage ZERO LLM maliyetli — sadece pandas hesaplama.
"""
from __future__ import annotations

import time

import numpy as np
import pandas as pd

from finllm.pipeline.context import Candidate, IngestedData, PipelineContext
from finllm.utils.logging import logger


def _compute_adr_pct(prices: pd.DataFrame, period: int = 20) -> float:
    """Average Daily Range (yüzde olarak).

    ADR % = mean((high - low) / close) * 100, son `period` gün.
    TradingView'in ADR(20) ile aynı tanım.
    """
    if len(prices) < period:
        return 0.0
    recent = prices.tail(period)
    daily_range = (recent["high"] - recent["low"]) / recent["close"]
    return float(daily_range.mean() * 100)


def _compute_ema(values: pd.Series, period: int) -> float | None:
    """Son bar için EMA — pandas .ewm() ile."""
    if len(values) < period:
        return None
    return float(values.ewm(span=period, adjust=False).mean().iloc[-1])


def _check_one(data: IngestedData, thresholds, currency: str) -> Candidate:
    """Tek ticker için tüm filtreleri sırayla uygula, ilk fail'de işaretle."""
    cand = Candidate(ticker=data.ticker, ingested=data)

    # Veri yeterli mi?
    if not data.has_price_data:
        return cand.reject(f"insufficient_data ({len(data.prices)} bars)")

    prices = data.prices
    latest = prices.iloc[-1]
    close = float(latest["close"])
    prev_close = float(prices["close"].iloc[-2]) if len(prices) >= 2 else close

    # 1. Min price
    if close < thresholds.min_price:
        return cand.reject(f"price<{thresholds.min_price} ({close:.2f})")

    # 2. Green day (today close > yesterday close)
    if thresholds.require_green_day and close <= prev_close:
        return cand.reject(f"not_green_day (close={close:.2f} prev={prev_close:.2f})")

    # 3. Market cap
    if data.fundamentals and data.fundamentals.market_cap is not None:
        mcap = float(data.fundamentals.market_cap)
        if mcap < thresholds.min_market_cap:
            return cand.reject(
                f"mcap<{thresholds.min_market_cap:.0e} ({mcap:.2e})"
            )

    # 4. Average volume 10d
    avg_vol_10d: float | None = None
    if data.fundamentals and data.fundamentals.avg_volume_10d is not None:
        avg_vol_10d = float(data.fundamentals.avg_volume_10d)
    elif len(prices) >= 10:
        avg_vol_10d = float(prices["volume"].tail(10).mean())

    if avg_vol_10d is not None and avg_vol_10d < thresholds.min_avg_volume_10d:
        return cand.reject(
            f"avg_vol_10d<{thresholds.min_avg_volume_10d:.0f} ({avg_vol_10d:.0f})"
        )

    # 5. Daily dollar volume (today's vol × close)
    today_vol = float(latest["volume"]) if not pd.isna(latest["volume"]) else 0.0
    daily_dollar = today_vol * close
    if daily_dollar < thresholds.min_daily_dollar_volume:
        return cand.reject(
            f"daily_${currency}_vol<{thresholds.min_daily_dollar_volume:.0e} "
            f"({daily_dollar:.2e})"
        )

    # 6. ADR%
    adr = _compute_adr_pct(prices, period=20)
    if adr < thresholds.min_adr_pct:
        return cand.reject(f"adr<{thresholds.min_adr_pct}% ({adr:.2f}%)")

    # 7. EMA21 / EMA50 uptrend
    closes = prices["close"]
    ema21 = _compute_ema(closes, 21)
    ema50 = _compute_ema(closes, 50)

    if thresholds.require_close_above_ema21:
        if ema21 is None:
            return cand.reject("ema21_insufficient_data")
        if close <= ema21:
            return cand.reject(f"close<=ema21 ({close:.2f} <= {ema21:.2f})")

    if thresholds.require_close_above_ema50:
        if ema50 is None:
            return cand.reject("ema50_insufficient_data")
        if close <= ema50:
            return cand.reject(f"close<=ema50 ({close:.2f} <= {ema50:.2f})")

    # Hepsi geçti — score için ekstra metadata
    cand.passed_hard_filter = True
    cand.indicators.update({
        "close": close,
        "ema21": ema21,
        "ema50": ema50,
        "adr_pct": adr,
        "avg_vol_10d": avg_vol_10d or 0.0,
        "daily_dollar_volume": daily_dollar,
        "close_vs_ema21_pct": (close - ema21) / ema21 * 100 if ema21 else 0.0,
        "close_vs_ema50_pct": (close - ema50) / ema50 * 100 if ema50 else 0.0,
    })

    # Hard filter score — eşiklere ne kadar uzak (ranking için)
    # Higher = more bullish: above ema by more, more adr, more volume
    score_components = [
        cand.indicators["close_vs_ema21_pct"],
        cand.indicators["close_vs_ema50_pct"],
        adr,
        np.log10(max(daily_dollar, 1)) - np.log10(thresholds.min_daily_dollar_volume),
    ]
    cand.hard_filter_score = float(np.mean(score_components))

    return cand


def run_stage1(ctx: PipelineContext) -> PipelineContext:
    """Stage 1 entry: ingest edilen tüm ticker'ları filtreden geçir."""
    started = time.perf_counter()
    thresholds = ctx.adapter.thresholds
    currency = ctx.adapter.currency

    candidates: list[Candidate] = []
    for data in ctx.ingested:
        cand = _check_one(data, thresholds, currency)
        candidates.append(cand)

    passed = [c for c in candidates if c.passed_hard_filter]
    passed.sort(key=lambda c: c.hard_filter_score, reverse=True)

    # Rejected reason istatistiği (debug için)
    reject_stats: dict[str, int] = {}
    for c in candidates:
        if not c.passed_hard_filter and c.rejected_reasons:
            first_reason = c.rejected_reasons[0].split(" ")[0]
            reject_stats[first_reason] = reject_stats.get(first_reason, 0) + 1

    ctx.candidates = candidates
    duration = time.perf_counter() - started
    ctx.log_stage("stage1_filter", duration)

    logger.info(
        f"[STAGE 1] {ctx.market}: {len(passed)}/{len(candidates)} hisse hard filter geçti "
        f"({duration:.2f}s)"
    )
    if reject_stats:
        top_rejects = sorted(reject_stats.items(), key=lambda x: -x[1])[:5]
        logger.info(
            f"[STAGE 1] reject breakdown: "
            f"{', '.join(f'{k}={v}' for k, v in top_rejects)}"
        )
    if passed:
        top5 = passed[:5]
        logger.info(
            f"[STAGE 1] top 5 by score: "
            f"{', '.join(f'{c.ticker.symbol}({c.hard_filter_score:.1f})' for c in top5)}"
        )

    return ctx
