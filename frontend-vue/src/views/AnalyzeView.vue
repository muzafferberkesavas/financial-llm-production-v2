<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { useRouter } from "vue-router";
import type { AnalysisResponse, AnalysisSignal } from "@/types";
import { ACTION_META } from "@/types";
import { runBistAnalysis, fetchLatestAnalysis } from "@/lib/api";

const router = useRouter();
const analysis = ref<AnalysisResponse | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);
const expandedTicker = ref<string | null>(null);
const llmBackend = ref("claude");

onMounted(async () => {
  try {
    const latest = await fetchLatestAnalysis();
    if (latest.status !== "no_analysis") {
      analysis.value = latest;
    }
  } catch { /* no previous analysis */ }
});

async function startAnalysis() {
  loading.value = true;
  error.value = null;
  analysis.value = null;
  try {
    analysis.value = await runBistAnalysis({ llm_backend: llmBackend.value });
  } catch (e: any) {
    error.value = e.message ?? "Analiz basarisiz";
  } finally {
    loading.value = false;
  }
}

function toggleExpand(ticker: string) {
  expandedTicker.value = expandedTicker.value === ticker ? null : ticker;
}

function fmtPct(val: number | null | undefined): string {
  if (val == null) return "—";
  const sign = val >= 0 ? "+" : "";
  return `${sign}${val.toFixed(2)}%`;
}

function fmtPrice(val: number | null | undefined): string {
  if (val == null) return "—";
  return val.toLocaleString("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function signalClass(signal: string): string {
  const meta = ACTION_META[signal as keyof typeof ACTION_META];
  if (!meta) return "";
  return { bull: "text-bull", bear: "text-bear", watch: "text-watch" }[meta.tone] ?? "";
}

function signalBgClass(signal: string): string {
  const meta = ACTION_META[signal as keyof typeof ACTION_META];
  if (!meta) return "";
  return { bull: "bg-bull/10 border-bull/30", bear: "bg-bear/10 border-bear/30", watch: "bg-watch/10 border-watch/30" }[meta.tone] ?? "";
}

function scenarioColor(label: string): string {
  return { bull: "text-bull", bear: "text-bear", base: "text-accent" }[label] ?? "text-muted";
}

function goToDetail(ticker: string) {
  router.push({ name: "stock-detail", params: { ticker }, query: { market: "bist" } });
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex flex-wrap items-center justify-between gap-4">
      <div>
        <h1 class="text-xl font-bold tracking-tight">BIST Analiz</h1>
        <p class="text-xs text-muted mt-1">
          Master Scorecard + Pipeline filtreleri + Opus derin analiz
        </p>
      </div>
      <div class="flex items-center gap-3">
        <select
          v-model="llmBackend"
          class="rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text outline-none"
        >
          <option value="claude">Claude Opus (gercek)</option>
          <option value="mock">Mock (test)</option>
        </select>
        <button
          class="rounded-lg bg-accent px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-accent/80 disabled:opacity-50"
          :disabled="loading"
          @click="startAnalysis"
        >
          <span v-if="loading" class="inline-flex items-center gap-2">
            <span class="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
            Analiz ediliyor...
          </span>
          <span v-else>Analiz Et</span>
        </button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="card p-8 text-center">
      <div class="inline-block h-8 w-8 animate-spin rounded-full border-3 border-accent/30 border-t-accent mb-3" />
      <p class="text-sm text-muted">Pipeline calisiyor: veri cekme → filtreleme → skorlama → LLM analiz...</p>
      <p class="text-xs text-faint mt-1">Bu islem 1-3 dakika surebilir</p>
    </div>

    <!-- Error -->
    <div v-if="error" class="rounded-xl border border-bear/30 bg-bear/5 p-4 text-sm text-bear">
      {{ error }}
    </div>

    <!-- Results -->
    <template v-if="analysis && analysis.status !== 'no_analysis'">
      <!-- Summary bar -->
      <div class="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6">
        <div class="card p-3">
          <div class="text-[10px] text-faint uppercase">Evren</div>
          <div class="num text-xl font-semibold">{{ analysis.universe_size }}</div>
        </div>
        <div class="card p-3">
          <div class="text-[10px] text-faint uppercase">Filtre Gecen</div>
          <div class="num text-xl font-semibold">{{ analysis.passed_filter }}</div>
        </div>
        <div class="card p-3">
          <div class="text-[10px] text-faint uppercase">Analiz Edilen</div>
          <div class="num text-xl font-semibold">{{ analysis.analyzed_count }}</div>
        </div>
        <div class="card p-3">
          <div class="text-[10px] text-faint uppercase">AL Sinyali</div>
          <div class="num text-xl font-semibold text-bull">{{ analysis.buy_signals.length }}</div>
        </div>
        <div class="card p-3">
          <div class="text-[10px] text-faint uppercase">Sure</div>
          <div class="num text-xl font-semibold">{{ analysis.duration_sec }}s</div>
        </div>
        <div class="card p-3">
          <div class="text-[10px] text-faint uppercase">LLM Maliyet</div>
          <div class="num text-xl font-semibold">${{ analysis.total_cost_usd }}</div>
        </div>
      </div>

      <!-- Signal cards -->
      <div v-if="!analysis.signals.length" class="card p-8 text-center text-muted">
        Pipeline sonucunda sinyal uretilemedi. Filtreler cok katiydi veya piyasa kosullari uygun degil.
      </div>

      <div v-for="sig in analysis.signals" :key="sig.ticker" class="card overflow-hidden">
        <!-- Signal header -->
        <div
          class="flex items-center justify-between p-4 cursor-pointer hover:bg-surface-2 transition"
          @click="toggleExpand(sig.ticker)"
        >
          <div class="flex items-center gap-3">
            <div class="flex flex-col">
              <div class="flex items-center gap-2">
                <span class="num text-lg font-bold cursor-pointer hover:text-accent" @click.stop="goToDetail(sig.ticker)">
                  {{ sig.ticker }}
                </span>
                <span class="text-xs text-muted">{{ sig.name }}</span>
                <span class="rounded-md bg-surface-2 px-1.5 py-0.5 text-[10px] text-faint">{{ sig.sector }}</span>
              </div>
              <div class="flex items-center gap-2 mt-0.5 text-[11px] text-faint">
                <span>Skor: <span class="num text-muted">{{ sig.master_score_pct?.toFixed(0) ?? '—' }}%</span></span>
                <span>Confluence: <span class="num text-muted">{{ sig.confluence_score }}</span></span>
                <span>Rejim: <span class="capitalize text-muted">{{ sig.market_regime }}</span></span>
              </div>
            </div>
          </div>
          <div class="flex items-center gap-4">
            <div class="text-right">
              <div class="rounded-lg border px-3 py-1 text-sm font-bold" :class="signalBgClass(sig.signal)">
                <span :class="signalClass(sig.signal)">{{ ACTION_META[sig.signal]?.label ?? sig.signal }}</span>
              </div>
              <div class="num text-xs text-muted mt-0.5">guven {{ (sig.confidence * 100).toFixed(0) }}%</div>
            </div>
            <span class="text-muted transition" :class="expandedTicker === sig.ticker ? 'rotate-180' : ''">▾</span>
          </div>
        </div>

        <!-- Expanded detail -->
        <div v-if="expandedTicker === sig.ticker" class="border-t border-border p-5 space-y-5">
          <!-- Price scenarios -->
          <section v-if="sig.scenarios.length">
            <h3 class="text-xs font-semibold uppercase tracking-wide text-muted mb-3">Fiyat Senaryolari</h3>
            <div class="grid gap-3 sm:grid-cols-3">
              <div v-for="sc in sig.scenarios" :key="sc.label" class="card-2 p-3">
                <div class="flex items-center justify-between mb-1">
                  <span class="text-xs font-semibold uppercase" :class="scenarioColor(sc.label)">
                    {{ { base: 'Baz', bull: 'Boga', bear: 'Ayi' }[sc.label] ?? sc.label }}
                  </span>
                  <span class="rounded-md bg-surface px-1.5 py-0.5 text-[10px] text-faint">
                    {{ (sc.probability * 100).toFixed(0) }}% olasilik
                  </span>
                </div>
                <div class="num text-xl font-bold" :class="scenarioColor(sc.label)">{{ fmtPrice(sc.target_price) }}</div>
                <div class="num text-xs" :class="sc.expected_return_pct >= 0 ? 'text-bull' : 'text-bear'">
                  {{ fmtPct(sc.expected_return_pct) }}
                </div>
              </div>
            </div>
          </section>

          <!-- Entry zone / stop loss -->
          <section class="grid gap-3 sm:grid-cols-4">
            <div class="card-2 p-3">
              <div class="text-[10px] text-faint uppercase">Giris Alti</div>
              <div class="num text-lg font-semibold">{{ fmtPrice(sig.entry_zone_low) }}</div>
            </div>
            <div class="card-2 p-3">
              <div class="text-[10px] text-faint uppercase">Giris Ustu</div>
              <div class="num text-lg font-semibold">{{ fmtPrice(sig.entry_zone_high) }}</div>
            </div>
            <div class="card-2 p-3">
              <div class="text-[10px] text-faint uppercase">Stop Loss</div>
              <div class="num text-lg font-semibold text-bear">{{ fmtPrice(sig.stop_loss) }}</div>
            </div>
            <div class="card-2 p-3">
              <div class="text-[10px] text-faint uppercase">Beklenen Getiri</div>
              <div class="num text-lg font-semibold" :class="(sig.expected_return_pct ?? 0) >= 0 ? 'text-bull' : 'text-bear'">
                {{ fmtPct(sig.expected_return_pct) }}
              </div>
            </div>
          </section>

          <!-- Allocation -->
          <section v-if="sig.allocation_weight > 0" class="grid gap-3 sm:grid-cols-3">
            <div class="card-2 p-3">
              <div class="text-[10px] text-faint uppercase">Tahsis Agirligi</div>
              <div class="num text-lg font-semibold">{{ sig.allocation_weight.toFixed(1) }}%</div>
            </div>
            <div class="card-2 p-3">
              <div class="text-[10px] text-faint uppercase">Tahsis Tutari</div>
              <div class="num text-lg font-semibold">{{ fmtPrice(sig.allocation_cash) }} TL</div>
            </div>
            <div class="card-2 p-3">
              <div class="text-[10px] text-faint uppercase">Vade</div>
              <div class="num text-lg font-semibold">{{ sig.time_horizon_days ?? '—' }} <span class="text-xs text-muted">gun</span></div>
            </div>
          </section>

          <!-- Rationale: bull/bear debate -->
          <section>
            <h3 class="text-xs font-semibold uppercase tracking-wide text-muted mb-2">Analiz Raporu</h3>
            <div class="space-y-2">
              <div v-if="sig.rationale.trend" class="rounded-xl border border-bull/20 bg-bull/5 p-3 text-sm">
                <span class="font-semibold text-bull">▲ Trend</span>
                <p class="mt-1 text-text/85">{{ sig.rationale.trend }}</p>
              </div>
              <div v-if="sig.rationale.formation" class="rounded-xl border border-accent/20 bg-accent/5 p-3 text-sm">
                <span class="font-semibold text-accent">◆ Formasyon</span>
                <p class="mt-1 text-text/85">{{ sig.rationale.formation }}</p>
              </div>
              <div v-if="sig.rationale.volume" class="rounded-xl border border-accent/20 bg-accent/5 p-3 text-sm">
                <span class="font-semibold text-accent">◆ Hacim</span>
                <p class="mt-1 text-text/85">{{ sig.rationale.volume }}</p>
              </div>
              <div v-if="sig.rationale.fibonacci" class="rounded-xl border border-accent/20 bg-accent/5 p-3 text-sm">
                <span class="font-semibold text-accent">◆ Fibonacci</span>
                <p class="mt-1 text-text/85">{{ sig.rationale.fibonacci }}</p>
              </div>
              <div v-if="sig.rationale.news" class="rounded-xl border border-bear/20 bg-bear/5 p-3 text-sm">
                <span class="font-semibold text-bear">▼ Haberler / Riskler</span>
                <p class="mt-1 text-text/85">{{ sig.rationale.news }}</p>
              </div>
            </div>
          </section>

          <!-- Full rationale -->
          <section v-if="sig.rationale.full">
            <h3 class="text-xs font-semibold uppercase tracking-wide text-muted mb-2">Detayli Degerlendirme</h3>
            <div class="rounded-xl border border-border bg-surface-2 p-4 text-sm leading-relaxed text-text/80 whitespace-pre-line">
              {{ sig.rationale.full }}
            </div>
          </section>

          <!-- Risks -->
          <section v-if="sig.rationale.risks?.length">
            <h3 class="text-xs font-semibold uppercase tracking-wide text-muted mb-2">Risk Faktorleri</h3>
            <ul class="space-y-1">
              <li v-for="(r, i) in sig.rationale.risks" :key="i" class="flex gap-2 text-sm text-text/75">
                <span class="text-bear">&#9679;</span><span>{{ r }}</span>
              </li>
            </ul>
          </section>

          <!-- Warning flags -->
          <div v-if="sig.warning_flags?.length" class="flex flex-wrap gap-2">
            <span
              v-for="(w, i) in sig.warning_flags"
              :key="i"
              class="rounded-md bg-watch/10 border border-watch/30 px-2 py-0.5 text-[11px] text-watch"
            >{{ w }}</span>
          </div>

          <!-- Footer -->
          <div class="flex justify-between text-[11px] text-faint border-t border-border pt-3">
            <span class="num">{{ sig.llm_model }} · ${{ sig.llm_cost_usd.toFixed(4) }}</span>
            <span>{{ sig.generated_at }}</span>
          </div>
        </div>
      </div>
    </template>

    <!-- No analysis yet -->
    <div v-if="!loading && !error && !analysis" class="card p-12 text-center">
      <p class="text-muted mb-2">Henuz analiz yapilmamis</p>
      <p class="text-xs text-faint">Yukaridaki "Analiz Et" butonuna tiklayarak BIST-100 pipeline'ini baslatabilirsiniz</p>
    </div>
  </div>
</template>
