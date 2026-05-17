import type { Signal } from "./types";

// MVP: backend hazır olana kadar dashboard'u sahte sinyallerle test edebilelim.
// Faz 4 sonunda /api/signals gerçek FastAPI backend'inden besleyecek.
export const MOCK_SIGNALS: Signal[] = [
  {
    symbol: "NVDA",
    direction: "BUY",
    confidence: 0.78,
    holdingDays: { min: 5, max: 15 },
    entryPrice: 142.3,
    targetPrice: 155.0,
    stopLoss: 135.5,
    expectedReturn: 0.089,
    rationale:
      "MACD pozitif kesişim, RSI 58 (aşırı alım değil), ADX 32 trend güçlü. Sentiment +0.42 (Blackwell talep haberleri pozitif). Earnings sürprizi yukarı yönlü.",
    signals: {
      technical: { score: 0.71, notes: "MACD↑, ADX 32, BB ortasında" },
      sentiment: { score: 0.42, notes: "Blackwell + AI capex haberleri pozitif" },
      fundamental: { score: 0.65, notes: "FY26 EPS revize ↑%4" },
    },
    generatedAt: new Date().toISOString(),
  },
  {
    symbol: "TSLA",
    direction: "SELL",
    confidence: 0.64,
    holdingDays: { min: 3, max: 10 },
    entryPrice: 248.7,
    targetPrice: 228.0,
    stopLoss: 258.0,
    expectedReturn: 0.083,
    rationale:
      "RSI 78 aşırı alım, BB üst banda yakın, hacim zayıflıyor. Delivery tahminleri sentimentte zayıflık. Kısa vadeli düzeltme olasılığı yüksek.",
    signals: {
      technical: { score: -0.55, notes: "RSI 78, BB%92, hacim azalıyor" },
      sentiment: { score: -0.31, notes: "Delivery downgrade haberleri" },
    },
    generatedAt: new Date().toISOString(),
  },
  {
    symbol: "MSFT",
    direction: "HOLD",
    confidence: 0.55,
    holdingDays: { min: 0, max: 0 },
    entryPrice: 418.2,
    rationale: "Sinyaller karışık — teknik nötr, sentiment hafif pozitif ama hacim doğrulaması yok.",
    signals: {
      technical: { score: 0.05, notes: "Range-bound, ADX 18 (zayıf trend)" },
      sentiment: { score: 0.18, notes: "Copilot kullanım haberleri pozitif ama mat" },
    },
    generatedAt: new Date().toISOString(),
  },
];
