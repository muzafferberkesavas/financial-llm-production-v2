"""Telegram DM bot — long-running process. Kullanıcı /signal, /portfolio vs. çalıştırır.

Usage:
    export TELEGRAM_BOT_TOKEN=...
    python scripts/telegram_dm_bot.py

Çalışır durumdaysa @BotFather'da kayıtlı bot'a DM atılıp komutlar denenir.
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(name)s — %(message)s")


def main() -> None:
    from finllm.alerts.telegram_dm import run_dm_bot

    asyncio.run(run_dm_bot())


if __name__ == "__main__":
    main()
