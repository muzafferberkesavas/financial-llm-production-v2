<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { useRouter } from "vue-router";
import type { AnalysisResponse, AnalysisSignal } from "@/types";
import { ACTION_META } from "@/types";
import { runBistAnalysis, fetchLatestAnalysis, fetchPromptPreview, fetchScoring, fetchLatestScoring } from "@/lib/api";
import type { PromptPreviewResponse, PromptCandidate, ScoringResponse } from "@/lib/api";

const router = useRouter();
const analysis = ref<AnalysisResponse | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);
const expandedTicker = ref<string | null>(null);
const llmBackend = ref("claude");

// Scoring state
const scoringLoading = ref(false);
const scoringData = ref<ScoringResponse | null>(null);
const scoringError = ref<string | null>(null);
const expandedScoring = ref<string | null>(null);

async function runScoring() {
  scoringLoading.value = true;
  scoringError.value = null;
  scoringData.value = null;
  try {
    scoringData.value = await fetchScoring(20, true);
  } catch (e: any) {
    scoringError.value = e.message ?? "Skorlama basarisiz";
  } finally {
    scoringLoading.value = false;
  }
}

function scoreLabelClass(label: string): string {
  if (label === "STRONG" || label === "VERY_STRONG") return "text-bull";
  if (label === "GOOD") return "text-accent";
  if (label === "MODERATE") return "text-watch";
  return "text-bear";
}

function scoreBarColor(pct: number): string {
  if (pct >= 70) return "bg-bull";
  if (pct >= 55) return "bg-accent";
  if (pct >= 40) return "bg-watch";
  return "bg-bear";
}

// Prompt preview state
const previewLoading = ref(false);
const previewData = ref<PromptPreviewResponse | null>(null);
const previewError = ref<string | null>(null);
const showPromptModal = ref(false);
const selectedCandidate = ref<PromptCandidate | null>(null);
const copiedField = ref<string | null>(null);

async function loadPromptPreview() {
  previewLoading.value = true;
  previewError.value = null;
  previewData.value = null;
  try {
    previewData.value = await fetchPromptPreview(5);
  } catch (e: any) {
    previewError.value = e.message ?? "Prompt onizleme basarisiz";
  } finally {
    previewLoading.value = false;
  }
}

function openPromptModal(cand: PromptCandidate) {
  selectedCandidate.value = cand;
  showPromptModal.value = true;
}

function closePromptModal() {
  showPromptModal.value = false;
  selectedCandidate.value = null;
  copiedField.value = null;
}

async function copyToClipboard(text: string, field: string) {
  await navigator.clipboard.writeText(text);
  copiedField.value = field;
  setTimeout(() => { copiedField.value = null; }, 2000);
}

onMounted(async () => {
  // Son skorlama + son analiz dosyadan yukle (varsa)
  const [scoringRes, analysisRes] = await Promise.allSettled([
    fetchLatestScoring(),
    fetchLatestAnalysis(),
  ]);
  if (scoringRes.status === "fulfilled" && scoringRes.value.status !== "no_scoring") {
    scoringData.value = scoringRes.value;
  }
  if (analysisRes.status === "fulfilled" && analysisRes.value.status !== "no_analysis") {
    analysis.value = analysisRes.value;
  }
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
          class="rounded-lg border border-watch/50 bg-watch/10 px-5 py-2.5 text-sm font-semibold text-watch transition hover:bg-watch/20 disabled:opacity-50"
          :disabled="scoringLoading || loading"
          @click="runScoring"
        >
          <span v-if="scoringLoading" class="inline-flex items-center gap-2">
            <span class="inline-block h-4 w-4 animate-spin rounded-full border-2 border-watch/30 border-t-watch" />
            Skorlaniyor...
          </span>
          <span v-else>Skorlama</span>
        </button>
        <button
          class="rounded-lg border border-accent/50 bg-accent/10 px-5 py-2.5 text-sm font-semibold text-accent transition hover:bg-accent/20 disabled:opacity-50"
          :disabled="previewLoading || loading"
          @click="loadPromptPreview"
        >
          <span v-if="previewLoading" class="inline-flex items-center gap-2">
            <span class="inline-block h-4 w-4 animate-spin rounded-full border-2 border-accent/30 border-t-accent" />
            Promptlar hazirlaniyor...
          </span>
          <span v-else>Prompt Onizleme</span>
        </button>
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

    <!-- Scoring Error -->
    <div v-if="scoringError" class="rounded-xl border border-bear/30 bg-bear/5 p-4 text-sm text-bear">
      {{ scoringError }}
    </div>

    <!-- Scoring Results -->
    <template v-if="scoringData">
      <div class="card p-4">
        <div class="flex items-center justify-between mb-3">
          <h2 class="text-sm font-semibold">Master Scorecard Siralaması</h2>
          <div class="flex items-center gap-3 text-[11px] text-faint">
            <span>Evren: {{ scoringData.universe_size }}</span>
            <span>Filtre Gecen: {{ scoringData.passed_filter }}</span>
            <span>Top {{ scoringData.scored_count }}</span>
            <span>{{ scoringData.duration_sec }}s</span>
            <span v-if="scoringData.from_cache" class="rounded-md bg-watch/10 border border-watch/30 px-1.5 py-0.5 text-watch">
              Cache ({{ scoringData.cache_age_min }}dk once)
            </span>
            <span v-else class="text-bull">Taze veri</span>
          </div>
        </div>

        <!-- Table header -->
        <div class="grid grid-cols-[1fr_80px_60px_80px_60px_80px] gap-2 px-3 py-2 text-[10px] text-faint uppercase border-b border-border">
          <span>Hisse</span>
          <span class="text-right">Skor</span>
          <span class="text-right">%</span>
          <span class="text-right">Confluence</span>
          <span class="text-right">Rejim</span>
          <span class="text-right">Setup</span>
        </div>

        <!-- Rows -->
        <div v-for="(stock, idx) in scoringData.stocks" :key="stock.ticker">
          <div
            class="grid grid-cols-[1fr_80px_60px_80px_60px_80px] gap-2 items-center px-3 py-2.5 cursor-pointer hover:bg-surface-2 transition border-b border-border/50"
            @click="expandedScoring = expandedScoring === stock.ticker ? null : stock.ticker"
          >
            <div class="flex items-center gap-2">
              <span class="num text-xs font-mono text-faint w-5">{{ idx + 1 }}</span>
              <span class="num text-sm font-bold">{{ stock.ticker }}</span>
              <span class="text-xs text-muted hidden sm:inline">{{ stock.name }}</span>
              <span class="rounded-md bg-surface-2 px-1 py-0.5 text-[9px] text-faint hidden sm:inline">{{ stock.sector }}</span>
            </div>
            <div class="text-right">
              <span class="num text-sm font-semibold">{{ stock.master_score }}</span>
              <span class="text-[10px] text-faint">/{{ stock.max_possible }}</span>
            </div>
            <div class="text-right">
              <span class="num text-sm font-bold" :class="scoreLabelClass(stock.label)">{{ stock.pct }}%</span>
            </div>
            <div class="text-right num text-sm">{{ stock.confluence_score }}</div>
            <div class="text-right text-[11px] capitalize text-muted">{{ stock.regime?.replace('_', ' ').toLowerCase() }}</div>
            <div class="text-right text-[11px] text-muted">{{ stock.setup_type !== 'none' ? stock.setup_type : '—' }}</div>
          </div>

          <!-- Expanded category breakdown -->
          <div v-if="expandedScoring === stock.ticker" class="px-3 py-3 bg-surface-2/50 border-b border-border">
            <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2">
              <div v-for="(cat, catName) in stock.categories" :key="catName" class="rounded-lg border border-border bg-surface p-2">
                <div class="text-[9px] text-faint uppercase truncate">{{ catName }}</div>
                <div class="flex items-center gap-2 mt-1">
                  <div class="flex-1 h-1.5 rounded-full bg-surface-2 overflow-hidden">
                    <div class="h-full rounded-full transition-all" :class="scoreBarColor(cat.max > 0 ? cat.score / cat.max * 100 : 0)" :style="{ width: (cat.max > 0 ? cat.score / cat.max * 100 : 0) + '%' }" />
                  </div>
                  <span class="num text-[11px] font-semibold">{{ cat.score }}/{{ cat.max }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- Prompt Preview Error -->
    <div v-if="previewError" class="rounded-xl border border-bear/30 bg-bear/5 p-4 text-sm text-bear">
      {{ previewError }}
    </div>

    <!-- Prompt Preview Results -->
    <template v-if="previewData">
      <div class="card p-4">
        <div class="flex items-center justify-between mb-3">
          <h2 class="text-sm font-semibold">Prompt Onizleme — Adaylar</h2>
          <div class="flex items-center gap-3 text-[11px] text-faint">
            <span>Evren: {{ previewData.universe_size }}</span>
            <span>Filtre Gecen: {{ previewData.passed_filter }}</span>
            <span>Top {{ previewData.candidate_count }} Aday</span>
            <span>{{ previewData.duration_sec }}s</span>
          </div>
        </div>
        <div class="space-y-2">
          <div
            v-for="cand in previewData.candidates"
            :key="cand.ticker"
            class="flex items-center justify-between rounded-lg border border-border bg-surface-2 p-3 hover:bg-surface transition"
          >
            <div class="flex items-center gap-3">
              <span class="num text-sm font-bold">{{ cand.ticker }}</span>
              <span class="text-xs text-muted">{{ cand.name }}</span>
              <span class="rounded-md bg-surface px-1.5 py-0.5 text-[10px] text-faint">{{ cand.sector }}</span>
            </div>
            <div class="flex items-center gap-3">
              <span class="text-[11px] text-faint">Skor: <span class="num text-muted">{{ cand.master_score_pct?.toFixed(0) ?? '-' }}%</span></span>
              <span class="text-[11px] text-faint">Confluence: <span class="num text-muted">{{ cand.confluence_score }}</span></span>
              <span class="text-[11px] text-faint capitalize">{{ cand.regime }}</span>
              <button
                class="rounded-lg border border-accent/40 bg-accent/10 px-3 py-1.5 text-xs font-semibold text-accent transition hover:bg-accent/20"
                @click="openPromptModal(cand)"
              >
                Promptlari Gor
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- Prompt Modal -->
    <Teleport to="body">
      <div v-if="showPromptModal && selectedCandidate && previewData" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="closePromptModal" />
        <div class="relative z-10 w-full max-w-4xl max-h-[90vh] overflow-y-auto rounded-2xl border border-border bg-bg p-6 shadow-2xl mx-4">
          <!-- Modal header -->
          <div class="flex items-center justify-between mb-5">
            <div>
              <h2 class="text-lg font-bold">{{ selectedCandidate.ticker }} — Claude Opus Promptlari</h2>
              <p class="text-xs text-muted mt-0.5">Bu promptlari kopyalayip Claude'a yapistirabilirsiniz</p>
            </div>
            <button class="rounded-lg p-2 text-muted hover:bg-surface-2 transition" @click="closePromptModal">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
              </svg>
            </button>
          </div>

          <!-- System Prompt -->
          <div class="mb-5">
            <div class="flex items-center justify-between mb-2">
              <h3 class="text-sm font-semibold text-accent">System Prompt</h3>
              <button
                class="rounded-md px-3 py-1 text-xs font-medium transition"
                :class="copiedField === 'system' ? 'bg-bull/20 text-bull' : 'bg-surface-2 text-muted hover:bg-surface'"
                @click="copyToClipboard(previewData!.system_prompt, 'system')"
              >
                {{ copiedField === 'system' ? 'Kopyalandi!' : 'Kopyala' }}
              </button>
            </div>
            <pre class="rounded-xl border border-border bg-surface-2 p-4 text-xs leading-relaxed text-text/80 overflow-x-auto max-h-60 overflow-y-auto whitespace-pre-wrap">{{ previewData.system_prompt }}</pre>
          </div>

          <!-- User Prompt -->
          <div>
            <div class="flex items-center justify-between mb-2">
              <h3 class="text-sm font-semibold text-accent">User Prompt</h3>
              <button
                class="rounded-md px-3 py-1 text-xs font-medium transition"
                :class="copiedField === 'user' ? 'bg-bull/20 text-bull' : 'bg-surface-2 text-muted hover:bg-surface'"
                @click="copyToClipboard(selectedCandidate!.user_prompt, 'user')"
              >
                {{ copiedField === 'user' ? 'Kopyalandi!' : 'Kopyala' }}
              </button>
            </div>
            <pre class="rounded-xl border border-border bg-surface-2 p-4 text-xs leading-relaxed text-text/80 overflow-x-auto max-h-80 overflow-y-auto whitespace-pre-wrap">{{ selectedCandidate.user_prompt }}</pre>
          </div>

          <!-- Copy All -->
          <div class="mt-5 flex justify-end">
            <button
              class="rounded-lg px-5 py-2.5 text-sm font-semibold transition"
              :class="copiedField === 'all' ? 'bg-bull/20 text-bull border border-bull/30' : 'bg-accent text-white hover:bg-accent/80'"
              @click="copyToClipboard('=== SYSTEM PROMPT ===\n\n' + previewData!.system_prompt + '\n\n=== USER PROMPT ===\n\n' + selectedCandidate!.user_prompt, 'all')"
            >
              {{ copiedField === 'all' ? 'Tumunu Kopyalandi!' : 'Tumunu Kopyala' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

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
