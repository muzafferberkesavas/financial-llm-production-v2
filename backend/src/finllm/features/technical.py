"""Teknik gösterge feature engineering — genişletilmiş set (~50 gösterge)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pandas_ta as ta


def add_technical_features(df: pd.DataFrame) -> pd.DataFrame:
    """OHLCV DataFrame'ine ~50 teknik gösterge ekler.

    Beklenen sütunlar (lowercase): open, high, low, close, volume.
    """
    out = df.copy()
    o, h, l, c, v = out["open"], out["high"], out["low"], out["close"], out["volume"]

    # === Returns & volatility ===
    out["ret_1d"] = c.pct_change()
    out["ret_5d"] = c.pct_change(5)
    out["ret_20d"] = c.pct_change(20)
    out["log_ret"] = np.log(c / c.shift(1))
    out["vol_20d"] = out["log_ret"].rolling(20).std() * np.sqrt(252)
    out["vol_60d"] = out["log_ret"].rolling(60).std() * np.sqrt(252)

    # === Trend / MA ===
    out["sma_10"] = ta.sma(c, length=10)
    out["sma_20"] = ta.sma(c, length=20)
    out["sma_50"] = ta.sma(c, length=50)
    out["sma_200"] = ta.sma(c, length=200)
    out["ema_12"] = ta.ema(c, length=12)
    out["ema_26"] = ta.ema(c, length=26)
    out["price_vs_sma20"] = c / out["sma_20"] - 1
    out["price_vs_sma50"] = c / out["sma_50"] - 1
    out["price_vs_sma200"] = c / out["sma_200"] - 1
    out["sma50_vs_sma200"] = out["sma_50"] / out["sma_200"] - 1   # golden/death cross

    # === Momentum (klasik) ===
    out["rsi_14"] = ta.rsi(c, length=14)
    out["rsi_7"] = ta.rsi(c, length=7)
    out["mom_10"] = ta.mom(c, length=10)
    macd = ta.macd(c, fast=12, slow=26, signal=9)
    if macd is not None and not macd.empty:
        out["macd"] = macd.iloc[:, 0]
        out["macd_signal"] = macd.iloc[:, 1]
        out["macd_hist"] = macd.iloc[:, 2]
    stoch = ta.stoch(h, l, c)
    if stoch is not None and not stoch.empty:
        out["stoch_k"] = stoch.iloc[:, 0]
        out["stoch_d"] = stoch.iloc[:, 1]

    # === Momentum (ek) ===
    out["cci_20"] = ta.cci(h, l, c, length=20)        # Commodity Channel Index
    out["willr_14"] = ta.willr(h, l, c, length=14)    # Williams %R
    out["roc_10"] = ta.roc(c, length=10)              # Rate of Change

    # === Volatilite ===
    bb = ta.bbands(c, length=20)
    if bb is not None and not bb.empty:
        out["bb_lower"] = bb.iloc[:, 0]
        out["bb_mid"] = bb.iloc[:, 1]
        out["bb_upper"] = bb.iloc[:, 2]
        out["bb_pct"] = (c - bb.iloc[:, 0]) / (bb.iloc[:, 2] - bb.iloc[:, 0])
        out["bb_width"] = (bb.iloc[:, 2] - bb.iloc[:, 0]) / bb.iloc[:, 1]
    atr = ta.atr(h, l, c, length=14)
    if atr is not None:
        out["atr_14"] = atr
        out["atr_pct"] = atr / c
    donch = ta.donchian(h, l, lower_length=20, upper_length=20)
    if donch is not None and not donch.empty:
        out["donch_lower"] = donch.iloc[:, 0]
        out["donch_upper"] = donch.iloc[:, 2]
        out["donch_pct"] = (c - donch.iloc[:, 0]) / (donch.iloc[:, 2] - donch.iloc[:, 0])

    # === Volume ===
    out["vol_sma_20"] = v.rolling(20).mean()
    out["vol_ratio"] = v / out["vol_sma_20"]
    out["obv"] = ta.obv(c, v)
    out["mfi_14"] = ta.mfi(h, l, c, v, length=14)     # Money Flow Index (RSI ama volüm-ağırlıklı)
    cmf = ta.cmf(h, l, c, v, length=20)
    if cmf is not None:
        out["cmf_20"] = cmf                            # Chaikin Money Flow
    # Yaklaşık günlük VWAP — gerçek VWAP intraday gerektirir
    typical = (h + l + c) / 3
    out["vwap_20"] = (typical * v).rolling(20).sum() / v.rolling(20).sum()
    out["price_vs_vwap"] = c / out["vwap_20"] - 1

    # === Trend gücü ===
    adx = ta.adx(h, l, c, length=14)
    if adx is not None and not adx.empty:
        out["adx_14"] = adx.iloc[:, 0]
        out["di_plus"] = adx.iloc[:, 1]
        out["di_minus"] = adx.iloc[:, 2]
    aroon = ta.aroon(h, l, length=25)
    if aroon is not None and not aroon.empty:
        out["aroon_down"] = aroon.iloc[:, 0]
        out["aroon_up"] = aroon.iloc[:, 1]
        out["aroon_osc"] = aroon.iloc[:, 2]

    # === Ichimoku (swing trading için altın standart) ===
    try:
        ich, _ = ta.ichimoku(h, l, c)
        if ich is not None and not ich.empty:
            out["ichi_tenkan"] = ich.iloc[:, 0]           # 9-period conversion
            out["ichi_kijun"] = ich.iloc[:, 1]            # 26-period base
            out["ichi_senkou_a"] = ich.iloc[:, 2]         # cloud üst
            out["ichi_senkou_b"] = ich.iloc[:, 3]         # cloud alt
            # Fiyat bulutun üstünde mi? (1 = bullish, -1 = bearish, 0 = içinde)
            cloud_top = pd.concat([out["ichi_senkou_a"], out["ichi_senkou_b"]], axis=1).max(axis=1)
            cloud_bot = pd.concat([out["ichi_senkou_a"], out["ichi_senkou_b"]], axis=1).min(axis=1)
            out["ichi_signal"] = np.where(c > cloud_top, 1, np.where(c < cloud_bot, -1, 0))
    except Exception:
        pass

    # === SuperTrend (swing için popüler trend filtresi) ===
    try:
        st = ta.supertrend(h, l, c, length=10, multiplier=3.0)
        if st is not None and not st.empty:
            out["supertrend"] = st.iloc[:, 0]
            out["supertrend_dir"] = st.iloc[:, 1]      # 1 = uptrend, -1 = downtrend
    except Exception:
        pass

    # === Mum formasyonları (klasik reversal sinyalleri) ===
    body = (c - o).abs()
    candle_range = h - l
    out["candle_body_pct"] = body / candle_range.replace(0, np.nan)
    out["candle_upper_shadow"] = (h - pd.concat([c, o], axis=1).max(axis=1)) / candle_range.replace(0, np.nan)
    out["candle_lower_shadow"] = (pd.concat([c, o], axis=1).min(axis=1) - l) / candle_range.replace(0, np.nan)
    # Engulfing: bugünkü mum dünkünü tamamen yutmuş
    prev_o, prev_c = o.shift(1), c.shift(1)
    bullish_engulf = (prev_c < prev_o) & (c > o) & (c >= prev_o) & (o <= prev_c)
    bearish_engulf = (prev_c > prev_o) & (c < o) & (c <= prev_o) & (o >= prev_c)
    out["pattern_bull_engulf"] = bullish_engulf.astype(int)
    out["pattern_bear_engulf"] = bearish_engulf.astype(int)
    # Hammer: küçük gövde, uzun alt fitil (>2x gövde), küçük üst fitil
    out["pattern_hammer"] = (
        (out["candle_body_pct"] < 0.3)
        & (out["candle_lower_shadow"] > 0.5)
        & (out["candle_upper_shadow"] < 0.15)
    ).astype(int)
    # Doji: gövde çok küçük (<%10)
    out["pattern_doji"] = (out["candle_body_pct"] < 0.1).astype(int)

    return out


def add_relative_strength(df: pd.DataFrame, benchmark_close: pd.Series, prefix: str = "rs_spy") -> pd.DataFrame:
    """Bir benchmark'a (örn. SPY) görece güç."""
    out = df.copy()
    aligned = benchmark_close.reindex(out.index).ffill()
    rs = out["close"] / aligned
    out[f"{prefix}"] = rs
    out[f"{prefix}_20d"] = rs / rs.shift(20) - 1     # 20 gün rölatif performans
    out[f"{prefix}_60d"] = rs / rs.shift(60) - 1
    return out


def make_swing_target(
    df: pd.DataFrame,
    horizon_days: int = 10,
    threshold: float = 0.03,
) -> pd.Series:
    fwd_return = df["close"].shift(-horizon_days) / df["close"] - 1
    return (fwd_return > threshold).astype(int).rename("target")
