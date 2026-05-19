"""Telegram alert stub — Phase 1'de logger'a yazıyor.

Phase 2'de aiogram ile gerçek bot:
  - Public channel: @nasdaq_signals, @bist_signals (günlük post)
  - Private DM: /signal AAPL gibi komutlar
"""
from __future__ import annotations

from finllm.pipeline.context import ExtendedSignal, PipelineContext
from finllm.utils.logging import logger


def format_signal_for_telegram(sig: ExtendedSignal, currency: str = "USD") -> str:
    """Tek sinyal için Telegram channel post'u (Markdown)."""
    cur_symbol = "$" if currency == "USD" else "₺"
    emoji = {
        "GUCLU_AL": "🟢🟢",
        "AL": "🟢",
        "IZLE": "🔵",
        "TUT": "⚪",
        "KISMI_SAT": "🟠",
        "SAT": "🔴",
        "ACIL_SAT": "🔴🔴",
    }.get(sig.signal, "⚪")

    lines = [
        f"{emoji} *{sig.signal.replace('_', ' ')}* — *{sig.ticker.symbol}* ({sig.ticker.name})",
        f"Sector: {sig.ticker.sector}",
        f"Confidence: *{sig.confidence:.2f}* | Regime: {sig.market_regime} | Weekly: {sig.weekly_trend}",
    ]

    if sig.allocation_cash > 0:
        lines.append(
            f"Allocation: {cur_symbol}{sig.allocation_cash:,.0f} "
            f"({sig.allocation_weight:.1%} of portfolio)"
        )

    if sig.expected_return_pct is not None:
        lines.append(
            f"Expected Return: *{sig.expected_return_pct:+.1f}%* "
            f"in {sig.time_horizon_days} days"
        )

    if sig.entry_zone_low and sig.entry_zone_high:
        lines.append(
            f"Entry: [{cur_symbol}{sig.entry_zone_low:.2f} — "
            f"{cur_symbol}{sig.entry_zone_high:.2f}]"
        )

    if sig.stop_loss:
        lines.append(f"Stop Loss: {cur_symbol}{sig.stop_loss:.2f}")

    if sig.scenarios:
        lines.append("Scenarios:")
        for sc in sig.scenarios:
            lines.append(
                f"  • {sc.label}: {cur_symbol}{sc.target_price:.2f} "
                f"({sc.probability:.0%} prob, {sc.expected_return_pct:+.1f}%)"
            )

    if sig.rationale_full:
        lines.append(f"\n_Analysis:_ {sig.rationale_full[:200]}")

    if sig.warning_flags:
        lines.append(f"\n⚠️ Flags: {', '.join(sig.warning_flags[:3])}")

    lines.append(
        f"\n_Backtest 30d: {sig.backtest_30d_return_pct:+.1f}%_"
        if sig.backtest_30d_return_pct is not None
        else ""
    )

    return "\n".join(filter(None, lines))


class TelegramStub:
    """Phase 1 logger-based stub. Phase 2'de aiogram ile değiştir."""

    def __init__(self, channel: str = "@signals"):
        self.channel = channel

    def post_to_channel(self, message: str) -> None:
        logger.info(f"[TELEGRAM:{self.channel}] would post:\n{message}\n")

    def post_signals(self, ctx: PipelineContext) -> None:
        actionable = [s for s in ctx.signals if s.is_actionable]
        if not actionable:
            logger.info(f"[TELEGRAM:{self.channel}] no actionable signals to post")
            return

        currency = ctx.adapter.currency
        market = ctx.adapter.name.upper()
        header = (
            f"📊 *{market} {ctx.mode.replace('_', ' ').title()} Signals* — "
            f"{ctx.started_at.strftime('%Y-%m-%d %H:%M UTC')}\n"
            f"Run: `{ctx.run_id}` | {len(actionable)} actionable\n"
            f"{'─' * 35}"
        )
        logger.info(f"[TELEGRAM:{self.channel}] header:\n{header}\n")
        for sig in actionable:
            self.post_to_channel(format_signal_for_telegram(sig, currency=currency))
