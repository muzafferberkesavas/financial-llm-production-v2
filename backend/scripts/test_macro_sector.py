"""Smoke-test the macro→sector appetite layer with a REAL Sonnet 4.6 call.

Cost: ~$0.04 per run (skill prompt cached after the first call).

Usage:
    python scripts/test_macro_sector.py
"""
from __future__ import annotations

import argparse

from rich.console import Console
from rich.table import Table

from finllm.data.macro import build_macro_context
from finllm.llm.macro_sector import MacroSectorClient

console = Console()

# Sample macro context (clearly a TEST fixture — not live data). Swap in a real
# data assembler once the layer's reasoning is validated.
SAMPLE_MACRO = """\
[RATES] Fed funds 4.25%. Last meeting: HELD (3rd consecutive pause). Market prices
one 25bp CUT in Q4. 2s10s curve un-inverted (+0.3%), normalizing.
[INFLATION] CPI 2.9% YoY, cooling for 4 straight months toward the 2% target.
PCE 2.6%.
[EMPLOYMENT] Unemployment 4.1% (gently rising). NFP softening but positive.
[MARKET REGIME] S&P 500 and Nasdaq both ABOVE their 200-DMA. VIX 14 (calm).
Breadth broadening beyond mega-cap tech.
[HEADLINES] AI capex cycle still strong; semis demand robust. Oil range-bound
$70-75. No active major-power conflict, but Middle East tension elevated keeping
a geopolitical bid under gold. USD softening on rate-cut expectations.
"""


def main() -> None:
    ap = argparse.ArgumentParser(description="Macro→sector smoke test")
    ap.add_argument("--live", action="store_true", help="Use real live macro data (yfinance+RSS) instead of the sample fixture")
    args = ap.parse_args()

    if args.live:
        console.print("[dim]Assembling LIVE macro context (free: yfinance + RSS)…[/dim]")
        macro_context = build_macro_context(with_news=True, news_limit=10)
        console.print(f"[dim]{macro_context}[/dim]\n")
    else:
        macro_context = SAMPLE_MACRO

    client = MacroSectorClient()
    console.print(f"[cyan]Model:[/cyan] {client.name}\n")
    console.print("[dim]Calling Sonnet 4.6 (real API)…[/dim]")

    result = client.analyze(macro_context)

    console.print(f"\n[bold]Overall stance:[/bold] [yellow]{result.overall_stance}[/yellow]")
    console.print(f"[bold]Macro summary:[/bold] {result.macro_summary}\n")

    t = Table(title="Sector appetite", show_header=True, header_style="bold cyan")
    t.add_column("Sector")
    t.add_column("Appetite", justify="right")
    t.add_column("Driver")
    for s in sorted(result.sectors, key=lambda x: x.appetite, reverse=True):
        color = "green" if s.appetite > 0.55 else "red" if s.appetite < 0.45 else "white"
        bar = "█" * round(s.appetite * 10)
        t.add_row(s.sector, f"[{color}]{s.appetite:.2f}[/{color}] {bar}", s.rationale)
    console.print(t)

    console.print(f"\n[bold]Cost this call:[/bold] [green]${result.cost_usd:.5f}[/green]")


if __name__ == "__main__":
    main()
