"""Setup detection — stage1b'den tasinmis pattern algilama fonksiyonlari."""
from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd

SetupType = Literal["pullback_ema", "bull_flag", "breakout", "none"]


def _detect_pullback_ema(prices: pd.DataFrame, ema21: float) -> tuple[float, dict]:
    """Pullback-to-EMA pattern strength (0-1) ve metadata doner."""
    if len(prices) < 21:
        return 0.0, {"reason": "insufficient_history"}

    closes = prices["close"].values
    highs = prices["high"].values
    lows = prices["low"].values
    opens = prices["open"].values
    volumes = prices["volume"].values

    today_idx = -1
    yest_idx = -2

    avg_vol_20 = float(np.mean(volumes[-21:-1]))
    if avg_vol_20 == 0:
        return 0.0, {"reason": "zero_avg_vol"}

    pullback_window = slice(-6, -1)
    pullback_vols = volumes[pullback_window]
    pullback_closes = closes[pullback_window]
    pullback_lows = lows[pullback_window]

    pullback_avg_vol = float(np.mean(pullback_vols))
    vol_dryup_ratio = pullback_avg_vol / avg_vol_20

    pullback_change = (pullback_closes[-1] - pullback_closes[0]) / pullback_closes[0]

    min_low = float(np.min(pullback_lows))
    touched_ema = min_low <= ema21 * 1.02 and min_low >= ema21 * 0.95

    today_vol = float(volumes[today_idx])
    vol_breakout_ratio = today_vol / avg_vol_20

    today_green = bool(closes[today_idx] > opens[today_idx])
    broke_yesterday_high = bool(closes[today_idx] > highs[yest_idx])

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

    if vol_dryup_ratio < 0.8:
        score += 0.25
    elif vol_dryup_ratio < 1.0:
        score += 0.15

    if -0.05 <= pullback_change < 0:
        score += 0.20
    elif pullback_change < -0.05:
        score += 0.10

    if touched_ema:
        score += 0.20

    if vol_breakout_ratio >= 1.5:
        score += 0.20
    elif vol_breakout_ratio >= 1.3:
        score += 0.15
    elif vol_breakout_ratio >= 1.0:
        score += 0.05

    if today_green and broke_yesterday_high:
        score += 0.15
    elif today_green:
        score += 0.05

    return min(score, 1.0), metadata


def _detect_breakout(prices: pd.DataFrame) -> tuple[float, dict]:
    """20-gun high kirilisi."""
    if len(prices) < 21:
        return 0.0, {"reason": "insufficient_history"}

    closes = prices["close"].values
    highs = prices["high"].values
    volumes = prices["volume"].values

    high_20 = float(np.max(highs[-21:-1]))
    today_close = float(closes[-1])
    today_vol = float(volumes[-1])
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

    recent_5 = closes[-6:-1]
    range_5 = (recent_5.max() - recent_5.min()) / recent_5.min()

    if len(closes) < 11:
        return 0.0, {"reason": "insufficient_history"}
    impulse_window = closes[-11:-6]
    impulse_change = (impulse_window[-1] - impulse_window[0]) / impulse_window[0]

    today_close = float(closes[-1])
    consolidation_high = float(recent_5.max())
    broke_consolidation = today_close > consolidation_high

    metadata = {
        "consolidation_range_pct": round(range_5 * 100, 2),
        "impulse_pct": round(impulse_change * 100, 2),
        "broke_consolidation": broke_consolidation,
    }

    score = 0.0
    if impulse_change >= 0.05 and range_5 <= 0.05:
        score += 0.5
        if broke_consolidation:
            score += 0.4

    return min(score, 1.0), metadata


def _best_setup(prices: pd.DataFrame, ema21: float | None) -> tuple[SetupType, float, dict]:
    """En yuksek skorlu setup'i sec."""
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


def detect_setup(prices: pd.DataFrame, ema21: float | None,
                 cand=None, snap=None) -> tuple[str, float, dict]:
    """Public API: setup detection + opsiyonel extended strategies.

    Returns:
        (setup_type, confidence, metadata)
    """
    setup_type, score, metadata = _best_setup(prices, ema21)

    # Extended strategies (PEAD, sector rotation)
    if cand is not None:
        ext = _try_extended_strategies(cand, snap)
        if ext and ext[1] > score:
            setup_type = ext[0]
            score = ext[1]
            metadata = ext[2]

    return setup_type, score, metadata


def _try_extended_strategies(cand, fundamental_snapshot) -> tuple[str, float, dict] | None:
    """Ek stratejiler (PEAD, sector_rotation)."""
    try:
        from finllm.strategies import all_strategies
    except ImportError:
        return None

    prices = cand.ingested.prices
    indicators = dict(cand.indicators)

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
            continue
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
