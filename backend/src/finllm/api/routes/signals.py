"""/v2/signals — son sinyalleri, tek ticker arama, run listesi."""
from __future__ import annotations

import glob
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from finllm.api.auth import optional_bearer
from finllm.config.settings import DATA_DIR

router = APIRouter(prefix="/v2/signals", tags=["signals"])

_OUTPUT_DIR = DATA_DIR / "out"


def _list_files(market: str | None = None) -> list[Path]:
    pattern = f"signals_{market}_*.json" if market else "signals_*.json"
    return sorted(_OUTPUT_DIR.glob(pattern), reverse=True)


@router.get("/latest")
def latest_signals(
    market: str | None = Query(default=None, regex="^(bist|nasdaq)$"),
    actionable_only: bool = False,
    _=Depends(optional_bearer),
) -> dict[str, Any]:
    """En son run'un sinyalleri. Market verilmezse tüm market'lerden en son."""
    files = _list_files(market=market)
    if not files:
        raise HTTPException(404, "No signals found yet")

    data = json.loads(files[0].read_text())
    if actionable_only:
        data["signals"] = [s for s in data["signals"] if s.get("is_actionable")]
    return data


@router.get("/by-ticker/{ticker}")
def signal_by_ticker(
    ticker: str,
    lookback: int = Query(default=10, ge=1, le=50),
    _=Depends(optional_bearer),
) -> dict[str, Any]:
    """Belirtilen ticker için son N run içinde son sinyali bul."""
    ticker = ticker.upper()
    files = _list_files()[:lookback]
    for f in files:
        try:
            data = json.loads(f.read_text())
        except Exception:
            continue
        for sig in data.get("signals", []):
            if sig.get("ticker") == ticker:
                return {"summary": data["summary"], "signal": sig}

    raise HTTPException(404, f"{ticker} son {lookback} run'da bulunamadı")


@router.get("/runs")
def list_runs(
    market: str | None = Query(default=None, regex="^(bist|nasdaq)$"),
    limit: int = Query(default=20, ge=1, le=100),
    _=Depends(optional_bearer),
) -> dict[str, Any]:
    """Run history."""
    files = _list_files(market=market)[:limit]
    runs = []
    for f in files:
        try:
            data = json.loads(f.read_text())
            runs.append(
                {
                    "run_id": data["summary"]["run_id"],
                    "market": data["summary"]["market"],
                    "mode": data["summary"]["mode"],
                    "started_at": data["summary"]["started_at"],
                    "universe_size": data["summary"]["universe_size"],
                    "passed_hard_filter": data["summary"]["passed_hard_filter"],
                    "signals_generated": data["summary"]["signals_generated"],
                    "actionable_signals": data["summary"]["actionable_signals"],
                    "total_cost_usd": data["summary"]["total_cost_usd"],
                    "duration_sec": data["summary"].get("total_duration_sec"),
                    "regime": data["summary"].get("regime"),
                }
            )
        except Exception:
            continue
    return {"runs": runs, "count": len(runs)}


@router.get("/run/{run_id}")
def get_run(run_id: str, _=Depends(optional_bearer)) -> dict[str, Any]:
    """Belirli bir run'ın tüm sinyallerini getir."""
    for f in _list_files():
        try:
            data = json.loads(f.read_text())
            if data["summary"]["run_id"] == run_id:
                return data
        except Exception:
            continue
    raise HTTPException(404, f"Run {run_id} bulunamadı")
