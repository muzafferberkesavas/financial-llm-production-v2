"""Açık pozisyonlar için çıkış sinyali değerlendirme."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from finllm.portfolio.models import ExitReason, Position
from finllm.signals.schema import Signal

SIGNAL_FLIP_MIN_CONFIDENCE = 0.60
NEGATIVE_NEWS_THRESHOLD = -0.50    # sentiment polarity altında olursa "kötü haber"


@dataclass
class ExitDecision:
    should_exit: bool
    reason: ExitReason | None = None
    note: str = ""


def evaluate_exit(
    position: Position,
    current_price: float,
    new_signal: Signal | None,
    now: datetime | None = None,
) -> ExitDecision:
    now = now or datetime.utcnow()

    # 1. Target hit
    if position.target_price and current_price >= position.target_price:
        return ExitDecision(True, "TARGET_HIT", f"${current_price:.2f} ≥ ${position.target_price:.2f}")

    # 2. Stop loss
    if position.stop_loss and current_price <= position.stop_loss:
        return ExitDecision(True, "STOP_HIT", f"${current_price:.2f} ≤ ${position.stop_loss:.2f}")

    # 3. Max holding süresi doldu
    days_held = (now - position.entry_date).days
    if days_held >= position.max_holding_days:
        return ExitDecision(True, "MAX_HOLDING", f"{days_held} gün ≥ {position.max_holding_days}")

    if new_signal is None:
        return ExitDecision(False)

    # 4. Sinyal SELL'e döndü ve yeterince güvenli
    if new_signal.direction == "SELL" and new_signal.confidence >= SIGNAL_FLIP_MIN_CONFIDENCE:
        return ExitDecision(
            True,
            "SIGNAL_FLIP",
            f"yeni sinyal SELL (güven {new_signal.confidence:.2f})",
        )

    # 5. Negatif haber şoku
    if new_signal.signals.sentiment.score <= NEGATIVE_NEWS_THRESHOLD:
        return ExitDecision(
            True,
            "NEGATIVE_NEWS",
            f"sentiment {new_signal.signals.sentiment.score:+.2f}",
        )

    return ExitDecision(False)
