// Mirrors the backend panel_serialize contract (api/panel_serialize.py).
export type Market = "bist" | "nasdaq";

export type SignalType =
  | "GUCLU_AL" | "AL" | "IZLE" | "TUT" | "KISMI_SAT" | "SAT" | "ACIL_SAT";

export interface RationaleBlock {
  trend: string;        // bull thesis
  formation: string;
  volume: string;
  news: string;         // bear thesis
  fibonacci: string;
  risks: string[];
  full: string;
}

export interface ExtendedSignal {
  ticker: string;
  sector?: string;
  market: Market;
  generated_at: string;
  run_id: string;
  signal: SignalType;
  confidence: number;
  time_horizon_days?: number | null;
  allocation_weight: number;
  allocation_cash: number;
  confluence_score: number;
  market_regime: string;
  backtest_gate_passed: boolean;
  is_actionable: boolean;
  rationale: RationaleBlock;
  warning_flags: string[];
  llm_model: string;
  llm_cost_usd: number;
}

export interface RunSummary {
  run_id: string;
  market: Market;
  mode: string;
  started_at: string;
  total_capital: number;
  cash_buffer_pct: number;
  universe_size: number;
  signals_generated: number;
  actionable_signals: number;
  total_cost_usd: number;
  regime?: { fear_level?: string; trade_enabled?: boolean };
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
  allocation_weight: number;
  allocation_cash: number;
  time_horizon_days?: number | null;
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

export const ACTION_META: Record<SignalType, { label: string; tone: "bull" | "bear" | "watch" }> = {
  GUCLU_AL: { label: "GÜÇLÜ AL", tone: "bull" },
  AL: { label: "AL", tone: "bull" },
  IZLE: { label: "İZLE", tone: "watch" },
  TUT: { label: "TUT", tone: "watch" },
  KISMI_SAT: { label: "KISMİ SAT", tone: "bear" },
  SAT: { label: "SAT", tone: "bear" },
  ACIL_SAT: { label: "ACİL SAT", tone: "bear" },
};
