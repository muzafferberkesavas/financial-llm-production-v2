/**
 * FinLLM v2 API client — backend/src/finllm/api/main.py'ye bağlanır.
 *
 * Env:
 *   BACKEND_API_URL  → http://localhost:8000 (default dev)
 *   API_BEARER_TOKEN → admin endpoint'ler için
 *
 * Routes covered:
 *   GET  /v2/signals/latest
 *   GET  /v2/signals/by-ticker/{ticker}
 *   GET  /v2/signals/runs
 *   GET  /v2/portfolio
 *   GET  /v2/portfolio/{market}
 *   GET  /v2/history/outcomes
 *   GET  /v2/history/calibration
 */

import type {
  CalibrationStatus,
  ExtendedSignal,
  Market,
  OutcomeRecord,
  PortfolioResponse,
  RunSummary,
  SignalsResponse,
} from "./types";

function backendUrl(): string {
  return process.env.BACKEND_API_URL ?? "http://localhost:8000";
}

function bearer(): string | null {
  return process.env.API_BEARER_TOKEN ?? null;
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const token = bearer();
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init?.body) headers.set("Content-Type", "application/json");

  const res = await fetch(`${backendUrl()}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(`API ${path}: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

// ---- Signals ----

export async function getLatestSignals(
  market?: Market,
  actionableOnly = false
): Promise<SignalsResponse> {
  const params = new URLSearchParams();
  if (market) params.set("market", market);
  if (actionableOnly) params.set("actionable_only", "true");
  return fetchJson<SignalsResponse>(`/v2/signals/latest?${params}`);
}

export async function getSignalByTicker(
  ticker: string,
  lookback = 10
): Promise<{ summary: RunSummary; signal: ExtendedSignal }> {
  return fetchJson(
    `/v2/signals/by-ticker/${encodeURIComponent(ticker.toUpperCase())}?lookback=${lookback}`
  );
}

export async function getRuns(
  market?: Market,
  limit = 20
): Promise<{ runs: RunSummary[]; count: number }> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (market) params.set("market", market);
  return fetchJson(`/v2/signals/runs?${params}`);
}

// ---- Portfolio ----

export async function getPortfolio(market: Market): Promise<PortfolioResponse> {
  return fetchJson(`/v2/portfolio/${market}`);
}

export async function getAllPortfolios(): Promise<{
  portfolios: Record<Market, RunSummary | undefined>;
}> {
  return fetchJson(`/v2/portfolio/`);
}

// ---- History ----

export async function getOutcomes(
  market?: Market,
  status?: string,
  limit = 100
): Promise<{
  count: number;
  wins: number;
  losses: number;
  hit_rate: number;
  outcomes: OutcomeRecord[];
}> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (market) params.set("market", market);
  if (status) params.set("status", status);
  return fetchJson(`/v2/history/outcomes?${params}`);
}

export async function getCalibrationStatus(): Promise<CalibrationStatus> {
  return fetchJson(`/v2/history/calibration`);
}

// ---- Triggers (admin) ----

export async function triggerRun(opts: {
  market: Market;
  mode?: "pre_market" | "intraday" | "end_of_day";
  capital?: number;
  llm_backend?: "mock" | "claude" | "claude-screen-only" | "claude-deep-only";
}): Promise<{ queued: boolean; message: string }> {
  return fetchJson(`/v2/trigger/run`, {
    method: "POST",
    body: JSON.stringify(opts),
  });
}
