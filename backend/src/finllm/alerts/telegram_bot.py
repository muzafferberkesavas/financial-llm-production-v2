"""Telegram bot — Phase 2.3 production implementation (aiogram).

İki rol:
  1. Channel poster (run_pipeline sonrası sinyali kanala post eder)
  2. Private DM bot (user'lar /signal AAPL gibi sorgu yapar)

Environment:
  TELEGRAM_BOT_TOKEN          — @BotFather'dan
  TELEGRAM_CHANNEL_NASDAQ     — @nasdaq_signals (veya -1001234567890 numeric ID)
  TELEGRAM_CHANNEL_BIST       — @bist_signals
  TELEGRAM_ADMIN_IDS          — comma-separated user IDs (admin komutları için)

Token yoksa TelegramStub'a fallback.
"""
from __future__ import annotations

import asyncio
from typing import Optional

import httpx

from finllm.alerts.telegram_stub import TelegramStub, format_signal_for_telegram
from finllm.config.settings import settings
from finllm.pipeline.context import ExtendedSignal, PipelineContext
from finllm.utils.logging import logger


_TELEGRAM_API_BASE = "https://api.telegram.org/bot"


class TelegramBot:
    """Lightweight Telegram channel poster — aiogram'a bağımlı değil.

    Bot tek bir thing yapar: kanala message gönder. DM handler ayrı bir
    long-running process (`scripts/telegram_dm_bot.py`).
    """

    def __init__(
        self,
        bot_token: str | None = None,
        channel: str | None = None,
        market: str = "nasdaq",
    ):
        self.bot_token = bot_token or settings.telegram_bot_token
        self.market = market
        if channel is None:
            channel = (
                settings.telegram_channel_nasdaq
                if market == "nasdaq"
                else settings.telegram_channel_bist
            )
        self.channel = channel
        self._available = bool(self.bot_token and self.channel)
        self._client = httpx.Client(timeout=15.0)

    def is_available(self) -> bool:
        return self._available

    def post_to_channel(self, message: str, parse_mode: str = "Markdown") -> bool:
        """Kanala message gönder. Telegram Markdown V1 desteği."""
        if not self._available:
            logger.warning("[TELEGRAM-BOT] not configured, skipping channel post")
            return False

        try:
            resp = self._client.post(
                f"{_TELEGRAM_API_BASE}{self.bot_token}/sendMessage",
                json={
                    "chat_id": self.channel,
                    "text": message,
                    "parse_mode": parse_mode,
                    "disable_web_page_preview": True,
                },
            )
            if resp.status_code != 200:
                logger.warning(
                    f"[TELEGRAM-BOT] {self.channel} post fail HTTP {resp.status_code}: "
                    f"{resp.text[:200]}"
                )
                return False
            return True
        except Exception as e:
            logger.warning(f"[TELEGRAM-BOT] channel post hatası: {e}")
            return False

    def post_signals(self, ctx: PipelineContext) -> int:
        """Tüm actionable sinyalleri kanala post et. Posted count döner."""
        actionable = [s for s in ctx.signals if s.is_actionable]
        if not actionable:
            logger.info(f"[TELEGRAM-BOT] no actionable signals for {self.channel}")
            return 0

        currency = ctx.adapter.currency
        market = ctx.adapter.name.upper()

        # Header post
        header = (
            f"📊 *{market} {ctx.mode.replace('_', ' ').title()}* — "
            f"{ctx.started_at.strftime('%Y-%m-%d %H:%M UTC')}\n"
            f"Run: `{ctx.run_id}` | {len(actionable)} actionable signals\n"
            f"VIX: {ctx.regime.vix or 'N/A'} | Fear: {ctx.regime.fear_level if ctx.regime else 'N/A'}"
        )
        self.post_to_channel(header)

        # Bireysel sinyaller
        posted = 0
        for sig in actionable:
            msg = format_signal_for_telegram(sig, currency=currency)
            if self.post_to_channel(msg):
                posted += 1

        logger.info(
            f"[TELEGRAM-BOT] posted {posted}/{len(actionable)} signals to {self.channel}"
        )
        return posted


def get_alert_target(market: str) -> TelegramBot | TelegramStub:
    """Token varsa gerçek bot, yoksa stub döner."""
    if settings.telegram_bot_token:
        bot = TelegramBot(market=market)
        if bot.is_available():
            return bot
    return TelegramStub(channel=f"@{market}_signals")


__all__ = ["TelegramBot", "get_alert_target"]
