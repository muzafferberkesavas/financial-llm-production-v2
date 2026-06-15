import type { SignalsResponse, PortfolioResponse, Market } from "@/types";

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
