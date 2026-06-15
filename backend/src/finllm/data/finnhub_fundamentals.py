"""Finnhub fundamental signals — earnings-surprise momentum + analyst consensus.

Enriches the per-stock decision with two signals yfinance.info doesn't carry,
both free on Finnhub's tier:
  • Earnings surprises (last 4 quarters): actual vs estimate → beat streak +
    average surprise (earnings-drift edge, ARCHITECTURE.md data layer).
  • Analyst recommendation consensus → conviction.

Day-cached per symbol (free tier is 60 req/min). Feeds indicators/risk_reward.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import httpx

from finllm.config.settings import settings
from finllm.utils.logging import logger

_BASE = "https://finnhub.io/api/v1"
_CACHE_DIR = Path("backend/data/cache/finnhub")


@dataclass(slots=True)
class FinnhubSignals:
    avg_surprise_pct: float | None = None   # mean of last quarters' surprisePercent
    beat_streak: int = 0                    # consecutive recent beats
    n_quarters: int = 0
    earnings_momentum: str = "unknown"      # beating | mixed | missing | unknown
    analyst_score: float | None = None      # 0-1 (1 = all strong buy)
    analyst_label: str = "unknown"          # bullish | neutral | bearish | unknown
    n_analysts: int = 0

    def as_dict(self) -> dict:
        return {
            "avg_surprise_pct": self.avg_surprise_pct,
            "beat_streak": self.beat_streak,
            "earnings_momentum": self.earnings_momentum,
            "analyst_score": self.analyst_score,
            "analyst_label": self.analyst_label,
            "n_analysts": self.n_analysts,
        }


def _cache_path(symbol: str) -> Path:
    return _CACHE_DIR / f"{symbol}_{datetime.utcnow():%Y%m%d}.json"


def _get(path: str) -> object | None:
    key = settings.finnhub_api_key
    if not key:
        return None
    try:
        r = httpx.get(f"{_BASE}/{path}&token={key}", timeout=15.0)
        r.raise_for_status()
        return r.json()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[FINNHUB] {path.split('?')[0]} failed: {e}")
        return None


def _analyst(reco: list | None) -> tuple[float | None, str, int]:
    if not reco:
        return None, "unknown", 0
    r = reco[0]  # most recent period
    sb, b, h, s, ss = (r.get(k, 0) for k in ("strongBuy", "buy", "hold", "sell", "strongSell"))
    n = sb + b + h + s + ss
    if n == 0:
        return None, "unknown", 0
    score = (sb * 1.0 + b * 0.75 + h * 0.5 + s * 0.25 + ss * 0.0) / n
    label = "bullish" if score >= 0.7 else "bearish" if score <= 0.45 else "neutral"
    return round(score, 3), label, n


def _earnings(eps: list | None, lookback: int = 4) -> tuple[float | None, int, int, str]:
    if not eps:
        return None, 0, 0, "unknown"
    recent = eps[:lookback]  # finnhub returns newest first
    surprises = [e["surprisePercent"] for e in recent if e.get("surprisePercent") is not None]
    if not surprises:
        return None, 0, 0, "unknown"
    avg = sum(surprises) / len(surprises)
    streak = 0
    for sp in surprises:  # from most recent
        if sp > 0:
            streak += 1
        else:
            break
    beats = sum(1 for sp in surprises if sp > 0)
    if beats >= len(surprises) - 0 and avg > 0:
        momentum = "beating"
    elif beats <= len(surprises) // 2 and avg < 0:
        momentum = "missing"
    else:
        momentum = "mixed"
    return round(avg, 2), streak, len(surprises), momentum


def fetch_finnhub_signals(symbol: str, use_cache: bool = True) -> FinnhubSignals | None:
    if not settings.finnhub_api_key:
        return None
    cache = _cache_path(symbol)
    if use_cache and cache.exists():
        try:
            return FinnhubSignals(**json.loads(cache.read_text()))
        except Exception:  # noqa: BLE001
            pass

    eps = _get(f"stock/earnings?symbol={symbol}")
    reco = _get(f"stock/recommendation?symbol={symbol}")
    if eps is None and reco is None:
        return None

    avg, streak, nq, momentum = _earnings(eps if isinstance(eps, list) else None)
    a_score, a_label, n_an = _analyst(reco if isinstance(reco, list) else None)
    sig = FinnhubSignals(
        avg_surprise_pct=avg, beat_streak=streak, n_quarters=nq, earnings_momentum=momentum,
        analyst_score=a_score, analyst_label=a_label, n_analysts=n_an,
    )
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(sig.as_dict()))
    except Exception:  # noqa: BLE001
        pass
    return sig


__all__ = ["FinnhubSignals", "fetch_finnhub_signals"]
