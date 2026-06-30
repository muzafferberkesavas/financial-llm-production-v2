"""56-Kriterli Master Scorecard — BIST orta vadeli swing trading.

Tek bir birlesik skor (0-200 puan, 10 kategori) ile tum mevcut teknik,
hacim, volatilite, fiyat yapisi ve temel verileri puanlar.

Temel metriklerde (F/K, PD/DD, FD/FAVOK, ROE, marj, borc, buyume)
capraz-kesit yuzdelik siralamasi kullanir — enflasyondan bagimsiz.

Sinyal eslemesi:
  >= 160 (%80+)  MUKEMMEL
  130-159         IYI
  100-129         ORTA
  70-99           ZAYIF
  < 70            KOTU
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from finllm.indicators.relative_score import _pct_ranks
from finllm.markets.base import FundamentalSnapshot
from finllm.pipeline.context import Candidate


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class CriterionResult:
    name: str
    category: str
    score: int
    max_score: int
    data_available: bool
    detail: str


@dataclass(slots=True)
class CategoryScore:
    name: str
    score: int
    max_score: int
    criteria: list[CriterionResult]


@dataclass(slots=True)
class MasterScore:
    total: int
    max_possible: int
    pct: float
    label: str
    categories: dict[str, CategoryScore]
    criteria: list[CriterionResult]

    def summary_line(self) -> str:
        """Compact one-liner for data_block."""
        cat_parts = " ".join(
            f"{k.lower()}={v.score}/{v.max_score}"
            for k, v in self.categories.items()
        )
        return f"{self.total}/{self.max_possible} ({self.pct:.0f}%) [{self.label}] | {cat_parts}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cr(name: str, category: str, score: int, max_score: int, detail: str,
        data_available: bool = True) -> CriterionResult:
    return CriterionResult(
        name=name, category=category,
        score=min(score, max_score), max_score=max_score,
        data_available=data_available, detail=detail,
    )


def _g(ind: dict, key: str):
    """Get indicator value, return None for missing/non-numeric."""
    v = ind.get(key)
    if v is None:
        return None
    if isinstance(v, str):
        return None
    return v


def _pct_from_52w_high(prices: pd.DataFrame) -> float | None:
    """Pct below 52-week high. 0.0 = at high, 0.30 = %30 below."""
    if prices is None or prices.empty or len(prices) < 50:
        return None
    high_col = prices["high"].tail(252)
    if high_col.empty:
        return None
    high_52w = float(high_col.max())
    if high_52w <= 0:
        return None
    close = float(prices["close"].iloc[-1])
    return (high_52w - close) / high_52w


def _label(pct: float) -> str:
    if pct >= 80:
        return "MUKEMMEL"
    if pct >= 65:
        return "IYI"
    if pct >= 50:
        return "ORTA"
    if pct >= 35:
        return "ZAYIF"
    return "KOTU"


# ---------------------------------------------------------------------------
# Percentile helper for fundamentals cross-section
# ---------------------------------------------------------------------------

def _compute_universe_percentiles(
    universe_fundamentals: dict[str, FundamentalSnapshot],
) -> dict[str, dict[str, float]]:
    """ticker -> {metric_name: percentile (0-1)} for fundamental metrics."""
    if not universe_fundamentals:
        return {}

    def _col(attr, transform=lambda x: x):
        return {
            t: (transform(getattr(s, attr)) if getattr(s, attr) is not None else None)
            for t, s in universe_fundamentals.items()
        }

    # lower-is-better metrics
    pe_pct = _pct_ranks(_col("pe_ratio", lambda v: v if v and v > 0 else None), higher_better=False)
    pb_pct = _pct_ranks(_col("pb_ratio", lambda v: v if v and v > 0 else None), higher_better=False)
    ev_ebitda_pct = _pct_ranks(_col("ev_to_ebitda", lambda v: v if v and v > 0 else None), higher_better=False)
    de_pct = _pct_ranks(_col("debt_to_equity"), higher_better=False)

    # higher-is-better metrics
    roe_pct = _pct_ranks(_col("roe"), higher_better=True)
    margin_pct = _pct_ranks(_col("profit_margin"), higher_better=True)
    rev_growth_pct = _pct_ranks(_col("revenue_growth_yoy"), higher_better=True)
    earn_growth_pct = _pct_ranks(_col("earnings_growth_yoy"), higher_better=True)

    out: dict[str, dict[str, float]] = {}
    for t in universe_fundamentals:
        out[t] = {
            "pe": pe_pct[t],
            "pb": pb_pct[t],
            "ev_ebitda": ev_ebitda_pct[t],
            "roe": roe_pct[t],
            "margin": margin_pct[t],
            "debt_equity": de_pct[t],
            "rev_growth": rev_growth_pct[t],
            "earn_growth": earn_growth_pct[t],
        }
    return out


def _quintile_score(pct: float, scores: tuple[int, int, int, int, int]) -> int:
    """Map percentile (0-1, 1=best) to quintile score."""
    if pct >= 0.8:
        return scores[0]  # top 20%
    if pct >= 0.6:
        return scores[1]
    if pct >= 0.4:
        return scores[2]
    if pct >= 0.2:
        return scores[3]
    return scores[4]  # bottom 20%


# ---------------------------------------------------------------------------
# 50 Criteria scoring functions
# ---------------------------------------------------------------------------

# ===== A. TREND (7 criteria, max 32) =====

def _c01_weekly_trend(ind: dict) -> CriterionResult:
    wt = ind.get("weekly_trend")
    if wt is None:
        return _cr("weekly_trend_direction", "TREND", 0, 6, "N/A", False)
    mapping = {"UPTREND": 6, "EARLY_RECOVERY": 4, "SIDEWAYS": 2, "EARLY_WEAKNESS": 0, "DOWNTREND": 0}
    s = mapping.get(wt, 0)
    return _cr("weekly_trend_direction", "TREND", s, 6, f"{wt} -> {s}/6")


def _c02_price_vs_sma200(ind: dict) -> CriterionResult:
    v = _g(ind, "price_vs_sma200")
    if v is None:
        return _cr("price_vs_sma200", "TREND", 0, 5, "N/A", False)
    if v > 0.10:
        s = 5
    elif v > 0.03:
        s = 4
    elif v > 0:
        s = 3
    elif v > -0.05:
        s = 1
    else:
        s = 0
    return _cr("price_vs_sma200", "TREND", s, 5, f"{v:+.3f} -> {s}/5")


def _c03_golden_cross(ind: dict) -> CriterionResult:
    v = _g(ind, "sma50_vs_sma200")
    if v is None:
        return _cr("sma50_vs_sma200", "TREND", 0, 4, "N/A", False)
    if v > 0.05:
        s = 4
    elif v > 0:
        s = 3
    elif v > -0.02:
        s = 2  # negative but narrowing
    else:
        s = 0
    return _cr("sma50_vs_sma200", "TREND", s, 4, f"{v:+.3f} -> {s}/4")


def _c04_adx(ind: dict) -> CriterionResult:
    v = _g(ind, "adx_14")
    if v is None:
        return _cr("adx_trend_strength", "TREND", 0, 5, "N/A", False)
    if v >= 35:
        s = 5
    elif v >= 25:
        s = 4
    elif v >= 20:
        s = 2
    else:
        s = 0
    return _cr("adx_trend_strength", "TREND", s, 5, f"{v:.1f} -> {s}/5")


def _c05_supertrend(ind: dict) -> CriterionResult:
    v = _g(ind, "supertrend_dir")
    if v is None:
        return _cr("supertrend_direction", "TREND", 0, 3, "N/A", False)
    s = 3 if v == 1 else 0
    return _cr("supertrend_direction", "TREND", s, 3, f"{v} -> {s}/3")


def _c06_ichimoku(ind: dict) -> CriterionResult:
    v = _g(ind, "ichi_signal")
    if v is None:
        return _cr("ichimoku_cloud", "TREND", 0, 5, "N/A", False)
    if v == 1:
        s = 5
    elif v == 0:
        s = 2
    else:
        s = 0
    return _cr("ichimoku_cloud", "TREND", s, 5, f"{v} -> {s}/5")


def _c07_aroon(ind: dict) -> CriterionResult:
    v = _g(ind, "aroon_osc")
    if v is None:
        return _cr("aroon_oscillator", "TREND", 0, 4, "N/A", False)
    if v > 60:
        s = 4
    elif v > 30:
        s = 3
    elif v > 0:
        s = 2
    elif v <= -30:
        s = 0
    else:
        s = 0
    return _cr("aroon_oscillator", "TREND", s, 4, f"{v:.0f} -> {s}/4")


# ===== B. MOMENTUM (7 criteria, max 30) =====

def _c08_rsi_sweet(ind: dict) -> CriterionResult:
    v = _g(ind, "rsi_14")
    if v is None:
        return _cr("rsi_sweet_spot", "MOMENTUM", 0, 5, "N/A", False)
    prev_rsi = _g(ind, "prev_rsi_14")
    rising = prev_rsi is not None and v > prev_rsi
    if 50 <= v <= 65:
        s = 5 if rising else 4
    elif 40 <= v < 50:
        s = 4 if rising else 3
    elif 65 < v <= 70:
        s = 3
    elif 30 <= v < 40:
        s = 4 if rising else 2  # oversold + rising = recovery
    elif v < 30:
        s = 3 if rising else 1  # deep oversold bounce
    else:  # > 70
        s = 0
    detail = f"{v:.1f} {'↑' if rising else '↓' if prev_rsi and not rising else '?'} -> {s}/5"
    return _cr("rsi_sweet_spot", "MOMENTUM", s, 5, detail)


def _c09_macd_hist(ind: dict) -> CriterionResult:
    hist = _g(ind, "macd_hist")
    if hist is None:
        return _cr("macd_histogram", "MOMENTUM", 0, 5, "N/A", False)
    prev_hist = _g(ind, "prev_macd_hist")
    if hist > 0:
        if prev_hist is not None and prev_hist <= 0:
            s = 5  # real golden cross (yesterday neg, today pos)
        elif prev_hist is not None and hist > prev_hist:
            s = 4  # bullish accelerating
        else:
            s = 3
    elif hist < 0:
        if prev_hist is not None and hist > prev_hist:
            s = 2  # bearish but converging
        else:
            s = 0
    else:
        s = 1
    cross_tag = ""
    if prev_hist is not None:
        cross_tag = f" prev={prev_hist:.3f}"
    return _cr("macd_histogram", "MOMENTUM", s, 5, f"hist={hist:.3f}{cross_tag} -> {s}/5")


def _c10_stochastic(ind: dict) -> CriterionResult:
    k = _g(ind, "stoch_k")
    d = _g(ind, "stoch_d")
    if k is None:
        return _cr("stochastic", "MOMENTUM", 0, 5, "N/A", False)
    if k is not None and d is not None:
        if k > d and 20 <= k <= 80:
            s = 4
        elif k < 20 and k > d:
            s = 5  # oversold golden cross
        elif k > 80:
            s = 1
        elif k < 20:
            s = 0
        else:
            s = 2
    else:
        s = 2
    return _cr("stochastic", "MOMENTUM", s, 5, f"K={k:.0f} D={d if d else '-'} -> {s}/5")


def _c11_roc(ind: dict) -> CriterionResult:
    v = _g(ind, "roc_10")
    if v is None:
        return _cr("roc_10", "MOMENTUM", 0, 4, "N/A", False)
    prev_roc = _g(ind, "prev_roc_10")
    accelerating = prev_roc is not None and v > prev_roc
    if 3 <= v <= 10:
        s = 4
    elif 1 <= v < 3:
        s = 4 if accelerating else 3  # positive + accelerating bonus
    elif 10 < v <= 15:
        s = 2
    elif v > 15:
        s = 1
    elif v < 0 and accelerating:
        s = 1  # negative but improving
    else:  # < 0
        s = 0
    accel_tag = " ↑accel" if accelerating else ""
    return _cr("roc_10", "MOMENTUM", s, 4, f"{v:.1f}%{accel_tag} -> {s}/4")


def _c12_williams_r(ind: dict) -> CriterionResult:
    v = _g(ind, "willr_14")
    if v is None:
        return _cr("williams_r", "MOMENTUM", 0, 4, "N/A", False)
    if -50 <= v <= -20:
        s = 4
    elif -80 <= v < -50:
        s = 3
    elif v > -20:
        s = 1
    elif v < -80:
        s = 2
    else:
        s = 0
    return _cr("williams_r", "MOMENTUM", s, 4, f"{v:.0f} -> {s}/4")


def _c13_weekly_rsi(ind: dict) -> CriterionResult:
    v = _g(ind, "weekly_rsi")
    if v is None:
        return _cr("weekly_rsi", "MOMENTUM", 0, 4, "N/A", False)
    if 50 <= v <= 70:
        s = 4
    elif 40 <= v < 50:
        s = 3
    elif v > 70:
        s = 1
    else:  # < 40
        s = 0
    return _cr("weekly_rsi", "MOMENTUM", s, 4, f"{v:.1f} -> {s}/4")


def _c14_cci(ind: dict) -> CriterionResult:
    v = _g(ind, "cci_20")
    if v is None:
        return _cr("cci_20", "MOMENTUM", 0, 3, "N/A", False)
    if 50 <= v <= 200:
        s = 3
    elif 0 <= v < 50:
        s = 2
    elif v > 200:
        s = 1
    else:  # < 0
        s = 0
    return _cr("cci_20", "MOMENTUM", s, 3, f"{v:.0f} -> {s}/3")


# ===== C. HACIM (6 criteria, max 28) =====

def _c15_vol_ratio(ind: dict) -> CriterionResult:
    v = _g(ind, "vol_ratio")
    if v is None:
        return _cr("volume_ratio", "HACIM", 0, 6, "N/A", False)
    if v >= 2.0:
        s = 6
    elif v >= 1.5:
        s = 5
    elif v >= 1.2:
        s = 3
    elif v >= 0.8:
        s = 1
    else:
        s = 0
    return _cr("volume_ratio", "HACIM", s, 6, f"{v:.2f}x -> {s}/6")


def _c16_obv_trend(ind: dict) -> CriterionResult:
    trend = ind.get("obv_trend")
    obv = _g(ind, "obv")
    obv_ma20 = _g(ind, "obv_ma20")
    obv_ema10 = _g(ind, "obv_ema10")
    obv_ema30 = _g(ind, "obv_ema30")
    if trend is None:
        return _cr("obv_trend", "HACIM", 0, 5, "N/A", False)
    # EMA-weighted trend: EMA(10) > EMA(30) = bullish accumulation
    ema_bullish = obv_ema10 is not None and obv_ema30 is not None and obv_ema10 > obv_ema30
    if trend == "RISING":
        if ema_bullish:
            s = 5  # strong: rising + EMA10 > EMA30
        elif obv is not None and obv_ma20 is not None and obv > obv_ma20:
            s = 4
        else:
            s = 3
    else:
        s = 1 if ema_bullish else 0  # falling but EMA structure still bullish
    ema_tag = " EMA10>30" if ema_bullish else ""
    return _cr("obv_trend", "HACIM", s, 5, f"{trend}{ema_tag} -> {s}/5")


def _c17_obv_divergence(ind: dict) -> CriterionResult:
    div_type = ind.get("obv_divergence_type")
    trend = ind.get("obv_trend")
    if div_type is None and trend is None:
        return _cr("obv_divergence", "HACIM", 2, 5, "N/A (neutral)", False)
    if div_type == "POSITIVE":
        s = 5
    elif div_type == "NEGATIVE":
        s = 0
    elif div_type is None or div_type == "NONE":
        s = 4 if trend == "RISING" else 2
    else:
        s = 2
    return _cr("obv_divergence", "HACIM", s, 5, f"div={div_type} trend={trend} -> {s}/5")


def _c18_mfi(ind: dict) -> CriterionResult:
    v = _g(ind, "mfi_14")
    if v is None:
        return _cr("money_flow_index", "HACIM", 0, 4, "N/A", False)
    if 40 <= v <= 70:
        s = 4
    elif 70 < v <= 80:
        s = 3
    elif 30 <= v < 40:
        s = 2
    elif v > 80:
        s = 0
    else:  # < 30
        s = 1
    return _cr("money_flow_index", "HACIM", s, 4, f"{v:.0f} -> {s}/4")


def _c19_cmf(ind: dict) -> CriterionResult:
    v = _g(ind, "cmf_20")
    if v is None:
        return _cr("chaikin_money_flow", "HACIM", 0, 4, "N/A", False)
    if v > 0.10:
        s = 4
    elif v > 0.05:
        s = 3
    elif v > 0:
        s = 2
    else:
        s = 0
    return _cr("chaikin_money_flow", "HACIM", s, 4, f"{v:.3f} -> {s}/4")


def _c20_dollar_volume(ind: dict, universe_dollar_vols: dict[str, float] | None,
                       ticker_symbol: str) -> CriterionResult:
    """Dollar volume percentile within universe."""
    close = _g(ind, "close")
    vol_sma = _g(ind, "vol_sma_20")
    if close is None or vol_sma is None:
        return _cr("daily_dollar_volume", "HACIM", 0, 4, "N/A", False)
    dv = close * vol_sma
    if universe_dollar_vols and len(universe_dollar_vols) > 1:
        pct = _pct_ranks(universe_dollar_vols, higher_better=True)
        p = pct.get(ticker_symbol, 0.5)
    else:
        p = 0.5
    s = _quintile_score(p, (4, 3, 2, 1, 0))
    return _cr("daily_dollar_volume", "HACIM", s, 4, f"dv={dv:.0f} pct={p:.2f} -> {s}/4")


# ===== D. VOLATILITE (4 criteria, max 16) =====

def _c21_bb_position(ind: dict) -> CriterionResult:
    v = _g(ind, "bb_pct")
    if v is None:
        return _cr("bb_position", "VOLATILITE", 0, 4, "N/A", False)
    if 0.3 <= v <= 0.7:
        s = 4
    elif 0.05 <= v < 0.3:
        s = 3
    elif 0.7 < v <= 0.9:
        s = 2
    elif v < 0.05:
        s = 2
    else:  # > 0.95
        s = 0
    return _cr("bb_position", "VOLATILITE", s, 4, f"%B={v:.2f} -> {s}/4")


def _c22_bb_squeeze(ind: dict) -> CriterionResult:
    sq = ind.get("bb_squeeze")
    wt = ind.get("bb_width_trend")
    if sq is None and wt is None:
        return _cr("bb_squeeze", "VOLATILITE", 0, 5, "N/A", False)
    if sq:
        s = 5
    elif wt == "NARROWING":
        s = 3
    elif wt == "WIDENING":
        s = 2
    elif wt == "STABLE":
        s = 1
    else:
        s = 1
    return _cr("bb_squeeze", "VOLATILITE", s, 5, f"squeeze={sq} trend={wt} -> {s}/5")


def _c23_vol_ratio_20_60(ind: dict) -> CriterionResult:
    v20 = _g(ind, "vol_20d")
    v60 = _g(ind, "vol_60d")
    if v20 is None or v60 is None or v60 == 0:
        return _cr("volatility_ratio", "VOLATILITE", 0, 4, "N/A", False)
    if v20 < v60 * 0.8:
        s = 4
    elif v20 < v60:
        s = 3
    elif v20 > v60 * 1.3:
        s = 1
    else:
        s = 2
    return _cr("volatility_ratio", "VOLATILITE", s, 4, f"20d={v20:.3f} 60d={v60:.3f} -> {s}/4")


def _c24_atr_pct(ind: dict) -> CriterionResult:
    v = _g(ind, "atr_pct")
    if v is None:
        return _cr("atr_percent", "VOLATILITE", 0, 3, "N/A", False)
    # atr_pct is typically stored as ratio (0.03 = 3%)
    pct = v * 100 if v < 1 else v
    if 2 <= pct <= 5:
        s = 3
    elif 1 <= pct < 2:
        s = 2
    elif 5 < pct <= 8:
        s = 2
    elif pct > 8:
        s = 0
    else:  # < 1
        s = 1
    return _cr("atr_percent", "VOLATILITE", s, 3, f"{pct:.1f}% -> {s}/3")


# ===== E. FIYAT YAPISI (5 criteria, max 22) =====

def _c25_fib_zone(ind: dict) -> CriterionResult:
    fz = ind.get("fib_zone")
    if fz is None:
        return _cr("fibonacci_zone", "FIYAT_YAPISI", 0, 5, "N/A", False)
    if "healthy_pullback" in str(fz):
        s = 5
    elif "strong_zone" in str(fz):
        s = 4
    elif "critical_support" in str(fz):
        s = 4
    elif "breakout" in str(fz).lower():
        s = 3
    elif "deep_pullback" in str(fz):
        s = 2
    elif "danger" in str(fz) or "broken" in str(fz):
        s = 0
    else:
        s = 2
    return _cr("fibonacci_zone", "FIYAT_YAPISI", s, 5, f"{fz} -> {s}/5")


def _c26_price_vs_vwap(ind: dict) -> CriterionResult:
    v = _g(ind, "price_vs_vwap")
    if v is None:
        return _cr("price_vs_vwap", "FIYAT_YAPISI", 0, 4, "N/A", False)
    if 0 < v < 0.05:
        s = 4
    elif v >= 0.05:
        s = 3
    elif -0.02 <= v <= 0:
        s = 2
    else:
        s = 0
    return _cr("price_vs_vwap", "FIYAT_YAPISI", s, 4, f"{v:+.3f} -> {s}/4")


def _c27_donchian(ind: dict) -> CriterionResult:
    v = _g(ind, "donch_pct")
    if v is None:
        return _cr("donchian_position", "FIYAT_YAPISI", 0, 5, "N/A", False)
    if 0.6 <= v <= 0.9:
        s = 5
    elif 0.4 <= v < 0.6:
        s = 3
    elif v > 0.95:
        s = 2
    elif v < 0.3:
        s = 0
    else:
        s = 2
    return _cr("donchian_position", "FIYAT_YAPISI", s, 5, f"{v:.2f} -> {s}/5")


def _c28_52w_high(prices: pd.DataFrame | None) -> CriterionResult:
    pct = _pct_from_52w_high(prices) if prices is not None else None
    if pct is None:
        return _cr("52w_high_proximity", "FIYAT_YAPISI", 0, 5, "N/A", False)
    pct100 = pct * 100
    if pct100 < 5:
        s = 5
    elif pct100 < 10:
        s = 4
    elif pct100 < 20:
        s = 3
    elif pct100 < 30:
        s = 1
    else:
        s = 0
    return _cr("52w_high_proximity", "FIYAT_YAPISI", s, 5, f"{pct100:.1f}% below -> {s}/5")


def _c29_swing_position(ind: dict) -> CriterionResult:
    sh = _g(ind, "swing_high_20")
    sl = _g(ind, "swing_low_20")
    close = _g(ind, "close")
    if sh is None or sl is None or close is None or sh <= sl:
        return _cr("swing_position", "FIYAT_YAPISI", 0, 3, "N/A", False)
    if close > sh:
        s = 3  # breakout
    elif close > sh * 0.98:
        s = 2  # near high
    elif close > (sh + sl) / 2:
        s = 1  # mid range
    else:
        s = 0  # near low
    return _cr("swing_position", "FIYAT_YAPISI", s, 3, f"close={close:.1f} sh={sh:.1f} sl={sl:.1f} -> {s}/3")


# ===== F. TEMEL - DEGER (5 criteria, max 18) =====

def _c30_pe(snap: FundamentalSnapshot | None, pctiles: dict[str, float] | None) -> CriterionResult:
    if snap is None or snap.pe_ratio is None or snap.pe_ratio <= 0:
        return _cr("pe_ratio_relative", "DEGER", 0, 4, "N/A", False)
    if pctiles:
        s = _quintile_score(pctiles.get("pe", 0.5), (4, 3, 2, 1, 0))
        return _cr("pe_ratio_relative", "DEGER", s, 4, f"PE={snap.pe_ratio:.1f} pct={pctiles.get('pe', 0.5):.2f} -> {s}/4")
    # fallback absolute
    if snap.pe_ratio < 8:
        s = 4
    elif snap.pe_ratio < 15:
        s = 3
    elif snap.pe_ratio < 25:
        s = 2
    else:
        s = 0
    return _cr("pe_ratio_relative", "DEGER", s, 4, f"PE={snap.pe_ratio:.1f} (abs) -> {s}/4")


def _c31_pb(snap: FundamentalSnapshot | None, pctiles: dict[str, float] | None) -> CriterionResult:
    if snap is None or snap.pb_ratio is None or snap.pb_ratio <= 0:
        return _cr("pb_ratio_relative", "DEGER", 0, 3, "N/A", False)
    if pctiles:
        s = _quintile_score(pctiles.get("pb", 0.5), (3, 2, 1, 0, 0))
        return _cr("pb_ratio_relative", "DEGER", s, 3, f"PB={snap.pb_ratio:.1f} pct={pctiles.get('pb', 0.5):.2f} -> {s}/3")
    if snap.pb_ratio < 1.5:
        s = 3
    elif snap.pb_ratio < 3:
        s = 2
    else:
        s = 0
    return _cr("pb_ratio_relative", "DEGER", s, 3, f"PB={snap.pb_ratio:.1f} (abs) -> {s}/3")


def _c32_ev_ebitda(snap: FundamentalSnapshot | None, pctiles: dict[str, float] | None) -> CriterionResult:
    if snap is None or snap.ev_to_ebitda is None or snap.ev_to_ebitda <= 0:
        return _cr("ev_ebitda_relative", "DEGER", 0, 4, "N/A", False)
    if pctiles:
        s = _quintile_score(pctiles.get("ev_ebitda", 0.5), (4, 3, 2, 1, 0))
        return _cr("ev_ebitda_relative", "DEGER", s, 4, f"EV/EBITDA={snap.ev_to_ebitda:.1f} pct={pctiles.get('ev_ebitda', 0.5):.2f} -> {s}/4")
    if snap.ev_to_ebitda < 6:
        s = 4
    elif snap.ev_to_ebitda < 10:
        s = 3
    elif snap.ev_to_ebitda < 15:
        s = 2
    else:
        s = 0
    return _cr("ev_ebitda_relative", "DEGER", s, 4, f"EV/EBITDA={snap.ev_to_ebitda:.1f} (abs) -> {s}/4")


def _c33_forward_vs_trailing(snap: FundamentalSnapshot | None) -> CriterionResult:
    if snap is None or snap.forward_pe is None or snap.pe_ratio is None or snap.pe_ratio <= 0:
        return _cr("forward_pe_vs_trailing", "DEGER", 0, 4, "N/A", False)
    ratio = snap.forward_pe / snap.pe_ratio
    if ratio < 0.85:
        s = 4
    elif ratio < 1.0:
        s = 3
    elif ratio == 1.0:
        s = 1
    else:
        s = 0
    return _cr("forward_pe_vs_trailing", "DEGER", s, 4, f"fwd/trail={ratio:.2f} -> {s}/4")


def _c34_peg(snap: FundamentalSnapshot | None) -> CriterionResult:
    if snap is None or snap.peg_ratio is None or snap.peg_ratio <= 0:
        return _cr("peg_ratio", "DEGER", 0, 3, "N/A", False)
    if snap.peg_ratio < 1.0:
        s = 3
    elif snap.peg_ratio < 1.5:
        s = 2
    elif snap.peg_ratio < 2.0:
        s = 1
    else:
        s = 0
    return _cr("peg_ratio", "DEGER", s, 3, f"PEG={snap.peg_ratio:.2f} -> {s}/3")


# ===== G. TEMEL - KALITE (5 criteria, max 18) =====

def _c35_roe(snap: FundamentalSnapshot | None, pctiles: dict[str, float] | None) -> CriterionResult:
    if snap is None or snap.roe is None:
        return _cr("roe_relative", "KALITE", 0, 4, "N/A", False)
    if pctiles:
        s = _quintile_score(pctiles.get("roe", 0.5), (4, 3, 2, 1, 0))
        return _cr("roe_relative", "KALITE", s, 4, f"ROE={snap.roe:.2%} pct={pctiles.get('roe', 0.5):.2f} -> {s}/4")
    if snap.roe > 0.25:
        s = 4
    elif snap.roe > 0.15:
        s = 3
    elif snap.roe > 0.05:
        s = 2
    elif snap.roe > 0:
        s = 1
    else:
        s = 0
    return _cr("roe_relative", "KALITE", s, 4, f"ROE={snap.roe:.2%} (abs) -> {s}/4")


def _c36_margin(snap: FundamentalSnapshot | None, pctiles: dict[str, float] | None) -> CriterionResult:
    if snap is None or snap.profit_margin is None:
        return _cr("profit_margin_relative", "KALITE", 0, 4, "N/A", False)
    if pctiles:
        s = _quintile_score(pctiles.get("margin", 0.5), (4, 3, 2, 1, 0))
        return _cr("profit_margin_relative", "KALITE", s, 4, f"margin={snap.profit_margin:.2%} pct={pctiles.get('margin', 0.5):.2f} -> {s}/4")
    if snap.profit_margin > 0.20:
        s = 4
    elif snap.profit_margin > 0.10:
        s = 3
    elif snap.profit_margin > 0.05:
        s = 2
    elif snap.profit_margin > 0:
        s = 1
    else:
        s = 0
    return _cr("profit_margin_relative", "KALITE", s, 4, f"margin={snap.profit_margin:.2%} (abs) -> {s}/4")


def _c37_debt_equity(snap: FundamentalSnapshot | None, pctiles: dict[str, float] | None) -> CriterionResult:
    if snap is None or snap.debt_to_equity is None:
        return _cr("debt_equity_safety", "KALITE", 0, 4, "N/A", False)
    if pctiles:
        s = _quintile_score(pctiles.get("debt_equity", 0.5), (4, 3, 2, 1, 0))
        return _cr("debt_equity_safety", "KALITE", s, 4, f"D/E={snap.debt_to_equity:.1f} pct={pctiles.get('debt_equity', 0.5):.2f} -> {s}/4")
    de = snap.debt_to_equity / 100 if snap.debt_to_equity > 5 else snap.debt_to_equity
    if de < 0.3:
        s = 4
    elif de < 0.7:
        s = 3
    elif de < 1.5:
        s = 2
    elif de < 2.5:
        s = 1
    else:
        s = 0
    return _cr("debt_equity_safety", "KALITE", s, 4, f"D/E={snap.debt_to_equity:.1f} (abs) -> {s}/4")


def _c38_current_ratio(snap: FundamentalSnapshot | None) -> CriterionResult:
    if snap is None or snap.current_ratio is None:
        return _cr("current_ratio", "KALITE", 0, 3, "N/A", False)
    if snap.current_ratio > 2.0:
        s = 3
    elif snap.current_ratio > 1.5:
        s = 2
    elif snap.current_ratio > 1.0:
        s = 1
    else:
        s = 0
    return _cr("current_ratio", "KALITE", s, 3, f"{snap.current_ratio:.2f} -> {s}/3")


def _c39_fcf(snap: FundamentalSnapshot | None) -> CriterionResult:
    if snap is None or snap.free_cash_flow is None:
        return _cr("free_cash_flow", "KALITE", 0, 3, "N/A", False)
    s = 3 if snap.free_cash_flow > 0 else 0
    return _cr("free_cash_flow", "KALITE", s, 3, f"{'positive' if snap.free_cash_flow > 0 else 'negative'} -> {s}/3")


# ===== H. TEMEL - BUYUME (4 criteria, max 14) =====

def _c40_rev_growth(snap: FundamentalSnapshot | None, pctiles: dict[str, float] | None) -> CriterionResult:
    if snap is None or snap.revenue_growth_yoy is None:
        return _cr("revenue_growth_relative", "BUYUME", 0, 4, "N/A", False)
    if pctiles:
        s = _quintile_score(pctiles.get("rev_growth", 0.5), (4, 3, 2, 1, 0))
        return _cr("revenue_growth_relative", "BUYUME", s, 4, f"rev_g={snap.revenue_growth_yoy:.2%} pct={pctiles.get('rev_growth', 0.5):.2f} -> {s}/4")
    if snap.revenue_growth_yoy > 0.30:
        s = 4
    elif snap.revenue_growth_yoy > 0.15:
        s = 3
    elif snap.revenue_growth_yoy > 0.05:
        s = 2
    elif snap.revenue_growth_yoy > 0:
        s = 1
    else:
        s = 0
    return _cr("revenue_growth_relative", "BUYUME", s, 4, f"rev_g={snap.revenue_growth_yoy:.2%} (abs) -> {s}/4")


def _c41_earn_growth(snap: FundamentalSnapshot | None, pctiles: dict[str, float] | None) -> CriterionResult:
    if snap is None or snap.earnings_growth_yoy is None:
        return _cr("earnings_growth_relative", "BUYUME", 0, 4, "N/A", False)
    if pctiles:
        s = _quintile_score(pctiles.get("earn_growth", 0.5), (4, 3, 2, 1, 0))
        return _cr("earnings_growth_relative", "BUYUME", s, 4, f"earn_g={snap.earnings_growth_yoy:.2%} pct={pctiles.get('earn_growth', 0.5):.2f} -> {s}/4")
    if snap.earnings_growth_yoy > 0.30:
        s = 4
    elif snap.earnings_growth_yoy > 0.15:
        s = 3
    elif snap.earnings_growth_yoy > 0.05:
        s = 2
    elif snap.earnings_growth_yoy > 0:
        s = 1
    else:
        s = 0
    return _cr("earnings_growth_relative", "BUYUME", s, 4, f"earn_g={snap.earnings_growth_yoy:.2%} (abs) -> {s}/4")


def _c42_rev_acceleration(snap: FundamentalSnapshot | None) -> CriterionResult:
    if snap is None or snap.revenue_growth_quarterly is None or snap.revenue_growth_yoy is None:
        return _cr("revenue_acceleration", "BUYUME", 0, 3, "N/A", False)
    if snap.revenue_growth_quarterly > snap.revenue_growth_yoy:
        s = 3
    elif abs(snap.revenue_growth_quarterly - snap.revenue_growth_yoy) < 0.02:
        s = 2
    else:
        s = 0
    return _cr("revenue_acceleration", "BUYUME", s, 3,
               f"q={snap.revenue_growth_quarterly:.2%} y={snap.revenue_growth_yoy:.2%} -> {s}/3")


def _c43_earnings_surprise(snap: FundamentalSnapshot | None) -> CriterionResult:
    if snap is None or snap.last_earnings_surprise_pct is None:
        return _cr("earnings_surprise", "BUYUME", 0, 3, "N/A", False)
    pct = snap.last_earnings_surprise_pct
    if pct > 5:
        s = 3
    elif pct > 2:
        s = 2
    elif pct > 0:
        s = 1
    else:
        s = 0
    return _cr("earnings_surprise", "BUYUME", s, 3, f"{pct:+.1f}% -> {s}/3")


# ===== I. RISK YONETIMI (4 criteria, max 12) =====

def _c44_risk_reward(ind: dict) -> CriterionResult:
    sh = _g(ind, "swing_high_20")
    sl = _g(ind, "swing_low_20")
    close = _g(ind, "close")
    if sh is None or sl is None or close is None:
        return _cr("risk_reward_ratio", "RISK", 0, 4, "N/A", False)
    upside = sh - close
    downside = close - sl
    if downside <= 0:
        s = 4  # at or below swing low — strong support
        rr = 99
    else:
        rr = upside / downside
        if rr > 3:
            s = 4
        elif rr > 2:
            s = 3
        elif rr > 1.5:
            s = 2
        elif rr > 1:
            s = 1
        else:
            s = 0
    return _cr("risk_reward_ratio", "RISK", s, 4, f"R:R={rr:.1f} -> {s}/4")


def _c45_earnings_proximity(snap: FundamentalSnapshot | None) -> CriterionResult:
    if snap is None or snap.days_to_earnings is None:
        return _cr("earnings_proximity", "RISK", 2, 3, "N/A (neutral)", False)
    dte = snap.days_to_earnings
    if dte > 30:
        s = 3
    elif dte > 15:
        s = 2
    elif dte > 5:
        s = 1
    else:
        s = 0
    return _cr("earnings_proximity", "RISK", s, 3, f"{dte}d -> {s}/3")


def _c46_vol_fitness(ind: dict) -> CriterionResult:
    vol20 = _g(ind, "vol_20d")
    atr_pct = _g(ind, "atr_pct")
    if vol20 is None or atr_pct is None:
        return _cr("volatility_fitness", "RISK", 0, 3, "N/A", False)
    atr_p = atr_pct * 100 if atr_pct < 1 else atr_pct
    if 0.15 <= vol20 <= 0.40 and 1.5 <= atr_p <= 5:
        s = 3
    elif 0.10 <= vol20 <= 0.50 and 1 <= atr_p <= 7:
        s = 2
    else:
        s = 0
    return _cr("volatility_fitness", "RISK", s, 3, f"vol20={vol20:.3f} atr={atr_p:.1f}% -> {s}/3")


def _c47_neg_div_penalty(ind: dict) -> CriterionResult:
    div_type = ind.get("obv_divergence_type")
    if div_type == "NEGATIVE":
        s = 0
    else:
        s = 2
    return _cr("negative_divergence_penalty", "RISK", s, 2, f"div={div_type} -> {s}/2")


# ===== J. COKLU ZAMAN DILIMI (3 criteria, max 12) =====

def _c48_tf_alignment(ind: dict) -> CriterionResult:
    v = ind.get("timeframe_alignment")
    if v is None:
        return _cr("timeframe_alignment", "COKLU_ZAMAN", 1, 5, "UNKNOWN -> 1/5", False)
    mapping = {"ALIGNED": 5, "PARTIALLY_ALIGNED": 2, "CONFLICTING": 0, "UNKNOWN": 1}
    s = mapping.get(v, 1)
    return _cr("timeframe_alignment", "COKLU_ZAMAN", s, 5, f"{v} -> {s}/5")


def _c49_ema_order(ind: dict) -> CriterionResult:
    ema12 = _g(ind, "ema_12")
    ema26 = _g(ind, "ema_26")
    sma50 = _g(ind, "sma_50")
    sma200 = _g(ind, "sma_200")
    vals = [ema12, ema26, sma50, sma200]
    if any(v is None for v in vals):
        return _cr("ema_order", "COKLU_ZAMAN", 0, 4, "N/A", False)
    # Count how many are in perfect descending order
    in_order = 0
    if ema12 > ema26:
        in_order += 1
    if ema26 > sma50:
        in_order += 1
    if sma50 > sma200:
        in_order += 1
    if in_order == 3:
        s = 4
    elif in_order == 2:
        s = 3
    elif in_order == 1:
        s = 2
    else:
        s = 0
    return _cr("ema_order", "COKLU_ZAMAN", s, 4, f"{in_order}/3 in order -> {s}/4")


def _c50_di_spread(ind: dict) -> CriterionResult:
    di_p = _g(ind, "di_plus")
    di_m = _g(ind, "di_minus")
    if di_p is None or di_m is None:
        return _cr("di_spread", "COKLU_ZAMAN", 0, 3, "N/A", False)
    diff = di_p - di_m
    if diff > 15:
        s = 3
    elif diff > 5:
        s = 2
    elif diff > 0:
        s = 1
    else:
        s = 0
    return _cr("di_spread", "COKLU_ZAMAN", s, 3, f"DI+={di_p:.0f} DI-={di_m:.0f} diff={diff:.0f} -> {s}/3")


# ===== K. YENI KRITERLER (6 criteria, max 23) =====

def _c51_green_day(ind: dict) -> CriterionResult:
    close = _g(ind, "close")
    prev_close = _g(ind, "prev_close")
    if close is None or prev_close is None or prev_close == 0:
        return _cr("green_day", "MOMENTUM", 0, 3, "N/A", False)
    chg_pct = (close - prev_close) / prev_close * 100
    if chg_pct > 2.0:
        s = 3
    elif chg_pct > 0.5:
        s = 2
    elif chg_pct > 0:
        s = 1
    else:
        s = 0
    return _cr("green_day", "MOMENTUM", s, 3, f"chg={chg_pct:+.2f}% -> {s}/3")


def _c52_close_vs_ema21(ind: dict) -> CriterionResult:
    close = _g(ind, "close")
    ema21 = _g(ind, "ema21")
    if close is None or ema21 is None or ema21 == 0:
        return _cr("close_vs_ema21", "TREND", 0, 4, "N/A", False)
    pct = (close - ema21) / ema21 * 100
    if pct > 3.0:
        s = 4
    elif pct > 1.0:
        s = 3
    elif pct > 0:
        s = 2
    elif pct > -2.0:
        s = 1
    else:
        s = 0
    return _cr("close_vs_ema21", "TREND", s, 4, f"{pct:+.2f}% -> {s}/4")


def _c53_close_vs_ema50(ind: dict) -> CriterionResult:
    close = _g(ind, "close")
    ema50 = _g(ind, "ema50")
    if close is None or ema50 is None or ema50 == 0:
        return _cr("close_vs_ema50", "TREND", 0, 4, "N/A", False)
    pct = (close - ema50) / ema50 * 100
    if pct > 5.0:
        s = 4
    elif pct > 2.0:
        s = 3
    elif pct > 0:
        s = 2
    elif pct > -3.0:
        s = 1
    else:
        s = 0
    return _cr("close_vs_ema50", "TREND", s, 4, f"{pct:+.2f}% -> {s}/4")


def _c54_adr_fitness(ind: dict) -> CriterionResult:
    adr = _g(ind, "adr_pct")
    if adr is None:
        return _cr("adr_fitness", "VOLATILITE", 0, 3, "N/A", False)
    if 2.5 <= adr <= 6.0:
        s = 3  # ideal swing range
    elif 2.0 <= adr < 2.5:
        s = 2
    elif 6.0 < adr <= 8.0:
        s = 2
    elif 1.5 <= adr < 2.0:
        s = 1
    else:
        s = 0
    return _cr("adr_fitness", "VOLATILITE", s, 3, f"{adr:.2f}% -> {s}/3")


def _c55_setup_pattern(cand) -> CriterionResult:
    setup = getattr(cand, "setup_type", "none")
    conf = getattr(cand, "setup_confidence", 0.0)
    if setup == "none" or conf <= 0:
        return _cr("setup_pattern", "FIYAT_YAPISI", 0, 5, "none", True)
    if conf >= 0.7:
        s = 5
    elif conf >= 0.5:
        s = 4
    elif conf >= 0.3:
        s = 3
    else:
        s = 1
    return _cr("setup_pattern", "FIYAT_YAPISI", s, 5, f"{setup}({conf:.2f}) -> {s}/5")


def _c56_candlestick_signal(ind: dict) -> CriterionResult:
    engulf = _g(ind, "pattern_bull_engulf")
    hammer = _g(ind, "pattern_hammer")
    vol_ratio = _g(ind, "vol_ratio")
    has_pattern = (engulf is not None and engulf > 0) or (hammer is not None and hammer > 0)
    if not has_pattern:
        return _cr("candlestick_signal", "FIYAT_YAPISI", 0, 4, "no pattern")
    high_vol = vol_ratio is not None and vol_ratio >= 1.2
    if has_pattern and high_vol:
        s = 4
    elif has_pattern:
        s = 2
    else:
        s = 0
    parts = []
    if engulf and engulf > 0:
        parts.append("engulf")
    if hammer and hammer > 0:
        parts.append("hammer")
    vol_tag = f" vol={vol_ratio:.1f}x" if vol_ratio else ""
    return _cr("candlestick_signal", "FIYAT_YAPISI", s, 4, f"{'+'.join(parts)}{vol_tag} -> {s}/4")


# ---------------------------------------------------------------------------
# Main compute function
# ---------------------------------------------------------------------------

CATEGORY_ORDER = [
    "TREND", "MOMENTUM", "HACIM", "VOLATILITE", "FIYAT_YAPISI",
    "DEGER", "KALITE", "BUYUME", "RISK", "COKLU_ZAMAN",
]


def compute_master_score(
    cand: Candidate,
    universe_fundamentals: dict[str, FundamentalSnapshot] | None = None,
    universe_dollar_volumes: dict[str, float] | None = None,
) -> MasterScore:
    """50-kriterli master scorecard hesapla.

    Args:
        cand: Stage 1C sonrasi Candidate (indicators dolu)
        universe_fundamentals: tum aktif adaylarin fundamentals'i (cross-section icin)
        universe_dollar_volumes: ticker -> close*vol_sma_20 (cross-section icin)
    """
    ind = cand.indicators
    snap = cand.ingested.fundamentals
    prices = cand.ingested.prices

    # Compute universe percentiles for this ticker
    pctiles: dict[str, float] | None = None
    if universe_fundamentals and cand.ticker.symbol in universe_fundamentals:
        all_pctiles = _compute_universe_percentiles(universe_fundamentals)
        pctiles = all_pctiles.get(cand.ticker.symbol)

    # Add close to indicators if not present (needed by several criteria)
    if "close" not in ind and prices is not None and not prices.empty:
        ind["close"] = float(prices["close"].iloc[-1])

    # Compute all 50 criteria
    all_criteria: list[CriterionResult] = [
        # A. TREND
        _c01_weekly_trend(ind),
        _c02_price_vs_sma200(ind),
        _c03_golden_cross(ind),
        _c04_adx(ind),
        _c05_supertrend(ind),
        _c06_ichimoku(ind),
        _c07_aroon(ind),
        # B. MOMENTUM
        _c08_rsi_sweet(ind),
        _c09_macd_hist(ind),
        _c10_stochastic(ind),
        _c11_roc(ind),
        _c12_williams_r(ind),
        _c13_weekly_rsi(ind),
        _c14_cci(ind),
        # C. HACIM
        _c15_vol_ratio(ind),
        _c16_obv_trend(ind),
        _c17_obv_divergence(ind),
        _c18_mfi(ind),
        _c19_cmf(ind),
        _c20_dollar_volume(ind, universe_dollar_volumes, cand.ticker.symbol),
        # D. VOLATILITE
        _c21_bb_position(ind),
        _c22_bb_squeeze(ind),
        _c23_vol_ratio_20_60(ind),
        _c24_atr_pct(ind),
        # E. FIYAT YAPISI
        _c25_fib_zone(ind),
        _c26_price_vs_vwap(ind),
        _c27_donchian(ind),
        _c28_52w_high(prices),
        _c29_swing_position(ind),
        # F. DEGER
        _c30_pe(snap, pctiles),
        _c31_pb(snap, pctiles),
        _c32_ev_ebitda(snap, pctiles),
        _c33_forward_vs_trailing(snap),
        _c34_peg(snap),
        # G. KALITE
        _c35_roe(snap, pctiles),
        _c36_margin(snap, pctiles),
        _c37_debt_equity(snap, pctiles),
        _c38_current_ratio(snap),
        _c39_fcf(snap),
        # H. BUYUME
        _c40_rev_growth(snap, pctiles),
        _c41_earn_growth(snap, pctiles),
        _c42_rev_acceleration(snap),
        _c43_earnings_surprise(snap),
        # I. RISK
        _c44_risk_reward(ind),
        _c45_earnings_proximity(snap),
        _c46_vol_fitness(ind),
        _c47_neg_div_penalty(ind),
        # J. COKLU ZAMAN
        _c48_tf_alignment(ind),
        _c49_ema_order(ind),
        _c50_di_spread(ind),
        # K. YENI KRITERLER (trend/momentum/volatilite/fiyat yapisi'na dagitilmis)
        _c51_green_day(ind),
        _c52_close_vs_ema21(ind),
        _c53_close_vs_ema50(ind),
        _c54_adr_fitness(ind),
        _c55_setup_pattern(cand),
        _c56_candlestick_signal(ind),
    ]

    # Group by category
    cat_map: dict[str, list[CriterionResult]] = {cat: [] for cat in CATEGORY_ORDER}
    for cr in all_criteria:
        cat_map[cr.category].append(cr)

    categories: dict[str, CategoryScore] = {}
    total = 0
    max_possible = 0
    for cat_name in CATEGORY_ORDER:
        criteria = cat_map[cat_name]
        cat_score = sum(c.score for c in criteria)
        cat_max = sum(c.max_score for c in criteria)
        categories[cat_name] = CategoryScore(
            name=cat_name, score=cat_score, max_score=cat_max, criteria=criteria,
        )
        total += cat_score
        max_possible += cat_max

    pct = (total / max_possible * 100) if max_possible > 0 else 0.0

    return MasterScore(
        total=total,
        max_possible=max_possible,
        pct=pct,
        label=_label(pct),
        categories=categories,
        criteria=all_criteria,
    )


__all__ = [
    "CriterionResult",
    "CategoryScore",
    "MasterScore",
    "compute_master_score",
]
