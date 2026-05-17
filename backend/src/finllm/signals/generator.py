"""Uçtan uca sinyal üretici: prices + news → features + sentiment → Claude → Signal."""
from __future__ import annotations

import math

import pandas as pd

from finllm.config.settings import settings
from finllm.data.prices import fetch_prices
from finllm.ensemble.claude_reasoner import reason as reason_single
from finllm.ensemble.multi_llm_voter import reason_ensemble
from finllm.features.technical import add_technical_features
from finllm.sentiment.provider import aggregate_polarity, get_provider
from finllm.signals.schema import (
    FactorScore,
    HoldingDays,
    ReasoningInput,
    Signal,
    SignalFactors,
)
from finllm.utils.logging import logger


def _technical_snapshot(feats: pd.DataFrame) -> tuple[dict, float]:
    """Son günün teknik göstergelerinden Claude'a verilecek özeti çıkar.

    Döner: (snapshot_dict, normalized_score ∈ [-1, 1])
    """
    last = feats.iloc[-1]
    snapshot = {}
    for key in [
        "close", "ret_5d", "ret_20d", "rsi_14", "macd", "macd_signal", "macd_hist",
        "stoch_k", "bb_pct", "adx_14", "di_plus", "di_minus", "atr_pct",
        "vol_ratio", "price_vs_sma50", "price_vs_sma200",
    ]:
        v = last.get(key)
        if v is not None and isinstance(v, (int, float)) and not math.isnan(v):
            snapshot[key] = round(float(v), 4)

    # Basit kural-bazlı teknik skor — Claude öncesi sayısal sinyal
    score = 0.0
    weights = 0
    if "rsi_14" in snapshot:
        rsi = snapshot["rsi_14"]
        score += (50 - rsi) / 50  # RSI 50 nötr, 30 = +0.4, 70 = -0.4
        weights += 1
    if "macd_hist" in snapshot:
        score += 1.0 if snapshot["macd_hist"] > 0 else -1.0
        weights += 1
    if "price_vs_sma50" in snapshot:
        score += min(max(snapshot["price_vs_sma50"] * 5, -1), 1)
        weights += 1
    if "adx_14" in snapshot and "di_plus" in snapshot and "di_minus" in snapshot:
        trend = (snapshot["di_plus"] - snapshot["di_minus"]) / 100
        strength = min(snapshot["adx_14"] / 50, 1.0)
        score += trend * strength
        weights += 1
    tech_score = score / max(weights, 1)
    tech_score = max(-1.0, min(1.0, tech_score))
    return snapshot, tech_score


def _sentiment_snapshot(symbol: str, days_back: int = 5) -> tuple[dict, float, list[dict]]:
    """Finnhub'tan haberi çek, FinBERT skorla, özet döndür.

    Döner: (sentiment_dict, polarity, recent_news_dicts)
    """
    if not settings.finnhub_api_key:
        logger.warning("FINNHUB_API_KEY yok — sentiment boş geçilecek")
        return ({"available": False, "reason": "no_api_key"}, 0.0, [])

    from finllm.data.news import fetch_news

    news = fetch_news(symbol, days_back=days_back)
    if not news:
        return ({"available": True, "newsCount": 0, "polarity": 0.0}, 0.0, [])

    texts = [n.text for n in news[:30]]
    results = get_provider().score_batch(texts)
    polarity = aggregate_polarity(results)
    pos = sum(1 for r in results if r.label == "positive")
    neg = sum(1 for r in results if r.label == "negative")
    neu = sum(1 for r in results if r.label == "neutral")

    snapshot = {
        "available": True,
        "newsCount": len(news),
        "analyzed": len(results),
        "polarity": round(polarity, 4),
        "positive": pos,
        "negative": neg,
        "neutral": neu,
    }
    recent = [
        {
            "headline": n.headline,
            "source": n.source,
            "publishedAt": n.published_at.isoformat(),
        }
        for n in news[:8]
    ]
    return snapshot, polarity, recent


def generate_signal(symbol: str, days_back_news: int = 5) -> Signal:
    """Bir hisse için uçtan uca sinyal üretir.

    Akış:
        1. yfinance ile son 2 yıllık fiyat
        2. 30+ teknik gösterge
        3. Finnhub haber (varsa) → FinBERT sentiment
        4. Claude meta-karar (BUY/SELL/HOLD + gerekçe)
    """
    logger.info(f"=== Sinyal üretimi başlıyor: {symbol} ===")

    prices = fetch_prices(symbol, start="2024-01-01")
    feats = add_technical_features(prices)
    tech_snapshot, tech_score = _technical_snapshot(feats)
    sent_snapshot, sent_score, recent_news = _sentiment_snapshot(symbol, days_back_news)
    current_price = float(feats["close"].iloc[-1])

    reasoning_input = ReasoningInput(
        symbol=symbol,
        currentPrice=current_price,
        technical=tech_snapshot,
        sentiment=sent_snapshot,
        recentNews=recent_news,
    )
    if settings.reasoner_mode == "ensemble":
        decision = reason_ensemble(reasoning_input)
    else:
        decision = reason_single(reasoning_input)

    signal = Signal(
        symbol=symbol,
        direction=decision.direction,
        confidence=decision.confidence,
        holdingDays=HoldingDays(min=decision.holdingDaysMin, max=decision.holdingDaysMax),
        entryPrice=current_price,
        targetPrice=decision.targetPrice,
        stopLoss=decision.stopLoss,
        expectedReturn=decision.expectedReturn,
        rationale=decision.rationale,
        riskFactors=decision.riskFactors,
        signals=SignalFactors(
            technical=FactorScore(score=tech_score, notes=decision.technicalNote),
            sentiment=FactorScore(score=sent_score, notes=decision.sentimentNote),
        ),
    )
    logger.info(f"=== {symbol}: {signal.direction} (güven {signal.confidence:.2f}) ===")
    return signal


def generate_signals(symbols: list[str]) -> list[Signal]:
    out: list[Signal] = []
    for sym in symbols:
        try:
            out.append(generate_signal(sym))
        except Exception as e:
            logger.error(f"{sym} sinyal üretiminde hata: {e}")
    return out
