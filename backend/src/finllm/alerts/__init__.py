"""Alert fanout — Telegram (Phase 2.3), FCM, WebSocket.

Token varsa gerçek bot, yoksa stub fallback.
"""
from finllm.alerts.telegram_bot import TelegramBot, get_alert_target
from finllm.alerts.telegram_stub import TelegramStub, format_signal_for_telegram

__all__ = [
    "TelegramBot",
    "TelegramStub",
    "format_signal_for_telegram",
    "get_alert_target",
]
