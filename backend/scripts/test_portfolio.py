"""Unit tests for portfolio construction (no API, free)."""
from __future__ import annotations

from finllm.llm.debate import DebateResult
from finllm.pipeline.decision_panel import PanelDecision
from finllm.portfolio.construction import PortfolioConfig, construct_portfolio
from finllm.signals.ranking import CandidateScore

SECTORS = {"NVDA": "Technology", "MU": "Technology", "AMD": "Technology",
           "JPM": "Financials", "XOM": "Energy", "META": "Communication Services"}


def _dec(sym, action, size, conf):
    return PanelDecision(
        candidate=CandidateScore(symbol=sym, setup_score=0.0, risk_reward=0.0,
                                 macro_appetite=0.5, quality_flag="ok", priority=0.0),
        debate=DebateResult(symbol=sym, action=action, confidence=conf, position_size_pct=size),
    )


def main() -> None:
    cfg = PortfolioConfig(max_positions=7, max_total_exposure_pct=95, max_sector_pct=40,
                          max_position_pct=25, min_position_pct=2)

    # 3 Tech @20% (60% > 40% sector cap) + JPM 10% + an IZLE (excluded)
    decs = [
        _dec("NVDA", "AL", 20, 0.70), _dec("MU", "AL", 20, 0.60), _dec("AMD", "AL", 20, 0.65),
        _dec("JPM", "AL", 10, 0.55), _dec("XOM", "IZLE", 0, 0.50),
    ]
    p = construct_portfolio(decs, cfg, sector_map=SECTORS)
    tech = p.sector_exposure.get("Technology", 0)

    # single-name cap test
    big = construct_portfolio([_dec("NVDA", "GUCLU_AL", 40, 0.9)], cfg, sector_map=SECTORS)

    # max_positions test (8 buys → 7)
    many = [_dec(f"S{i}", "AL", 5, 0.5 + i * 0.01) for i in range(8)]
    sm = {f"S{i}": f"Sec{i}" for i in range(8)}
    mp = construct_portfolio(many, cfg, sector_map=sm)

    cases = [
        ("IZLE excluded", all(pos.symbol != "XOM" for pos in p.positions)),
        ("4 positions kept", len(p.positions) == 4),
        ("Tech capped ~40%", 39 <= tech <= 41),
        ("total exposure <= 95", p.total_exposure_pct <= 95.0 + 1e-6),
        ("cash = 100 - exposure", abs(p.cash_pct - (100 - p.total_exposure_pct)) < 1e-6),
        ("single-name cap 25", big.positions[0].weight_pct <= 25.0 + 1e-6),
        ("max_positions 7", len(mp.positions) == 7),
        ("kept highest-confidence", all(pos.symbol != "S0" for pos in mp.positions)),
    ]
    passed = sum(1 for _, ok in cases if ok)
    for name, ok in cases:
        print(("  ok   " if ok else "  FAIL ") + name)
    print(f"\n{passed}/{len(cases)} passed")
    print("\nexample portfolio:", p.as_dict())
    raise SystemExit(0 if passed == len(cases) else 1)


if __name__ == "__main__":
    main()
