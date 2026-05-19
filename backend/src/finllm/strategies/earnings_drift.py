"""Post-Earnings Announcement Drift (PEAD) — akademik en güçlü anomali.

Setup:
  - Son 30 gün içinde EPS beat veya revenue beat (positive earnings surprise)
  - Bilanço sonrası fiyat ≥ %2 yukarı reaksiyon
  - Halen yükseliş trendinde (close > EMA21)
  - Bilançodan beri henüz drift fazı (60g'ye kadar momentum devam eder)

Çıktı: setup_score 0-1.
Aktif regime: TREND, STRONG_TREND.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from finllm.strategies.base import Regime, StrategySetup, TradingStrategy


class PostEarningsDriftStrategy:
    """PEAD — earnings surprise + momentum continuation."""

    name = "post_earnings_drift"
    applicable_regimes: tuple[Regime, ...] = ("TREND", "STRONG_TREND")

    def detect(
        self,
        prices: pd.DataFrame,
        indicators: dict[str, float | None],
    ) -> StrategySetup | None:
        # Earnings surprise info — indicators dict'inde fundamental snapshot'tan gelir
        # last_earnings_surprise_pct'ı fundamental.py içinde fetch ediyoruz
        last_surprise = indicators.get("last_earnings_surprise_pct")
        days_since_earnings = indicators.get("days_since_earnings")

        # Earnings 5-30 gün önce olduysa drift fazındayız
        if days_since_earnings is None or not (5 <= days_since_earnings <= 60):
            return None

        if last_surprise is None or last_surprise < 5.0:
            # Beat <5% drift için yeterli güç değil
            return None

        if len(prices) < 50:
            return None

        ema21 = indicators.get("ema_21") or indicators.get("ema21")
        if ema21 is None or prices["close"].iloc[-1] <= ema21:
            # Trend bozulmuş
            return None

        # Earnings günü reaksiyon ne kadar güçlüydü?
        # Approx: bilanço günü +/- bar'da % değişim
        try:
            earnings_idx = -int(days_since_earnings)
            if abs(earnings_idx) >= len(prices):
                return None
            earnings_day_close = float(prices["close"].iloc[earnings_idx])
            prev_day_close = float(prices["close"].iloc[earnings_idx - 1])
            earnings_reaction_pct = (earnings_day_close - prev_day_close) / prev_day_close * 100
        except (IndexError, ZeroDivisionError):
            return None

        if earnings_reaction_pct < 2.0:
            # Pozitif beat ama piyasa karşılık vermedi
            return None

        # Score: surprise + reaction + drift maturity (mid-period en güçlü)
        surprise_pts = min(last_surprise / 10.0, 1.0) * 0.35
        reaction_pts = min(earnings_reaction_pct / 5.0, 1.0) * 0.30

        # Drift faz: 5-30 gün sweet spot
        if days_since_earnings <= 30:
            drift_pts = 0.30
        elif days_since_earnings <= 45:
            drift_pts = 0.20
        else:
            drift_pts = 0.10

        # Trend filter bonus
        trend_pts = 0.05 if prices["close"].iloc[-1] > prices["close"].iloc[-5] else 0

        score = min(surprise_pts + reaction_pts + drift_pts + trend_pts, 1.0)

        if score < 0.5:
            return None

        return StrategySetup(
            strategy=self.name,
            setup_score=score,
            metadata={
                "earnings_surprise_pct": round(last_surprise, 1),
                "earnings_reaction_pct": round(earnings_reaction_pct, 2),
                "days_since_earnings": int(days_since_earnings),
                "in_drift_window": True,
            },
            rationale=(
                f"PEAD: EPS surprise +{last_surprise:.1f}%, day-of reaction "
                f"+{earnings_reaction_pct:.1f}%, {days_since_earnings}d into drift window."
            ),
        )


_assert_protocol: TradingStrategy = PostEarningsDriftStrategy()  # noqa: F841
