import { SignalCard } from "@/components/signal-card";
import type { Signal } from "@/lib/types";
import { MOCK_SIGNALS } from "@/lib/mock-signals";

async function getSignals(): Promise<Signal[]> {
  const backend = process.env.BACKEND_API_URL;
  if (backend) {
    try {
      const r = await fetch(`${backend}/signals/latest`, { cache: "no-store" });
      if (r.ok) {
        const data = await r.json();
        return data.signals ?? [];
      }
    } catch {
      // fall through to mock below
    }
  }
  return MOCK_SIGNALS;
}

export default async function Home() {
  const signals = await getSignals();
  const buys = signals.filter((s) => s.direction === "BUY").length;
  const sells = signals.filter((s) => s.direction === "SELL").length;

  return (
    <main className="min-h-screen bg-black text-zinc-100">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <header className="mb-8 flex items-end justify-between border-b border-zinc-800 pb-6">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">FinLLM Swing Signals</h1>
            <p className="text-sm text-zinc-400 mt-1">
              Hibrit model: FinBERT sentiment + Qlib teknik + Claude meta-karar
            </p>
          </div>
          <div className="flex gap-6 text-sm">
            <div>
              <span className="text-zinc-500">Sinyaller</span>
              <p className="text-zinc-100 font-semibold tabular-nums">{signals.length}</p>
            </div>
            <div>
              <span className="text-zinc-500">AL</span>
              <p className="text-emerald-400 font-semibold tabular-nums">{buys}</p>
            </div>
            <div>
              <span className="text-zinc-500">SAT</span>
              <p className="text-rose-400 font-semibold tabular-nums">{sells}</p>
            </div>
          </div>
        </header>

        {signals.length === 0 ? (
          <div className="text-center py-20 text-zinc-500">
            Henüz sinyal yok. Backend'i çalıştır veya MOCK_SIGNALS'ı kontrol et.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {signals.map((s) => (
              <SignalCard key={s.symbol} signal={s} />
            ))}
          </div>
        )}

        <footer className="mt-12 pt-6 border-t border-zinc-800 text-xs text-zinc-500">
          Bu yatırım tavsiyesi değildir. Sadece araştırma amaçlıdır.
        </footer>
      </div>
    </main>
  );
}
