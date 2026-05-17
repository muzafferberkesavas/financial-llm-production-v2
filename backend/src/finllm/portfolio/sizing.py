"""Confidence-weighted pozisyon büyüklüğü hesaplama.

Kurallar:
1. Sadece direction=BUY ve confidence >= MIN_CONFIDENCE adayları
2. 3-7 pozisyon (en az 3, en fazla 7)
3. Ağırlık = confidence^EXPONENT / sum(confidence^EXPONENT), exponent ile aşırı yoğunlaşmayı yumuşat
4. Min ağırlık %8, max ağırlık %35 — concentration limit
5. Toplam ağırlık %100'ü geçmez; geçerse pro-rata düşür
"""
from __future__ import annotations

from finllm.signals.schema import Signal

MIN_CONFIDENCE = 0.60
MIN_POSITIONS = 3
MAX_POSITIONS = 7
MIN_WEIGHT_PCT = 8.0
MAX_WEIGHT_PCT = 35.0
EXPONENT = 1.5            # 1.0 = direct confidence; >1 = yüksek confidence'a daha fazla ağırlık


def select_buy_candidates(signals: list[Signal], exclude_symbols: set[str]) -> list[Signal]:
    candidates = [
        s for s in signals
        if s.direction == "BUY"
        and s.confidence >= MIN_CONFIDENCE
        and s.symbol not in exclude_symbols
    ]
    candidates.sort(key=lambda s: s.confidence, reverse=True)
    return candidates[:MAX_POSITIONS]


def compute_weights(candidates: list[Signal]) -> list[tuple[Signal, float]]:
    """(Signal, weight_pct) listesi döndürür. weight_pct toplamı <= 100."""
    if not candidates:
        return []
    if len(candidates) < MIN_POSITIONS:
        # Yeterli yüksek-güven aday yok — boş pozisyonu nakit olarak tut
        return []

    raw = [s.confidence ** EXPONENT for s in candidates]
    total = sum(raw)
    weights = [(s, (w / total) * 100) for s, w in zip(candidates, raw)]

    # Concentration limit: ağırlık tavanı/tabanı uygula, sonra renormalize
    capped = [(s, max(MIN_WEIGHT_PCT, min(MAX_WEIGHT_PCT, w))) for s, w in weights]
    s_total = sum(w for _, w in capped)
    if s_total > 100:
        # Pro-rata down-scale
        capped = [(s, w * 100 / s_total) for s, w in capped]
    return capped
