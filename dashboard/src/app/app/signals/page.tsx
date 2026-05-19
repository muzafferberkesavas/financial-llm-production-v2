import Link from "next/link";

import { SignalCardV2 } from "@/components/signal-card-v2";
import { getLatestSignals } from "@/lib/api";
import type { ExtendedSignal, Market, SignalsResponse } from "@/lib/types";

async function safeFetch(market: Market): Promise<SignalsResponse | null> {
  try {
    return await getLatestSignals(market);
  } catch {
    return null;
  }
}

export default async function Home({
  searchParams,
}: {
  searchParams: Promise<{ market?: string }>;
}) {
  const params = await searchParams;
  const selectedMarket = (params.market === "bist" ? "bist" : "nasdaq") as Market;

  const data = await safeFetch(selectedMarket);
  const signals: ExtendedSignal[] = data?.signals ?? [];

  const buys = signals.filter((s) => ["AL", "GUCLU_AL"].includes(s.signal)).length;
  const watches = signals.filter((s) => s.signal === "IZLE").length;
  const sells = signals.filter((s) =>
    ["SAT", "KISMI_SAT", "ACIL_SAT"].includes(s.signal)
  ).length;
  const actionable = signals.filter((s) => s.is_actionable).length;

  return (
    <main className="min-h-screen bg-black text-zinc-100">
      <div className="mx-auto max-w-7xl px-6 py-10">
        <header className="mb-8 flex items-end justify-between border-b border-zinc-800 pb-6">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">
              FinLLM Cross-Market
            </h1>
            <p className="text-sm text-zinc-400 mt-1">
              AI swing-trading sinyalleri • Claude Opus 4.7 + News + Calibration
            </p>
            <nav className="mt-3 flex gap-4 text-sm">
              <Link
                href="/?market=nasdaq"
                className={`hover:text-zinc-100 transition ${
                  selectedMarket === "nasdaq" ? "text-zinc-100 font-semibold" : "text-zinc-500"
                }`}
              >
                NASDAQ
              </Link>
              <Link
                href="/?market=bist"
                className={`hover:text-zinc-100 transition ${
                  selectedMarket === "bist" ? "text-zinc-100 font-semibold" : "text-zinc-500"
                }`}
              >
                BIST
              </Link>
              <Link href="/portfolio" className="text-zinc-500 hover:text-zinc-100 transition">
                Portfolio
              </Link>
              <Link href="/history" className="text-zinc-500 hover:text-zinc-100 transition">
                History
              </Link>
            </nav>
          </div>

          <div className="grid grid-cols-4 gap-4 text-sm">
            <Stat label="Signals" value={signals.length} />
            <Stat label="AL" value={buys} accent="emerald" />
            <Stat label="IZLE" value={watches} accent="blue" />
            <Stat label="SAT" value={sells} accent="rose" />
          </div>
        </header>

        {data?.summary && (
          <div className="mb-6 rounded border border-zinc-800 bg-zinc-950 px-4 py-3 text-xs flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-4 flex-wrap">
              <span className="text-zinc-500">Run:</span>
              <code className="text-zinc-300">{data.summary.run_id}</code>
              <span className="text-zinc-500">•</span>
              <span className="text-zinc-400">
                {new Date(data.summary.started_at).toLocaleString("tr-TR")}
              </span>
              <span className="text-zinc-500">•</span>
              <span className="text-zinc-400">
                Universe {data.summary.universe_size} → {data.summary.passed_hard_filter} →{" "}
                {actionable} actionable
              </span>
            </div>
            <div className="flex items-center gap-4">
              {data.summary.regime?.vix !== null && data.summary.regime?.vix !== undefined && (
                <span className="text-zinc-400">
                  VIX: <span className="text-zinc-200">{data.summary.regime.vix.toFixed(1)}</span>
                </span>
              )}
              <span className="text-zinc-400">
                Cost: <span className="text-zinc-200">${data.summary.total_cost_usd.toFixed(2)}</span>
              </span>
              <span className="text-zinc-400">
                Duration:{" "}
                <span className="text-zinc-200">{data.summary.total_duration_sec.toFixed(0)}s</span>
              </span>
            </div>
          </div>
        )}

        {signals.length === 0 ? (
          <div className="text-center py-24 text-zinc-500">
            <p className="text-lg mb-2">
              {selectedMarket.toUpperCase()} için henüz sinyal yok.
            </p>
            <p className="text-xs mb-4">Backend'i başlat ve pipeline'ı tetikle:</p>
            <code className="text-zinc-400 bg-zinc-950 px-3 py-1 rounded text-xs">
              python scripts/run_funnel.py --market {selectedMarket} --llm claude
            </code>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {signals.map((s) => (
              <SignalCardV2 key={`${s.market}-${s.ticker}-${s.run_id}`} signal={s} />
            ))}
          </div>
        )}

        <footer className="mt-12 pt-6 border-t border-zinc-800 text-xs text-zinc-500">
          ⚠️ Bu yatırım tavsiyesi değildir, araştırma amaçlıdır. Her sinyali kendi
          değerlendirmenize tabi tutun.
        </footer>
      </div>
    </main>
  );
}

function Stat({
  label,
  value,
  accent,
}: {
  label: string;
  value: number;
  accent?: "emerald" | "blue" | "rose";
}) {
  const valueClass =
    accent === "emerald"
      ? "text-emerald-400"
      : accent === "blue"
        ? "text-blue-400"
        : accent === "rose"
          ? "text-rose-400"
          : "text-zinc-100";

  return (
    <div>
      <span className="text-zinc-500 text-xs">{label}</span>
      <p className={`${valueClass} font-semibold text-2xl tabular-nums`}>{value}</p>
    </div>
  );
}
