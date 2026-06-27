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
from finllm.pipeline.decision_panel import CandidateInput, run_decision_panel

console = Console()

DEFAULTS = {
    "nasdaq": "AAPL,NVDA,XOM,MU,JPM,AMD,META,CAT,AMZN,AVGO",
    "bist": "THYAO.IS,GARAN.IS,ASELS.IS,AKBNK.IS,KCHOL.IS,EREGL.IS,BIMAS.IS,SISE.IS,TUPRS.IS,FROTO.IS",
}


def build_tmap(market: str) -> dict:
    """symbol → Ticker. BIST keyed by the yahoo '.IS' symbol the data layer uses."""
    if market == "bist":
        from finllm.markets.universes.bist_100 import BIST_100_TICKERS
        return {f"{t.symbol}.IS": t for t in BIST_100_TICKERS}
    from finllm.markets.universes.nasdaq import NASDAQ_ALL
    return {t.symbol: t for t in NASDAQ_ALL}


def _setup_and_momentum(symbol: str, thresholds) -> tuple[float | None, float | None]:
    """Technical setup score + 12-1m momentum from one cached price fetch."""
    from finllm.backtest.strategy_signals import MIN_BARS, strategy_signal
    from finllm.indicators.momentum import momentum_12_1
    try:
        p = fetch_prices(symbol, start="2023-06-01", use_cache=True)
    except Exception:
        return None, None
    if p.empty or len(p) < MIN_BARS:
        return None, None
    sig = strategy_signal(symbol, p, datetime.utcnow(), thresholds, min_setup_score=0.0)
    setup = sig.signals.technical.score if sig else None
    return setup, momentum_12_1(p)


def main() -> None:
    ap = argparse.ArgumentParser(description="End-to-end decision panel")
    ap.add_argument("--market", choices=["nasdaq", "bist"], default="nasdaq")
    ap.add_argument("--symbols", default=None, help="comma list; defaults per market")
    ap.add_argument(
        "--universe", default=None,
        help="adlı evren (ör. 'bist' = düzenlenebilir data/universes/bist100.json). "
             "Verilirse --symbols yerine geçer. Liste uzunsa ilk çalıştırma yavaştır.",
    )
    ap.add_argument("--top-n", type=int, default=4)
    ap.add_argument("--no-debate", action="store_true")
    ap.add_argument("--no-macro", action="store_true")
    ap.add_argument("--export", action="store_true",
                    help="write the panel as signals_<market>.json for the dashboard API")
    args = ap.parse_args()

    market = args.market
    tmap = build_tmap(market)
    if args.universe:
        from finllm.backtest.universe import resolve
        symbols = resolve(args.universe)
        console.print(f"[dim]Evren '{args.universe}': {len(symbols)} sembol[/dim]")
    else:
        symbols = [s.strip().upper() for s in (args.symbols or DEFAULTS[market]).split(",") if s.strip()]
    thresholds = get_adapter(market).thresholds

    # 1) assemble candidate inputs (real setups + fundamentals + finnhub)
    console.print(f"[dim]Assembling {market} candidates (setups + fundamentals + Finnhub, free)…[/dim]")
    inputs: list[CandidateInput] = []
    for sym in symbols:
        t = tmap.get(sym)
        if t is None:
            continue
        setup, mom = _setup_and_momentum(sym, thresholds)
        snap = fetch_fundamentals(t, sym, use_cache=True)
        fh = fetch_finnhub_signals(sym) if market == "nasdaq" else None  # Finnhub US-only
        inputs.append(CandidateInput(symbol=sym, setup_score=setup or 0.0, snap=snap, finnhub=fh, momentum=mom))

    # BIST enrichment: relative (percentile) scoring instead of US benchmarks +
    # KAP/Turkish news for the debate.
    if market == "bist":
        from finllm.data.kap import fetch_kap
        from finllm.data.news.bist_stock_news import fetch_bist_stock_news
        from finllm.data.news.rss_reader import RssReader
        from finllm.indicators.relative_score import relative_composites, to_risk_reward
        console.print("[dim]BIST: göreli skorlama + KAP/haber…[/dim]")
        snaps = {i.symbol: i.snap for i in inputs if i.snap is not None}
        rel = relative_composites(snaps) if snaps else {}
        feed = RssReader(market="bist").fetch(max_age_hours=120, limit=120)
        for i in inputs:
            if i.symbol in rel:
                i.rr = to_risk_reward(rel[i.symbol])
            rss = [n.title for n in fetch_bist_stock_news(i.symbol, _feed=feed)]
            kap = fetch_kap(i.symbol).disclosures
            i.news = (rss + kap)[:6]

    # 2) macro view (1 call) unless disabled
    macro = None
    if not args.no_macro:
        from finllm.data.macro import build_macro_context
        from finllm.llm.macro_sector import MacroSectorClient
        console.print("[dim]Macro→sector (Sonnet, ~$0.02)…[/dim]")
        macro = MacroSectorClient().analyze(build_macro_context(market=market, with_news=True, news_limit=10))
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

    # 7) export for the dashboard API (DATA_DIR/out/signals_nasdaq_*.json)
    if args.export:
        from finllm.api.panel_serialize import panel_to_response, write_signals_file
        from finllm.data.commodities import fetch_commodities
        from finllm.portfolio.construction import construct_portfolio
        port = construct_portfolio(result.decisions) if result.actionable() else None
        commodities = fetch_commodities()
        payload = panel_to_response(
            result, port, market=market,
            macro_stance=(macro.overall_stance if macro else ""), macro=macro,
            commodities=commodities,
        )
        path = write_signals_file(payload, market)
        console.print(f"[green]Exported[/green] {len(payload['signals'])} signals → {path}")


if __name__ == "__main__":
    main()
