"""Stage 4 — Meta-judge: multi-confirmation + position allocation.

Anthropic'in "auditor" pattern'i + memory/trading-strategy.md allocation logic.

Checks (Stage 3 output üzerinde):
  1. Minimum return threshold (ctx.min_expected_return_pct, default %5)
  2. Multi-confirmation rule — confluence detail'de en az 3 bileşen >= eşik
  3. [UNSOURCED] flag check — varsa confidence × 0.7
  4. Regime kill-switch — TRANSITIONAL ise confidence -0.1
  5. Position sizing: confidence × expected_return × prob_base → weight
  6. Max position cap (default %25), cash buffer (default %15)
"""
from __future__ import annotations

import time

from finllm.calibration import PlattCalibrator, recommend_kelly_size
from finllm.pipeline.context import ExtendedSignal, PipelineContext
from finllm.utils.logging import logger


def _count_confirmations(sig: ExtendedSignal) -> int:
    """Sinyalin kaç farklı bileşeni güçlü?"""
    return sum(
        1
        for v in (
            sig.confluence_score >= 55,
            sig.market_regime in ("TREND", "STRONG_TREND"),
            sig.weekly_trend in ("UPTREND", "EARLY_RECOVERY"),
            sig.expected_return_pct is not None and sig.expected_return_pct >= 8,
            bool(sig.scenarios) and len(sig.scenarios) >= 3,
            not sig.unsourced_flag,
        )
        if v
    )


def _apply_quality_filters(sig: ExtendedSignal, ctx: PipelineContext) -> ExtendedSignal:
    """Bireysel sinyale kalite check'leri uygula. Confidence düşürebilir, sinyal değiştirebilir."""
    # 1. Min return — düşük getiri sinyalleri TUT'a düşür
    if (
        sig.expected_return_pct is not None
        and sig.expected_return_pct < ctx.min_expected_return_pct
        and sig.signal in ("AL", "GUCLU_AL")
    ):
        sig.signal = "TUT"
        sig.warning_flags.append(
            f"REJECTED_LOW_RETURN(<{ctx.min_expected_return_pct}%)"
        )

    # 2. [UNSOURCED] cezası
    if sig.unsourced_flag:
        sig.confidence *= 0.7
        sig.warning_flags.append("UNSOURCED_DOWNGRADE")

    # 3. Regime-based cap
    if sig.market_regime == "TRANSITIONAL":
        sig.confidence = max(0.0, sig.confidence - 0.1)
        sig.warning_flags.append("REGIME_TRANSITIONAL_-0.1")
    elif sig.market_regime == "VOLATILE":
        sig.confidence = min(sig.confidence, 0.6)
        sig.warning_flags.append("VOLATILE_CAP_0.6")

    # 4. Multi-confirmation check
    sig.confirmation_count = _count_confirmations(sig)
    if sig.confirmation_count < 3 and sig.signal in ("AL", "GUCLU_AL"):
        # Downgrade 1 level
        if sig.signal == "GUCLU_AL":
            sig.signal = "AL"
        else:
            sig.signal = "IZLE"
        sig.warning_flags.append(f"INSUFFICIENT_CONFIRMATIONS({sig.confirmation_count})")
        sig.confidence *= 0.85

    # 5. Regime kill-switch (eğer Stage 0'da yakalanmadıysa)
    if ctx.regime and not ctx.regime.trade_enabled:
        sig.signal = "TUT"
        sig.confidence = 0.0
        sig.warning_flags.append(f"REGIME_HALT:{ctx.regime.halt_reason}")

    sig.confidence = round(max(0.0, min(1.0, sig.confidence)), 3)
    return sig


def _allocate_kelly(signals: list[ExtendedSignal], ctx: PipelineContext) -> None:
    """Kelly-based allocation overlay — calibrated_probability + win/loss ratio'dan."""
    actionable = [s for s in signals if s.signal in ("AL", "GUCLU_AL") and s.calibrated_probability]
    if not actionable:
        return

    total_kelly = 0.0
    kelly_per_sig: dict[str, float] = {}
    for sig in actionable:
        target = sig.expected_return_pct or 0
        stop_pct = None
        if sig.stop_loss and sig.entry_zone_low:
            entry = (sig.entry_zone_low + sig.entry_zone_high) / 2 if sig.entry_zone_high else sig.entry_zone_low
            stop_pct = (sig.stop_loss - entry) / entry * 100
        if not stop_pct or target <= 0:
            continue

        rec = recommend_kelly_size(
            calibrated_probability=sig.calibrated_probability,
            target_return_pct=target,
            stop_loss_pct=stop_pct,
            total_capital=ctx.total_capital,
            kelly_multiplier=0.5,  # half Kelly
            max_position_pct=ctx.max_position_pct,
        )
        kelly_per_sig[sig.ticker.symbol] = rec["kelly_fraction"]
        total_kelly += rec["kelly_fraction"]

    if total_kelly <= 0:
        return

    investable = ctx.total_capital * (1.0 - ctx.cash_buffer_pct)
    # Yeniden ağırlıkla — Kelly fraction'ları normalize et
    for sig in actionable:
        kf = kelly_per_sig.get(sig.ticker.symbol, 0)
        if kf <= 0:
            continue
        sig.allocation_weight = round(min(kf, ctx.max_position_pct), 4)
        sig.allocation_cash = round(ctx.total_capital * sig.allocation_weight, 2)


def _allocate_positions(
    signals: list[ExtendedSignal],
    total_capital: float,
    max_position_pct: float,
    cash_buffer_pct: float,
    max_positions: int,
) -> list[ExtendedSignal]:
    """Confidence × expected_return × base_prob weighted allocation.

    Cash buffer her zaman tutulur (yeni fırsatlar için).
    Tek pozisyon max_position_pct'i geçemez.
    """
    eligible = [
        s
        for s in signals
        if s.signal in ("AL", "GUCLU_AL")
        and s.expected_return_pct is not None
        and s.expected_return_pct > 0
    ]
    if not eligible:
        return signals

    # Top N
    eligible.sort(key=lambda s: s.confidence, reverse=True)
    eligible = eligible[:max_positions]

    # Score: confidence × expected_return × prob_base
    def score(s: ExtendedSignal) -> float:
        prob_base = 0.55  # default
        for sc in s.scenarios:
            if sc.label == "base":
                prob_base = sc.probability
                break
        return s.confidence * (s.expected_return_pct or 0) * prob_base

    scores = {s.ticker.symbol: score(s) for s in eligible}
    total_score = sum(scores.values())
    if total_score <= 0:
        return signals

    investable = total_capital * (1.0 - cash_buffer_pct)

    for s in eligible:
        raw_weight = scores[s.ticker.symbol] / total_score
        capped_weight = min(raw_weight, max_position_pct)
        s.allocation_weight = round(capped_weight, 4)
        s.allocation_cash = round(investable * capped_weight, 2)

    # Re-normalize if any position was capped
    total_alloc = sum(s.allocation_weight for s in eligible)
    if total_alloc > 0:
        scale = min(1.0, (1.0 - cash_buffer_pct) / total_alloc)
        for s in eligible:
            s.allocation_weight = round(s.allocation_weight * scale, 4)
            s.allocation_cash = round(s.allocation_weight * total_capital, 2)

    return signals


def run_stage4(ctx: PipelineContext) -> PipelineContext:
    """Stage 4 entry: kalite filtreleri + allocation + (varsa) Platt + Kelly."""
    started = time.perf_counter()
    signals = ctx.signals

    if not signals:
        logger.warning("[STAGE 4] Sinyal yok, skip")
        ctx.log_stage("stage4_judge", time.perf_counter() - started)
        return ctx

    # 1. Quality filters
    for sig in signals:
        _apply_quality_filters(sig, ctx)

    # 2. Calibration (varsa eğitilmiş model)
    calibrator = PlattCalibrator.load()
    if calibrator.is_trained:
        for sig in signals:
            sig.calibrated_probability = round(
                calibrator.predict(
                    confidence=sig.confidence,
                    confluence_score=sig.confluence_score,
                    confirmation_count=sig.confirmation_count,
                    market_regime=sig.market_regime,
                    timeframe_alignment=sig.weekly_trend or "UNKNOWN",
                ),
                3,
            )
        logger.info(
            f"[STAGE 4] Platt calibration applied (n_train={calibrator.n_train}, "
            f"hit_rate_history={calibrator.n_wins / max(1, calibrator.n_train):.2%})"
        )
    else:
        # Identity — raw confidence = calibrated_probability
        for sig in signals:
            sig.calibrated_probability = sig.confidence

    # 3. Allocation: calibrated_probability + Kelly varsa onu kullan
    _allocate_positions(
        signals,
        ctx.total_capital,
        ctx.max_position_pct,
        ctx.cash_buffer_pct,
        ctx.max_positions,
    )

    # 4. Kelly recommendation (calibrator trained ise allocation'ın Kelly versiyonu)
    if calibrator.is_trained:
        _allocate_kelly(signals, ctx)

    by_signal = {}
    allocated_count = 0
    total_alloc_cash = 0.0
    for s in signals:
        by_signal[s.signal] = by_signal.get(s.signal, 0) + 1
        if s.allocation_cash > 0:
            allocated_count += 1
            total_alloc_cash += s.allocation_cash

    duration = time.perf_counter() - started
    ctx.log_stage("stage4_judge", duration)
    logger.info(
        f"[STAGE 4] judge: {by_signal} | allocated {allocated_count} positions "
        f"= ${total_alloc_cash:.0f} ({duration:.2f}s)"
    )

    # Top allocated
    by_alloc = sorted(signals, key=lambda s: s.allocation_cash, reverse=True)
    for s in by_alloc[:5]:
        if s.allocation_cash > 0:
            logger.info(
                f"[STAGE 4] {s.ticker.symbol:<6} {s.signal:<10} "
                f"weight={s.allocation_weight:.1%} cash=${s.allocation_cash:.0f} "
                f"confirmations={s.confirmation_count}"
            )

    return ctx
