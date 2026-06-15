"""Measure the fundamental ranking lift (look-ahead-safe, $0 LLM).

Re-ranks the candidates competing for entry slots by a blend of technical setup
and the POINT-IN-TIME fundamental composite (quality + growth + leverage; valuation
omitted — see finnhub_pit). Compares the setup-only baseline (weight 0) against
fundamental-weighted ranking, with the 200-DMA regime gate + Midas costs on.

Free: Finnhub financials-reported (cached per symbol) + cached prices. No LLM.

Usage:
    python scripts/measure_fundamental_lift.py --weights 0,0.3,0.5
"""
from __future__ import annotations

import argparse
from datetime import datetime

from rich.console import Console
from rich.table import Table

from finllm.backtest.engine import BacktestConfig
from finllm.backtest.reports import build_metrics
from finllm.backtest.strategy_engine import StrategyBacktestEngine
from finllm.backtest.universe import resolve
from finllm.backtest.universe import BROAD_UNIVERSE
from finllm.data.finnhub_pit import fetch_pit_fundamentals
from finllm.indicators.risk_reward import score_risk_reward
from finllm.markets.base import Ticker
from finllm.markets.universes.nasdaq import NASDAQ_ALL

console = Console()
_TMAP = {t.symbol: t for t in NASDAQ_ALL}
# Broad-universe names not in NASDAQ_ALL get a Ticker built from their sector label.
for _sym, _sec in BROAD_UNIVERSE.items():
    _TMAP.setdefault(_sym, Ticker(_sym, "nasdaq", sector=_sec))


def parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d")


def make_pit_provider():
    """(symbol, as_of) → risk/reward composite (0-100), cached per (symbol, year)."""
    cache: dict[tuple[str, str], float | None] = {}

    def provider(symbol: str, as_of: str) -> float | None:
        key = (symbol, as_of[:4])  # annual fundamentals → cache by year
        if key in cache:
            return cache[key]
        t = _TMAP.get(symbol)
        comp = None
        if t is not None:
            snap = fetch_pit_fundamentals(t, symbol, as_of)
            if snap is not None:
                comp = score_risk_reward(snap, sector_appetite=0.5).composite
        cache[key] = comp
        return comp

    return provider


def main() -> None:
    ap = argparse.ArgumentParser(description="Fundamental ranking lift")
    ap.add_argument("--universe", default="nasdaq")
    ap.add_argument("--start", type=parse_date, default=parse_date("2022-01-01"))
    ap.add_argument("--end", type=parse_date, default=parse_date("2024-12-31"))
    ap.add_argument("--min-setup-score", type=float, default=0.5)
    ap.add_argument("--weights", default="0,0.3,0.5")
    args = ap.parse_args()

    symbols = resolve(args.universe)
    weights = [float(w) for w in args.weights.split(",")]
    provider = make_pit_provider()

    rows = []
    for fw in weights:
        cfg = BacktestConfig(universe=symbols, start=args.start, end=args.end)
        eng = StrategyBacktestEngine(
            cfg, min_setup_score=args.min_setup_score,
            fundamental_provider=provider if fw > 0 else None, fundamental_weight=fw,
        )
        res = eng.run()
        m = build_metrics(res)
        rows.append((fw, m, len(res.ledger.closed_trades)))
        console.print(f"  weight {fw}: return {m.total_return_pct:+.1f}%  PF {m.profit_factor:.2f}  "
                      f"Sharpe {m.sharpe:.2f}  trades {len(res.ledger.closed_trades)}")

    t = Table(title=f"Fundamental ranking lift — {args.universe} {args.start.date()}..{args.end.date()}",
              show_header=True, header_style="bold cyan")
    for col in ("Fund weight", "Return", "CAGR", "Sharpe", "PF", "MaxDD", "Trades"):
        t.add_column(col, justify="right")
    base = rows[0][1]
    for fw, m, n in rows:
        ds = f" ({m.sharpe - base.sharpe:+.2f})" if fw != rows[0][0] else ""
        t.add_row(f"{fw:.2f}", f"{m.total_return_pct:+.1f}%", f"{m.cagr_pct:+.1f}%",
                  f"{m.sharpe:.2f}{ds}",
                  f"{'∞' if m.profit_factor==float('inf') else f'{m.profit_factor:.2f}'}",
                  f"{m.max_drawdown_pct:.1f}%", str(n))
    console.print()
    console.print(t)


if __name__ == "__main__":
    main()
