"""Tests for the sector gate (Faz B.2).

Default: pure unit tests (no API, free) over weight/filter/veto/off modes.
--live: also run a real macro→sector call (~$0.02) and show the gate reshaping
        a handful of universe symbols' confidences.

Usage:
    python scripts/test_sector_gate.py
    python scripts/test_sector_gate.py --live
"""
from __future__ import annotations

import argparse

from finllm.llm.macro_sector import MacroSectorAnalysis, SectorAppetite
from finllm.portfolio.sector_gate import (
    SectorGateConfig,
    apply_sector_gate,
    build_sector_map,
    normalize_sector,
    weight_factor,
)


def unit_tests() -> int:
    A = MacroSectorAnalysis(
        overall_stance="risk_on", macro_summary="test",
        sectors=[SectorAppetite("Technology", 0.8, ""), SectorAppetite("Energy", 0.3, ""),
                 SectorAppetite("Financials", 0.5, "")],
    )
    A_off = MacroSectorAnalysis(
        overall_stance="risk_off", macro_summary="",
        sectors=[SectorAppetite("Technology", 0.6, "")],
    )
    cases = [
        ("normalize Financial", normalize_sector("Financial") == "Financials"),
        ("normalize Healthcare", normalize_sector("Healthcare") == "Health Care"),
        ("normalize Consumer Defensive", normalize_sector("Consumer Defensive") == "Consumer Staples"),
        ("wf neutral=1.0", abs(weight_factor(0.5, 1.0) - 1.0) < 1e-9),
        ("wf hot=1.3", abs(weight_factor(0.8, 1.0) - 1.3) < 1e-9),
        ("wf cold=0.8", abs(weight_factor(0.3, 1.0) - 0.8) < 1e-9),
        ("weight tech 0.6→0.78", apply_sector_gate(0.6, "Technology", A).adjusted_confidence == 0.78),
        ("weight energy 0.6→0.48", abs(apply_sector_gate(0.6, "Energy", A).adjusted_confidence - 0.48) < 1e-6),
        ("weight caps at 1.0", apply_sector_gate(0.95, "Technology", A).adjusted_confidence <= 1.0),
        ("filter energy drops", not apply_sector_gate(0.6, "Energy", A, SectorGateConfig(mode="filter")).keep),
        ("filter tech keeps", apply_sector_gate(0.6, "Technology", A, SectorGateConfig(mode="filter")).keep),
        ("veto risk_off blocks", not apply_sector_gate(0.9, "Technology", A_off, SectorGateConfig(mode="veto")).keep),
        ("off passthrough", apply_sector_gate(0.6, "Energy", A, SectorGateConfig(mode="off")).adjusted_confidence == 0.6),
        ("None analysis passthrough", apply_sector_gate(0.6, "Energy", None).adjusted_confidence == 0.6),
        ("unknown sector neutral", abs(apply_sector_gate(0.6, "Utilities", A).adjusted_confidence - 0.6) < 1e-6),
        ("sector map AAPL=Technology", build_sector_map().get("AAPL") == "Technology"),
    ]
    passed = sum(1 for _, ok in cases if ok)
    for name, ok in cases:
        print(("  ok   " if ok else "  FAIL ") + name)
    print(f"\n{passed}/{len(cases)} passed")
    return 0 if passed == len(cases) else 1


def live_demo() -> None:
    from finllm.data.macro import build_macro_context
    from finllm.llm.macro_sector import MacroSectorClient

    ctx = build_macro_context(with_news=True, news_limit=10)
    res = MacroSectorClient().analyze(ctx)
    sm = build_sector_map()
    print(f"\nLIVE — stance: {res.overall_stance}  (cost ${res.cost_usd:.5f})")
    print(f"{'Symbol':8}{'Sector':24}{'Appetite':>9}{'Conf 0.60→':>12}")
    print("-" * 55)
    for sym in ["NVDA", "AAPL", "AMZN", "JPM", "XOM", "META", "CAT"]:
        sec = sm.get(sym, "?")
        g = apply_sector_gate(0.60, sec, res)
        arrow = "↑" if g.adjusted_confidence > 0.6 else ("↓" if g.adjusted_confidence < 0.6 else "=")
        print(f"{sym:8}{sec:24}{g.appetite:>9.2f}{g.adjusted_confidence:>11.2f} {arrow}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="also run a real macro call (~$0.02)")
    args = ap.parse_args()
    rc = unit_tests()
    if args.live:
        live_demo()
    raise SystemExit(rc)


if __name__ == "__main__":
    main()
