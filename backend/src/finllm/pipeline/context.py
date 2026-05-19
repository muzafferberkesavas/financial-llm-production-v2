"""Pipeline veri yapıları — stage'ler arasında akan tip-güvenli kontratlar.

Akış:
    Stage 0 → list[IngestedData]
    Stage 1 → list[Candidate]      (hard filter geçenler)
    Stage 1B → list[Candidate]      (setup detected eklenir)
    Stage 1C → list[Candidate]      (indicators + confluence eklenir)
    Stage 2 → list[Candidate]      (screen verdict eklenir)
    Stage 3 → list[ExtendedSignal] (LLM deep analysis)
    Stage 4 → list[ExtendedSignal] (allocator + multi-confirm)
    Stage 4.5 → list[ExtendedSignal] (backtest gate filtre)
    Stage 5 → None (write + alert)

PipelineContext: run metadata + adapter + config — tüm stage'lere geçirilir.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

import pandas as pd

from finllm.markets.base import (
    FundamentalSnapshot,
    MarketAdapter,
    RegimeContext,
    Ticker,
)

# ---- Signal enum (lib.zip uyumlu 7 etiket) ----
SignalType = Literal[
    "GUCLU_AL",   # Strong Buy
    "AL",         # Buy
    "IZLE",       # Watch
    "TUT",        # Hold
    "KISMI_SAT",  # Partial Sell
    "SAT",        # Sell
    "ACIL_SAT",   # Urgent Sell (stop-out)
]

SIGNAL_TO_DIRECTION: dict[SignalType, Literal["BUY", "SELL", "HOLD"]] = {
    "GUCLU_AL":  "BUY",
    "AL":        "BUY",
    "IZLE":      "HOLD",
    "TUT":       "HOLD",
    "KISMI_SAT": "SELL",
    "SAT":       "SELL",
    "ACIL_SAT":  "SELL",
}

BUY_SIGNALS = {"GUCLU_AL", "AL"}
SELL_SIGNALS = {"KISMI_SAT", "SAT", "ACIL_SAT"}


PipelineMode = Literal["pre_market", "intraday", "end_of_day"]


# ---- Stage 0 ingest output ----
@dataclass(slots=True)
class IngestedData:
    """Stage 0'da bir ticker için toplanan ham veri paketi."""

    ticker: Ticker
    prices: pd.DataFrame                          # OHLCV, son ~1 yıl
    fundamentals: FundamentalSnapshot | None
    news: list[dict] = field(default_factory=list)
    fetch_errors: list[str] = field(default_factory=list)

    @property
    def has_price_data(self) -> bool:
        return not self.prices.empty and len(self.prices) >= 50

    @property
    def latest_close(self) -> float | None:
        if not self.has_price_data:
            return None
        return float(self.prices["close"].iloc[-1])


# ---- Stage 1+ candidate ----
@dataclass(slots=True)
class Candidate:
    """Filter ve indicator stage'lerinde birikerek akar.

    Her stage Candidate üzerine alan ekler:
      Stage 1   → passed_hard_filter, rejected_reasons
      Stage 1B  → setup_type, setup_confidence
      Stage 1C  → indicators dict, confluence_score, regime
      Stage 2   → screen_verdict, screen_rationale

    Bu "dataclass of accumulator" pattern lib.zip'in StockAnalysisData
    yapısının daha tip-güvenli ve incremental halidir.
    """

    ticker: Ticker
    ingested: IngestedData

    # Stage 1 — hard filter
    passed_hard_filter: bool = False
    hard_filter_score: float = 0.0           # eşiklere ne kadar uzakta (debugging)
    rejected_reasons: list[str] = field(default_factory=list)

    # Stage 1B — setup detection (Phase 3.6 strategy ensemble desteği)
    setup_type: str = "none"  # pullback_ema | bull_flag | breakout | post_earnings_drift | sector_rotation | none
    setup_confidence: float = 0.0            # 0-1, algoritmik
    setup_metadata: dict[str, Any] = field(default_factory=dict)

    # Stage 1C — indicators + confluence
    indicators: dict[str, float] = field(default_factory=dict)
    confluence_score: int = 0                # 0-100 (lib.zip'in 8-bileşenli)
    confluence_detail: dict[str, int] = field(default_factory=dict)
    regime: str = "UNKNOWN"                  # TREND/RANGE/SQUEEZE/VOLATILE

    # Stage 1C — fundamental analysis (Phase 3.1)
    fundamental_score: int = 0               # 0-100 (value + quality + growth)
    fundamental_detail: dict[str, Any] = field(default_factory=dict)

    # Stage 2 — cheap LLM screen
    screen_verdict: Literal["strong", "potential", "skip", "pending"] = "pending"
    screen_rationale: str = ""

    # Tracking
    stage_timings_ms: dict[str, int] = field(default_factory=dict)

    def reject(self, reason: str) -> "Candidate":
        """Hard filter veya başka bir gate'te reddet."""
        self.passed_hard_filter = False
        self.rejected_reasons.append(reason)
        return self

    def __repr__(self) -> str:
        status = "PASS" if self.passed_hard_filter else "FAIL"
        return f"<Candidate {self.ticker} [{status}] conf={self.confluence_score}>"


# ---- Stage 3+ signal ----
@dataclass(slots=True)
class PriceScenario:
    """Senaryo-bazlı hedef fiyat — Stage 3 LLM output."""

    label: Literal["base", "bull", "bear"]
    target_price: float
    probability: float                # 0-1
    expected_return_pct: float        # current'dan hedefe %


@dataclass(slots=True)
class ExtendedSignal:
    """Stage 3'ten sonraki zengin Signal — lib.zip + analyst-grade.

    mevcut `signals/schema.py` Signal'inin genişletilmiş hali.
    API çıktısında bu objeyi dump ediyoruz (Postgres + Telegram + dashboard).
    """

    # Identification
    ticker: Ticker
    generated_at: datetime = field(default_factory=datetime.utcnow)
    session_id: int | None = None
    run_id: str = ""

    # Core decision
    signal: SignalType = "TUT"
    confidence: float = 0.0           # 0-1, calibrated'da gerçek probabilite
    calibrated_probability: float | None = None  # Phase 2'de Platt scaling

    # Pricing
    entry_zone_low: float | None = None
    entry_zone_high: float | None = None
    stop_loss: float | None = None
    scenarios: list[PriceScenario] = field(default_factory=list)
    expected_return_pct: float | None = None     # probability-weighted
    time_horizon_days: int | None = None

    # Allocation (Stage 4 dolduruyor)
    allocation_weight: float = 0.0    # 0-1, max_position_size'a göre
    allocation_cash: float = 0.0      # absolute, currency

    # Rationale (analyst-grade output)
    rationale_trend: str = ""
    rationale_formation: str = ""
    rationale_volume: str = ""
    rationale_news: str = ""
    rationale_fibonacci: str = ""
    rationale_risks: list[str] = field(default_factory=list)
    rationale_full: str = ""          # original LLM full text

    # Quality flags
    warning_flags: list[str] = field(default_factory=list)
    unsourced_flag: bool = False      # [UNSOURCED] tag içeriyorsa
    confirmation_count: int = 0       # multi-confirm rule (Stage 4)
    backtest_30d_return_pct: float | None = None  # Stage 4.5 sonucu
    backtest_gate_passed: bool = False

    # Inheritance from candidate
    confluence_score: int = 0
    market_regime: str = ""
    weekly_trend: str = ""

    # Audit
    llm_model: str = ""
    llm_cost_usd: float = 0.0
    prompt_hash: str = ""

    @property
    def is_actionable(self) -> bool:
        """AL/GUCLU_AL ve backtest gate'ten geçmiş mi?"""
        return self.signal in BUY_SIGNALS and self.backtest_gate_passed

    @property
    def direction(self) -> Literal["BUY", "SELL", "HOLD"]:
        return SIGNAL_TO_DIRECTION[self.signal]

    def __repr__(self) -> str:
        return (
            f"<Signal {self.ticker.symbol} [{self.signal}] "
            f"conf={self.confidence:.2f} exp_ret={self.expected_return_pct}%>"
        )


# ---- Pipeline-wide context ----
@dataclass(slots=True)
class PipelineContext:
    """Tüm pipeline çalışmasını paketleyen üst nesne.

    Stage fonksiyonları bunu alır, kendi outputlarını yazar.
    Tek bir run = tek bir PipelineContext.
    """

    adapter: MarketAdapter
    mode: PipelineMode
    run_id: str
    started_at: datetime = field(default_factory=datetime.utcnow)
    regime: RegimeContext | None = None

    # Top-level configuration (overridable)
    total_capital: float = 10_000.0   # adapter.currency
    max_positions: int = 5
    max_position_pct: float = 0.25    # tek pozisyon max %25
    cash_buffer_pct: float = 0.15     # her zaman %15 cash
    min_expected_return_pct: float = 5.0  # bu altı sinyal reddedilir

    # Stage outputs (accumulator)
    ingested: list[IngestedData] = field(default_factory=list)
    candidates: list[Candidate] = field(default_factory=list)
    stage3_queue: list[Candidate] = field(default_factory=list)  # Stage 2'den 3'e geçen alt liste
    signals: list[ExtendedSignal] = field(default_factory=list)

    # Market agenda (Phase 2.2 — news context)
    # MarketAgenda objesi — type hint için import yapmıyoruz (circular avoid)
    market_agenda: object | None = None

    # Metrics
    total_cost_usd: float = 0.0
    stage_durations_sec: dict[str, float] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def log_stage(self, name: str, duration_sec: float) -> None:
        self.stage_durations_sec[name] = duration_sec

    @property
    def market(self) -> str:
        return self.adapter.name

    @property
    def active_candidates(self) -> list[Candidate]:
        """Hard filter'dan geçenler — sonraki stage'ler bunu kullanır."""
        return [c for c in self.candidates if c.passed_hard_filter]

    @property
    def actionable_signals(self) -> list[ExtendedSignal]:
        """Final çıktı için actionable sinyaller."""
        return [s for s in self.signals if s.is_actionable]
