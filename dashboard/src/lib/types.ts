/**
 * Type definitions — backend/src/finllm/api JSON kontratıyla uyumlu.
 *
 * Legacy types (Signal/BacktestSummary) korunuyor (eski kodlar için).
 * ExtendedSignal + yeni response tipleri Phase 2.5 API'ye karşılık geliyor.
 */

// ---- Legacy (v1) — eski components için korunuyor ----
export type SignalDirection = "BUY" | "SELL" | "HOLD";

export interface Signal {
  symbol: string;
  direction: SignalDirection;
  confidence: number; // 0..1
  holdingDays: { min: number; max: number };
  entryPrice: number;
  targetPrice?: number;
  stopLoss?: number;
  expectedReturn?: number;
  rationale: string;
  signals: {
    technical: { score: number; notes: string };
    sentiment: { score: number; notes: string };
    fundamental?: { score: number; notes: string };
  };
  generatedAt: string;
}

export interface BacktestSummary {
  start: string;
  end: string;
  totalReturn: number;
  sharpe: number;
  maxDrawdown: number;
  winRate: number;
  avgHoldingDays: number;
  tradeCount: number;
}

// ---- v2 — Phase 2.5 API ----
export type Market = "bist" | "nasdaq";

export type SignalType =
  | "GUCLU_AL"
  | "AL"
  | "IZLE"
  | "TUT"
  | "KISMI_SAT"
  | "SAT"
  | "ACIL_SAT";

export interface PriceScenario {
  label: "base" | "bull" | "bear";
  target_price: number;
  probability: number;
  expected_return_pct: number;
}

export interface RationaleBlock {
  trend: string;
  formation: string;
  volume: string;
  news: string;
  fibonacci: string;
  risks: string[];
  full: string;
}

export interface ExtendedSignal {
  ticker: string;
  name?: string;
  sector?: string;
  market: Market;
  generated_at: string;
  session_id?: number | null;
  run_id: string;
  signal: SignalType;
  confidence: number;
  calibrated_probability?: number | null;
  entry_zone_low?: number | null;
  entry_zone_high?: number | null;
  stop_loss?: number | null;
  expected_return_pct?: number | null;
  time_horizon_days?: number | null;
  scenarios: PriceScenario[];
  allocation_weight: number;
  allocation_cash: number;
  confluence_score: number;
  market_regime: string;
  weekly_trend: string;
  confirmation_count: number;
  backtest_30d_return_pct?: number | null;
  backtest_gate_passed: boolean;
  is_actionable: boolean;
  rationale: RationaleBlock;
  warning_flags: string[];
  unsourced_flag: boolean;
  llm_model: string;
  llm_cost_usd: number;
}

export interface RegimeInfo {
  vix?: number | null;
  benchmark_change_5d?: number | null;
  trade_enabled?: boolean;
  halt_reason?: string | null;
  fear_level?: string;
}

export interface RunSummary {
  run_id: string;
  market: Market;
  mode: string;
  started_at: string;
  total_capital: number;
  max_positions: number;
  max_position_pct: number;
  cash_buffer_pct: number;
  min_expected_return_pct: number;
  regime: RegimeInfo;
  universe_size: number;
  passed_hard_filter: number;
  stage3_queue_size: number;
  signals_generated: number;
  actionable_signals: number;
  stage_durations_sec: Record<string, number>;
  total_duration_sec: number;
  total_cost_usd: number;
  duration_sec?: number;
}

export interface SignalsResponse {
  summary: RunSummary;
  signals: ExtendedSignal[];
}

export interface PortfolioPosition {
  ticker: string;
  name: string;
  sector: string;
  signal: SignalType;
  confidence: number;
  calibrated_probability?: number | null;
  allocation_weight: number;
  allocation_cash: number;
  expected_return_pct?: number | null;
  time_horizon_days?: number | null;
  entry_zone_low?: number | null;
  entry_zone_high?: number | null;
  stop_loss?: number | null;
}

export interface PortfolioResponse {
  market: Market;
  run_id: string;
  as_of: string;
  total_capital: number;
  cash_buffer_pct: number;
  allocated_count: number;
  allocated_total: number;
  cash_remaining: number;
  positions: PortfolioPosition[];
}

export interface OutcomeRecord {
  run_id: string;
  ticker: string;
  market: Market;
  generated_at: string;
  signal: SignalType;
  confidence: number;
  expected_return_pct: number | null;
  status:
    | "open"
    | "win_target"
    | "win_partial"
    | "loss_stop"
    | "loss_time"
    | "neutral_time";
  realized_return_pct: number | null;
  days_held: number | null;
  exit_reason: string;
}

export interface CalibrationStatus {
  is_trained: boolean;
  n_train: number;
  n_wins: number;
  historical_hit_rate: number | null;
  trained_at: string;
  feature_names: string[] | null;
  coefs: number[] | null;
  intercept: number;
}
