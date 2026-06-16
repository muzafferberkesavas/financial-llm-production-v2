"""Isotonic confidence calibration from backtest outcomes (signal research #3).

The backtest revealed the strategy's raw setup-score confidence is MIS-calibrated
and even inverted at the top (0.9-1.0 confidence wins LESS than 0.6-0.7). Mapping
raw confidence → actual win probability (a monotonic isotonic fit via Pool Adjacent
Violators) corrects this with no sklearn dependency.

Fit once on backtest closed trades; the panel applies calibrate() to turn a raw
confidence into a calibrated probability (the dashboard's calibrated_probability).
"""
from __future__ import annotations

import json
from pathlib import Path

from finllm.config.settings import DATA_DIR

_MODEL = DATA_DIR / "calibration" / "reliability.json"


def _pav(ys: list[float]) -> list[float]:
    """Pool Adjacent Violators → monotonic non-decreasing fit of ys."""
    # blocks of (sum, count); merge while a block mean exceeds the next
    blocks: list[list[float]] = [[y, 1.0] for y in ys]
    i = 0
    while i < len(blocks) - 1:
        if blocks[i][0] / blocks[i][1] > blocks[i + 1][0] / blocks[i + 1][1]:
            blocks[i][0] += blocks[i + 1][0]
            blocks[i][1] += blocks[i + 1][1]
            del blocks[i + 1]
            if i > 0:
                i -= 1
        else:
            i += 1
    out: list[float] = []
    for s, c in blocks:
        out.extend([s / c] * int(c))
    return out


def fit_isotonic(pairs: list[tuple[float, int]]) -> dict:
    """pairs = [(confidence, win∈{0,1})]; returns a calibration {xs, ys} map."""
    pairs = sorted(pairs, key=lambda p: p[0])
    xs = [p[0] for p in pairs]
    cal = _pav([float(p[1]) for p in pairs])
    # compress to unique x knots (mean calibrated prob per x)
    knots: dict[float, list[float]] = {}
    for x, y in zip(xs, cal):
        knots.setdefault(round(x, 4), []).append(y)
    kx = sorted(knots)
    ky = [sum(knots[x]) / len(knots[x]) for x in kx]
    return {"xs": kx, "ys": ky, "n": len(pairs)}


class Reliability:
    def __init__(self, xs: list[float] | None = None, ys: list[float] | None = None, n: int = 0):
        self.xs, self.ys, self.n = xs or [], ys or [], n

    @property
    def is_trained(self) -> bool:
        return len(self.xs) >= 2

    def calibrate(self, confidence: float) -> float:
        """Raw confidence → calibrated win probability (linear interp; identity if untrained)."""
        if not self.is_trained:
            return confidence
        xs, ys = self.xs, self.ys
        if confidence <= xs[0]:
            return ys[0]
        if confidence >= xs[-1]:
            return ys[-1]
        for i in range(len(xs) - 1):
            if xs[i] <= confidence <= xs[i + 1]:
                t = (confidence - xs[i]) / (xs[i + 1] - xs[i]) if xs[i + 1] > xs[i] else 0
                return ys[i] + t * (ys[i + 1] - ys[i])
        return confidence

    def save(self, path: Path | None = None) -> None:
        path = path or _MODEL
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"xs": self.xs, "ys": self.ys, "n": self.n}, indent=2))

    @classmethod
    def load(cls, path: Path | None = None) -> "Reliability":
        path = path or _MODEL
        if not path.exists():
            return cls()
        try:
            d = json.loads(path.read_text())
            return cls(d.get("xs"), d.get("ys"), d.get("n", 0))
        except Exception:  # noqa: BLE001
            return cls()


__all__ = ["fit_isotonic", "Reliability"]
