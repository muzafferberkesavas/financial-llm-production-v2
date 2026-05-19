"""Outcome tracker — her sinyalin lifecycle'ını izle.

Akış:
  1. Stage 5 sinyal kaydederken outcome_records.jsonl'a "open" record yaz
  2. Cron job (scripts/update_outcomes.py) günde 1 kere her open record için:
     - Şu anki fiyatı çek
     - Stop hit, target hit, ya da time stop kontrolü yap
     - "closed" haline geçir + realized_return_pct, win bayrağı

  3. Calibrator (platt.py) bu kayıtlardan eğitim seti üretir.

Phase 2.4'te JSON Lines dosya, Phase 3'te Neon Postgres.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

from finllm.config.settings import DATA_DIR
from finllm.pipeline.context import ExtendedSignal
from finllm.utils.logging import logger


_OUTCOMES_FILE = DATA_DIR / "outcomes.jsonl"


@dataclass
class OutcomeRecord:
    """Her bir sinyalin ömrü boyunca güncellenen kayıt."""

    # Sinyal anı
    run_id: str
    ticker: str
    market: str
    generated_at: str            # ISO timestamp
    signal: str
    confidence: float
    expected_return_pct: float | None
    time_horizon_days: int | None
    entry_zone_low: float | None
    entry_zone_high: float | None
    stop_loss: float | None
    target_base: float | None    # base scenario target
    target_bull: float | None
    target_bear: float | None
    confluence_score: int
    market_regime: str
    weekly_trend: str
    confirmation_count: int
    warning_flags: list[str]
    setup_type: str = ""

    # Realized
    status: Literal["open", "win_target", "win_partial", "loss_stop", "loss_time", "neutral_time"] = "open"
    realized_return_pct: float | None = None
    realized_at: str | None = None
    days_held: int | None = None
    exit_reason: str = ""
    max_high_during_hold: float | None = None
    max_low_during_hold: float | None = None

    @property
    def is_win(self) -> bool:
        return self.status in ("win_target", "win_partial")

    @property
    def is_closed(self) -> bool:
        return self.status != "open"


def _get_target_price(scenarios: list, label: str) -> float | None:
    for s in scenarios:
        if s.get("label") == label:
            return s.get("target_price")
    return None


class OutcomeTracker:
    """JSON Lines outcome storage. Append + scan + rewrite pattern."""

    def __init__(self, file: Path | None = None):
        self.file = file or _OUTCOMES_FILE
        self.file.parent.mkdir(parents=True, exist_ok=True)
        if not self.file.exists():
            self.file.write_text("")

    def append(self, sig: ExtendedSignal, market: str) -> None:
        """Stage 5'ten çağrılır. Yeni open record yazar."""
        record = OutcomeRecord(
            run_id=sig.run_id,
            ticker=sig.ticker.symbol,
            market=market,
            generated_at=sig.generated_at.isoformat(),
            signal=sig.signal,
            confidence=sig.confidence,
            expected_return_pct=sig.expected_return_pct,
            time_horizon_days=sig.time_horizon_days,
            entry_zone_low=sig.entry_zone_low,
            entry_zone_high=sig.entry_zone_high,
            stop_loss=sig.stop_loss,
            target_base=next(
                (s.target_price for s in sig.scenarios if s.label == "base"), None
            ),
            target_bull=next(
                (s.target_price for s in sig.scenarios if s.label == "bull"), None
            ),
            target_bear=next(
                (s.target_price for s in sig.scenarios if s.label == "bear"), None
            ),
            confluence_score=sig.confluence_score,
            market_regime=sig.market_regime,
            weekly_trend=sig.weekly_trend,
            confirmation_count=sig.confirmation_count,
            warning_flags=list(sig.warning_flags),
        )
        with self.file.open("a") as f:
            f.write(json.dumps(asdict(record), default=str) + "\n")

    def append_many(self, signals: list[ExtendedSignal], market: str) -> int:
        """Birden çok sinyali append et. Actionable olanları sayar."""
        count = 0
        with self.file.open("a") as f:
            for sig in signals:
                if not sig.is_actionable:
                    continue
                record = OutcomeRecord(
                    run_id=sig.run_id,
                    ticker=sig.ticker.symbol,
                    market=market,
                    generated_at=sig.generated_at.isoformat(),
                    signal=sig.signal,
                    confidence=sig.confidence,
                    expected_return_pct=sig.expected_return_pct,
                    time_horizon_days=sig.time_horizon_days,
                    entry_zone_low=sig.entry_zone_low,
                    entry_zone_high=sig.entry_zone_high,
                    stop_loss=sig.stop_loss,
                    target_base=next(
                        (s.target_price for s in sig.scenarios if s.label == "base"),
                        None,
                    ),
                    target_bull=next(
                        (s.target_price for s in sig.scenarios if s.label == "bull"),
                        None,
                    ),
                    target_bear=next(
                        (s.target_price for s in sig.scenarios if s.label == "bear"),
                        None,
                    ),
                    confluence_score=sig.confluence_score,
                    market_regime=sig.market_regime,
                    weekly_trend=sig.weekly_trend,
                    confirmation_count=sig.confirmation_count,
                    warning_flags=list(sig.warning_flags),
                )
                f.write(json.dumps(asdict(record), default=str) + "\n")
                count += 1
        return count

    def load_all(self) -> list[OutcomeRecord]:
        if not self.file.exists():
            return []
        records = []
        for line in self.file.read_text().splitlines():
            if not line.strip():
                continue
            try:
                d = json.loads(line)
                records.append(OutcomeRecord(**d))
            except Exception as e:
                logger.warning(f"[OUTCOME-TRACKER] bad line skipped: {e}")
        return records

    def open_records(self) -> list[OutcomeRecord]:
        return [r for r in self.load_all() if not r.is_closed]

    def closed_records(self) -> list[OutcomeRecord]:
        return [r for r in self.load_all() if r.is_closed]

    def rewrite(self, records: list[OutcomeRecord]) -> None:
        """Tüm dosyayı yeniden yaz (status güncelleme sonrası)."""
        with self.file.open("w") as f:
            for r in records:
                f.write(json.dumps(asdict(r), default=str) + "\n")


def update_realized_outcomes(
    tracker: OutcomeTracker | None = None,
    price_fetcher=None,
) -> dict:
    """Tüm open record'ları için realized outcome hesabı.

    price_fetcher: callable(ticker, market) → list[(date, high, low, close)]
                   None ise yfinance ile defaultlar kullanılır.

    Döner: {"updated": N, "wins": W, "losses": L, "still_open": O}
    """
    import pandas as pd

    from finllm.markets import get_adapter
    from finllm.markets.base import Ticker

    tracker = tracker or OutcomeTracker()
    records = tracker.load_all()
    if not records:
        return {"updated": 0, "wins": 0, "losses": 0, "still_open": 0}

    stats = {"updated": 0, "wins": 0, "losses": 0, "still_open": 0}

    # Group by (market, ticker) — bir ticker'ın çoklu sinyalleri olabilir
    grouped: dict[tuple[str, str], list[OutcomeRecord]] = {}
    for r in records:
        if r.is_closed:
            continue
        grouped.setdefault((r.market, r.ticker), []).append(r)

    for (market, ticker_sym), open_recs in grouped.items():
        try:
            adapter = get_adapter(market)  # type: ignore
            ticker = Ticker(symbol=ticker_sym, market=market)  # type: ignore
        except Exception:
            continue

        # Sinyal başlangıcından itibaren fiyat geçmişi
        earliest = min(
            datetime.fromisoformat(r.generated_at).replace(tzinfo=None)
            for r in open_recs
        )
        start = (earliest - timedelta(days=5)).strftime("%Y-%m-%d")
        try:
            prices = adapter.fetch_prices(ticker, start=start)
        except Exception as e:
            logger.warning(f"[OUTCOME] {market}/{ticker_sym} price fetch: {e}")
            continue

        if prices.empty:
            continue

        for r in open_recs:
            gen_date = datetime.fromisoformat(r.generated_at).replace(tzinfo=None)
            # Sinyal sonrası fiyat barları
            after = prices[prices.index > gen_date]
            if after.empty:
                stats["still_open"] += 1
                continue

            horizon = r.time_horizon_days or 20
            cutoff = gen_date + timedelta(days=horizon)
            now = datetime.utcnow()

            # Sinyal sonrası bugüne kadar bakılacak bar window
            window = after[after.index <= min(cutoff, now)]
            if window.empty:
                stats["still_open"] += 1
                continue

            entry_mid = (
                (r.entry_zone_low + r.entry_zone_high) / 2
                if r.entry_zone_low and r.entry_zone_high
                else float(after.iloc[0]["close"])
            )

            window_high = float(window["high"].max())
            window_low = float(window["low"].min())

            r.max_high_during_hold = window_high
            r.max_low_during_hold = window_low

            # Exit kuralı: stop_loss veya target_base hit?
            stop_hit = r.stop_loss and window_low <= r.stop_loss
            target_hit = r.target_base and window_high >= r.target_base

            # Hangisi önce oldu? (basit yaklaşım: ilk bar'a göre)
            stop_idx = None
            target_idx = None
            for i, (_, row) in enumerate(window.iterrows()):
                if r.stop_loss and row["low"] <= r.stop_loss and stop_idx is None:
                    stop_idx = i
                if r.target_base and row["high"] >= r.target_base and target_idx is None:
                    target_idx = i

            close_idx_in_window = len(window) - 1
            final_close = float(window.iloc[-1]["close"])
            days_held = (window.index[-1] - gen_date.replace(tzinfo=window.index[-1].tzinfo)).days if window.index[-1].tzinfo else (window.index[-1] - gen_date).days

            if stop_idx is not None and (target_idx is None or stop_idx < target_idx):
                r.status = "loss_stop"
                r.realized_return_pct = (r.stop_loss - entry_mid) / entry_mid * 100
                r.exit_reason = f"stop_hit_day{stop_idx + 1}"
                r.days_held = stop_idx + 1
                r.realized_at = window.index[stop_idx].isoformat()
                stats["losses"] += 1
                stats["updated"] += 1
            elif target_idx is not None:
                r.status = "win_target"
                r.realized_return_pct = (r.target_base - entry_mid) / entry_mid * 100
                r.exit_reason = f"target_hit_day{target_idx + 1}"
                r.days_held = target_idx + 1
                r.realized_at = window.index[target_idx].isoformat()
                stats["wins"] += 1
                stats["updated"] += 1
            elif now > cutoff:
                # Time stop
                r.status = "neutral_time" if final_close >= entry_mid * 0.98 else "loss_time"
                r.realized_return_pct = (final_close - entry_mid) / entry_mid * 100
                r.exit_reason = "time_stop"
                r.days_held = days_held
                r.realized_at = window.index[-1].isoformat()
                if r.status == "neutral_time" and r.realized_return_pct > 2:
                    r.status = "win_partial"
                    stats["wins"] += 1
                elif r.status == "loss_time":
                    stats["losses"] += 1
                stats["updated"] += 1
            else:
                stats["still_open"] += 1

    tracker.rewrite(records)
    logger.info(f"[OUTCOME-UPDATE] {stats}")
    return stats


__all__ = ["OutcomeRecord", "OutcomeTracker", "update_realized_outcomes"]
