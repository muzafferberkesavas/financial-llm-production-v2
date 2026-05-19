"""/v2/portfolio — son run'un allocation'ı, market bazlı."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from finllm.api.auth import optional_bearer
from finllm.config.settings import DATA_DIR

router = APIRouter(prefix="/v2/portfolio", tags=["portfolio"])

_OUTPUT_DIR = DATA_DIR / "out"


@router.get("/{market}")
def portfolio_for_market(
    market: str,
    _=Depends(optional_bearer),
) -> dict[str, Any]:
    if market not in ("bist", "nasdaq"):
        raise HTTPException(400, "market must be 'bist' or 'nasdaq'")

    files = sorted(_OUTPUT_DIR.glob(f"signals_{market}_*.json"), reverse=True)
    if not files:
        raise HTTPException(404, f"No {market} runs yet")

    data = json.loads(files[0].read_text())
    allocated = [s for s in data["signals"] if s.get("allocation_cash", 0) > 0]
    total = sum(s["allocation_cash"] for s in allocated)
    capital = data["summary"]["total_capital"]

    return {
        "market": market,
        "run_id": data["summary"]["run_id"],
        "as_of": data["summary"]["started_at"],
        "total_capital": capital,
        "cash_buffer_pct": data["summary"]["cash_buffer_pct"],
        "allocated_count": len(allocated),
        "allocated_total": total,
        "cash_remaining": capital - total,
        "positions": [
            {
                "ticker": s["ticker"],
                "name": s.get("name", ""),
                "sector": s.get("sector", ""),
                "signal": s["signal"],
                "confidence": s["confidence"],
                "calibrated_probability": s.get("calibrated_probability"),
                "allocation_weight": s["allocation_weight"],
                "allocation_cash": s["allocation_cash"],
                "expected_return_pct": s.get("expected_return_pct"),
                "time_horizon_days": s.get("time_horizon_days"),
                "entry_zone_low": s.get("entry_zone_low"),
                "entry_zone_high": s.get("entry_zone_high"),
                "stop_loss": s.get("stop_loss"),
            }
            for s in allocated
        ],
    }


@router.get("/")
def all_portfolios(_=Depends(optional_bearer)) -> dict[str, Any]:
    """Tüm market'lerin son portföyleri tek response."""
    result = {}
    for market in ("nasdaq", "bist"):
        files = sorted(_OUTPUT_DIR.glob(f"signals_{market}_*.json"), reverse=True)
        if not files:
            continue
        try:
            data = json.loads(files[0].read_text())
            allocated = [s for s in data["signals"] if s.get("allocation_cash", 0) > 0]
            result[market] = {
                "run_id": data["summary"]["run_id"],
                "as_of": data["summary"]["started_at"],
                "allocated_count": len(allocated),
                "allocated_total": sum(s["allocation_cash"] for s in allocated),
                "total_capital": data["summary"]["total_capital"],
            }
        except Exception:
            continue
    return {"portfolios": result}
