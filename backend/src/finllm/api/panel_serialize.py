"""Serialize the decision panel (Faz C) into the dashboard's SignalsResponse JSON.

The v2 API serves DATA_DIR/out/signals_<market>_<run_id>.json as
{summary: RunSummary, signals: ExtendedSignal[]} (dashboard/src/lib/types.ts).
Writing the panel output in that exact shape lets the EXISTING API + dashboard
display it with no frontend changes — the UI bridge.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from finllm.config.settings import DATA_DIR
from finllm.pipeline.decision_panel import PanelResult
from finllm.portfolio.construction import Portfolio


def _rationale_block(decision) -> dict:
    v = decision.debate
    bull = " · ".join(p.claim for p in v.bull_points) if v else ""
    bear = " · ".join(p.claim for p in v.bear_points) if v else ""
    return {
        "trend": bull[:600],            # bull thesis in the 'trend' slot
        "formation": "",
        "volume": "",
        "news": bear[:600],             # bear thesis in the 'news' slot
        "fibonacci": "",
        "risks": (v.key_risks if v else []),
        "full": (v.rationale if v else ""),
    }


def _signal(decision, weight: float, capital: float, market: str, run_id: str, generated_at: str) -> dict:
    c = decision.candidate
    v = decision.debate
    action = v.action if v else "IZLE"
    actionable = bool(v and action in ("AL", "GUCLU_AL") and v.position_size_pct > 0)
    return {
        "ticker": c.symbol,
        "market": market,
        "generated_at": generated_at,
        "run_id": run_id,
        "signal": action,
        "confidence": round(v.confidence if v else 0.0, 3),
        "calibrated_probability": None,
        "entry_zone_low": None,
        "entry_zone_high": None,
        "stop_loss": None,
        "expected_return_pct": None,
        "time_horizon_days": (v.time_horizon_days if v else None),
        "scenarios": [],
        "allocation_weight": round(weight, 2),
        "allocation_cash": round(capital * weight / 100.0, 2),
        "confluence_score": round(c.priority, 1),
        "market_regime": "",
        "weekly_trend": "",
        "confirmation_count": 0,
        "backtest_30d_return_pct": None,
        "backtest_gate_passed": True,
        "is_actionable": actionable,
        "rationale": _rationale_block(decision),
        "warning_flags": [],
        "unsourced_flag": False,
        "llm_model": (v.model if v else ""),
        "llm_cost_usd": round(v.cost_usd if v else 0.0, 5),
        "sector": "",
    }


def panel_to_response(
    result: PanelResult,
    portfolio: Portfolio | None,
    *,
    market: str = "nasdaq",
    capital: float = 10_000.0,
    macro_stance: str = "",
    macro=None,
    run_id: str | None = None,
    generated_at: str | None = None,
) -> dict:
    """Build the {summary, signals} payload the dashboard expects.

    `macro` (MacroSectorAnalysis) adds the sector-appetite heatmap data to the
    summary so the UI can render the macro→sector view.
    """
    generated_at = generated_at or datetime.utcnow().isoformat()
    run_id = run_id or f"{market}-panel-{generated_at[:19].replace(':', '')}"
    weights = {p.symbol: p.weight_pct for p in (portfolio.positions if portfolio else [])}

    signals = []
    for d in result.decisions:
        sig = _signal(d, weights.get(d.candidate.symbol, 0.0), capital, market, run_id, generated_at)
        sig["market_regime"] = macro_stance
        signals.append(sig)

    actionable = sum(1 for s in signals if s["is_actionable"])
    summary = {
        "run_id": run_id,
        "market": market,
        "mode": "panel",
        "started_at": generated_at,
        "total_capital": capital,
        "max_positions": 7,
        "max_position_pct": 25.0,
        "cash_buffer_pct": round(portfolio.cash_pct if portfolio else 100.0, 1),
        "min_expected_return_pct": 0.0,
        "regime": {"trade_enabled": True, "fear_level": macro_stance},
        "universe_size": len(result.ranked),
        "passed_hard_filter": len(result.ranked),
        "stage3_queue_size": len(result.decisions),
        "signals_generated": len(signals),
        "actionable_signals": actionable,
        "stage_durations_sec": {},
        "total_duration_sec": 0.0,
        "total_cost_usd": round(result.total_cost_usd, 4),
        "macro": {
            "stance": (macro.overall_stance if macro else macro_stance),
            "summary": (macro.macro_summary if macro else ""),
            "sectors": (
                sorted(
                    [{"sector": s.sector, "appetite": round(s.appetite, 3), "rationale": s.rationale}
                     for s in macro.sectors],
                    key=lambda x: x["appetite"], reverse=True,
                ) if macro else []
            ),
        },
    }
    return {"summary": summary, "signals": signals}


def write_signals_file(payload: dict, market: str = "nasdaq", out_dir: Path | None = None) -> Path:
    """Write to DATA_DIR/out/signals_<market>_<run_id>.json (what /v2/signals/latest reads)."""
    out_dir = out_dir or (DATA_DIR / "out")
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = payload["summary"]["run_id"]
    path = out_dir / f"signals_{market}_{run_id}.json"
    path.write_text(json.dumps(payload, indent=2, default=str))
    return path


__all__ = ["panel_to_response", "write_signals_file"]
