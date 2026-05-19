"""Probability calibration — Platt scaling + Kelly sizing.

Akış:
  1. Outcome tracker (tracker.py): her sinyalin realized outcome'unu topla
  2. Calibrator (platt.py): sklearn LogisticRegression ile P(win) → calibrated_p
  3. Kelly sizer (kelly.py): position size = calibrated_p × win/loss − (1-p) / b
  4. Stage 4 entegrasyonu: signal.calibrated_probability + allocation update
"""
from finllm.calibration.kelly import kelly_fraction, recommend_kelly_size
from finllm.calibration.platt import PlattCalibrator, train_calibrator
from finllm.calibration.tracker import (
    OutcomeRecord,
    OutcomeTracker,
    update_realized_outcomes,
)

__all__ = [
    "OutcomeRecord",
    "OutcomeTracker",
    "PlattCalibrator",
    "kelly_fraction",
    "recommend_kelly_size",
    "train_calibrator",
    "update_realized_outcomes",
]
