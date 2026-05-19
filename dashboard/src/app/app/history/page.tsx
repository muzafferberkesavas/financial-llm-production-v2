import Link from "next/link";

import { getCalibrationStatus, getOutcomes, getRuns } from "@/lib/api";
import type { CalibrationStatus, OutcomeRecord, RunSummary } from "@/lib/types";

async function safeOutcomes(): Promise<{
  count: number;
  wins: number;
  losses: number;
  hit_rate: number;
  outcomes: OutcomeRecord[];
}> {
  try {
    return await getOutcomes();
  } catch {
    return { count: 0, wins: 0, losses: 0, hit_rate: 0, outcomes: [] };
  }
}

async function safeCalibration(): Promise<CalibrationStatus | null> {
  try {
    return await getCalibrationStatus();
  } catch {
    return null;
  }
}

async function safeRuns(): Promise<RunSummary[]> {
  try {
    const r = await getRuns(undefined, 30);
    return r.runs;
  } catch {
    return [];
  }
}

export default async function HistoryPage() {
  const [outcomes, calib, runs] = await Promise.all([
    safeOutcomes(),
    safeCalibration(),
    safeRuns(),
  ]);

  return (
    <main className="min-h-screen bg-black text-zinc-100">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <header className="mb-8 flex items-end justify-between border-b border-zinc-800 pb-6">
          <div>
            <h1 className="text-3xl font-bold">History &amp; Calibration</h1>
            <p className="text-sm text-zinc-400 mt-1">
              Realized outcomes + Platt model durumu + son run'lar
            </p>
            <nav className="mt-3 flex gap-4 text-sm">
              <Link href="/" className="text-zinc-500 hover:text-zinc-100">
                ← Signals
              </Link>
              <Link href="/portfolio" className="text-zinc-500 hover:text-zinc-100">
                Portfolio
              </Link>
            </nav>
          </div>
        </header>

        {/* Calibration status */}
        <section className="mb-8 rounded border border-zinc-800 bg-zinc-950 p-6">
          <h2 className="text-xl font-bold mb-3">Platt Calibration</h2>
          {calib?.is_trained ? (
            <div className="grid grid-cols-4 gap-4 text-sm">
              <Box label="Status" value="TRAINED" accent="emerald" />
              <Box label="Train Size" value={calib.n_train.toString()} />
              <Box
                label="Historical Hit Rate"
                value={
                  calib.historical_hit_rate
                    ? `${(calib.historical_hit_rate * 100).toFixed(1)}%`
                    : "-"
                }
                accent={calib.historical_hit_rate && calib.historical_hit_rate >= 0.5 ? "emerald" : "rose"}
              />
              <Box
                label="Last Trained"
                value={calib.trained_at ? new Date(calib.trained_at).toLocaleDateString("tr-TR") : "-"}
              />
            </div>
          ) : (
            <div>
              <p className="text-zinc-400 text-sm mb-2">
                Henüz eğitilmedi (en az 30 closed outcome gerekli).
              </p>
              <p className="text-zinc-500 text-xs">
                Current: <span className="text-zinc-300">{calib?.n_train ?? 0}</span> closed records.
                Sinyal sonuçları dolarak Platt modeli otomatik eğitilecek.
              </p>
            </div>
          )}
        </section>

        {/* Outcomes summary */}
        <section className="mb-8 rounded border border-zinc-800 bg-zinc-950 p-6">
          <h2 className="text-xl font-bold mb-3">Outcomes Summary</h2>
          <div className="grid grid-cols-4 gap-4 text-sm mb-4">
            <Box label="Total" value={outcomes.count.toString()} />
            <Box label="Wins" value={outcomes.wins.toString()} accent="emerald" />
            <Box label="Losses" value={outcomes.losses.toString()} accent="rose" />
            <Box
              label="Hit Rate"
              value={
                outcomes.count
                  ? `${(outcomes.hit_rate * 100).toFixed(1)}%`
                  : "-"
              }
              accent={outcomes.hit_rate >= 0.5 ? "emerald" : outcomes.count > 0 ? "rose" : undefined}
            />
          </div>
          {outcomes.outcomes.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-zinc-800 text-zinc-500">
                    <th className="text-left p-2">Ticker</th>
                    <th className="text-left p-2">Market</th>
                    <th className="text-left p-2">Generated</th>
                    <th className="text-left p-2">Signal</th>
                    <th className="text-right p-2">Conf</th>
                    <th className="text-right p-2">Expected</th>
                    <th className="text-right p-2">Realized</th>
                    <th className="text-left p-2">Status</th>
                    <th className="text-right p-2">Days</th>
                  </tr>
                </thead>
                <tbody>
                  {outcomes.outcomes.slice(0, 20).map((o, i) => (
                    <tr key={`${o.run_id}-${o.ticker}-${i}`} className="border-b border-zinc-900">
                      <td className="p-2 font-semibold">{o.ticker}</td>
                      <td className="p-2 text-zinc-500">{o.market}</td>
                      <td className="p-2 text-zinc-500">
                        {new Date(o.generated_at).toLocaleDateString("tr-TR")}
                      </td>
                      <td className="p-2">{o.signal}</td>
                      <td className="p-2 text-right tabular-nums">
                        {(o.confidence * 100).toFixed(0)}%
                      </td>
                      <td className="p-2 text-right text-zinc-400 tabular-nums">
                        {o.expected_return_pct !== null
                          ? `${o.expected_return_pct > 0 ? "+" : ""}${o.expected_return_pct.toFixed(1)}%`
                          : "-"}
                      </td>
                      <td
                        className={`p-2 text-right tabular-nums ${
                          o.realized_return_pct !== null && o.realized_return_pct >= 0
                            ? "text-emerald-400"
                            : o.realized_return_pct !== null
                              ? "text-rose-400"
                              : "text-zinc-600"
                        }`}
                      >
                        {o.realized_return_pct !== null
                          ? `${o.realized_return_pct > 0 ? "+" : ""}${o.realized_return_pct.toFixed(1)}%`
                          : "-"}
                      </td>
                      <td
                        className={`p-2 ${
                          o.status.startsWith("win")
                            ? "text-emerald-400"
                            : o.status.startsWith("loss")
                              ? "text-rose-400"
                              : "text-zinc-500"
                        }`}
                      >
                        {o.status}
                      </td>
                      <td className="p-2 text-right text-zinc-500 tabular-nums">
                        {o.days_held ?? "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* Recent runs */}
        <section className="rounded border border-zinc-800 bg-zinc-950 p-6">
          <h2 className="text-xl font-bold mb-3">Recent Runs</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-zinc-800 text-zinc-500">
                  <th className="text-left p-2">Run ID</th>
                  <th className="text-left p-2">Market</th>
                  <th className="text-left p-2">Mode</th>
                  <th className="text-left p-2">Time</th>
                  <th className="text-right p-2">Universe</th>
                  <th className="text-right p-2">Filter</th>
                  <th className="text-right p-2">Signals</th>
                  <th className="text-right p-2">Actionable</th>
                  <th className="text-right p-2">Cost</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((r) => (
                  <tr key={r.run_id} className="border-b border-zinc-900">
                    <td className="p-2 font-mono text-zinc-400">{r.run_id.split("-").pop()}</td>
                    <td className="p-2">{r.market}</td>
                    <td className="p-2 text-zinc-500">{r.mode}</td>
                    <td className="p-2 text-zinc-500">
                      {new Date(r.started_at).toLocaleString("tr-TR")}
                    </td>
                    <td className="p-2 text-right tabular-nums">{r.universe_size}</td>
                    <td className="p-2 text-right tabular-nums">{r.passed_hard_filter}</td>
                    <td className="p-2 text-right tabular-nums">{r.signals_generated}</td>
                    <td className="p-2 text-right text-emerald-400 tabular-nums">
                      {r.actionable_signals}
                    </td>
                    <td className="p-2 text-right text-zinc-500 tabular-nums">
                      ${r.total_cost_usd.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </main>
  );
}

function Box({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: "emerald" | "rose";
}) {
  const cls =
    accent === "emerald"
      ? "text-emerald-400"
      : accent === "rose"
        ? "text-rose-400"
        : "text-zinc-100";
  return (
    <div className="rounded bg-zinc-900 p-3">
      <div className="text-zinc-500 text-xs">{label}</div>
      <div className={`text-lg font-semibold tabular-nums mt-0.5 ${cls}`}>{value}</div>
    </div>
  );
}
