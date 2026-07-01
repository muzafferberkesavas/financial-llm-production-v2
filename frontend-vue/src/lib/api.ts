import type { SignalsResponse, PortfolioResponse, CommoditiesResponse, StockDetailResponse, BistStocksResponse, AnalysisResponse, Market } from "@/types";

// In dev, Vite proxies /api → backend (vite.config.ts). In prod, set VITE_API_URL.
const BASE = (import.meta.env.VITE_API_URL ?? "/api").replace(/\/$/, "");

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { Accept: "application/json" },
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} — ${path}`);
  return (await res.json()) as T;
}

export function fetchSignals(market?: Market): Promise<SignalsResponse> {
  const q = market ? `?market=${market}` : "";
  return getJson<SignalsResponse>(`/v2/signals/latest${q}`);
}

export function fetchPortfolio(market?: Market): Promise<PortfolioResponse> {
  const q = market ? `?market=${market}` : "";
  return getJson<PortfolioResponse>(`/v2/portfolio${q}`);
}

export function fetchCommodities(): Promise<CommoditiesResponse> {
  return getJson<CommoditiesResponse>(`/v2/commodities`);
}

export function fetchStockDetail(ticker: string, market: Market): Promise<StockDetailResponse> {
  return getJson<StockDetailResponse>(`/v2/stocks/${ticker}?market=${market}`);
}

export function fetchBistStocks(): Promise<BistStocksResponse> {
  return getJson<BistStocksResponse>(`/v2/universe/bist`);
}

export async function runBistAnalysis(options?: { capital?: number; llm_backend?: string }): Promise<AnalysisResponse> {
  const res = await fetch(`${BASE}/v2/analyze/bist`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({
      capital: options?.capital ?? 100000,
      llm_backend: options?.llm_backend ?? "claude",
      max_top: 5,
      skip_backtest: true,
      skip_news: true,
    }),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return (await res.json()) as AnalysisResponse;
}

export function fetchLatestAnalysis(): Promise<AnalysisResponse> {
  return getJson<AnalysisResponse>(`/v2/analyze/latest?market=bist`);
}
