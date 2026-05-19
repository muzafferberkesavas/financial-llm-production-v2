"""Backfill: data/out/signals_*.json → SQLAlchemy DB.

Bir defalık migration — Phase 3.2'de geçmiş JSON output'larını DB'ye aktarır.
Idempotent: aynı run_id varsa skip eder.
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

logging.basicConfig(level=logging.INFO, format="%(levelname)-7s | %(message)s")


def _parse_dt(s: str):
    from datetime import datetime
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return datetime.utcnow()


def main() -> int:
    from sqlalchemy import select

    from finllm.config.settings import DATA_DIR
    from finllm.storage.engine import init_schema, session_scope
    from finllm.storage.models import Outcome, Run, Signal, SignalScenario

    init_schema()

    out_dir = DATA_DIR / "out"
    files = sorted(out_dir.glob("signals_*.json"))
    if not files:
        print("No JSON files to migrate.")
        return 0

    print(f"Found {len(files)} JSON files.")
    imported = 0
    skipped = 0

    for f in files:
        try:
            data = json.loads(f.read_text())
        except Exception as e:
            print(f"  Skip {f.name}: {e}")
            continue

        summary = data["summary"]
        run_id_str = summary["run_id"]

        with session_scope() as sess:
            existing = sess.execute(
                select(Run).where(Run.run_id == run_id_str)
            ).scalar_one_or_none()
            if existing:
                skipped += 1
                continue

            run = Run(
                run_id=run_id_str,
                market=summary["market"],
                mode=summary["mode"],
                started_at=_parse_dt(summary["started_at"]),
                total_capital=summary["total_capital"],
                max_positions=summary["max_positions"],
                max_position_pct=summary["max_position_pct"],
                cash_buffer_pct=summary["cash_buffer_pct"],
                min_expected_return_pct=summary["min_expected_return_pct"],
                vix=(summary.get("regime") or {}).get("vix"),
                benchmark_change_5d=(summary.get("regime") or {}).get("benchmark_change_5d"),
                trade_enabled=(summary.get("regime") or {}).get("trade_enabled", True),
                halt_reason=(summary.get("regime") or {}).get("halt_reason"),
                fear_level=(summary.get("regime") or {}).get("fear_level", "calm"),
                universe_size=summary["universe_size"],
                passed_hard_filter=summary["passed_hard_filter"],
                stage3_queue_size=summary.get("stage3_queue_size", 0),
                signals_generated=summary["signals_generated"],
                actionable_signals=summary["actionable_signals"],
                total_duration_sec=summary.get("total_duration_sec", 0),
                total_cost_usd=summary.get("total_cost_usd", 0),
                stage_durations=summary.get("stage_durations_sec"),
            )
            sess.add(run)
            sess.flush()

            for sig_dict in data["signals"]:
                db_sig = Signal(
                    run_db_id=run.id,
                    ticker=sig_dict["ticker"],
                    name=sig_dict.get("name"),
                    sector=sig_dict.get("sector"),
                    market=sig_dict["market"],
                    generated_at=_parse_dt(sig_dict["generated_at"]),
                    run_id=sig_dict["run_id"],
                    signal=sig_dict["signal"],
                    confidence=sig_dict["confidence"],
                    calibrated_probability=sig_dict.get("calibrated_probability"),
                    entry_zone_low=sig_dict.get("entry_zone_low"),
                    entry_zone_high=sig_dict.get("entry_zone_high"),
                    stop_loss=sig_dict.get("stop_loss"),
                    expected_return_pct=sig_dict.get("expected_return_pct"),
                    time_horizon_days=sig_dict.get("time_horizon_days"),
                    allocation_weight=sig_dict.get("allocation_weight", 0),
                    allocation_cash=sig_dict.get("allocation_cash", 0),
                    confluence_score=sig_dict.get("confluence_score", 0),
                    market_regime=sig_dict.get("market_regime", ""),
                    weekly_trend=sig_dict.get("weekly_trend", ""),
                    confirmation_count=sig_dict.get("confirmation_count", 0),
                    backtest_30d_return_pct=sig_dict.get("backtest_30d_return_pct"),
                    backtest_gate_passed=sig_dict.get("backtest_gate_passed", False),
                    is_actionable=sig_dict.get("is_actionable", False),
                    rationale=sig_dict.get("rationale", {}),
                    warning_flags=sig_dict.get("warning_flags", []),
                    unsourced_flag=sig_dict.get("unsourced_flag", False),
                    llm_model=sig_dict.get("llm_model", ""),
                    llm_cost_usd=sig_dict.get("llm_cost_usd", 0),
                )
                sess.add(db_sig)
                sess.flush()
                for sc in sig_dict.get("scenarios", []):
                    sess.add(SignalScenario(
                        signal_id=db_sig.id,
                        label=sc["label"],
                        target_price=sc["target_price"],
                        probability=sc["probability"],
                        expected_return_pct=sc["expected_return_pct"],
                    ))
        imported += 1

    print(f"\n✓ Imported {imported} runs, skipped {skipped} (already in DB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
