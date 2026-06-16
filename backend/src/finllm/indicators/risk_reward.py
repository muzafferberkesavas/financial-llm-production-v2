"""Medium-term Risk/Reward fusion score.

The user's goal is "optimal risk/getiri oranının en optimal olduğu hisseler" —
medium-term holds with the best risk-adjusted upside. The pieces already exist
(technical setup, sector-relative fundamental score, macro→sector appetite); this
module FUSES them into one rankable score:

  reward  (0-100) — upside potential: value headroom + growth + PEG
  risk    (0-100, higher = worse) — downside/fragility: leverage, cash burn,
            liquidity, unprofitability, imminent-earnings event risk
  quality (strong/ok/weak) — medium-term durability (ROE, margins)
  composite (0-100) — reward, lifted by quality + macro tailwind, cut by risk

Pure function over already-fetched data — no network, no LLM, no look-ahead
beyond whatever the snapshot already carries (so use point-in-time fundamentals
for backtests).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from finllm.data.finnhub_fundamentals import FinnhubSignals
from finllm.indicators.fundamentals import FundamentalScore, compute_fundamental_score
from finllm.markets.base import FundamentalSnapshot


@dataclass(slots=True)
class RiskRewardScore:
    reward: float = 50.0          # 0-100 upside potential
    risk: float = 0.0             # 0-100 downside/fragility (higher worse)
    quality_flag: str = "ok"      # strong | ok | weak
    composite: float = 50.0       # 0-100 final rankable medium-term score
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "reward": round(self.reward, 1),
            "risk": round(self.risk, 1),
            "quality": self.quality_flag,
            "composite": round(self.composite, 1),
            "notes": self.notes,
        }


def _reward(snap: FundamentalSnapshot, fs: FundamentalScore, notes: list[str]) -> float:
    # Base: value (cheapness) + growth, each already sector-relative.
    base = (fs.value_score + fs.growth_score) / 70.0 * 100.0  # 0-100
    peg = snap.peg_ratio
    if peg and 0 < peg < 1.0:
        base = min(100.0, base + 10.0)
        notes.append(f"PEG {peg:.2f}<1 (cheap growth)")
    elif peg and peg > 2.5:
        base = max(0.0, base - 8.0)
        notes.append(f"PEG {peg:.2f}>2.5 (rich vs growth)")
    # Forward P/E below trailing → improving earnings → upside
    if snap.pe_ratio and snap.forward_pe and 0 < snap.forward_pe < snap.pe_ratio:
        base = min(100.0, base + 5.0)
        notes.append("forward P/E < trailing (earnings improving)")
    return max(0.0, min(100.0, base))


def _risk(snap: FundamentalSnapshot, fs: FundamentalScore, notes: list[str]) -> float:
    risk = 0.0
    de = snap.debt_to_equity  # yfinance: ~150 means 1.5x
    if de is not None:
        if de > 300:
            risk += 30; notes.append(f"very high leverage (D/E {de:.0f})")
        elif de > 150:
            risk += 18; notes.append(f"high leverage (D/E {de:.0f})")
        elif de > 80:
            risk += 8
    if snap.free_cash_flow is not None and snap.free_cash_flow < 0:
        risk += 18; notes.append("negative free cash flow")
    if snap.current_ratio is not None and snap.current_ratio < 1.0:
        risk += 12; notes.append(f"current ratio {snap.current_ratio:.2f}<1 (liquidity)")
    if snap.pe_ratio is not None and snap.pe_ratio <= 0:
        risk += 15; notes.append("unprofitable (negative P/E)")
    if snap.profit_margin is not None and snap.profit_margin < 0:
        risk += 10; notes.append("negative profit margin")
    if fs.earnings_warning:
        risk += 12; notes.append("earnings within 5d (event risk)")
    return max(0.0, min(100.0, risk))


def _quality(fs: FundamentalScore) -> str:
    if fs.quality_score >= 22:
        return "strong"
    if fs.quality_score >= 12:
        return "ok"
    return "weak"


_QUALITY_MULT = {"strong": 1.15, "ok": 1.0, "weak": 0.82}


def _apply_finnhub(fh: FinnhubSignals, reward: float, risk: float, notes: list[str]) -> tuple[float, float]:
    """Earnings-surprise momentum + PEAD drift + analyst consensus nudge reward/risk."""
    from finllm.indicators.pead import pead_label, pead_score

    if fh.earnings_momentum == "beating" and (fh.avg_surprise_pct or 0) > 0:
        reward = min(100.0, reward + 8.0)
        notes.append(f"earnings beating ({fh.beat_streak}Q streak, avg +{fh.avg_surprise_pct:.1f}%)")
    elif fh.earnings_momentum == "missing":
        risk = min(100.0, risk + 12.0)
        notes.append(f"earnings missing (avg {fh.avg_surprise_pct:+.1f}%)")

    # PEAD: active drift in the window right after the print (research-validated).
    pead = pead_score(fh)
    lab = pead_label(pead)
    if lab == "drift-up":
        reward = min(100.0, reward + (pead - 50) / 50 * 10)
        notes.append(f"PEAD drift-up (surprise {fh.last_surprise_pct:+.1f}%, recent print)")
    elif lab == "drift-down":
        risk = min(100.0, risk + (50 - pead) / 50 * 10)
        notes.append(f"PEAD drift-down (surprise {fh.last_surprise_pct:+.1f}%, recent print)")
    if fh.analyst_label == "bullish":
        reward = min(100.0, reward + 5.0)
        notes.append(f"analyst bullish ({fh.analyst_score:.2f}, n={fh.n_analysts})")
    elif fh.analyst_label == "bearish":
        risk = min(100.0, risk + 6.0)
        notes.append(f"analyst bearish ({fh.analyst_score:.2f})")
    return reward, risk


def score_risk_reward(
    snap: FundamentalSnapshot | None,
    fund_score: FundamentalScore | None = None,
    sector_appetite: float = 0.5,
    finnhub: FinnhubSignals | None = None,
) -> RiskRewardScore:
    """Fuse fundamentals + earnings/analyst signals + macro appetite into a
    medium-term risk/reward score.

    sector_appetite (0-1, 0.5 neutral) is the macro→sector tailwind from Faz B.
    finnhub adds earnings-surprise momentum + analyst consensus (free signals).
    """
    if snap is None:
        return RiskRewardScore(notes=["no fundamentals"])
    fs = fund_score or compute_fundamental_score(snap)

    notes: list[str] = []
    reward = _reward(snap, fs, notes)
    risk = _risk(snap, fs, notes)
    quality = _quality(fs)

    if finnhub is not None:
        reward, risk = _apply_finnhub(finnhub, reward, risk, notes)

    # Composite: reward, lifted by quality + macro tailwind, cut by fragility.
    macro_mult = 0.5 + sector_appetite               # [0.5, 1.5]
    composite = reward * _QUALITY_MULT[quality] * macro_mult * (1.0 - risk / 200.0)
    composite = max(0.0, min(100.0, composite))

    return RiskRewardScore(
        reward=reward, risk=risk, quality_flag=quality,
        composite=composite, notes=notes,
    )


__all__ = ["RiskRewardScore", "score_risk_reward"]
