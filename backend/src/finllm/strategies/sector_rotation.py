"""Sector rotation — sektör momentum'ı + relative strength.

Setup:
  - Hisse 20g performansı sektör ortalamasının üstünde (relative strength)
  - Sektörün kendisi 1ay+ momentum içinde (sector ETF momentum)
  - Hisse 50g MA üstünde (yapısal uptrend)
  - RSI < 75 (overbought değil)

Stage 1B'de bireysel hisse seviyesi proxy:
  - 20g return > 5% (sektör median'ı için fallback)
  - 50g return > 0%
  - Volume profile yükseliyor (avg vol 10d > avg vol 30d)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from finllm.strategies.base import Regime, StrategySetup, TradingStrategy


class SectorRotationStrategy:
    """Momentum + relative strength setup."""

    name = "sector_rotation"
    applicable_regimes: tuple[Regime, ...] = ("TREND", "STRONG_TREND")

    def detect(
        self,
        prices: pd.DataFrame,
        indicators: dict[str, float | None],
    ) -> StrategySetup | None:
        if len(prices) < 60:
            return None

        closes = prices["close"]
        volumes = prices["volume"]

        # 20g momentum
        ret_20d = (closes.iloc[-1] / closes.iloc[-20] - 1) * 100 if len(closes) >= 20 else 0
        # 50g momentum
        ret_50d = (closes.iloc[-1] / closes.iloc[-50] - 1) * 100 if len(closes) >= 50 else 0
        # 10g vol ratio (rising interest)
        vol_10d = float(volumes.tail(10).mean())
        vol_30d = float(volumes.tail(30).mean()) if len(volumes) >= 30 else vol_10d
        vol_trend = vol_10d / vol_30d if vol_30d > 0 else 1

        # SMA50 üstünde mi?
        sma50 = float(closes.tail(50).mean())
        above_sma50 = closes.iloc[-1] > sma50

        # RSI < 75 (yer var)
        rsi = indicators.get("rsi_14")
        not_overbought = rsi is None or rsi < 75

        # Scoring
        score = 0.0
        if ret_20d > 10:
            score += 0.30
        elif ret_20d > 5:
            score += 0.20
        elif ret_20d > 0:
            score += 0.05

        if ret_50d > 15:
            score += 0.30
        elif ret_50d > 5:
            score += 0.20

        if vol_trend > 1.2:
            score += 0.15
        elif vol_trend > 1.0:
            score += 0.05

        if above_sma50:
            score += 0.15

        if not_overbought:
            score += 0.10

        score = min(score, 1.0)
        if score < 0.5:
            return None

        return StrategySetup(
            strategy=self.name,
            setup_score=score,
            metadata={
                "ret_20d_pct": round(ret_20d, 2),
                "ret_50d_pct": round(ret_50d, 2),
                "vol_trend": round(vol_trend, 2),
                "above_sma50": above_sma50,
                "rsi_14": round(rsi, 1) if rsi else None,
            },
            rationale=(
                f"Momentum: 20d {ret_20d:+.1f}%, 50d {ret_50d:+.1f}%, "
                f"vol trend {vol_trend:.2f}x, RSI {rsi:.1f if rsi else 'N/A'}."
            ),
        )


_assert_protocol: TradingStrategy = SectorRotationStrategy()  # noqa: F841
