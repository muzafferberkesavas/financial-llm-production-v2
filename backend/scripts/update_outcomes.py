"""Cron: outcome update + Platt retrain.

Günde 1 kere (örn. 18:30 ET / EOD) çalıştır:
  - Tüm "open" outcome record'ları için gerçek fiyat çek
  - Stop hit / target hit / time stop kontrolü
  - Closed olarak işaretle
  - Eğer ≥30 closed record varsa Platt modelini yeniden eğit

Usage:
    python scripts/update_outcomes.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s")


def main() -> int:
    from finllm.calibration import (
        OutcomeTracker,
        train_calibrator,
        update_realized_outcomes,
    )

    tracker = OutcomeTracker()
    print(f"Outcome file: {tracker.file}")
    all_records = tracker.load_all()
    print(f"Loaded {len(all_records)} records")
    print(f"  Open: {sum(1 for r in all_records if not r.is_closed)}")
    print(f"  Closed: {sum(1 for r in all_records if r.is_closed)}")

    # 1. Update realized outcomes
    print()
    print("=== UPDATE REALIZED OUTCOMES ===")
    stats = update_realized_outcomes(tracker)
    print(f"  Updated: {stats['updated']}")
    print(f"  Wins:    {stats['wins']}")
    print(f"  Losses:  {stats['losses']}")
    print(f"  Still open: {stats['still_open']}")

    # 2. Retrain Platt
    print()
    print("=== RETRAIN PLATT CALIBRATOR ===")
    calibrator = train_calibrator(tracker)
    if calibrator.is_trained:
        hit_rate = calibrator.n_wins / calibrator.n_train
        print(f"  ✓ Trained on {calibrator.n_train} closed records")
        print(f"    Historical hit rate: {hit_rate:.2%}")
        print(f"    Saved to: {Path('data/calibration/platt_model.json')}")
    else:
        print(f"  ⏳ Need ≥30 closed records, have {calibrator.n_train}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
