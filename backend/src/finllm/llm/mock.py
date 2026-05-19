"""MockLLM — deterministic, kural-bazlı LLM simülasyonu.

Phase 1'de gerçek LLM olmadan tüm pipeline'ı çalıştırmak için.
Çıktı hash-based seeded random — aynı input → aynı output (testable).

Kural mantığı confluence skoruna + setup type'a göre. Gerçek LLM'in
yaklaşık davranışını taklit eder ama HALÜSİNASYON YOK — gerçek output'la
karşılaştırma yapabilmek için deterministik.
"""
from __future__ import annotations

import hashlib
import json
import re

from finllm.llm.base import (
    DeepAnalysis,
    LLMClient,
    PriceScenarioOutput,
    ScreenVerdict,
)


def _parse_block_for_summary(data_block: str) -> dict:
    """Data block'tan key metrikleri regex ile çıkar (deterministik karar için)."""
    out: dict = {}

    # Header: [STOCK: TICKER | name | sector | tags...]
    m = re.search(r"\[(?:STOCK|COMMODITY):\s*(\S+)\s*\|", data_block)
    if m:
        out["ticker"] = m.group(1)

    # PRICE: Last=X | Chg=Y% | Vol=Z(Avg20:V) | VolRatio=Rx(LABEL)
    m = re.search(r"Last=([\d.]+)", data_block)
    if m:
        out["close"] = float(m.group(1))

    m = re.search(r"VolRatio=([\d.]+)x\(([A-Z_]+)\)", data_block)
    if m:
        out["vol_ratio"] = float(m.group(1))
        out["vol_label"] = m.group(2)

    # CONFLUENCE: Score=X/100
    m = re.search(r"CONFLUENCE:\s*Score=(\d+)/100", data_block)
    if m:
        out["confluence"] = int(m.group(1))

    # CONFLUENCE_SIGNAL: LABEL (confidence: a-b)
    m = re.search(r"CONFLUENCE_SIGNAL:\s*(\w+)\s*\(confidence:\s*([\d.]+)-([\d.]+)\)", data_block)
    if m:
        out["suggested_signal"] = m.group(1)
        out["conf_low"] = float(m.group(2))
        out["conf_high"] = float(m.group(3))

    # ATR
    m = re.search(r"ATR14:\s*([\d.]+)", data_block)
    if m:
        out["atr"] = float(m.group(1))

    # RSI
    m = re.search(r"RSI14:\s*([\d.]+)\s*\|\s*Momentum=([A-Z_]+)", data_block)
    if m:
        out["rsi"] = float(m.group(1))
        out["rsi_label"] = m.group(2)

    # Setup type
    m = re.search(r"SETUP:\s*(\w+)\s*\(([\d.]+)\)", data_block)
    if m:
        out["setup"] = m.group(1)
        out["setup_conf"] = float(m.group(2))

    # Regime
    m = re.search(r"MARKET REGIME:\s*(\w+)", data_block)
    if m:
        out["regime"] = m.group(1)

    # Weekly trend (specifically WEEKLY satırında)
    m = re.search(r"WEEKLY:[^\n]*?Trend=(\w+)", data_block)
    if m:
        out["weekly_trend"] = m.group(1)

    # Timeframe alignment
    m = re.search(r"TIMEFRAME:\s*Alignment=(\w+)", data_block)
    if m:
        out["timeframe_alignment"] = m.group(1)

    return out


def _seeded_random(text: str, salt: str = "mock") -> float:
    """Hash-based deterministic [0,1) random."""
    h = hashlib.md5((text + salt).encode()).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


class MockLLM(LLMClient):
    """Pipeline test için deterministic LLM stub.

    Kural-bazlı:
      - Confluence >= 70 + setup_score >= 0.7 → GUCLU_AL
      - Confluence >= 55 + setup_score >= 0.5 → AL
      - Confluence 40-55 → IZLE
      - Confluence 25-40 → TUT
      - Confluence < 25 → SAT

    Confidence = confluence/100 ± seeded noise.
    """

    def __init__(self, role: str = "deep"):
        """role: 'screen' (cheap, fast) or 'deep' (full analysis)."""
        self.role = role
        self.name = f"mock-{role}"
        self.cost_per_1k_input = 0.0
        self.cost_per_1k_output = 0.0

    def screen(self, data_block: str) -> ScreenVerdict:
        """Stage 2 — strong/potential/skip etiketi."""
        meta = _parse_block_for_summary(data_block)
        ticker = meta.get("ticker", "UNKNOWN")
        confluence = meta.get("confluence", 0)
        setup_conf = meta.get("setup_conf", 0.0)

        if confluence >= 65 and setup_conf >= 0.7:
            verdict = "strong"
            rationale = (
                f"Confluence {confluence} + setup {meta.get('setup', 'n/a')} "
                f"({setup_conf:.2f}) high quality. {meta.get('regime', 'n/a')} regime favorable."
            )
        elif confluence >= 50:
            verdict = "potential"
            rationale = (
                f"Confluence {confluence} moderate. {meta.get('weekly_trend', 'n/a')} weekly. "
                f"Needs LLM confirmation."
            )
        else:
            verdict = "skip"
            rationale = f"Confluence {confluence} too low; weak setup."

        return ScreenVerdict(
            ticker=ticker,
            verdict=verdict,
            rationale=rationale,
            cost_usd=0.0,
        )

    def deep_analyze(self, data_block: str) -> DeepAnalysis:
        """Stage 3 — tam analist çıktısı simülasyonu."""
        meta = _parse_block_for_summary(data_block)
        ticker = meta.get("ticker", "UNKNOWN")
        confluence = meta.get("confluence", 0)
        close = meta.get("close", 100.0)
        atr = meta.get("atr", close * 0.02)
        setup_conf = meta.get("setup_conf", 0.0)
        suggested = meta.get("suggested_signal", "TUT")
        regime = meta.get("regime", "UNKNOWN")
        weekly = meta.get("weekly_trend", "UNKNOWN")
        rsi = meta.get("rsi", 50.0)
        rsi_label = meta.get("rsi_label", "NEUTRAL")
        vol_label = meta.get("vol_label", "NORMAL")

        # Confidence from confluence + small seeded noise
        base_conf = confluence / 100.0
        noise = _seeded_random(ticker + data_block, "conf") * 0.1 - 0.05
        confidence = max(0.0, min(1.0, base_conf + noise))

        # Signal mapping — confluence dominant, confirmations boost
        confirmations = 0
        if regime in ("TREND", "STRONG_TREND"):
            confirmations += 1
        if rsi_label in ("BULLISH_MOMENTUM", "OVERSOLD_BOUNCING", "OVERBOUGHT"):
            # Overbought TRENDde tolere edilir
            confirmations += 1
        if vol_label in ("HIGH", "VERY_HIGH", "EXTREME"):
            confirmations += 1
        if setup_conf >= 0.5:
            confirmations += 1
        if weekly in ("UPTREND", "EARLY_RECOVERY"):
            confirmations += 1
        if meta.get("timeframe_alignment") == "ALIGNED":
            confirmations += 1

        # Confluence dominant — confirmations modülasyon yapar
        if confluence >= 70 and confirmations >= 2:
            signal = "GUCLU_AL"
        elif confluence >= 55 and confirmations >= 1:
            signal = "AL"
        elif confluence >= 40:
            signal = "IZLE"
        elif confluence >= 25:
            signal = "TUT"
        else:
            signal = "SAT"

        # Confluence warning durumunda confidence ceza
        if "WEEKLY_CONFLICT" in data_block:
            confidence = min(confidence, 0.5)
        if "LOW_VOLUME" in data_block:
            confidence = min(confidence, 0.6)

        # Price targets — ATR-based, scenario distribution
        if signal in ("GUCLU_AL", "AL"):
            stop_loss = close - atr * 2.0
            base_target = close + atr * 4.0
            bull_target = close + atr * 7.0
            bear_target = stop_loss
            entry_low = close - atr * 0.5
            entry_high = close + atr * 0.5

            expected_ret = (
                (base_target / close - 1) * 0.55
                + (bull_target / close - 1) * 0.25
                + (bear_target / close - 1) * 0.20
            ) * 100

            scenarios = [
                PriceScenarioOutput(
                    "base", base_target, 0.55,
                    expected_return_pct=(base_target / close - 1) * 100,
                ),
                PriceScenarioOutput(
                    "bull", bull_target, 0.25,
                    expected_return_pct=(bull_target / close - 1) * 100,
                ),
                PriceScenarioOutput(
                    "bear", bear_target, 0.20,
                    expected_return_pct=(bear_target / close - 1) * 100,
                ),
            ]
            horizon = 15 + int(_seeded_random(ticker, "horizon") * 15)  # 15-30 gün
        else:
            stop_loss = None
            entry_low = entry_high = None
            scenarios = []
            expected_ret = 0.0
            horizon = None

        rationale_trend = (
            f"Market regime: {regime}. Weekly trend {weekly}. "
            f"RSI {rsi:.1f} ({rsi_label}). "
            f"{'Multi-timeframe ALIGNED — trust momentum.' if weekly == 'UPTREND' else 'Weekly mixed — moderate sizing.'}"
        )
        rationale_volume = (
            f"Volume tier {vol_label}. {'Confirms breakout.' if vol_label in ('HIGH', 'VERY_HIGH', 'EXTREME') else 'No volume confirmation yet.'}"
        )
        rationale_formation = (
            f"Setup detected: {meta.get('setup', 'none')} (confidence {setup_conf:.2f}). "
            f"{'Classic pullback to EMA — high-probability entry.' if meta.get('setup') == 'pullback_ema' else ''}"
        )
        rationale_risks = []
        if rsi > 75:
            rationale_risks.append("RSI overbought — partial profit at resistance")
        if vol_label in ("LOW", "VERY_LOW"):
            rationale_risks.append("Low volume — breakout unconfirmed")
        if "TRANSITIONAL" in regime:
            rationale_risks.append("Regime transition — reduce position size")

        rationale_full = (
            f"{ticker}: Confluence {confluence}/100, {confirmations} confirmations. "
            f"Signal {signal} (conf {confidence:.2f}). "
            f"[MOCK LLM — deterministic rule-based output, replace with Claude Opus in Phase 2]"
        )

        return DeepAnalysis(
            ticker=ticker,
            signal=signal,
            confidence=round(confidence, 3),
            entry_zone_low=entry_low,
            entry_zone_high=entry_high,
            stop_loss=stop_loss,
            scenarios=scenarios,
            expected_return_pct=round(expected_ret, 2) if expected_ret else None,
            time_horizon_days=horizon,
            rationale_trend=rationale_trend,
            rationale_formation=rationale_formation,
            rationale_volume=rationale_volume,
            rationale_news="[MOCK] News integration in Phase 2",
            rationale_fibonacci="",
            rationale_risks=rationale_risks,
            rationale_full=rationale_full,
            warning_flags=[],
            unsourced_flag=False,
            model=self.name,
            cost_usd=0.0,
        )
