"""Telegram channel post test — son JSON output'tan sinyalleri kanala yollar.

Usage:
    export TELEGRAM_BOT_TOKEN=...
    export TELEGRAM_CHANNEL_NASDAQ=@your_channel  # or -100xxx
    python scripts/telegram_test_post.py --market nasdaq
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

logging.basicConfig(level=logging.INFO, format="%(levelname)-7s | %(message)s")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", choices=["bist", "nasdaq"], default="nasdaq")
    args = parser.parse_args()

    from finllm.alerts.telegram_bot import TelegramBot
    from finllm.config.settings import settings

    if not settings.telegram_bot_token:
        print("❌ TELEGRAM_BOT_TOKEN env'de yok")
        print("   Kurulum:")
        print("     1. @BotFather'a /newbot, token al")
        print("     2. .env'e ekle: TELEGRAM_BOT_TOKEN=...")
        print("     3. Bot'u kanala admin ekle, .env'e TELEGRAM_CHANNEL_NASDAQ=@kanal")
        return 1

    bot = TelegramBot(market=args.market)
    if not bot.is_available():
        print(f"❌ Bot var ama TELEGRAM_CHANNEL_{args.market.upper()} ayarlanmamış")
        return 1

    # En son output'u al
    out_dir = Path(__file__).resolve().parents[1] / "data" / "out"
    files = sorted(out_dir.glob(f"signals_{args.market}_*.json"))
    if not files:
        print(f"❌ {out_dir} içinde signals_{args.market}_*.json yok")
        print("   Önce: python scripts/run_funnel.py --market", args.market)
        return 1

    data = json.loads(files[-1].read_text())
    actionable = [s for s in data["signals"] if s.get("is_actionable")]
    print(f"📂 Loaded: {files[-1].name}")
    print(f"   Actionable signals: {len(actionable)}")

    if not actionable:
        print("⚠️  No actionable signals to post")
        return 0

    summary = data["summary"]
    header = (
        f"📊 *{args.market.upper()} {summary['mode'].replace('_', ' ').title()}*\n"
        f"_{summary['started_at'][:16]}_\n"
        f"Run: `{summary['run_id']}` | {len(actionable)} signals\n"
        f"VIX: {summary['regime']['vix'] or 'N/A'} | "
        f"Fear: {summary['regime']['fear_level']}"
    )
    ok = bot.post_to_channel(header)
    print(f"   Header post: {'✓' if ok else '✗'}")

    for sig in actionable:
        text_lines = [
            f"*{sig['signal'].replace('_', ' ')}* — *{sig['ticker']}* "
            f"(conf {sig['confidence']:.2f})",
        ]
        if sig.get("expected_return_pct"):
            text_lines.append(
                f"Expected: *{sig['expected_return_pct']:+.1f}%* "
                f"in {sig.get('time_horizon_days', '?')}d"
            )
        if sig.get("allocation_cash", 0) > 0:
            text_lines.append(
                f"Allocation: ${sig['allocation_cash']:,.0f} "
                f"({sig['allocation_weight']:.1%})"
            )
        if sig.get("entry_zone_low"):
            text_lines.append(
                f"Entry: [${sig['entry_zone_low']:.2f}-${sig['entry_zone_high']:.2f}] "
                f"Stop: ${sig['stop_loss']:.2f}"
            )
        if sig["rationale"].get("full"):
            text_lines.append(f"\n_{sig['rationale']['full'][:300]}_")
        if sig.get("warning_flags"):
            text_lines.append(f"\n⚠️ {', '.join(sig['warning_flags'][:4])}")

        msg = "\n".join(text_lines)
        ok = bot.post_to_channel(msg)
        print(f"   {sig['ticker']}: {'✓' if ok else '✗'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
