"""End-to-end decision panel — the whole stack on real tickers (Faz C wiring).

Pipeline: real technical setups (strategy) + fundamentals + Finnhub + live macro
→ unified ranking → bull/bear debate on the top-N → final verdicts.

COST: 1 macro call (~$0.02) + top_n debates (~$0.035 each). --no-debate / --no-macro
for $0. Default top-n 5 → ~$0.20.

Usage:
    python scripts/run_decision_panel.py --symbols AAPL,NVDA,XOM,MU,JPM,AMD,META,CAT --top-n 4
    python scripts/run_decision_panel.py --no-debate            # $0 ranking only
"""
from __future__ import annotations

import argparse
from datetime import datetime

from rich.console import Console
from rich.table import Table

from finllm.data.finnhub_fundamentals import fetch_finnhub_signals
from finllm.data.fundamentals import fetch_fundamentals
from finllm.data.prices import fetch_prices
from finllm.markets import get_adapter
from finllm.markets.universes.nasdaq import NASDAQ_ALL
from finllm.pipeline.decision_panel import CandidateInput, run_decision_panel

console = Console()
_TMAP = {t.symbol: t for t in NASDAQ_ALL}


def _setup_score(symbol: str, thresholds) -> float | None:
    from finllm.backtest.strategy_signals import MIN_BARS, strategy_signal
    try:
        p = fetch_prices(symbol, start="2024-01-01", use_cache=True)
    except Exception:
        return None
    if p.empty or len(p) < MIN_BARS:
        return None
    sig = strategy_signal(symbol, p, datetime.utcnow(), thresholds, min_setup_score=0.0)
    return sig.signals.technical.score if sig else None


def main() -> None:
    ap = argparse.ArgumentParser(description="End-to-end decision panel")
    ap.add_argument("--symbols", default="AAPL,NVDA,XOM,MU,JPM,AMD,META,CAT,AMZN,AVGO")
    ap.add_argument("--top-n", type=int, default=4)
    ap.add_argument("--no-debate", action="store_true")
    ap.add_argument("--no-macro", action="store_true")
    args = ap.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    thresholds = get_adapter("nasdaq").thresholds

    # 1) assemble candidate inputs (real setups + fundamentals + finnhub)
    console.print("[dim]Assembling candidates (setups + fundamentals + Finnhub, free)…[/dim]")
    inputs: list[CandidateInput] = []
    for sym in symbols:
        t = _TMAP.get(sym)
        if t is None:
            continue
        setup = _setup_score(sym, thresholds)
        snap = fetch_fundamentals(t, sym, use_cache=True)
        fh = fetch_finnhub_signals(sym)
        inputs.append(CandidateInput(symbol=sym, setup_score=setup or 0.0, snap=snap, finnhub=fh))

    # 2) macro view (1 call) unless disabled
    macro = None
    if not args.no_macro:
        from finllm.data.macro import build_macro_context
        from finllm.llm.macro_sector import MacroSectorClient
        console.print("[dim]Macro→sector (Sonnet, ~$0.02)…[/dim]")
        macro = MacroSectorClient().analyze(build_macro_context(with_news=True, news_limit=10))
        console.print(f"  stance: [yellow]{macro.overall_stance}[/yellow]")

    # 3) run the panel
    debate_client = None
    if not args.no_debate:
        from finllm.llm.debate import DebateClient
        debate_client = DebateClient()
    result = run_decision_panel(
        inputs, macro=macro, top_n=args.top_n,
        run_debate=not args.no_debate, debate_client=debate_client,
    )

    # 4) ranking table
    t = Table(title="Ranked candidates (medium-term priority)", show_header=True, header_style="bold cyan")
    for col in ("#", "Sym", "Setup", "R/R", "Macro", "Quality", "Priority"):
        t.add_column(col, justify="right" if col not in ("Sym", "Quality") else "left")
    for i, c in enumerate(result.ranked, 1):
        t.add_row(str(i), c.symbol, f"{c.setup_score:.2f}", f"{c.risk_reward:.0f}",
                  f"{c.macro_appetite:.2f}", c.quality_flag, f"{c.priority:.1f}")
    console.print(t)

    # 5) debate verdicts
    for d in result.decisions:
        v = d.debate
        if v is None:
            continue
        console.print(f"\n[bold]{v.symbol}[/bold] → [yellow]{v.action}[/yellow] "
                      f"conf {v.confidence:.2f} · size {v.position_size_pct:.1f}% · {v.time_horizon_days}d")
        console.print(f"  [green]bull:[/green] " + " | ".join(p.claim for p in v.bull_points[:2]))
        console.print(f"  [red]bear:[/red] " + " | ".join(p.claim for p in v.bear_points[:2]))
        console.print(f"  [dim]{v.rationale[:240]}…[/dim]")

    # 6) construct the portfolio from actionable verdicts (free)
    if not args.no_debate and result.actionable():
        from finllm.portfolio.construction import construct_portfolio
        port = construct_portfolio(result.decisions)
        pt = Table(title="Constructed portfolio (risk-limited)", show_header=True, header_style="bold green")
        for col in ("Symbol", "Sector", "Weight", "Action", "Conf"):
            pt.add_column(col, justify="right" if col in ("Weight", "Conf") else "left")
        for pos in port.positions:
            pt.add_row(pos.symbol, pos.sector, f"{pos.weight_pct:.1f}%", pos.action, f"{pos.confidence:.2f}")
        pt.add_row("[dim]CASH[/dim]", "", f"[dim]{port.cash_pct:.1f}%[/dim]", "", "")
        console.print()
        console.print(pt)
        console.print(f"  invested {port.total_exposure_pct:.0f}% | sectors "
                      + ", ".join(f"{k} {v:.0f}%" for k, v in port.sector_exposure.items()))
        if port.notes:
            console.print(f"  [dim]{'; '.join(port.notes)}[/dim]")

    if not args.no_debate:
        console.print(f"\n[bold]Total LLM cost:[/bold] [green]${result.total_cost_usd:.4f}[/green] "
                      f"({len(result.actionable())} actionable AL/GUCLU_AL)")


if __name__ == "__main__":
    main()
