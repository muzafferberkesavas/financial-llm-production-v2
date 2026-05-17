import { cn } from "@/lib/utils";
import type { Signal } from "@/lib/types";

const directionStyles: Record<Signal["direction"], string> = {
  BUY: "bg-emerald-500/15 text-emerald-400 border-emerald-500/40",
  SELL: "bg-rose-500/15 text-rose-400 border-rose-500/40",
  HOLD: "bg-zinc-500/15 text-zinc-400 border-zinc-500/40",
};

function ScoreBar({ value, label }: { value: number; label: string }) {
  const pct = ((value + 1) / 2) * 100;
  const color = value > 0.1 ? "bg-emerald-500" : value < -0.1 ? "bg-rose-500" : "bg-zinc-500";
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-zinc-400">
        <span>{label}</span>
        <span className="tabular-nums">{value > 0 ? "+" : ""}{value.toFixed(2)}</span>
      </div>
      <div className="h-1.5 bg-zinc-800 rounded-full overflow-hidden">
        <div className={cn("h-full transition-all", color)} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function SignalCard({ signal }: { signal: Signal }) {
  return (
    <article className="rounded-lg border border-zinc-800 bg-zinc-950 p-5 hover:border-zinc-700 transition-colors">
      <header className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-xl font-bold text-zinc-50">{signal.symbol}</h3>
          <p className="text-xs text-zinc-500 mt-0.5">
            ${signal.entryPrice.toFixed(2)} • {signal.holdingDays.min}-{signal.holdingDays.max} gün
          </p>
        </div>
        <div
          className={cn(
            "px-3 py-1 rounded-md border text-sm font-semibold",
            directionStyles[signal.direction],
          )}
        >
          {signal.direction}
        </div>
      </header>

      <div className="grid grid-cols-2 gap-3 mb-4 text-sm">
        <div>
          <span className="text-zinc-500">Güven</span>
          <p className="text-zinc-100 font-semibold tabular-nums">
            {(signal.confidence * 100).toFixed(0)}%
          </p>
        </div>
        {signal.expectedReturn !== undefined && (
          <div>
            <span className="text-zinc-500">Beklenen getiri</span>
            <p className="text-emerald-400 font-semibold tabular-nums">
              +{(signal.expectedReturn * 100).toFixed(1)}%
            </p>
          </div>
        )}
        {signal.targetPrice && (
          <div>
            <span className="text-zinc-500">Hedef</span>
            <p className="text-zinc-100 tabular-nums">${signal.targetPrice.toFixed(2)}</p>
          </div>
        )}
        {signal.stopLoss && (
          <div>
            <span className="text-zinc-500">Stop</span>
            <p className="text-zinc-100 tabular-nums">${signal.stopLoss.toFixed(2)}</p>
          </div>
        )}
      </div>

      <div className="space-y-2 mb-4">
        <ScoreBar value={signal.signals.technical.score} label="Teknik" />
        <ScoreBar value={signal.signals.sentiment.score} label="Sentiment" />
        {signal.signals.fundamental && (
          <ScoreBar value={signal.signals.fundamental.score} label="Temel" />
        )}
      </div>

      <p className="text-sm text-zinc-400 leading-relaxed">{signal.rationale}</p>
    </article>
  );
}
