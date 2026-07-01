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
  macro?: MacroBlock;
}

export interface SectorAppetite {
  sector: string;
  appetite: number;     // 0..1, 0.5 neutral
  rationale?: string;
}

export interface MacroBlock {
  stance: string;       // risk_on | neutral | risk_off
  summary: string;
  sectors: SectorAppetite[];
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

export interface Commodity {
  key: string;
  label: string;
  price: number;
  unit: string;
  change_5d_pct?: number | null;
  change_20d_pct?: number | null;
}

export interface CommoditiesResponse {
  as_of: string;
  instruments: Commodity[];
}

// --- Stock Detail ---

export interface QuarterlyRecord {
  period: string;
  revenue: number | null;
  net_income: number | null;
  gross_margin: number | null;
  operating_margin: number | null;
  net_margin: number | null;
  total_debt: number | null;
  total_equity: number | null;
  free_cash_flow: number | null;
  capex: number | null;
  total_assets: number | null;
}

export interface QuarterlyFinancials {
  quarters: QuarterlyRecord[];
  fetched_at: string;
}

export interface KapInfo {
  ticker: string;
  disclosures: string[];
  financial_periods: string[];
}

export interface TechnicalIndicators {
  as_of: string;
  price: {
    close: number | null;
    change_1d_pct: number | null;
    change_5d_pct: number | null;
    change_20d_pct: number | null;
  };
  indicators: Record<string, number | null>;
}

export interface BistStock {
  symbol: string;
  name: string;
  sector: string;
}

export interface BistStocksResponse {
  market: string;
  count: number;
  stocks: BistStock[];
}

export interface StockDetailResponse {
  ticker: string;
  market: Market;
  quarterly_financials: QuarterlyFinancials | null;
  kap: KapInfo | null;
  technicals: TechnicalIndicators | null;
}

// --- Analysis ---

export interface PriceScenario {
  label: "base" | "bull" | "bear";
  target_price: number;
  probability: number;
  expected_return_pct: number;
}

export interface AnalysisSignal {
  ticker: string;
  name: string;
  sector: string;
  market: string;
  generated_at: string;
  run_id: string;
  signal: SignalType;
  confidence: number;
  entry_zone_low: number | null;
  entry_zone_high: number | null;
  stop_loss: number | null;
  expected_return_pct: number | null;
  time_horizon_days: number | null;
  scenarios: PriceScenario[];
  allocation_weight: number;
  allocation_cash: number;
  confluence_score: number;
  market_regime: string;
  weekly_trend: string;
  master_score_pct: number | null;
  confirmation_count: number;
  backtest_gate_passed: boolean;
  is_actionable: boolean;
  rationale: RationaleBlock;
  warning_flags: string[];
  llm_model: string;
  llm_cost_usd: number;
}

export interface AnalysisResponse {
  status: string;
  run_id?: string;
  market: string;
  duration_sec?: number;
  total_cost_usd?: number;
  universe_size?: number;
  passed_filter?: number;
  analyzed_count?: number;
  signals: AnalysisSignal[];
  buy_signals: AnalysisSignal[];
  portfolio_additions?: any[];
  stage_durations?: Record<string, number>;
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
