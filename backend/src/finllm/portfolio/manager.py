"""Portfolio manager — günlük refresh orkestrasyonu.

Akış:
    1. Universe için sinyal üret (cache'le)
    2. Açık pozisyonları yeniden değerlendir, SELL emirleri oluştur
    3. Boş slotlar için BUY adayları seç (confidence-weighted)
    4. BUY emirlerini oluştur (pending)
    5. Özet döndür
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from finllm.config.settings import settings
from finllm.config.universe import get_universe
from finllm.data.prices import fetch_prices
from finllm.portfolio import repository as repo
from finllm.portfolio.exits import evaluate_exit
from finllm.portfolio.models import Order, PortfolioSnapshot
from finllm.portfolio.sizing import compute_weights, select_buy_candidates
from finllm.signals.generator import generate_signal
from finllm.signals.schema import Signal
from finllm.utils.logging import logger


@dataclass
class RefreshReport:
    mode: str
    generated_at: datetime
    signals_generated: int = 0
    positions_evaluated: int = 0
    sell_orders_created: int = 0
    buy_orders_created: int = 0
    errors: list[str] = field(default_factory=list)


def _current_price(symbol: str) -> float | None:
    try:
        prices = fetch_prices(symbol, start="2025-01-01")
        return float(prices["close"].iloc[-1])
    except Exception as e:
        logger.warning(f"{symbol}: current price çekilemedi: {e}")
        return None


def daily_refresh(mode: str = "pre_open", universe: str = "core") -> RefreshReport:
    """Tam bir günlük refresh çevrimi."""
    repo.ensure_schema()
    report = RefreshReport(mode=mode, generated_at=datetime.utcnow())
    symbols = get_universe(universe)

    # --- 1. Sinyaller üret ---
    signals: dict[str, Signal] = {}
    for sym in symbols:
        try:
            s = generate_signal(sym)
            signals[sym] = s
            repo.log_signal(s, refresh_mode=mode)
            report.signals_generated += 1
        except Exception as e:
            msg = f"{sym} sinyal üretiminde hata: {e}"
            logger.warning(msg)
            report.errors.append(msg)

    # --- 2. Açık pozisyonları değerlendir ---
    open_pos = repo.open_positions()
    held_symbols = {p.symbol for p in open_pos}

    for pos in open_pos:
        report.positions_evaluated += 1
        cp = _current_price(pos.symbol)
        if cp is None:
            continue
        new_sig = signals.get(pos.symbol)
        decision = evaluate_exit(pos, cp, new_sig)
        if decision.should_exit:
            logger.info(f"EXIT {pos.symbol}: {decision.reason} ({decision.note})")
            order = Order(
                symbol=pos.symbol,
                side="SELL",
                status="pending",
                suggested_price=cp,
                rationale=f"{decision.reason}: {decision.note}",
                reason_code=decision.reason,
                related_position_id=pos.id,
                capital_usd=pos.capital_usd,
                weight_pct=pos.weight_pct,
            )
            repo.insert_order(order)
            report.sell_orders_created += 1

    # --- 3. Yeni BUY adayları ---
    deployed_pct = sum(p.weight_pct for p in open_pos)
    available_pct = max(0.0, 100.0 - deployed_pct)

    if available_pct < 5.0:
        logger.info(f"Portföy doluya yakın (deployed {deployed_pct:.1f}%) — yeni BUY üretilmiyor")
        return report

    candidates = select_buy_candidates(list(signals.values()), held_symbols)
    if not candidates:
        logger.info("Yeterli aday yok (BUY, confidence>=0.60)")
        return report

    weighted = compute_weights(candidates)

    # Mevcut müsait kapasiteye scale et
    raw_total = sum(w for _, w in weighted)
    if raw_total > available_pct:
        scale = available_pct / raw_total
        weighted = [(s, w * scale) for s, w in weighted]

    for sig, weight_pct in weighted:
        capital_usd = settings.portfolio_initial_capital_usd * (weight_pct / 100)
        order = Order(
            symbol=sig.symbol,
            side="BUY",
            status="pending",
            suggested_price=sig.entryPrice,
            target_price=sig.targetPrice,
            stop_loss=sig.stopLoss,
            weight_pct=weight_pct,
            capital_usd=capital_usd,
            rationale=sig.rationale,
        )
        repo.insert_order(order)
        report.buy_orders_created += 1
        logger.info(f"BUY {sig.symbol}: {weight_pct:.1f}% (${capital_usd:.0f})")

    return report


def get_snapshot() -> PortfolioSnapshot:
    repo.ensure_schema()
    open_pos = repo.open_positions()
    pending = repo.pending_orders()
    stats = repo.portfolio_stats()

    deployed = sum(p.capital_usd for p in open_pos)
    open_pnl = 0.0
    for p in open_pos:
        cp = _current_price(p.symbol)
        if cp:
            open_pnl += p.capital_usd * (cp / p.entry_price - 1)

    initial = settings.portfolio_initial_capital_usd
    realized = stats["realized_pnl_usd"]
    cash = initial + realized - deployed

    return PortfolioSnapshot(
        initial_capital_usd=initial,
        deployed_capital_usd=deployed,
        open_positions=open_pos,
        pending_orders=pending,
        realized_pnl_usd=realized,
        open_pnl_usd=open_pnl,
        total_value_usd=cash + deployed + open_pnl,
        n_open=len(open_pos),
        n_pending=len(pending),
    )
