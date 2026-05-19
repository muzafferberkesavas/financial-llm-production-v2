"""Telegram DM handler — aiogram private DM bot (long-running process).

Komutlar:
  /start             — Bot tanıtımı + komut listesi
  /signal AAPL        — AAPL için son sinyali göster (out/ JSON'dan)
  /signal nasdaq      — En son NASDAQ run'undaki tüm sinyalleri
  /portfolio          — Aktif portföy (allocation_cash > 0)
  /watchlist add AAPL — Watchlist'e ekle
  /watchlist          — Watchlist'i göster
  /status             — Sistem durumu (son run zamanı, signal sayıları)
  /help               — Komut listesi

Watchlist Phase 2.3'te basit JSON dosyada saklanır; Phase 2.5'te Postgres.
"""
from __future__ import annotations

import asyncio
import glob
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from finllm.alerts.telegram_stub import format_signal_for_telegram
from finllm.config.settings import settings, DATA_DIR
from finllm.utils.logging import logger


_WATCHLIST_FILE = DATA_DIR / "telegram_watchlists.json"
_OUTPUT_DIR = DATA_DIR / "out"


def _load_watchlists() -> dict[str, list[str]]:
    if not _WATCHLIST_FILE.exists():
        return {}
    try:
        return json.loads(_WATCHLIST_FILE.read_text())
    except Exception:
        return {}


def _save_watchlists(data: dict[str, list[str]]) -> None:
    _WATCHLIST_FILE.parent.mkdir(parents=True, exist_ok=True)
    _WATCHLIST_FILE.write_text(json.dumps(data, indent=2))


def _latest_signals(market: str | None = None) -> dict | None:
    """En son run'un JSON output'unu yükle. market verilmezse tüm market'lerden son."""
    pattern = f"signals_{market}_*.json" if market else "signals_*.json"
    files = sorted(_OUTPUT_DIR.glob(pattern))
    if not files:
        return None
    return json.loads(files[-1].read_text())


def _find_signal(ticker: str) -> tuple[dict, dict] | None:
    """En son JSON'larda ticker'ı ara. (summary, signal_dict) döner."""
    files = sorted(_OUTPUT_DIR.glob("signals_*.json"), reverse=True)
    for f in files[:10]:
        try:
            data = json.loads(f.read_text())
            for sig in data["signals"]:
                if sig["ticker"].upper() == ticker.upper():
                    return data["summary"], sig
        except Exception:
            continue
    return None


def build_dispatcher() -> Dispatcher:
    """aiogram Dispatcher with all handlers."""
    dp = Dispatcher()

    @dp.message(Command("start"))
    async def cmd_start(message: Message) -> None:
        await message.answer(
            "🤖 *FinLLM Cross-Market Bot*\n\n"
            "Türk ve ABD borsasında AI destekli swing-trade sinyalleri.\n\n"
            "Komutlar:\n"
            "/signal <ticker> — Bir hisse için son sinyali göster\n"
            "/portfolio — Aktif portföy\n"
            "/watchlist — Watchlist görüntüle\n"
            "/watchlist add AAPL — Watchlist'e ekle\n"
            "/watchlist del AAPL — Watchlist'ten çıkar\n"
            "/status — Sistem durumu\n\n"
            "Kanal: @nasdaq\\_signals, @bist\\_signals\n"
            "⚠️ Bu sistem yatırım tavsiyesi vermez; bilgilendirme amaçlıdır.",
            parse_mode="Markdown",
        )

    @dp.message(Command("help"))
    async def cmd_help(message: Message) -> None:
        await cmd_start(message)

    @dp.message(Command("signal"))
    async def cmd_signal(message: Message, command: CommandObject) -> None:
        if not command.args:
            await message.answer(
                "Kullanım: `/signal AAPL` veya `/signal nasdaq`",
                parse_mode="Markdown",
            )
            return

        arg = command.args.strip().upper()

        # Market mi?
        if arg.lower() in ("nasdaq", "bist"):
            data = _latest_signals(market=arg.lower())
            if not data:
                await message.answer(f"{arg} için henüz sinyal yok.")
                return
            summary = data["summary"]
            actionable = [s for s in data["signals"] if s["is_actionable"]]
            if not actionable:
                await message.answer(
                    f"📊 {arg.upper()} — son run\n"
                    f"Run: {summary['run_id']}\n"
                    f"⚠️ Actionable sinyal yok ({summary['signals_generated']} taranan)"
                )
                return

            text = f"📊 *{arg.upper()}* — son run\n_{summary['started_at']}_\n\n"
            for s in actionable[:5]:
                ret_str = f"+{s['expected_return_pct']:.1f}%" if s.get("expected_return_pct") else "-"
                text += (
                    f"• *{s['ticker']}* {s['signal']} "
                    f"(conf {s['confidence']:.2f}, exp {ret_str})\n"
                )
            await message.answer(text, parse_mode="Markdown")
            return

        # Tek ticker
        found = _find_signal(arg)
        if not found:
            await message.answer(f"❌ {arg} son 10 run'da bulunamadı.")
            return

        summary, sig = found
        # ticker dict → ExtendedSignal-ish formatlama için legacy stub'ı kullan
        # Manuel format
        rationale = sig.get("rationale", {})
        text = (
            f"*{sig['signal']}* — *{sig['ticker']}* ({sig.get('name', '')})\n"
            f"_{summary['market']} run {summary['run_id']}_\n\n"
            f"Confidence: *{sig['confidence']:.2f}*\n"
            f"Regime: {sig.get('market_regime', '-')} | Weekly: {sig.get('weekly_trend', '-')}\n"
        )
        if sig.get("expected_return_pct"):
            text += f"Expected Return: *{sig['expected_return_pct']:+.1f}%* in {sig.get('time_horizon_days', '?')}d\n"
        if sig.get("allocation_cash", 0) > 0:
            text += f"Allocation: ${sig['allocation_cash']:,.0f} ({sig['allocation_weight']:.1%})\n"
        if sig.get("entry_zone_low"):
            text += f"Entry: [${sig['entry_zone_low']:.2f}-${sig['entry_zone_high']:.2f}]\n"
        if sig.get("stop_loss"):
            text += f"Stop Loss: ${sig['stop_loss']:.2f}\n"
        if sig.get("scenarios"):
            text += "\nScenarios:\n"
            for sc in sig["scenarios"]:
                text += (
                    f"  • {sc['label']}: ${sc['target_price']:.2f} "
                    f"({sc['probability']:.0%}, {sc['expected_return_pct']:+.1f}%)\n"
                )
        if rationale.get("full"):
            text += f"\n_Analysis:_ {rationale['full'][:400]}"
        if sig.get("warning_flags"):
            text += f"\n\n⚠️ {', '.join(sig['warning_flags'][:5])}"
        await message.answer(text, parse_mode="Markdown")

    @dp.message(Command("portfolio"))
    async def cmd_portfolio(message: Message) -> None:
        for market in ["nasdaq", "bist"]:
            data = _latest_signals(market=market)
            if not data:
                continue
            allocated = [s for s in data["signals"] if s.get("allocation_cash", 0) > 0]
            if not allocated:
                continue

            text = f"📊 *{market.upper()} Portfolio* — {data['summary']['started_at']}\n\n"
            total = 0
            for s in allocated:
                text += (
                    f"• *{s['ticker']}*: ${s['allocation_cash']:,.0f} "
                    f"({s['allocation_weight']:.1%}) "
                    f"{s['signal']}\n"
                )
                total += s["allocation_cash"]
            text += f"\n*Total:* ${total:,.0f} / ${data['summary']['total_capital']:,.0f}"
            await message.answer(text, parse_mode="Markdown")

    @dp.message(Command("watchlist"))
    async def cmd_watchlist(message: Message, command: CommandObject) -> None:
        user_id = str(message.from_user.id)
        lists = _load_watchlists()
        user_list = lists.get(user_id, [])

        if not command.args:
            if not user_list:
                await message.answer(
                    "Watchlist boş. Eklemek için: `/watchlist add AAPL`",
                    parse_mode="Markdown",
                )
                return
            text = "*Watchlist:*\n" + "\n".join(f"• `{t}`" for t in user_list)
            await message.answer(text, parse_mode="Markdown")
            return

        parts = command.args.strip().split()
        if len(parts) < 2:
            await message.answer(
                "Kullanım: `/watchlist add AAPL` veya `/watchlist del AAPL`",
                parse_mode="Markdown",
            )
            return

        action, ticker = parts[0].lower(), parts[1].upper()
        if action == "add":
            if ticker not in user_list:
                user_list.append(ticker)
                lists[user_id] = user_list
                _save_watchlists(lists)
                await message.answer(f"✓ {ticker} watchlist'e eklendi")
            else:
                await message.answer(f"{ticker} zaten watchlist'te")
        elif action in ("del", "remove", "rm"):
            if ticker in user_list:
                user_list.remove(ticker)
                lists[user_id] = user_list
                _save_watchlists(lists)
                await message.answer(f"✓ {ticker} watchlist'ten çıkarıldı")
            else:
                await message.answer(f"{ticker} watchlist'te yok")
        else:
            await message.answer(f"Bilinmeyen action: {action}")

    @dp.message(Command("status"))
    async def cmd_status(message: Message) -> None:
        files = sorted(_OUTPUT_DIR.glob("signals_*.json"), reverse=True)
        if not files:
            await message.answer("📊 Henüz hiç run yapılmamış.")
            return

        text = "*FinLLM Status:*\n\n"
        seen_markets = set()
        for f in files[:10]:
            try:
                data = json.loads(f.read_text())
                m = data["summary"]["market"]
                if m in seen_markets:
                    continue
                seen_markets.add(m)
                summary = data["summary"]
                actionable = sum(
                    1 for s in data["signals"] if s.get("is_actionable")
                )
                text += (
                    f"*{m.upper()}* — {summary['started_at'][:16]}\n"
                    f"  Universe: {summary['universe_size']}\n"
                    f"  Filter pass: {summary['passed_hard_filter']}\n"
                    f"  Signals: {summary['signals_generated']} ({actionable} actionable)\n"
                    f"  Cost: ${summary['total_cost_usd']:.2f}\n\n"
                )
            except Exception:
                continue
        await message.answer(text, parse_mode="Markdown")

    return dp


async def run_dm_bot() -> None:
    """Long-running DM handler — `python -m scripts.telegram_dm_bot` ile başlatılır."""
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN env'de yok")

    bot = Bot(token=settings.telegram_bot_token)
    dp = build_dispatcher()
    logger.info("[TELEGRAM-DM] starting polling...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


__all__ = ["build_dispatcher", "run_dm_bot"]
