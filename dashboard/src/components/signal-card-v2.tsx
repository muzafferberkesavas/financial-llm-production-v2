import type { ExtendedSignal } from "@/lib/types";

const SIGNAL_COLORS: Record<string, string> = {
  GUCLU_AL: "bg-emerald-700 text-emerald-50",
  AL: "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30",
  IZLE: "bg-blue-500/20 text-blue-300 border border-blue-500/30",
  TUT: "bg-zinc-500/20 text-zinc-400 border border-zinc-500/30",
  KISMI_SAT: "bg-orange-500/20 text-orange-300 border border-orange-500/30",
  SAT: "bg-rose-500/20 text-rose-300 border border-rose-500/30",
  ACIL_SAT: "bg-rose-700 text-rose-50",
};

function currencySymbol(market: string): string {
  return market === "bist" ? "₺" : "$";
}

export function SignalCardV2({ signal }: { signal: ExtendedSignal }) {
  const cur = currencySymbol(signal.market);
  const colorClass = SIGNAL_COLORS[signal.signal] ?? SIGNAL_COLORS.TUT;
  const baseScenario = signal.scenarios.find((s) => s.label === "base");
  const bullScenario = signal.scenarios.find((s) => s.label === "bull");
  const bearScenario = signal.scenarios.find((s) => s.label === "bear");

  return (
    <article className="rounded-lg border border-zinc-800 bg-zinc-950 p-5 space-y-3 hover:border-zinc-700 transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold tabular-nums">{signal.ticker}</span>
            {signal.unsourced_flag && (
              <span
                title="LLM unsourced data flag"
                className="text-xs bg-amber-900/50 text-amber-300 px-1.5 py-0.5 rounded"
              >
                ⚠️ UNSOURCED
              </span>
            )}
          </div>
          {signal.name && (
            <p className="text-xs text-zinc-500 mt-0.5">
              {signal.name} • {signal.sector}
            </p>
          )}
        </div>
        <span
          className={`px-3 py-1 rounded text-xs font-semibold tabular-nums ${colorClass}`}
        >
          {signal.signal.replace("_", " ")}
        </span>
      </div>

      {/* Key metrics row */}
      <div className="grid grid-cols-3 gap-2 text-xs">
        <div>
          <div className="text-zinc-500">Confidence</div>
          <div className="text-zinc-100 font-semibold tabular-nums">
            {(signal.confidence * 100).toFixed(0)}%
            {signal.calibrated_probability !== null &&
              signal.calibrated_probability !== signal.confidence && (
                <span className="text-zinc-500 text-[10px] ml-1">
                  (cal {(signal.calibrated_probability! * 100).toFixed(0)}%)
                </span>
              )}
          </div>
        </div>
        <div>
          <div className="text-zinc-500">Expected</div>
          <div
            className={
              signal.expected_return_pct && signal.expected_return_pct > 0
                ? "text-emerald-400 font-semibold tabular-nums"
                : "text-zinc-400 font-semibold tabular-nums"
            }
          >
            {signal.expected_return_pct
              ? `${signal.expected_return_pct > 0 ? "+" : ""}${signal.expected_return_pct.toFixed(1)}%`
              : "-"}
          </div>
        </div>
        <div>
          <div className="text-zinc-500">Horizon</div>
          <div className="text-zinc-100 font-semibold tabular-nums">
            {signal.time_horizon_days ? `${signal.time_horizon_days}d` : "-"}
          </div>
        </div>
      </div>

      {/* Allocation */}
      {signal.allocation_cash > 0 && (
        <div className="bg-zinc-900 rounded p-2.5 text-xs">
          <div className="flex items-center justify-between">
            <span className="text-zinc-500">Allocation</span>
            <span className="text-zinc-100 font-semibold tabular-nums">
              {cur}
              {signal.allocation_cash.toLocaleString()}
            </span>
          </div>
          <div className="flex items-center gap-2 mt-1">
            <div className="flex-1 h-1.5 bg-zinc-800 rounded overflow-hidden">
              <div
                className="h-full bg-emerald-500"
                style={{
                  width: `${Math.min(signal.allocation_weight * 100, 100)}%`,
                }}
              />
            </div>
            <span className="text-zinc-500 tabular-nums text-[10px]">
              {(signal.allocation_weight * 100).toFixed(1)}%
            </span>
          </div>
        </div>
      )}

      {/* Entry/Stop */}
      {signal.entry_zone_low && signal.stop_loss && (
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="rounded bg-emerald-950/50 border border-emerald-900/50 p-2">
            <div className="text-emerald-500/70 text-[10px]">Entry</div>
            <div className="text-emerald-300 font-mono tabular-nums">
              {cur}
              {signal.entry_zone_low.toFixed(2)} - {cur}
              {signal.entry_zone_high?.toFixed(2)}
            </div>
          </div>
          <div className="rounded bg-rose-950/50 border border-rose-900/50 p-2">
            <div className="text-rose-500/70 text-[10px]">Stop</div>
            <div className="text-rose-300 font-mono tabular-nums">
              {cur}
              {signal.stop_loss.toFixed(2)}
            </div>
          </div>
        </div>
      )}

      {/* Scenarios */}
      {signal.scenarios.length > 0 && (
        <div className="space-y-1.5 text-xs">
          {baseScenario && (
            <ScenarioRow label="Base" scenario={baseScenario} cur={cur} accent="zinc" />
          )}
          {bullScenario && (
            <ScenarioRow label="Bull" scenario={bullScenario} cur={cur} accent="emerald" />
          )}
          {bearScenario && (
            <ScenarioRow label="Bear" scenario={bearScenario} cur={cur} accent="rose" />
          )}
        </div>
      )}

      {/* Regime + Confluence */}
      <div className="flex items-center gap-2 text-[11px] flex-wrap">
        <span className="bg-zinc-900 text-zinc-400 px-1.5 py-0.5 rounded">
          Regime: {signal.market_regime}
        </span>
        <span className="bg-zinc-900 text-zinc-400 px-1.5 py-0.5 rounded">
          Weekly: {signal.weekly_trend}
        </span>
        <span className="bg-zinc-900 text-zinc-400 px-1.5 py-0.5 rounded">
          Confluence: {signal.confluence_score}/100
        </span>
        {signal.confirmation_count > 0 && (
          <span className="bg-zinc-900 text-zinc-400 px-1.5 py-0.5 rounded">
            {signal.confirmation_count}/6 confirms
          </span>
        )}
      </div>

      {/* Warning flags */}
      {signal.warning_flags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {signal.warning_flags.slice(0, 4).map((flag) => (
            <span
              key={flag}
              className="text-[10px] bg-amber-900/30 text-amber-300/80 px-1.5 py-0.5 rounded border border-amber-800/40"
            >
              {flag}
            </span>
          ))}
        </div>
      )}

      {/* Rationale */}
      {signal.rationale.full && (
        <p className="text-xs text-zinc-400 leading-relaxed border-t border-zinc-800 pt-2.5">
          {signal.rationale.full.slice(0, 350)}
          {signal.rationale.full.length > 350 && "..."}
        </p>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between text-[10px] text-zinc-600 pt-1">
        <span>{new Date(signal.generated_at).toLocaleString("tr-TR")}</span>
        <span>
          {signal.llm_model} · ${signal.llm_cost_usd.toFixed(3)}
        </span>
      </div>
    </article>
  );
}

function ScenarioRow({
  label,
  scenario,
  cur,
  accent,
}: {
  label: string;
  scenario: { target_price: number; probability: number; expected_return_pct: number };
  cur: string;
  accent: "zinc" | "emerald" | "rose";
}) {
  const labelColor =
    accent === "emerald"
      ? "text-emerald-400"
      : accent === "rose"
        ? "text-rose-400"
        : "text-zinc-400";
  return (
    <div className="flex items-center justify-between">
      <span className={`${labelColor} font-medium w-12`}>{label}:</span>
      <span className="text-zinc-300 font-mono tabular-nums">
        {cur}
        {scenario.target_price.toFixed(2)}
      </span>
      <span className="text-zinc-500 tabular-nums">
        {(scenario.probability * 100).toFixed(0)}%
      </span>
      <span
        className={
          scenario.expected_return_pct >= 0 ? "text-emerald-400 tabular-nums" : "text-rose-400 tabular-nums"
        }
      >
        {scenario.expected_return_pct >= 0 ? "+" : ""}
        {scenario.expected_return_pct.toFixed(1)}%
      </span>
    </div>
  );
}
