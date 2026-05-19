"""Confluence scoring — lib.zip'in 8-bileşenli puanlama Python port'u.

Toplam 100 puan üzerinden, multi-factor agreement skoru:
  weekly  20  (multi-timeframe alignment)
  adx     15  (trend strength)
  rsi     15  (momentum)
  macd    12  (momentum confirmation)
  vol     12  (volume confirmation)
  obv     10  (volume divergence)
  bb      8   (volatility position)
  fib     8   (price structure)
  ─────── ───
  TOTAL  100

LLM bu skoru "GUIDE for confidence" olarak alır:
  >= 75 → GUCLU_AL (conf 0.70-0.85)
  >= 55 → AL       (conf 0.50-0.69)
  >= 40 → IZLE     (conf 0.35-0.49)
  >= 25 → TUT      (conf 0.25-0.39)
  <  25 → SAT      (conf 0.15-0.30)

Bu cross-sectional ranking için de kullanılabilir (top decile filter).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ConfluenceComponents:
    """Skor breakdown'u — debug + LLM'e gerekçe için."""

    weekly: int = 0   # max 20
    adx: int = 0      # max 15
    rsi: int = 0      # max 15
    macd: int = 12    # max 12 (3 ile başlar default neutral)
    vol: int = 0      # max 12
    obv: int = 5      # max 10 (default neutral)
    bb: int = 3       # max 8 (default neutral)
    fib: int = 4      # max 8 (default neutral)

    def total(self) -> int:
        return max(0, self.weekly + self.adx + self.rsi + self.macd + self.vol + self.obv + self.bb + self.fib)

    def as_dict(self) -> dict[str, int]:
        return {
            "weekly": self.weekly,
            "adx": self.adx,
            "rsi": self.rsi,
            "macd": self.macd,
            "vol": self.vol,
            "obv": self.obv,
            "bb": self.bb,
            "fib": self.fib,
        }


def _score_weekly(timeframe_alignment: str | None) -> int:
    if timeframe_alignment == "ALIGNED":
        return 20
    if timeframe_alignment == "PARTIALLY_ALIGNED":
        return 10
    if timeframe_alignment == "CONFLICTING":
        return 0
    return 10  # unknown → neutral


def _score_adx(adx: float | None) -> int:
    if adx is None:
        return 0
    if adx >= 40:
        return 15
    if adx >= 30:
        return 12
    if adx >= 25:
        return 8
    if adx >= 20:
        return 4
    return 0


def _score_rsi(rsi: float | None) -> int:
    if rsi is None:
        return 5
    if rsi < 30:
        return 15      # oversold = bounce setup
    if rsi < 40:
        return 12
    if 50 < rsi < 70:
        return 10      # sweet spot
    if rsi >= 70:
        return 2       # overbought = warning
    return 5           # 40-50 transition


def _score_macd(macd_hist: float | None, prev_macd_hist: float | None) -> int:
    if macd_hist is None:
        return 4
    if macd_hist > 0:
        if prev_macd_hist is not None and prev_macd_hist <= 0:
            return 12   # GOLDEN_CROSS bugün
        return 8        # bullish
    return 2            # bearish


def _score_volume(vol_ratio: float | None) -> int:
    if vol_ratio is None:
        return 0
    if vol_ratio >= 2.0:
        return 12
    if vol_ratio >= 1.5:
        return 8
    if vol_ratio >= 0.8:
        return 4
    return 0


def _score_obv(
    obv_trend: str | None,
    obv_above_ma20: bool | None,
    obv_divergence_type: str | None,
) -> int:
    score = 5
    if obv_trend == "RISING":
        score = 8
        if obv_above_ma20 is True:
            score = 10
    if obv_divergence_type == "NEGATIVE":
        score = -5
    elif obv_divergence_type == "POSITIVE":
        score = max(score, 6)
    return score


def _score_bb(bb_percent_b: float | None, bb_squeeze: bool | None) -> int:
    if bb_percent_b is None:
        return 3
    if bb_squeeze:
        return 6
    if bb_percent_b < 0.05:
        return 7        # alt banda yakın → reversal şansı
    if 0.5 < bb_percent_b < 0.8:
        return 5
    if bb_percent_b > 0.95:
        return 2        # üst banda yapışmış
    return 3


def _score_fib(fib_zone: str | None) -> int:
    if fib_zone is None:
        return 4
    if "critical_support" in fib_zone or "healthy_pullback" in fib_zone:
        return 8
    if "strong_zone" in fib_zone:
        return 6
    if "danger_zone" in fib_zone:
        return 1
    if "trend_broken" in fib_zone:
        return 0
    return 4


def compute_confluence(
    indicators: dict[str, float | None],
    timeframe_alignment: str | None = None,
    obv_trend: str | None = None,
    obv_above_ma20: bool | None = None,
    obv_divergence_type: str | None = None,
    bb_squeeze: bool | None = None,
    fib_zone: str | None = None,
    prev_macd_hist: float | None = None,
) -> ConfluenceComponents:
    """8-bileşenli confluence skorunu hesaplar."""
    c = ConfluenceComponents(
        weekly=_score_weekly(timeframe_alignment),
        adx=_score_adx(indicators.get("adx_14")),
        rsi=_score_rsi(indicators.get("rsi_14")),
        macd=_score_macd(indicators.get("macd_hist"), prev_macd_hist),
        vol=_score_volume(indicators.get("vol_ratio")),
        obv=_score_obv(obv_trend, obv_above_ma20, obv_divergence_type),
        bb=_score_bb(indicators.get("bb_pct"), bb_squeeze),
        fib=_score_fib(fib_zone),
    )
    return c


def confluence_to_signal_suggestion(score: int) -> tuple[str, tuple[float, float]]:
    """Skoru sinyal etiketine + confidence aralığına çevir.

    LLM bu öneriyi GUIDE olarak alır, kesin kural değil.
    """
    if score >= 75:
        return "GUCLU_AL", (0.70, 0.85)
    if score >= 55:
        return "AL", (0.50, 0.69)
    if score >= 40:
        return "IZLE", (0.35, 0.49)
    if score >= 25:
        return "TUT", (0.25, 0.39)
    return "SAT", (0.15, 0.30)
