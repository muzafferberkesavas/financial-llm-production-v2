"""/v2/history — outcome tracker + calibration stats."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from finllm.api.auth import optional_bearer
from finllm.calibration import OutcomeTracker, PlattCalibrator

router = APIRouter(prefix="/v2/history", tags=["history"])


@router.get("/outcomes")
def get_outcomes(
    market: str | None = Query(default=None, regex="^(bist|nasdaq)$"),
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    _=Depends(optional_bearer),
) -> dict:
    """Closed (or all) outcomes — calibration için eğitim seti."""
    tracker = OutcomeTracker()
    records = tracker.load_all()

    if market:
        records = [r for r in records if r.market == market]
    if status:
        records = [r for r in records if r.status == status]

    records.sort(key=lambda r: r.generated_at, reverse=True)
    records = records[:limit]

    wins = sum(1 for r in records if r.is_win)
    losses = sum(1 for r in records if r.status.startswith("loss_"))

    return {
        "count": len(records),
        "wins": wins,
        "losses": losses,
        "hit_rate": (wins / len(records)) if records else 0,
        "outcomes": [
            {
                "run_id": r.run_id,
                "ticker": r.ticker,
                "market": r.market,
                "generated_at": r.generated_at,
                "signal": r.signal,
                "confidence": r.confidence,
                "expected_return_pct": r.expected_return_pct,
                "status": r.status,
                "realized_return_pct": r.realized_return_pct,
                "days_held": r.days_held,
                "exit_reason": r.exit_reason,
            }
            for r in records
        ],
    }


@router.get("/calibration")
def get_calibration_status(_=Depends(optional_bearer)) -> dict:
    """Platt model durumu — eğitilmiş mi, hit rate ne?"""
    calibrator = PlattCalibrator.load()
    return {
        "is_trained": calibrator.is_trained,
        "n_train": calibrator.n_train,
        "n_wins": calibrator.n_wins,
        "historical_hit_rate": (
            calibrator.n_wins / calibrator.n_train if calibrator.n_train else None
        ),
        "trained_at": calibrator.trained_at,
        "feature_names": calibrator.feature_names,
        "coefs": calibrator.coefs,
        "intercept": calibrator.intercept,
    }
