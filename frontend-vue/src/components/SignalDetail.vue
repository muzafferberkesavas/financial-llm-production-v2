<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import type { ExtendedSignal } from "@/types";
import { ACTION_META } from "@/types";
import GaugeRing from "./GaugeRing.vue";
import ActionBadge from "./ActionBadge.vue";

const props = defineProps<{ signal: ExtendedSignal | null }>();
const emit = defineEmits<{ close: [] }>();
const router = useRouter();

const tone = computed(() => (props.signal ? ACTION_META[props.signal.signal].tone : "watch"));
const gaugeColor = computed(() => ({ bull: "#34d399", bear: "#f43f5e", watch: "#f0b454" }[tone.value]));

function goToDetail() {
  if (!props.signal) return;
  emit("close");
  router.push({ name: "stock-detail", params: { ticker: props.signal.ticker }, query: { market: props.signal.market } });
}
</script>

<template>
  <Transition name="drawer">
    <div v-if="signal" class="fixed inset-0 z-30 flex justify-end" @keydown.esc="emit('close')">
      <div class="absolute inset-0 bg-black/55 backdrop-blur-sm" @click="emit('close')" />
      <aside class="relative h-full w-full max-w-md overflow-y-auto border-l border-border bg-surface shadow-2xl">
        <header class="sticky top-0 z-10 flex items-start justify-between border-b border-border bg-surface/90 px-5 py-4 backdrop-blur">
          <div>
            <div class="flex items-center gap-2">
              <h2 class="num text-2xl font-semibold tracking-tight">{{ signal.ticker }}</h2>
              <ActionBadge :action="signal.signal" />
            </div>
            <div class="mt-1 text-xs text-muted">{{ signal.sector || '—' }} · {{ signal.market.toUpperCase() }}</div>
          </div>
          <button class="rounded-lg p-1.5 text-muted hover:bg-surface-2 hover:text-white" @click="emit('close')">✕</button>
        </header>

        <div class="space-y-5 p-5">
          <!-- Hisse Detay butonu -->
          <button
            class="w-full rounded-lg border border-border bg-surface-2 py-2 text-sm font-medium text-muted transition hover:bg-surface hover:text-text"
            @click="goToDetail"
          >Hisse Detayi &rarr;</button>
          <!-- key metrics -->
          <div class="flex items-center gap-4">
            <GaugeRing :value="signal.confidence" :color="gaugeColor" :size="92" label="güven" />
            <div class="grid flex-1 grid-cols-2 gap-2.5">
              <div class="card-2 px-3 py-2">
                <div class="num text-lg" :class="signal.allocation_weight > 0 ? '' : 'text-faint'">
                  {{ signal.allocation_weight > 0 ? signal.allocation_weight.toFixed(1) + '%' : '—' }}
                </div>
                <div class="text-[10px] text-muted">tahsis ağırlığı</div>
              </div>
              <div class="card-2 px-3 py-2">
                <div class="num text-lg">{{ signal.confluence_score.toFixed(0) }}</div>
                <div class="text-[10px] text-muted">öncelik skoru</div>
              </div>
              <div class="card-2 px-3 py-2">
                <div class="num text-lg">{{ signal.time_horizon_days ?? '—' }}<span v-if="signal.time_horizon_days" class="text-xs text-muted">g</span></div>
                <div class="text-[10px] text-muted">vade</div>
              </div>
              <div class="card-2 px-3 py-2">
                <div class="num text-lg" :class="signal.backtest_gate_passed ? 'text-bull' : 'text-bear'">
                  {{ signal.backtest_gate_passed ? '✓' : '✗' }}
                </div>
                <div class="text-[10px] text-muted">backtest gate</div>
              </div>
            </div>
          </div>

          <!-- bull / bear debate -->
          <section>
            <h3 class="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">Bull / Bear Tartışması</h3>
            <div class="space-y-2">
              <div v-if="signal.rationale.trend" class="rounded-xl border border-bull/20 bg-bull/5 p-3 text-sm text-bull/90">
                <span class="font-semibold">▲ Boğa</span><p class="mt-1 text-text/85">{{ signal.rationale.trend }}</p>
              </div>
              <div v-if="signal.rationale.news" class="rounded-xl border border-bear/20 bg-bear/5 p-3 text-sm text-bear/90">
                <span class="font-semibold">▼ Ayı</span><p class="mt-1 text-text/85">{{ signal.rationale.news }}</p>
              </div>
            </div>
          </section>

          <!-- judge rationale -->
          <section v-if="signal.rationale.full">
            <h3 class="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">Hakem Gerekçesi</h3>
            <p class="text-sm leading-relaxed text-text/80">{{ signal.rationale.full }}</p>
          </section>

          <!-- risks -->
          <section v-if="signal.rationale.risks?.length">
            <h3 class="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">Ana Riskler</h3>
            <ul class="space-y-1.5">
              <li v-for="(r, i) in signal.rationale.risks" :key="i" class="flex gap-2 text-sm text-text/75">
                <span class="text-bear">•</span><span>{{ r }}</span>
              </li>
            </ul>
          </section>

          <footer class="flex justify-between border-t border-border pt-3 text-[11px] text-faint">
            <span class="num">{{ signal.llm_model.replace('claude-', 'Claude ') }}</span>
            <span class="num">${{ signal.llm_cost_usd.toFixed(4) }}</span>
          </footer>
        </div>
      </aside>
    </div>
  </Transition>
</template>

<style scoped>
.drawer-enter-active, .drawer-leave-active { transition: opacity 0.2s; }
.drawer-enter-active aside, .drawer-leave-active aside { transition: transform 0.25s ease; }
.drawer-enter-from, .drawer-leave-to { opacity: 0; }
.drawer-enter-from aside, .drawer-leave-to aside { transform: translateX(100%); }
</style>
