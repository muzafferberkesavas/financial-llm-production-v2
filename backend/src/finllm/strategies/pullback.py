"""Pullback-to-EMA strategy — kullanıcının manuel TradingView pattern'i.

Mevcut stage1b_setup.py'deki algoritmayı strategy abstraction'a port.
Aktif regime: TREND, STRONG_TREND, TRANSITIONAL (trend devamı bekleniyor).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from finllm.strategies.base import Regime, StrategySetup, TradingStrategy


class PullbackToEMAStrategy:
    """Düşük hacimle EMA21'e çekildikten sonra hacimle reversal."""

    name = "pullback_ema"
    applicable_regimes: tuple[Regime, ...] = ("TREND", "STRONG_TREND", "TRANSITIONAL")

    def detect(
        self,
        prices: pd.DataFrame,
        indicators: dict[str, float | None],
    ) -> StrategySetup | None:
        if len(prices) < 21:
            return None

        ema21 = indicators.get("ema_21") or indicators.get("ema21")
        if ema21 is None:
            return None

        closes = prices["close"].values
        highs = prices["high"].values
        lows = prices["low"].values
        opens = prices["open"].values
        volumes = prices["volume"].values

        avg_vol_20 = float(np.mean(volumes[-21:-1]))
        if avg_vol_20 == 0:
            return None

        # Pullback window: son 5 gün (bugün hariç)
        pullback_vols = volumes[-6:-1]
        pullback_closes = closes[-6:-1]
        pullback_lows = lows[-6:-1]

        vol_dryup = float(np.mean(pullback_vols)) / avg_vol_20
        pullback_change = (pullback_closes[-1] - pullback_closes[0]) / pullback_closes[0]
        min_low = float(np.min(pullback_lows))
        touched_ema = min_low <= ema21 * 1.02 and min_low >= ema21 * 0.95

        # Bugün — reversal
        today_vol = float(volumes[-1])
        vol_breakout = today_vol / avg_vol_20
        today_green = bool(closes[-1] > opens[-1])
        broke_yest_high = bool(closes[-1] > highs[-2])

        score = 0.0
        if vol_dryup < 0.8:
            score += 0.25
        elif vol_dryup < 1.0:
            score += 0.15

        if -0.05 <= pullback_change < 0:
            score += 0.20
        elif pullback_change < -0.05:
            score += 0.10

        if touched_ema:
            score += 0.20

        if vol_breakout >= 1.5:
            score += 0.20
        elif vol_breakout >= 1.3:
            score += 0.15

        if today_green and broke_yest_high:
            score += 0.15
        elif today_green:
            score += 0.05

        score = min(score, 1.0)
        if score < 0.3:
            return None

        return StrategySetup(
            strategy=self.name,
            setup_score=score,
            metadata={
                "vol_dryup_ratio": round(vol_dryup, 2),
                "pullback_pct": round(pullback_change * 100, 2),
                "touched_ema21": touched_ema,
                "today_vol_ratio": round(vol_breakout, 2),
                "today_green": today_green,
                "broke_yesterday_high": broke_yest_high,
            },
            rationale=(
                f"Pullback-to-EMA21 ({pullback_change * 100:+.1f}% with vol_dryup "
                f"{vol_dryup:.2f}x); today reversal {vol_breakout:.2f}x avg vol."
            ),
        )


# Type assert
_assert_protocol: TradingStrategy = PullbackToEMAStrategy()  # noqa: F841
