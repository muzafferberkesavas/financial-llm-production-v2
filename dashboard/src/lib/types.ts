export type SignalDirection = "BUY" | "SELL" | "HOLD";

export interface Signal {
  symbol: string;
  direction: SignalDirection;
  confidence: number;          // 0..1
  holdingDays: { min: number; max: number };
  entryPrice: number;
  targetPrice?: number;
  stopLoss?: number;
  expectedReturn?: number;     // örn. 0.06 → %6
  rationale: string;
  signals: {
    technical: { score: number; notes: string };
    sentiment: { score: number; notes: string };  // -1..1
    fundamental?: { score: number; notes: string };
  };
  generatedAt: string;         // ISO
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
