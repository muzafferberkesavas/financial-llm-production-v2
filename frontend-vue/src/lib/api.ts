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

export interface QuickQuote {
  ticker: string;
  market: string;
  price: number;
  prev_close: number;
  change_pct: number;
  as_of: string;
  error?: string;
}

export function fetchQuote(ticker: string, market: string = "bist"): Promise<QuickQuote> {
  return getJson<QuickQuote>(`/v2/quote/${ticker}?market=${market}`);
}

export interface ScoringCategory {
  score: number;
  max: number;
}

export interface ScoringStock {
  ticker: string;
  name: string;
  sector: string;
  master_score: number;
  max_possible: number;
  pct: number;
  label: string;
  confluence_score: number;
  regime: string;
  setup_type: string;
  categories: Record<string, ScoringCategory>;
}

export interface ScoringResponse {
  status: string;
  duration_sec: number;
  universe_size: number;
  passed_filter: number;
  scored_count: number;
  stocks: ScoringStock[];
  from_cache: boolean;
  cache_age_min?: number;
  scored_at: string;
}

export async function fetchScoring(maxResults: number = 20, forceRefresh: boolean = false): Promise<ScoringResponse> {
  const res = await fetch(`${BASE}/v2/analyze/scoring`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ max_results: maxResults, force_refresh: forceRefresh }),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return (await res.json()) as ScoringResponse;
}

export function fetchLatestScoring(): Promise<ScoringResponse> {
  return getJson<ScoringResponse>(`/v2/analyze/scoring/latest`);
}

export interface PromptCandidate {
  ticker: string;
  name: string;
  sector: string;
  master_score_pct: number | null;
  confluence_score: number;
  regime: string;
  user_prompt: string;
}

export interface PromptPreviewResponse {
  status: string;
  duration_sec: number;
  universe_size: number;
  passed_filter: number;
  candidate_count: number;
  system_prompt: string;
  candidates: PromptCandidate[];
}

export async function fetchPromptPreview(maxTop: number = 5): Promise<PromptPreviewResponse> {
  const res = await fetch(`${BASE}/v2/analyze/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ max_top: maxTop, skip_news: true }),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return (await res.json()) as PromptPreviewResponse;
}

// ---- Notebook ----

export interface NotebookEntry {
  id: string;
  ticker: string;
  note: string;
  entryPrice: number;
  entryDate: string;
  currentPrice: number | null;
  currentDate: string | null;
  addedAt: string;
}

export function fetchNotebookEntries(): Promise<NotebookEntry[]> {
  return getJson<NotebookEntry[]>(`/v2/notebook/entries`);
}

export async function addNotebookEntry(entry: NotebookEntry): Promise<void> {
  const res = await fetch(`${BASE}/v2/notebook/entries`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(entry),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
}

export async function updateNotebookNote(entryId: string, note: string): Promise<void> {
  const res = await fetch(`${BASE}/v2/notebook/entries/${entryId}/note`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ note }),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
}

export async function updateNotebookPrices(prices: Record<string, { currentPrice: number; currentDate: string }>): Promise<void> {
  const res = await fetch(`${BASE}/v2/notebook/entries/prices`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prices }),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
}

export async function deleteNotebookEntry(entryId: string): Promise<void> {
  const res = await fetch(`${BASE}/v2/notebook/entries/${entryId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
}
