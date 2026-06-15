"""Unit tests for the medium-term risk/reward fusion score (no API, free)."""
from __future__ import annotations

from finllm.indicators.risk_reward import score_risk_reward
from finllm.markets.base import FundamentalSnapshot, Ticker


def _snap(**kw):
    t = Ticker("X", "nasdaq", sector=kw.pop("sector", "Technology"))
    return FundamentalSnapshot(ticker=t, **kw)


def main() -> None:
    A = _snap(pe_ratio=18, forward_pe=15, pb_ratio=4, peg_ratio=0.8, roe=0.30,
              profit_margin=0.25, revenue_growth_yoy=0.20, earnings_growth_yoy=0.25,
              debt_to_equity=30, current_ratio=2.5, free_cash_flow=5e9)
    B = _snap(pe_ratio=-5, pb_ratio=8, roe=-0.10, profit_margin=-0.08,
              revenue_growth_yoy=0.40, debt_to_equity=350, current_ratio=0.7, free_cash_flow=-2e9)
    C = _snap(pe_ratio=22, forward_pe=21, pb_ratio=5, peg_ratio=1.8, roe=0.16,
              profit_margin=0.12, revenue_growth_yoy=0.08, earnings_growth_yoy=0.09,
              debt_to_equity=90, current_ratio=1.3, free_cash_flow=1e9)

    a, b, c = score_risk_reward(A), score_risk_reward(B), score_risk_reward(C)
    cases = [
        ("A high reward", a.reward >= 70),
        ("A zero/low risk", a.risk <= 10),
        ("A strong quality", a.quality_flag == "strong"),
        ("B high risk", b.risk >= 60),
        ("B weak quality", b.quality_flag == "weak"),
        ("B low composite", b.composite < 20),
        ("ranking A>C>B", a.composite > c.composite > b.composite),
        ("macro tailwind lifts A", score_risk_reward(A, sector_appetite=0.8).composite >= a.composite),
        ("macro headwind cuts A", score_risk_reward(A, sector_appetite=0.2).composite < a.composite),
        ("None → safe default", score_risk_reward(None).composite == 50.0),
        ("B notes cite leverage", any("leverage" in n for n in b.notes)),
    ]
    passed = sum(1 for _, ok in cases if ok)
    for name, ok in cases:
        print(("  ok   " if ok else "  FAIL ") + name)
    print(f"\n{passed}/{len(cases)} passed")
    raise SystemExit(0 if passed == len(cases) else 1)


if __name__ == "__main__":
    main()
