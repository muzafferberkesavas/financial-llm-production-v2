"""POST /v2/analyze/bist — BIST analiz pipeline'i.

Scoring → Preview → Analiz zinciri ayni pipeline context'i kullanir.
Skorlama yapildiginda ctx cache'lenir, diger endpoint'ler onu kullanir.
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel

from finllm.config.settings import DATA_DIR, settings
from finllm.utils.logging import logger

router = APIRouter(prefix="/v2/analyze", tags=["analyze"])

_ANALYSIS_DIR = DATA_DIR / "analysis"


# ---- Shared pipeline cache ----
# Skorlama yapildiginda ctx + sirali adaylar burada tutulur.
# Preview ve Analiz ayni ctx'i kullanir.
_pipeline_cache: dict = {
    "ctx": None,
    "sorted_candidates": None,  # master_score'a gore sirali tum adaylar
    "timestamp": 0.0,
}
_CACHE_TTL = 86400  # 1 gun


def _run_pipeline_stages(force: bool = False):
    """Stage 0-1c calistir, sonucu cache'le. 1 gun gecmediyse ve force degilse skip."""
    import time as _time

    from finllm.markets import get_adapter
    from finllm.pipeline.context import PipelineContext
    from finllm.pipeline.regime import run_regime_check
    from finllm.pipeline.stage0_ingest import run_stage0
    from finllm.pipeline.stage1_filter import run_stage1
    from finllm.pipeline.stage1c_features import run_stage1c

    now = _time.time()
    if (
        not force
        and _pipeline_cache["ctx"] is not None
        and (now - _pipeline_cache["timestamp"]) < _CACHE_TTL
    ):
        return _pipeline_cache["ctx"], _pipeline_cache["sorted_candidates"], True

    adapter = get_adapter("bist")
    run_id = f"bist-{uuid.uuid4().hex[:8]}"

    ctx = PipelineContext(
        adapter=adapter,
        mode="end_of_day",
        run_id=run_id,
        total_capital=100_000.0,
    )

    run_regime_check(ctx)
    run_stage0(ctx, lookback_days=400, skip_news=True)
    run_stage1(ctx)
    run_stage1c(ctx, max_pass_to_stage3=20)

    # Tum aktif adaylari master_score'a gore sirala
    active = ctx.active_candidates
    sorted_cands = sorted(
        active,
        key=lambda c: c.master_score.total if c.master_score else 0,
        reverse=True,
    )

    _pipeline_cache["ctx"] = ctx
    _pipeline_cache["sorted_candidates"] = sorted_cands
    _pipeline_cache["timestamp"] = _time.time()

    return ctx, sorted_cands, False


# ---- Scoring ----

class ScoringRequest(BaseModel):
    max_results: int = 20
    force_refresh: bool = False


_SCORING_DIR = DATA_DIR / "scoring"


def _save_scoring(result: dict) -> Path:
    _SCORING_DIR.mkdir(parents=True, exist_ok=True)
    fpath = _SCORING_DIR / "bist_scoring_latest.json"
    fpath.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return fpath


@router.post("/scoring")
def run_scoring(req: ScoringRequest) -> dict:
    """Master Scorecard calistir (stage 0-1c). Sonuc 1 gun cache'lenir."""
    import time as _time

    logger.info(f"[SCORING] Baslatiliyor (force={req.force_refresh}, max={req.max_results})")
    started = _time.perf_counter()

    try:
        ctx, sorted_cands, from_cache = _run_pipeline_stages(force=req.force_refresh)
    except Exception as e:
        logger.error(f"[SCORING] Pipeline hatasi: {e}")
        raise

    duration = _time.perf_counter() - started

    stocks = []
    for cand in sorted_cands[:req.max_results]:
        ms = cand.master_score
        if ms is None:
            continue
        categories = {
            k: {"score": v.score, "max": v.max_score}
            for k, v in ms.categories.items()
        }
        stocks.append({
            "ticker": cand.ticker.symbol,
            "name": cand.ticker.name,
            "sector": cand.ticker.sector,
            "master_score": ms.total,
            "max_possible": ms.max_possible,
            "pct": round(ms.pct, 1),
            "label": ms.label,
            "confluence_score": cand.confluence_score,
            "regime": cand.regime,
            "setup_type": cand.setup_type,
            "categories": categories,
        })

    result = {
        "status": "ok",
        "duration_sec": round(duration, 1),
        "universe_size": len(ctx.ingested),
        "passed_filter": sum(1 for c in ctx.candidates if c.passed_hard_filter),
        "scored_count": len(stocks),
        "stocks": stocks,
        "from_cache": from_cache,
        "scored_at": _time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    if from_cache:
        result["cache_age_min"] = round(
            (_time.time() - _pipeline_cache["timestamp"]) / 60, 1
        )

    # Dosyaya kaydet
    fpath = _save_scoring(result)
    top5 = ", ".join(s["ticker"] for s in stocks[:5])
    logger.info(
        f"[SCORING] Tamam: {len(stocks)} hisse | top5=[{top5}] | "
        f"{'cache' if from_cache else 'taze'} | {duration:.1f}s | {fpath}"
    )

    return result


@router.get("/scoring/latest")
def get_latest_scoring() -> dict:
    """Son skorlama sonucunu dosyadan yukle."""
    _SCORING_DIR.mkdir(parents=True, exist_ok=True)
    fpath = _SCORING_DIR / "bist_scoring_latest.json"
    if not fpath.exists():
        return {"status": "no_scoring", "stocks": []}
    return json.loads(fpath.read_text(encoding="utf-8"))


# ---- Preview (prompt onizleme) ----

class PreviewRequest(BaseModel):
    max_top: int = 5
    skip_news: bool = True


@router.post("/preview")
def preview_prompts(req: PreviewRequest) -> dict:
    """Cache'li pipeline ctx'den top N hissenin system+user promptlarini dondur."""
    import time as _time

    from finllm.llm import build_data_block
    from finllm.skills import load_skill

    started = _time.perf_counter()

    # Eger skorlama hic yapilmadiysa, otomatik calistir
    ctx, sorted_cands, from_cache = _run_pipeline_stages(force=False)

    # Top N adayi al (skorlama siralamasiyla ayni)
    top_cands = sorted_cands[:req.max_top]

    # System prompt
    system_prompt = load_skill("deep-analyst")

    # Her aday icin user prompt olustur
    candidates = []
    for cand in top_cands:
        data_block = build_data_block(
            cand,
            market_agenda=ctx.market_agenda,
            kap_disclosures=ctx.kap_per_ticker.get(cand.ticker.symbol.upper()),
        )
        user_prompt = (
            "Analyze the following ticker. Read Layer 0 first if MARKET AGENDA exists, "
            "then proceed through Layers 1-6. Output via the produce_analysis tool.\n\n"
            f"```\n{data_block}\n```"
        )
        candidates.append({
            "ticker": cand.ticker.symbol,
            "name": cand.ticker.name,
            "sector": cand.ticker.sector,
            "master_score_pct": cand.master_score.pct if cand.master_score else None,
            "confluence_score": cand.confluence_score,
            "regime": cand.regime,
            "user_prompt": user_prompt,
        })

    duration = _time.perf_counter() - started

    return {
        "status": "ok",
        "duration_sec": round(duration, 1),
        "universe_size": len(ctx.ingested),
        "passed_filter": sum(1 for c in ctx.candidates if c.passed_hard_filter),
        "candidate_count": len(candidates),
        "system_prompt": system_prompt,
        "candidates": candidates,
    }


# ---- Analiz (full LLM pipeline) ----

class AnalyzeRequest(BaseModel):
    capital: float = 100_000.0
    llm_backend: str = "claude"
    max_top: int = 5
    skip_backtest: bool = True
    skip_news: bool = True


def _signal_to_dict(sig) -> dict:
    """ExtendedSignal -> JSON-serializable dict."""
    return {
        "ticker": sig.ticker.symbol,
        "name": sig.ticker.name,
        "sector": sig.ticker.sector,
        "market": sig.ticker.market,
        "generated_at": sig.generated_at.isoformat(),
        "run_id": sig.run_id,
        "signal": sig.signal,
        "confidence": sig.confidence,
        "entry_zone_low": sig.entry_zone_low,
        "entry_zone_high": sig.entry_zone_high,
        "stop_loss": sig.stop_loss,
        "expected_return_pct": sig.expected_return_pct,
        "time_horizon_days": sig.time_horizon_days,
        "scenarios": [
            {
                "label": s.label,
                "target_price": s.target_price,
                "probability": s.probability,
                "expected_return_pct": s.expected_return_pct,
            }
            for s in sig.scenarios
        ],
        "allocation_weight": sig.allocation_weight,
        "allocation_cash": sig.allocation_cash,
        "confluence_score": sig.confluence_score,
        "market_regime": sig.market_regime,
        "weekly_trend": sig.weekly_trend,
        "master_score_pct": sig.master_score_pct,
        "confirmation_count": sig.confirmation_count,
        "backtest_gate_passed": sig.backtest_gate_passed,
        "is_actionable": sig.is_actionable,
        "rationale": {
            "trend": sig.rationale_trend,
            "formation": sig.rationale_formation,
            "volume": sig.rationale_volume,
            "news": sig.rationale_news,
            "fibonacci": sig.rationale_fibonacci,
            "risks": sig.rationale_risks,
            "full": sig.rationale_full,
        },
        "warning_flags": sig.warning_flags,
        "llm_model": sig.llm_model,
        "llm_cost_usd": sig.llm_cost_usd,
    }


def _save_analysis(result: dict) -> Path:
    """Analiz sonucunu dosyaya kaydet."""
    _ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    fpath = _ANALYSIS_DIR / f"bist_analysis_{ts}.json"
    fpath.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return fpath


@router.post("/bist")
def run_bist_analysis(req: AnalyzeRequest) -> dict:
    """Cache'li pipeline ctx'den top N hisseyi LLM ile analiz et."""
    import copy

    from finllm.llm import ClaudeDeepClient, MockLLM
    from finllm.pipeline.stage3_deep import run_stage3
    from finllm.pipeline.stage4_judge import run_stage4
    from finllm.pipeline.stage5_writer import run_stage5

    started = time.perf_counter()

    # Cache'li ctx'i al (yoksa otomatik calistir)
    cached_ctx, sorted_cands, _ = _run_pipeline_stages(force=False)

    # Shallow copy — analiz cached ctx'i kirletmesin
    ctx = copy.copy(cached_ctx)
    ctx.stage3_queue = list(sorted_cands[:req.max_top])
    ctx.signals = []
    ctx.total_cost_usd = 0.0
    ctx.total_capital = req.capital
    ctx.stage_durations_sec = dict(cached_ctx.stage_durations_sec)

    # LLM secimi
    if req.llm_backend == "mock":
        deep_llm = MockLLM(role="deep")
    else:
        deep_llm = ClaudeDeepClient()

    logger.info(f"[ANALYZE] LLM: {deep_llm.name}, top {req.max_top} hisse analiz ediliyor")

    run_stage3(ctx, client=deep_llm)
    run_stage4(ctx)

    if not req.skip_backtest:
        from finllm.pipeline.stage4_5_backtest_gate import run_stage4_5
        run_stage4_5(ctx)
    else:
        for s in ctx.signals:
            s.backtest_gate_passed = s.signal in ("AL", "GUCLU_AL")

    run_stage5(ctx)

    duration = time.perf_counter() - started

    signals = [_signal_to_dict(s) for s in ctx.signals]
    buy_signals = [s for s in signals if s["signal"] in ("GUCLU_AL", "AL")]

    result = {
        "status": "completed",
        "run_id": ctx.run_id,
        "market": "bist",
        "duration_sec": round(duration, 1),
        "total_cost_usd": round(ctx.total_cost_usd, 4),
        "universe_size": len(ctx.ingested),
        "passed_filter": sum(1 for c in ctx.candidates if c.passed_hard_filter),
        "analyzed_count": len(ctx.stage3_queue),
        "signals": signals,
        "buy_signals": buy_signals,
        "portfolio_additions": [
            {
                "ticker": s["ticker"],
                "signal": s["signal"],
                "confidence": s["confidence"],
                "entry_zone_low": s["entry_zone_low"],
                "entry_zone_high": s["entry_zone_high"],
                "stop_loss": s["stop_loss"],
                "scenarios": s["scenarios"],
                "allocation_weight": s["allocation_weight"],
                "allocation_cash": s["allocation_cash"],
            }
            for s in buy_signals
        ],
        "stage_durations": ctx.stage_durations_sec,
    }

    fpath = _save_analysis(result)
    logger.info(f"[ANALYZE] BIST analysis saved: {fpath}")

    return result


@router.get("/latest")
def get_latest_analysis(
    market: str = Query("bist", pattern="^(bist|nasdaq)$"),
) -> dict:
    """Son analiz sonuclarini getir."""
    _ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    pattern = f"{market}_analysis_*.json"
    files = sorted(_ANALYSIS_DIR.glob(pattern), reverse=True)
    if not files:
        return {"status": "no_analysis", "signals": [], "buy_signals": []}

    return json.loads(files[0].read_text(encoding="utf-8"))
