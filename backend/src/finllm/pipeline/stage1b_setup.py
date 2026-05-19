"""Stage 1B — Setup detection: pullback-to-EMA + volume breakout.

Kullanıcının manuel TradingView'da avladığı pattern'in algoritmik versiyonu
(bkz memory/trading-strategy.md):

PULLBACK-TO-EMA:
    Son 5 gün:
        - mean(volume[N-5..N-1]) < avg_vol_20 * 0.8 (kuruyan ilgi)
        - close[N-1] < close[N-5] (gerileme)
        - min(low[N-5..N-1]) <= ema21 * 1.02 (EMA21'e temas)

    Bugün (N):
        - volume[N] > avg_vol_20 * 1.3 (hacim patlaması)
        - close[N] > open[N] (yeşil mum)
        - close[N] > high[N-1] (önceki günü kırdı)

BULL FLAG (alternatif, daha az sıkı):
    - Son 3-7 günlük dar konsolidasyon (range < 5%)
    - Konsolidasyon öncesi +5% sharp impulse
    - Bugün konsolidasyon tepesini hacimle kırış

BREAKOUT (yedek):
    - Son 20 gün high'ı kırış
    - Hacim > 1.5x avg_vol_20

Bu stage sadece passed_hard_filter=True olan candidate'lara uygulanır.
LLM maliyeti SIFIR.
"""
from __future__ import annotations

import time
from typing import Literal

import numpy as np
import pandas as pd

from finllm.pipeline.context import Candidate, PipelineContext
from finllm.utils.logging import logger

SetupType = Literal["pullback_ema", "bull_flag", "breakout", "none"]


def _detect_pullback_ema(prices: pd.DataFrame, ema21: float) -> tuple[float, dict]:
    """Pullback-to-EMA pattern strength (0-1) ve metadata döner.

    Yüksek skor = klasik pattern. Tüm koşullar tam sağlanırsa ~0.9+.
    """
    if len(prices) < 21:
        return 0.0, {"reason": "insufficient_history"}

    closes = prices["close"].values
    highs = prices["high"].values
    lows = prices["low"].values
    opens = prices["open"].values
    volumes = prices["volume"].values

    today_idx = -1
    yest_idx = -2

    # avg vol 20 (bugün hariç son 20)
    avg_vol_20 = float(np.mean(volumes[-21:-1]))
    if avg_vol_20 == 0:
        return 0.0, {"reason": "zero_avg_vol"}

    # Son 5 gün (N-5..N-1, bugün hariç) düşük hacimli pullback
    pullback_window = slice(-6, -1)  # 5 gün
    pullback_vols = volumes[pullback_window]
    pullback_closes = closes[pullback_window]
    pullback_lows = lows[pullback_window]

    pullback_avg_vol = float(np.mean(pullback_vols))
    vol_dryup_ratio = pullback_avg_vol / avg_vol_20

    # Pullback yönü: son 5 günde düşen
    pullback_change = (pullback_closes[-1] - pullback_closes[0]) / pullback_closes[0]

    # EMA21'e dokunma (son 5 gün lows EMA21'in %2 altına geldi mi)
    min_low = float(np.min(pullback_lows))
    touched_ema = min_low <= ema21 * 1.02 and min_low >= ema21 * 0.95

    # Bugün — breakout
    today_vol = float(volumes[today_idx])
    vol_breakout_ratio = today_vol / avg_vol_20

    today_green = bool(closes[today_idx] > opens[today_idx])
    broke_yesterday_high = bool(closes[today_idx] > highs[yest_idx])

    # Scoring (0-1, ağırlıklı)
    score = 0.0
    metadata = {
        "vol_dryup_ratio": round(vol_dryup_ratio, 2),
        "pullback_pct": round(pullback_change * 100, 2),
        "touched_ema21": touched_ema,
        "min_low": round(min_low, 2),
        "ema21": round(ema21, 2),
        "today_vol_ratio": round(vol_breakout_ratio, 2),
        "today_green": today_green,
        "broke_yesterday_high": broke_yesterday_high,
    }

    # Vol dry-up — 0.8 altı ideal
    if vol_dryup_ratio < 0.8:
        score += 0.25
    elif vol_dryup_ratio < 1.0:
        score += 0.15

    # Pullback negatif olmalı
    if -0.05 <= pullback_change < 0:
        score += 0.20  # ideal, küçük gerileme
    elif pullback_change < -0.05:
        score += 0.10  # daha derin pullback

    # EMA dokunma
    if touched_ema:
        score += 0.20

    # Bugün vol breakout
    if vol_breakout_ratio >= 1.5:
        score += 0.20
    elif vol_breakout_ratio >= 1.3:
        score += 0.15
    elif vol_breakout_ratio >= 1.0:
        score += 0.05

    # Today candle confirmation
    if today_green and broke_yesterday_high:
        score += 0.15
    elif today_green:
        score += 0.05

    return min(score, 1.0), metadata


def _detect_breakout(prices: pd.DataFrame) -> tuple[float, dict]:
    """20-gün high kırılışı (basit momentum breakout)."""
    if len(prices) < 21:
        return 0.0, {"reason": "insufficient_history"}

    closes = prices["close"].values
    highs = prices["high"].values
    volumes = prices["volume"].values

    today = -1
    high_20 = float(np.max(highs[-21:-1]))  # bugün hariç son 20
    today_close = float(closes[today])
    today_vol = float(volumes[today])
    avg_vol_20 = float(np.mean(volumes[-21:-1]))

    if avg_vol_20 == 0:
        return 0.0, {"reason": "zero_avg_vol"}

    broke_high = today_close > high_20
    vol_ratio = today_vol / avg_vol_20

    metadata = {
        "high_20": round(high_20, 2),
        "today_close": round(today_close, 2),
        "vol_ratio": round(vol_ratio, 2),
        "broke_20d_high": broke_high,
    }

    score = 0.0
    if broke_high:
        score += 0.5
        if vol_ratio >= 1.5:
            score += 0.4
        elif vol_ratio >= 1.2:
            score += 0.2

    return min(score, 1.0), metadata


def _detect_bull_flag(prices: pd.DataFrame) -> tuple[float, dict]:
    """Sharp impulse + tight consolidation + breakout."""
    if len(prices) < 15:
        return 0.0, {"reason": "insufficient_history"}

    closes = prices["close"].values

    # Son 5 gün konsolidasyon
    recent_5 = closes[-6:-1]
    range_5 = (recent_5.max() - recent_5.min()) / recent_5.min()

    # 6-10 gün önce impulse (5'lik ortalama)
    if len(closes) < 11:
        return 0.0, {"reason": "insufficient_history"}
    impulse_window = closes[-11:-6]
    impulse_change = (impulse_window[-1] - impulse_window[0]) / impulse_window[0]

    # Bugün breakout
    today_close = float(closes[-1])
    consolidation_high = float(recent_5.max())
    broke_consolidation = today_close > consolidation_high

    metadata = {
        "consolidation_range_pct": round(range_5 * 100, 2),
        "impulse_pct": round(impulse_change * 100, 2),
        "broke_consolidation": broke_consolidation,
    }

    score = 0.0
    if impulse_change >= 0.05 and range_5 <= 0.05:  # impulse +5%, range <5%
        score += 0.5
        if broke_consolidation:
            score += 0.4

    return min(score, 1.0), metadata


def _best_setup(prices: pd.DataFrame, ema21: float | None) -> tuple[SetupType, float, dict]:
    """En yüksek skorlu setup'ı seç.

    Phase 3.6: lib.zip'in 3 native pattern (pullback_ema, bull_flag, breakout)
    Phase 3.6+: strategies/ package'ı (PEAD, sector_rotation) de çağrılır.
    Bu fonksiyon native detector'ları döner; ek strategies stage1b/strategies
    aracılığıyla aktif edilir.
    """
    candidates: list[tuple[SetupType, float, dict]] = []

    if ema21 is not None:
        score, meta = _detect_pullback_ema(prices, ema21)
        candidates.append(("pullback_ema", score, meta))

    score, meta = _detect_bull_flag(prices)
    candidates.append(("bull_flag", score, meta))

    score, meta = _detect_breakout(prices)
    candidates.append(("breakout", score, meta))

    candidates.sort(key=lambda x: x[1], reverse=True)
    best_type, best_score, best_meta = candidates[0]

    if best_score < 0.3:
        return "none", 0.0, {"all_setups": [
            {"type": t, "score": round(s, 2)} for t, s, _ in candidates
        ]}

    return best_type, best_score, best_meta


def _try_extended_strategies(
    cand: "Candidate",
    fundamental_snapshot,
) -> tuple[str, float, dict] | None:
    """Phase 3.6: ek stratejiler (PEAD, sector_rotation) — daha güçlü skor varsa override."""
    from finllm.strategies import all_strategies

    prices = cand.ingested.prices

    # Indicator dict (strategy contract için)
    indicators = dict(cand.indicators)
    # PEAD için earnings info ekle
    if fundamental_snapshot:
        from datetime import datetime
        if fundamental_snapshot.earnings_date:
            days = (datetime.utcnow() - fundamental_snapshot.earnings_date.replace(tzinfo=None)).days
            indicators["days_since_earnings"] = -days if days < 0 else days
        if fundamental_snapshot.last_earnings_surprise_pct is not None:
            indicators["last_earnings_surprise_pct"] = fundamental_snapshot.last_earnings_surprise_pct

    best = None
    best_score = 0.0
    for strategy in all_strategies():
        if strategy.name == "pullback_ema":
            continue  # zaten native detector'da var
        # Regime check
        if cand.regime != "UNKNOWN" and cand.regime not in strategy.applicable_regimes:
            continue
        try:
            setup = strategy.detect(prices, indicators)
        except Exception:
            continue
        if setup and setup.setup_score > best_score:
            best = setup
            best_score = setup.setup_score

    if best is None:
        return None
    return best.strategy, best.setup_score, {"rationale": best.rationale, **best.metadata}


def run_stage1b(ctx: PipelineContext, min_setup_score: float = 0.5) -> PipelineContext:
    """Stage 1B entry: hard filter'ı geçenler için setup detection."""
    started = time.perf_counter()

    active = ctx.active_candidates
    detected = 0

    for cand in active:
        ema21 = cand.indicators.get("ema21")
        prices = cand.ingested.prices
        setup_type, score, metadata = _best_setup(prices, ema21)

        # Phase 3.6: ek strategy'ler (PEAD, sector rotation)
        ext = _try_extended_strategies(cand, cand.ingested.fundamentals)
        if ext and ext[1] > score:
            setup_type = ext[0]
            score = ext[1]
            metadata = ext[2]

        cand.setup_type = setup_type
        cand.setup_confidence = score
        cand.setup_metadata = metadata

        if setup_type != "none":
            detected += 1

    # Setup score'u min eşik altındaki candidate'ları filter dışı bırakma —
    # sadece etiketle, Stage 4 LLM'in son kararı olsun
    high_quality = [c for c in active if c.setup_confidence >= min_setup_score]

    duration = time.perf_counter() - started
    ctx.log_stage("stage1b_setup", duration)

    logger.info(
        f"[STAGE 1B] {ctx.market}: {detected}/{len(active)} setup tespit edildi, "
        f"{len(high_quality)} >= {min_setup_score} threshold ({duration:.2f}s)"
    )
    if high_quality:
        sorted_by_setup = sorted(high_quality, key=lambda c: c.setup_confidence, reverse=True)
        top5 = sorted_by_setup[:5]
        logger.info(
            f"[STAGE 1B] top setups: "
            + ", ".join(
                f"{c.ticker.symbol}({c.setup_type}:{c.setup_confidence:.2f})"
                for c in top5
            )
        )

    return ctx
