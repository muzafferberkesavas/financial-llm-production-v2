"""Platt scaling — LLM confidence → realized hit probability.

Sklearn LogisticRegression ile (confidence, signal_label, regime, ...) → P(win).
Az sample (<30) varsa identity fallback (calibrated = raw confidence).

Kaydedilen model: data/calibration/platt_model.json (sklearn coef + intercept).
Phase 2'de basit, Phase 3'te per-market + per-regime ayrı modeller.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from finllm.calibration.tracker import OutcomeRecord, OutcomeTracker
from finllm.config.settings import DATA_DIR
from finllm.utils.logging import logger


_MODEL_FILE = DATA_DIR / "calibration" / "platt_model.json"
_MIN_SAMPLES_FOR_TRAINING = 30


@dataclass
class PlattCalibrator:
    """Logistic regression: P(win | features).

    Phase 2 features: [confidence, confluence_score/100, confirmation_count/6,
                       is_strong_trend (0/1), is_aligned (0/1)]
    """

    intercept: float = 0.0
    coefs: list[float] | None = None  # 5 feature
    feature_names: list[str] | None = None
    n_train: int = 0
    n_wins: int = 0
    trained_at: str = ""

    @property
    def is_trained(self) -> bool:
        return self.coefs is not None and self.n_train >= _MIN_SAMPLES_FOR_TRAINING

    def features_for(
        self,
        confidence: float,
        confluence_score: int,
        confirmation_count: int,
        market_regime: str,
        timeframe_alignment: str = "UNKNOWN",
    ) -> list[float]:
        return [
            confidence,
            confluence_score / 100.0,
            confirmation_count / 6.0,
            1.0 if market_regime in ("TREND", "STRONG_TREND") else 0.0,
            1.0 if timeframe_alignment == "ALIGNED" else 0.0,
        ]

    def predict(
        self,
        confidence: float,
        confluence_score: int,
        confirmation_count: int,
        market_regime: str,
        timeframe_alignment: str = "UNKNOWN",
    ) -> float:
        """Calibrated probability döner. Trained değilse identity (raw confidence)."""
        if not self.is_trained or not self.coefs:
            return confidence

        x = self.features_for(
            confidence, confluence_score, confirmation_count, market_regime, timeframe_alignment
        )
        z = self.intercept + sum(c * v for c, v in zip(self.coefs, x))
        try:
            return 1.0 / (1.0 + math.exp(-z))
        except OverflowError:
            return 0.0 if z < 0 else 1.0

    def save(self, path: Path | None = None) -> None:
        path = path or _MODEL_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "intercept": self.intercept,
                    "coefs": self.coefs,
                    "feature_names": self.feature_names,
                    "n_train": self.n_train,
                    "n_wins": self.n_wins,
                    "trained_at": self.trained_at,
                },
                indent=2,
            )
        )

    @classmethod
    def load(cls, path: Path | None = None) -> "PlattCalibrator":
        path = path or _MODEL_FILE
        if not path.exists():
            return cls()  # untrained
        try:
            d = json.loads(path.read_text())
            return cls(
                intercept=d["intercept"],
                coefs=d["coefs"],
                feature_names=d.get("feature_names"),
                n_train=d.get("n_train", 0),
                n_wins=d.get("n_wins", 0),
                trained_at=d.get("trained_at", ""),
            )
        except Exception as e:
            logger.warning(f"[PLATT] load fail: {e}, returning untrained")
            return cls()


def train_calibrator(
    tracker: OutcomeTracker | None = None,
    min_samples: int = _MIN_SAMPLES_FOR_TRAINING,
) -> PlattCalibrator:
    """Closed outcomes'tan Platt model eğit. sklearn LogisticRegression.

    Az sample varsa untrained PlattCalibrator döner (identity).
    """
    from datetime import datetime

    tracker = tracker or OutcomeTracker()
    closed = tracker.closed_records()

    # AL/GUCLU_AL sinyalleri (BUY-side) — şimdilik sadece bunları kalibre ediyoruz
    buy_records = [
        r for r in closed if r.signal in ("AL", "GUCLU_AL")
    ]

    if len(buy_records) < min_samples:
        logger.info(
            f"[PLATT] yetersiz sample ({len(buy_records)} < {min_samples}), "
            f"identity calibrator döndürülüyor"
        )
        return PlattCalibrator(n_train=len(buy_records))

    try:
        import numpy as np
        from sklearn.linear_model import LogisticRegression
    except ImportError:
        logger.warning("[PLATT] sklearn yok, identity calibrator")
        return PlattCalibrator(n_train=len(buy_records))

    feature_names = [
        "confidence",
        "confluence_score_norm",
        "confirmation_count_norm",
        "is_strong_trend",
        "is_aligned",
    ]
    X = []
    y = []
    for r in buy_records:
        x = [
            r.confidence,
            r.confluence_score / 100.0,
            r.confirmation_count / 6.0,
            1.0 if r.market_regime in ("TREND", "STRONG_TREND") else 0.0,
            1.0 if "ALIGNED" in r.weekly_trend else 0.0,
        ]
        X.append(x)
        y.append(1 if r.is_win else 0)

    X = np.array(X)
    y = np.array(y)

    model = LogisticRegression(C=1.0, solver="lbfgs", max_iter=200)
    model.fit(X, y)

    calibrator = PlattCalibrator(
        intercept=float(model.intercept_[0]),
        coefs=[float(c) for c in model.coef_[0]],
        feature_names=feature_names,
        n_train=len(buy_records),
        n_wins=int(y.sum()),
        trained_at=datetime.utcnow().isoformat(),
    )
    calibrator.save()
    logger.info(
        f"[PLATT] trained on n={len(buy_records)}, "
        f"wins={int(y.sum())}, hit_rate={y.mean():.2%}"
    )
    return calibrator


__all__ = ["PlattCalibrator", "train_calibrator"]
