"""Unit tests for the unified candidate ranker (no API, free)."""
from __future__ import annotations

from finllm.indicators.risk_reward import RiskRewardScore
from finllm.signals.ranking import (
    W_RISK_REWARD,
    W_TECHNICAL,
    rank_candidates,
    score_candidate,
)


def main() -> None:
    # priority = 0.65·rr + 0.35·(setup·100)
    c = score_candidate("T", 0.8, None, sector_appetite=0.5)  # snap None → rr=50
    expected = W_RISK_REWARD * 50 + W_TECHNICAL * 80

    # strong fundamentals / weak setup vs weak fundamentals / strong setup
    strong_fund = score_candidate("F", 0.45, rr=RiskRewardScore(composite=100, quality_flag="strong"))
    strong_tech = score_candidate("Tk", 0.80, rr=RiskRewardScore(composite=37, quality_flag="ok"))
    ranked = rank_candidates([strong_tech, strong_fund])

    cases = [
        ("priority math", abs(c.priority - expected) < 1e-6),
        ("setup clamped", score_candidate("X", 1.5, None).setup_score == 1.0),
        ("priority bounded 0-100", 0 <= c.priority <= 100),
        ("fundamentals dominate medium-term", ranked[0].symbol == "F"),
        ("rank desc", ranked[0].priority >= ranked[1].priority),
        ("None snap → rr 50 baseline", abs(score_candidate("Z", 0.0, None).risk_reward - 50.0) < 1e-6),
    ]
    passed = sum(1 for _, ok in cases if ok)
    for name, ok in cases:
        print(("  ok   " if ok else "  FAIL ") + name)
    print(f"\n{passed}/{len(cases)} passed")
    raise SystemExit(0 if passed == len(cases) else 1)


if __name__ == "__main__":
    main()
