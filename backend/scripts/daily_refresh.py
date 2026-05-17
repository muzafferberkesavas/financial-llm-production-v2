"""Günlük portföy refresh CLI'ı.

Kullanım:
    python -m scripts.daily_refresh --mode pre_open --universe core
    python -m scripts.daily_refresh --mode post_close --universe high_beta

Bunu launchd / cron ile günde 2x çağırırsın:
    15:00 TR (NYSE açılışından ~30dk önce)   → --mode pre_open
    23:30 TR (NYSE kapanışından sonra)        → --mode post_close
"""
from __future__ import annotations

import argparse
import sys

from rich.console import Console
from rich.table import Table

from finllm.portfolio.manager import daily_refresh, get_snapshot

console = Console()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["pre_open", "post_close", "manual"], default="manual")
    parser.add_argument("--universe", default="core", help="default | core | high_beta")
    args = parser.parse_args()

    console.rule(f"[bold]Daily refresh: {args.mode} ({args.universe})[/bold]")
    report = daily_refresh(mode=args.mode, universe=args.universe)

    summary = Table(title="Refresh özeti", show_header=False)
    summary.add_row("Mod", report.mode)
    summary.add_row("Üretilen sinyal", str(report.signals_generated))
    summary.add_row("Değerlendirilen açık pozisyon", str(report.positions_evaluated))
    summary.add_row("Yeni SELL emri", str(report.sell_orders_created))
    summary.add_row("Yeni BUY emri", str(report.buy_orders_created))
    summary.add_row("Hata", str(len(report.errors)))
    console.print(summary)

    if report.errors:
        console.print("[yellow]Hatalar:[/yellow]")
        for e in report.errors[:10]:
            console.print(f"  • {e}")

    snap = get_snapshot()
    console.rule("Portföy durumu")
    info = Table(show_header=False)
    info.add_row("Initial capital", f"${snap.initial_capital_usd:,.0f}")
    info.add_row("Deployed", f"${snap.deployed_capital_usd:,.0f}")
    info.add_row("Realized PnL", f"${snap.realized_pnl_usd:+,.2f}")
    info.add_row("Open PnL", f"${snap.open_pnl_usd:+,.2f}")
    info.add_row("Total value", f"${snap.total_value_usd:,.0f}")
    info.add_row("Açık pozisyon", str(snap.n_open))
    info.add_row("Bekleyen emir", str(snap.n_pending))
    console.print(info)

    if snap.pending_orders:
        console.rule("Bekleyen emirler (sen manuel uygula)")
        for o in snap.pending_orders:
            tag = "[green]BUY[/green]" if o.side == "BUY" else "[red]SELL[/red]"
            console.print(
                f"  {tag} {o.symbol} @ ${o.suggested_price:.2f}"
                f" — {o.weight_pct or 0:.1f}% (${o.capital_usd or 0:.0f})"
                + (f" [{o.reason_code}]" if o.reason_code else "")
            )

    return 0 if not report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
