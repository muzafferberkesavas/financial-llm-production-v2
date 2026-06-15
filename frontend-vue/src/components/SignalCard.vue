<script setup lang="ts">
import { computed } from "vue";
import type { ExtendedSignal } from "@/types";
import { ACTION_META } from "@/types";

const props = defineProps<{ signal: ExtendedSignal }>();

const meta = computed(() => ACTION_META[props.signal.signal]);
const toneClass = computed(() => ({
  bull: "bg-bull/15 text-bull border-bull/30",
  bear: "bg-bear/15 text-bear border-bear/30",
  watch: "bg-watch/15 text-watch border-watch/30",
}[meta.value.tone]));
const confPct = computed(() => Math.round(props.signal.confidence * 100));
</script>

<template>
  <article class="rounded-2xl border border-border bg-surface p-4 transition hover:border-accent/40">
    <header class="flex items-start justify-between">
      <div>
        <div class="flex items-center gap-2">
          <h3 class="text-lg font-semibold tracking-tight">{{ signal.ticker }}</h3>
          <span v-if="signal.sector" class="text-[11px] text-muted">{{ signal.sector }}</span>
        </div>
        <div class="mt-0.5 text-[11px] text-muted">
          öncelik {{ signal.confluence_score.toFixed(0) }} · {{ signal.market_regime || '—' }}
        </div>
      </div>
      <span class="rounded-lg border px-2.5 py-1 text-xs font-semibold" :class="toneClass">
        {{ meta.label }}
      </span>
    </header>

    <!-- confidence + allocation -->
    <div class="mt-3 grid grid-cols-2 gap-3 text-xs">
      <div>
        <div class="mb-1 flex justify-between text-muted"><span>Güven</span><span>{{ confPct }}%</span></div>
        <div class="h-1.5 overflow-hidden rounded-full bg-surface-2">
          <div class="h-full rounded-full bg-accent" :style="{ width: confPct + '%' }" />
        </div>
      </div>
      <div>
        <div class="mb-1 flex justify-between text-muted"><span>Tahsis</span><span>{{ signal.allocation_weight.toFixed(1) }}%</span></div>
        <div class="text-white/90">${{ signal.allocation_cash.toLocaleString() }}
          <span v-if="signal.time_horizon_days" class="text-muted">· {{ signal.time_horizon_days }}g</span>
        </div>
      </div>
    </div>

    <!-- bull / bear -->
    <div v-if="signal.rationale.trend || signal.rationale.news" class="mt-3 space-y-1.5 text-xs">
      <p v-if="signal.rationale.trend" class="text-bull/90"><span class="font-semibold">▲</span> {{ signal.rationale.trend }}</p>
      <p v-if="signal.rationale.news" class="text-bear/90"><span class="font-semibold">▼</span> {{ signal.rationale.news }}</p>
    </div>

    <p v-if="signal.rationale.full" class="mt-3 text-xs leading-relaxed text-muted">
      {{ signal.rationale.full }}
    </p>

    <footer class="mt-3 flex items-center justify-between border-t border-border pt-2 text-[11px] text-muted">
      <span :class="signal.backtest_gate_passed ? 'text-bull' : 'text-bear'">
        {{ signal.backtest_gate_passed ? '✓ gate' : '✗ gate' }}
      </span>
      <span>{{ signal.llm_model.replace('claude-', '') }} · ${{ signal.llm_cost_usd.toFixed(4) }}</span>
    </footer>
  </article>
</template>
