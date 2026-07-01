<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import type { ExtendedSignal } from "@/types";
import { ACTION_META } from "@/types";
import GaugeRing from "./GaugeRing.vue";
import ActionBadge from "./ActionBadge.vue";

const props = defineProps<{ signal: ExtendedSignal }>();
const emit = defineEmits<{ open: [ExtendedSignal] }>();
const router = useRouter();

const tone = computed(() => ACTION_META[props.signal.signal].tone);
const gaugeColor = computed(() => ({ bull: "#34d399", bear: "#f43f5e", watch: "#f0b454" }[tone.value]));

function goToDetail(e: Event) {
  e.stopPropagation();
  router.push({ name: "stock-detail", params: { ticker: props.signal.ticker }, query: { market: props.signal.market } });
}
</script>

<template>
  <article
    class="card group cursor-pointer p-4 transition hover:border-border-2 hover:bg-surface-2"
    @click="emit('open', signal)"
  >
    <header class="flex items-start justify-between gap-3">
      <div class="min-w-0">
        <div class="flex items-center gap-2">
          <h3 class="num text-lg font-semibold tracking-tight hover:text-accent hover:underline" @click="goToDetail($event)">{{ signal.ticker }}</h3>
          <span v-if="signal.sector" class="truncate text-[11px] text-muted">{{ signal.sector }}</span>
        </div>
        <div class="mt-0.5 flex items-center gap-2 text-[11px] text-faint">
          <span>öncelik <span class="num text-muted">{{ signal.confluence_score.toFixed(0) }}</span></span>
          <span v-if="signal.market_regime" class="capitalize">· {{ signal.market_regime }}</span>
        </div>
      </div>
      <GaugeRing :value="signal.confidence" :color="gaugeColor" :size="60" />
    </header>

    <div class="mt-1 flex items-center justify-between">
      <ActionBadge :action="signal.signal" />
      <div class="text-right text-xs">
        <div class="num font-medium" :class="signal.allocation_weight > 0 ? 'text-text' : 'text-faint'">
          {{ signal.allocation_weight > 0 ? signal.allocation_weight.toFixed(1) + '%' : '—' }}
        </div>
        <div class="text-[10px] text-muted">tahsis</div>
      </div>
    </div>

    <!-- bull / bear thesis -->
    <div class="mt-3 space-y-1.5 border-t border-border pt-3 text-xs">
      <p v-if="signal.rationale.trend" class="line-clamp-2 text-bull/90">
        <span class="font-semibold">▲</span> {{ signal.rationale.trend }}
      </p>
      <p v-if="signal.rationale.news" class="line-clamp-2 text-bear/90">
        <span class="font-semibold">▼</span> {{ signal.rationale.news }}
      </p>
    </div>

    <footer class="mt-3 flex items-center justify-between text-[10px] text-faint">
      <span class="inline-flex items-center gap-1" :class="signal.backtest_gate_passed ? 'text-bull/80' : 'text-bear/80'">
        <span class="h-1 w-1 rounded-full" :class="signal.backtest_gate_passed ? 'bg-bull' : 'bg-bear'" />
        gate {{ signal.backtest_gate_passed ? 'geçti' : 'kaldı' }}
      </span>
      <span class="num">{{ signal.llm_model.replace('claude-', '') }} · ${{ signal.llm_cost_usd.toFixed(4) }}</span>
    </footer>
  </article>
</template>
