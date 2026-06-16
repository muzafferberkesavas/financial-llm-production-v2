"""PEAD — Post-Earnings-Announcement Drift (Faz: signal research 2026-06).

One of the most robust, replicated anomalies: after an earnings surprise, prices
keep drifting in the surprise's direction for weeks (research: ~18% abnormal,
declining but real). Edge lives in a WINDOW right after the announcement and scales
with surprise magnitude (SUE proxy). Outside the window there is no active drift.

Returns a 0-100 drift score (50 = neutral): >50 bullish drift (recent positive
surprise), <50 bearish (recent miss). Uses Finnhub's last earnings date + surprise.
"""
from __future__ import annotations

from datetime import datetime

from finllm.data.finnhub_fundamentals import FinnhubSignals

DRIFT_WINDOW_DAYS = 75       # ~one quarter of drift after the announcement
SURPRISE_FULL_PCT = 8.0      # |surprise| at/above this → full-strength signal
# Finnhub gives the fiscal PERIOD END; earnings are announced ~this many days later.
# Drift starts at the announcement, so offset the period-end date by this lag.
ANNOUNCE_LAG_DAYS = 35


def pead_score(fh: FinnhubSignals | None, as_of: str | None = None) -> float:
    """Active drift score in [0,100]; 50 if no recent earnings / outside window."""
    if fh is None or not fh.last_earnings_date or fh.last_surprise_pct is None:
        return 50.0
    try:
        ed = datetime.strptime(fh.last_earnings_date[:10], "%Y-%m-%d")
        now = datetime.strptime(as_of[:10], "%Y-%m-%d") if as_of else datetime.utcnow()
    except (ValueError, TypeError):
        return 50.0
    days = (now - ed).days - ANNOUNCE_LAG_DAYS            # days since the announcement
    if days < 0 or days > DRIFT_WINDOW_DAYS:
        return 50.0  # drift not active

    decay = 1.0 - days / DRIFT_WINDOW_DAYS                 # strongest right after the print
    magnitude = min(1.0, abs(fh.last_surprise_pct) / SURPRISE_FULL_PCT)
    direction = 1.0 if fh.last_surprise_pct > 0 else -1.0
    return round(50.0 + direction * magnitude * decay * 50.0, 1)


def pead_label(score: float) -> str:
    if score >= 60:
        return "drift-up"
    if score <= 40:
        return "drift-down"
    return "none"


__all__ = ["pead_score", "pead_label", "DRIFT_WINDOW_DAYS"]
