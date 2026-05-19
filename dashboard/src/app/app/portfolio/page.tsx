import Link from "next/link";

import { getPortfolio } from "@/lib/api";
import type { Market, PortfolioResponse } from "@/lib/types";

async function safe(market: Market): Promise<PortfolioResponse | null> {
  try {
    return await getPortfolio(market);
  } catch {
    return null;
  }
}

export default async function PortfolioPage() {
  const [nasdaq, bist] = await Promise.all([safe("nasdaq"), safe("bist")]);

  return (
    <main className="min-h-screen bg-black text-zinc-100">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <header className="mb-8 flex items-end justify-between border-b border-zinc-800 pb-6">
          <div>
            <h1 className="text-3xl font-bold">Portfolio Allocation</h1>
            <p className="text-sm text-zinc-400 mt-1">
              Confidence × expected return × probability weighted positions
            </p>
            <nav className="mt-3 flex gap-4 text-sm">
              <Link href="/" className="text-zinc-500 hover:text-zinc-100">
                ← Back to Signals
              </Link>
              <Link href="/history" className="text-zinc-500 hover:text-zinc-100">
                History
              </Link>
            </nav>
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <PortfolioBlock data={nasdaq} marketLabel="NASDAQ" />
          <PortfolioBlock data={bist} marketLabel="BIST" />
        </div>

        <footer className="mt-12 pt-6 border-t border-zinc-800 text-xs text-zinc-500">
          Pozisyonlar son pipeline run'undan. Gerçek sahiplik için broker'da işlem yapın.
        </footer>
      </div>
    </main>
  );
}

function PortfolioBlock({
  data,
  marketLabel,
}: {
  data: PortfolioResponse | null;
  marketLabel: string;
}) {
  const cur = marketLabel === "BIST" ? "₺" : "$";

  if (!data) {
    return (
      <div className="rounded border border-zinc-800 bg-zinc-950 p-6">
        <h2 className="text-xl font-bold mb-3">{marketLabel}</h2>
        <p className="text-zinc-500 text-sm">No portfolio data yet.</p>
      </div>
    );
  }

  const cashPct = (data.cash_remaining / data.total_capital) * 100;
  const allocatedPct = (data.allocated_total / data.total_capital) * 100;

  return (
    <div className="rounded border border-zinc-800 bg-zinc-950 p-6 space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-xl font-bold">{marketLabel}</h2>
          <p className="text-xs text-zinc-500 mt-1">
            {new Date(data.as_of).toLocaleString("tr-TR")}
          </p>
        </div>
        <div className="text-right">
          <div className="text-xs text-zinc-500">Total Capital</div>
          <div className="text-xl font-semibold tabular-nums">
            {cur}
            {data.total_capital.toLocaleString()}
          </div>
        </div>
      </div>

      {/* Allocation bar */}
      <div className="space-y-2">
        <div className="flex justify-between text-xs">
          <span className="text-emerald-400">
            Allocated: {cur}
            {data.allocated_total.toLocaleString()} ({allocatedPct.toFixed(1)}%)
          </span>
          <span className="text-zinc-400">
            Cash: {cur}
            {data.cash_remaining.toLocaleString()} ({cashPct.toFixed(1)}%)
          </span>
        </div>
        <div className="h-2 bg-zinc-800 rounded overflow-hidden flex">
          <div
            className="bg-emerald-500"
            style={{ width: `${allocatedPct}%` }}
          />
          <div className="bg-zinc-600" style={{ width: `${cashPct}%` }} />
        </div>
      </div>

      {/* Positions */}
      {data.positions.length === 0 ? (
        <p className="text-sm text-zinc-500 py-4">No active positions.</p>
      ) : (
        <div className="space-y-2">
          {data.positions.map((p) => (
            <div
              key={p.ticker}
              className="rounded bg-zinc-900 p-3 grid grid-cols-12 gap-2 items-center text-sm"
            >
              <div className="col-span-3">
                <div className="font-semibold tabular-nums">{p.ticker}</div>
                <div className="text-[10px] text-zinc-500">{p.sector}</div>
              </div>
              <div className="col-span-2">
                <div
                  className={`text-xs font-semibold ${
                    p.signal === "GUCLU_AL" || p.signal === "AL"
                      ? "text-emerald-400"
                      : "text-zinc-400"
                  }`}
                >
                  {p.signal}
                </div>
                <div className="text-[10px] text-zinc-500 tabular-nums">
                  conf {(p.confidence * 100).toFixed(0)}%
                </div>
              </div>
              <div className="col-span-3 text-right">
                <div className="font-semibold tabular-nums">
                  {cur}
                  {p.allocation_cash.toLocaleString()}
                </div>
                <div className="text-[10px] text-zinc-500 tabular-nums">
                  {(p.allocation_weight * 100).toFixed(1)}% of portfolio
                </div>
              </div>
              <div className="col-span-2 text-right">
                {p.expected_return_pct !== null && p.expected_return_pct !== undefined ? (
                  <div className="text-emerald-400 font-semibold tabular-nums">
                    +{p.expected_return_pct.toFixed(1)}%
                  </div>
                ) : (
                  <div className="text-zinc-500">-</div>
                )}
                <div className="text-[10px] text-zinc-500 tabular-nums">
                  {p.time_horizon_days}d horizon
                </div>
              </div>
              <div className="col-span-2 text-right text-[10px] text-zinc-500">
                {p.entry_zone_low && p.stop_loss ? (
                  <>
                    <div>
                      E: {cur}
                      {p.entry_zone_low.toFixed(2)}-
                      {p.entry_zone_high?.toFixed(2)}
                    </div>
                    <div>
                      S: {cur}
                      {p.stop_loss.toFixed(2)}
                    </div>
                  </>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
