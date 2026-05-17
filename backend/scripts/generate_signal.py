"""CLI: tek bir hisse için sinyal üret ve göster.

Kullanım:
    cd backend && python -m scripts.generate_signal AAPL
    cd backend && python -m scripts.generate_signal NVDA TSLA MSFT
"""
from __future__ import annotations

import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from finllm.signals.generator import generate_signal

console = Console()


def render(signal) -> None:
    color = {"BUY": "green", "SELL": "red", "HOLD": "yellow"}[signal.direction]
    title = f"[{color}]{signal.symbol} — {signal.direction}[/{color}] (güven {signal.confidence:.0%})"

    info = Table.grid(padding=(0, 2))
    info.add_row("Giriş", f"${signal.entryPrice:.2f}")
    if signal.targetPrice:
        info.add_row("Hedef", f"${signal.targetPrice:.2f}")
    if signal.stopLoss:
        info.add_row("Stop", f"${signal.stopLoss:.2f}")
    if signal.expectedReturn:
        info.add_row("Beklenen getiri", f"{signal.expectedReturn:+.1%}")
    info.add_row("Tutma", f"{signal.holdingDays.min}-{signal.holdingDays.max} gün")
    info.add_row("Teknik skor", f"{signal.signals.technical.score:+.2f}")
    info.add_row("Sentiment skor", f"{signal.signals.sentiment.score:+.2f}")

    body = (
        f"{info}\n\n"
        f"[bold]Gerekçe:[/bold] {signal.rationale}\n\n"
        f"[bold]Teknik:[/bold] {signal.signals.technical.notes}\n"
        f"[bold]Sentiment:[/bold] {signal.signals.sentiment.notes}\n"
    )
    if signal.riskFactors:
        body += "\n[bold yellow]Riskler:[/bold yellow]\n"
        for r in signal.riskFactors:
            body += f"  • {r}\n"

    console.print(Panel(body, title=title, border_style=color))


def main() -> int:
    symbols = sys.argv[1:] or ["AAPL"]
    for sym in symbols:
        try:
            sig = generate_signal(sym.upper())
            render(sig)
        except Exception as e:
            console.print(f"[red]{sym} hata: {e}[/red]")
            console.print_exception()
    return 0


if __name__ == "__main__":
    sys.exit(main())
